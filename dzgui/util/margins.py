import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402

def set_surrounding_margins(widget: Gtk.Widget, margin: int) -> None:
    """
    Utility function that sets all margins
    on a widget to a uniform integer value
    """
    widget.set_margin_top(margin)
    widget.set_margin_start(margin)
    widget.set_margin_end(margin)
