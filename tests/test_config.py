import json
import pytest

from dzgui.config.query import get_config
from dzgui.config.xdg import get_xdg_paths, parse_filepaths
from dzgui.config import convert
from tests.fixtures import fixture_path

pytestmark = pytest.mark.config


@pytest.fixture
def legacy_config():
    return fixture_path("dztuirc_one")


@pytest.fixture
def keys():
    return [
        "bm_api",
        "fav_server",
        "fav_label",
        "name",
        "fullscreen",
        "steam_api",
        "auto_install",
        "default_steam_path",
        "client",
        "ip_list",
        "use_miles",
        "start_tab",
    ]


@pytest.fixture
def config():
    paths = get_xdg_paths()
    xdg = parse_filepaths(paths)
    return get_config(xdg.config)


@pytest.mark.post_install
def test_invalid_config_value(config):
    with pytest.raises(Exception):
        assert config["foo"] is None


@pytest.mark.post_install
def test_default_config_values(keys, config):
    for key in keys:
        assert config[key] is not None


@pytest.mark.post_install
def test_contains_invalid_values(keys, config):
    for key in config:
        assert key in keys


@pytest.mark.parametrize(
    "fixture, expect",
    [
        ("dztuirc_one", (False, True, True)),
        ("dztuirc_two", (False, False, False)),
    ],
)
def test_bool_conversion(fixture, expect):
    fixture = fixture_path(fixture)
    j = convert.rc2json(fixture)
    j = json.loads(j)
    assert j["fullscreen"] == expect[0]
    assert j["auto_install"] == expect[2]
    assert not j["use_miles"]


def test_key_conversion(legacy_config):
    j = convert.rc2json(legacy_config)
    j = json.loads(j)
    keys = [
        "api_key",
        "staging_dir",
        "src_path",
        "steam_path",
        "preferred_client",
        "debug",
    ]
    for key in keys:
        assert key not in j


# TODO: test that when a config file is created from scratch, it contains all values
