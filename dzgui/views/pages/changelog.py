import logging
import re
import textwrap

from typing import TYPE_CHECKING
from importlib import resources

from dzgui.const.constants import APP_NAME, APP_NAME_LOWER, CHANGELOG_PATH
from dzgui.util.strings import missing_changelog
from dzgui.util.format import format_pango
from dzgui.views.components.box import HBox, VBox
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

        # FIXME: wrap long text
        self.controller = controller
        self.box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=5, margin_top=10
        )
        self.add(self.box)

        expand_all = Gtk.Button(
            label="Expand all", halign=Gtk.Align.START, margin_start=20
        )
        expand_all.connect("clicked", self._on_expand_all_clicked)
        self.box.add(expand_all)

        self.expanded = False
        self.expanders: list[Gtk.Expander] = []
        self.connect("key-press-event", self._on_keypress)
        self.connect("key-press-event", self._on_esc_keypress)

        changes = self._parse(changelog)
        self._generate_nodes(changes)

        self.show_all()

    def _on_expand_all_clicked(self, button: Gtk.Button) -> None:
        self.expanded = not self.expanded
        for expander in self.expanders:
            # NOTE: simply setting set_expanded() does not trigger activate() signal,
            # so margins are not applied
            if expander.get_expanded() == self.expanded:
                continue
            expander.activate()
        label = "Collapse all" if self.expanded else "Expand all"
        button.set_label(label)

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

            container = Gtk.Box(valign=Gtk.Align.START, halign=Gtk.Align.START)
            label = Gtk.Label()
            label.set_markup(formatted)
            container.add(label)

            version, date = self._parse_version(header)
            button_text = f"{version} ({date})"
            button = Gtk.Button(label=button_text, margin_start=5)

            expander = Gtk.Expander()
            expander.set_label_widget(button)
            expander.add(container)
            expander.connect("activate", self._on_expand, container)
            self.box.add(expander)
            self.expanders.append(expander)

    def _on_expand(self, expander: Gtk.Box, container: Gtk.Box) -> None:
        """
        Wayland/some themes do not expect widgets to have a size allocation until expanded.
        Trying to set margins a priori may cause negative allocation,
        as the margins are subtracted from zero. In effect, the widget is not realized
        until it is expanded for the first time.
        """
        container.set_margin_start(15)
        container.set_margin_top(15)
        container.set_margin_bottom(15)

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
            release_notes.append(textwrap.fill(line.rstrip(), width=120))
        return releases
