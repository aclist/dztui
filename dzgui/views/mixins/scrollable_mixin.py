from dzgui.const.enum import VAdjustment
from dzgui.const.constants import SCROLL_INCREMENT

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk  # noqa


class ScrollableMixin:
    def _on_keypress(self, widget: Gtk.Widget, event: Gdk.EventKey) -> bool:
        match event.keyval:
            case Gdk.KEY_k | Gdk.KEY_Up:
                self._set_adjustment(VAdjustment.UP)
                return True
            case Gdk.KEY_Down | Gdk.KEY_j:
                self._set_adjustment(VAdjustment.DOWN)
                return True
            case Gdk.KEY_g:
                self._set_adjustment(VAdjustment.TOP)
                return True
            case Gdk.KEY_G:
                self._set_adjustment(VAdjustment.BOTTOM)
                return True
            case Gdk.KEY_l | Gdk.KEY_Right:
                self.controller.get_emitter().emit("request_button_box_focus")  # type: ignore
                return True
            case _:
                return False

    def _set_adjustment(self, adjustment: VAdjustment) -> None:
        vadj = self.get_vadjustment()  # type: ignore
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
