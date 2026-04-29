import json
import logging

from typing import TYPE_CHECKING

from dzgui.const.constants import APP_NAME
from dzgui.util._json import read_json

import gi

gi.require_version("Gtk", "3.0")

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller
    from pathlib import Path

logger = logging.getLogger(APP_NAME)


class NoteManager:
    def __init__(self, controller: "Controller", path: "Path") -> None:
        self.notes_path = path
        self.cache: dict[str, str] = read_json(self.notes_path)

    def add_note(self, server: str, note: str) -> None:
        self.cache[server] = note
        self.write_file()

    def delete_note(self, server: str) -> None:
        del self.cache[server]
        self.write_file()

    def get_note(self, server: str) -> str:
        try:
            text = self.cache[server]
            return text
        except Exception:
            return ""

    def write_file(self) -> None:
        j = json.dumps(self.cache, indent=2)
        self.notes_path.write_text(j)
