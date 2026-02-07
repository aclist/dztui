from typing import Union, TYPE_CHECKING

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GObject  # noqa E402

if TYPE_CHECKING:
    from dzgui.const.enum import NotebookPage, ServerTab

# TODO: rename signals to e.g. maps_keybinding_pressed

class Emitter(GObject.GObject):
    def __init__(self) -> None:
        super().__init__()

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=())
    def request_keyword_focus(self) -> None:
        """User invoked Ctrl-f keybinding from ServerTreeView"""
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
    def request_lan_entry_focus(self) -> None:
        """User invoked Ctrl-p keybinding from ServerTreeView"""
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=())
    def request_button_box_focus(self) -> None:
        """User invoked right movement keybinding from ServerTreeView"""
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(int,))
    def check_button_pressed(self, keyval: int) -> None:
        """User toggled filter panel check button via keyboard"""

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

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(object,))
    def servers_loaded(self, tag: "ServerTab") -> None:
        pass

    @GObject.Signal(
        flags=GObject.SignalFlags.RUN_LAST,
        arg_types=(
            object,
            object,
        ),
    )
    def distcalc_ended(
        self, dist: Union[str, None], context: Union["ServerTab", "NotebookPage"]
    ) -> None:
        pass
