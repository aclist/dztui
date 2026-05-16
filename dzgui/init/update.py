import logging
import requests

from packaging.version import Version

from dzgui.const.constants import APP_NAME, REQUEST_TIMEOUT
from dzgui.const.endpoints import GITHUB_RELEASES, CODEBERG_RELEASES

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
