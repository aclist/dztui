import logging
import requests
from typing import Any, Optional, TYPE_CHECKING

from dzgui.const.constants import APP_NAME
from dzgui.const.endpoints import BM_SERVERS

logger = logging.getLogger(APP_NAME)

if TYPE_CHECKING:
    from dzgui.api.servers import Record


def get_attributes(key: str, uid: int) -> Any:
    # TODO: handle if key is not set
    # TODO: tests for malformed IDs/values

    hdr = {"Authorization": "Bearer " + key}
    payload: dict[str, str] = {
        "filter[game]": "dayz",
        "sort": "-players",
        "filter[ids][whitelist]": str(uid),
    }
    res = requests.get(BM_SERVERS, params=payload, headers=hdr)
    res.raise_for_status()
    j = res.json()["data"][0]["attributes"]
    return j


def map_id_to_record(key: str, uid: int) -> Optional["Record"]:
    from dzgui.api.servers import Record

    try:
        record = get_attributes(key, uid)
        ip = record["ip"]
        port = int(record["port"])
        qport = int(record["portQuery"])
        return Record(ip, port, qport)
    except Exception:
        return None
