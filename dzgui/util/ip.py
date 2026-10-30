import a2s
from ipaddress import ip_address
import requests
import shutil
import subprocess

from dataclasses import dataclass
from typing import TYPE_CHECKING

from dzgui.api.servers import Record
from dzgui.config.ipdb import read_from_table
from dzgui.const.constants import REQUEST_TIMEOUT
from dzgui.const.endpoints import IP_ECHO


if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class Coords:
    lat: float
    lon: float


class GeolocationError(Exception):
    pass


class ReservedIPError(Exception):
    pass


def ip2list(ip: str) -> list:
    return [int(digit) for digit in ip.split(".")]


def is_usable(ip: str) -> bool:
    address = ip_address(ip)
    if address.is_reserved or address.is_private:
        return False
    return True


def get_coords(db_path: "Path", ip: str) -> Coords:
    if not is_usable(ip):
        raise ReservedIPError(f"{ip} is a reserved IP address.")
    try:
        lat, lon = read_from_table(db_path, ip)
        return Coords(lat, lon)
    except Exception:
        raise GeolocationError("No matching records found")


def get_local_ip() -> str:
    ip = ""
    if shutil.which("dig") is not None:
        proc = subprocess.run(
            [
                "/usr/bin/dig",
                "-4",
                "+short",
                "myip.opendns.com",
                "@resolver1.opendns.com",
            ],
            capture_output=True,
            text=True,
        )

        if proc.returncode == 0:
            ip = proc.stdout.rstrip("\n")
    else:
        res = requests.get(IP_ECHO, timeout=REQUEST_TIMEOUT)
        res.raise_for_status()
        ip = res.text
    return ip


def resolve_ip(address: Record) -> Record:
    # TODO: unit test for resolved ips
    """
    Multiple game modes may be hosted on the same IP and query port,
    but resolve to different game ports. The canonical record must
    contain the real game port. This is merely used when saving a
    record as a UUID.
    """
    res = a2s.info((address.ip, address.qport))
    real_gport = res.port
    return Record(address.ip, real_gport, address.qport)


def is_valid_port(port: str) -> bool:
    if len(port) < 1:
        return True
    if not port.isdigit() or int(port) == 0 or int(port[0]) == 0 or int(port) > 65535:
        return True
    return False
