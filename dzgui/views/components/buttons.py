from typing import Callable, Self, TYPE_CHECKING

from dzgui.util.clip import copy_clipboard
from dzgui.util.format import pluralize
from dzgui.strings import buttons
from dzgui.util.strings import (
    alert_button_tooltip,
    atomic_buttons,
    connect_panel,
)
from dzgui.const.constants import (
    CLIPBOARD,
    INPUT_KEYBOARD,
    LIST_ADD,
    REFRESH_ICON,
    STEAM_ICON,
    WARNING,
    WEB_BROWSER,
)

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib  # noqa E402

if TYPE_CHECKING:
    from gi.repository import GLib
    from dzgui.controllers.mc import Controller
    from dzgui.controllers.emitter import Emitter
    from dzgui.const.enum import ServerTab


class Icon(Gtk.Image):
    def __init__(self, name: str, l_margin: int = 0) -> None:
        super().__init__(
            icon_name=name,
            icon_size=Gtk.IconSize.BUTTON,
            margin_start=l_margin,
            ypad=2,
        )


class LargeIcon(Gtk.Image):
    def __init__(self, name: str, l_margin: int = 5) -> None:
        super().__init__(
            icon_name=name, icon_size=Gtk.IconSize.LARGE_TOOLBAR, margin_start=l_margin
        )


class IconButton(Gtk.Button):
    def __init__(self, icon: str, margin: int = 0) -> None:
        super().__init__()
        self.icon = Icon(icon, l_margin=margin)
        self.set_image(self.icon)
        self.set_image_position(Gtk.PositionType.RIGHT)
        self.set_focus_on_click(False)


class IconTextButton(IconButton):
    def __init__(self, icon: str, label: str) -> None:
        super().__init__(icon, margin=5)
        self.set_label(label)


class LargeIconTextButton(IconButton):
    def __init__(self, icon: str, label: str) -> None:
        super().__init__(icon)
        self.set_label(label)
        self.set_image(LargeIcon(icon))


class ClipboardButton(IconTextButton):
    def __init__(self, controller: "Controller", func: Callable) -> None:
        super().__init__(CLIPBOARD, atomic_buttons.copy)
        self.controller = controller
        self.connect("clicked", self._on_button_clicked, func)

        self.set_tooltip_text("Copy IP to clipboard")

    def _on_button_clicked(self, button: Self, func: Callable) -> None:
        data = func()
        copy_clipboard(data)


class WebButton(IconTextButton):
    def __init__(self, label: str) -> None:
        super().__init__(icon=WEB_BROWSER, label=label)
        pass


class RefreshButton(IconTextButton):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(
            icon=REFRESH_ICON,
            label=atomic_buttons.refresh,
        )
        self.controller = controller
        emitter = self.controller.get_emitter()
        self.loading = False

        self.time = 30

        self.set_margin_top(10)
        self.set_margin_start(80)
        self.set_margin_end(80)
        self.set_tooltip_text(atomic_buttons.refresh_tooltip)

        self.connect("clicked", self._on_refresh_clicked)
        emitter.connect("servers_loaded", self.start_decrement)

    def _on_refresh_clicked(self, button: Self) -> None:
        """Spawned in a thread"""
        self.loading = True
        self.controller.refresh_tree()
        # TODO: get server tab enum
        # if LAN tab, reload existing entries in place

    def start_decrement(self, emitter: "Emitter", tab: "ServerTab") -> None:
        if self.loading:
            self.set_sensitive(False)
            self.loading = False
            self.show_time(True)
            GLib.timeout_add_seconds(1, self.decrement)

    def decrement(self) -> bool:
        self.time -= 1
        if self.time == 0:
            self.time = 30
            self.show_time(False)
            self.set_sensitive(True)
            return False
        self.show_time(True)
        return True

    def show_time(self, state: bool) -> None:
        if state is True:
            self.set_label(f"{atomic_buttons.refresh} ({str(self.time)})")
        else:
            self.set_label(atomic_buttons.refresh)


class KeysButton(IconTextButton):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(icon=INPUT_KEYBOARD, label=atomic_buttons.keys)

        self.controller = controller
        self.set_margin_top(10)
        self.set_margin_start(80)
        self.set_margin_end(80)

        self.set_tooltip_text(atomic_buttons.keys_tooltip)

        self.connect("clicked", self._on_keys_clicked)

    def _on_keys_clicked(self, button: Gtk.Button) -> None:
        self.controller.open_keybindings()


class SteamConnectButton(LargeIconTextButton):
    def __init__(self) -> None:
        super().__init__(icon=STEAM_ICON, label=connect_panel.connect)
        self.set_tooltip_text(connect_panel.connect_tooltip)


class SteamTextButton(SteamConnectButton):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.set_label(label)


class SteamWorkshopButton(SteamTextButton):
    def __init__(self) -> None:
        super().__init__(label=buttons.workshop)
        self.set_tooltip_text(buttons.workshop_tooltip)


class AddButton(IconTextButton):
    def __init__(self) -> None:
        super().__init__(icon=LIST_ADD, label=connect_panel.add)
        self.set_tooltip_text(connect_panel.add_tooltip)


class LoggerAlertsButton(IconTextButton):
    def __init__(self, warnings: int, errors: int) -> None:
        warnings_text = ""
        errors_text = ""
        separator = ""
        if warnings > 0:
            warnings_plural = pluralize("warnings", warnings)
            warnings_text = f"{warnings} {warnings_plural}"
        if errors > 0:
            errors_plural = pluralize("errors", errors)
            errors_text = f" {errors} {errors_plural}"
        if warnings + errors > 1:
            separator = ","
        concat = warnings_text + separator + errors_text
        super().__init__(
            icon=WARNING,
            label=f"Loaded with{concat}",
        )
        self.set_halign(Gtk.Align.END)
        self.set_hexpand(True)
        self.set_tooltip_text(alert_button_tooltip)
