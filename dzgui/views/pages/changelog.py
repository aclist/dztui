import logging
import re

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
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5, margin_top=10)
        self.add(self.box)

        self.connect("key-press-event", self._on_keypress)
        self.connect("key-press-event", self._on_esc_keypress)

        changes = self._parse(changelog)
        self._generate_nodes(changes)
        self.show_all()

    def grab_content_area(self) -> None:
        self.grab_focus()

    def _parse_version(self, version: str) -> tuple[str, str]:
        pattern = r"(^##\s\[)(.+)(\] )(.+$)"
        match = re.match(pattern, version)
        if match:
            version = match.group(2)
            date = match.group(4)
            return version, date
        raise ValueError("Changelog parse error")


    def _generate_nodes(self, releases: list[tuple[str, list[str]]]) -> None:
        for header, changes in releases:
            for ind in (0, -1):
                if changes[ind] == "":
                    del changes[ind]
            text = "\n".join(changes)
            formatted = format_pango(text)

            label = Gtk.Label(valign=Gtk.Align.START, margin=15, halign=Gtk.Align.START)
            label.set_markup(formatted)

            version, date = self._parse_version(header)
            button_text = f"{version} ({date})"
            button = Gtk.Button(label=button_text, margin_start=5)

            expander = Gtk.Expander()
            expander.set_label_widget(button)
            expander.add(label)
            self.box.add(expander)


    def _parse(self, changelog: str) -> list[tuple[str, list[str]]]:
        release = ""
        releases: list[tuple[str, list[str]]] = []
        release_notes: list[str] = []
        for line in changelog.splitlines():
            if line.startswith("# "):
                continue
            if line.startswith("## "):
                if release != "":
                    releases.append((release, release_notes))
                    release_notes = []
                    release = ""
                release = line
                continue
            release_notes.append(line.rstrip())
        return releases
