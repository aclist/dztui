import pytest
import re

from dzgui.api.servers import Details, Record, get_details


@pytest.fixture
def details() -> Details:
    """
    Static official server, metadata is expected to be invariate
    """
    r = Record("85.190.157.111", 10400, 10401)
    return get_details(r)


def test_invalid_server() -> None:
    r = Record("127.0.0.1", 10400, 10401)
    assert get_details(r) is None


@pytest.mark.parametrize("key, expect", [("day_accel", 2.3), ("night_accel", 6.8)])
def test_time_accel(details, key, expect) -> None:
    assert getattr(details, key) == expect


def test_gametime(details) -> None:
    time_reg = r"^(0[0-9]|1[0-9]|2[0-3]):([0-5][0-9]$)"
    match = re.match(time_reg, details.gametime)
    assert match is not None


def test_metadata(details) -> None:
    for row in details.data:
        label, value = row
        match label:
            case "Password":
                assert value == "Disabled"
            case "Platform":
                assert value == "Windows"
            case "Battleye":
                assert value == "Enabled"
            case "Valve Anti-Cheat":
                assert value == "Enabled"
            case _:
                pass
