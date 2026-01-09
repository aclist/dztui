from dataclasses import dataclass
from dzgui.config.xdg import Xdg
from dzgui.util.ip import Coords

@dataclass(slots=True, frozen=True)
class UserPrefs:
    is_steam_deck: bool
    is_game_mode: bool
    is_developer: bool
    coords: Coords | None
    version: str
    allow_updates: bool
    paths: Xdg
