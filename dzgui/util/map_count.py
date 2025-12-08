import subprocess

from pathlib import Path
from dzgui.const.constants import VM_FILE, MIN_COUNT

def get_map_count() -> int | None:
    path = Path(VM_FILE)
    if path.is_file() is False:
        return None
    count = int(path.read_text())
    return count

    # TODO: unfinished
    #if count < MIN_COUNT:
    #    print("needs sudo escalation")
    #    # pop prompt
    #    # get response
    #    set_map_count()
    #return count

# TODO: unfinished
def set_map_count() -> None:
    conf = "/etc/sysctl.d/dayz.conf"
    count = f"vm.max_map_count={MIN_COUNT}"
    with open(conf, "w") as f:
        f.write(count)
    # TODO: use concat_bash_args()
    subprocess.run(["/usr/bin/sudo", "sysctl", "-p", conf])
