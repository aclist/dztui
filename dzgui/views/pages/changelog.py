import logging

from typing import TYPE_CHECKING
from importlib import resources

from dzgui.const.constants import APP_NAME, APP_NAME_LOWER, CHANGELOG_PATH
from dzgui.util.strings import missing_changelog
from dzgui.util.format import format_pango
from dzgui.views.mixins.help_menu_mixin import HelpMenuMixin
from dzgui.views.mixins.scrollable_mixin import ScrollableMixin

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402

logger = logging.getLogger(APP_NAME)

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller


class Changelog(HelpMenuMixin, ScrollableMixin, Gtk.ScrolledWindow):  # type: ignore
    def __init__(self, controller: "Controller"):
        super().__init__(propagate_natural_width=False)

        try:
            changelog = resources.read_text(APP_NAME_LOWER, CHANGELOG_PATH)
        except OSError as e:
            logger.critical(e)
            changelog = missing_changelog

        # TODO: should long text be wrapped?
        self.controller = controller
        formatted = format_pango(changelog)
        self.changelog_label = Gtk.Label(valign=Gtk.Align.START, margin=15)
        self.changelog_label.set_markup(formatted)
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box.add(self.changelog_label)
        self.add(self.box)

        self.connect("key-press-event", self._on_keypress)
        self.connect("key-press-event", self._on_esc_keypress)

    def grab_content_area(self) -> None:
        self.grab_focus()
