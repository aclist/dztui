from typing import Literal, Self, TYPE_CHECKING

from dzgui.const.constants import NO_EXPAND, NO_FILL, NO_PADDING, EXPAND, FILL
from dzgui.util import strings
from dzgui.views.components.buttons import ClipboardButton

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller


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
            transient_for=controller.get_window(),
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

        self.get_action_area().set_layout(Gtk.ButtonBoxStyle.CENTER)  # type: ignore
        self.get_action_area().set_margin_bottom(20)
        self.outer = self.get_content_area()
        self.outer.set_margin_start(30)
        self.outer.set_margin_end(30)

    def pack(self, widget: Gtk.Widget) -> None:
        content = self.get_content_area()
        content.pack_start(widget, EXPAND, FILL, NO_PADDING)


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
        if cancel is None:
            return
        if hasattr(cancel, "set_label"):
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
    def __init__(
        self,
        controller: "Controller",
        secondary: str,
        jobs: int = 1,
        show_cancel: bool = False,
    ):
        super().__init__(
            controller=controller,
            text=strings.wait,
            mtype=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.NONE,
            secondary=secondary,
        )

        self.controller = controller
        self.jobs = jobs
        self.cur_job = 1

        self.cancel = Gtk.Button(label="Cancel", halign=Gtk.Align.CENTER)
        self.cancel.connect("clicked", lambda _: self.controller.set_cancel_event())

        self.connect("delete-event", lambda widget, event: True)
        content = self.get_content_area()
        spinner = Gtk.Spinner()
        self.prog = Gtk.ProgressBar()

        content.pack_end(self.cancel, NO_EXPAND, NO_FILL, 0)
        content.pack_end(spinner, NO_EXPAND, NO_FILL, 0)

        if self.jobs > 1:
            content.pack_end(self.prog, NO_EXPAND, NO_FILL, 0)
        else:
            spinner.start()

        if show_cancel is False:
            self.connect("realize", lambda _: self.cancel.set_visible(False))

    def update_text(self, msg: str) -> None:
        self.format_secondary_text(msg)

    def increment(self, msg: str = "") -> None:
        if msg != "":
            self.format_secondary_text(msg)
        fraction = self.cur_job / self.jobs
        self.prog.set_fraction(fraction)
        self.cur_job += 1

    def show_cancel(self, state: bool) -> None:
        self.cancel.set_visible(state)


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
        # TODO: use a signal?
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
        # TODO: wrap/truncate long messages
        textview = Gtk.TextView(
            wrap_mode=Gtk.WrapMode.WORD, editable=False, left_margin=10, right_margin=10
        )
        textview.set_buffer(Gtk.TextBuffer(text=self.trace))
        box.pack_start(textview, EXPAND, FILL, 10)
        scrollable.add(box)

        content = self.get_content_area()
        content.set_spacing(0)
        # TODO: padding around top of content area when traceback is long
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
                return None
            case Gtk.ResponseType.NONE:
                return True
            case Gtk.ResponseType.DELETE_EVENT:
                self.destroy()
                return None
            case _:
                return None
