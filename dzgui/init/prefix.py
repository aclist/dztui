import os
import sys

from importlib import metadata
from pathlib import Path

from dzgui.const.constants import APP_NAME_LOWER

def is_prefix_writeable() -> bool:
    prefix = sys.prefix
    path = Path(prefix)
    file = path / ".is_writeable"
    try:
        with open(file, "w") as f:
            f.write("")
        os.remove(file)
    except OSError:
        return False
    return True


def get_version() -> str:
    return metadata.version(APP_NAME_LOWER)
