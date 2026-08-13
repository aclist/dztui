import re

day = r"([0][7-9]|[1][0-6])"
night = r"([0][0-6]|[1][7-9]|[2][0-3])"

def iterate(h: str, r: str) -> None:
    for m in range(60):
        time = f"{h:02}:{m:02}"
        assert re.match(r, time) is not None


def test_day() -> None:
    for h in range(17):
        if h < 7:
            continue
        iterate(h, day)


def test_night() -> None:
    for h in range(24):
        if 6 < h < 17:
            continue
        iterate(h, night)
