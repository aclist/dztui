import logging
import multiprocessing
from math import radians, cos, sin, asin, sqrt
from typing import TYPE_CHECKING

from dzgui.util.ip import GeolocationError, get_coords
from dzgui.util.localize import number

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402

if TYPE_CHECKING:
    from dzgui.util.ip import Coords
    from dzgui.controllers.mc import Controller

logger = logging.getLogger(__name__)

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

class CalcDist(multiprocessing.Process):
    def __init__(
        self,
        addr: str,
        result_queue: multiprocessing.Queue,
        controller: "Controller",
    ) -> None:
        super().__init__()

        self.controller = controller
        self.result_queue = result_queue
        self.addr = addr
        self.ip = addr.split(":")[0]

    def run(self) -> None:
        cache = self.controller.get_dist_cache()
        if self.addr in cache:
            logger.info(f"Address '{self.addr}' already in cache")
            self.result_queue.put([self.addr, cache[self.addr]])
            return

        dist = self.compare(self.ip)
        self.result_queue.put([self.addr, dist])

    def compare(self, remote: str) -> int | None:
        prefs = self.controller.get_prefs()
        local = prefs.coords
        if local is None:
            return None
        try:
            remote = get_coords(prefs.paths.ips, remote)
        except GeolocationError:
            return None

        # TODO: handle failed remote dist
        haversine = Haversine(local.lat, local.lon, remote.lat, remote.lon)
        return haversine
