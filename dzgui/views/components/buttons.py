from typing import Callable, Self, TYPE_CHECKING

from dzgui.util.strings import refresh, connect_panel
from dzgui.const.constants import (
    CLIPBOARD,
    INPUT_KEYBOARD,
    LIST_ADD,
    REFRESH_ICON,
    STEAM_ICON,
    WEB_BROWSER,
)

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller


class Icon(Gtk.Image):
    def __init__(self, name: str, l_margin=0) -> None:
        super().__init__(icon_name=name,
            icon_size=Gtk.IconSize.BUTTON,
            margin_start=l_margin,
            ypad=2,
        )

class LargeIcon(Gtk.Image):
    def __init__(self, name: str, l_margin=5) -> None:
        super().__init__(icon_name=name,
            icon_size=Gtk.IconSize.LARGE_TOOLBAR,
            margin_start=l_margin
        )


class IconButton(Gtk.Button):
    def __init__(self, icon: str, margin: int = 0) -> None:
        super().__init__()
        self.icon = Icon(icon, l_margin=margin)
        self.set_image(self.icon)
        self.set_image_position(Gtk.PositionType.RIGHT)


class IconTextButton(IconButton):
    def __init__(self, icon: str, label: str) -> None:
        super().__init__(icon, margin=5)
        self.set_label(label)


class LargeIconTextButton(IconButton):
    def __init__(self, icon: str, label: str) -> None:
        super().__init__(icon)

        self.set_label(label)
        self.set_image(LargeIcon(icon))


class ClipboardButton(IconButton):
    def __init__(self, controller: "Controller", data: str) -> None:
        super().__init__(CLIPBOARD)
        self.controller = controller
        self.connect("clicked", self._on_button_clicked, data)

    def _on_button_clicked(self, button: Self, data: str) -> None:
        self.controller.copy_clipboard(data)


class WebButton(IconTextButton):
    def __init__(self, label: str) -> None:
        super().__init__(icon=WEB_BROWSER, label=label)
        pass


class RefreshButton(IconTextButton):
    def __init__(self) -> None:
        super().__init__(icon=REFRESH_ICON, label=refresh)
        self.set_margin_top(10)
        self.set_margin_start(80)
        self.set_margin_end(80)


class KeysButton(IconTextButton):
    def __init__(self, label: str) -> None:
        super().__init__(icon=INPUT_KEYBOARD, label=label)
        self.set_margin_top(10)
        self.set_margin_start(80)
        self.set_margin_end(80)


class SteamConnectButton(LargeIconTextButton):
    def __init__(self) -> None:
        super().__init__(icon=STEAM_ICON, label=connect_panel.connect)
        self.set_tooltip_text(connect_panel.connect_tooltip)


class SteamTextButton(SteamConnectButton):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.set_label(label)


class AddButton(IconTextButton):
    def __init__(self) -> None:
        super().__init__(icon=LIST_ADD, label=connect_panel.add)
        self.set_tooltip_text(connect_panel.add_tooltip)
