import logging
import requests
from typing import Optional, TYPE_CHECKING

from dzgui.const.endpoints import BM_SERVERS

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from dzgui.api.servers import Record


def get_attributes(key: str, uid: int) -> str:
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
        port = record["port"]
        qport = record["portQuery"]
        return Record(ip, port, qport)
    except Exception:
        return None
