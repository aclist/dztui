import logging

from math import radians, cos, sin, asin, sqrt
from typing import TYPE_CHECKING

from dzgui.const.constants import APP_NAME
from dzgui.util.ip import get_coords

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402

if TYPE_CHECKING:
    from dzgui.const.enum import ServerTab
    from dzgui.controllers.mc import Controller
    from queue import Queue

logger = logging.getLogger(APP_NAME)


class Haversine:
    def __init__(self, lat1: float, lon1: float, lat2: float, lon2: float) -> None:

        R = 6371 * 1000

        dLat = radians(lat2 - lat1)
        dLon = radians(lon2 - lon1)
        lat1 = radians(lat1)
        lat2 = radians(lat2)

        a = sin(dLat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dLon / 2) ** 2
        c = 2 * asin(sqrt(a))

        self.dist = R * c

    def as_kilometers(self) -> float:
        return self.dist / 1000

    def as_miles(self) -> float:
        return self.dist / 1609.344


class CalcDist:
    def __init__(
        self,
        addr: str,
        enum: "ServerTab",
        result_queue: "Queue",
        controller: "Controller",
        cache: dict[str, Haversine],
    ) -> None:
        super().__init__()

        self.enum = enum
        self.controller = controller
        self.result_queue = result_queue
        self.addr = addr
        self.ip = self.addr

        dist = self.compare(self.ip)
        self.result_queue.put([self.addr, dist, self.enum])

    def compare(self, remote: str) -> int | None:
        prefs = self.controller.get_prefs()
        local = prefs.coords
        if local is None:
            return None
        try:
            remote = get_coords(prefs.paths.ips, remote)
        except Exception:
            return None

        # TODO: handle failed remote dist
        haversine = Haversine(local.lat, local.lon, remote.lat, remote.lon)
        return haversine
