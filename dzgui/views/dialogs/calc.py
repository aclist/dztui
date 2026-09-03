import gi
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Literal

from dzgui.views.components.labels import BoldLabel
from dzgui.strings import calc
from dzgui.views.components.box import VBox

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, GObject  # type: ignore  # noqa E402

DAY_START_TIME = time(hour=6, minute=0, second=0)
DAY_END_TIME = time(hour=17, minute=59, second=59)
NIGHT_START_TIME = time(hour=18, minute=0, second=0)
NIGHT_END_TIME = time(hour=5, minute=59, second=59)
EXTENDED_TIME_FORMAT = "%H:%M:%S"


@dataclass(slots=True, frozen=True)
class Time:
    time: str
    day_accel: float
    night_accel: float


class Emitter(GObject.GObject):
    def __init__(self) -> None:
        super().__init__()

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(object, object))
    def local_time_incremented(self, time_now: datetime, elapsed: timedelta) -> None:
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(object,))
    def server_time_incremented(self, server_time: datetime) -> None:
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=())
    def calculate_button_clicked(self) -> None:
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(object,))
    def target_time_changed(self, time: timedelta) -> None:
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(object,))
    def remaining_time_changed(self, time: datetime) -> None:
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(object,))
    def adjusted_local_time_changed(self, time: datetime) -> None:
        pass


class LocalClock:
    def __init__(self, emitter: Emitter) -> None:
        self.emitter = emitter
        self.start_time = datetime.now()
        GLib.timeout_add(500, self.check_time)

    # FIXME: sometimes skips 2s
    def get_time(self) -> str:
        return datetime.now().time().strftime(EXTENDED_TIME_FORMAT)

    def get_elapsed_time(self) -> timedelta:
        return datetime.now() - self.start_time

    def check_time(self) -> Literal[True]:
        time_now = datetime.now()
        elapsed = datetime.now() - self.start_time
        self.emitter.emit("local_time_incremented", time_now, elapsed)
        return True


class ServerClock:
    def __init__(
        self, server_time: Time, emitter: Emitter, local_clock: LocalClock
    ) -> None:

        self.local_clock = local_clock
        self.emitter = emitter

        hour, minute = self.split_time(server_time)
        self.day_accel = server_time.day_accel
        self.night_accel = server_time.night_accel

        self.start_time = datetime.combine(datetime.today(), time(hour, minute))
        self.cur_time = datetime.combine(datetime.today(), time(hour, minute))

        # NOTE: at highest possible accel interval (64 * 64), real time is 0.876 seconds
        if self.is_night():
            GLib.timeout_add(500, self.increment_night)
        else:
            GLib.timeout_add(500, self.increment_day)

    @staticmethod
    def split_time(server_time: Time) -> tuple[int, int]:
        split = server_time.time.split(":")
        return int(split[0]), int(split[1])

    def _increment_with_offset(self, offset: float) -> None:
        elapsed = self.local_clock.get_elapsed_time()
        virtual_elapsed = elapsed * offset
        self.cur_time = self.start_time + virtual_elapsed
        self.emitter.emit("server_time_incremented", self.cur_time)

    def increment_day(self) -> bool:
        if self.is_night():
            GLib.timeout_add(500, self.increment_night)
            return False
        offset = self.day_accel
        self._increment_with_offset(offset)
        return True

    def increment_night(self) -> bool:
        if not self.is_night():
            GLib.timeout_add(500, self.increment_day)
            return False
        offset = self.night_accel * self.day_accel
        self._increment_with_offset(offset)
        return True

    def is_night(self) -> bool:
        return (
            self.cur_time.time() >= NIGHT_START_TIME
            or self.cur_time.time() <= NIGHT_END_TIME
        )

    def get_values(self) -> tuple[int, int]:
        return self.cur_time.hour, self.cur_time.minute

    def get_time(self) -> time:
        return self.cur_time.time()

    def get_cycle_remainder(self, accel: bool = True) -> float:
        # NOTE: calc from cycle start time to current point
        if self.is_night():
            cutoff = DAY_START_TIME
            offset = self.day_accel * self.night_accel
        else:
            cutoff = NIGHT_START_TIME
            offset = self.day_accel
        start = datetime.combine(self.cur_time, cutoff)

        if accel is False:
            offset = 1
        return (start - self.cur_time).total_seconds() / offset

    def get_full_cycle(self, end_time: time, start_time: time) -> float:
        end = datetime.combine(self.cur_time, end_time)
        start = datetime.combine(self.cur_time, start_time)
        if start > end:
            end += timedelta(days=1)
        return (end - start).total_seconds()

    def get_day_cycle(self) -> float:
        return self.get_full_cycle(DAY_END_TIME, DAY_START_TIME)

    def get_night_cycle(self) -> float:
        return self.get_full_cycle(NIGHT_END_TIME, NIGHT_START_TIME)

    def get_delta(self, picker_time: time, start_time: time) -> float:
        start = datetime.combine(self.cur_time, start_time)
        picker_date = datetime.combine(self.cur_time, picker_time)
        if start > picker_date:
            picker_date += timedelta(days=1)
        delta = (picker_date - start).total_seconds()
        return delta

    def get_next_cycle(self) -> float:
        if self.is_night():
            return self.get_day_cycle() / self.day_accel
        else:
            return self.get_night_cycle() / (self.day_accel * self.night_accel)

    def get_remaining_delta(self, picker_time: time, is_night: bool) -> float:
        if is_night:
            start_time = NIGHT_START_TIME
            offset = self.day_accel * self.night_accel
        else:
            start_time = DAY_START_TIME
            offset = self.day_accel
        return self.get_delta(picker_time, start_time) / offset

    def calc_delta(self, picker_time: time, is_night: bool) -> timedelta:
        # NOTE: time spans two full cycles
        if self.get_time() > picker_time:
            to_end = self.get_cycle_remainder()
            next_cycle = self.get_next_cycle()
            delta = self.get_remaining_delta(picker_time, is_night)
            total = to_end + next_cycle + delta
        else:
            # TODO: fix calculation
            picker_date = datetime.combine(self.cur_time, picker_time)
            # NOTE: strip sub-minute values
            new = self.cur_time.replace(second=0, microsecond=0)
            delta = (picker_date - new).total_seconds()
            remainder_till_cycle_end = self.get_cycle_remainder(accel=False)
            if delta <= remainder_till_cycle_end:
                if self.is_night():
                    total = delta / (self.day_accel * self.night_accel)
                else:
                    total = delta / self.day_accel
            else:
                total = self.get_remaining_delta(picker_time, is_night)

        total = round(total)
        td = timedelta(seconds=total)
        return td


class RemainderClock:
    def __init__(self, emitter: Emitter) -> None:
        self.emitter = emitter
        self.emitter.connect("target_time_changed", self._on_target_time_changed)
        self.emitter.connect("local_time_incremented", self._on_local_time_incremented)
        self.reset_time()

        self.previous = timedelta(0)

    def reset_time(self) -> None:
        self.time = datetime.combine(datetime.now(), time(hour=0, minute=0, second=0))

    def _on_local_time_incremented(
        self, emitter: Emitter, time: datetime, elapsed: timedelta
    ) -> None:
        if self.time == datetime.min.time():
            return

        delta = elapsed - self.previous
        # NOTE: clamp to midnight
        self.time = max(
            self.time - delta, self.time.replace(hour=0, minute=0, second=0)
        )
        self.previous = elapsed
        self.emitter.emit("remaining_time_changed", self.time)

    def _on_target_time_changed(self, emitter: Emitter, time: timedelta) -> None:
        self.reset_time()
        self.time += time
        self.emitter.emit("remaining_time_changed", self.time)

    def get_time(self) -> str:
        return self.time.strftime(EXTENDED_TIME_FORMAT)


class AdjustedClock:
    def __init__(self, emitter: Emitter) -> None:
        self.emitter = emitter
        self.emitter.connect("target_time_changed", self._on_target_time_changed)
        self.start_time = datetime.now()

    def _on_target_time_changed(self, emitter: Emitter, time: timedelta) -> None:
        self.start_time = datetime.now()
        adjusted = self.start_time + time
        self.emitter.emit("adjusted_local_time_changed", adjusted)

    def get_time(self) -> str:
        return self.start_time.strftime(EXTENDED_TIME_FORMAT)


class VerticalSpinBox(Gtk.SpinButton):
    def __init__(self, value: int, upper: int) -> None:
        super().__init__(
            adjustment=Gtk.Adjustment(
                value=value,
                lower=0,
                upper=upper,
                step_increment=1,
                page_increment=1,
                page_size=0,
            ),
            orientation=Gtk.Orientation.VERTICAL,
        )


class HourSpinBox(VerticalSpinBox):
    def __init__(self, hour: int) -> None:
        super().__init__(value=hour, upper=23)


class MinuteSpinBox(VerticalSpinBox):
    def __init__(self, minute: int) -> None:
        super().__init__(value=minute, upper=59)

        self.get_adjustment().set_page_increment(10)


class TimePicker(Gtk.Box):
    def __init__(self, hour: int, minute: int) -> None:
        super().__init__(
            orientation=Gtk.Orientation.HORIZONTAL,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        )
        self.hour_spin = HourSpinBox(hour)
        self.minute_spin = MinuteSpinBox(minute)
        self.add(self.hour_spin)
        self.add(self.minute_spin)

        self.hour_spin.connect("output", self._on_output)
        self.minute_spin.connect("output", self._on_output)

    def _on_output(self, spin_button: VerticalSpinBox) -> Literal[True]:
        val = spin_button.get_value()
        spin_button.set_text(f"{int(val):02d}")
        # NOTE: indicates that rendering completed
        return True

    def get_values(self) -> tuple[int, int]:
        hour = self.get_hour()
        minute = self.get_minute()
        return hour, minute

    def get_hour(self) -> int:
        return int(self.hour_spin.get_adjustment().get_value())

    def get_minute(self) -> int:
        return int(self.minute_spin.get_adjustment().get_value())

    def get_time(self) -> time:
        return time(hour=self.get_hour(), minute=self.get_minute())

    def set_time(self, hour: int, minute: int) -> None:
        self.hour_spin.get_adjustment().set_value(hour)
        self.minute_spin.get_adjustment().set_value(minute)

    def is_night(self) -> bool:
        t = self.get_time()
        return t >= NIGHT_START_TIME or t <= NIGHT_END_TIME


class AdjustedTimeFrame(Gtk.Frame):
    def __init__(self, emitter: Emitter) -> None:
        super().__init__(margin_start=50, margin_end=50)

        self.emitter = emitter
        self.emitter.connect(
            "adjusted_local_time_changed", self._on_adjusted_time_changed
        )
        self.emitter.connect("remaining_time_changed", self._on_remainder_changed)

        self.remainder_clock = RemainderClock(emitter)
        self.remainder_heading = BoldLabel(calc.heading_remainder_time)
        self.remaining_time = Gtk.Label(label=self.remainder_clock.get_time())

        self.adjusted_clock = AdjustedClock(emitter)
        self.adjusted_heading = BoldLabel(calc.heading_adjusted_time)
        self.adjusted_local_time = Gtk.Label(label=self.adjusted_clock.get_time())

        flowbox = Gtk.FlowBox(
            row_spacing=20,
            column_spacing=50,
            min_children_per_line=2,
            max_children_per_line=2,
            margin=15,
            halign=Gtk.Align.CENTER,
            selection_mode=Gtk.SelectionMode.NONE,
        )
        flowbox.add(self.remainder_heading)
        flowbox.add(self.adjusted_heading)
        flowbox.add(self.remaining_time)
        flowbox.add(self.adjusted_local_time)

        recalc = Gtk.Button(
            label=calc.calculate, halign=Gtk.Align.CENTER, margin_bottom=20
        )
        recalc.connect("clicked", self._on_recalc_clicked)

        vbox = VBox()
        vbox.extend([flowbox, recalc])
        self.add(vbox)

    def _on_remainder_changed(self, emitter: Emitter, time: datetime) -> None:
        strtime = str(time.strftime(EXTENDED_TIME_FORMAT))
        self.remaining_time.set_text(strtime)

    def _on_adjusted_time_changed(self, emitter: Emitter, time: datetime) -> None:
        strtime = str(time.strftime(EXTENDED_TIME_FORMAT))
        self.adjusted_local_time.set_text(strtime)

    def _on_recalc_clicked(self, button: Gtk.Button) -> None:
        self.emitter.emit("calculate_button_clicked")


class TimePickerFrame(Gtk.Frame):
    def __init__(self, emitter: Emitter, stime: Time) -> None:
        super().__init__(margin_start=50, margin_end=50)

        self.emitter = emitter
        self.emitter.connect("local_time_incremented", self._on_local_clock_increment)
        self.emitter.connect("server_time_incremented", self._on_server_clock_increment)
        self.emitter.connect(
            "calculate_button_clicked", self._on_calculate_button_clicked
        )

        self.local_clock = LocalClock(self.emitter)
        local_clock_time = self.local_clock.get_time()

        self.server_time = ServerClock(stime, self.emitter, self.local_clock)
        hour, minute = self.server_time.get_values()
        self.picker = TimePicker(hour, minute)

        self.local_timelabel = Gtk.Label(label=local_clock_time)
        self.server_timelabel = Gtk.Label(label=stime.time, halign=Gtk.Align.CENTER)

        h0 = BoldLabel(calc.heading_local_time)
        h1 = BoldLabel(calc.heading_server_time)
        h2 = BoldLabel(calc.heading_target_time)

        flowbox = Gtk.FlowBox(
            row_spacing=10,
            column_spacing=50,
            min_children_per_line=3,
            max_children_per_line=3,
            margin=15,
            halign=Gtk.Align.CENTER,
            selection_mode=Gtk.SelectionMode.NONE,
        )
        flowbox.add(h0)
        flowbox.add(h1)
        flowbox.add(h2)
        flowbox.add(self.local_timelabel)
        flowbox.add(self.server_timelabel)
        flowbox.add(self.picker)

        self.add(flowbox)

    def _on_server_clock_increment(self, emitter: Emitter, time_now: datetime) -> None:
        t = time_now.time().strftime("%H:%M")
        self.server_timelabel.set_text(t)

    def _on_local_clock_increment(
        self, emitter: Emitter, time_now: datetime, elapsed: timedelta
    ) -> None:
        t = time_now.time().strftime(EXTENDED_TIME_FORMAT)
        self.local_timelabel.set_text(t)

    def _on_calculate_button_clicked(self, button: Gtk.Button) -> None:
        if (self.picker.get_values()) == (self.server_time.get_values()):
            total_time = timedelta(seconds=0)
        else:
            picker_time = self.picker.get_time()
            is_night = self.picker.is_night()
            total_time = self.server_time.calc_delta(picker_time, is_night)
        self.emitter.emit("target_time_changed", total_time)


class ServerTimeCalculator(Gtk.ScrolledWindow):
    def __init__(self, stime: Time) -> None:
        super().__init__(propagate_natural_width=True)

        self.emitter = Emitter()
        outerbox = Gtk.Box(
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.START,
            spacing=20,
            orientation=Gtk.Orientation.VERTICAL,
        )
        time_picker_frame = TimePickerFrame(self.emitter, stime)
        adjusted_time_frame = AdjustedTimeFrame(self.emitter)
        disclaimer = Gtk.Label(
            label=calc.disclaimer,
            justify=Gtk.Justification.CENTER,
        )
        for el in time_picker_frame, adjusted_time_frame, disclaimer:
            outerbox.add(el)
        self.add(outerbox)


# TEST: write tests with/without live clock increment
# FIXME: with accel of (1, 1), a 60min change converts to 55 mins instead of 59/60
# FIXME: real time until target time is not zero padded
