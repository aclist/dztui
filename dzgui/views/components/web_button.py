from dzgui.views.components.icon import Icon
from dzgui.const.constants import WEB_BROWSER

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402

# TODO: abstract to support other icons
class WebButton(Gtk.Button):
    def __init__(self, label: str):
        super().__init__(label=label)

        icon = Icon(WEB_BROWSER, l_margin=5)
        self.set_image(icon)
        self.set_image_position(Gtk.PositionType.RIGHT)
