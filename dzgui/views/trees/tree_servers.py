import logging
import threading

from queue import Queue
from typing import Any, Optional, Self
from warnings import deprecated

from dzgui.views.mixins.context_mixin import ContextMixin
from dzgui.const.enum import ContextMenu, ContextMenuGroup, ServerTab
from dzgui.api.servers import Record
from dzgui.model.map_model import MapManager
from dzgui.model.filtered_model import FilteredModelManager
from dzgui.util.dist import CalcDist
from dzgui.util import strings
from typing import Literal, TYPE_CHECKING


from dzgui.views.trees.tree_base import TreeView
import dzgui.util._json as JSON  # noqa

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa


logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller
    from dzgui.controllers.emitter import Emitter

QUEUE_CHECK_DELAY = 200


class ServerTreeView(ContextMixin, TreeView):
    def __init__(
        self, controller: "Controller", enum: ServerTab, menu: ContextMenuGroup
    ) -> None:
        super().__init__(controller, menu=ContextMenuGroup.SERVER_BROWSER)

        self.controller = controller
        self.emitter = controller.get_emitter()
        self.enum = enum

        self.loaded = False

        self.filter_man = FilteredModelManager(controller)
        model = self.filter_man.get_proxy_model()
        self.set_model(model)

        # NOTE: each tab context has its own unique maps
        self.map_man = MapManager()

        self.set_fixed_height_mode(True)
        self.set_headers_visible(True)

        self.queue_id: int
        self.handler_id: int
        self.queue = Queue()

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

        # TODO: abstract
        # FIXME: resize col width func causes snapping behavior
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
            # if column_title == "Ping":
            # self.fancy_col = column
            # self.fancy_rend = renderer
            # column.set_cell_data_func(renderer, self._get_ping)
            # if column_title == "Name":
            #    column.set_fixed_width(800)
            # if column_title == "Map":
            #    column.set_fixed_width(300)

            # TODO: standardize widths based on column title and longest content
            # if column_title == "Name":
            #    column.set_fixed_width(500)
            # if column_title == "Map":
            #    column.set_fixed_width(200)
            # if column_title == "IP":
            #    column.set_fixed_width(240)

            column.connect("notify::fixed-width", self._on_col_width_changed)
            self.append_column(column)

        self.connect("button-press-event", self.present_menu)
        self.connect("generic_row_activated", self._parent_row_activated)
        self.connect("generic_treesel_changed", self._parent_selection_changed)
        self.connect("key-press-event", self._on_server_keypress)
        self.connect("key-press-event", self.present_menu)
        self.connect("map", self._on_map)
        self.connect("unmap", self._on_unmap)

        # TODO: why is this being saved?
        self.thread = None

    def start_timeout(self) -> None:
        self.queue_id = GLib.timeout_add(QUEUE_CHECK_DELAY, self._check_result_queue)

    def get_map_man(self) -> MapManager:
        return self.map_man

    def get_filter_man(self) -> FilteredModelManager:
        return self.filter_man

    # def shrink_to_fit(self) -> None:
    #    cols = self.get_columns()
    #    # TODO: run on only one treeview and propagate results
    #    # TODO: does not shrink name, map, ip fields to fit
    #    # TODO: col width changed signal is buggy on current treeview
    #    for col in cols:
    #        title = col.get_title()
    #        if title == "Name":
    #            continue
    #        if title == "Map":
    #            continue
    #        if title == "IP":
    #            continue
    #        label = Gtk.Label(label=title)
    #        pango = label.get_layout()
    #        size = pango.get_pixel_size()
    #        if size.width > 50:
    #            width = size.width * 1.30
    #        else:
    #            width = size.width * 1.65
    #        col.set_fixed_width(width)

    def get_enum(self) -> None:
        return self.enum

    def _on_map(self, widget: Self) -> None:
        # TODO: disable filter panel if current model is None
        if self.get_enum() is ServerTab.LAN:
            self.emitter.emit("lan_tab_toggled", True)

        store = self.map_man.get_map_store()
        # FIXME: if model is none, wipe maps
        self.emitter.emit("load_maps", store)
        self.handler_id = self.emitter.connect("statusbar_loaded", self.start_distcalc)
        self.start_timeout()
        self.start_distcalc()

    def _on_unmap(self, a) -> None:
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

    def start_distcalc(self, emitter: Optional["Emitter"] = None):
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
        self.thread = threading.Thread(
            daemon=True,
            target=CalcDist,
            args=(record.ip, enum, self.queue, self.controller),
        )
        self.thread.start()

    def _check_result_queue(self) -> Literal[True]:
        latest_result = None
        while not self.queue.empty():
            latest_result = self.queue.get()

        # FIXME: cache is being checked in two passes
        cache = self.controller.get_dist_cache()

        if latest_result:
            addr = latest_result[0]
            haversine = latest_result[1]
            if addr not in cache:
                cache[addr] = haversine
            # TODO: should be emitting a statusbar signal here instead?
            self.controller.set_statusbar_dist(haversine, self.get_enum())
        return True

    def _on_server_keypress(
        self, treeview: Gtk.TreeView, event: Gdk.EventKey
    ) -> bool | None:
        if event.state is Gdk.ModifierType.CONTROL_MASK:
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

    # TODO: unimplemented
    # def is_modded(self) -> bool:
    #    select = self.get_selection()
    #    sels = select.get_selected_rows()
    #    (model, pathlist) = sels
    #    path = pathlist[0]
    #    tree_iter = model.get_iter(path)
    #    mods = model.get_value(tree_iter, 11)
    #    return mods

    # TODO: unimplemented
    # def is_in_favs(self) -> bool:
    #    record = self.get_record_string()
    #    proc = call_out("is_in_favs", record)
    #    if proc.returncode == 0:
    #        return True
    #    return False

    def _parent_row_activated(
        self, tree: TreeView, path: Gtk.TreePath, column: Gtk.TreeViewColumn
    ) -> None:
        print(self.get_value_at_index(0))

    def _parent_selection_changed(self, base_class: TreeView, sel: Gtk.TreeSelection):
        if self.loaded is False:
            return
        self.start_distcalc()

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
        r = self.get_record_string()
        try:
            ip, gameport, qport = r.split(":")
            return Record(ip, int(gameport), int(qport))
        except ValueError:
            return None

    def is_loaded(self) -> bool:
        return self.loaded

    def set_loaded(self, status: bool) -> None:
        self.loaded = status

    # @deprecated("currently unused")
    # def _get_ping(
    #    self,
    #    column: Gtk.TreeViewColumn,
    #    cell: Gtk.CellRendererText,
    #    model: Gtk.TreeModel,
    #    it: Gtk.TreeIter,
    #    data: Any,
    # ):
    #    def ping_server(model, _iter, ip: str, qport: int, ping: int):
    #        res = Ping(0, ip, qport, ping)
    #        ping = res.ping
    #        GLib.idle_add(lambda: model.set(_iter, ping_column, ping))

    #    addr_column = 7
    #    qport_column = 8
    #    ping_column = 9

    #    addr = model.get_value(it, addr_column).split(":")[0]
    #    qport = model.get_value(it, qport_column)
    #    ping = model.get_value(it, ping_column)
    #    ip = f"{addr}:{qport}"

    #    if ip in self.seen_cache:
    #        return
    #    self.seen_cache.append(ip)

    #    thread = threading.Thread(
    #        daemon=True,
    #        target=ping_server,
    #        args=(model, it, addr, qport, ping),
    #    )
    #    thread.start()

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
