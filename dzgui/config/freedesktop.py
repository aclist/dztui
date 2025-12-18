import shutil
import textwrap
from pathlib import Path


def write_desktop_file(share_path: Path) -> None:
    template = f"""\
    [Desktop Entry]
    Version=1.0
    Type=Application
    Terminal=false
    Exec={share_path}/launch.sh
    Name=DZGUI
    Comment=dzgui
    Icon={share_path}/dzgui
    Categories=Game"""

    file = share_path / "dzgui.desktop"
    file.write_text(textwrap.dedent(template))


def write_shim_file(share_path: Path) -> None:
    # FIXME: expects sys.prefix to be a venv
    file = share_path / "launch.sh"
    template=f"""\
    source {venv}/bin/activate
    python3.13 dzgui
    """
    try:
        file.write_text(textwrap.dedent(template))
        file.chmod(file.stat().st_mode | stat.S_IEXEC)
    except OSError as e:
        logger.critical(e)
        return
    clear_old_path()
    write_desktop_file(share_path)


def clear_old_path() -> None:
    home = Path.home()
    path = home / ".local/share/dzgui"
    shutil.rmtree(path)
