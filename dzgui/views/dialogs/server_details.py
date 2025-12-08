import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa

from dzgui.const.enum import Popup

class ServerDetailsDialog(GenericDialog):
    def __init__(self, server_name: str, ip: str, qport: int):
        super().__init__(server_name, Popup.DETAILS)

        dialog_box = self.get_content_area()
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_size_request(800, 700)

        self.ip = ip.split(":")[0]
        self.qport = qport
        self.store = Gtk.ListStore(str, str, Pango.Weight)

        self.view = Gtk.TreeView(
            enable_search=False,
            search_column=-1,
            headers_visible=False,
            fixed_height_mode=True,
        )
        self.view.connect("row-activated", self._on_row_activated)

        for i, column_title in enumerate(["Item", "Details"]):
            renderer = Gtk.CellRendererText(xalign=0)
            if i == 0:
                column = Gtk.TreeViewColumn(
                    column_title, renderer, text=i, weight=2
                )
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

        scrollable_message = Gtk.ScrolledWindow()
        desc = Gtk.Label(label=strings.server_message, valign=Gtk.Align.START)
        css.add_class(desc, "details-heading")
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, halign=Gtk.Align.CENTER
        )
        self.description = Gtk.Label(
            justify=Gtk.Justification.CENTER, wrap=True
        )
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_bottom(10)
        for el in desc, sep, self.description:
            box.add(el)
        scrollable_message.add(box)

        dialog_box.pack_start(scrollable_tree, EXPAND, FILL, 0)
        dialog_box.pack_start(scrollable_message, EXPAND, FILL, 0)

        self.wait_dialog = GenericDialog(strings.details, Popup.WAIT)
        self.wait_dialog.show_all()
        thread = threading.Thread(
            target=self._background, args=(self.wait_dialog, ip, qport)
        )
        thread.start()

    def _on_row_activated(
        self,
        treeview: Gtk.TreeView,
        tree_iter: Gtk.TreeIter,
        col: Gtk.TreeViewColumn,
    ) -> None:
        self.destroy()

    def _load(self) -> None:
        if self.wait_dialog:
            self.wait_dialog.destroy()
        if self.success is False:
            AppNav.window.spawn_dialog(strings.server_error, Popup.NOTIFY)
            return
        self.show_all()
        self.run()
        self.destroy()

    def _background(
        self, dialog: "GenericDialog", ip: str, qport: int
    ) -> None:
        response = Servers.details(self.ip, self.qport)
        if response.success:
            for row in response.data:
                self.store.append(row + [Pango.Weight.BOLD])
            self.view.set_model(self.store)

            text = response.description
            text = format_hyperlinks(text)
            self.description.set_markup(text)

        self.success = response.success
        GLib.idle_add(self._load)
