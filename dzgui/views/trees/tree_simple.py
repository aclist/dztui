from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from dzgui.model.model_factory import FastInsertListStore

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa


class SimpleTree(Gtk.ScrolledWindow):
    """Simple scrollable 1-column tree"""

    def __init__(
        self, model: Union[Gtk.ListStore, "FastInsertListStore"], title: str
    ) -> None:
        super().__init__(
            overlay_scrolling=False,
            propagate_natural_width=True,
            propagate_natural_height=True,
        )

        self.tree = Gtk.TreeView(model=model, enable_search=False)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(title, renderer, text=0)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column.set_resizable(False)
        column.set_sort_column_id(0)
        self.tree.append_column(column)

        self.add(self.tree)

    def get_tree(self) -> Gtk.TreeView:
        return self.tree
