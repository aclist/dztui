import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa

from dzgui.const.constants import NO_EXPAND, NO_FILL, NO_PADDING
from dzgui.const.enum import Popup


class EntryDialog(GenericDialog):
    def __init__(self, text: str, mode: Popup, link: str, button_type=None):
        super().__init__(text, mode)

        """
        Wraps Gtk.Entry in a dialog and provides basic response handling.
        Returns user input as a string or None.
        The Entry widget itself can be manipulated via the get_entry() method.
        """

        self.dialog = GenericDialog(text, mode)
        self.dialogBox = self.dialog.get_content_area()
        self.dialog.set_default_response(Gtk.ResponseType.OK)
        self.dialog.set_size_request(500, 0)

        self.user_entry = Gtk.Entry()
        set_surrounding_margins(self.user_entry, 20)
        self.user_entry.set_margin_top(0)
        self.user_entry.set_size_request(250, 0)
        self.user_entry.set_activates_default(True)
        self.dialogBox.pack_start(self.user_entry, NO_EXPAND, NO_FILL, NO_PADDING)

        if link:
            button = Gtk.Button(label=link)
            button.set_margin_start(60)
            button.set_margin_end(60)
            button.connect("clicked", self._on_button_clicked, button_type)
            self.dialogBox.pack_end(button, NO_EXPAND, NO_FILL, NO_PADDING)

        self.ok = self.dialog.action_area.get_children()[1]
        self.ok.set_sensitive(False)
        self.user_entry.connect("insert-text", self._on_text_typed)
        self.user_entry.get_property("buffer").connect(
            "deleted-text", self._on_text_deleted
        )

    def _is_valid_text(self, text: str) -> bool:
        if text.isspace():
            return False
        if len(text) == 0:
            return False
        return True

    def _on_text_deleted(
        self, buffer: Gtk.EntryBuffer, position: int, chars: int
    ) -> None:
        text = buffer.get_text()
        state = self._is_valid_text(text)
        self.ok.set_sensitive(state)

    def _on_text_typed(
        self, entry: Gtk.Entry, text: str, length: int, pos: int
    ) -> None:
        state = self._is_valid_text(text)
        self.ok.set_sensitive(state)

    def _on_button_clicked(self, button: Gtk.Button, enum: RowType) -> None:
        result = open_links.open_link_by_rowtype(enum)
        if result is False:
            AppNav.window.spawn_dialog(strings.something_wrong, Popup.NOTIFY)

    def get_entry(self) -> Gtk.Entry:
        return self.user_entry

    def get_input(self) -> str | None:
        self.dialog.show_all()

        response = self.dialog.run()
        text = self.user_entry.get_text()
        self.dialog.destroy()
        if (response == Gtk.ResponseType.OK) and (text != ""):
            return text
        else:
            return None
