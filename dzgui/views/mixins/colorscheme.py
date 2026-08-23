from typing import Any

from dzgui.const.constants import (
    GIO_SETTINGS_KEY,
    GIO_SETTINGS_INTERFACE,
    GIO_SETTINGS_PROP,
    GIO_SETTINGS_VAL,
)

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio  # noqa


class ColorAwareApp:
    """
    Polls the local theme's color scheme settings.
    Intended to be consumed by Gtk.Applications (or ephemeral widgets like EarlyAlertDialogs)
    on initialization, prior to being realized. Applying scheme changes too late in the chain
    may cause a blinking effect.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.interface_settings = Gio.Settings.new(GIO_SETTINGS_INTERFACE)
        self.interface_settings.connect(
            "changed::color-scheme", self._on_color_scheme_changed
        )
        self.default_settings = Gtk.Settings.get_default()
        self._on_color_scheme_changed(self.interface_settings, GIO_SETTINGS_PROP)

    def _on_color_scheme_changed(self, settings: Gio.Settings, prop: str) -> None:
        state = self.interface_settings.get_string(prop) == GIO_SETTINGS_VAL
        if self.default_settings is None:
            return
        self.default_settings.set_property(GIO_SETTINGS_KEY, state)
