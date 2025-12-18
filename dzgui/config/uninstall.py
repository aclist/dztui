import shutil
from pathlib import Path

def uninstall(path: Path) -> None:
    pass
    # TODO: use xdg object?
    # partial/full (keep config?)
    # -u removes state, log
    # XDG_SHARE_HOME/dzgui
    # XDG_STATE_HOME/dzgui
    # XDG_DATA_HOME/dzgui
