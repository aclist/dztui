from typing import Self

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa

from dzgui.const.constants import NO_EXPAND, NO_FILL, NO_PADDING
from dzgui.util.import strings

class LanDialog(Gtk.MessageDialog):
    """
    Performs integer validation on the provided port
    and blocks if out of range. Returns None if user cancels
    """
    def __init__(self) -> None:
        super().__init__(
            transient_for=AppNav.window, #FIXME
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=strings.scan_servers,
            secondary_text=strings.select_port,
            title=strings.dialog_header,
            modal=True,
        )

        self.set_size_request(500, 0)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        buttons = [
            (strings.default_port, Port.DEFAULT),
            (strings.custom_port, Port.CUSTOM),
        ]

        self.button_box = Gtk.Box()
        self.button_box.set_orientation(Gtk.Orientation.VERTICAL)
        self.button_box.active_button = None

        for k, v in buttons:
            button = Gtk.RadioButton(label=k)
            button.port = v
            button.connect("toggled", self._on_button_toggled)
            self.button_box.add(button)
            if v == Port.DEFAULT:
                self.button_box.active_button = button
            else:
                button.join_group(self.button_box.active_button)

        self.entry = Gtk.Entry()
        self.button_box.add(self.entry)
        self.entry.set_no_show_all(True)

        # TODO: strings
        self.warn_label = Gtk.Label(label="Invalid port")
        self.warn_label.set_no_show_all(True)
        self.button_box.add(self.warn_label)

        content = self.get_content_area()
        content.pack_start(self.button_box, NO_EXPAND, NO_FILL, NO_PADDING)
        content.set_margin_start(30)
        content.set_margin_end(30)
        content.show_all()

        self.action_area.set_layout(Gtk.ButtonBoxStyle.CENTER)
        self.action_area.set_margin_bottom(20)

        self.port = None
        self.ok = self.action_area.get_children()[1]

        self.connect("response", self._on_dialog_response)
        self.connect("key-press-event", self._on_keypress)
        self.connect("delete-event", self.restore_context)

        self.entry.connect("insert-text", self._on_text_typed)
        self.entry.get_property("buffer").connect(
            "deleted-text", self._on_text_deleted
        )

    def _validate(self, text: str) -> None:
        state = ip.is_valid_port(text)
        self.ok.set_sensitive(not state)
        self.warn_label.set_visible(state)

        # TODO: can put in validation method
        if len(text) == 0:
            self.warn_label.set_visible(False)

    def _on_text_deleted(
        self, buffer: Gtk.EntryBuffer, position: int, chars: int
    ) -> None:
        text = buffer.get_text()
        self._validate(text)

    def _on_text_typed(
        self, entry: Gtk.Entry, text: str, length: int, pos: int) -> None:
        self._validate(entry.get_text() + text)

    def restore_context(self, *args: Any) -> None:
        context = WindowContext.MAIN_MENU
        AppNav.treeview.set_view(context)

    def _on_keypress(self, widget: Gtk.Widget, event: Gdk.EventKey) -> None:
        if event.keyval == Gdk.KEY_Return:
            if self.ok.is_sensitive():
                self.response(Gtk.ResponseType.OK)
            if self.button_box.get_children()[0].is_focus():
                self.response(Gtk.ResponseType.OK)
            else:
                self.restore_context()

        if event.keyval == Gdk.KEY_Up:
            self.ok.set_sensitive(True)
            self.entry.set_text("")
            self.button_box.get_children()[0].grab_focus()

    def _on_dialog_response(
        self, dialog: Self, response: Gtk.ResponseType
    ) -> None:
        cancel_events = [
            Gtk.ResponseType.CLOSE,
            Gtk.ResponseType.CANCEL,
            Gtk.ResponseType.DELETE_EVENT,
        ]

        if response in cancel_events:
            self.restore_context()
            return

        string = self.entry.get_text()
        port = self.button_box.active_button.port

        match port:
            case Port.DEFAULT:
                self.port = UDP_PORT
            case Port.CUSTOM:
                if ip.is_valid_port(string):
                    self.stop_emission_by_name("response")
                else:
                    self.port = int(string)

    def get_selected_port(self) -> int:
        return self.port

    def _on_button_toggled(self, button: Gtk.Button) -> None:
        if button.get_active():
            self.button_box.active_button = button
            match button.port:
                case Port.DEFAULT:
                    self.entry.set_visible(False)
                case Port.CUSTOM:
                    self.entry.set_visible(True)
                    self.entry.grab_focus()
                    self.ok.set_sensitive(False)
