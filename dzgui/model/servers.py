import logging
import threading

from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

import dzgui.api.servers as Servers
from dzgui.const.constants import (
    APPID_DAYZ,
    APPID_DAYZ_EXP,
    APP_NAME,
)
from dzgui.const.enum import FilterMode, Preferences, ServerTab
from dzgui.managers.threading import call_on_thread, StoredFunc, ThreadingManager
from dzgui.strings import dialogs
from dzgui.util.strings import api_warn_msg, dialog
from dzgui.views.dialogs.generic import ExceptionDialog

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402

if TYPE_CHECKING:
    from dzgui.api.servers import A2SInfo, Record
    from dzgui.controllers.mc import Controller
    from dzgui.model.proxy_model import ProxyModelManager
    from dzgui.views.trees.tree_servers import ServerTreeView

logger = logging.getLogger(APP_NAME)
LAN_TIMEOUT = 0.5
API_TIMEOUT = 3


@dataclass
class NewPlayerCount:
    treeiter: Gtk.TreeIter
    players: int
    queue: int


class ServerModelManager:
    def __init__(self, controller: "Controller", tv: "ServerTreeView") -> None:

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
        Load is not called on init. There may be cases where you want to instantiate this class without dumping servers,
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
                self.emitter.emit("lan_page_initialized")
                pass
            case _:
                pass

    def refresh(self) -> None:
        self.preserve_on_fail = True
        self.load()

    @call_on_thread(dialog.fetching)
    def _dump_api(self) -> None:
        # TODO: pass api key a priori in .load() call?
        failure_func = StoredFunc(self._cleanup_on_failure)
        config_man = self.controller.get_config_man()
        key = config_man.lookup(Preferences.STEAM)
        job = Servers.query_api
        params = Servers.params
        servers = []
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(job, key, APPID_DAYZ, param) for param in params]
            for future in as_completed(futures):
                try:
                    # NOTE: faciliates early aborting via sigint
                    # TODO: make this logic available to all dump contexts
                    if self.controller.get_exit_event().is_set():
                        return
                    self.thread_man.increment_dialog()
                    res = future.result(timeout=API_TIMEOUT)
                    if res.status != 200 or not res.parsed:
                        self.thread_man.set_cleanup_func(
                            failure_func, destroy_first=True
                        )
                        return
                    j = res.json
                    if j is not None:
                        servers.extend(j["response"]["servers"])
                except Exception as e:
                    logger.critical(e)
                    self.thread_man.set_cleanup_func(failure_func, destroy_first=True)
                    return

        # NOTE: this step is allowed to fail, since this metadata is incidental
        res = Servers.query_api(key, APPID_DAYZ_EXP, "")
        if res.status == 200 and res.parsed is True:
            j = res.json
            if j is not None:
                servers.extend(j["response"]["servers"])

        parsed = Servers.parse_json(servers)
        self._push_data(parsed)

    @call_on_thread(dialog.scanning, show_cancel=True)
    def dump_lan(self, port: int, early_abort: bool) -> None:
        self.first_iteration = True

        servers = []
        ports = range(1, 256)
        failure_func = StoredFunc(self._cleanup_on_lan_failure)

        event = threading.Event()
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(Servers.test_ip, i, port, event) for i in ports]
            for future in as_completed(futures):
                try:
                    if self.controller.is_cancel_pending():
                        event.set()
                        return
                    res = future.result(timeout=LAN_TIMEOUT)
                    if res is None:
                        continue
                    servers.append(res)
                    if early_abort is True:
                        # NOTE: on first non-empty hit, flag pending threads to close
                        event.set()
                        break
                except Exception as e:
                    logger.critical(e)
                    self.thread_man.set_cleanup_func(failure_func, destroy_first=True)
            if len(servers) == 0:
                self.thread_man.set_cleanup_func(failure_func, destroy_first=True)
                return
        parsed = Servers.parse_json(servers)
        self._push_data(parsed)

    @call_on_thread(dialog.fetching)
    def _dump_ips(self, ips: list[str]) -> None:
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
                # TODO: wrap except
                if self.controller.get_exit_event().is_set():
                    return
                res = future.result(timeout=API_TIMEOUT)
                self.thread_man.increment_dialog()
                # NOTE: failing entries are culled
                if res is None:
                    # TODO: log which servers failed
                    continue
                servers.append(res)
                if len(servers) == 0:
                    self.thread_man.set_cleanup_func(
                        StoredFunc(self._cleanup_on_failure), destroy_first=True
                    )
                    return

        parsed = Servers.parse_json(servers)
        self._push_data(parsed)

    @call_on_thread(dialog.querying)
    def add_by_id(self, _id: str) -> None:
        config_man = self.controller.get_config_man()
        key = config_man.lookup(Preferences.BM)
        res = Servers.query_by_id(int(_id), key)
        self._parse_single_record(res)

    @call_on_thread(dialog.querying)
    def add_by_ip(self, addr: str) -> None:
        res = Servers.query_by_ip(addr)
        self._parse_single_record(res)

    @call_on_thread(dialog.querying)
    def add_by_record(self, record: Servers.Record) -> None:
        # NOTE: rationale: a raw Record as shown in server browser may resolve to a different IP
        res = Servers.query_by_record(record)
        self._parse_single_record(res)

    @call_on_thread(dialog.querying)
    def remove_by_record(self, record: Servers.Record) -> None:
        res = Servers.query_by_record(record)
        self._parse_single_record(res, delete=True)

    def update_history(
        self,
        rows: (
            list[tuple[str, str, str, str, int, int, int, str, int, int, str, bool]]
            | None
        ) = None,
    ) -> None:
        proxy_man = self._get_proxy_man()
        if rows is not None:
            records = rows
        else:
            control_model = proxy_man.get_control()
            records = control_model

        self._sort_unique_maps(records)
        proxy = proxy_man.get_proxy_model()
        self.tv.set_model(proxy)

        self.emitter.emit("servers_loaded", self.enum)

        filter_man = self.tv.get_filter_man()
        maps = self._get_new_maps()
        filter_man.set_unique_maps(maps)
        store = filter_man.get_map_store()

        self.first_iteration = False
        self.emitter.emit("load_maps", store)
        # self.emitter.emit("servers_loaded_init")

    # TODO: dataclass for record rows; check for other dict annotations
    def add_to_history(self, data: tuple[dict[str, Any], "Record"]) -> None:
        row, record = data
        proxy_man = self._get_proxy_man()
        rows = Servers.parse_json([row])
        try:
            proxy_man.append_row_to_history(rows[0])
            self.update_history()
        except Exception:
            self.update_history(rows)

        fqip = Servers.record_to_fqip(record)
        config_man = self.controller.get_config_man()
        config_man.update_history_file(fqip)

    def remove_from_history(self, record: Servers.Record) -> None:
        proxy_man = self._get_proxy_man()
        proxy_man.remove_row_from_control(record)
        self.update_history()

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

    def _parse_single_record(self, response: "A2SInfo", delete: bool = False) -> None:
        self.preserve_on_fail = True
        try:
            row = response.as_row()
        except Exception as e:
            logger.warning(e)
            self.thread_man.set_cleanup_func(
                StoredFunc(self._cleanup_on_failure), destroy_first=True
            )
            return

        # NOTE: expected to only contain one item
        records = Servers.parse_json([row])
        server = records[0]
        if server is None:
            return

        proxy_man = self._get_proxy_man()
        config_man = self.controller.get_config_man()
        fqip = Servers.response_to_fqip(row)
        record = response.get_record()

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
                func = StoredFunc(lambda: self.emitter.emit("already_saved_server"))
                self.thread_man.set_cleanup_func(func)
                return
            config_man.add_saved_server(fqip)

            # FIXME: this is valid if saved servers tab is already open,
            # but not if app was just booted; causes single row to appear prematurely
            if proxy_man.has_control_model() is False:
                proxy_man.push(records)
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
                StoredFunc(self._cleanup_on_failure, False), destroy_first=True
            )
            return
        if len(rows) == 0:
            # TODO: customize statusbar to mention how records are added after connecting
            self.thread_man.set_cleanup_func(
                StoredFunc(self._cleanup_on_failure, False), destroy_first=True
            )
            return
        self.thread_man.set_job_count(len(rows))
        self._dump_ips(rows)

    def _dump_favorites(self) -> None:
        config_man = self.controller.get_config_man()
        ips = config_man.lookup(Preferences.IP_LIST)
        self.thread_man.set_job_count(len(ips))

        if len(ips) == 0:
            # TODO: customize statusbar to mention how records can be added via contextmenu
            self.thread_man.set_cleanup_func(
                StoredFunc(self._cleanup_on_failure, False), destroy_first=True
            )
            return
        self._dump_ips(ips)

    def _cleanup_single_ip(self) -> None:
        proxy = self._get_proxy_man().get_proxy_model()
        self.tv.set_model(proxy)

        if self.controller.get_active_treeview().get_enum() == ServerTab.SAVED:
            self.emitter.emit("servers_loaded", self.enum)

        filter_man = self.tv.get_filter_man()
        # NOTE: maps are set outside of thread because it triggers map changed signals
        maps = self._get_new_maps()
        filter_man.set_unique_maps(maps)
        store = filter_man.get_map_store()
        self.emitter.emit("load_maps", store)

        self.first_iteration = False
        self.emitter.emit("saved_servers_changed")

    def _update_maps(self) -> None:
        filter_man = self.tv.get_filter_man()
        filter_man.set_unique_maps(self._get_new_maps())
        store = filter_man.get_map_store()
        self.emitter.emit("load_maps", store)
        self.first_iteration = False

    def _cleanup_on_success(self) -> None:
        proxy = self.proxy_man.get_proxy_model()
        self.tv.set_model(proxy)
        if self.preserve_on_fail is True:
            self.proxy_man.wipe_cache()

        self.emitter.emit("servers_loaded", self.enum)
        if self.first_iteration:
            self._update_maps()

    def _cleanup_on_lan_failure(self, show_dialog: bool = True) -> None:
        if self.preserve_on_fail is False:
            self.tv.set_model(None)
            filter_man = self.tv.get_filter_man()
            filter_man.set_unique_maps([])

        if show_dialog:
            dialog = ExceptionDialog(self.controller, dialogs.load_error_lan)
            dialog.run()

    def _cleanup_on_failure(self, show_dialog: bool = True) -> None:
        # TODO: disable map, keyword, and filter widgets if model is None
        # signal driven (servers_empty, servers_failed_to_load)

        if self.preserve_on_fail is False:
            self.tv.set_model(None)
            filter_man = self.tv.get_filter_man()
            filter_man.set_unique_maps([])

        # TODO: distinguish signals, e.g. "servers_failed_to_load", "servers_loaded_empty"
        # customize statusbar and dialog accordingly
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
