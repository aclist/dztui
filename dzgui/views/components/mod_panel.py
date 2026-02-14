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
        super().__init__(margin_start=10, margin_end=10)

        self.enum = enum
        self.set_label(enum.dict["label"])
        self.set_tooltip_text(enum.dict["tooltip"])


class ModSelectionPanel(Gtk.Box):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(spacing=6, orientation=Gtk.Orientation.VERTICAL, margin_top=15)

        self.controller = controller
        emitter = controller.get_emitter()
        emitter.connect("mod_page_toggled", self._on_mod_page_toggled)

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

    def _on_mod_page_toggled(self, emitter: "Emitter", state: bool) -> None:
        self.set_visible(state)

    def after_colorize(self) -> None:
        # TODO: split into signal that touches two widgets,
        # modtreeview and this widget
        self.controller.unselect_all_mods()
        self.swap_sensitive(True)

    def swap_sensitive(self, state: bool) -> None:
        for child in self.stale_panel.get_children():
            if child.enum == ModButton.HIGHLIGHT_STALE:
                child.set_sensitive(not state)
            else:
                child.set_sensitive(state)

    def _on_button_clicked(self, button: EnumeratedModButton) -> None:
        match button.enum:
            case ModButton.SELECT_ALL:
                # TODO: signals
                self.controller.toggle_mod_selection(True)
            case ModButton.UNSELECT_ALL:
                self.controller.toggle_mod_selection(False)
            case ModButton.DELETE_SELECTED:
                self.controller.delete_multiple_mods()

            case ModButton.HIGHLIGHT_STALE:
                self.controller.set_callback(self.after_colorize)
                self.controller.highlight_stale()
            case ModButton.UNHIGHLIGHT_STALE:
                self.controller.uncolorize_mods()
                self.swap_sensitive(False)
            case ModButton.SELECT_STALE:
                self.controller.select_colorized()
