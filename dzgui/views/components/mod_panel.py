from typing import Self, TYPE_CHECKING

from dzgui.const.enum import ModButton
from dzgui.const.constants import NO_EXPAND, FILL, NO_PADDING
from dzgui.util.strings import mod_panel
from dzgui.views.components.labels import BoldLabel

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller
    from dzgui.controllers.emitter import Emitter


class EnumeratedModButton(Gtk.Button):
    def __init__(self, enum: ModButton) -> None:
        super().__init__(margin_start=10, margin_end=10, focus_on_click=False)

        self.enum = enum
        self.set_label(enum.dict["label"])
        self.set_tooltip_text(enum.dict["tooltip"])


class ModPanelButton(EnumeratedModButton):
    def __init__(self, enum: ModButton) -> None:
        super().__init__(enum=enum)

        self.enum = enum
        if enum is not ModButton.HIGHLIGHT_STALE:
            self.set_sensitive(False)


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
            ModButton.UNSUB_SELECTED,
        )
        for button in buttons:
            b = EnumeratedModButton(button)
            b.connect("clicked", self._on_button_clicked)
            self.main_panel.pack_start(b, NO_EXPAND, FILL, NO_PADDING)

        self.stale_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.highlight_stale_button = ModPanelButton(ModButton.HIGHLIGHT_STALE)
        self.unhighlight_stale_button = ModPanelButton(ModButton.UNHIGHLIGHT_STALE)
        self.select_stale_button = ModPanelButton(ModButton.SELECT_STALE)

        for b in (
            self.highlight_stale_button,
            self.unhighlight_stale_button,
            self.select_stale_button,
        ):
            self.stale_panel.pack_start(b, NO_EXPAND, FILL, NO_PADDING)
            b.connect("clicked", self._on_button_clicked)

        for el in header, self.main_panel, self.stale_panel:
            self.pack_start(el, NO_EXPAND, FILL, NO_PADDING)

        self.connect("map", self._reinit_button)

    def _reinit_button(self, widget: Self) -> None:
        self.unhighlight_stale_button.set_sensitive(False)
        self.select_stale_button.set_sensitive(False)
        self.highlight_stale_button.set_sensitive(True)

    def _on_mods_updated(self, emitter: "Emitter", msg: str, mods: int) -> None:
        self._toggle_panel_sensitivity(mods)

    def _toggle_panel_sensitivity(self, mods: int) -> None:
        state = bool(mods)
        for el in self.main_panel, self.stale_panel:
            el.set_sensitive(state)

    def _on_mods_highlighted(self, emitter: "Emitter") -> None:
        self.swap_sensitive(True)

    def _on_mod_page_toggled(self, emitter: "Emitter", state: bool, mods: int) -> None:
        self._toggle_panel_sensitivity(mods)
        self.set_visible(state)

    def swap_sensitive(self, state: bool) -> None:
        self.highlight_stale_button.set_sensitive(not state)
        self.unhighlight_stale_button.set_sensitive(state)
        self.select_stale_button.set_sensitive(state)

    def _on_button_clicked(self, button: EnumeratedModButton) -> None:
        match button.enum:
            case ModButton.SELECT_ALL:
                self.controller.toggle_mod_selection(True)
            case ModButton.UNSELECT_ALL:
                self.controller.toggle_mod_selection(False)
            case ModButton.UNSUB_SELECTED:
                self.controller.unsub_mods()
            case ModButton.HIGHLIGHT_STALE:
                self.controller.highlight_stale()
            case ModButton.UNHIGHLIGHT_STALE:
                self.controller.uncolorize_mods()
                self.swap_sensitive(False)
            case ModButton.SELECT_STALE:
                self.controller.select_colorized()
