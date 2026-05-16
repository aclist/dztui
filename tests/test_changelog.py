import pytest

from importlib import resources
from dzgui.const.constants import APP_NAME_LOWER, CHANGELOG_PATH


@pytest.fixture
def changelog():
    path = resources.files(APP_NAME_LOWER).joinpath(CHANGELOG_PATH)
    return path


def test_headings(changelog):
    with open(changelog, "r") as f:
        lines = f.readlines()
    for line in lines:
        if line.startswith("#"):
            pass
        # TODO: use regex
    pass
