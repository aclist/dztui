import logging

from typing import TYPE_CHECKING

from dzgui.const.constants import SEPARATOR
from dzgui.util.keys import is_navkey
from dzgui.views.mixins.cursor_mixin import CursorMixin

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller
    from dzgui.const.enum import ContextMenuGroup


class TreeView(CursorMixin, Gtk.TreeView):  # type: ignore
    def __init__(
        self, controller: "Controller", menu: "ContextMenuGroup" = None
    ) -> None:
        super().__init__(
            enable_search=False,
            search_column=-1,
            headers_visible=False,
        )

        self.menu = menu
        self.controller = controller
        self.sel_blocked = False
        self.set_row_separator_func(self._separate)

        self.selected_row = self.get_selection()
        self.selected_row.set_mode(Gtk.SelectionMode.SINGLE)
        self.selected_row.connect("changed", self._on_tree_selection_changed)
        self.connect("row-activated", self._on_row_activated)
        self.connect("key-press-event", self._on_keypress)
        self.connect("key-release-event", self._on_key_release)

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(Gtk.TreeSelection,))
    def generic_treesel_changed(self, selection: Gtk.TreeSelection) -> None:
        pass

    @GObject.Signal(
        flags=GObject.SignalFlags.RUN_LAST, arg_types=(Gtk.TreePath, Gtk.TreeViewColumn)
    )
    def generic_row_activated(
        self, path: Gtk.TreePath, column: Gtk.TreeViewColumn
    ) -> None:
        pass

    def _separate(self, model: Gtk.ListStore, iter_: Gtk.TreeIter) -> bool:
        if model[iter_][0] == SEPARATOR:
            return True
        return False

    def get_current_iter(self) -> Gtk.TreeIter | None:
        it = self.get_selection().get_selected()[1]
        return it

    def get_focused_row_iter(self) -> Gtk.TreeIter:
        path = self.get_focused_row_path()
        model = self.get_model()
        return model.get_iter(path)

    def get_focused_row_path(self) -> Gtk.TreePath:
        return self.get_cursor().path

    def get_focused_row_index(self) -> int:
        return self.get_cursor().path[0]

    def get_selected_records(self) -> list:
        sel = self.get_selection()
        model, rows = sel.get_selected_rows()
        return [model[row] for row in rows]

    def _on_keypress(self, treeview: Gtk.TreeView, event: Gdk.EventKey) -> None:

        if is_navkey(event.keyval):
            # TODO: if model is None
            if len(self.get_model()) < 2:
                return
            if self.sel_blocked is False:
                self.controller.suppress_signal(
                    self,
                    self.selected_row,
                    "_on_tree_selection_changed",
                    True,
                )
            self._vim_nav(event)
        return

    def _on_key_release(self, treeview: Gtk.TreeView, event: Gdk.EventKey) -> None:
        # TODO: explain this better
        """
        Suppresses spamming on keydown
        """
        # TODO: multisel
        # if event.keyval is Gdk.KEY_space:
        #    it = self.get_focused_row_iter()
        #    self.get_selection().select_iter(it)
        #    return True

        if len(self.get_model()) < 2:
            return

        if is_navkey(event.keyval):
            if self.sel_blocked is True:
                self.controller.suppress_signal(
                    self.controller.mediator.treeview,
                    self.controller.mediator.treeview.selected_row,
                    "_on_tree_selection_changed",
                    False,
                )
            selection = self.get_selection()
            self._on_tree_selection_changed(selection)

    def _on_tree_selection_changed(self, selection: Gtk.TreeSelection) -> None:
        self.emit("generic_treesel_changed", selection)

    def toggle_selection(self, state: bool) -> None:
        for i, row in enumerate(self.get_model()):  # type: ignore
            path = Gtk.TreePath.new_from_indices([i])
            if state:
                self.get_selection().select_path(path)
            else:
                self.get_selection().unselect_path(path)

    def focus_first_row(self) -> None:
        self.set_cursor(0)

    def get_value_at_index(self, index: int) -> str:
        select = self.get_selection()
        sels = select.get_selected_rows()
        (model, pathlist) = sels
        if len(pathlist) < 1:
            return ""
        path = pathlist[0]
        tree_iter = model.get_iter(path)
        value = model.get_value(tree_iter, index)
        return value

    def get_name(self) -> str:
        name = self.get_value_at_index(0)
        return name

    def select_first_row(self):
        sel = self.get_selection()
        self._on_tree_selection_changed(sel)

    def get_mpath(self) -> Gtk.TreePath | None:
        select = self.get_selection()
        sels = select.get_selected_rows()
        (model, pathlist) = sels
        if len(pathlist) < 1:
            return None
        path = pathlist[0]
        return path

    # @signal_emission
    def _on_row_activated(
        self,
        treeview: Gtk.TreeView,
        path: Gtk.TreePath,
        col: Gtk.TreeViewColumn,
    ) -> None:
        self.emit("generic_row_activated", path, col)

    def is_selection_empty(self) -> bool:
        # TODO: reduce duplicated methods
        sel = self.get_selection()
        sels = sel.get_selected_rows()
        (model, pathlist) = sels
        if len(pathlist) < 1:
            return True
        return False

    def get_selected_row(self) -> Gtk.TreeModelRow | None:
        ind = self.get_selected_row_index()
        model = self.get_model()
        if model is None:
            return None
        row = model[ind]
        return row
