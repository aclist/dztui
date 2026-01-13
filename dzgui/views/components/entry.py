from typing import Callable, TYPE_CHECKING

from dzgui.api.servers import validate_ip
from dzgui.util.css import add_class, remove_class
from dzgui.util.strings import connect_panel, lan_panel

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GObject # noqa E402

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
    __gsignals__ = {
        "string_validated": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }
    def __init__(self, controller: "Controller", func: Callable) -> None:
        super().__init__(
            hexpand=True,
            placeholder_text=connect_panel.placeholder,
            tooltip_text=connect_panel.entry_tooltip
        )

        self.func: Callable
        self.set_validation_func(func)
        self.controller = controller

        self.classname = "invalid-entry"
        self.connect("key-press-event", self._on_entry_keypress)
        self.connect("changed", self._on_text_changed)

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
        self.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, "edit-clear-symbolic")
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
        super().__init__(controller, func=validate_ip_or_id)
        self.set_placeholder_text(connect_panel.placeholder)
        self.set_tooltip_text(connect_panel.entry_tooltip)

class PortEntry(ValidatedEntry):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(controller, func=validate_port)
        self.set_placeholder_text(lan_panel.placeholder)
        self.set_tooltip_text(lan_panel.entry_tooltip)
