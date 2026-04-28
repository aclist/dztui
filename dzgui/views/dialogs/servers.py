from typing import Self, TYPE_CHECKING

from dzgui.const.constants import EXPAND, FILL, NO_PADDING
from dzgui.model.model_factory import ModelFactory
from dzgui.util import css
from dzgui.util import strings
from dzgui.util.format import format_hyperlinks, format_server_mods
from dzgui.views.dialogs.generic import GenericDialog
from dzgui.views.trees.tree_base import TreeView

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa

if TYPE_CHECKING:
    from dzgui.api.servers import Details
    from dzgui.controllers.mc import Controller


class ServerDialog(GenericDialog):
    def __init__(self, controller: "Controller", title: str, secondary: str):
        super().__init__(
            controller=controller,
            text=title,
            buttons=Gtk.ButtonsType.OK,
            mtype=Gtk.MessageType.INFO,
            secondary=secondary,
        )

        self.set_default_response(Gtk.ResponseType.OK)
        self.set_size_request(800, 700)

        self.view = TreeView(controller)
        self.view.set_fixed_height_mode(True)

        self.connect("response", self._on_response)
        self.view.connect("key-press-event", self._on_keypress)

        self.scrollable_tree = Gtk.ScrolledWindow()
        self.scrollable_tree.add(self.view)
        self.scrollable_tree.set_size_request(700, 400)

        self.content = self.get_content_area()
        self.content.pack_start(self.scrollable_tree, EXPAND, FILL, 0)

    # def pack(self, widget: Gtk.Widget) -> None:
    #     self.content.pack_start(widget, EXPAND, FILL, NO_PADDING)

    def _on_keypress(self, view: Gtk.TreeView, event: Gdk.EventKey) -> bool:
        # NOTE: ESC normally unfocuses treeview instead of destroying dialog
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()
            return True
        return False

    def _on_response(self, dialog: Self, response: Gtk.ResponseType) -> None:
        self.destroy()


class ServerDetailsDialog(ServerDialog):
    def __init__(self, controller, details: "Details"):
        name = controller.get_server_name()
        super().__init__(controller, strings.server_details, name)

        self.store = Gtk.ListStore(str, str, Pango.Weight)
        self.view.connect("row-activated", self._on_row_activated)

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

        # TODO: make "Server message" text boldface
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

        self.pack(scrollable_message)

        for row in details.data:
            self.store.append(row + [Pango.Weight.BOLD])
        self.view.set_model(self.store)
        text = details.description
        text = format_hyperlinks(text)
        self.description.set_markup(text)

        self.show_all()

    def _on_row_activated(
        self,
        treeview: Gtk.TreeView,
        tree_iter: Gtk.TreeIter,
        col: Gtk.TreeViewColumn,
    ) -> None:
        self.destroy()


class ServerModDialog(ServerDialog):
    def __init__(self, controller, mods: list[str]):

        name = controller.get_server_name()
        super().__init__(controller, strings.modlist, name)

        self.controller = controller
        self.mod_store = ModelFactory().make_server_mod_store()

        self.view.set_headers_visible(True)
        self.view.set_model(self.mod_store)
        self.view.connect("row-activated", self._on_row_activated)

        for i, column_title in enumerate(strings.server_mod_cols):
            renderer = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END)
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            self.view.append_column(column)
            column.set_sort_column_id(i)
            # FIXME: do not recycle generic string vars
            match column_title:
                case strings.mod:
                    column.set_fixed_width(350)
                case strings._id:
                    column.set_fixed_width(200)
                case _:
                    pass

        mod_count = len(mods)
        self._set_footer(mod_count)

        for mod in mods:
            self.mod_store.append(mod)

        self.show_all()

    def _set_footer(self, mods: int) -> None:
        footer = Gtk.Label(
            valign=Gtk.Align.START, justify=Gtk.Justification.CENTER, wrap=True
        )
        footer_text = format_server_mods(mods)
        footer.set_text(footer_text)
        self.pack(footer)

    def _on_row_activated(
        self,
        treeview: Gtk.TreeView,
        path: Gtk.TreePath,
        col: Gtk.TreeViewColumn,
    ) -> None:
        mod = self.view.get_value_at_index(1)
        self.controller.open_workshop_page(mod)
