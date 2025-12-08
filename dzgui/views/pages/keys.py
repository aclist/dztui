from dzgui.util.strings import navigation, servers, vim, key_header, key_contexts
from dzgui.util.css import add_class

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk # noqa E402


class Keybindings(Gtk.Box):
    """
    Notebook page holding a prearranged grid
    of keybindings and their descriptions
    """
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        label = Gtk.Label(label=key_header)
        add_class(label, "page-heading")
        self.add(label)

        grid = self.build_grid([servers, navigation, vim])
        self.add(grid)

    def build_keys(self, items: list) -> Gtk.Grid:
        grid = Gtk.Grid(row_spacing=10, column_homogeneous=True)
        grid.set_halign(Gtk.Align.START)
        row, col = 1, 0
        w, h = 1, 1
        sep = None
        for item in items:
            for k, v in item.items():
                desc = Gtk.Label(label=k)
                desc.set_halign(Gtk.Align.START)

                key = Gtk.Label(label=v)
                key.set_halign(Gtk.Align.CENTER)

                frame = Gtk.Frame()
                frame.add(key)
                add_class(frame, "frame")

                col = col + 1
                if col > 1:
                    row += 1
                    col = 1
                if not sep:
                    grid.attach(desc, col, row, w, h)
                else:
                    grid.attach_next_to(
                        desc, sep, Gtk.PositionType.BOTTOM, w, h
                    )
                    row += 1
                    sep = None
                grid.attach_next_to(frame, desc, Gtk.PositionType.RIGHT, w, h)

            l_spacer = Gtk.Label(label="")
            r_spacer = Gtk.Label(label="")
            grid.attach(l_spacer, col, row + 1, w, h)
            grid.attach_next_to(
                r_spacer, l_spacer, Gtk.PositionType.RIGHT, w, h
            )
            row += 1
        return grid

    def build_sidebar(self, categories: list) -> Gtk.Grid:
        row, col = 0, 0
        w, h = 1, 1
        sidebar = Gtk.Grid(
            row_homogeneous=True, orientation=Gtk.Orientation.VERTICAL
        )
        for cat in categories:
            label = Gtk.Label(label=cat)
            add_class(label, "left-label")
            row += 1
            sidebar.attach(label, col, row, w, h)
        return sidebar

    def build_grid(self, items: list) -> Gtk.Grid:
        grid = Gtk.Grid(
            row_spacing=20,
            halign=Gtk.Align.CENTER,
            margin_top=20,
            column_spacing=50,
        )

        row, column = 1, 1
        w, h = 1, 1
        sidebar = self.build_sidebar(
            key_contexts
        )
        separator = Gtk.Separator()
        keys_box = self.build_keys(items)

        grid.attach(sidebar, column, row, w, h)
        grid.attach_next_to(separator, sidebar, Gtk.PositionType.RIGHT, w, h)
        grid.attach_next_to(keys_box, separator, Gtk.PositionType.RIGHT, w, h)
        return grid
