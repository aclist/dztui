import textwrap
from typing import Self, TYPE_CHECKING

from dzgui.const.constants import EXPAND, FILL, NO_PADDING
from dzgui.model.model_factory import ModelFactory
from dzgui.util import css
from dzgui.util import strings
from dzgui.util.format import format_hyperlinks
from dzgui.views.dialogs.generic import GenericDialog

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa

if TYPE_CHECKING:
    from dzgui.api.servers import Details


# TODO: make a more generic base class
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

    def __init__(self, controller, details: "Details"):
        super().__init__(
            controller=controller,
            text=details.name,
            buttons=Gtk.ButtonsType.OK,
            mtype=Gtk.MessageType.INFO,
            secondary=strings.server_details,
        )


# TODO: data type is dayzquery.DayzMod


class ServerModDialog(GenericDialog):
    def __init__(self, controller, mods: list[str]):

        # TODO: center secondary text
        msg = textwrap.dedent(strings.workshop)
        super().__init__(
            controller=controller,
            text=msg,
            buttons=Gtk.ButtonsType.OK,
            mtype=Gtk.MessageType.INFO,
            secondary="",
        )

        self.mod_store = ModelFactory().make_server_mod_store()

        dialogBox = self.get_content_area()
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_size_request(800, 700)

        self.scrollable = Gtk.ScrolledWindow()
        self.view = Gtk.TreeView(
            enable_search=False, search_column=-1, fixed_height_mode=True
        )
        self.scrollable.add(self.view)

        # set_surrounding_margins(self.scrollable, 20)
        self.connect("response", self._on_response)
        self.view.connect("row-activated", self._on_row_activated)
        self.view.set_model(self.mod_store)

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
        dialogBox.pack_end(self.scrollable, EXPAND, FILL, 0)

        mod_count = len(mods)
        self.set_markup(f"Modlist ({mod_count} mods)")
        for mod in mods:
            self.mod_store.append(mod)

        self.show_all()

    def _on_response(self, dialog: Self, response: Gtk.ResponseType) -> None:
        self.destroy()

    def _on_keypress(self, view: Gtk.TreeView, event: Gdk.EventKey) -> None:
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()
            return True
        return False

    def _on_row_activated(
        self,
        treeview: Gtk.TreeView,
        tree_iter: Gtk.TreeIter,
        col: Gtk.TreeViewColumn,
    ) -> None:
        select = treeview.get_selection()
        sels = select.get_selected_rows()
        (model, pathlist) = sels
        if len(pathlist) < 1:
            return
        path = pathlist[0]
        tree_iter = model.get_iter(path)
        mod_id = model.get_value(tree_iter, 1)
        print(mod_id)
        # call_bash_func("open_workshop_page", mod_id)
