from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "3.0")
from gi.repository.Gtk import ListStore  # noqa E402
from gi.repository import Gdk, GObject  # noqa E402

if TYPE_CHECKING:
    from dzgui.const.enum import NotebookPage, ServerTab

# TODO: rename signals to e.g. maps_keybinding_pressed


class Emitter(GObject.GObject):
    def __init__(self) -> None:
        super().__init__()

    # TODO: rename request verbs
    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=())
    def request_keyword_focus(self) -> None:
        """User invoked Ctrl-f keybinding from ServerTreeView"""
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=())
    def saved_servers_changed(self) -> None:
        """Record was added/removed from Saved Servers model"""
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=())
    def request_maps_focus(self) -> None:
        """User invoked Ctrl-m keybinding from ServerTreeView"""
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=())
    def request_ip_entry_focus(self) -> None:
        """User invoked Ctrl-i keybinding from ServerTreeView"""
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=())
    def request_custom_port_focus(self) -> None:
        """User invoked Ctrl-n keybinding from ServerTreeView"""
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=())
    def request_default_port_focus(self) -> None:
        """user invoked ctrl-d keybinding from servertreeview"""
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=())
    def request_button_box_focus(self) -> None:
        """User invoked right movement keybinding from ServerTreeView"""
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(str, str))
    def fav_server_changed(self, name: str, addr: str) -> None:
        """Change favorite server via context menu"""

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(int,))
    def check_button_pressed(self, keyval: int) -> None:
        """User toggled filter panel check button via keyboard"""

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(object,))
    def server_page_changed(self, keyval: int) -> None:
        """Triggered on 'switch-page' signal within tabs of NotebookPage.SERVERS."""
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(bool,))
    def server_page_toggled(self, keyval: int) -> None:
        """Triggered on map/unmap signal from NotebookPage.SERVERS. Shows/hides grid panels."""
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=())
    def statusbar_loaded(self) -> None:
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=())
    def distcalc_started(self) -> None:
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(bool,))
    def mod_page_toggled(self, state: bool) -> None:
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(bool,))
    def lan_tab_toggled(self, state: bool) -> None:
        pass

    @GObject.Signal(
        flags=GObject.SignalFlags.RUN_LAST,
        arg_types=(
            object,
            object,
        ),
    )
    def distcalc_ended(
        self, dist: str | None, context: "ServerTab | NotebookPage"
    ) -> None:
        pass

    @GObject.Signal(
        flags=GObject.SignalFlags.RUN_LAST,
        arg_types=(
            str,
            bool,
        ),
    )
    def check_toggled(self, label: str, state: bool) -> None:
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(object,))
    def servers_loaded(self, tag: "ServerTab") -> None:
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=())
    def servers_loaded_init(self) -> None:
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(str,))
    def map_selection_changed(self, map: str) -> None:
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(object,))
    def load_maps(self, store: ListStore) -> None:
        pass

    @GObject.Signal(
        flags=GObject.SignalFlags.RUN_LAST,
        arg_types=(
            str,
            int,
        ),
    )
    def mods_updated(self, msg: str, mods: int) -> None:
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=())
    def mods_highlighted(self) -> None:
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=())
    def api_change_failed(self) -> None:
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=())
    def already_saved_server(self) -> None:
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(str,))
    def keyword_set(self, keyword: str) -> None:
        pass

    # TODO: if servers fail to load, may leave dangling widgets waiting for a signal
