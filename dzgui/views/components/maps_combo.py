import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib  # noqa E402


class MapsCombo(Gtk.EntryCompletion):
    def __init__(self):
        super().__init__(inline_completion=True)
        self.set_text_column(0)
        self.set_minimum_key_length(1)
