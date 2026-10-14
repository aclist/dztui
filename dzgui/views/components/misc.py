from dzgui.const.constants import ERROR, FLATPAK_RUN_CMD, FLATPAK_SANDBOX, STEAM_CMD
from dzgui.strings import options
from dzgui.views.components.box import HBox
from dzgui.views.components.buttons import Icon

from typing import Self
from dzgui.init.prereqs import has_steam_client, has_flatpak_client

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa


class ClientCombo(Gtk.ComboBox):
    def __init__(self) -> None:
        super().__init__()

        has_steam = has_steam_client()
        has_flatpak = has_flatpak_client()
        self.client_store = Gtk.ListStore(str, str, bool)
        self.clients = (
            (
                options.steam_combo,
                STEAM_CMD,
                has_steam,
            ),
            (
                options.flatpak_combo,
                FLATPAK_RUN_CMD,
                has_flatpak,
            ),
            (
                options.flatpak_container_combo,
                FLATPAK_SANDBOX,
                has_flatpak,
            ),
        )
        for client in self.clients:
            self.client_store.append(client)

        self.set_model(self.client_store)
        renderer_text = Gtk.CellRendererText()
        self.pack_start(renderer_text, True)
        self.add_attribute(renderer_text, "text", 0)
        self.set_active(0)

        self.set_cell_data_func(self.get_cells()[0], self.data_func)

    def data_func(
        self,
        combo: Self,
        cell: Gtk.CellRendererText,
        model: Gtk.ListStore,
        _iter: Gtk.TreeIter,
    ) -> None:
        sens = model[_iter][2]
        cell.set_property("sensitive", sens)

    def get_client_human_readable(self, cmd: str) -> str:
        for client in self.clients:
            human, command, sens = client
            if command == cmd:
                return human
        raise TypeError("Not a valid Steam client selection")


class ErrorPopover(Gtk.Popover):
    def __init__(self, relative_to: Gtk.Widget, position: Gtk.PositionType) -> None:
        super().__init__(relative_to=relative_to, position=position)

        self.hbox = HBox()
        self.label = Gtk.Label(label="", margin_start=10, margin_end=10)
        error_icon = Icon(ERROR, margin_start=10)
        self.hbox.extend([error_icon, self.label])
        self.add(self.hbox)
        self.show_all()
        self.popdown()

    def set_label(self, label: str) -> None:
        self.label.set_label(label)
