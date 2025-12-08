import logging

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa

from dzgui.const.enum import (
    ContextMenuGroup,
    Popup,
    RowType,
    WindowContext,
    )
from dzgui.util.open_links import open_workshop_page
from dzgui.util import strings, localize
from typing import Any

from dzgui.views.trees.tree_base import TreeView

class ModDialog(GenericDialog):
    def __init__(self, record: str):
        # TODO: center secondary text
        msg = strings.workshop
        super().__init__(textwrap.dedent(msg), Popup.MODLIST)

        dialogBox = self.get_content_area()
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_size_request(800, 500)

        self.scrollable = Gtk.ScrolledWindow()
        self.view = Gtk.TreeView(
            enable_search=False, search_column=-1, fixed_height_mode=True
        )
        self.scrollable.add(self.view)
        set_surrounding_margins(self.scrollable, 20)

        self.connect("generic_row_activated", self._on_mod_row_activated)
        self.connect("generic_treesel_changed", self._parent_selection_changed)

        for i, column_title in enumerate(strings.server_mod_cols):
            renderer = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END)
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            self.view.append_column(column)
            column.set_sort_column_id(i)
            match column_title:
                case strings.mod:
                    column.set_fixed_width(350)
                case strings._id:
                    column.set_fixed_width(200)
                case _:
                    pass

        dialogBox.pack_end(self.scrollable, EXPAND, FILL, 0)

        wait_dialog = GenericDialog(strings.modlist, Popup.WAIT)
        wait_dialog.show_all()
        thread = threading.Thread(
            target=self._background, args=(wait_dialog, record)
        )
        thread.start()

    def _on_mod_row_activated(self,
        treeview: Gtk.TreeView,
        path: Gtk.TreePath,
        column: Gtk.TreeViewColumn
    ) -> None:
        uid = self.get_value_at_index(1)
        self.controller.open_mod_page(uid)

    def _parent_selection_changed(self, base_class: TreeView, sel: Gtk.TreeSelection):
        pass

    # TODO: threading shouldn't take place inside this dialog, should be external to controller
    #def _background(self, dialog: "GenericDialog", record: str) -> None:
    #    def _load():
    #        dialog.destroy()
    #        # TODO: natively implemented
    #        #if data.returncode == 1:
    #        #    AppNav.window.spawn_dialog(strings.server_error, Popup.NOTIFY)
    #        #    return
    #        self.show_all()
    #        self.set_markup(f"Modlist ({mod_count} mods)")
    #        self.run()
    #        self.destroy()

    #    record = AppNav.treeview.get_record()
    #    if not record:
    #        return

    #    # TODO: thread
    #    try:
    #        modlist = get_server_modlist(record)
    #        mod_count = self._parse_modlist_rows(modlist)
    #    except Exception:
    #        # TODO: needs to pop error dialog
    #        mod_count = 0
    #        modlist_store.clear()
    #    self.view.set_model(modlist_store)
    #    GLib.idle_add(_load)

    #def _parse_modlist_rows(self, rows: list) -> bool | int:
    #    for row in rows:
    #        modlist_store.append(row)
    #    return len(rows)
