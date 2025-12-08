from dzgui.util import localize


def test_de(monkeypatch):
    monkeypatch.setenv("LC_CTYPE", "de_DE.UTF-8")
    localize.set_locale()
    assert localize.number(9900) == "9.900"
    assert localize.number(99.88) == "99,88"


def test_en(monkeypatch):
    monkeypatch.setenv("LC_CTYPE", "en_US.UTF-8")
    localize.set_locale()
    assert localize.number(9900) == "9,900"
    assert localize.number(99.88) == "99.88"


def test_none(monkeypatch):
    localize.set_locale()
    assert localize.number(9900) == "9,900"
    assert localize.number(99.88) == "99.88"


def test_empty(monkeypatch):
    monkeypatch.setenv("LC_CTYPE", "")
    localize.set_locale()
    assert localize.number(9900) == "9,900"
    assert localize.number(99.88) == "99.88"
