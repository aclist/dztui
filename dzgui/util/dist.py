import multiprocessing
from math import radians, cos, sin, asin, sqrt
from typing import TYPE_CHECKING


import dzgui.util.ip as ip
from dzgui.util.ip import GeolocationError
from dzgui.util.localize import number

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402

if TYPE_CHECKING:
    from dzgui.util.ip import Coords

class Haversine():
    def __init__(self, lat1: float, lon1: float, lat2: float, lon2: float) -> None:

        R = 6371 * 1000

        dLat = radians(lat2 - lat1)
        dLon = radians(lon2 - lon1)
        lat1 = radians(lat1)
        lat2 = radians(lat2)

        a = sin(dLat/2) ** 2 + cos(lat1) * cos(lat2) * sin(dLon/2) ** 2
        c = 2 * asin(sqrt(a))

        self.dist = R * c

    def as_kilometers(self) -> float:
        return self.dist / 1000

    def as_miles(self) -> float:
        return self.dist / 1609.344

def compare(local: "Coords", remote_c: str, fmt: str) -> int | None:
    if local is None:
        return None
    try:
        # FIXME: expects XDG.ips
        remote = ip.get_coords(remote_c)
    except GeolocationError:
        return None

    haversine = Haversine(local.lat, local.lon, remote.lat, remote.lon)
    if fmt == "km":
        dist = haversine.as_kilometers()
    else:
        dist = haversine.as_miles()
    return round(dist)

class CalcDist(multiprocessing.Process):
    def __init__(
        self,
        widget: Gtk.Widget,
        addr: str,
        result_queue: multiprocessing.Queue,
        cache: dict,
    ):
        super().__init__()

        self.result_queue = result_queue
        self.addr = addr
        self.ip = addr.split(":")[0]

    # TODO: pass  controller correctly
    def run(self) -> None:
        use_miles = MainController.query_config("use_miles")
        fmt = "mi" if use_miles else "km"

        # TODO: get cache accordingly
        if self.addr in cache:
            if fmt in cache[self.addr]:
                logger.info(f"Address '{self.addr}' already in cache")
                self.result_queue.put([self.addr, cache[self.addr]])
                return

        prefs = MainController.get_prefs()
        dist = compare(prefs.coords, prefs.paths.ips, self.ip, fmt)
        if dist is None:
            dist_pretty =  "Unknown"
        else:
            d = number(dist)
            dist_pretty = f"{d} {fmt}"
        self.result_queue.put([self.addr, dist_pretty])
