import shutil
import subprocess

from pathlib import Path

"""
Find possible locations of default steam path
"""

def get_steam_dirs() -> list[Path]:
    dirs = []
    # pass 1
    if shutil.which("locate") is not None:
        # TODO: config or steamapps path? cf. LIBRARYFOLDERS_PATH
        proc = subprocess.run(
            ["/usr/bin/locate", "Steam/config/libraryfolders.vdf"],
            capture_output=True,
            text=True
        )

        if proc.returncode == 0:
            for d in proc.stdout.splitlines():
                dirs.append(Path(d))
            return dirs

    # pass 2
    for d in Path.home().rglob("Steam/config/libraryfolders.vdf"):
        dirs.append(d)

    # pass 3
    # if still nothing, let them select it
    # prompt what the dir should look like
    if len(dirs) == 0:
        print("none found")
    return dirs


dirs = get_steam_dirs()
print(dirs)

# TODO: present these in a group of radio buttons
"""
when user toggles radio button, updates text saying
"this is the standard steam location on debian" etc.

if None or if not satisfied, pop a filepicker and choose
if selection was custom, it has to have a libraryfolders.vdf
keeps next button grayed out until requirements are satisfied

Cancel      Next
"""
