import gi
import logging
from typing import TYPE_CHECKING

from dzgui.const.constants import APP_NAME
from dzgui.const.enum import ContextMenu, Preferences
from dzgui.util.clip import copy_clipboard
from dzgui.util.open_links import open_workshop_page

from dzgui.views.dialogs.note import NoteDialog
from dzgui.views.trees.tree_mods import ModTreeView, OfflineModTreeView
from dzgui.views.trees.tree_log import LogTreeView
from dzgui.views.trees.tree_servers import ServerTreeView
from dzgui.views.trees.tree_server_mods import ServerModTreeView


gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GObject  # noqa E402


logger = logging.getLogger(APP_NAME)

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller


class ContextMenuManager:
    def __init__(
        self,
        treeview: (
            LogTreeView
            | ModTreeView
            | ServerTreeView
            | ServerModTreeView
            | OfflineModTreeView
        ),
        controller: "Controller",
    ) -> None:
        self.controller = controller
        self.treeview = treeview

    def process(self, action: ContextMenu) -> None:
        if isinstance(self.treeview, ServerTreeView):
            record = self.treeview.get_record()
            if record is None:
                return

            match action:
                # UNTHREADED
                case ContextMenu.ADD_NOTE:
                    dialog = NoteDialog(self.controller)
                    dialog.run()
                case ContextMenu.COPY_SERVER_IP:
                    self.copy_server_ip()
                case ContextMenu.COPY_SERVER_NAME:
                    self.copy_server_name()
                case ContextMenu.SET_FAV:
                    name = self.treeview.get_value_at_index(0)
                    # NOTE: fully qualified ip
                    fqip = self.treeview.get_record_string()
                    # NOTE: short ip for display purposes
                    simple = self.treeview.get_simplified_ip()
                    self.controller.set_fav(name, fqip, simple)

                # THREADED
                case ContextMenu.ADD_SERVER:
                    self.controller.add_by_record(record)
                case ContextMenu.CONNECT:
                    self.controller.connect_by_record(record)
                case ContextMenu.REFRESH_PLAYERS:
                    self.controller.refresh_players(record)
                case ContextMenu.REMOVE_HISTORY:
                    self.controller.remove_from_history(record)
                case ContextMenu.REMOVE_SERVER:
                    self.controller.remove_by_record(record)
                case ContextMenu.SHOW_DETAILS:
                    self.controller.get_details(record)
                case ContextMenu.SHOW_MODS:
                    self.controller.get_modlist(record)

        if isinstance(self.treeview, (ModTreeView, OfflineModTreeView)):
            match action:
                case ContextMenu.DELETE_MOD:
                    self.controller.delete_mods(self.treeview)
                case ContextMenu.OPEN_WORKSHOP:
                    self.open_mod_page()

        if isinstance(self.treeview, LogTreeView):
            match action:
                case ContextMenu.COPY_LOG_CLIPBOARD:
                    self.copy_log()

        if isinstance(self.treeview, ServerModTreeView):
            match action:
                case ContextMenu.OPEN_WORKSHOP:
                    self.open_mod_page()

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
        if not hasattr(self.treeview, "get_selected_mod"):
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
