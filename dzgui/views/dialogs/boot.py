import sys
from typing import Any, Literal, Self, TYPE_CHECKING

# import time
from enum import Enum


from dzgui.views.mixins.colorscheme import ColorAwareApp

# TODO: import dialog titles
from dzgui.api.mods import remove_stale_signatures as remove_stale
from dzgui.config.ipdb import get_ipdb
from dzgui.const.constants import HEX_GREEN, HEX_RED
from dzgui.init.coords import get_local_coords
from dzgui.init.dayz import is_dayz_installed
from dzgui.init.update import check_updates
from dzgui.const.constants import EXPAND, FILL
from dzgui.managers.threading import call_on_thread, StoredFunc, ThreadingManager
from dzgui.strings import preboot, dialogs
from dzgui.util.format import format_exception
from dzgui.util.strings import dialog_header
from dzgui.util.symlink import rebuild_symlinks
from dzgui.views.components.buttons import ClipboardButton


import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk  # noqa

if TYPE_CHECKING:
    from dzgui.config.xdg import Xdg
    from dzgui.util.ip import Coords


class Success(Enum):
    OK = 1
    FAIL = 2


# TODO: strings for "Running", "Failed", etc.
# TODO: add margins to tree
class BootDialog(ColorAwareApp, Gtk.Dialog):  # type: ignore
    def __init__(self, parent: "BootWindow", xdg: "Xdg", version: str) -> None:
        super().__init__(
            title=dialog_header,
            transient_for=parent,
            modal=True,
        )

        self.parent = parent
        self.set_modal(True)
        self.xdg = xdg
        self.version = version

        self.thread_man = ThreadingManager(None)
        self.set_size_request(700, 500)

        self.store = Gtk.ListStore(str, str, bool, int)

        self.view = Gtk.TreeView(enable_search=False, headers_visible=False)
        self.view.set_model(self.store)

        # TODO: capture sigint in early dialogs
        self.connect("key-press-event", self._on_keypress)

        for i, column_title in enumerate(["Task", "State"]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            column.set_resizable(False)
            column.set_sort_column_id(i)
            column.set_cell_data_func(renderer, self._format_color, func_data=None)
            self.view.append_column(column)
            if i == 0:
                column.set_fixed_width(300)

        self.spinner_renderer = Gtk.CellRendererSpinner()
        self.spinner_renderer.set_property("size", Gtk.IconSize.LARGE_TOOLBAR)
        col_bool = Gtk.TreeViewColumn("Spinner", self.spinner_renderer, active=3)
        col_bool.set_alignment(0.0)
        col_bool.set_cell_data_func(
            self.spinner_renderer, self._set_spinner_vis, func_data=None
        )
        self.view.append_column(col_bool)

        col_int = Gtk.TreeViewColumn("Int", Gtk.CellRendererText(), text=3)
        col_int.set_visible(False)
        self.view.append_column(col_int)

        self.view.get_selection().set_mode(Gtk.SelectionMode.NONE)
        self.connect("delete-event", self._on_delete)

        self.scrollable_tree = Gtk.ScrolledWindow(overlay_scrolling=False)
        self.scrollable_tree.add(self.view)
        self.scrollable_tree.set_size_request(700, 400)

        self.error_box = Gtk.Box(
            halign=Gtk.Align.CENTER,
            orientation=Gtk.Orientation.VERTICAL,
            spacing=20,
            margin_top=30,
            margin_bottom=30,
        )
        self.error_label = Gtk.Label()

        # TODO: abstract class
        self.copy_button = ClipboardButton(None, lambda: self.error_label.get_text())
        self.button_hbox = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.CENTER, spacing=10
        )
        self.exit_button = Gtk.Button(label="Exit", halign=Gtk.Align.CENTER)
        self.exit_button.connect("clicked", lambda _: sys.exit(1))
        self.button_hbox.add(self.copy_button)
        self.button_hbox.add(self.exit_button)

        self.error_box.add(self.error_label)
        self.error_box.add(self.button_hbox)

        self.content = self.get_content_area()
        self.content.pack_start(self.scrollable_tree, EXPAND, FILL, 0)
        self.content.pack_start(self.error_box, EXPAND, FILL, 0)
        self.show_all()

        self.error_box.hide()

        steps = [
            (StoredFunc(is_dayz_installed, self.xdg.config), preboot.dayz, False),
            (StoredFunc(rebuild_symlinks, self.xdg.config), preboot.symlinks, False),
            (
                StoredFunc(remove_stale, self.xdg.config, self.xdg.version),
                preboot.signatures,
                False,
            ),
            (StoredFunc(get_ipdb, self.xdg.ips), preboot.geo, False),
            # TODO: handle IP DB failure and use coords fallback
            (StoredFunc(get_local_coords, self.xdg.ips), preboot.coords, True),
            (StoredFunc(check_updates, self.version), preboot.updates, True),
        ]
        self.results: list[Any] = []
        self.failed = False
        self.steps = iter(steps)

        GLib.timeout_add(100, self.pulse_spinner)

    def _on_keypress(self, widget: Self, event: Gdk.EventKey) -> None:
        if event.keyval == Gdk.KEY_Escape:
            self.exit_button.emit("clicked")

    def pulse_spinner(self) -> Literal[True]:
        for row in self.store:
            if row[2]:
                if row[3] == 150:
                    row[3] = 0
                else:
                    row[3] += 1
        self.spinner_renderer.set_property("pulse", row[3])
        return True

    def run(self) -> None:
        self.iter_step()

    def _on_delete(self, widget: Self, event: Gdk.Event) -> Literal[True]:
        return True

    def iter_step(self) -> None:
        if self.failed:
            self.error_box.show()
            self.error_label.set_text(self.exception)
            return
        try:
            step, label, store_output = next(self.steps)
            self.update_task(label)
            self.background(step, store_output)
        except StopIteration:
            self.parent.set_results(self.results)
            self.destroy()

    @call_on_thread("", show_dialog=False)
    def background(self, func: StoredFunc, store_output: bool) -> None:
        try:
            if store_output:
                res = func.call()
                self.results.append(res)
            else:
                func.call()
            callback = StoredFunc(self.update_status, Success.OK)
            self.thread_man.set_cleanup_func(callback)
        except Exception as e:
            self.failed = True
            self.exception = format_exception(e)
            callback = StoredFunc(self.update_status, Success.FAIL)
            self.thread_man.set_cleanup_func(callback)

    def update_task(self, task: str) -> None:
        self.store.append((task, dialogs.running, True, 0))

    def update_status(self, state: Success) -> None:
        d = {Success.OK: dialogs.ok, Success.FAIL: dialogs.failed}
        msg = d[state]
        self.store[len(self.store) - 1][1] = msg
        self.iter_step()

    def _set_spinner_vis(
        self,
        column: Gtk.TreeViewColumn,
        cell: Gtk.CellRendererSpinner,
        model: Gtk.TreeModel,
        it: Gtk.TreeIter,
        data: Any,
    ) -> None:
        if model[it][1] == dialogs.running:
            cell.set_property("visible", True)
        else:
            cell.set_property("visible", False)

    def _format_color(
        self,
        column: Gtk.TreeViewColumn,
        cell: Gtk.CellRendererText,
        model: Gtk.TreeModel,
        it: Gtk.TreeIter,
        data: Any,
    ) -> None:
        prop = "foreground"
        state = model[it][1]
        if column.get_sort_column_id() != 1:
            return
        if state == dialogs.ok:
            cell.set_property(prop, HEX_GREEN)
        elif state == dialogs.failed:
            cell.set_property(prop, HEX_RED)
        else:
            cell.set_property(prop, None)


class BootWindow(Gtk.Window):
    def __init__(self, xdg: "Xdg", version: str) -> None:
        super().__init__()

        self.results: list[Any] = []

        dialog = BootDialog(self, xdg, version)
        dialog.run()
        dialog.connect("destroy", self._on_destroy)
        Gtk.main()

    def set_results(self, res: list[Any]) -> None:
        self.results = res

    def get_results(self) -> tuple["Coords", str]:
        coords, version_url = self.results
        return (coords, version_url)

    def _on_destroy(self, dialog: BootDialog) -> None:
        Gtk.main_quit()
