from dzgui.util.strings import refresh
from dzgui.views.components.icon import Icon
from dzgui.const.constants import REFRESH_ICON, WEB_BROWSER, INPUT_KEYBOARD

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402


class IconButton(Gtk.Button):
    def __init__(self, icon: str, margin: int = 0) -> None:
        super().__init__()
        i = Icon(icon, l_margin=margin)
        self.set_image(i)
        self.set_image_position(Gtk.PositionType.RIGHT)

class IconTextButton(IconButton):
    def __init__(self, icon: str, label: str) -> None:
        super().__init__(icon, margin=5)
        self.set_label(label)


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
