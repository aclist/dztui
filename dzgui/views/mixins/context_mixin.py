import logging

from dzgui.const.constants import APP_NAME
from dzgui.const.enum import ContextMenu
from dzgui.util.keys import is_navkey
from dzgui.util.strings import edit_note
from dzgui.views.trees.tree_base import TreeView

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa E402

logger = logging.getLogger(APP_NAME)


class ContextMixin(TreeView):
    def present_menu(
        self,
        widget: Gtk.Widget,
        event: Gdk.EventButton | Gdk.EventKey,
    ) -> bool:

        if self.is_selection_empty():
            return False

        match event.type:
            case Gdk.EventType.BUTTON_PRESS:
                if event.button != 3:
                    return False
                self._process_button_event(event)
            case Gdk.EventType.KEY_PRESS:
                if event.state is not Gdk.ModifierType.CONTROL_MASK:
                    return False
                if event.keyval is not Gdk.KEY_l:
                    return False
            case _:
                return False

        group = self.menu
        self.context_menu = Gtk.Menu()
        self.context_menu.connect("key-press-event", self._on_key)

        for row in group.value:
            item = self._process_dynamic_row(row)
            self.context_menu.append(item)

        self.context_menu.show_all()

        match event.type:
            case Gdk.EventType.KEY_PRESS:
                self.context_menu.popup_at_widget(
                    widget, Gdk.Gravity.CENTER, Gdk.Gravity.WEST
                )
            case Gdk.EventType.BUTTON_PRESS | Gdk.EventType.BUTTON_RELEASE:
                self.context_menu.popup_at_pointer(event)

        self.context_menu.select_first(False)
        return True

    def _process_dynamic_row(self, row: ContextMenu) -> Gtk.MenuItem:
        if row == ContextMenu.ADD_SERVER and self.is_in_favs():  # type: ignore
            row = ContextMenu.REMOVE_SERVER

        item = Gtk.MenuItem(label=row.dict["label"])
        item.connect("activate", self._on_menu_click, row)

        if row == ContextMenu.SHOW_MODS:
            item.set_sensitive(self.is_modded())  # type: ignore

        if row == ContextMenu.ADD_NOTE:
            if self.controller.has_note():
                item.set_label(edit_note)

        return item

    def _process_button_event(self, event: Gdk.EventButton) -> bool:
        try:
            pathinfo = self.get_path_at_pos(int(event.x), int(event.y))
            if pathinfo is None:
                return True
            (path, col, cellx, celly) = pathinfo
            if path is None:
                return True
            selection = self.get_selection()
            model, selected_paths = selection.get_selected_rows()
            if path not in selected_paths:
                for p in selected_paths:
                    selection.unselect_path(p)
                self.set_cursor(path, col, False)
            return True
        except AttributeError:
            return False

    def _on_menu_click(self, widget: Gtk.MenuItem, enum: ContextMenu) -> None:
        self.controller.menu_action(enum, self)

    def _on_key(self, menu: Gtk.Menu, event: Gdk.EventKey) -> bool | None:
        if not is_navkey(event.keyval):
            return False
        menu = self.context_menu
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
                menu.select_item(children[ind + 1])
            case Gdk.KEY_k:
                if ind - 1 < 0:
                    return True
                menu.select_item(children[ind - 1])
            case Gdk.KEY_g:
                menu.select_item(children[0])
            case Gdk.KEY_G:
                ind = len(children) - 1
                menu.select_item(children[ind])
            case _:
                return False
        return True
