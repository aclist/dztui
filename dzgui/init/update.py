import logging
import requests
import subprocess
import sys

from importlib import resources
from packaging.version import Version

from dzgui.const.constants import APP_NAME, APP_NAME_LOWER, REQUEST_TIMEOUT
from dzgui.const.endpoints import GITHUB_RELEASES, CODEBERG_RELEASES
from dzgui.init.prefix import is_prefix_writeable

logger = logging.getLogger(APP_NAME)


def get_latest_release() -> str | None:
    tag = None
    # TODO: check order; github often has gateway errors
    for url in [GITHUB_RELEASES, CODEBERG_RELEASES]:
        try:
            res = requests.get(url, timeout=REQUEST_TIMEOUT)
            if res.status_code == 200:
                print(res.json())
                tag = res.json()["tag_name"]
                break
        except Exception as e:
            logger.critical(e)
            continue
    return tag


def check_updates(version: str) -> str | None:
    try:
        latest = get_latest_release()
        if latest is None:
            return
        if Version(version) >= Version(latest):
            return
        return latest
    except Exception:
        return
