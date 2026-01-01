import logging
import multiprocessing
import subprocess

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa

from dzgui.const.enum import (
    ContextMenu,
    ContextMenuGroup,
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

class EnumeratedMenuItem(Gtk.MenuItem):
    def __init__(self, enum: ContextMenu):
        super().__init__(label=enum.dict["label"])
        self.enum = enum


class ServerTreeView(TreeView):
    __gsignals__ = {
        "on_distcalc_started": (GObject.SignalFlags.RUN_FIRST, None, ())
    }
    def __init__(self, controller: "Controller") -> None:
        super().__init__(controller)

        QUEUE_CHECK_DELAY = 200

        self.loaded = False
        self.query_func: Callable = None

        self.menu = Gtk.Menu()
        self.menu.connect("key-press-event", self._on_key)
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

            column.connect("notify::fixed-width", self._on_col_width_changed)
            self.append_column(column)

        self.connect("on_distcalc_started", self._on_calclat_started)
        self.connect("button-release-event", self._on_server_button_release)
        self.connect("key-press-event", self._on_server_keypress)
        self.connect("generic_row_activated", self._parent_row_activated)
        self.connect("generic_treesel_changed", self._parent_selection_changed)

        GLib.timeout_add(QUEUE_CHECK_DELAY, self._check_result_queue)

    def _on_key(self, menu: Gtk.Menu, event: Gdk.EventKey) -> bool | None:
        if not is_navkey(event.keyval):
            return False
        sel = menu.get_selected_item()
        children = menu.get_children()
        for i, child in enumerate(children):
            if sel is child:
                ind = i
                break

        match event.keyval:
            case Gdk.KEY_j:
                if ind == len(children) - 1:
                    return True
                menu.select_item(children[ind+1])
            case Gdk.KEY_k:
                if ind - 1 < 0:
                    return True
                menu.select_item(children[ind-1])
            case Gdk.KEY_g:
                menu.select_item(children[0])
            case Gdk.KEY_G:
                ind = len(children) - 1
                menu.select_item(children[ind])
            case _:
                return False
        return True

    def set_query_func(self, func: Callable) -> None:
        self.query_func = func

    def get_query_func(self) -> Callable | None:
        return self.query_func

    def _on_col_width_changed(
        self, col: Gtk.TreeViewColumn, width: GObject.ParamSpecInt
    ) -> None:
        """
        Propagate width change to other tabs
        """
        title = col.get_title()
        size = col.get_width()

        # NOTE: get final width after drag action completes
        GLib.idle_add(self.controller.propagate_column_width, col)

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
            # FIXME
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
                    self.controller.mediator.grid.right_panel.filters_vbox.keyword_entry.grab_focus()
                case Gdk.KEY_m:
                    self.controller.mediator.grid.right_panel.filters_vbox.maps_entry.grab_focus()
        else:
            match event.keyval:
                case Gdk.KEY_l | Gdk.KEY_Right:
                    self.controller.mediator.right_panel.focus_button_box()
                case _:
                    self.controller.toggle_check(event)

    def set_context_menu(self, items: ContextMenuGroup) -> None:
        # TODO: if debug is on, add raw command
        for item in items.value:
            menu_item = EnumeratedMenuItem(item)
            menu_item.connect("activate", self._on_menu_click)
            self.menu.append(menu_item)
        self.menu.show_all()

    def _on_menu_click(self, item) -> None:
        pass

    def _on_server_button_release(
        self, widget: Gtk.Widget, event: Gdk.EventButton
    ) -> None:
        # TODO: use ContextMixin
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

        mod_context_items = [ContextMenu.OPEN_WORKSHOP, ContextMenu.DELETE_MOD]

        # TODO: dynamic menu entries
        #for row in items:
        #    if row == ContextMenu.ADD_SERVER:
        #        if self.is_in_favs():
        #            row = ContextMenu.REMOVE_SERVER
        #    item = Gtk.MenuItem(label=row.dict["label"])
        #    item.type = row
        #    item.action = row.dict["action"]
        #    self.menu.append(item)
        #    if row == ContextMenu.SHOW_MODS:
        #        if not self.has_mods():
        #            item.set_sensitive(False)
        #    if row == ContextMenu.ADD_NOTE:
        #        if self.get_record_string() in notes_cache:
        #            item.set_label(strings.edit_note)

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
        # TODO: get record
        print(self.get_value_at_index(0))

    def _parent_selection_changed(self, base_class: TreeView, sel: Gtk.TreeSelection):

        self.terminate_process()
        record = self.get_record()

        if record is None:
            return

        #model = self.get_model()
        #if record is None:
        #    self.controller.update_server_status(model)
        #    return

        ip = record.ip
        # TODO
        #self.emit("on_distcalc_started")
        #self.current_proc = CalcDist(self, record.ip, self.queue, cache)
        #self.current_proc.start()

    def get_record_string(self) -> str:
        addr = self.get_value_at_index(7)
        qport = self.get_value_at_index(8)
        return f"{addr}:{qport}"

    def get_record(self) -> dict | None:
        # TODO: delegate to controller
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

    def get_loaded(self) -> bool:
        return self.loaded

    def set_loaded(self, status: bool) -> None:
        self.loaded = status
