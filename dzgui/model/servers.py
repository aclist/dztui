from datetime import datetime
import logging

from concurrent.futures import wait, as_completed
from concurrent.futures import ThreadPoolExecutor

import dzgui.api.servers as Servers
from dzgui.const.constants import (
    APPID_DAYZ,
    APPID_DAYZ_EXP,
)
from dzgui.const.enum import FilterMode, Preferences, ServerTab
from dzgui.managers.thread_man import call_on_thread, StoredFunc, ThreadingManager
from dzgui.util.strings import dialog
from dzgui.views.dialogs.generic import ExceptionDialog

from typing import Optional, TYPE_CHECKING

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib  # noqa E402


if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller
    from dzgui.controllers.emitter import Emitter
    from dzgui.model.filtered_model import FilteredModelManager

logger = logging.getLogger(__name__)

class ServerModelManager:
    def __init__(self, controller: "Controller", tv: Gtk.TreeView, first_iteration=False) -> None:

        enum = tv.get_enum()
        self.controller = controller
        self.emitter = controller.get_emitter()
        if tv.is_loaded():
            self.emitter.emit("servers_loaded", enum)

        self.tv = tv
        self.jobs = 1

        self.filter_man = tv.get_filter_man()
        self.thread_man = ThreadingManager(parent=controller)

        # TODO: if first iteration, clear filter man control model
        # literal first load: iteration 1
        # refresh: iteration 1 (wipe model)
        # filter: iteration N+1
        self.first_iteration = first_iteration

        match enum:
            case ServerTab.BROWSER:
                # NOTE: extra DAYZ_EXP param
                self.thread_man.set_job_count(len(Servers.params) + 1)
                self._dump_api()
            case ServerTab.SAVED:
                self._dump_favorites()
            case ServerTab.RECENT:
                # TODO: get row count
                self._dump_history()
            case ServerTab.LAN:
                self._dump_lan()

    @call_on_thread(dialog.fetching)
    def _dump_api(self) -> None:
        key = self.controller.query_config(Preferences.STEAM)
        job = Servers.query_api
        params = Servers.params
        servers = []
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(job, key, APPID_DAYZ, param) for param in params]
            for future in as_completed(futures):
                try:
                    self.thread_man.increment_dialog()
                    res = future.result(timeout=3)
                    if res.status != 200 or not res.parsed:
                        self.thread_man.set_cleanup_func(StoredFunc(self._cleanup_on_failure))
                        return
                    j = res.json
                    servers += j["response"]["servers"]
                except Exception as e:
                    # TODO: could store exception in cleanup func
                    logger.critical(e)
                    self.thread_man.set_cleanup_func(StoredFunc(self._cleanup_on_failure))
                    return

        # NOTE: This step is allowed to fail, since this metadata is incidental
        res = Servers.query_api(key, APPID_DAYZ_EXP, "")
        if res.status == 200 and res.parsed is True:
            j = res.json
            servers += j["response"]["servers"]

        # TODO: strings
        #self.thread_man.increment_dialog_with_str("Unpacking servers")
        # TODO: try/except
        parsed = Servers.parse_json(servers)
        self._push_data_success(parsed, FilterMode.INITIAL)

    # TODO: strings
    @call_on_thread("scanning LAN ports")
    def _dump_lan(self, port: int, early_abort: bool) -> None:
        servers = []
        ports = range(1, 256)

        event = threading.Event()
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(Servers.test_ip, i, port, event) for i in ports
            ]
            for future in as_completed(futures):
                try:
                    res = future.result(timeout=0.5)
                    if res is not None and early_abort is True:
                        # NOTE: first non-empty hit, flag pending threads to close
                        event.set()
                        servers.append(res)
                        self.cleanup_func = StoredFunc(self._cleanup_on_success)
                        return
                    if res is None:
                        continue
                    servers.append(res)
                except Exception as e:
                    logger.critical(e)
                    self.cleanup_func = StoredFunc(self._cleanup_on_failure)
            if len(servers) == 0:
                self.cleanup_func = StoredFunc(self._cleanup_on_failure)
                return
        parsed = Servers.parse_json(servers)
        self._push_data_success(parsed, FilterMode.INITIAL)

    # TODO: strings
    @call_on_thread("dumping ips")
    def _dump_ips(self, ips: list[str]) -> None:
        # NOTE: block malformed records (TODO: add github issue no.)
        # TODO: sanitize ip list at config time, drop this
        ips = [ip for ip in ips if len(ip.split(":")) == 3 and ip.split(":")[2] != ""]
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    Servers.query_direct,
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
                    self.cleanup_func = StoredFunc(self._cleanup_on_failure)
                    return

        # NOTE: 1 extra progress bar pass for parsing
        parsed = Servers.parse_json(servers)
        self._push_data_success(parsed, FilterMode.INITIAL)

    def _query_ip_id(self, addr: str) -> None:
        # NOTE: Battlemetrics
        if addr.isdigit():
            # FIXME:
            config = self.controller.get_prefs().paths.config
            resolved = map_id_to_record(config, addr)
            res = Servers.query_direct(resolved.ip, resolved.qport)
        else:
            record = addr.split(":")
            ip, qport = record[0], record[1]
            res = Servers.query_direct(ip, int(qport))
        return res

    # TODO: strings
    @call_on_thread("querying address")
    def _connect_by_id_or_ip(self, addr: str) -> None:
        res = self.query_ip_id(addr)

    @call_on_thread("querying address")
    def _add_by_id_or_ip(self, addr: str) -> None:
        res = self.query_ip_id(addr)
        # TODO: investigate this
        if res is None:
            self.set_cleanup_func(StoredFunc(self._cleanup_on_failure))
            return
        # NOTE: single record insertion
        self.insert_record = Servers.parse_json([res])
        # TODO: add into saved servers file
        # TODO: update saved servers model
        # NOTE: this can be called from other tabs--if current focus is not ServerTab.SAVED, update label only
        # TODO: saved servers might not be loaded yet, in which case should just update local file only
        # TODO: perform simple equality comparison of self.tv.get_enum() == ServerTab.SAVED
        # FIXME: filter man is saved on a per tab basis, so this will mismatch
        self.set_cleanup_func(StoredFunc(self._cleanup_on_insert))

    def _dump_history(self) -> None:
        history = self.controller.get_prefs().paths.history
        # TODO: customize statusbar to mention how records are added after connecting
        try:
            with open(history, "r") as f:
                rows = [row.rstrip("\n") for row in f]
        except OSError:
            self.cleanup_func = StoredFunc(self._cleanup_on_failure, False)
            return
        if len(rows) == 0:
            self.cleanup_func = StoredFunc(self._cleanup_on_failure, False)
            return
        self.thread_man.set_job_count(len(rows))
        self._dump_ips(rows)

    def _dump_favorites(self) -> None:
        ips = self.controller.query_config(Preferences.IP_LIST)
        self.thread_man.set_job_count(len(ips))
        # TODO: customize statusbar to mention how records can be added via contextmenu
        if len(ips) == 0:
            # FIXME: this is not a failure, just a quiet exit with custom statusbar
            # TODO: add custom statusbar parameters
            self.cleanup_func = StoredFunc(self._cleanup_on_failure, False)
            return
        self._dump_ips(ips)

    def _cleanup_on_insert(self) -> None:
        filter_man = self.get_filter_man()
        model = filter_man.get_control()

        # FIXME: this is a single row insertion,
        # but refiltration should occur in thread for consistency/scalability
        model.append(self.insert_record[0])
        proxy = filter_man.filter(FilterMode.INITIAL)

        # TODO: get proxy model out of thread
        proxy = self.get_filter_man().get_proxy_model()
        self.tv.set_model(proxy)

        # TODO: update statusbar
        context = self.tv.get_enum()
        # TODO: adding a row may update available maps
        # TODO: if all filters are already applied, strange behavior may occur
        # -> need to insert and update per current filters
        self.emitter.emit("servers_loaded", context)

    def _cleanup_on_success(self) -> None:
        self.pending_jobs = 1
        self.tv.set_loaded(True)
        self.tv.set_model(self.to_insert)

        # TODO: this will allow history and saved tab to emit signals to statusbar
        # CHORE: test if treeview's sort method inserts row at the correct index
        # inserting a row serializes file on disk, updates control model for that tab, and
        # reapplies filters to ephemeral model; since filters are applied, in-situ insertion might not be necessary
        # TODO: will be inserted out of order
        #self.to_insert.connect("row-inserted", lambda *args: print("row inserted into model"))

        # TODO: signals or other approach to deferring map
        # model insertion after thread closes
        # cf. servers_loaded signal

        # TODO: servers_loaded vs servers_reloaded
        context = self.tv.get_enum()
        self.emitter.emit("servers_loaded", context)

        # CHORE: this is placeholder logic
        if self.first_iteration:
            map_man = self.tv.get_map_man()
            map_man.set_unique_maps(self.new_maps)
            self.emitter.emit("servers_loaded_init")
            self.first_iteration = False
            self.new_maps = None

        self.tv.grab_focus()

    def _cleanup_on_failure(self, show_dialog=True) -> None:
        self.treeview.set_loaded(True)
        map_man = self.treeview.get_map_man()

        # TODO: disable map, keyword, and filter widgets if model is None
        # -> signal driven (servers_empty)
        # TODO: what if refresh action occurred and failed, and the old model is still valid?
        # skip the step below if refresh action failed
        # do not wipe control model in this case
        # e.g. if treeview.is_refresh():
        # revert old model
        # wipe refresh state to False

        self.treeview.set_model(None)
        self.treeview.grab_focus()

        map_man.set_unique_maps(None)
        context = self.treeview.get_enum()

        # TODO: distinguish signals, e.g. "servers_failed_to_load", "servers_loaded_empty"
        # customize statusbar accordingly
        self.emitter.emit("servers_loaded", context)
        if show_dialog:
            dialog = ExceptionDialog(self, strings.api_warn_msg)
            dialog.run()

    # TODO: break into initial dump and refilter modes, can drop filtermode kwarg
    # and stop pushing empty data
    def _push_data_success(self, data: tuple, mode: Optional[FilterMode]) -> None:
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
            # TODO: pre parse maps
            u_maps = set([row[1] for row in data])
            self.new_maps = sorted(u_maps)

        self.thread_man.set_cleanup_func(StoredFunc(self._cleanup_on_success))

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
    #def refilter_model(self, mode: FilterMode, label: Optional[str] = None) -> None:
    #    tv = self.get_active_treeview()
    #    filter_man = tv.get_filter_man()
    #    if filter_man.get_control() is None:
    #        return
    #    self.filter_threaded(filter_man, mode, label)
