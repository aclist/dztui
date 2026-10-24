import shlex

from dzgui.const.constants import STEAM_CMD
from dzgui.init.proc import is_sandboxed


def concat_bash_args(command: str) -> list[str]:
    # NOTE: NSGs spawned from sandbox cannot access host application commands,
    # so fallback to Steam internal URIs
    if is_sandboxed():
        return [STEAM_CMD]
    return shlex.split(command)
