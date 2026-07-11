import textwrap

from pathlib import Path

from dzgui.util.dirs import copy_dzgui_to_xdg_data, find_icon_resource, make_parents


def write_desktop_file(exe_path: Path) -> None:
    icon = find_icon_resource()

    template = f"""\
    [Desktop Entry]
    Version=1.0
    Type=Application
    Terminal=false
    Exec={exe_path}
    Name=DZGUI
    Comment=dzgui
    Icon={icon}
    Categories=Game"""

    copy_dzgui_to_xdg_data(exe_path)

    share_path = exe_path.parent.parent
    file = share_path.joinpath("applications/dzgui.desktop")
    make_parents(file)
    file.write_text(textwrap.dedent(template))


def write_desktop_shortcut(exe_path: Path) -> None:
    # TODO: symlink the above, /Desktop
    # TODO: dynamically link to prior option in UI
    pass
