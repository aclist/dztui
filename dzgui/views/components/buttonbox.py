import logging
from typing import TYPE_CHECKING

from dzgui.const.constants import APP_NAME, NO_EXPAND, NO_FILL, NO_PADDING
from dzgui.const.enum import ButtonType

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk  # noqa E402

logger = logging.getLogger(APP_NAME)

if TYPE_CHECKING:
    from dzgui.const.enum import NotebookPage
    from dzgui.controller.mc import Controller
    from dzgui.controllers.emitter import Emitter


class ContextualButton(Gtk.Button):
    def __init__(
        self, label: str, opens: "NotebookPage", tooltip: str, context: ButtonType
    ) -> None:
        super().__init__(
            label=label,
            tooltip_text=tooltip,
            focus_on_click=False,
        )

        self.context = context
        self.opens = opens


class ButtonBox(Gtk.Box):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(
            spacing=6,
            margin_top=0,
            margin_start=10,
            margin_end=10,
            orientation=Gtk.Orientation.VERTICAL,
        )

        self.controller = controller
        self.emitter = controller.get_emitter()
        self.emitter.connect("request_button_box_focus", self._focus_first_button)

        self.buttons = list()
        self.connect("key-press-event", self._on_keypress)
        prefs = controller.get_prefs()

        for side_button in ButtonType:
            button = ContextualButton(
                label=side_button.dict["label"],
                opens=side_button.dict["opens"],
                tooltip=side_button.dict["tooltip"],
                context=side_button,
            )

            size = (10, 10) if prefs.is_steam_deck else (50, 50)
            x, y = size
            button.set_size_request(x, y)

            self.buttons.append(button)
            button.connect("clicked", self._on_selection_button_clicked)
            self.pack_start(button, NO_EXPAND, NO_FILL, NO_PADDING)

    def _focus_first_button(self, emitter: "Emitter") -> None:
        self.buttons[0].grab_focus()

    def _on_selection_button_clicked(self, button: Gtk.Button) -> None:
        self.controller.open_page_by_button(button)

    def _walk_buttons(self, increment: int) -> None:
        for i, button in enumerate(self.buttons):
            if button.is_focus():
                n = i + increment
                if n == len(self.buttons):
                    return
                if n == -1:
                    return
                n = self.buttons[n]
                n.grab_focus()
                return

    def _on_keypress(self, widget: Gtk.Widget, event: Gdk.EventKey) -> None:
        match event.keyval:
            case Gdk.KEY_h:
                self.controller.focus_notebook()
            case Gdk.KEY_j:
                self._walk_buttons(1)
            case Gdk.KEY_k:
                self._walk_buttons(-1)
            case Gdk.KEY_question:
                self.controller.open_keybindings()
