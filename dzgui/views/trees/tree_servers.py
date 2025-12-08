import logging
import multiprocessing
import subprocess

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa

from dzgui.const.enum import (
    ContextMenu,
    RowType,
    )
from dzgui.const.constants import UDP_PORT
from dzgui.api.servers import Record
from dzgui.util.dist import CalcDist
from dzgui.util.keys import is_navkey
from dzgui.util import strings
from typing import Any, Callable, Literal, TYPE_CHECKING

from dzgui.views.trees.tree_base import TreeView
import dzgui.util._json as JSON  # noqa

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller

# TODO: restore missing methods
# TODO: add multiprocessing queue
# TODO: fix cache

class ServerTreeView(TreeView):
    __gsignals__ = {
        "on_distcalc_started": (GObject.SignalFlags.RUN_FIRST, None, ())
    }
    def __init__(self, controller: "Controller") -> None:
        super().__init__(controller)

        self.controller = controller

        self.set_fixed_height_mode(True)
        self.set_headers_visible(True)

        self.current_proc = None
        self.queue = multiprocessing.Queue()

        prefs = self.controller.get_prefs()
        columns = prefs.paths.columns

        try:
            data = JSON.read_json(columns)
            valid_json = True
        except Exception as e:
            logger.critical(e)
            valid_json = False

        browser_cols = strings.browser_cols
        for i, column_title in enumerate(browser_cols):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            column.set_resizable(True)
            column.set_sort_column_id(i)

            # TODO: use index of column instead of name
            # so literal name won't matter
            # needs conversion logic for old configs
            if valid_json:
                try:
                    saved_size = data["cols"][column_title]
                except KeyError:
                    saved_size = 100
                column.set_fixed_width(saved_size)
                column.set_expand(True)
            else:
                if column_title == "Name":
                    column.set_fixed_width(800)
                if column_title == "Map":
                    column.set_fixed_width(300)

            self.append_column(column)

        # TODO: do not load model on initial init
        # TODO: row_store = self.controller.get_row_store()
        # TODO: test values: see below
        r = Gtk.ListStore(
            str, str, str, str, int, int, int, str, int, int, str, bool
        )
        r.append(["TEST", "a", "a", "a", 0, 0, 0, "a", 0, 0, "a", False])
        self.set_model(r)

        self.connect("on_distcalc_started", self._on_calclat_started)


        self.connect("button-release-event", self._on_server_button_release)
        self.connect("key-press-event", self._on_server_keypress)

        self.connect("generic_row_activated", self._parent_row_activated)
        self.connect("generic_treesel_changed", self._parent_selection_changed)

        GLib.timeout_add(200, self._check_result_queue)

    def terminate_process(self) -> None:
      if self.current_proc and self.current_proc.is_alive():
          self.current_proc.terminate()

    def _on_calclat_started(self, treeview):
        server_tooltip[0] = format_tooltip()
        server_tooltip[1] = server_tooltip[0] + "| Distance: calculating..."
        self.update_statusbar(server_tooltip[1])

    def _check_result_queue(self) -> Literal[True]:
        latest_result = None
        while not self.queue.empty():
            latest_result = self.queue.get()

        if latest_result:
            addr = latest_result[0]
            km = latest_result[1]
            cache[addr] = km
            # TODO: fixme
            self.statusbar.append_distance(km)
        return True

    def _on_server_keypress(
        self, treeview: Gtk.TreeView, event: Gdk.EventKey
    ) -> bool | None:
        # TODO: use mixins
        # CONTROL_MASK + KEY_l
        if event.state is Gdk.ModifierType.CONTROL_MASK:
            match event.keyval:
                case Gdk.KEY_l:
                    self._on_server_button_release(self, event)
                case Gdk.KEY_r:
                    self.refresh_player_count()
                case Gdk.KEY_f:
                    if not AppNav.treeview.is_server_context(AppNav.treeview.view):
                        return True
                    AppNav.right_panel.filters_vbox.keyword_entry.grab_focus()
                case Gdk.KEY_m:
                    # FIXME: should no longer be relevant
                    if AppNav.treeview.view == WindowContext.TABLE_MODS:
                        return True
                    AppNav.right_panel.filters_vbox.maps_entry.grab_focus()
        else:
            keyname = Gdk.keyval_name(event.keyval)
            if keyname.isnumeric() and int(keyname) > 0:
                digit = int(keyname) - 1
                AppNav.grid.right_panel.filters_vbox.toggle_check(digit)
                return False
            match event.keyval:
                case Gdk.KEY_l | Gdk.KEY_Right:
                    #if event.state is Gdk.ModifierType.CONTROL_MASK:
                    #    return
                    self.controller.mediator.right_panel.focus_button_box()
                case Gdk.KEY_0:
                    grid.right_panel.filters_vbox.toggle_check(9)
                case Gdk.KEY_minus:
                    grid.right_panel.filters_vbox.toggle_check(10)
                case Gdk.KEY_backslash:
                    grid.right_panel.filters_vbox.toggle_check(11)
                case _:
                    return False

    def _on_server_button_release(
        self, widget: Gtk.Widget, event: Gdk.EventButton
    ) -> None:
        if event.type is Gdk.EventType.BUTTON_RELEASE and event.button != 3:
            return

        try:
            pathinfo = self.get_path_at_pos(int(event.x), int(event.y))
            if pathinfo is None:
                return
            (path, col, cellx, celly) = pathinfo
            if path is None:
                return
            self.set_cursor(path, col, False)
        except AttributeError:
            pass

        self.menu = Gtk.Menu()
        mod_context_items = [ContextMenu.OPEN_WORKSHOP, ContextMenu.DELETE_MOD]
        # TODO: reimplement server context enums
        server_context_items = {
            RowType.SERVER_BROWSER: [
                ContextMenu.ADD_SERVER,
                ContextMenu.COPY_NAME,
                ContextMenu.COPY_CLIPBOARD,
                ContextMenu.ADD_NOTE,
                ContextMenu.SHOW_MODS,
                ContextMenu.SHOW_DETAILS,
                ContextMenu.REFRESH_PLAYERS,
            ],
            RowType.SCAN_LAN: [
                ContextMenu.COPY_NAME,
                ContextMenu.COPY_CLIPBOARD,
                ContextMenu.ADD_NOTE,
                ContextMenu.SHOW_MODS,
                ContextMenu.SHOW_DETAILS,
                ContextMenu.REFRESH_PLAYERS,
            ],
            RowType.SAVED_SERVERS: [
                ContextMenu.REMOVE_SERVER,
                ContextMenu.COPY_NAME,
                ContextMenu.COPY_CLIPBOARD,
                ContextMenu.ADD_NOTE,
                ContextMenu.SHOW_MODS,
                ContextMenu.SHOW_DETAILS,
                ContextMenu.REFRESH_PLAYERS,
            ],
            RowType.RECENT_SERVERS: [
                ContextMenu.ADD_SERVER,
                ContextMenu.REMOVE_HISTORY,
                ContextMenu.COPY_NAME,
                ContextMenu.ADD_NOTE,
                ContextMenu.COPY_CLIPBOARD,
                ContextMenu.SHOW_MODS,
                ContextMenu.SHOW_DETAILS,
                ContextMenu.REFRESH_PLAYERS,
            ],
        }

        # TODO: how to get current server context
        if self.view == WindowContext.TABLE_MODS:
            items = mod_context_items
        elif self.subpage in server_context_items:
            items = server_context_items[self.subpage]
        else:
            return

        for row in items:
            if row == ContextMenu.ADD_SERVER:
                if self.is_in_favs():
                    row = ContextMenu.REMOVE_SERVER
            item = Gtk.MenuItem(label=row.dict["label"])
            item.type = row
            item.action = row.dict["action"]
            item.connect("activate", self._on_menu_click)
            self.menu.append(item)
            if row == ContextMenu.SHOW_MODS:
                if not self.has_mods():
                    item.set_sensitive(False)
            if row == ContextMenu.ADD_NOTE:
                if self.get_record_string() in notes_cache:
                    item.set_label(strings.edit_note)

        self.menu.show_all()

        if event.type is Gdk.EventType.KEY_PRESS and event.keyval is Gdk.KEY_l:
            if self.is_selection_empty():
                return
            self.menu.popup_at_widget(
                widget, Gdk.Gravity.CENTER, Gdk.Gravity.WEST
            )
        else:
            self.menu.popup_at_pointer(event)
        self.menu.select_first(False)

    def _parent_row_activated(self,
            tree: TreeView,
            path: Gtk.TreePath,
            column: Gtk.TreeViewColumn
        ) -> None:
        # TODO: process server connection
        print(self.get_value_at_index(0))

    def _parent_selection_changed(self, base_class: TreeView, sel: Gtk.TreeSelection):
        print(self.get_value_at_index(0))

        self.terminate_process()
        record = self.get_record()
        print(record)

        # TODO: ?
        if not record:
            grid.statusbar.update_server_meta()
            return

        ip = record.ip

        self.emit("on_distcalc_started")
        self.current_proc = CalcDist(self, record.ip, self.queue, cache)
        self.current_proc.start()

    def get_record_string(self) -> str:
        addr = self.get_value_at_index(7)
        qport = self.get_value_at_index(8)
        return f"{addr}:{qport}"

    def get_record(self) -> dict | None:
        select = self.get_selection()
        sels = select.get_selected_rows()
        (model, pathlist) = sels
        if len(pathlist) < 1:
            return None
        path = pathlist[0]
        model = self.get_model()
        if not model:
            return None
        addr = model[path][7]
        qport = model[path][8]
        ip = addr.split(":")[0]
        gameport = int(addr.split(":")[1])
        return Record(ip, gameport, qport)
