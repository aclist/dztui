import json
import math
import os
import re
import socket
import subprocess
import sys
import typing  # noqa

from dataclasses import dataclass
from urllib import request, parse
from urllib.error import HTTPError
from typing import Union

sys.path.append("a2s")
import a2s  # noqa
from a2s import dayzquery  # noqa

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


def get_netmask() -> str:
    hostname = os.uname()[1]
    i = socket.gethostbyname(hostname)
    netmask = i.rsplit(".", 1)[0]
    return netmask


def test_ip(suffix: int, port: int) -> dict | None:
    netmask = get_netmask()
    hostname = f"{netmask}.{str(suffix)}"
    ping = ["ping", "-c1", "-i", "0.1", "-w", "1"]
    output = subprocess.run(ping + [hostname], capture_output=True)
    if output.returncode == 0:
        return query_direct(hostname, port)
    return None


def sanitize(name: str) -> str:
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
                continue

        r = row["gametype"].split(",")
        if "no3rd" in r:
            view = "1PP"
        else:
            view = "3PP"

        if "external" in r:
            provider = "Unoffic."
        else:
            provider = "Official"

        if "mod" in r:
            modded = True
        else:
            modded = False

        try:
            r = row["gametype"].split("lqs")
            queue = r[1].split(",")[0]
        except IndexError:
            queue = 0

        try:
            test_time = re.search(r"[0-9]{2}:[0-9]{2}", row["gametype"])
            if test_time:
                time = test_time.group(0)
            else:
                time = "Unknown"
        except AttributeError:
            time = "Unknown"

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
        raw = [
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
        ]
        rows.append(raw)
    return rows


def query_direct(ip: str, qport: int, TIMEOUT=3.0) -> dict | None:
    try:
        info = a2s.info((ip, qport), TIMEOUT)

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
    except TimeoutError:
        return None
    except KeyError:
        return None


@dataclass
class Res:
    status: int
    parsed: bool
    json: Union[str, None]


@dataclass
class Ping:
    addr: str
    iteration: int
    ping: int


@dataclass
class Details:
    data: Union[list, None]
    description: str
    success: bool


def is_passworded(ip: str, qport: int) -> bool:
    try:
        info = a2s.info((ip, qport))
    except TimeoutError:
        return False

    try:
        password = info.password_protected
    except AttributeError:
        return False
    return password


def details(ip: str, qport: int) -> Details:
    default_str = "None provided"

    try:
        info = a2s.info((ip, qport))
    except TimeoutError:
        return Details(None, default_str, False)
    try:
        rules = dayzquery.dayz_rules((ip, int(qport)))
    except TimeoutError:
        return Details(None, default_str, False)

    try:
        keywords = info.keywords.split(",")
    except AttributeError:
        return Details(None, default_str, False)

    battleye = "Disabled"
    if "battleye" in keywords:
        battleye = "Enabled"

    day_accel = 0.0
    night_accel = 0.0
    for keyword in keywords:
        if "etm" in keyword:
            day_accel = float(keyword.lstrip("etm"))
            day_accel = f"{day_accel:g}"
        if "entm" in keywords:
            night_accel = float(keyword.lstrip("entm"))
            night_accel = f"{night_accel:g}"

    try:
        password = info.password_protected
        if password is False:
            password = "Disabled"
        else:
            password = "Enabled"
    except AttributeError:
        password = "-"

    try:
        vac = info.vac_enabled
        if vac is False:
            vac = "Disabled"
        else:
            vac = "Enabled"
    except AttributeError:
        vac = "-"

    try:
        version = info.version
    except AttributeError:
        version = "-"

    try:
        dlc = rules.dlc_flags
        if dlc == 0:
            dlc = "None"
        if dlc == 2:
            dlc = "Frostline"
    except AttributeError:
        dlc = "not specified"

    try:
        platform = rules.platform
        if platform == "win":
            platform = "Windows"
        if platform == "?":
            platform = "Linux"
    except AttributeError:
        platform = "not specified"

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


def ping(iteration: int, row: list) -> Ping:
    addr = row[7]
    qport = row[8]

    res = None

    if row[9] != 9999:
        return Ping(addr, iteration, row[9])

    try:
        ip = addr.split(":")[0]
    except IndexError:
        ping = 9999

    try:
        res = query_direct(ip, qport, 0.5)
    except Exception:
        pass

    if res is None:
        ping = 9999
    else:
        ping = res["ping"]

    return Ping(addr, iteration, ping)


def query_api(key: str, param: str) -> Res:
    LIMIT = 10000
    url = "https://api.steampowered.com/IGameServersService/GetServerList/v1/?"

    payload: dict[str, Union[int, str]] = {
        "filter": r"\appid\221100" + param,
        "limit": LIMIT,
        "key": key,
    }
    par = parse.urlencode(payload)
    url = f"{url}{par}"

    status = 200
    parsed = True
    data = None

    try:
        with request.urlopen(url) as response:
            if response.status != 200:
                status = response.status
            try:
                parsed = True
                data = json.load(response)
            except json.decoder.JSONDecodeError:
                parsed = False
                data = None
    except HTTPError:
        status = 403
        parsed = False
        data = None
    finally:
        return Res(status, parsed, data)
