import logging
import requests
from pathlib import Path

from dzgui.api.servers import Record
from dzgui.config.query import lookup
from dzgui.const.endpoints import BM_SERVERS
from dzgui.const.enum import Preferences

from typing import Union

logger = logging.getLogger(__name__)

def get_attributes(config: Path, uid: int) -> str:
    # TODO: handle if key is not set
    # TODO: tests for malformed IDs/values
    key = lookup(config, Preferences.BM)

    hdr = {"Authorization": "Bearer " + key}
    payload: dict[str, str] = {
        "filter[game]": "dayz",
        "sort": "-players",
        "filter[ids][whitelist]": str(uid)
    }
    res = requests.get(BM_SERVERS, params=payload, headers=hdr)
    res.raise_for_status()
    j = res.json()["data"][0]["attributes"]
    return j


def map_id_to_record(config: Path, uid: int) -> Record | None:
    try:
        record = get_attributes(config, uid)
        ip = record["ip"]
        port = record["port"]
        qport = record["portQuery"]
        return Record(ip, port, qport)
    except Exception as e:
        logger.warn(e)
        return None
