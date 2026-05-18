import logging
import os
import requests
import shutil
import subprocess
import tarfile

from typing import Literal, TYPE_CHECKING

from dzgui.const.constants import (
    APP_NAME,
    NO_EXPAND,
    NO_FILL,
    FILL,
    NO_PADDING,
    TMP_EXE,
    TMP_PATH,
    TMP_TARBALL,
)
from dzgui.const.enum import ServerTab
from dzgui.managers.threading import call_on_thread, StoredFunc, ThreadingManager
from dzgui.strings import dialogs
from dzgui.util.clip import copy_clipboard
from dzgui.views.components.buttonbox import ButtonBox
from dzgui.views.components.filter_panel import FilterPanel
from dzgui.views.components.mod_panel import ModSelectionPanel
from dzgui.views.components.buttons import IconTextButton, RefreshButton, KeysButton
from dzgui.views.dialogs.generic import ExceptionDialog, QuitDialog

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

        self.thread_man = ThreadingManager(controller)
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
        if update is not None:
            self.update_button.set_halign(Gtk.Align.END)
            self.gutter_box.add(self.update_button)
            self.update_button.connect(
                "clicked", self._on_update_button_clicked, update
            )
        self.gutter_box.add(eb)
        self.pack_start(self.gutter_box, NO_EXPAND, FILL, NO_PADDING)

    def _on_update_success(self) -> None:
        msg = dialogs.update_success
        dialog = QuitDialog(self.controller, msg)
        dialog.run()

    def _on_update_failure(self, msg: str) -> None:
        dialog = ExceptionDialog(self.controller, msg)
        dialog.run()

    @call_on_thread(dialogs.fetching_update)
    def _on_update_button_clicked(self, button: Gtk.Button, url: str) -> None:
        try:
            res = requests.get(url)
            if res.status_code == 200:
                with open(TMP_TARBALL, "wb") as file:
                    file.write(res.content)
                with tarfile.open(TMP_TARBALL) as tar:
                    tar.extractall(TMP_PATH)

                exe_path = os.getenv("PYAPP")
                if exe_path is None:
                    msg = "Failed to find DZGUI launch executable"
                    func = StoredFunc(self._on_update_failure, msg)
                    self.thread_man.set_cleanup_func(func, destroy_first=True)
                    return
                shutil.move(TMP_EXE, exe_path)

                proc = subprocess.run([exe_path, "self", "restore"])
                if proc.returncode == 0:
                    func = StoredFunc(self._on_update_success)
                    self.thread_man.set_cleanup_func(func, destroy_first=True)
                else:
                    msg = dialogs.failed_to_update
                    func = StoredFunc(self._on_update_failure, msg)
                    self.thread_man.set_cleanup_func(func, destroy_first=True)
        except Exception as e:
            func = StoredFunc(self._on_update_failure, e)
            self.thread_man.set_cleanup_func(func, destroy_first=True)
            logger.warning(e)

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
