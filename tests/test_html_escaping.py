from dzgui.api.servers import Details
from dzgui.views.dialogs.servers import ServerDetailsDialog

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402


class MockController:
    def __init__(self) -> None:
        self.window = Gtk.Window()

    def get_window(self) -> Gtk.Window:
        return self.window

    def get_server_name(self) -> str:
        return "My server"

    def get_emitter(self) -> None:
        return None


def test_html_escaping() -> None:
    name = "Test server"
    desc = "<Server description> Game & mods"
    gametime = "05:30"
    day_accel = 5.0
    night_accel = 1.0
    details = Details([["0", "1"]], name, desc, gametime, day_accel, night_accel)
    controller = MockController()
    dialog = ServerDetailsDialog(controller, details)
    dialog.destroy()

    assert dialog.description.get_text() == desc
