import fcntl
import os
import sys

from pathlib import Path
from typing import TextIO

from dzgui.const.constants import LOCK_FILE
from dzgui.util.strings import cannot_acquire_lock
from dzgui.views.dialogs.early_alert import EarlyAlertDialog


def lock_release(lock: TextIO) -> None:
    fcntl.flock(lock, fcntl.LOCK_UN)
    os.close(lock.fileno())


def lock_acquire() -> TextIO:
    lockfile = Path(LOCK_FILE)
    lock = open(lockfile, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        EarlyAlertDialog(cannot_acquire_lock)
        sys.exit(1)
    return lock
