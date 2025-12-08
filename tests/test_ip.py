import pytest

from dzgui.api.servers import validate_ip

def test_ip_validation() -> None:
    ip = "192.168.1.1:100"
    record = validate_ip(ip)
    assert record.ip == "192.168.1.1"
    assert record.gameport == 0
    assert record.qport == 100


def test_invalid_port() -> None:
    ip = "192.168.1.1:foo"
    with pytest.raises(Exception):
        validate_ip(ip)

@pytest.mark.parametrize("port", [-1, 65536])
def test_port_out_of_range(port: int) -> None:
    ip = f"192.168.1.1:{port}"
    with pytest.raises(Exception):
        validate_ip(ip)


def test_invalid_socket() -> None:
    ip = "0.0.0.0"
    with pytest.raises(Exception):
        validate_ip(ip)

# TODO: ?
def test_ipdb() -> None:
    pass
