from typing import Any, Callable, TYPE_CHECKING

from dzgui.api.servers import validate_ip
from dzgui.const.constants import VIEW_CONCEAL, VIEW_REVEAL
from dzgui.util.css import add_class, remove_class
from dzgui.util.strings import connect_panel, lan_panel
from dzgui.strings.errors import api_popover

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GObject  # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller


def validate_port(text: str) -> bool:
    if text.isdigit():
        if int(text) < 1:
            return False
        if int(text) > 65535:
            return False
        return True
    else:
        return False


def validate_ip_or_id(text: str) -> bool:
    try:
        validate_ip(text)
        return True
    except Exception:
        if text.isdigit():
            return True
        else:
            return False


class ValidatedEntry(Gtk.Entry):
    def __init__(
        self,
        controller: "Controller",
        func: Callable,
        placeholder_text: str = "",
        tooltip_text: str = "",
    ) -> None:
        super().__init__(
            hexpand=True, placeholder_text=placeholder_text, tooltip_text=tooltip_text
        )

        self.func: Callable
        self.set_validation_func(func)
        self.controller = controller

        self.emitter = self.controller.get_emitter()

        self.classname = "invalid-entry"
        self.connect("key-press-event", self._on_entry_keypress)
        self.connect("changed", self._on_text_changed)

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(bool,))
    def string_validated(self, valid: bool) -> None:
        pass

    def mark_valid(self) -> None:
        self.emit("string_validated", True)
        remove_class(self, self.classname)

    def mark_invalid(self) -> None:
        self.emit("string_validated", False)
        add_class(self, self.classname)

    def mark_default(self) -> None:
        self.emit("string_validated", False)
        remove_class(self, self.classname)

    def set_validation_func(self, func: Callable) -> None:
        self.func = func

    def insert_icon(self) -> None:
        self.set_icon_from_icon_name(
            Gtk.EntryIconPosition.SECONDARY, "edit-clear-symbolic"
        )
        self.set_icon_activatable(Gtk.EntryIconPosition.SECONDARY, True)
        self.connect("icon-release", self._on_icon_release)

    def remove_icon(self) -> None:
        self.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, "")

    def _on_text_changed(self, entry: Gtk.Entry) -> None:
        # TODO: on submission, strip whitespace and newlines
        # (validate_ip() is permissive of whitespace)
        text = entry.get_text()
        if len(text) < 1:
            self.mark_default()
            self.remove_icon()
            return
        if len(text) > 0:
            self.insert_icon()

        if self.func(text) is True:
            self.mark_valid()
        else:
            self.mark_invalid()

    def _on_icon_release(
        self,
        entry: Gtk.Entry,
        icon_pos: Gtk.EntryIconPosition,
        event: Gdk.Event,
    ) -> None:
        entry.set_text("")
        self.remove_icon()

    def _on_entry_keypress(self, entry: Gtk.Entry, event: Gdk.EventKey) -> None:
        if event.keyval == Gdk.KEY_Escape:
            # NOTE: unselect text
            entry.select_region(0, 0)
            self.controller.grab_active_treeview()


class IpEntry(ValidatedEntry):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(
            controller,
            func=validate_ip_or_id,
            placeholder_text=connect_panel.placeholder,
            tooltip_text=connect_panel.entry_tooltip,
        )
        self.set_placeholder_text(connect_panel.placeholder)
        self.set_tooltip_text(connect_panel.entry_tooltip)


class PortEntry(ValidatedEntry):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(
            controller,
            func=validate_port,
            placeholder_text=connect_panel.placeholder,
            tooltip_text=connect_panel.entry_tooltip,
        )
        self.set_placeholder_text(lan_panel.placeholder)
        self.set_tooltip_text(lan_panel.entry_tooltip)


# TODO: backport to Options page
class APIEntry(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        self.func: Callable | None = None

        # TODO: strings
        self.entry = Gtk.Entry(
            width_chars=60, hexpand=True, placeholder_text="Enter API key"
        )
        self.entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, VIEW_REVEAL)
        self.entry.set_icon_activatable(Gtk.EntryIconPosition.SECONDARY, True)
        self.entry.set_visibility(False)
        self.entry.connect("changed", self._on_text_changed)
        self.entry.connect("icon-release", self._on_icon_release)
        self.entry.connect("activate", self._on_field_activated)

        # TODO: strings
        self.submit = Gtk.Button(label="Validate")
        self.submit.set_sensitive(False)
        self.submit.connect("clicked", self._on_submit)

        self.pop = Gtk.Popover()
        self.pop_label = Gtk.Label(
            label=api_popover,
            margin_start=10,
            margin_end=10,
        )
        self.pop.add(self.pop_label)
        # NOTE: render once to draw text in bubble
        self.pop.show_all()
        self.pop.set_margin_start(10)
        self.pop.set_relative_to(self.entry)
        self.pop.popdown()

        for el in self.entry, self.submit:
            self.add(el)

    def get_entry(self) -> Gtk.Entry:
        return self.entry

    def popup(self) -> None:
        self.pop.popup()

    def get_submit(self) -> Gtk.Button:
        return self.submit

    def _is_valid_text(self, text: str) -> bool:
        if text.isspace():
            return False
        if len(text) == 0:
            return False
        return True

    def _on_text_changed(self, entry: Gtk.Entry) -> None:
        text = entry.get_text()
        if self._is_valid_text(text):
            self.submit.set_sensitive(True)
        else:
            self.submit.set_sensitive(False)

    def _on_icon_release(
        self,
        widget: Gtk.Entry,
        icon_pos: Gtk.EntryIconPosition,
        event: Gdk.Event,
    ) -> None:
        visible = widget.get_visibility()
        if visible:
            icon, state = VIEW_REVEAL, False
        else:
            icon, state = VIEW_CONCEAL, True
        widget.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, icon)
        widget.set_visibility(state)

    def _on_field_activated(self, entry: Gtk.Entry) -> None:
        self.submit.emit("clicked")

    def _on_submit(self, button: Gtk.Button) -> Any:
        if self.func is None:
            return
        text = self.entry.get_text()
        res = self.func(text)
        return res

    def set_validation_func(self, func: Callable | None) -> None:
        self.func = func

    def disable_button(self) -> None:
        self.submit.set_sensitive(False)

    def enable_button(self) -> None:
        self.submit.set_sensitive(True)
