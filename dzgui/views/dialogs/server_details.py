import gi

import dzgui.api.servers as Servers
from dzgui.const.constants import EXPAND, FILL, NO_PADDING
from dzgui.const.enum import Popup
from dzgui.util import css
from dzgui.util import strings
from dzgui.util.format import format_hyperlinks
from dzgui.views.dialogs.generic import GenericDialog

from typing import Self, TYPE_CHECKING

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa

if TYPE_CHECKING:
    from dzgui.api.servers import Details


class ServerDetailsDialog(GenericDialog):
    def __init__(self, controller, details: "Details"):
        super().__init__(
            controller=controller,
            text=details.name,
            buttons=Gtk.ButtonsType.OK,
            mtype=Gtk.MessageType.INFO,
            secondary=strings.server_details,
        )

        dialog_box = self.get_content_area()
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_size_request(800, 700)

        self.store = Gtk.ListStore(str, str, Pango.Weight)

        self.view = Gtk.TreeView(
            enable_search=False,
            search_column=-1,
            headers_visible=False,
            fixed_height_mode=True,
        )
        self.view.connect("row-activated", self._on_row_activated)
        self.view.connect("key-press-event", self._on_keypress)

        for i, column_title in enumerate(["Item", "Details"]):
            renderer = Gtk.CellRendererText(xalign=0)
            if i == 0:
                column = Gtk.TreeViewColumn(column_title, renderer, text=i, weight=2)
            else:
                column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            if i != 2:
                self.view.append_column(column)
            column.set_sort_column_id(i)
            column.set_expand(True)

        scrollable_tree = Gtk.ScrolledWindow()
        scrollable_tree.add(self.view)
        scrollable_tree.set_size_request(700, 200)

        # TODO: center header text
        scrollable_message = Gtk.ScrolledWindow()
        desc = Gtk.Label(label=strings.server_message, valign=Gtk.Align.START)
        css.add_class(desc, "details-heading")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, halign=Gtk.Align.CENTER)
        self.description = Gtk.Label(justify=Gtk.Justification.CENTER, wrap=True)
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_bottom(10)
        for el in desc, sep, self.description:
            box.add(el)
        scrollable_message.add(box)

        dialog_box.pack_start(scrollable_tree, EXPAND, FILL, NO_PADDING)
        dialog_box.pack_start(scrollable_message, EXPAND, FILL, NO_PADDING)

        for row in details.data:
            self.store.append(row + [Pango.Weight.BOLD])
        self.view.set_model(self.store)
        text = details.description
        text = format_hyperlinks(text)
        self.description.set_markup(text)

        self.connect("response", self._on_response)
        self.show_all()

    def _on_keypress(self, view: Gtk.TreeView, event: Gdk.EventKey) -> None:
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()
            return True
        return False

    def _on_response(self, dialog: Self, response: Gtk.ResponseType) -> None:
        self.destroy()

    def _on_row_activated(
        self,
        treeview: Gtk.TreeView,
        tree_iter: Gtk.TreeIter,
        col: Gtk.TreeViewColumn,
    ) -> None:
        self.destroy()
