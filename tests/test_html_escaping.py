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
    text = "<Server description> Game & mods"
    details = Details([["0", "1"]], text, True)
    controller = MockController()
    dialog = ServerDetailsDialog(controller, details)

    assert dialog.description.get_text() == text
