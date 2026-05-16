from dzgui.strings import options
from dzgui.const.constants import FLATPAK_RUN_CMD, FLATPAK_SANDBOX, STEAM_CMD

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa


class ClientCombo(Gtk.ComboBox):
    def __init__(self) -> None:
        super().__init__()

        self.client_store = Gtk.ListStore(str, str)
        clients = (
            (
                options.steam_combo,
                STEAM_CMD,
            ),
            (
                options.flatpak_combo,
                FLATPAK_RUN_CMD,
            ),
            (
                options.flatpak_container_combo,
                FLATPAK_SANDBOX,
            ),
        )
        for client in clients:
            self.client_store.append(client)
        self.set_model(self.client_store)  # Text()
        renderer_text = Gtk.CellRendererText()
        self.pack_start(renderer_text, True)
        self.add_attribute(renderer_text, "text", 0)
        self.set_active(0)
