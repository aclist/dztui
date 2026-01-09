from dzgui.util.format import format_pango
from dzgui.util.strings import thanks
from dzgui.views.mixins.scrollable_mixin import ScrollableMixin

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402

# TODO: wrap and center long values

class Thanks(ScrollableMixin, Gtk.ScrolledWindow):  # type: ignore
    """
    Special thanks page recognizing contributors to the project in alpha-order
    """
    def __init__(self) -> None:
        super().__init__()

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        label = format_pango(thanks.header)
        header = Gtk.Label()
        header.set_markup(label)

        description = Gtk.Label(label=thanks.description, justify=Gtk.Justification.CENTER)

        users = [f"- {user}" for user in sorted(thanks.users, key=str.lower)]
        pretty_users = "\n".join(users)
        body = Gtk.Label()
        body.set_markup(pretty_users)

        for el in header, description, body:
            self.box.add(el)
        self.add(self.box)

        self.connect("key-press-event", self._on_keypress)
