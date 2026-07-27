import pytest

from dzgui.config.query import get_config
from dzgui.config.xdg import get_xdg_paths, parse_filepaths
from dzgui.api import probe

pytestmark = pytest.mark.webtest


@pytest.fixture
def config():
    paths = get_xdg_paths()
    xdg = parse_filepaths(paths)
    return get_config(xdg.config)


def test_ipdb():
    assert probe.test_ipdb()


def test_steam(config):
    key = config["steam_api"]
    assert probe.test_steam_api(key)
