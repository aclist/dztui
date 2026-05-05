import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk  # noqa


class HelpMenuMixin:
    def _on_esc_keypress(self, widget: Gtk.Widget, event: Gdk.EventKey) -> bool:
        if event.keyval == Gdk.KEY_Escape:
            prior = self.controller.get_prior_page()  # type: ignore
            self.controller.open_page(prior)  # type: ignore
            return True
        return False
