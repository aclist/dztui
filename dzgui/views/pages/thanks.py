from dzgui.util.format import format_pango
from dzgui.util.strings import thanks

import gi  # noqa E402
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

"""
Special thanks page recognizing contributors to the project in alpha-order
"""

# TODO: make scrollable, test long values/wrapping

class Thanks(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10
        )


        label = format_pango(thanks.header)
        header = Gtk.Label()
        header.set_markup(label)
        self.add(header)

        description = Gtk.Label(label=thanks.description)
        self.add(description)

        users = [f"- {user}" for user in sorted(thanks.users, key=str.lower)]
        pretty_users = "\n".join(users)
        body = Gtk.Label()
        body.set_markup(pretty_users)
        self.add(body)
