from dzgui.const.enum import CursorPosition
from dzgui.const.constants import SEPARATOR
from dzgui.util.keys import is_ctrl_mask

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa E402


class CursorMixin:
    def _vim_nav(self, event: Gdk.EventKey):
        match event.keyval:
            case Gdk.KEY_g:
                self._move_cursor(CursorPosition.TOP)
            case Gdk.KEY_G:
                self._move_cursor(CursorPosition.BOTTOM)
            case Gdk.KEY_j:
                self._move_cursor(CursorPosition.DOWN)
            case Gdk.KEY_k:
                self._move_cursor(CursorPosition.UP)
            case Gdk.KEY_l | Gdk.KEY_Right:
                if is_ctrl_mask(event):
                    return
                self.emitter.emit("request_button_box_focus")  # type: ignore
            case _:
                return False

    def _move_cursor(self, position: CursorPosition) -> bool:
        cur_row = self.get_focused_row_index()  # type: ignore
        model = self.get_model()  # type: ignore
        if model:
            end = len(model) - 1
        else:
            return True

        if position == CursorPosition.DOWN:
            if cur_row == end:
                return True
            dest = cur_row + 1
            if model[dest][0] == SEPARATOR:
                dest += 1
        if position == CursorPosition.UP:
            if cur_row == 0:
                return True
            dest = cur_row - 1
            if model[dest][0] == "SEPARATOR":
                dest -= 1
        if position == CursorPosition.TOP:
            if cur_row == 0:
                return True
            dest = 0
        if position == CursorPosition.BOTTOM:
            if cur_row == end:
                return True
            dest = end

        path = Gtk.TreePath.new_from_indices([dest])
        self.set_cursor(path)  # type: ignore
        return True
