import logging
import threading

from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

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


@dataclass
class NewPlayerCount:
    treeiter: Gtk.TreeIter
    players: int
    queue: int


class ServerModelManager:
    def __init__(self, controller: "Controller", tv: Gtk.TreeView) -> None:

        self.tv = tv
        self.enum = tv.get_enum()
        self.controller = controller
        self.emitter = controller.get_emitter()

        self.first_iteration: bool
        self.preserve_on_fail = False
        self.jobs = 1

        self.proxy_man = tv.get_proxy_man()
        self.thread_man = ThreadingManager(self.controller)

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

    @call_on_thread(dialog.querying)
    def add_by_id(self, addr: str) -> None:
        config_man = self.controller.get_config_man()
        key = config_man.lookup(Preferences.BM)
        res = Servers.query_by_id(addr, key)
        self._parse_single_record(res)

    @call_on_thread(dialog.querying)
    def add_by_ip(self, addr: str) -> None:
        res = Servers.query_by_ip(addr)
        self._parse_single_record(res)

    @call_on_thread(dialog.querying)
    def add_by_record(self, record: Servers.Record) -> None:
        """
        Rationale: a Record as shown in server browser may resolve to a different IP
        """
        res = Servers.query_by_record(record)
        self._parse_single_record(res)

    @call_on_thread(dialog.querying)
    def remove_by_record(self, record: Servers.Record) -> None:
        res = Servers.query_by_record(record)
        self._parse_single_record(res, delete=True)

    def remove_from_history(self, record: Servers.Record) -> None:
        """Fully unthreaded, just removes a row"""
        proxy_man = self._get_proxy_man()
        proxy_man.remove_row_from_control(record)
        control_model = proxy_man.get_control()

        config_man = self.controller.get_config_man()
        config_man.update_history_file(control_model)

        self._sort_unique_maps(control_model)
        proxy = proxy_man.get_proxy_model()
        self.tv.set_model(proxy)

        self.emitter.emit("servers_loaded", self.enum)

        filter_man = self.tv.get_filter_man()
        maps = self._get_new_maps()
        filter_man.set_unique_maps(maps)

        self.first_iteration = False
        self.emitter.emit("servers_loaded_init")

    def add_by_str(self, addr: str) -> None:
        if addr.isdigit():
            self.add_by_id(addr)
        else:
            self.add_by_ip(addr)

    @call_on_thread(dialog.querying)
    def update_playercount(
        self, treeiter: Gtk.TreeIter, record: Servers.Record
    ) -> None:
        res = Servers.query_playercount(record)
        if res is None:
            return
        players, queue = res

        self.playercount = NewPlayerCount(treeiter, players, queue)
        self.thread_man.set_cleanup_func(StoredFunc(self._push_playercount))

    def _push_playercount(self) -> None:
        proxy_man = self._get_proxy_man()
        proxy_man.update_playercount(self.playercount)

    def _parse_single_record(self, response: dict, delete: bool = False) -> None:
        self.preserve_on_fail = True
        if response is None:
            self.thread_man.set_cleanup_func(StoredFunc(self._cleanup_on_failure))
            return

        # NOTE: expected to only contain one item
        records = Servers.parse_json([response])
        server = records[0]

        proxy_man = self._get_proxy_man()
        fqip = Servers.response_to_fqip(response)
        record = Servers.response_to_record(response)

        config_man = self.controller.get_config_man()

        # TODO: less convoluted
        if delete:
            # NOTE: abort early if Saved Servers tab was not loaded yet
            config_man.remove_saved_server(fqip)
            if proxy_man.has_control_model() is False:
                self.thread_man.set_cleanup_func(
                    StoredFunc(self._cleanup_when_no_model)
                )
                return
            proxy_man.remove_row_from_control(record)
        else:
            if config_man.is_in_favs(fqip):
                self.emitter.emit("already_saved_server")
                return
            config_man.add_saved_server(fqip)
            if proxy_man.has_control_model() is False:
                self._get_proxy_man().push(records)
            else:
                proxy_man.append_row_to_control(server)

        control_model = proxy_man.get_control()
        self._sort_unique_maps(control_model)
        self.thread_man.set_cleanup_func(StoredFunc(self._cleanup_single_ip))

    def _cleanup_when_no_model(self) -> None:
        self.emitter.emit("saved_servers_changed")

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

        # TODO: animate saved servers tab if we are on other tab
        self.emitter.emit("servers_loaded", self.enum)

        filter_man = self.tv.get_filter_man()
        # NOTE: maps are set outside of thread because it triggers map changed signals
        maps = self._get_new_maps()
        filter_man.set_unique_maps(maps)

        self.first_iteration = False
        self.emitter.emit("servers_loaded_init")
        self.emitter.emit("saved_servers_changed")

    def _update_maps(self) -> None:
        filter_man = self.tv.get_filter_man()
        filter_man.set_unique_maps(self._get_new_maps())
        self.emitter.emit("servers_loaded_init")
        self.first_iteration = False

    def _cleanup_on_success(self) -> None:
        proxy = self._get_proxy_man().get_proxy_model()
        self.tv.set_model(proxy)

        # TODO: servers_loaded vs servers_reloaded
        self.emitter.emit("servers_loaded", self.enum)

        if self.first_iteration:
            self._update_maps()

    def _cleanup_on_failure(self, show_dialog=True) -> None:
        # TODO: disable map, keyword, and filter widgets if model is None
        # -> signal driven (servers_empty, servers_failed_to_load)

        if self.preserve_on_fail is False:
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

    def _push_data(self, data: list[Any]) -> None:
        self._get_proxy_man().push(data)
        self._sort_unique_maps(data)
        self.thread_man.set_cleanup_func(StoredFunc(self._cleanup_on_success))

    def _sort_unique_maps(self, data: list) -> None:
        u_maps = set([row[1] for row in data])
        self._set_new_maps(sorted(u_maps))

    def _set_new_maps(self, maps: list[str]) -> None:
        self.new_maps: list[str] = maps

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
        self.thread_man.set_cleanup_func(StoredFunc(self._cleanup_on_success))
