import gi
import html
from typing import Self, TYPE_CHECKING

from dzgui.const.constants import CALCULATOR
from dzgui.const.enum import ContextMenuGroup
from dzgui.model.model_factory import ModelFactory
from dzgui.util import css
from dzgui.util.format import format_hyperlinks, format_server_mods
from dzgui.strings import server_mods, dialogs
from dzgui.views.components.buttons import IconTextButton
from dzgui.views.components.box import VBox
from dzgui.views.dialogs.calc import Time, ServerTimeCalculator
from dzgui.views.dialogs.generic import GenericDialog
from dzgui.views.trees.tree_base import TreeView

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Pango  # noqa

if TYPE_CHECKING:
    from dzgui.api.servers import Details
    from dzgui.controllers.mc import Controller


class ServerDialog(GenericDialog):
    def __init__(
        self,
        controller: "Controller",
        title: str,
        secondary: str,
        menu: ContextMenuGroup | None,
    ) -> None:
        super().__init__(
            controller=controller,
            text=title,
            buttons=Gtk.ButtonsType.OK,
            mtype=Gtk.MessageType.INFO,
            secondary=secondary,
        )

        self.set_default_response(Gtk.ResponseType.OK)
        self.set_size_request(800, 700)

        self.view = TreeView(controller, menu)
        self.view.set_fixed_height_mode(True)

        self.connect("response", self._on_response)
        self.view.connect("key-press-event", self._on_keypress)

        self.scrollable_tree = Gtk.ScrolledWindow(vexpand=True)
        self.scrollable_tree.add(self.view)
        self.scrollable_tree.set_size_request(700, 500)

        self.stack = Gtk.Stack()
        self.content_box = VBox(10)
        self.content_box.set_valign(Gtk.Align.FILL)
        self.content_box.add(self.scrollable_tree)

        self.stack.add_named(self.content_box, "METADATA")

        self.content = self.get_content_area()
        self.content.pack_start(self.stack, expand=True, fill=True, padding=0)

    def _on_keypress(self, view: Gtk.TreeView, event: Gdk.EventKey) -> bool:
        # NOTE: ESC normally unfocuses treeview instead of destroying dialog
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()
            return True
        return False

    def _on_response(self, dialog: Self, response: Gtk.ResponseType) -> None:
        self.destroy()


class ServerDetailsDialog(ServerDialog):
    def __init__(self, controller: "Controller", details: "Details"):
        super().__init__(controller, dialogs.server_details, details.name, menu=None)

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

        scrollable_message = Gtk.ScrolledWindow(vexpand=True)
        desc = Gtk.Label(label=dialogs.server_message, valign=Gtk.Align.START)
        css.add_class(desc, "server-subheading")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, halign=Gtk.Align.CENTER)
        self.description = Gtk.Label(justify=Gtk.Justification.CENTER, wrap=True)
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_bottom(10)
        for el in desc, sep, self.description:
            box.add(el)
        scrollable_message.add(box)
        self.content_box.add(scrollable_message)

        for row in details.data:
            self.store.append(row + [Pango.Weight.BOLD])
        self.view.set_model(self.store)
        text = details.description
        text = format_hyperlinks(text)
        self.description.set_markup(html.escape(text))

        calc_button = IconTextButton(CALCULATOR, dialogs.toggle_calc)
        calc_button.connect("clicked", self._on_calc_pressed)
        calc_button.set_halign(Gtk.Align.END)
        calc_button.set_valign(Gtk.Align.START)
        self.content.pack_start(calc_button, False, False, 0)
        self.content.reorder_child(calc_button, 2)

        self.scrollable_tree.set_size_request(700, 250)
        self.calc = ServerTimeCalculator(
            Time(details.gametime, details.day_accel, details.night_accel)
        )
        self.stack.add_named(self.calc, "CALCULATOR")

        self.connect("map", self._on_map)
        self.show_all()

    def _on_map(self, dialog: Self) -> None:
        if widget := self.get_widget_for_response(Gtk.ResponseType.OK):
            widget.grab_focus()

    def _on_calc_pressed(self, button: Gtk.Button) -> None:
        if self.stack.get_visible_child_name() == "METADATA":
            self.stack.set_visible_child_name("CALCULATOR")
        else:
            self.stack.set_visible_child_name("METADATA")

    def _on_row_activated(
        self,
        treeview: Gtk.TreeView,
        tree_iter: Gtk.TreeIter,
        col: Gtk.TreeViewColumn,
    ) -> None:
        self.destroy()


class ServerModDialog(ServerDialog):
    def __init__(
        self,
        controller: "Controller",
        mods: list[list[str]],
    ):

        name = controller.get_server_name()
        super().__init__(
            controller, server_mods.modlist, name, menu=ContextMenuGroup.SERVER_MOD
        )

        self.controller = controller
        self.mod_store = ModelFactory().make_server_mod_store()

        self.view.set_headers_visible(True)
        self.view.set_model(self.mod_store)
        self.view.connect("row-activated", self._on_row_activated)

        # TODO: inherit from ServerModTreeView
        columns = [
            server_mods.mod,
            server_mods.mod_id,
            server_mods.up_to_date,
        ]
        for i, column_title in enumerate(columns):
            renderer = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END)
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            self.view.append_column(column)
            column.set_sort_column_id(i)
            match column_title:
                case server_mods.mod:
                    column.set_fixed_width(350)
                case server_mods.mod_id:
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
