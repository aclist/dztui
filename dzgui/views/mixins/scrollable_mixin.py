from dzgui.const.enum import VAdjustment
from dzgui.const.constants import SCROLL_INCREMENT

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk  # noqa

class ScrollableMixin:
    def _on_keypress(self, widget: Gtk.Widget, event: Gdk.EventKey) -> None:
        match event.keyval:
            case Gdk.KEY_k | Gdk.KEY_Up:
                self._set_adjustment(VAdjustment.UP)
            case Gdk.KEY_Down | Gdk.KEY_j:
                self._set_adjustment(VAdjustment.DOWN)
            case Gdk.KEY_g:
                self._set_adjustment(VAdjustment.TOP)
            case Gdk.KEY_G:
                self._set_adjustment(VAdjustment.BOTTOM)

    def _set_adjustment(self, adjustment: VAdjustment) -> None:
        vadj = self.get_vadjustment()
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

