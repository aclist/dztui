from typing import TYPE_CHECKING

import dzgui.api.servers as Servers

from dzgui.api.mods import get_local_mod_ids
from dzgui.const.enum import Preferences
from dzgui.managers.thread_man import call_on_thread, StoredFunc, ThreadingManager
from dzgui.util.strings import dialog, server_timeout, checkmark
from dzgui.views.dialogs.generic import ExceptionDialog
from dzgui.views.dialogs.servers import ServerDetailsDialog, ServerModDialog

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller


class ConnectionManager:
    def __init__(self, controller: "Controller") -> None:

        self.controller = controller
        self.thread_man = ThreadingManager(parent=controller)

    @call_on_thread(dialog.querying)
    def connect_by_id(self, addr: str, key: str) -> None:
        res = Servers.query_by_id(addr, key)
        if res is None:
            self.thread_man.set_cleanup_func(
                StoredFunc(self._server_timeout), destroy_first=True
            )

        print("DEBUG")
        print(res)

    @call_on_thread(dialog.querying)
    def connect_by_ip(self, addr: str) -> None:
        res = Servers.query_by_ip(addr)
        if res is None:
            self.thread_man.set_cleanup_func(
                StoredFunc(self._server_timeout), destroy_first=True
            )

        print("DEBUG")
        print(res)

    @call_on_thread(dialog.querying)
    def connect_by_record(self, record: Servers.Record) -> None:
        res = Servers.query_by_record(record)
        if res is None:
            self.thread_man.set_cleanup_func(
                StoredFunc(self._server_timeout), destroy_first=True
            )

        # TODO: add to history if successful
        print("DEBUG")
        print(res)

    @call_on_thread(dialog.querying)
    def query_details(self, record: Servers.Record) -> None:
        details = Servers.get_details(record)
        if details.success is False:
            self.thread_man.set_cleanup_func(
                StoredFunc(self._server_timeout), destroy_first=True
            )
            return
        self.thread_man.set_cleanup_func(
            StoredFunc(self._present_details_dialog, details), destroy_first=True
        )

    @call_on_thread(dialog.querying)
    def query_modlist(self, record: Servers.Record) -> None:

        mods = Servers.get_rules(record)
        steam_path = self.controller.query_config(Preferences.DEFAULT)
        local = get_local_mod_ids(steam_path)
        if len(mods) == 0:
            # TODO: separate message for no mods
            # TODO: separate message for actual timeout
            self.thread_man.set_cleanup_func(
                StoredFunc(self._server_timeout), destroy_first=True
            )
            return
        alpha_mods = [
            [
                mod.name,
                str(mod.workshop_id),
                checkmark if mod.workshop_id in local else "",
            ]
            for mod in mods
        ]
        alpha_mods.sort(key=lambda x: x[0])

        self.thread_man.set_cleanup_func(
            StoredFunc(self._present_modlist_dialog, alpha_mods),
            destroy_first=True,
        )

    def _present_modlist_dialog(self, mods: list[str]) -> None:
        dialog = ServerModDialog(self.controller, mods)
        dialog.run()

    def _present_details_dialog(self, details: Servers.Details) -> None:
        dialog = ServerDetailsDialog(self.controller, details)
        dialog.run()

    def _server_timeout(self) -> None:
        dialog = ExceptionDialog(self.controller, server_timeout)
        dialog.run()
