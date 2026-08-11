import subprocess
import sys
import tempfile

from pathlib import Path
from dzgui.const.constants import VM_FILE, MIN_COUNT
from dzgui.util.bash import concat_bash_args
from dzgui.views.dialogs.early_alert import EarlyIgnoreDialog


def is_map_count_valid() -> bool:
    count = get_map_count()
    if count is None:
        # NOTE: permit if count was unreadable
        return True
    return count >= MIN_COUNT


def get_map_count() -> int | None:
    path = Path(VM_FILE)
    if path.is_file() is False:
        return None
    count = int(path.read_text())
    return count


def test_map_count() -> None:
    if is_map_count_valid():
        return
    msg = (
        "System map count is not high enough to run DayZ.\n"
        "Please exit and run 'dzgui -m' to update map count."
    )
    EarlyIgnoreDialog(msg)


def set_map_count() -> None:
    valid = is_map_count_valid()
    if valid is None:
        return
    elif valid:
        print("System map count already meets the minimum.")
        return

    conf = "/etc/sysctl.d/dayz.conf"
    count = f"vm.max_map_count={MIN_COUNT}"
    try:
        msg = (
            f"Updated map count will be written to the file '{conf}'.\n"
            "Enter sudo password to proceed."
        )
        print(msg)
        with tempfile.NamedTemporaryFile(delete=False) as f:
            tmp = f.name
        Path(tmp).write_text(count)
        args = concat_bash_args(f"sudo mv {tmp} {conf}")
        subprocess.run([*args])
        args = concat_bash_args(f"sudo sysctl -p {conf}")
        subprocess.run([*args])
    except Exception as e:
        print(e)
    except KeyboardInterrupt:
        print("User exit")
        sys.exit(0)
