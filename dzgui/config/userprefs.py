from dataclasses import dataclass
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from dzgui.config.xdg import Xdg
    from dzgui.util.ip import Coords


# NOTE: mutable dataclass, 'use_miles' key changes on demand
@dataclass(slots=True)
class UserPrefs:
    is_steam_deck: bool
    is_game_mode: bool
    is_debug: bool
    coords: Union["Coords", None]
    version: str
    paths: "Xdg"
    update_available: bool
    use_miles: bool
