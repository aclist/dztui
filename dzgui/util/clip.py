import gi

gi.require_version("Gtk", "3.0")
from gi.repository.Gdk import SELECTION_CLIPBOARD  # noqa E402
from gi.repository.Gtk import Clipboard  # noqa E402


def copy_clipboard(text: str) -> None:
    clipboard = Clipboard.get(SELECTION_CLIPBOARD)
    clipboard.set_text(text, -1)
