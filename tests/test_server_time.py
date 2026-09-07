import pytest

from hypothesis import given, strategies as st
from datetime import datetime, timedelta

from dzgui.views.dialogs.calc import (
    LocalClock,
    ServerClock,
    Time,
    TimePicker,
    DAY_START_TIME,
    DAY_END_TIME,
)

pytestmark = pytest.mark.FOO


class DummyEmitter:
    pass


@pytest.fixture(params=[("05:00", 10.0), ("15:30", 5.0)])
def accel_server_clock(request) -> None:
    clock_time, expect = request.param
    cur_time = Time(clock_time, 5.0, 2.0)
    emitter = DummyEmitter()
    local_clock = LocalClock(emitter)
    server_clock = ServerClock(cur_time, emitter, local_clock)
    return expect, server_clock


def test_accel_factor(accel_server_clock) -> None:
    """Static test checking times at known boundaries"""
    expect, clock = accel_server_clock
    assert clock.get_accel_factor(clock.cur_time) == expect


def reference_calc(start, end, day_factor, night_factor):
    """
    Reference implementation to test validity of UI-side calculator
    Aggregates total seconds and applies accel factors after
    """
    day_start = datetime.combine(start.date(), DAY_START_TIME)
    day_end = datetime.combine(start.date(), DAY_END_TIME)
    night_factor = day_factor * night_factor

    if end < start:
        end += timedelta(days=1)

    day_max = max(start, day_start)
    day_min = min(end, day_end)

    next_day_start = datetime.combine(end.date(), DAY_START_TIME)
    next_day_end = datetime.combine(end.date(), DAY_END_TIME)

    range1 = (day_end - day_max).total_seconds()
    range2 = (min(end, next_day_end) - next_day_start).total_seconds()

    if end.date() > start.date():
        day_seconds = max(0, range1) + max(0, range2)
    else:
        day_seconds = max(0, (day_min - day_max).total_seconds())

    total_seconds = (end - start).total_seconds()
    night_seconds = (total_seconds - day_seconds) / night_factor
    day_seconds = day_seconds / day_factor
    total = night_seconds + day_seconds

    return timedelta(seconds=total)


day_accel = st.floats(
    min_value=1.0, max_value=24.0, allow_nan=False, allow_infinity=False
)
night_accel = st.floats(
    min_value=1.0, max_value=64.0, allow_nan=False, allow_infinity=False
)


@st.composite
def time_ranges(draw):
    start_time = draw(st.times())
    deltas = st.timedeltas(min_value=timedelta(0), max_value=timedelta(days=1))
    duration = draw(deltas)

    start = datetime.combine(datetime.now(), start_time)
    end = start + duration
    return start, end


@given(span=time_ranges(), day_factor=day_accel, night_factor=night_accel)
def test_time_aggregation(span, day_factor, night_factor) -> None:
    start, end = span

    strtime = start.strftime("%H:%M")
    t = Time(strtime, day_factor, night_factor)
    emitter = DummyEmitter()
    local_clock = LocalClock(emitter)
    server_clock = ServerClock(t, emitter, local_clock)
    h = end.time().hour
    m = end.time().minute
    picker = TimePicker(h, m)

    # NOTE: truncates microseconds to mimic widget HH:MM selection behavior
    start = server_clock.get_datetime()
    end = picker.get_time()
    actual = server_clock.calc_delta(end)
    expect = reference_calc(start, end, day_factor, night_factor)

    assert actual == expect
