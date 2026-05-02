import gi
import logging
from typing import TYPE_CHECKING

from dzgui.const.constants import APP_NAME
from dzgui.const.enum import ContextMenu, Preferences
from dzgui.util.clip import copy_clipboard
from dzgui.util.open_links import open_workshop_page

from dzgui.views.dialogs.note import NoteDialog
from dzgui.views.trees.tree_mods import ModTreeView
from dzgui.views.trees.tree_log import LogTreeView
from dzgui.views.trees.tree_servers import ServerTreeView


gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GObject  # noqa E402


logger = logging.getLogger(APP_NAME)

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller


class ContextMenuManager:
    def __init__(
        self,
        treeview: LogTreeView | ModTreeView | ServerTreeView,
        controller: "Controller",
    ) -> None:
        self.controller = controller
        self.treeview = treeview

    def process(self, action: ContextMenu) -> None:
        match action:
            # UNTHREADED
            case ContextMenu.ADD_NOTE:
                dialog = NoteDialog(self.controller)
                dialog.run()
            case ContextMenu.COPY_LOG_CLIPBOARD:
                self.copy_log()
            case ContextMenu.COPY_SERVER_IP:
                self.copy_server_ip()
            case ContextMenu.COPY_SERVER_NAME:
                self.copy_server_name()
            case ContextMenu.DELETE_MOD:
                self.controller.delete_mods()
            case ContextMenu.OPEN_WORKSHOP:
                self.open_mod_page()
            case ContextMenu.SET_FAV:
                name = self.treeview.get_value_at_index(0)
                record_str = self.treeview.get_record_string()
                simple = self.treeview.get_simplified_ip()
                self.controller.set_fav(name, record_str, simple)

            # THREADED
            case ContextMenu.ADD_SERVER:
                record = self.treeview.get_record()
                if record is None:
                    return
                self.controller.add_by_record(record)
            case ContextMenu.CONNECT:
                record = self.treeview.get_record()
                if record is None:
                    return
                self.controller.connect_by_record(record)
            case ContextMenu.REFRESH_PLAYERS:
                record = self.treeview.get_record()
                if record is None:
                    return
                self.controller.refresh_players(record)
            case ContextMenu.REMOVE_HISTORY:
                record = self.treeview.get_record()
                if record is None:
                    return
                self.controller.remove_from_history(record)
            case ContextMenu.REMOVE_SERVER:
                record = self.treeview.get_record()
                if record is None:
                    return
                self.controller.remove_by_record(record)
            case ContextMenu.SHOW_DETAILS:
                record = self.treeview.get_record()
                if record is None:
                    return
                self.controller.get_details(record)
            case ContextMenu.SHOW_MODS:
                record = self.treeview.get_record()
                self.controller.get_modlist(record)

    def copy_server_ip(self) -> None:
        if not isinstance(self.treeview, ServerTreeView):
            return
        record = self.treeview.get_simplified_ip()
        copy_clipboard(record)

    def copy_server_name(self) -> None:
        name = self.treeview.get_value_at_index(0)
        if name is None:
            return
        copy_clipboard(name)

    def open_mod_page(self) -> None:
        if not isinstance(self.treeview, ModTreeView):
            return
        mod = self.treeview.get_selected_mod()
        cmd = self.controller.query_config(Preferences.CLIENT)
        open_workshop_page(mod, cmd)

    def copy_log(self) -> None:
        if not isinstance(self.treeview, LogTreeView):
            return
        log = self.treeview.concatenate_rows()
        if log is None:
            return
        copy_clipboard(log)
