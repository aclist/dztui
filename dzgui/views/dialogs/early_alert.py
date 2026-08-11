import textwrap
import sys

from typing import Self
from dzgui.util.strings import dialog_error, dialog_header

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402

class AbortDialog(Gtk.MessageDialog):
    def __init__(self, string: str, buttons: Gtk.ButtonsType) -> None:
        super().__init__(
            title=dialog_header,
            text=dialog_error,
            transient_for=None,
            buttons=buttons,
        )

        msg = textwrap.fill(string, 50)
        self.format_secondary_text(msg)

        aa = self.get_action_area()
        aa.set_margin_bottom(20)
        aa.set_layout(Gtk.ButtonBoxStyle.CENTER)

        self.outer = self.get_content_area()
        self.outer.set_margin_start(30)
        self.outer.set_margin_end(30)

        self.set_default_size(250, 100)

        abort = self.get_widget_for_response(Gtk.ResponseType.OK)
        ignore = self.get_widget_for_response(Gtk.ResponseType.CANCEL)
        if abort is not None and hasattr(abort, "set_label"):
            abort.set_label("Exit")
        if ignore is not None and hasattr(ignore, "set_label"):
            ignore.set_label("Ignore")

        self.connect("response", self._on_response)

        self.run()
        self.destroy()

    def _on_response(self, dialog: Self, response: Gtk.ResponseType) -> None:
        match response:
            case Gtk.ResponseType.OK | Gtk.ResponseType.DELETE_EVENT:
                sys.exit(1)
            case Gtk.ResponseType.CANCEL:
                print("response was cancel")
                return

class EarlyAlertDialog(AbortDialog):
    def __init__(self, string: str, buttons: Gtk.ButtonsType) -> None:
        super().__init__(string=string, buttons=Gtk.ButtonsType.OK)

class EarlyIgnoreDialog(AbortDialog):
    def __init__(self, string: str) -> None:
        super().__init__(string=string, buttons=Gtk.ButtonsType.OK_CANCEL)

