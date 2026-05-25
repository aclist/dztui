from dzgui.util import css

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa


class NoOverlayScrolledWindow(Gtk.ScrolledWindow):
    def __init__(self) -> None:
        super().__init__(overlay_scrolling=False)
