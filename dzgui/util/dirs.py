import os
import shutil

from importlib import resources
from pathlib import Path

from dzgui.const.constants import APP_NAME_LOWER, IMAGES_PATH

def make_parents(path: "Path") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

def copy_dzgui_to_xdg_data(exe_path: Path) -> None:
    dzgui = os.getenv("PYAPP")
    if dzgui is None:
        return
    make_parents(exe_path)
    shutil.copy(dzgui, exe_path)

def find_icon_resource() -> "Path":
    traversable = resources.files(APP_NAME_LOWER).joinpath(IMAGES_PATH)
    images = Path(str(traversable))
    icon = images.joinpath("icon.png")
    return icon
