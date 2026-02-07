from typing import Literal

from dzgui.const.enum import NotebookPage

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk  # noqa

class HelpMenuMixin:
    def _on_esc_keypress(self, widget: Gtk.Widget, event: Gdk.EventKey) -> Literal[True]:
        if event.keyval == Gdk.KEY_Escape:
            self.controller.open_page(NotebookPage.HELP)
            return True
