import re
import subprocess
from pathlib import Path

CPU_FILE = "/proc/cpuinfo"

def is_steam_deck() -> bool:
    # TODO: tests
    r = r"AMD Custom APU [0-9]{4}"
    with open(CPU_FILE, "r") as f:
        s = f.read()
        match = re.search(r, s)
        if match:
            if "0932" in match.group() or "0405" in match.group():
                return True
    return False


def is_game_mode() -> bool:
    proc = subprocess.run(
        ["/usr/bin/pgrep", "-a", "gamescope"],
        capture_output=True,
        text=True
    )
    if proc.returncode != 0:
        return False
    if "generate-drm-mode" in proc.stdout:
        return True
    else:
        return False
