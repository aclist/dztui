from pathlib import Path
from typing import Callable

import gi

from dzgui.api.steam import get_app_path, get_steam_paths
from dzgui.config.query import lookup
from dzgui.config.update import write_config
from dzgui.const.constants import APPID_DAYZ
from dzgui.const.enum import Preferences

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402


class SteamPathSelector(Gtk.Box):
    """Select and validate the Steam installation used to locate DayZ."""

    def __init__(self, changed: Callable[[bool], None], initial: str = "") -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.changed = changed
        self.valid_path = ""
        self.add(
            Gtk.Label(
                label="Choose the Steam installation folder containing steamapps/libraryfolders.vdf.\n"
                "DayZ must be installed in one of its libraries.",
                wrap=True,
            )
        )
        self.detected = Gtk.ComboBoxText()
        self.detected.connect("changed", self._on_detected)
        self.add(self.detected)
        scan = Gtk.Button(label="Scan for Steam")
        scan.connect("clicked", self._scan)
        self.add(scan)
        self.manual = Gtk.CheckButton(label="Choose a folder manually")
        self.manual.connect("toggled", self._on_manual)
        self.add(self.manual)
        self.entry = Gtk.Entry(hexpand=True)
        self.entry.connect("changed", self._validate)
        browse = Gtk.Button(label="Browse…")
        browse.connect("clicked", self._browse)
        self.manual_box = Gtk.Box(spacing=10)
        self.manual_box.add(self.entry)
        self.manual_box.add(browse)
        self.manual_box.set_sensitive(False)
        self.add(self.manual_box)
        self.status = Gtk.Label(wrap=True, selectable=True)
        self.add(self.status)
        if initial:
            self.manual.set_active(True)
            self.entry.set_text(initial)

    def _scan(self, button: Gtk.Button) -> None:
        self.detected.remove_all()
        for path, _description in get_steam_paths():
            self.detected.append_text(str(path))
        self.manual.set_active(False)
        self.detected.set_active(0)
        self._validate()

    def _on_detected(self, combo: Gtk.ComboBoxText) -> None:
        self._validate()

    def _on_manual(self, button: Gtk.CheckButton) -> None:
        self.manual_box.set_sensitive(button.get_active())
        self.detected.set_sensitive(not button.get_active())
        self._validate()

    def _browse(self, button: Gtk.Button) -> None:
        dialog = Gtk.FileChooserDialog(
            title="Choose Steam folder",
            transient_for=self.get_toplevel(),
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(
            "Cancel", Gtk.ResponseType.CANCEL, "Select", Gtk.ResponseType.OK
        )
        if dialog.run() == Gtk.ResponseType.OK:
            self.entry.set_text(dialog.get_filename() or "")
        dialog.destroy()

    def _validate(self, entry: Gtk.Entry | None = None) -> None:
        value = (
            self.entry.get_text()
            if self.manual.get_active()
            else self.detected.get_active_text() or ""
        ).strip()
        self.valid_path = ""
        try:
            if not value:
                raise ValueError("Scan for Steam or choose a folder manually.")
            path = Path(value).expanduser().resolve()
            library = get_app_path(path, APPID_DAYZ)
            self.valid_path = str(path)
            self.status.set_text(f"DayZ library found: {library}")
        except Exception as error:
            self.status.set_text(
                f"{error}\nSelect the Steam installation that contains DayZ."
            )
        self.changed(bool(self.valid_path))


class SteamPathDialog(Gtk.Dialog):
    def __init__(self, parent: Gtk.Window, config: Path) -> None:
        super().__init__(
            title="Reconfigure Steam / DayZ", transient_for=parent, modal=True
        )
        self.config = config
        self.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Save", Gtk.ResponseType.OK)
        self.set_response_sensitive(Gtk.ResponseType.OK, False)
        self.selector = SteamPathSelector(
            lambda valid: self.set_response_sensitive(Gtk.ResponseType.OK, valid),
            lookup(config, Preferences.DEFAULT) or "",
        )
        self.get_content_area().add(self.selector)
        self.set_default_size(650, 300)
        self.show_all()

    def save(self) -> bool:
        try:
            while self.run() == Gtk.ResponseType.OK:
                self.selector._validate()
                if not self.selector.valid_path:
                    continue
                try:
                    write_config(
                        self.config, Preferences.DEFAULT, self.selector.valid_path
                    )
                except Exception as error:
                    self.selector.status.set_text(
                        f"Could not save configuration: {error}"
                    )
                    continue
                return True
            return False
        finally:
            self.destroy()
