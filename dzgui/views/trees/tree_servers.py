import logging
import multiprocessing
from typing import Any, Self
from warnings import deprecated

from dzgui.views.mixins.context_mixin import ContextMixin
from dzgui.const.enum import ContextMenuGroup, ServerTab
from dzgui.api.servers import Record
from dzgui.model.filtered_model import FilteredModelManager
from dzgui.util.dist import CalcDist
from dzgui.util import strings
from typing import Callable, Literal, TYPE_CHECKING

from dzgui.views.trees.tree_base import TreeView
import dzgui.util._json as JSON  # noqa

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa


logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller
    from dzgui.controllers.emitter import Emitter


class ServerTreeView(ContextMixin, TreeView):
    def __init__(
        self, controller: "Controller", enum: ServerTab, menu: ContextMenuGroup
    ) -> None:
        super().__init__(controller, menu=ContextMenuGroup.SERVER_BROWSER)

        QUEUE_CHECK_DELAY = 200

        self.controller = controller
        self.emitter = controller.get_emitter()
        self.enum = enum

        self.loaded = False
        self.query_func: Callable = None

        self.filter_man = FilteredModelManager(controller)
        model = self.filter_man.get_model()
        self.set_model(model)

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

        # TODO: abstract
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
            # TODO: standardize widths based on column title and longest content
            # TODO: resize col width func causes snapping behavior
            if column_title == "Name":
                column.set_fixed_width(500)
            if column_title == "Map":
                column.set_fixed_width(200)
            if column_title == "IP":
                column.set_fixed_width(240)

            column.connect("notify::fixed-width", self._on_col_width_changed)
            self.append_column(column)

        self.connect("key-press-event", self._on_server_keypress)
        self.connect("generic_row_activated", self._parent_row_activated)
        self.connect("generic_treesel_changed", self._parent_selection_changed)
        self.connect("map", self._on_map)
        self.connect("unmap", self._on_unmap)

        self.connect("key-press-event", self.present_menu)
        self.connect("button-press-event", self.present_menu)

        self.emitter.connect("statusbar_loaded", self._on_distcalc_started)
        self.emitter.connect("distcalc_started", self._on_distcalc_started)
        GLib.timeout_add(QUEUE_CHECK_DELAY, self._check_result_queue)

    def get_filter_man(self) -> FilteredModelManager:
        return self.filter_man

    def shrink_to_fit(self) -> None:
        cols = self.get_columns()
        # TODO: run on only one treeview and propagate results
        # TODO: does not shrink name, map, ip fields to fit
        # TODO: col width changed signal is buggy on current treeview
        for col in cols:
            title = col.get_title()
            if title == "Name":
                continue
            if title == "Map":
                continue
            if title == "IP":
                continue
            label = Gtk.Label(label=title)
            pango = label.get_layout()
            size = pango.get_pixel_size()
            if size.width > 50:
                width = size.width * 1.30
            else:
                width = size.width * 1.65
            col.set_fixed_width(width)

    def get_enum(self) -> None:
        return self.enum

    def _on_map(self, a) -> None:
        if self.get_enum() is ServerTab.LAN:
            # TODO: use emitter here
            self.controller.mediator.grid.conpan.lan.set_visible(True)

    def _on_unmap(self, a) -> None:
        if self.get_enum() is ServerTab.LAN:
            self.controller.mediator.grid.conpan.lan.set_visible(False)

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
        # NOTE: get final width after drag action completes
        GLib.idle_add(self.controller.propagate_column_width, col)

    def terminate_process(self) -> None:
        if self.current_proc and self.current_proc.is_alive():
            self.current_proc.terminate()

    def _on_distcalc_started(self, emitter: "Emitter"):
        record = self.get_record()
        if record is None:
            return

        cache = self.controller.get_dist_cache()

        if record.ip in cache:
            haversine = cache[record.ip]
            self.controller.set_statusbar_dist(haversine, self.get_enum())
            return

        self.current_proc = CalcDist(
            record.ip, self.get_enum(), self.queue, self.controller
        )
        self.current_proc.start()

    def _check_result_queue(self) -> Literal[True]:
        # TODO: delegate to controller
        latest_result = None
        while not self.queue.empty():
            latest_result = self.queue.get()

        cache = self.controller.get_dist_cache()

        if latest_result:
            addr = latest_result[0]
            haversine = latest_result[1]
            if addr not in cache:
                cache[addr] = haversine
            self.controller.set_statusbar_dist(haversine, self.get_enum())
        return True

    def _on_server_keypress(
        self, treeview: Gtk.TreeView, event: Gdk.EventKey
    ) -> bool | None:
        if event.state is Gdk.ModifierType.CONTROL_MASK:
            match event.keyval:
                case Gdk.KEY_r:
                    self.refresh_player_count()
                case Gdk.KEY_f:
                    self.emitter.emit("request_keyword_focus")
                case Gdk.KEY_m:
                    self.emitter.emit("request_maps_focus")
                case Gdk.KEY_i:
                    self.emitter.emit("request_ip_entry_focus")
                case Gdk.KEY_p:
                    if self.enum is ServerTab.LAN:
                        self.emitter.emit("request_lan_entry_focus", self.enum)
                case Gdk.KEY_c:
                    record = self.get_record()
                    self.controller.copy_ip(record)
        else:
            match event.keyval:
                case Gdk.KEY_l | Gdk.KEY_Right:
                    self.emitter.emit("request_button_box_focus")
                case _:
                    self.emitter.emit("check_button_pressed", event.keyval)

        # mod_context_items = [ContextMenu.OPEN_WORKSHOP, ContextMenu.DELETE_MOD]
        # TODO: dynamic menu entries
        # for row in items:
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

        # if event.type is Gdk.EventType.KEY_PRESS and event.keyval is Gdk.KEY_l:
        #     if self.is_selection_empty():
        #         return
        #     self.menu.popup_at_widget(widget, Gdk.Gravity.CENTER, Gdk.Gravity.WEST)
        # else:
        #     self.menu.popup_at_pointer(event)
        # self.menu.select_first(False)

    def _parent_row_activated(
        self, tree: TreeView, path: Gtk.TreePath, column: Gtk.TreeViewColumn
    ) -> None:
        # TODO: process server connection
        # TODO: get record
        print(self.get_value_at_index(0))

    def _parent_selection_changed(self, base_class: TreeView, sel: Gtk.TreeSelection):
        self.terminate_process()
        self.emitter.emit("distcalc_started")

    def get_record_string(self) -> str:
        addr = self.get_value_at_index(7)
        qport = self.get_value_at_index(8)
        return f"{addr}:{qport}"

    def get_record(self) -> Record | None:
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
        if addr is None:
            return
        qport = model[path][8]
        ip = addr.split(":")[0]
        gameport = int(addr.split(":")[1])
        return Record(ip, gameport, qport)

    def is_loaded(self) -> bool:
        return self.loaded

    def set_loaded(self, status: bool) -> None:
        self.loaded = status

    @deprecated("Currently unused")
    def _lazy_load(
        self,
        column: Gtk.TreeViewColumn,
        cell: Gtk.CellRendererText,
        model: Gtk.TreeModel,
        it: Gtk.TreeIter,
        col_index: int,
    ) -> Any:
        """
        Lazy load contents from model manager into visible CellRenderers on demand
        N.B., all row data types will be stringified and must be fetched
        from separate model manager, not internally from TreeView
        cf. Gtk.TreeViewColumn.set_cell_data_func()
        """
        path = model.get_path(it)
        row_index = path.get_indices()[0]
        try:
            start, end = self.get_visible_range()
        except Exception:
            return
        if row_index >= start[0] <= end[0]:
            # NOTE: fetch raw data rows
            real_model = self.filter_man.get_control()
            value = real_model[row_index][col_index]
            cell.set_property("text", str(value))
