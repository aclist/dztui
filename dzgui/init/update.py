import logging
import requests

from packaging.version import Version

from dzgui.const.constants import APP_NAME, REQUEST_TIMEOUT
from dzgui.const.endpoints import GITHUB_RELEASES, CODEBERG_RELEASES

logger = logging.getLogger(APP_NAME)


def get_latest_release() -> tuple[str, str] | tuple[None, None]:
    tag = None
    url = None
    # TODO: check order; github often has gateway errors
    for url in [GITHUB_RELEASES, CODEBERG_RELEASES]:
        try:
            res = requests.get(url, timeout=REQUEST_TIMEOUT)
            if res.status_code == 200:
                tag = str(res.json()["tag_name"])
                url = str(res.json()["assets"][0]["browser_download_url"])
                break
        except Exception as e:
            logger.critical(e)
            continue
    return tag, url


def check_updates(version: str) -> str | None:
    try:
        latest, url = get_latest_release()
        if latest is None:
            return None
        if Version(version) >= Version(latest):
            return None
        return url
    except Exception:
        return None
