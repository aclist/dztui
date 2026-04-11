import logging
import threading
from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import dzgui.api.servers as Servers
from dzgui.const.enum import FilterMode, Preferences, ServerTab
from dzgui.const.constants import (
    APPID_DAYZ,
    APPID_DAYZ_EXP,
)
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
    from dzgui.model.proxy_model import ProxyModelManager

logger = logging.getLogger(__name__)


# TODO: failure: spawns error dialog
# TODO: non failure with empty model: updates statusbar with help text


class ServerModelManager:
    def __init__(self, controller: "Controller", tv: Gtk.TreeView) -> None:

        self.tv = tv
        self.enum = tv.get_enum()
        self.controller = controller
        self.emitter = controller.get_emitter()

        self.first_iteration: bool
        self.preserve_on_fail = False
        self.jobs = 1

        # NOTE: store filter man for access inside thread
        self.proxy_man = tv.get_proxy_man()

        # FIXME: change WaitDialog to use parent window only
        self.thread_man = ThreadingManager(parent=controller)

        # TODO: if first iteration, clear filter man control model
        # literal first load: iteration 1
        # refresh: should be functionally identical to iteration 1
        # filter: iteration N+1

    def load(self) -> None:
        """
        There may be cases where you want to instantiate this class without dumping servers,
        e.g., adding saved servers from another tab
        """
        self.first_iteration = True
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

    def refresh(self) -> None:
        self.preserve_on_fail = True
        self.load()
        # TODO: if refresh is active, callback to button decrement signal
        # and do not mark refresh as sensitive

    @call_on_thread(dialog.fetching)
    def _dump_api(self) -> None:
        # TODO: pass api key a priori in .load() call
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

        # NOTE: this step is allowed to fail, since this metadata is incidental
        res = Servers.query_api(key, APPID_DAYZ_EXP, "")
        if res.status == 200 and res.parsed is True:
            j = res.json
            servers += j["response"]["servers"]

        parsed = Servers.parse_json(servers)
        self._push_data(parsed)

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
                        # NOTE: on first non-empty hit, flag pending threads to close
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
        self._push_data(parsed)

    @call_on_thread(dialog.fetching)
    def _dump_ips(self, ips: list[str]) -> None:
        # NOTE: block malformed records (TODO: add github issue no.)
        # TODO: sanitize ip list at config time and drop this
        # TODO: make test for this
        ips = [ip for ip in ips if len(ip.split(":")) == 3 and ip.split(":")[2] != ""]
        job = Servers.query_direct
        servers = []
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    job,
                    ip.split(":")[0],
                    int(ip.split(":")[2]),
                )
                for ip in ips
            ]
            for future in as_completed(futures):
                res = future.result(timeout=API_TIMEOUT)
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
        self._push_data(parsed)

    # TODO: add cleanup?
    # FIXME: use "adding server" string
    @call_on_thread(dialog.querying)
    def add_by_id(self, addr: str) -> None:
        config_man = self.controller.get_config_man()
        key = config_man.lookup(Preferences.BM)
        res = Servers.query_by_id(addr, key)
        self._parse_single_record(res)

    # TODO: add cleanup?
    # FIXME: use "adding server" string
    @call_on_thread(dialog.querying)
    def add_by_ip(self, addr: str) -> None:
        res = Servers.query_by_ip(addr)
        self._parse_single_record(res)

    # TODO: add cleanup?
    # FIXME: use "adding server" string
    @call_on_thread(dialog.querying)
    def add_by_record(self, record: Servers.Record) -> None:
        res = Servers.query_by_record(record)
        self._parse_single_record(res)

    def add_by_str(self, addr: str) -> None:
        if addr.isdigit():
            self.add_by_id(addr)
        else:
            self.add_by_ip(addr)

    def _parse_single_record(self, response: dict) -> None:
        if response is None:
            self.thread_man.set_cleanup_func(StoredFunc(self._cleanup_on_failure))
            return

        records = Servers.parse_json([response])
        record = records[0]

        proxy_man = self._get_proxy_man()
        raw_model = proxy_man.get_control()

        fqip = Servers.response_to_fq_ip(response)
        config_man = self.controller.get_config_man()
        config_man.add_saved_server(fqip)

        # NOTE: if tab contents were not loaded yet
        if raw_model is None:
            return

        # NOTE: expected to only contain one item
        raw_model.append(record)

        # TODO: if all filters are already applied, strange behavior may occur
        # -> need to insert and reupdate tree per current filters
        # for example, non-empty will only show up in empty because it is not cached
        proxy_man.filter(FilterMode.INITIAL)

        filter_man = self.tv.get_filter_man()
        old_maps = filter_man.get_unique_maps()
        cur_map = record[1]
        if cur_map not in old_maps:
            self._set_new_maps([cur_map])
        self.thread_man.set_cleanup_func(StoredFunc(self._cleanup_single_ip))

    def _dump_history(self) -> None:
        history = self.controller.get_prefs().paths.history
        try:
            with open(history, "r") as f:
                rows = [row.rstrip("\n") for row in f]
        except OSError:
            self.thread_man.set_cleanup_func(
                StoredFunc(self._cleanup_on_failure, False)
            )
            return
        if len(rows) == 0:
            # TODO: customize statusbar to mention how records are added after connecting
            # cf. cleanup on empty
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
        proxy = self._get_proxy_man().get_proxy_model()
        self.tv.set_model(proxy)

        # TODO: if current tab != self.saved, add label
        self.emitter.emit("servers_loaded", self.enum)

        # TODO: consolidate methods and handle multi/single map addition
        filter_man = self.tv.get_filter_man()
        filter_man.append_map(self._get_new_maps())
        self.emitter.emit("servers_loaded_init")
        self.first_iteration = False

    def _update_maps(self) -> None:
        filter_man = self.tv.get_filter_man()
        filter_man.set_unique_maps(self._get_new_maps())
        self.emitter.emit("servers_loaded_init")
        self.first_iteration = False

    def _cleanup_on_success(self) -> None:
        proxy = self._get_proxy_man().get_proxy_model()
        self.tv.set_model(proxy)
        # self.tv.set_model(None)
        # self.tv.set_model(self.to_insert)

        # TODO: make sure control model len is N + 1
        # inserting a row serializes file on disk, updates control model for that tab, and updates model
        # NOTE: when inserting new rows, the entire control model is wiped and rebuilt, then proxy model is swapped in
        # TODO: signals or other approach to deferring map
        # model insertion after thread closes
        # cf. servers_loaded signal

        # TODO: servers_loaded vs servers_reloaded
        self.emitter.emit("servers_loaded", self.enum)

        if self.first_iteration:
            self._update_maps()

    def _cleanup_on_failure(self, show_dialog=True) -> None:
        # TODO: disable map, keyword, and filter widgets if model is None
        # -> signal driven (servers_empty, servers_failed_to_load)

        # NOTE: used by refresh button action
        if not self.preserve_on_fail:
            self.tv.set_model(None)
            filter_man = self.tv.get_filter_man()
            filter_man.set_unique_maps(None)
            # TODO: emit signal to not disable widget sensitivity

        # TODO: distinguish signals, e.g. "servers_failed_to_load", "servers_loaded_empty"
        # customize statusbar and dialog accordingly
        self.emitter.emit("servers_loaded", self.enum)
        # TODO: destroy wait dialog first
        # see threadman.set_cleanup_func(_, destroy_first=True)
        if show_dialog:
            dialog = ExceptionDialog(self.controller, api_warn_msg)
            dialog.run()

    def _push_data(self, data: list) -> None:
        # if data is None:
        #    self.to_insert = None
        # else:

        manager = self._get_proxy_man()
        # TODO: consolidate these methods
        manager.wipe_cache()
        manager.set_control(data)
        manager.filter(FilterMode.INITIAL)
        self.to_insert = manager.get_proxy_model()

        # TODO: abstract for all methods
        self._sort_unique_maps(data)

        self.thread_man.set_cleanup_func(StoredFunc(self._cleanup_on_success))

    def _sort_unique_maps(self, data: list) -> None:
        u_maps = set([row[1] for row in data])
        self._set_new_maps(sorted(u_maps))

    def _set_new_maps(self, maps: list[str]) -> None:
        self.new_maps = maps

    def _get_new_maps(self) -> list[str]:
        return self.new_maps

    def _get_proxy_man(self) -> "ProxyModelManager":
        return self.proxy_man

    @call_on_thread(dialog.filtering)
    def refilter(self, mode: FilterMode) -> None:
        # FIXME: causes two wait dialogs when map selection change signal emits after loading servers
        self.first_iteration = False
        proxy_man = self._get_proxy_man()
        proxy_man.filter(mode)
        # proxy_man.filter(mode, label)
        self.to_insert = proxy_man.get_proxy_model()
        self.thread_man.set_cleanup_func(StoredFunc(self._cleanup_on_success))
