from typing import TYPE_CHECKING

from dzgui.const.enum import ModButton
from dzgui.const.constants import NO_EXPAND, FILL, NO_PADDING
from dzgui.util.strings import mod_panel
from dzgui.views.components.labels import BoldLabel

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller, Emitter


class EnumeratedModButton(Gtk.Button):
    def __init__(self, enum: ModButton) -> None:
        super().__init__(margin_start=10, margin_end=10, focus_on_click=False)

        self.enum = enum
        self.set_label(enum.dict["label"])
        self.set_tooltip_text(enum.dict["tooltip"])


class ModSelectionPanel(Gtk.Box):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(spacing=6, orientation=Gtk.Orientation.VERTICAL, margin_top=15)

        self.controller = controller
        emitter = controller.get_emitter()
        emitter.connect("mod_page_toggled", self._on_mod_page_toggled)
        emitter.connect("mods_highlighted", self._on_mods_highlighted)
        emitter.connect("mods_updated", self._on_mods_updated)

        header = BoldLabel(mod_panel.header)

        self.main_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        buttons = (
            ModButton.SELECT_ALL,
            ModButton.UNSELECT_ALL,
            ModButton.DELETE_SELECTED,
        )
        for button in buttons:
            b = EnumeratedModButton(button)
            b.connect("clicked", self._on_button_clicked)
            self.main_panel.pack_start(b, NO_EXPAND, FILL, NO_PADDING)

        self.stale_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        buttons = (
            ModButton.HIGHLIGHT_STALE,
            ModButton.SELECT_STALE,
            ModButton.UNHIGHLIGHT_STALE,
        )
        for button in buttons:
            b = EnumeratedModButton(button)
            b.connect("clicked", self._on_button_clicked)
            if button is not ModButton.HIGHLIGHT_STALE:
                b.set_sensitive(False)
            self.stale_panel.pack_start(b, NO_EXPAND, FILL, NO_PADDING)

        for el in header, self.main_panel, self.stale_panel:
            self.pack_start(el, NO_EXPAND, FILL, NO_PADDING)

        self.connect("map", self._reinit_button)

    def _reinit_button(self, s) -> None:
        for child in self.stale_panel.get_children():
            if child.enum == ModButton.UNHIGHLIGHT_STALE:
                child.set_sensitive(False)
            elif child.enum == ModButton.SELECT_STALE:
                child.set_sensitive(False)
            else:
                child.set_sensitive(True)

    def _on_mods_updated(self, emitter: "Emitter", msg: str, mods: int) -> None:
        if mods < 1:
            self.main_panel.set_sensitive(False)
            self.stale_panel.set_sensitive(False)

    def _on_mods_highlighted(self, emitter: "Emitter") -> None:
        self.swap_sensitive(True)

    def _on_mod_page_toggled(self, emitter: "Emitter", state: bool) -> None:
        self.set_visible(state)

    def swap_sensitive(self, state: bool) -> None:
        for child in self.stale_panel.get_children():
            if child.enum == ModButton.HIGHLIGHT_STALE:
                child.set_sensitive(not state)
            else:
                child.set_sensitive(state)

    def _on_button_clicked(self, button: EnumeratedModButton) -> None:
        match button.enum:
            case ModButton.SELECT_ALL:
                self.controller.toggle_mod_selection(True)
            case ModButton.UNSELECT_ALL:
                self.controller.toggle_mod_selection(False)
            case ModButton.DELETE_SELECTED:
                self.controller.delete_mods()
            case ModButton.HIGHLIGHT_STALE:
                self.controller.highlight_stale()
            case ModButton.UNHIGHLIGHT_STALE:
                self.controller.uncolorize_mods()
                self.swap_sensitive(False)
            case ModButton.SELECT_STALE:
                self.controller.select_colorized()
