import a2s
import requests
import shutil
import subprocess
from warnings import deprecated

from dataclasses import dataclass
from typing import TYPE_CHECKING

from dzgui.api.servers import Record
from dzgui.const.constants import REQUEST_TIMEOUT
from dzgui.const.endpoints import COORDS_API, IP_ECHO


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


# TODO: tests
def is_reserved(digits: list) -> bool:
    reserved = [0, 10, 127]

    if digits[0] in reserved:
        return True
    if digits[0] == 192 and digits[1] == 168:
        return True
    return False


def get_coords(ips: "Path", ip: str) -> Coords:
    split = ip2list(ip)

    if is_reserved(split):
        raise ReservedIPError(f"{ip} is a reserved IP address.")

    prefix = f"^{split[0]}.{split[1]}."

    if shutil.which("rg") is not None:
        args = ["/usr/bin/rg", prefix, str(ips)]
    else:
        args = ["/usr/bin/grep", "-E", prefix, str(ips)]
    proc = subprocess.run(args, capture_output=True, text=True)

    if proc.returncode != 0:
        raise GeolocationError("Failed to split records")

    ip_list = proc.stdout.splitlines()

    for address in ip_list:
        fields = address.split(",")
        upper = fields[1]

        upper_digits = ip2list(upper)
        if ip == upper:
            return Coords(float(fields[-2]), float(fields[-1]))

        if split[2] > upper_digits[2]:
            continue

        if split[2] == upper_digits[2]:
            if split[3] > upper_digits[3]:
                continue

        if split[2] <= upper_digits[2]:
            return Coords(float(fields[-2]), float(fields[-1]))
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


@deprecated("use ips.csv")
def get_local_coords(ip: str) -> str:
    url = COORDS_API + "/" + ip
    # local res=$(curl -Ls "$url" | jq -r '"\(.lat)\n\(.lon)"')
    return url
