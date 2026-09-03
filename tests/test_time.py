import re

from dzgui.model.proxy_model import DAY_REG, NIGHT_REG
import pytest

pytestmark = pytest.mark.FOO

def iterate(h: str, r: str) -> None:
    for m in range(60):
        time = f"{h:02}:{m:02}"
        assert re.match(r, time) is not None


def test_day() -> None:
    for h in range(17):
        if h < 7:
            continue
        iterate(h, DAY_REG)


def test_night() -> None:
    for h in range(24):
        if 5 < h < 18:
            continue
        iterate(h, NIGHT_REG)
