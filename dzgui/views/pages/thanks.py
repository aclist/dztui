from typing import TYPE_CHECKING

from dzgui.util.format import format_pango
from dzgui.util.strings import thanks
from dzgui.views.mixins.help_menu_mixin import HelpMenuMixin
from dzgui.views.mixins.scrollable_mixin import ScrollableMixin

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402

# TODO: wrap and center long values
if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller


class Thanks(HelpMenuMixin, ScrollableMixin, Gtk.ScrolledWindow):  # type: ignore
    """
    Special thanks page recognizing contributors to the project in alpha-order
    """

    def __init__(self, controller: "Controller") -> None:
        super().__init__()

        self.controller = controller
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        label = format_pango(thanks.header)
        header = Gtk.Label()
        header.set_markup(label)

        description = Gtk.Label(
            label=thanks.description, justify=Gtk.Justification.CENTER
        )

        users = [f"- {user}" for user in sorted(thanks.users, key=str.lower)]
        pretty_users = "\n".join(users)
        body = Gtk.Label()
        body.set_markup(pretty_users)

        for el in header, description, body:
            self.box.add(el)
        self.add(self.box)

        self.connect("key-press-event", self._on_keypress)
        self.connect("key-press-event", self._on_esc_keypress)
    
    def grab_content_area(self) -> None:
        self.grab_focus()
