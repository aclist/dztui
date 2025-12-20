import logging

from typing import TYPE_CHECKING
from importlib import resources

from dzgui.const.constants import APP_NAME_LOWER
from dzgui.util.format import format_pango

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller

class Changelog(Gtk.Box):
    def __init__(self, controller: "Controller"):
        super().__init__()

        try:
            changelog = resources.read_text(APP_NAME_LOWER, "data/CHANGELOG.md")
        except OSError as e:
            logger.critical(e)
            changelog = "Error: Failed to read changelog"

        # TODO: should long text be wrapped?
        formatted = format_pango(changelog)
        self.changelog_label = Gtk.Label(valign=Gtk.Align.START, margin=15)
        self.changelog_label.set_markup(formatted)
        self.add(self.changelog_label)
