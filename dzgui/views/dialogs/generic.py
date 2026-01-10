import textwrap
from typing import Any, Literal, Self, TYPE_CHECKING

from dzgui.const.constants import NO_EXPAND, NO_FILL, EXPAND, FILL
from dzgui.const.enum import Popup, ButtonType, NotebookPage
from dzgui.util import strings

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa E402


if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller

class ExceptionDialog(Gtk.MessageDialog):
    def __init__(self, controller: "Controller", trace: str):
        super().__init__(
            transient_for=controller.mediator.window,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Error",
            secondary_text="Something went wrong. See the detailed error below.",
            title=strings.dialog_header,
            modal=True,
        )

        # TODO: strings
        self.set_size_request(550, 250)

        from dzgui.views.components.buttons import ClipboardButton
        content = self.get_content_area()
        content.set_spacing(0)

        box = Gtk.Box(hexpand=True, vexpand=True, orientation=Gtk.Orientation.VERTICAL)
        textview = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD, editable=False, left_margin=10, right_margin=10)
        textview.set_buffer(Gtk.TextBuffer(text=trace))
        # NOTE: box expands to end of content area
        box.pack_start(textview, EXPAND, FILL, 10)

        action_area = self.get_action_area()
        action_area.set_spacing(10)
        action_area.set_margin_bottom(10)
        action_area.set_layout(Gtk.ButtonBoxStyle.CENTER)

        but = ClipboardButton(controller, trace)
        # TODO: flag to set button with text, or other class
        but.set_label("Copy")
        action_area.pack_start(but, True, True, 10)
        # NOTE: reverse button order after insertion
        action_area.set_direction(Gtk.TextDirection.RTL)
        content.add(box)

        self.set_default_response(Gtk.ResponseType.OK)
        self.connect("response", self._on_response)
        self.show_all()
        """
        usage:
        from dzgui.views.dialogs.generic import ExceptionDialog
        try:
            a.banana()
        except Exception as e:
            trace = traceback.format_exc()
            dialog = ExceptionDialog(MainController, trace)
            dialog.run()
        """


    def _on_response(self, dialog: Self, response: Gtk.ResponseType) -> None:
        self.destroy()


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

        Gtk.MessageDialog.__init__(
            self,
            transient_for=controller.mediator.window,
            message_type=dialog_type,
            buttons=button_type,
            text=header_text,
            secondary_text=textwrap.fill(text, 50),
            # NOTE: steam deck prints <2> if dialog title is same as window title
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
