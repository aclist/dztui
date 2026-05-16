from importlib import resources

from dzgui.const.constants import APP_NAME_LOWER, CSS_PATH

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk  # noqa E402


def add_class(widget: Gtk.Widget, label: str) -> None:
    """
    Sets the classname of a widget, used
    to apply CSS styling later
    """
    context = widget.get_style_context()
    context.add_class(label)


def remove_class(widget: Gtk.Widget, label: str) -> None:
    context = widget.get_style_context()
    context.remove_class(label)


def load_css() -> None:
    css = resources.read_text(APP_NAME_LOWER, CSS_PATH)
    prov = Gtk.CssProvider()
    prov.load_from_data(css.encode("ascii"))
    screen = Gdk.Screen.get_default()
    if screen:
        Gtk.StyleContext.add_provider_for_screen(
            screen, prov, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )
