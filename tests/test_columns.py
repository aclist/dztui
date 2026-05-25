import pytest

from dzgui.init.migrate import convert_cols_file
from tests.fixtures import fixture_path

@pytest.fixture
def columns_with_perspective():
    return fixture_path("columns_1")

@pytest.fixture
def columns_without_perspective():
    return fixture_path("columns_2")

@pytest.fixture
def columns_with_view():
    return fixture_path("columns_3")

@pytest.mark.config
def test_columns_with_perspective(columns_with_perspective):
    j = convert_cols_file(columns_with_perspective)
    assert "View" in j["cols"]
    assert "Max" in j["cols"]

@pytest.mark.config
def test_columns_without_perspective(columns_without_perspective):
    j = convert_cols_file(columns_without_perspective)
    assert "View" not in j["cols"]
    assert "Max" not in j["cols"]

@pytest.mark.config
def test_columns_with_view(columns_with_view):
    j = convert_cols_file(columns_with_view)
    assert j is None
