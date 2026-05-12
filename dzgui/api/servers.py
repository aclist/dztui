import ipaddress
import logging
import math
import os
import re
import requests
import socket
import subprocess
import threading

from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING, Union

from dzgui.api.bm import map_id_to_record
from dzgui.const.constants import APP_NAME, REQUEST_TIMEOUT
from dzgui.const.endpoints import STEAM_SERVERS
from dzgui.util import strings

import a2s
import dayzquery

if TYPE_CHECKING:
    from a2s import SourceInfo
    from dayzquery import DayzMod

logger = logging.getLogger(APP_NAME)

# TODO: confirm that patches from testing are incorporated here
# particularly around malformed values in JSON response. check commit log

params = [
    r"\nor\1\map\chernarusplus\nor\1\map\sakhal\nor\1\map\enoch\empty\1\nor\1\map\namalsk",  # noqa
    r"\map\namalsk\empty\1",
    r"\map\namalsk\noplayers\1",
    r"\map\chernarusplus\empty\1",
    r"\map\chernarusplus\noplayers\1",
    r"\map\sakhal\empty\1",
    r"\map\sakhal\noplayers\1",
    r"\map\enoch\empty\1",
    r"\map\enoch\noplayers\1",
]


class InvalidIpError(Exception):
    pass


@dataclass(slots=True, frozen=True)
class Res:
    status: int
    parsed: bool
    json: Union[dict[str, Any], None]


@dataclass(slots=True, frozen=True)
class Details:
    data: Union[list, None]
    description: str
    success: bool


@dataclass(slots=True)
class Record:
    """
    The gameport field is manipulated by the RowType.CONN_BY_IP method
    """

    ip: str
    gameport: int
    qport: int


class A2SInfo:
    def __init__(self, record: Record, info: a2s.SourceInfo | None) -> None:
        self.record = record
        self.info = info

    def get_record(self) -> Record:
        return self.record

    def get_info(self) -> a2s.SourceInfo | None:
        return self.info

    def as_row(self) -> dict[str, Any] | None:
        if self.info is None:
            return None
        ip = self.record.ip
        qport = self.record.qport
        return source_info_to_dict(ip, qport, self.info)

    def is_modded(self) -> bool:
        if self.info is None:
            raise ValueError("Cannot call this method on Nonetype")
        try:
            kw = self.info.keywords.split(",")
            state = True if "mod" in kw else False
            return state
        except Exception as e:
            logger.warning(e)
            raise e


def get_netmask() -> str:
    hostname = os.uname()[1]
    i = socket.gethostbyname(hostname)
    netmask = i.rsplit(".", 1)[0]
    return netmask


# TODO: rename
def test_ip(suffix: int, port: int, event: threading.Event) -> dict | None:
    if event.is_set():
        return None
    netmask = get_netmask()
    hostname = f"{netmask}.{str(suffix)}"
    ping = ["ping", "-c1", "-i", "0.1", "-w", "1"]
    output = subprocess.run(ping + [hostname], capture_output=True)
    if output.returncode == 0:
        return query_direct(hostname, port)
    return None


def sanitize(name: str) -> str:
    """
    Strips extraneous padding and spammy junk chars in server names
    """
    name = re.sub(r"\r", r"", name)
    name = re.sub(r"\n", r"", name)
    name = re.sub(r"\x01", r"", name)
    name = re.sub(r"\ufeff", r"", name)
    name = re.sub(r"(^!\s*)", r"-", name)
    name = re.sub(r"(^-\s*)", r"", name)
    name = re.sub(r"(^-)", r"", name)
    name = re.sub(r"(^\s*)", r"", name)
    name = re.sub(r"\t", "", name)
    return name


def parse_json(json: list) -> list:
    """
    Server metadata is underspecified and server operators
    tend to insert random garbage in the headers. In case
    sanitization failed, discard malformed rows rather than
    aborting outright.
    """
    rows = []
    for row in json:
        try:
            name = sanitize(row["name"])
            if name == "":
                continue
        except KeyError:
            continue

        malformed = False
        for key in [
            "map",
            "gametype",
            "players",
            "max_players",
            "addr",
            "gameport",
        ]:
            try:
                row[key]
            except KeyError:
                malformed = True
                break

        if malformed is True:
            continue

        try:
            r = row["gametype"].split(",")
        except KeyError:
            continue

        if "no3rd" in r:
            view = strings.filter_1pp
        else:
            view = strings.filter_3pp

        if "external" in r:
            provider = strings.filter_unofficial
        else:
            provider = strings.filter_official

        if "mod" in r:
            modded = True
        else:
            modded = False

        try:
            r = row["gametype"].split("lqs")
            queue = r[1].split(",")[0]
            if int(queue) > 255:
                continue
        except IndexError:
            queue = 0

        try:
            test_time = re.search(r"[0-9]{2}:[0-9]{2}", row["gametype"])
            if test_time:
                time = test_time.group(0)
            else:
                time = strings.unknown
        except AttributeError:
            time = strings.unknown

        try:
            ip = row["addr"].split(":")[0] + ":" + str(row["gameport"])
            qport = row["addr"].split(":")[1]
        except IndexError:
            continue

        try:
            ping = row["ping"]
        except KeyError:
            ping = 9999

        mapname = row["map"].lower()
        players = row["players"]
        max_players = row["max_players"]
        raw = (
            name,
            mapname,
            view,
            time,
            int(players),
            int(max_players),
            int(queue),
            ip,
            int(qport),
            ping,
            provider,
            modded,
        )
        rows.append(raw)
    return rows


def source_info_to_dict(ip: str, qport: int, info: "SourceInfo") -> dict[str, Any]:
    try:
        name = info.server_name
        mapname = info.map_name
        address = ip + ":" + str(qport)
        gameport = str(info.port)
        players = info.player_count
        max_players = info.max_players
        keywords = info.keywords

        try:
            ping = info.ping
            ping = math.floor(info.ping * 1000)
        except AttributeError:
            ping = 9999

        res = {}
        res["name"] = name
        res["map"] = mapname
        res["gametype"] = keywords
        res["players"] = players
        res["max_players"] = max_players
        res["addr"] = address
        res["gameport"] = gameport
        res["ping"] = ping
        return res
    except Exception as e:
        # TODO: generalized function
        logger.critical(f"{type(e).__name__}: {e} ({ip}:{qport})")
        return None


def query_direct(ip: str, qport: int, timeout: float = 3.0) -> dict[str, Any] | None:
    try:
        info = a2s.info((ip, qport), timeout)
        return source_info_to_dict(ip, qport, info)
    except Exception as e:
        logger.warning(e)
        return None


def get_details(record: Record) -> Details:
    ip = record.ip
    qport = record.qport
    default_str = strings.none_provided

    try:
        info = a2s.info((ip, qport))
    except TimeoutError:
        return Details(None, default_str, False)
    try:
        rules = dayzquery.dayz_rules((ip, qport))
    except Exception:
        return Details(None, default_str, False)

    try:
        keywords = info.keywords.split(",")
    except AttributeError:
        return Details(None, default_str, False)

    battleye = strings.disabled
    if "battleye" in keywords:
        battleye = strings.enabled

    day_accel = 0.0
    night_accel = 0.0
    for keyword in keywords:
        if "etm" in keyword:
            day_accel = float(keyword.lstrip("etm"))
            day_accel = float(f"{day_accel:g}")
        if "entm" in keywords:
            night_accel = float(keyword.lstrip("entm"))
            night_accel = float(f"{night_accel:g}")

    try:
        password = info.password_protected
        if password is False:
            password = strings.disabled
        else:
            password = strings.enabled
    except AttributeError:
        password = "-"

    try:
        vac = info.vac_enabled
        if vac is False:
            vac = strings.disabled
        else:
            vac = strings.enabled
    except AttributeError:
        vac = strings.null

    try:
        version = info.version
    except AttributeError:
        version = strings.null

    try:
        dlc = rules.dlc_flags
        if dlc == 0:
            dlc = strings.none
        if dlc == 2:
            dlc = strings.dlc_frostline
    except AttributeError:
        dlc = strings.unspecified

    try:
        platform = rules.platform
        if platform == "win":
            platform = strings.windows
        if platform == "?":
            platform = strings.linux
    except AttributeError:
        platform = strings.unspecified

    try:
        description = rules.description.strip()
        if description == "":
            description = default_str
    except AttributeError:
        description = default_str

    rows = [
        ["Battleye", battleye],
        ["Daytime acceleration", f"{day_accel}x"],
        ["DLC", dlc],
        ["Night-time acceleration", f"{night_accel}x"],
        ["Password", password],
        ["Platform", platform],
        ["Valve Anti-Cheat", vac],
        ["Version", version],
    ]

    return Details(rows, description, True)


def ping(ip: str, qport: int) -> int:
    try:
        res = query_direct(ip, qport, 0.5)
        if res is None:
            return 9999
        else:
            return res["ping"]
    except Exception:
        return 9999


def query_api(key: str, appid: int, param: str) -> Res:
    LIMIT = 10000
    payload: dict[str, Union[int, str]] = {
        "filter": r"\appid" + rf"\{appid}" + param,
        "limit": LIMIT,
        "key": key,
    }
    try:
        """
        NOTE: the global default timeout is None;
        using a low timeout (~5s) sometimes fails
        """
        res = requests.get(STEAM_SERVERS, params=payload, timeout=REQUEST_TIMEOUT)
        res.raise_for_status()
        parsed = True
        status = 200
        json = res.json()
    except Exception:
        parsed = False
        json = None
        status = 403
    finally:
        return Res(status, parsed, json)


def validate_ip(addr: str) -> Record:
    fields = addr.split(":")
    if len(fields) != 2:
        raise InvalidIpError("Address must be formatted as IP:Queryport")

    ip = fields[0]
    port = fields[1]

    try:
        int(port)
    except ValueError:
        raise InvalidIpError(f"'{port}' is not a valid port")

    if int(port) > 65535 or int(port) < 0:
        raise InvalidIpError(f"'{port}' is not a valid port")

    try:
        ipaddress.ip_address(ip)
    except ValueError:
        raise InvalidIpError(f"'{ip}' is not a valid IP")

    ip = addr.split(":")[0]
    qport = int(addr.split(":")[1])
    record = Record(ip, 0, qport)
    return record


def get_rules(record: Record) -> list["DayzMod"]:
    ip = record.ip
    qport = record.qport
    mods = dayzquery.dayz_rules((ip, qport)).mods
    return [mod for mod in mods]


def query_playercount(record: Record) -> tuple[int, int] | None:
    try:
        res = query_direct(record.ip, record.qport)
        players = int(res["players"])
        r = res["gametype"].split("lqs")
        try:
            queue = int(r[1].split(",")[0])
        except IndexError:
            queue = 0
        return players, queue
    except Exception as e:
        logger.critical(e)
        return None


def query_by_ip(addr: str) -> A2SInfo:
    record = short_ip_to_record(addr)
    return query_by_record(record, update_gameport=True)

def query_by_id(server_id: int, key: str) -> A2SInfo:
    """
    Used with numeric Battlemetrics IDs
    """
    record = map_id_to_record(key, server_id)
    return query_by_record(record)


def query_by_record(record: Record, update_gameport: bool = False) -> A2SInfo:
    try:
        info = a2s.info((record.ip, record.qport), 3.0)
        if update_gameport:
            record = Record(record.ip, info.port, record.qport)
        return A2SInfo(record, info)
    except Exception as e:
        logger.warning(e)
        return A2SInfo(record, None)


def short_ip_to_record(addr: str) -> Optional[Record]:
    r = addr.split(":")
    if len(r) != 2:
        return None
    return Record(r[0], 0, int(r[1]))


def fqip_to_record(addr: str) -> Optional[Record]:
    r = addr.split(":")
    if len(r) != 3:
        return None
    return Record(r[0], int(r[1]), int(r[2]))


def response_to_fqip(res: dict) -> str:
    ip = res["addr"].split(":")[0]
    gameport = res["gameport"]
    qport = res["addr"].split(":")[1]
    return f"{ip}:{gameport}:{qport}"


def response_to_record(res: dict) -> Record:
    ip = res["addr"].split(":")[0]
    gameport = res["gameport"]
    qport = res["addr"].split(":")[1]
    return Record(ip, int(gameport), int(qport))
