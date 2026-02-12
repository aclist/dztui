import textwrap
from typing import Literal, Self, TYPE_CHECKING

from dzgui.const.constants import NO_EXPAND, NO_FILL, EXPAND, FILL
from dzgui.const.enum import Popup, ButtonType, NotebookPage
from dzgui.util import strings
from dzgui.views.components.buttons import ClipboardButton

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller

# TODO: reimplement as standalone dialogs
# NOTE: steam deck prints <2> if dialog title is same as window title
#    case Popup.MODLIST:
#        dialog_type = Gtk.MessageType.INFO
#        button_type = Gtk.ButtonsType.OK
#        header_text = strings.modlist
#    case Popup.DETAILS:
#        dialog_type = Gtk.MessageType.INFO
#        button_type = Gtk.ButtonsType.OK
#        header_text = strings.server_details
# TODO: unused
# def update_label(self, text: str) -> None:
#    self.format_secondary_text(text)


class GenericDialog(Gtk.MessageDialog):
    def __init__(
        self,
        controller: "Controller",
        text: str,
        mtype: Gtk.MessageType,
        buttons: Gtk.ButtonsType,
        secondary: str,
    ) -> None:
        super().__init__(
            transient_for=controller.mediator.window,
            message_type=mtype,
            buttons=buttons,
            text=text,
            secondary_text=secondary,
            title=strings.dialog_header,
            modal=True,
        )

        self.set_size_request(500, 0)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        self.set_default_response(Gtk.ResponseType.OK)
        self.connect("response", self._on_response)

        self.action_area.set_layout(Gtk.ButtonBoxStyle.CENTER)
        self.action_area.set_margin_bottom(20)
        self.outer = self.get_content_area()
        self.outer.set_margin_start(30)
        self.outer.set_margin_end(30)

    def _on_response(self, dialog: Self, response: Gtk.ResponseType) -> None:
        self.destroy()
        return response


class ConfirmationDialog(GenericDialog):
    def __init__(self, controller: "Controller", secondary: str):
        super().__init__(
            controller=controller,
            text=strings.confirm,
            mtype=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            secondary=secondary,
        )


class IgnoreDialog(GenericDialog):
    def __init__(self, controller: "Controller", secondary: str):
        super().__init__(
            controller=controller,
            text=strings.confirm,
            mtype=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            secondary=secondary,
        )
        cancel = self.get_widget_for_response(Gtk.ResponseType.CANCEL)
        cancel.set_label("Ignore")


class NotifyDialog(GenericDialog):
    def __init__(self, controller: "Controller", secondary: str):
        super().__init__(
            controller=controller,
            text=strings.notice,
            mtype=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            secondary=secondary,
        )


class WaitDialog(GenericDialog):
    def __init__(self, controller: "Controller", secondary: str):
        super().__init__(
            controller=controller,
            text=strings.wait,
            mtype=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.NONE,
            secondary=secondary,
        )

        self.connect("delete-event", self._on_dialog_delete)
        content = self.get_content_area()
        spinner = Gtk.Spinner()
        content.pack_end(spinner, NO_EXPAND, NO_FILL, 0)

        spinner.start()
        # FIXME: center on parent window
        # self.show_all()

    def _on_dialog_delete(
        self, response_id: Gtk.ResponseType, event: Gdk.Event
    ) -> Literal[True]:
        """
        Prevent manual dialog destruction
        """
        return True


class QuitDialog(GenericDialog):
    def __init__(self, controller: "Controller", secondary: str):
        super().__init__(
            controller=controller,
            text=strings.wait,
            mtype=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.NONE,
            secondary=secondary,
        )

        self.controller = controller
        self.add_button(strings.exit_app, Gtk.ResponseType.OK)

        self.connect("response", self._on_response)
        self.connect("delete-event", self._on_response)

    def _on_response(self, dialog: Self, response: Gtk.ResponseType) -> None:
        self.controller.save_res_and_quit()


class ExceptionDialog(GenericDialog):
    """
    Error dialog with rich traceback.
    Usage:
        try:
            foo()
        except Exception:
            trace = traceback.format_exc()
            dialog = ExceptionDialog(Controller, trace)
            dialog.run()
    """

    def __init__(self, controller: "Controller", trace: str):
        super().__init__(
            controller=controller,
            text=strings.error_heading,
            mtype=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.NONE,
            secondary=strings.something_wrong,
        )

        self.trace = trace
        # NOTE: box expands to end of content area
        scrollable = Gtk.ScrolledWindow(
            propagate_natural_height=True, max_content_height=500
        )
        box = Gtk.Box(hexpand=True, vexpand=True, orientation=Gtk.Orientation.VERTICAL)
        textview = Gtk.TextView(
            wrap_mode=Gtk.WrapMode.WORD, editable=False, left_margin=10, right_margin=10
        )
        textview.set_buffer(Gtk.TextBuffer(text=self.trace))
        box.pack_start(textview, EXPAND, FILL, 10)
        scrollable.add(box)

        content = self.get_content_area()
        content.set_spacing(0)
        # FIXME: padding around top of content area when traceback is long
        content.add(scrollable)

        copy_button = ClipboardButton(controller, self.get_trace)
        self.add_action_widget(copy_button, Gtk.ResponseType.NONE)
        self.add_button("OK", Gtk.ResponseType.OK)

        self.show_all()
        self.action_area.get_children()[1].grab_focus()
        self.connect("response", self._on_response)

    def get_trace(self) -> str:
        return self.trace

    def _on_response(
        self, dialog: Self, response: Gtk.ResponseType
    ) -> None | Literal[True]:
        match response:
            case Gtk.ResponseType.OK:
                self.destroy()
            case Gtk.ResponseType.NONE:
                return True
            case Gtk.ResponseType.DELETE_EVENT:
                self.destroy()
