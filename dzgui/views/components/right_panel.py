from typing import TYPE_CHECKING

from dzgui.const.enum import ServerTab
from dzgui.util.clip import copy_clipboard
from dzgui.views.components.buttonbox import ButtonBox
from dzgui.views.components.filter_panel import FilterPanel
from dzgui.views.components.mod_panel import ModSelectionPanel
from dzgui.views.components.buttons import RefreshButton, KeysButton
from dzgui.const.constants import NO_EXPAND, NO_FILL, FILL, NO_PADDING

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib  # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller
    from dzgui.controllers.emitter import Emitter
    from dzgui.controllers.views.trees.tree_servers import ServerTreeView


class RightPanel(Gtk.Box):
    def __init__(self, controller: "Controller"):
        super().__init__(spacing=6, orientation=Gtk.Orientation.VERTICAL)

        self.controller = controller
        self.controller.register_widget("right_panel", self)

        emitter = controller.get_emitter()
        emitter.connect("servers_loaded", self._on_servers_loaded)
        emitter.connect("server_page_changed", self._on_server_page_changed)

        self.button_vbox = ButtonBox(controller)
        self.filters_vbox = FilterPanel(controller)

        self.sel_panel = ModSelectionPanel(controller)

        self.refresh_button = RefreshButton(controller)
        self.keys = KeysButton(controller)

        self.copying = False

        version = self.controller.get_prefs().version
        self.version_label = Gtk.Label(
            label=version,
            hexpand=True,
            vexpand=True,
            halign=Gtk.Align.END,
            valign=Gtk.Align.END,
        )
        eb = Gtk.EventBox(halign=Gtk.Align.END, valign=Gtk.Align.END)
        eb.add(self.version_label)
        eb.connect("button-press-event", self._on_version_clicked)

        for el in self.button_vbox, self.keys, self.filters_vbox, self.refresh_button:
            self.pack_start(el, NO_EXPAND, FILL, NO_PADDING)

        self.pack_start(self.sel_panel, NO_EXPAND, NO_FILL, NO_PADDING)
        self.pack_start(eb, NO_EXPAND, FILL, NO_PADDING)

    def _on_server_page_changed(
        self, emitter: "Emitter", page: "ServerTreeView"
    ) -> None:
        """Initially set filter area to disabled"""
        if page.loaded is True:
            return
        self.filters_vbox.set_sensitive(False)

    def _on_servers_loaded(self, emitter: "Emitter", context: "ServerTab") -> None:
        # TODO: similar logic on notebook page change
        state = self.controller.has_server_model()
        for widget in (self.refresh_button, self.filters_vbox):
            widget.set_sensitive(state)

    def _on_version_clicked(self, widget: Gtk.EventBox, event: Gdk.EventButton) -> None:
        def revert() -> GLib.SOURCE_REMOVE:
            self.copying = False
            self.version_label.set_text(version)
            return GLib.SOURCE_REMOVE

        if self.copying:
            return
        self.copying = True
        version = self.version_label.get_text()
        self.version_label.set_text("Copied!")
        copy_clipboard(version)
        GLib.timeout_add_seconds(0.5, revert)
