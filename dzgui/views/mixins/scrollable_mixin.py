from dzgui.const.enum import VAdjustment
from dzgui.const.constants import SCROLL_INCREMENT

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk  # noqa

class ScrollableMixin:
    def _set_adjustment(self, adjustment = VAdjustment) -> None:
        vadj = self.scrollable.get_vadjustment()
        match adjustment:
            case VAdjustment.TOP:
                adj = vadj.get_lower()
            case VAdjustment.BOTTOM:
                adj = vadj.get_upper()
            case VAdjustment.UP:
                adj = vadj.get_value() - SCROLL_INCREMENT
            case VAdjustment.DOWN:
                adj = vadj.get_value() + SCROLL_INCREMENT
        vadj.set_value(adj)

