import logging
import os

from typing import Literal, TYPE_CHECKING

from dzgui.const.constants import (
    APP_NAME,
    NO_EXPAND,
    NO_FILL,
    FILL,
    NO_PADDING,
)
from dzgui.const.enum import ServerTab
from dzgui.managers.update import UpdateManager
from dzgui.util.clip import copy_clipboard
from dzgui.views.components.buttonbox import ButtonBox
from dzgui.views.components.filter_panel import FilterPanel
from dzgui.views.components.mod_panel import ModSelectionPanel
from dzgui.views.components.buttons import IconTextButton, RefreshButton, KeysButton

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib  # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller
    from dzgui.controllers.emitter import Emitter
    from dzgui.views.trees.tree_servers import ServerTreeView

logger = logging.getLogger(APP_NAME)


class RightPanel(Gtk.Box):
    def __init__(self, controller: "Controller"):
        super().__init__(spacing=6, orientation=Gtk.Orientation.VERTICAL)

        self.controller = controller
        self.controller.register_widget("right_panel", self)

        emitter = controller.get_emitter()
        emitter.connect("servers_loaded", self._on_servers_loaded)
        emitter.connect("server_page_changed", self._on_server_page_changed)
        emitter.connect("lan_page_initialized", self._on_lan_page_init)

        self.button_vbox = ButtonBox(controller)
        self.filters_vbox = FilterPanel(controller)

        self.sel_panel = ModSelectionPanel(controller)

        self.refresh_button = RefreshButton(controller)
        self.keys = KeysButton(controller)

        self.copying = False

        prefs = self.controller.get_prefs()
        version = prefs.version
        update = prefs.latest_release

        self.version_label = Gtk.Label(
            label=version,
            hexpand=True,
            vexpand=True,
            halign=Gtk.Align.END,
            valign=Gtk.Align.END,
            # TODO: strings
            tooltip_text="Click to copy to clipboard",
        )
        eb = Gtk.EventBox(halign=Gtk.Align.END, valign=Gtk.Align.END)
        eb.add(self.version_label)
        eb.connect("button-press-event", self._on_version_clicked)

        for el in self.button_vbox, self.keys, self.filters_vbox, self.refresh_button:
            self.pack_start(el, NO_EXPAND, FILL, NO_PADDING)

        self.pack_start(self.sel_panel, NO_EXPAND, NO_FILL, NO_PADDING)

        self.update_button = IconTextButton(
            "dialog-information-symbolic", label="Updates available"
        )

        self.gutter_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            halign=Gtk.Align.END,
            valign=Gtk.Align.END,
            spacing=10,
        )
        exe_path = os.getenv("PYAPP")
        if exe_path and update is not None:
            self.update_button.set_halign(Gtk.Align.END)
            self.gutter_box.add(self.update_button)
            self.update_button.connect(
                "clicked", self._on_update_button_clicked, exe_path, update
            )
        self.gutter_box.add(eb)
        self.pack_start(self.gutter_box, NO_EXPAND, FILL, NO_PADDING)

    def _on_update_button_clicked(
        self, button: Gtk.Button, exe_path: str, url: str
    ) -> None:
        UpdateManager(self.controller).update_version(exe_path, url)

    def _on_server_page_changed(
        self, emitter: "Emitter", page: "ServerTreeView"
    ) -> None:
        """Initially set filter area to disabled"""
        if page.loaded is True:
            return
        self.filters_vbox.set_sensitive(False)
        # TODO: unless it is lan page
        #self.refresh_button.set_sensitive(False)

    def _on_lan_page_init(self, emitter: "Emitter") -> None:
        self.filters_vbox.set_sensitive(False)

    def _on_servers_loaded(self, emitter: "Emitter", context: "ServerTab") -> None:
        # TODO: similar logic on notebook page change
        state = self.controller.has_server_model()
        self.filters_vbox.set_sensitive(state)

    def _on_version_clicked(self, widget: Gtk.EventBox, event: Gdk.EventButton) -> None:
        def revert() -> Literal[False]:
            self.copying = False
            self.version_label.set_text(version)
            return False

        if self.copying:
            return
        self.copying = True
        version = self.version_label.get_text()
        self.version_label.set_text("Copied!")
        copy_clipboard(version)
        GLib.timeout_add_seconds(1, revert)
