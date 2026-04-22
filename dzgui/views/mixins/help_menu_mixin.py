from typing import Literal

from dzgui.const.enum import NotebookPage

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk  # noqa


class HelpMenuMixin:
    def _on_esc_keypress(
        self, widget: Gtk.Widget, event: Gdk.EventKey
    ) -> Literal[True]:
        if event.keyval == Gdk.KEY_Escape:
            prior = self.controller.get_prior_page()
            self.controller.open_page(prior)  # type: ignore
            return True
