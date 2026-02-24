from typing import TYPE_CHECKING

import dzgui.api.servers as Servers
from dzgui.managers.thread_man import call_on_thread, StoredFunc, ThreadingManager
from dzgui.util.strings import api_warn_msg, dialog
from dzgui.views.dialogs.generic import ExceptionDialog


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
    def connect_by_ip(self, addr: str) -> None:
        res = Servers.query_by_ip(addr)
        if res is None:
            self.thread_man.set_cleanup_func(StoredFunc(self._connection_failure))
        # TODO: add to history if successful

    def _connection_failure(self) -> None:
        # TODO: more explicit warning message, not necessarily API failure?
        dialog = ExceptionDialog(self.controller, api_warn_msg)
        dialog.run()
