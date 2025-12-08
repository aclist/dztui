import fcntl
import os
import sys

from pathlib import Path
from typing import TextIO

from dzgui.views.dialogs.early_alert import EarlyAlertDialog
from dzgui.util.strings import cannot_acquire_lock


def lock_release(lock: TextIO) -> None:
    fcntl.flock(lock, fcntl.LOCK_UN)
    os.close(lock.fileno())


def lock_acquire() -> TextIO:
    lockfile = Path("/tmp/dzgui.flock")
    lock = open(lockfile, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        EarlyAlertDialog(cannot_acquire_lock)
        sys.exit(1)
    return lock
