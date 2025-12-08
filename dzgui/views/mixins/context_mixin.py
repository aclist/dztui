import logging
from dzgui.views.trees.tree_base import TreeView
from dzgui.const.enum import Popup, ContextMenu

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa E402


logger = logging.getLogger(__name__)

class ContextMixin(TreeView):
    def present_menu(self,
        widget: Gtk.Widget,
        event: Gdk.EventButton | Gdk.EventKey,
    ) -> None:

        #if self.is_selection_empty():
        #    return

        if event.type is Gdk.EventType.BUTTON_PRESS:
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

        if event.type is Gdk.EventType.KEY_PRESS:
            if event.state is not Gdk.ModifierType.CONTROL_MASK:
                return
            if event.keyval is not Gdk.KEY_l:
                return

        group = self.menu
        self.context_menu = Gtk.Menu()
        for row in group.value:
            item = Gtk.MenuItem(label=row.dict["label"])
            item.connect("activate", self._on_menu_click, row)
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

    def _on_menu_click(self, widget: Gtk.MenuItem, enum: ContextMenu) -> None:
        """
        Local mods page allows multi selection, so ensure that only focused row
        is selected. Used by ContextMenu.OPEN_WORKSHOP and ContextMenu.DELETE_MOD.

        Mod tree right panel supports multi-delete, but context menu enforces
        single deletion on the focused row.

        Debug log page allows multi selection and copy of rows, so special handling
        is used.
        """
        if enum == ContextMenu.COPY_LOG_CLIPBOARD:
            model, records = self.get_selection().get_selected_rows()
            clipboard = self.controller.copy_log(records)
            self.controller.copy_clipboard(clipboard)
        else:
            path = self.get_focused_row_path()
            self.controller.menu_action(enum, path)
