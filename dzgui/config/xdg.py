import os

from pathlib import Path
from dataclasses import dataclass

from dzgui.const.constants import APP_NAME_LOWER, DEBUG_LOG, SYSTEM_LOG


@dataclass
class Xdg:
    config: Path
    columns: Path
    notes: Path
    resolution: Path
    history: Path
    version: Path
    system: Path
    debug: Path
    ips: Path
    filters: Path
    shortcut: Path


def is_writeable(path_str: str) -> bool:
    if path_str is None:
        return False

    path = Path(path_str)

    if not path.exists():
        try:
            path.mkdir(parents=True)
            path.unlink()
        except OSError:
            return False
        return True

    try:
        file = Path(path / "temp")
        with open(file, "w") as f:
            f.write("")
    except Exception:
        return False
    file.unlink()
    return True


def get_xdg_paths() -> dict:
    home = Path.home()
    xdg_paths = {
        "XDG_CONFIG_HOME": home / ".config",
        "XDG_STATE_HOME": home / ".local" / "state",
        "XDG_DATA_HOME": home / ".local" / "share",
        "XDG_CACHE_HOME": home / ".cache",
    }

    resolved_paths = {}
    for path in xdg_paths:
        real_path = os.environ.get(path)
        if real_path is not None and is_writeable(real_path):
            new_path = Path(real_path)
        else:
            new_path = xdg_paths[path]
        resolved_paths[path] = new_path / APP_NAME_LOWER
    return resolved_paths


def parse_filepaths(xdg: dict) -> Xdg:
    config = xdg["XDG_CONFIG_HOME"]
    state = xdg["XDG_STATE_HOME"]
    share = xdg["XDG_DATA_HOME"]

    config = config / "config.json"

    system = state / "logs" / SYSTEM_LOG
    debug = state / "logs" / DEBUG_LOG

    columns = state / "dzg.columns.json"
    notes = state / "dzg.notes.json"
    resolution = state / "dzg.res.json"
    history = state / "dzg.history"
    versions = state / "dzg.versions"
    ips = state / "ips.csv"
    filters = state / "dzg.filters.json"

    shortcut = share / APP_NAME_LOWER

    return Xdg(
        config,
        columns,
        notes,
        resolution,
        history,
        versions,
        system,
        debug,
        ips,
        filters,
        shortcut,
    )
