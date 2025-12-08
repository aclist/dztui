import textwrap
from typing import Any, Literal, TYPE_CHECKING

from dzgui.const.constants import NO_EXPAND, NO_FILL
from dzgui.const.enum import Popup, ButtonType, NotebookPage
from dzgui.util import strings

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa E402


if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller

class GenericDialog(Gtk.MessageDialog):
    def __init__(self, controller: "Controller", text: str, mode: Popup):
        match mode:
            case Popup.WAIT:
                dialog_type = Gtk.MessageType.INFO
                button_type = Gtk.ButtonsType.NONE
                header_text = strings.wait
            case Popup.NOTIFY | Popup.RETURN | Popup.QUIT:
                dialog_type = Gtk.MessageType.INFO
                button_type = Gtk.ButtonsType.OK
                header_text = strings.notice
            case Popup.CONFIRM:
                dialog_type = Gtk.MessageType.QUESTION
                button_type = Gtk.ButtonsType.OK_CANCEL
                header_text = strings.confirmation
            case Popup.ENTRY:
                dialog_type = Gtk.MessageType.QUESTION
                button_type = Gtk.ButtonsType.OK_CANCEL
                header_text = strings.input_required
            case Popup.MODLIST:
                dialog_type = Gtk.MessageType.INFO
                button_type = Gtk.ButtonsType.OK
                header_text = strings.modlist
            case Popup.DETAILS:
                dialog_type = Gtk.MessageType.INFO
                button_type = Gtk.ButtonsType.OK
                header_text = strings.server_details

        # NOTE: steam deck prints <2> if dialog title is same as window title
        Gtk.MessageDialog.__init__(
            self,
            transient_for=controller.mediator.window,
            message_type=dialog_type,
            buttons=button_type,
            text=header_text,
            secondary_text=textwrap.fill(text, 50),
            title=strings.dialog_header,
            modal=True,
        )

        self.controller = controller

        if mode == Popup.WAIT:
            dialogBox = self.get_content_area()
            spinner = Gtk.Spinner()
            dialogBox.pack_end(spinner, NO_EXPAND, NO_FILL, 0)
            spinner.start()
            self.connect("delete-event", self._on_dialog_delete)

        if mode == Popup.RETURN:
            button_label = strings.main_menu
            ok = self.action_area.get_children()[0]
            ok.set_label(button_label)
            ok.connect("clicked", self._return_to_main_menu)
            self.connect("delete-event", self._return_to_main_menu)

        if mode == Popup.QUIT:
            button_label = strings.exit_app
            ok = self.action_area.get_children()[0]
            ok.set_label(button_label)
            ok.connect("clicked", self._quit)
            self.connect("delete-event", self._quit)

        self.set_default_response(Gtk.ResponseType.OK)
        self.set_size_request(500, 0)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        self.action_area.set_layout(Gtk.ButtonBoxStyle.CENTER)
        self.action_area.set_margin_bottom(20)
        self.outer = self.get_content_area()
        self.outer.set_margin_start(30)
        self.outer.set_margin_end(30)

    def _quit(self, *args: Any) -> None:
        self.controller.save_res_and_quit()

    def _on_dialog_delete(
            self, response_id: Gtk.ResponseType, event: Gdk.Event
    ) -> Literal[True]:
        """
        Prevent manual dialog destruction
        """
        return True

    def _return_to_main_menu(self, widget: Gtk.Widget) -> None:
        self.controller.open_page(NotebookPage.MAIN)

    def update_label(self, text: str) -> None:
        self.format_secondary_text(text)
