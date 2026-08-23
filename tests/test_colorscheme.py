import pytest
import subprocess

from dzgui.const.constants import GIO_SETTINGS_KEY
from dzgui.views.mixins.colorscheme import ColorAwareApp

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, GLib  # noqa


class TestWidget(ColorAwareApp, Gtk.Button):
    def __init__(self) -> None:
        super().__init__()

        self.state: bool

    def check_theme(self) -> None:
        self.state = self.get_settings().get_property(GIO_SETTINGS_KEY)
        Gtk.main_quit()


@pytest.fixture
def widget() -> TestWidget:
    return TestWidget()


@pytest.mark.integration
@pytest.mark.parametrize("key, expect", [("default", False), ("prefer-dark", True)])
def test_light_mode(widget, key: str, expect: bool) -> None:
    local_pref = subprocess.run(
        ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
        capture_output=True,
        text=True,
    ).stdout
    subprocess.run(
        [
            "gsettings",
            "set",
            "org.gnome.desktop.interface",
            "color-scheme",
            key,
        ],
    )

    # NOTE: allow changes to propagate
    GLib.idle_add(widget.check_theme)
    Gtk.main()
    subprocess.run(
        [
            "gsettings",
            "set",
            "org.gnome.desktop.interface",
            "color-scheme",
            local_pref,
        ]
    )
    assert widget.state is expect
