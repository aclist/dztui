from datetime import datetime
from pathlib import Path


def is_writeable(path: "Path") -> bool:
    now = int(datetime.now().timestamp())
    suffix = ".dzgtmp"
    file = str(now) + suffix
    filepath = Path(str(path) + "_" + file)
    try:
        filepath.touch()
        filepath.unlink()
        return True
    except OSError:
        return False
