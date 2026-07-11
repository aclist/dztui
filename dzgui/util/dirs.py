import logging
import os
import shutil

from importlib import resources
from pathlib import Path

from dzgui.const.constants import APP_NAME_LOWER, IMAGES_PATH

logger = logging.getLogger(APP_NAME)


def make_parents(path: "Path") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def copy_dzgui_to_xdg_data(exe_path: Path) -> None:
    dzgui = os.getenv("PYAPP")
    if dzgui is None:
        return
    try:
        make_parents(exe_path)
        shutil.copy(dzgui, exe_path)
    except Exception as e:
        logger.critical(e)


def find_icon_resource() -> "Path":
    traversable = resources.files(APP_NAME_LOWER).joinpath(IMAGES_PATH)
    images = Path(str(traversable))
    icon = images.joinpath("icon.png")
    return icon
