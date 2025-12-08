import pytest
import time

from dzgui.util import cooldown


def test_time_under():
    time_before = cooldown.get_time()
    time.sleep(1)
    result = cooldown.is_elapsed(time_before)
    assert result is False


@pytest.mark.slow
def test_time_over():
    time_before = cooldown.get_time()
    time.sleep(31)
    result = cooldown.is_elapsed(time_before)
    assert result is True
