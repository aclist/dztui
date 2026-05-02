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
