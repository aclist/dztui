import gi  # noqa E402
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk

def is_navkey(key: int) -> bool:
    nav_keys = [
        Gdk.KEY_Down,
        Gdk.KEY_Up,
        Gdk.KEY_Right,
        Gdk.KEY_Page_Down,
        Gdk.KEY_Page_Up,
        Gdk.KEY_j,
        Gdk.KEY_k,
        Gdk.KEY_g,
        Gdk.KEY_G,
    ]
    if key in nav_keys:
        return True
    return False

def is_ctrl_mask(event: Gdk.EventKey) -> bool:
    if event.keyval is Gdk.KEY_l \
        and event.state is Gdk.ModifierType.CONTROL_MASK:
            return True
    else:
        return False
