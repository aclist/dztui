import logging
import requests
import subprocess
import sys

from importlib import resources
from packaging.version import Version, InvalidVersion

from dzgui.const.constants import APP_NAME_LOWER, REQUEST_TIMEOUT
from dzgui.const.endpoints import GITHUB_RELEASES, CODEBERG_RELEASES
from dzgui.init.prefix import is_prefix_writeable

logger = logging.getLogger(__name__)

def get_latest_release() -> str | None:
    tag = None
    for url in [GITHUB_RELEASES, CODEBERG_RELEASES]:
        try:
            res = requests.get(url, timeout=REQUEST_TIMEOUT)
            if res.status_code == 200:
                tag = res.json()["tag_name"]
                break
        except Exception as e:
            logger.critical(e)
            continue
    return tag

def allow_updates(allow: bool) -> bool:
    if allow is False:
        return False
    if allow is True:
        return is_prefix_writeable()

def check_updates(version: str) -> None:
    latest = get_latest_release()
    prefix = sys.prefix
    if latest is None:
        return
    try:
        if Version(version) >= Version(latest):
            return

        # TODO: test update logic
        print("UNIMPLEMENTED: fetches in-app updates")
        return

        with resources.path(APP_NAME_LOWER, "scripts/update.sh") as path:
            proc = subprocess.Popen(["/usr/bin/env", "bash", path, latest, prefix])
            if proc != 0:
                # TODO: pop a dialog
                pass
            sys.exit(proc)
    except InvalidVersion:
        return
