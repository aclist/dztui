import logging
import threading

from queue import Queue
from typing import Any, Self, Union
from warnings import deprecated

from dzgui.api.servers import ping, Record
from dzgui.const.constants import APP_NAME
from dzgui.const.enum import ContextMenu, ContextMenuGroup, ServerTab
from dzgui.managers.filter import FilterManager
from dzgui.model.proxy_model import ProxyModelManager
from dzgui.util import strings
from dzgui.util.dist import CalcDist
from dzgui.util.keys import is_ctrl_mask
from dzgui.views.mixins.context_mixin import ContextMixin
from typing import Literal, TYPE_CHECKING


from dzgui.views.trees.tree_base import TreeView
import dzgui.util._json as JSON  # noqa

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa


logger = logging.getLogger(APP_NAME)

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller
    from dzgui.controllers.emitter import Emitter
    from dzgui.model.model_factory import FastInsertListStore

QUEUE_CHECK_DELAY = 200


class ServerTreeView(ContextMixin, TreeView):  # type: ignore
    def __init__(
        self, controller: "Controller", enum: ServerTab, menu: ContextMenuGroup
    ) -> None:
        super().__init__(controller, menu=menu)

        self.controller = controller
        self.emitter = controller.get_emitter()
        self.enum = enum

        self.loaded = False

        self.filter_man = FilterManager()
        self.proxy_man = ProxyModelManager(self.filter_man)
        model = self.proxy_man.get_proxy_model()
        self.set_model(model)

        self.set_fixed_height_mode(True)
        # NOTE: headers become visible on model load
        self.set_headers_visible(False)

        self.queue_id: int
        self.handler_id: int
        self.queue: Queue = Queue()

        self.seen_cache: list[str] = []

        prefs = self.controller.get_prefs()
        columns = prefs.paths.columns
        try:
            data = JSON.read_json(columns)
            valid_json = True
        except Exception as e:
            logger.critical(e)
            valid_json = False

        width_map = {
            "Name": 800,
            "Map": 300,
            "IP": 240,
        }

        # TODO: abstract column population logic
        # TODO: resize col width func causes snapping behavior
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
                w = width_map[column_title]
                column.set_fixed_width(w)
            if column_title == "Ping":
                column.set_cell_data_func(renderer, self._get_ping)

            column.connect("notify::fixed-width", self._on_col_width_changed)
            self.append_column(column)

        self.connect("button-press-event", self.present_menu)
        self.connect("generic_row_activated", self._parent_row_activated)
        self.connect("generic_treesel_changed", self._parent_selection_changed)
        self.connect("key-press-event", self._on_server_keypress)
        self.connect("key-press-event", self.present_menu)
        self.connect("map", self._on_map)
        self.connect("unmap", self._on_unmap)

        self.set_has_tooltip(True)
        self.connect("query-tooltip", self._on_tooltip)

        # TODO: why is this being saved?
        # self.thread = None

    def _on_tooltip(
        self,
        treeview: Self,
        x: int,
        y: int,
        keyboard_mode: bool,
        tooltip: Gtk.Tooltip,
    ) -> bool:
        """
        Present record data for the hovered row even if it is unfocused
        """
        coords_x, coords_y = treeview.convert_widget_to_bin_window_coords(x, y)
        path = self.get_path_at_pos(coords_x, coords_y)
        if path is None or path[0] is None:
            return False
        model = self.get_model()
        if model is None:
            return False
        tree_iter = model.get_iter(path[0])
        ip = model.get_value(tree_iter, 7)
        qport = model.get_value(tree_iter, 8)
        addr = ip + ":" + str(qport)
        note = self.controller.get_note_by_record(addr)

        if len(note) > 0:
            tooltip.set_text(note)
            self.set_tooltip_row(tooltip, path[0])
            return True
        return False

    def start_queue_checker(self) -> None:
        self.queue_id = GLib.timeout_add(QUEUE_CHECK_DELAY, self._check_result_queue)

    def get_filter_man(self) -> FilterManager:
        return self.filter_man

    def get_proxy_man(self) -> ProxyModelManager:
        return self.proxy_man

    def get_enum(self) -> ServerTab:
        return self.enum

    def _on_map(self, widget: Self) -> None:
        # TODO: disable filter panel if current model is None
        if self.get_enum() is ServerTab.LAN:
            self.emitter.emit("lan_tab_toggled", True)

        store = self.filter_man.get_map_store()

        # FIXME: if model is none, wipe maps
        # distinguish this signal from changing map combo in-situ
        self.emitter.emit("load_maps", store)
        self.handler_id = self.emitter.connect("statusbar_loaded", self.start_distcalc)
        self.start_queue_checker()
        self.start_distcalc()

    def _on_unmap(self, tree: Self) -> None:
        # NOTE: removes queue checker for this tab
        GLib.Source.remove(self.queue_id)
        self.emitter.disconnect(self.handler_id)
        if self.get_enum() is ServerTab.LAN:
            self.emitter.emit("lan_tab_toggled", False)

    def _on_col_width_changed(
        self, col: Gtk.TreeViewColumn, width: GObject.ParamSpecInt
    ) -> None:
        """
        Propagate width change to other tabs
        """
        # NOTE: get final width after drag action completes
        GLib.idle_add(self.controller.propagate_column_width, col)

    def start_distcalc(self, emitter: Union["Emitter", None] = None) -> None:
        self.emitter.emit("distcalc_started")
        record = self.get_record()
        if record is None:
            context = self.get_enum()
            self.emitter.emit("distcalc_ended", None, context)
            return

        cache = self.controller.get_dist_cache()

        if record.ip in cache:
            haversine = cache[record.ip]
            self.controller.set_statusbar_dist(haversine, self.get_enum())
            return

        enum = self.get_enum()
        thread = threading.Thread(
            daemon=True,
            target=CalcDist,
            args=(record.ip, enum, self.queue, self.controller, cache),
        )
        thread.start()

    def _check_result_queue(self) -> Literal[True]:
        latest_result = None
        while not self.queue.empty():
            latest_result = self.queue.get()

        # FIXME: cache is being checked in two passes
        cache = self.controller.get_dist_cache()

        if latest_result:
            addr, haversine, tab = latest_result
            if addr not in cache:
                self.controller.set_dist_cache(addr, haversine)
            # TODO: should be emitting a statusbar signal here instead?
            self.controller.set_statusbar_dist(haversine, self.get_enum())
        return True

    def _on_server_keypress(self, treeview: Gtk.TreeView, event: Gdk.EventKey) -> None:
        if is_ctrl_mask(event):
            match event.keyval:
                case Gdk.KEY_f:
                    self.emitter.emit("request_keyword_focus")
                case Gdk.KEY_m:
                    self.emitter.emit("request_maps_focus")
                case Gdk.KEY_i:
                    self.emitter.emit("request_ip_entry_focus")
                case Gdk.KEY_d:
                    self.emitter.emit("request_default_port_focus")
                case Gdk.KEY_n:
                    if self.enum is ServerTab.LAN:
                        self.emitter.emit("request_custom_port_focus")
                case Gdk.KEY_c:
                    self.controller.menu_action(ContextMenu.COPY_SERVER_IP, self)
                case Gdk.KEY_r:
                    # TODO: unimplemented, needs threading
                    self.controller.menu_action(ContextMenu.REFRESH_PLAYERS, self)
        else:
            match event.keyval:
                case Gdk.KEY_l | Gdk.KEY_Right:
                    self.emitter.emit("request_button_box_focus")
                case _:
                    self.emitter.emit("check_button_pressed", event.keyval)

    def is_modded(self) -> bool:
        select = self.get_selection()
        sels = select.get_selected_rows()
        (model, pathlist) = sels
        path = pathlist[0]
        tree_iter = model.get_iter(path)
        has_mods = model.get_value(tree_iter, 11)
        return bool(has_mods)

    # def get_selected_row(self) -> Gtk.TreeModelRow:
    #    sel = self.get_selection()
    #    sels = sel.get_selected_rows()
    #    print(type(sels[0]))
    #    return sels[0]

    def is_in_favs(self) -> bool:
        record = self.get_record_string()
        if self.controller.get_config_man().is_in_favs(record):
            return True
        return False

    def _parent_row_activated(
        self, tree: TreeView, path: Gtk.TreePath, column: Gtk.TreeViewColumn
    ) -> None:
        record = self.get_record()
        if record is None:
            return
        self.controller.connect_by_record(record)

    def _parent_selection_changed(
        self, base_class: TreeView, sel: Gtk.TreeSelection
    ) -> None:
        if self.loaded is False:
            return
        self.start_distcalc()

    def get_name(self) -> str:
        return str(self.get_value_at_index(0))

    def get_simplified_ip(self) -> str:
        addr = self.get_value_at_index(7)
        qport = self.get_value_at_index(8)
        ip = addr.split(":")[0]
        return f"{ip}:{qport}"

    def get_record_string(self) -> str:
        addr = self.get_value_at_index(7)
        qport = self.get_value_at_index(8)
        return f"{addr}:{qport}"

    def get_record(self) -> Record | None:
        if self.loaded is False:
            return None
        try:
            r = self.get_record_string()
            ip, gameport, qport = r.split(":")
            return Record(ip, int(gameport), int(qport))
        except ValueError as e:
            logger.critical(e)
            return None

    def is_loaded(self) -> bool:
        return self.loaded

    def set_loaded(self, status: bool) -> None:
        self.loaded = status

    def get_model_and_control_model(
        self,
    ) -> tuple[Union[Gtk.TreeModel, None], list[Any]]:
        model = self.get_model()
        control = self.proxy_man.get_control()
        return model, control

    @staticmethod
    def ping_server(
        model: "FastInsertListStore",
        _iter: Gtk.TreeIter,
        ip: str,
        qport: int,
        ping_column: int,
    ) -> None:
        _ping = ping(ip, qport)
        GLib.idle_add(lambda: model.set(_iter, ping_column, _ping))

    def _get_ping(
        self,
        column: Gtk.TreeViewColumn,
        cell: Gtk.CellRendererText,
        model: Gtk.TreeModel,
        _iter: Gtk.TreeIter,
        data: Any,
    ) -> None:

        addr_column = 7
        qport_column = 8
        ping_column = 9

        addr = model.get_value(_iter, addr_column).split(":")
        ip = addr[0]
        gameport = addr[1]
        qport = model.get_value(_iter, qport_column)
        record = f"{addr}:{gameport}:{qport}"

        if record in self.seen_cache:
            return
        self.seen_cache.append(record)

        thread = threading.Thread(
            daemon=True,
            target=self.ping_server,
            args=(model, _iter, ip, qport, ping_column),
        )
        thread.start()

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
            real_model = self.proxy_man.get_control()
            value = real_model[row_index][col_index]
            cell.set_property("text", str(value))
