from dataclasses import dataclass
from typing import Self, Sequence, TYPE_CHECKING

from dzgui.const.constants import (
    ERROR,
    WARNING,
)
from dzgui.const.enum import NotebookPage
from dzgui.util.css import add_class
from dzgui.util.keys import is_ctrl_mask
from dzgui.util.localize import number
from dzgui.strings.server_mods import checkmark
from dzgui.strings import preconnect
from dzgui.views.components.frame import HeadingFrame
from dzgui.views.trees.tree_server_mods import ServerModTreeView

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk  # noqa E402


if TYPE_CHECKING:
    from dzgui.managers.connection import Prerequisites
    from dzgui.controllers.mc import Controller
    from dzgui.controllers.emitter import Emitter


@dataclass
class Warnings:
    passworded: bool
    dayz_running: bool
    no_steam: bool
    wrong_version: bool


@dataclass
class Errors:
    no_space: bool
    no_dayz_exp: bool
    no_dayz: bool


class Placeholder(Gtk.Label):
    def __init__(self, text: str) -> None:
        super().__init__(
            label=text,
            halign=Gtk.Align.START,
            valign=Gtk.Align.START,
            margin_start=10,
            margin_bottom=5,
        )


class MaskedTree(Gtk.TreeView):
    def __init__(self, icon: str) -> None:
        super().__init__(headers_visible=False, can_focus=False)

        self.icon = icon
        self.store = Gtk.ListStore(str, str)
        self.set_model(self.store)
        self.get_selection().set_mode(Gtk.SelectionMode.NONE)

        icon_renderer = Gtk.CellRendererPixbuf()
        # NOTE: adjust vertical offset between columns
        icon_renderer.set_property("yalign", 0.6)
        icon_column = Gtk.TreeViewColumn("", icon_renderer)
        icon_column.add_attribute(icon_renderer, "icon-name", 0)
        icon_column.set_fixed_width(50)

        text_renderer = Gtk.CellRendererText()
        text_column = Gtk.TreeViewColumn("", text_renderer, text=1)

        self.append_column(icon_column)
        self.append_column(text_column)
        add_class(self, "masked-tree")

    def append(self, item: Sequence[str]) -> None:
        if len(item) > 1:
            raise ValueError("This method only accepts one item")
        self.store.append([self.icon, item])

    def extend(self, items: list[str]) -> None:
        self.store.clear()
        for item in items:
            self.store.append([self.icon, item])


class PreConnectionAssistant(Gtk.Box):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self.controller = controller

        self.button_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            halign=Gtk.Align.END,
            valign=Gtk.Align.END,
            hexpand=True,
            vexpand=True,
            spacing=10,
        )

        self.controller.register_widget("preconnect", self)

        self.back = Gtk.Button(
            label=preconnect.back, halign=Gtk.Align.END, hexpand=True
        )
        self.ok = Gtk.Button(label=preconnect.update_mods, halign=Gtk.Align.END)
        self.connect_last = Gtk.Button(
            label=preconnect.connect_last,
            halign=Gtk.Align.END,
            tooltip_text=preconnect.connect_last_tooltip,
        )

        self.button_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            valign=Gtk.Align.END,
            vexpand=True,
            spacing=5,
        )
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        for button in self.back, self.ok, self.connect_last:
            box.add(button)
        self.button_box.add(box)

        self.back.connect("clicked", self._on_back_clicked)
        self.ok.connect("clicked", self._on_ok_clicked)
        self.connect_last.connect("clicked", self._on_connect_last_clicked)

        self.title = Gtk.Label(label="")
        add_class(self.title, "preconnect-heading")

        self.tree = ServerModTreeView(self.controller)
        self.mod_count = Gtk.Label(
            label="",
            halign=Gtk.Align.START,
            margin_start=10,
            margin_top=10,
            margin_bottom=10,
        )
        self.progress_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        self.progress_box.add(self.mod_count)

        self.scrolled = Gtk.ScrolledWindow(margin_end=10)
        self.scrolled.add(self.tree)
        self.scrolled.set_size_request(600, 400)

        self.tree_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.tree_box.add(self.scrolled)
        self.tree_box.add(self.progress_box)

        # TODO: strings
        self.mods_placeholder = Placeholder("This server has no mods.")
        self.tree_box.add(self.mods_placeholder)

        self.tree_frame = HeadingFrame.new_with_widget_and_label(
            self.tree_box, preconnect.mods
        )

        # TODO: abstract into components
        self.warning_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.warning_tree = MaskedTree(WARNING)
        # TODO: strings
        self.warning_placeholder = Placeholder("No warnings.")
        self.warning_box.add(self.warning_tree)
        self.warning_box.add(self.warning_placeholder)
        self.warning_frame = HeadingFrame.new_with_widget_and_label(
            self.warning_box, preconnect.warnings
        )

        self.error_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.error_tree = MaskedTree(ERROR)
        # TODO: strings
        self.error_placeholder = Placeholder("No errors.")
        self.error_box.add(self.error_tree)
        self.error_box.add(self.error_placeholder)
        self.error_frame = HeadingFrame.new_with_widget_and_label(
            self.error_box, preconnect.errors
        )

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.box.add(self.title)
        self.box.add(self.tree_frame)
        self.box.add(self.warning_frame)
        self.box.add(self.error_frame)

        self.scrolled_box = Gtk.ScrolledWindow(
            vexpand=True, propagate_natural_height=True
        )
        self.scrolled_box.add(self.box)
        self.add(self.scrolled_box)
        self.add(self.button_box)

        emitter = self.controller.get_emitter()
        emitter.connect("all_mods_synched", self._on_mods_synched)
        self.connect("key-press-event", self._on_keypress)
        self.connect("map", self._on_map)

    def _on_mods_synched(self, emitter: "Emitter") -> None:
        self.tree.mark_mods_synched()

    def _on_map(self, widget: Self) -> None:
        widgets = (
            self.tree_frame,
            self.progress_box,
            self.error_placeholder,
            self.warning_placeholder,
        )
        for child in widgets:
            child.set_visible(True)

        self.ok.set_sensitive(True)
        self.ok.set_label(preconnect.update_mods)

    def _on_keypress(self, widget: Self, event: Gdk.EventKey) -> None:
        if event.keyval == Gdk.KEY_Escape:
            self.back.emit("clicked")
        if is_ctrl_mask(event):
            if event.keyval == Gdk.KEY_u:
                self.ok.emit("clicked")

    def _on_connect_last_clicked(self, button: Gtk.Button) -> None:
        self.controller.update_and_load_to_menu()

    def _on_ok_clicked(self, button: Gtk.Button) -> None:
        self.controller.update_and_connect()

    def _on_back_clicked(self, button: Gtk.Button) -> None:
        self.controller.open_page(NotebookPage.SERVERS)

    def _process_warnings(self, prereqs: "Prerequisites") -> None:
        warnings: list[str] = []
        errors: list[str] = []

        resync_msg = (
            f"If you recently installed {prereqs.build} or moved it to a different drive,\n"
            "restart Steam to allow these changes to synchronize, then try again."
        )

        """Errors"""
        if prereqs.binary_missing:
            errors.append(
                f"Remote server is running the build '{prereqs.build}', but it is not installed.\n{resync_msg}"
            )
        elif prereqs.local_version != prereqs.remote_version:
            errors.append(
                f"Local client version '{prereqs.local_version}' does not match remote version '{prereqs.remote_version}'.\n{resync_msg}"
            )
        if prereqs.required_space > prereqs.available_space:
            required_pretty = number(prereqs.required_space)
            available_pretty = number(prereqs.available_space)
            errors.append(
                f"Need to update {required_pretty} MiB of mods, but installation path only has {available_pretty} MiB."
            )
        if len(prereqs.mods) > 0 and prereqs.game_mode:
            errors.append("Use Desktop Mode to download mods on Steam Deck")

        if prereqs.steam_proc.is_running is False:
            client = prereqs.steam_proc.name
            errors.append(
                f"'{client}' is set as the default Steam client, but it is either not installed or not running."
            )

        """Warnings"""
        if prereqs.passworded:
            warnings.append(
                "Protected: you will be prompted for a password when connecting to this server."
            )
        if prereqs.dayz_running is True:
            warnings.append(
                "It looks like DayZ is already running in the background. Exit DayZ before connecting."
            )

        self.add_warnings(warnings)
        self.add_errors(errors)

        if len(warnings) > 0:
            self.warning_placeholder.set_visible(False)
        if len(errors) > 0:
            self.error_placeholder.set_visible(False)
            self.ok.set_sensitive(False)

    def _hide_mod_area(self) -> None:
        self.scrolled.set_visible(False)
        self.progress_box.set_visible(False)
        self.mods_placeholder.set_visible(True)

    def _show_mod_area(self) -> None:
        self.scrolled.set_visible(True)
        self.progress_box.set_visible(True)
        self.mods_placeholder.set_visible(False)

    def populate(self, prereqs: "Prerequisites") -> None:
        mods = prereqs.mods
        self.tree.populate(mods)
        total_mods = len(mods)

        name = prereqs.name
        self.title.set_text(name)

        if total_mods < 1:
            self._hide_mod_area()
        else:
            self._show_mod_area()
            msg = preconnect.up_to_date
            self.mod_count.set_text(msg)

        if prereqs.required_space != 0:
            pretty = number(prereqs.required_space)
            suffix = f" Need to download {pretty} MiB of mod updates."
            prefix = preconnect.total_mods
            self.mod_count.set_text(f"{prefix}{str(total_mods)}.{suffix}")
        else:
            self.ok.set_label(preconnect.connect)

        if prereqs.is_last_server:
            self.connect_last.show()
        else:
            self.connect_last.hide()

        self._process_warnings(prereqs)
        self.tree.grab_focus()

    def mark_finished(self) -> None:
        self.mod_count.set_label(preconnect.all_updated)
        model = self.tree.get_model()
        if model is None:
            return
        for row in model:
            row[2] = checkmark

    def add_errors(self, errors: list[str]) -> None:
        self.error_tree.extend(errors)

    def add_warnings(self, warnings: list[str]) -> None:
        self.warning_tree.extend(warnings)
