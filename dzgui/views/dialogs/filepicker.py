from pathlib import Path

import gi  # noqa E402
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GObject

from dzgui.util.strings import picker


class FilePicker(Gtk.FileChooserDialog):
    def __init__(self, parent: Gtk.Window) -> None:
        super().__init__(
            title=picker.title,
            action=Gtk.FileChooserAction.SAVE,
            parent=parent,
            resizable=True,
        )
        self.add_buttons("_Cancel", Gtk.ResponseType.CANCEL)
        self.add_buttons("_Save", Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)

        self.set_current_name(picker.placeholder)

    def pick_file(self) -> Path | None:
        res = self.run()
        if res in (Gtk.ResponseType.CANCEL, Gtk.ResponseType.DELETE_EVENT):
            self.destroy()
            return None
        if res == Gtk.ResponseType.OK:
            file = self.get_filename()
            if file is not None:
                self.destroy()
                return Path(file)
        return None
