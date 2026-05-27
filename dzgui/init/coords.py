import logging
from typing import TYPE_CHECKING

from dzgui.const.constants import APP_NAME
from dzgui.util.ip import get_local_ip, get_coords, Coords

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(APP_NAME)


def get_local_coords(path: "Path") -> Coords | None:
    try:
        my_ip = get_local_ip()
        return get_coords(path, my_ip)
    except Exception as e:
        logger.warn(e)
        return None
