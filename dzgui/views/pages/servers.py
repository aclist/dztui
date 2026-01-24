import logging

from typing import Self, TYPE_CHECKING

from dzgui.const.enum import ContextMenuGroup, ServerTab
from dzgui.views.trees.tree_servers import ServerTreeView
from dzgui.util.strings import server_labels

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib  # noqa E402

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller


class ServerNotebook(Gtk.ScrolledWindow):
    def __init__(self, controller: "Controller"):
        super().__init__()

        self.controller = controller
        self.controller.register_widget("servers", self)
        self.notebook = Gtk.Notebook(show_tabs=True)

        self.browser = ServerTreeView(
            controller, ServerTab.BROWSER, ContextMenuGroup.SERVER_BROWSER
        )
        self.saved = ServerTreeView(controller, ServerTab.SAVED, ContextMenuGroup.SAVED)
        self.recent = ServerTreeView(
            controller, ServerTab.RECENT, ContextMenuGroup.RECENT
        )
        self.lan = ServerTreeView(controller, ServerTab.LAN, ContextMenuGroup.SCAN_LAN)

        self.lan.set_query_func(self.controller.dump_test_2)
        self.browser.set_query_func(self.controller.dump_api)

        tabs = [
            (self.browser, server_labels.browser),
            (self.saved, server_labels.saved),
            (self.recent, server_labels.recent),
            (self.lan, server_labels.lan),
        ]

        for tree, label in tabs:
            scrolled = Gtk.ScrolledWindow()
            scrolled.add(tree)
            self.notebook.append_page(scrolled, Gtk.Label(label=label))

        self.add(self.notebook)
        self.notebook.connect_after("switch-page", self._on_page_changed)
        self.connect("key-press-event", self._on_keypress)
        self.connect("map", self._on_map)
        self.connect("unmap", self._on_unmap)

    def _on_map(self, widget: Self) -> None:
        self.controller.toggle_server_panels(True)

    def _on_unmap(self, widget: Self) -> None:
        self.controller.toggle_server_panels(False)

    def _on_keypress(self, widget: Self, event: Gdk.EventKey) -> None:
        match event.keyval:
            case Gdk.KEY_n:
                self.notebook.next_page()
            case Gdk.KEY_p:
                if event.state is Gdk.ModifierType.CONTROL_MASK:
                    return
                self.notebook.prev_page()
            case _:
                return
        self.get_active_treeview().grab_focus()

    def get_current_tab_text(self) -> None:
        ind = self.notebook.get_current_page()
        child = self.notebook.get_nth_page(ind)
        return self.notebook.get_tab_label_text(child)

    def _on_page_changed(
        self, notebook: Gtk.Notebook, child: Gtk.Widget, index: int
    ) -> None:
        if self.controller.loaded is False:
            return

        label = self.notebook.get_tab_label_text(child)
        if label is None:
            return

        # TODO: strings
        text = label.strip("*")
        self.notebook.set_tab_label_text(child, text)
        # NOTE: spawns a thread
        self.controller.populate_model()

    def get_active_treeview(self) -> ServerTreeView:
        index = self.notebook.get_current_page()
        scrollable = self.notebook.get_nth_page(index)
        treeview = scrollable.get_children()[0]
        return treeview

    def add_notification(self) -> None:
        saved = self.notebook.get_nth_page(1)
        if saved is None:
            return
        text = self.notebook.get_tab_label_text(saved)
        if text is None:
            return
        # TODO: strings
        if "*" in text:
            return
        text += "*"
        self.notebook.set_tab_label_text(saved, text)

    def update_tab_widths(self, col: Gtk.TreeViewColumn) -> None:
        # TODO: may cause pixel offsets when application is maximized
        width = col.get_width()
        title = col.get_title()
        for tab in (self.browser, self.saved, self.recent, self.lan):
            if tab == self.get_active_treeview():
                continue
            for col in tab.get_columns():
                if col.get_title() == title:
                    self.controller.suppress_signal(
                        tab, col, "_on_col_width_changed", True
                    )
                    col.set_fixed_width(width)
                    self.controller.suppress_signal(
                        tab, col, "_on_col_width_changed", False
                    )

    def get_tabs(self) -> tuple:
        return (self.browser, self.saved, self.recent, self.lan)
