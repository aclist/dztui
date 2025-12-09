import sys

from pathlib import Path
from dzgui.const.constants import LEGACY_CONFIG_PATH
from dzgui.config.convert import rc2json


def test_legacy_conf(config: Path) -> None:
    if config.exists() is True:
        return
    old_conf = Path.home() / LEGACY_CONFIG_PATH
    if old_conf.is_file():
        j = rc2json(old_conf)
        # FIXME: superfluous use of Path()
        Path(config).parent.mkdir(parents=True, exist_ok=True)
        config.write_text(j)
    else:
        print("Unimplemented. You must have a working dztuirc.")
        sys.exit(1)


def move_state_files(state_path: Path) -> None:
    home = Path.home()
    legacy = home / ".local/state/dzgui"
    if state_path == legacy:
        # TODO: log this
        return
    for file in legacy.iterdir():
        file.rename(state_path / file.name)


def move_ipdb(ips_path: Path) -> None:
    home = Path.home()
    name = "ips.csv"
    legacy = home / ".local/share/helpers/dzgui" / name
    if ips_path == legacy:
        return
    legacy.rename(ips_path)
