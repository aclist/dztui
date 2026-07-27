import stat
import textwrap

from pathlib import Path

from dzgui.const.constants import APP_NAME
from dzgui.util.dirs import copy_dzgui_to_xdg_data, find_icon_resource, make_parents


def get_share_path(exe_path: Path) -> Path:
    return exe_path.parent.parent


def write_desktop_file(exe_path: Path) -> Path:
    icon = find_icon_resource()

    template = f"""\
    [Desktop Entry]
    Version=1.0
    Type=Application
    Terminal=false
    Exec={exe_path}
    Name=DZGUI
    Comment=DayZ server browser and mod manager
    Icon={icon}
    Categories=Game"""

    copy_dzgui_to_xdg_data(exe_path)

    share_path = get_share_path(exe_path)
    desktop_file = share_path.joinpath("applications/dzgui.desktop")
    make_parents(desktop_file)
    desktop_file.write_text(textwrap.dedent(template))
    desktop_file.chmod(desktop_file.stat().st_mode | stat.S_IEXEC)
    return desktop_file


def write_desktop_shortcut(desktop_file: Path) -> None:
    # NOTE: necessarily depends on the above (UI blocks creation without XDG entry first)
    link = Path.home().joinpath(f"Desktop/dzgui.desktop")
    make_parents(link)
    if link.exists():
        link.unlink()
    link.symlink_to(desktop_file)
