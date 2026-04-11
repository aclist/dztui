from typing import Self, TYPE_CHECKING

from dzgui.views.components.entry import ValidatedEntry
from dzgui.views.dialogs.generic import GenericDialog

import gi  # noqa E402

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk  # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller


class NoteDialog(GenericDialog):
    def __init__(self, controller: "Controller"):
        # TODO: add to strings
        title = "Add a short note/reminder."
        secondary = "Limit 30 chars"
        super().__init__(
            controller=controller,
            text=title,
            buttons=Gtk.ButtonsType.NONE,
            mtype=Gtk.MessageType.INFO,
            secondary=secondary,
        )

        self.controller = controller

        delete_button = Gtk.Button(label="Delete note")
        delete_button.set_sensitive(False)
        self.add_action_widget(delete_button, Gtk.ResponseType.CANCEL)
        self.add_button("OK", Gtk.ResponseType.OK)
        self.ok = self.get_widget_for_response(Gtk.ResponseType.OK)
        self.ok.grab_default()

        self.entry = ValidatedEntry(controller, self.validate)
        self.entry.set_max_length(30)
        self.entry.set_size_request(250, 0)
        self.pack(self.entry)

        note = self.controller.get_note()
        self.entry.set_text(note)
        if len(note) > 0:
            delete_button.set_sensitive(True)

        self.show_all()
        # NOTE: explicitly deselect region and move to end of line
        self.entry.set_position(-1)

        self.entry.set_activates_default(True)
        self.connect("response", self._on_response)

    def validate(self, text: str) -> None:
        # FIXME: not checking for text deletion, e.g., ctrl-a, ctrl-x
        if text.isspace():
            sensitive = False
        else:
            sensitive = True
        self.ok.set_sensitive(sensitive)
        return sensitive

    def _on_response(self, dialog: Self, response: Gtk.ResponseType) -> None:
        match response:
            case Gtk.ResponseType.DELETE_EVENT:
                self.destroy()
            case Gtk.ResponseType.OK:
                note = self.entry.get_text()
                # FIXME: handle deleting existing note, going from N chars to 0 chars and clicking OK
                if len(note) > 0:
                    self.controller.add_note(note)
                self.destroy()
            case Gtk.ResponseType.CANCEL:
                self.controller.delete_note()
                self.destroy()
            case Gtk.ResponseType.CANCEL | Gtk.ResponseType.CLOSE:
                self.destroy()
