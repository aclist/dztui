import gi
import textwrap
from typing import TYPE_CHECKING

from dzgui.const.constants import EXPAND, FILL
from dzgui.model.model_factory import ModelFactory
from dzgui.util import strings
from dzgui.views.dialogs.generic import GenericDialog

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa

if TYPE_CHECKING:
    from dzgui.api.servers import Record


class ServerModDialog(GenericDialog):
    def __init__(self, controller, mods: list[str]):

        # TODO: center secondary text
        msg = textwrap.dedent(strings.workshop)
        super().__init__(
            controller=controller,
            text=msg,
            buttons="Gtk.ButtonsType.OK",
            mtype="Gtk.MessageType.INFO",
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
            match column_title:
                case strings.mod:
                    column.set_fixed_width(350)
                case strings.id:
                    column.set_fixed_width(200)
                case _:
                    pass
        dialogBox.pack_end(self.scrollable, EXPAND, FILL, 0)

        mod_count = len(mods)
        self.set_markup(f"Modlist ({mod_count} mods")
        for mod in mods:
            self.mod_store.append(mod)

        self.show_all()

        # TODO: handle response a la details dialog

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
