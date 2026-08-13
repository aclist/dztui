import logging
import subprocess
import sys
import tempfile
import traceback

from pathlib import Path
from dzgui.const.constants import APP_NAME, VM_FILE, MIN_COUNT
from dzgui.util.bash import concat_bash_args
from dzgui.strings import map_count
from dzgui.views.dialogs.early_alert import EarlyIgnoreDialog

logger = logging.getLogger(APP_NAME)


def is_map_count_valid(count: int | None) -> bool:
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
    count = get_map_count()
    if is_map_count_valid(count):
        return
    msg = map_count.exit_msg
    EarlyIgnoreDialog(msg)


def set_map_count() -> None:
    count = get_map_count()
    valid = is_map_count_valid(count)
    if count is None:
        print(map_count.failed_to_parse)
        return
    elif valid:
        msg = map_count.meets_minimum.format(count)
        print(msg)
        return

    conf = "/etc/sysctl.d/dayz.conf"
    count = f"vm.max_map_count={MIN_COUNT}"
    try:
        1/0
        msg = map_count.prompt.format(conf)
        print(msg)
        with tempfile.NamedTemporaryFile(delete=False) as f:
            tmp = f.name
        Path(tmp).write_text(count)

        mv_cmd = f"sudo mv {tmp} {conf}"
        reload_cmd = f"sudo sysctl -p {conf}"
        for cmd in mv_cmd, reload_cmd:
            args = concat_bash_args(cmd)
            subprocess.run([*args])
    except Exception as e:
        logger.debug(e)
        trace = traceback.format_exc()
        print(map_count.failed_to_update.format(trace))
    except KeyboardInterrupt:
        print(map_count.user_exit)
        sys.exit(0)
