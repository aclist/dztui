import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk  # noqa E402


def add_class(widget: Gtk.Widget, label: str) -> None:
    """
    Sets the classname of a widget, used
    to apply CSS styling later
    """
    context = widget.get_style_context()
    context.add_class(label)


def remove_class(widget: Gtk.Widget, label: str) -> None:
    context = widget.get_style_context()
    context.remove_class(label)


def load_css() -> None:
    # TODO: consider storing this in a data file
    css = """
    .invalid-entry {
        border-color: red;
    }
    .frame {
        border: 0px;
    }
    .toast-label {
        background-color: black;
        border: 1px solid white;
    }
    .frame > border {
        border-radius: 5px;
        padding: 5px;
    }
    .page-heading {
        font-size: 1.5rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
    }
    .settings-subheading {
        font-size: 1.2rem;
        font-weight: 700;
    }
    .left-label {
        font-size: 1.3rem;
    }
    .details-heading {
        font-size: 1.2rem
    }
    """
    prov = Gtk.CssProvider()
    prov.load_from_data(css.encode("ascii"))
    screen = Gdk.Screen.get_default()
    if screen:
        Gtk.StyleContext.add_provider_for_screen(
            screen, prov, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )
