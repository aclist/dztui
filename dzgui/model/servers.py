import logging
import threading
from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, TYPE_CHECKING

import dzgui.api.servers as Servers
from dzgui.const.enum import FilterMode, Preferences, ServerTab
from dzgui.const.constants import (
    APPID_DAYZ,
    APPID_DAYZ_EXP,
)
from dzgui.managers.config import ConfigManager
from dzgui.managers.thread_man import call_on_thread, StoredFunc, ThreadingManager
from dzgui.util.strings import api_warn_msg, dialog
from dzgui.views.dialogs.generic import ExceptionDialog

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402

LAN_TIMEOUT = 0.5
API_TIMEOUT = 3

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller
    from dzgui.model.filtered_model import FilteredModelManager

logger = logging.getLogger(__name__)


# TODO: failure: spawns error dialog
# TODO: non failure with empty model: updates statusbar with help text


class ServerModelManager:
    def __init__(
        self, controller: "Controller", tv: Gtk.TreeView, first_iteration=False
    ) -> None:

        self.tv = tv
        self.enum = tv.get_enum()
        self.controller = controller
        self.emitter = controller.get_emitter()

        self.jobs = 1

        # NOTE: store filter man for access inside thread
        self.filter_man = tv.get_filter_man()

        # FIXME: change WaitDialog to use parent window only
        self.thread_man = ThreadingManager(parent=controller)

        # TODO: if first iteration, clear filter man control model
        # literal first load: iteration 1
        # refresh: iteration 1 (wipe model)
        # filter: iteration N+1
        # TODO: can drop first iteration arg and process in methods
        self.first_iteration = first_iteration

    def load(self) -> None:
        """
        There may be cases where you want to instantiate this class without dumping servers,
        e.g., adding saved servers from another tab
        """
        match self.enum:
            case ServerTab.BROWSER:
                # NOTE: extra DAYZ_EXP param
                self.thread_man.set_job_count(len(Servers.params) + 1)
                self._dump_api()
            case ServerTab.SAVED:
                self._dump_favorites()
            case ServerTab.RECENT:
                self._dump_history()
            case ServerTab.LAN:
                # NOTE: LAN tab is only loaded on demand
                pass
            case _:
                pass

    @call_on_thread(dialog.fetching)
    def _dump_api(self) -> None:
        config_man = self.controller.get_config_man()
        key = config_man.lookup(Preferences.STEAM)
        job = Servers.query_api
        params = Servers.params
        servers = []
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(job, key, APPID_DAYZ, param) for param in params]
            for future in as_completed(futures):
                try:
                    self.thread_man.increment_dialog()
                    res = future.result(timeout=API_TIMEOUT)
                    if res.status != 200 or not res.parsed:
                        self.thread_man.set_cleanup_func(
                            StoredFunc(self._cleanup_on_failure)
                        )
                        return
                    j = res.json
                    servers += j["response"]["servers"]
                except Exception as e:
                    # TODO: could store exception in cleanup func
                    logger.critical(e)
                    self.thread_man.set_cleanup_func(
                        StoredFunc(self._cleanup_on_failure)
                    )
                    return

        # NOTE: This step is allowed to fail, since this metadata is incidental
        res = Servers.query_api(key, APPID_DAYZ_EXP, "")
        if res.status == 200 and res.parsed is True:
            j = res.json
            servers += j["response"]["servers"]

        parsed = Servers.parse_json(servers)
        self._push_data(parsed, FilterMode.INITIAL)

    @call_on_thread(dialog.scanning)
    def dump_lan(self, port: int, early_abort: bool) -> None:
        servers = []
        ports = range(1, 256)

        event = threading.Event()
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(Servers.test_ip, i, port, event) for i in ports]
            for future in as_completed(futures):
                try:
                    res = future.result(timeout=LAN_TIMEOUT)
                    if res is not None and early_abort is True:
                        # NOTE: first non-empty hit, flag pending threads to close
                        event.set()
                        servers.append(res)
                        self.thread_man.set_cleanup_func(
                            StoredFunc(self._cleanup_on_success)
                        )
                        return
                    if res is None:
                        continue
                    servers.append(res)
                except Exception as e:
                    logger.critical(e)
                    self.thread_man.set_cleanup_func(
                        StoredFunc(self._cleanup_on_failure)
                    )
            if len(servers) == 0:
                self.thread_man.set_cleanup_func(StoredFunc(self._cleanup_on_failure))
                return
        parsed = Servers.parse_json(servers)
        self._push_data(parsed, FilterMode.INITIAL)

    @call_on_thread(dialog.fetching)
    def _dump_ips(self, ips: list[str]) -> None:
        # NOTE: block malformed records (TODO: add github issue no.)
        # TODO: sanitize ip list at config time and drop this
        ips = [ip for ip in ips if len(ip.split(":")) == 3 and ip.split(":")[2] != ""]
        job = Servers.query_direct
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    job,
                    ip.split(":")[0],
                    int(ip.split(":")[2]),
                )
                for ip in ips
            ]
            servers = []
            for future in as_completed(futures):
                res = future.result()
                self.thread_man.increment_dialog()
                # NOTE: failing entries are culled
                if res is None:
                    continue
                servers.append(res)
                if len(servers) == 0:
                    self.thread_man.set_cleanup_func(
                        StoredFunc(self._cleanup_on_failure)
                    )
                    return

        parsed = Servers.parse_json(servers)
        self._push_data(parsed, FilterMode.INITIAL)

    @call_on_thread(dialog.querying)
    def _add_by_id_or_ip(self, addr: str) -> None:
        res = Servers.query_id_or_ip(addr)
        if res is None:
            self.thread_man.set_cleanup_func(StoredFunc(self._cleanup_on_failure))
            return

        record = Servers.parse_json([res])

        filter_man = self._get_filter_man()
        model = filter_man.get_control()

        fqip = Servers.response_to_fq_ip(res)
        config_man = self.controller.get_config_man()
        config_man.add_saved_server(fqip)

        if model is not None:
            # NOTE: single record insertion
            model.append(record[0])
            # TODO: if all filters are already applied, strange behavior may occur
            # -> need to insert and update per current filters
            filter_man.filter(FilterMode.INITIAL)

        self.thread_man.set_cleanup_func(StoredFunc(self._cleanup_single_ip))

    def _dump_history(self) -> None:
        history = self.controller.get_prefs().paths.history
        # TODO: customize statusbar to mention how records are added after connecting
        try:
            with open(history, "r") as f:
                rows = [row.rstrip("\n") for row in f]
        except OSError:
            self.thread_man.set_cleanup_func(
                StoredFunc(self._cleanup_on_failure, False)
            )
            return
        if len(rows) == 0:
            self.thread_man.set_cleanup_func(
                StoredFunc(self._cleanup_on_failure, False)
            )
            return
        self.thread_man.set_job_count(len(rows))
        self._dump_ips(rows)

    def _dump_favorites(self) -> None:
        config_man = self.controller.get_config_man()
        ips = config_man.lookup(Preferences.IP_LIST)
        self.thread_man.set_job_count(len(ips))

        # TODO: customize statusbar to mention how records can be added via contextmenu
        if len(ips) == 0:
            # FIXME: this is not a failure, just a quiet exit with custom statusbar
            # TODO: add custom statusbar parameters
            self.thread_man.set_cleanup_func(
                StoredFunc(self._cleanup_on_failure, False)
            )
            return
        self._dump_ips(ips)

    def _cleanup_single_ip(self) -> None:
        proxy = self._get_filter_man().get_proxy_model()
        self.tv.set_model(proxy)

        # TODO: if current tab != self.saved, add label
        # TODO: adding a row may update available maps
        self.emitter.emit("servers_loaded", self.enum)
        self._update_maps()

    def _update_maps(self) -> None:
        map_man = self.tv.get_map_man()
        map_man.set_unique_maps(self._get_new_maps())
        self.emitter.emit("servers_loaded_init")
        self.first_iteration = False

    def _cleanup_on_success(self) -> None:
        self.tv.set_model(self.to_insert)

        # inserting a row serializes file on disk, updates control model for that tab, and updates model
        # NOTE: when inserting new rows, the entire control model is wiped and rebuilt, then proxy model is swapped in
        # TODO: signals or other approach to deferring map
        # model insertion after thread closes
        # cf. servers_loaded signal

        # TODO: servers_loaded vs servers_reloaded
        context = self.tv.get_enum()
        self.emitter.emit("servers_loaded", context)

        if self.first_iteration:
            self._update_maps()

    def _cleanup_on_failure(self, show_dialog=True) -> None:
        map_man = self.tv.get_map_man()

        # TODO: disable map, keyword, and filter widgets if model is None
        # -> signal driven (servers_empty, servers_failed_to_load)
        # TODO: what if refresh action occurred and failed, and the old model is still valid?
        # skip the step below if refresh action failed
        # do not wipe control model in this case
        # e.g. if treeview.is_refresh():
        # revert old model
        # wipe refresh state to False

        self.tv.set_model(None)
        map_man.set_unique_maps(None)
        context = self.tv.get_enum()

        # TODO: distinguish signals, e.g. "servers_failed_to_load", "servers_loaded_empty"
        # customize statusbar and dialog accordingly
        self.emitter.emit("servers_loaded", context)
        if show_dialog:
            dialog = ExceptionDialog(self.controller, api_warn_msg)
            dialog.run()

    # TODO: break into initial dump and refilter modes, can drop filtermode kwarg
    # and stop pushing empty data
    def _push_data(self, data: tuple, mode: Optional[FilterMode]) -> None:
        # FIXME: calls treeview read methods in thread
        # treeview = self.get_active_treeview()
        # manager = treeview.get_filter_man()
        manager = self._get_filter_man()

        if data is None:
            self.to_insert = None
        else:
            if mode == FilterMode.INITIAL:
                manager.set_control(data)
            manager.filter(mode)
            self.to_insert = manager.get_proxy_model()

            u_maps = set([row[1] for row in data])
            self._set_new_maps(sorted(u_maps))

        self.thread_man.set_cleanup_func(StoredFunc(self._cleanup_on_success))

    def _set_new_maps(self, maps: list[str]) -> None:
        self.new_maps = maps

    def _get_new_maps(self) -> list[str]:
        return self.new_maps

    def _get_filter_man(self) -> "FilteredModelManager":
        return self.filter_man

    # TODO: unimplemented
    # @call_on_thread(strings.dialog.filtering)
    # def filter_threaded(
    #     self, filter_man: "FilteredModelManager", mode: FilterMode, label: str
    # ) -> None:
    #     filter_man.filter(mode, label)
    #     self.to_insert = filter_man.get_proxy_model()
    #     print("filtering threaded")
    #     self.cleanup_func = StoredFunc(self.cleanup_on_success)

    # TODO: call filter_man methods directly
    def refilter_model(self, mode: FilterMode, label: Optional[str] = None) -> None:
        tv = self.get_active_treeview()
        self.filter_man = tv.get_filter_man()
        if self.filter_man.get_control() is None:
            return
        self.filter_threaded(self.filter_man, mode, label)
