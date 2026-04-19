import logging
import requests

from typing import Union, TYPE_CHECKING

from dzgui.const.constants import APPID_DAYZ, REQUEST_TIMEOUT
from dzgui.const import endpoints

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from requests import Response


def test_steam_api(key: str) -> bool:
    appid = APPID_DAYZ
    payload: dict[str, Union[int, str]] = {
        "filter": r"\appid" + rf"\{appid}",
        "limit": 10,
        "key": key,
    }
    try:
        res = requests.get(
            endpoints.STEAM_SERVERS, params=payload, timeout=REQUEST_TIMEOUT
        )
        return is_remote_up(res)
    except Exception as e:
        logger.critical(e)
        # TODO: pass exception text into dialog
        return False


# TODO: consolidate is_remote_up and exception logic into one function
def test_ipdb() -> bool:
    try:
        res = requests.get(endpoints.DB_IP, timeout=REQUEST_TIMEOUT)
        return is_remote_up(res)
    except Exception as e:
        logger.critical(e)
        return False


def test_bm_api(key: str) -> bool:
    payload: dict[str, str] = {
        "filter[game]": "dayz",
    }
    hdr = {"Authorization": "Bearer " + key}
    try:
        res = requests.get(
            endpoints.BM_SERVERS, params=payload, headers=hdr, timeout=REQUEST_TIMEOUT
        )
        return is_remote_up(res)
    except Exception as e:
        logger.critical(e)
        return False


def is_remote_up(res: "Response") -> bool:
    if res.status_code == 200:
        return True
    else:
        return False
