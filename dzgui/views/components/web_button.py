from dzgui.views.components.icon import Icon
from dzgui.const.constants import REFRESH_ICON, WEB_BROWSER

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402


class IconButton(Gtk.Button):
    def __init__(self, icon: str, margin: int = 0):
        super().__init__()

        i = Icon(icon, l_margin=margin)
        self.set_image(i)
        self.set_image_position(Gtk.PositionType.RIGHT)


class IconTextButton(IconButton):
    def __init__(self, icon: str, label: str):
        super().__init__(icon, margin=5)

        self.set_label(label)


class WebButton(IconTextButton):
    def __init__(self, label: str):
        super().__init__(icon=WEB_BROWSER, label=label)
        pass


class RefreshButton(IconTextButton):
    def __init__(self, label: str):
        super().__init__(icon=REFRESH_ICON, label=label)
        pass
