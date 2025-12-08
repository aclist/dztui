import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa

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

        self.view.connect("row-activated", self._on_row_activated)

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

        wait_dialog = GenericDialog(strings.modlist, Popup.WAIT)
        wait_dialog.show_all()
        thread = threading.Thread(
            target=self._background, args=(wait_dialog, record)
        )
        thread.start()

    # TODO: why are we passing record here?
    def _background(self, dialog: "GenericDialog", record: str) -> None:
        def _load():
            dialog.destroy()
            # TODO: natively implement
            #if data.returncode == 1:
            #    AppNav.window.spawn_dialog(strings.server_error, Popup.NOTIFY)
            #    return
            self.show_all()
            self.set_markup(f"Modlist ({mod_count} mods)")
            self.run()
            self.destroy()

        record = AppNav.treeview.get_record()
        if not record:
            return

        # TODO: thread
        try:
            # TODO: get default_steam_path from config
            modlist = get_server_modlist(record)
            mod_count = self._parse_modlist_rows(modlist)
        except Exception:
            # TODO: needs to pop error dialog
            mod_count = 0
            modlist_store.clear()
        self.view.set_model(modlist_store)
        GLib.idle_add(_load)

    def _parse_modlist_rows(self, rows: list) -> bool | int:
        for row in rows:
            modlist_store.append(row)
        return len(rows)

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
        call_bash_func("open_workshop_page", mod_id)
