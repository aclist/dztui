import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk  # noqa E402

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
    if event.state is Gdk.ModifierType.CONTROL_MASK:
        return True
    else:
        return False

def is_filterkey(key: int) -> bool:
    keys = (
        Gdk.KEY_0,
        Gdk.KEY_1,
        Gdk.KEY_2,
        Gdk.KEY_3,
        Gdk.KEY_4,
        Gdk.KEY_5,
        Gdk.KEY_6,
        Gdk.KEY_7,
        Gdk.KEY_8,
        Gdk.KEY_9,
        Gdk.KEY_backslash,
        Gdk.KEY_minus,
    )
    if key in keys:
        return True
    return False
