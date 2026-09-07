import gi
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Literal

from dzgui.const.constants import DAY_ICON, NIGHT_ICON
from dzgui.strings import calc
from dzgui.views.components.icon import Icon
from dzgui.views.components.labels import BoldLabel
from dzgui.views.components.box import VBox, HBox

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, GObject  # type: ignore  # noqa E402

DAY_START_TIME = time(hour=6, minute=0, second=0)
DAY_END_TIME = time(hour=18, minute=0, second=0)
NIGHT_START_TIME = time(hour=18, minute=0, second=0)
NIGHT_END_TIME = time(hour=6, minute=0, second=0)
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
    def target_time_reset(self, time: timedelta) -> None:
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
        # NOTE: highest theoretical accel interval is 24 * 64
        GLib.timeout_add(500, self.check_time)

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

        self._last_elapsed = self.local_clock.get_elapsed_time()
        self.emitter.connect("local_time_incremented", self._on_local_time_incremented)

    @staticmethod
    def split_time(server_time: Time) -> tuple[int, int]:
        split = server_time.time.split(":")
        return int(split[0]), int(split[1])

    def is_day(self) -> bool:
        if DAY_START_TIME <= self.cur_time.time() <= DAY_END_TIME:
            return True
        return False

    def _on_local_time_incremented(
        self,
        emitter: Emitter,
        time: datetime,
        elapsed: timedelta,
    ) -> Literal[True]:
        delta = elapsed - self._last_elapsed
        self._last_elapsed = elapsed
        factor = self.get_accel_factor(self.cur_time)
        self.cur_time += delta * factor
        self.emitter.emit("server_time_incremented", self.cur_time)
        return True

    def get_accel_factor(self, dt: datetime) -> float:
        return (
            self.day_accel
            if DAY_START_TIME <= dt.time() < DAY_END_TIME
            else (self.night_accel * self.day_accel)
        )

    def get_values(self) -> tuple[int, int]:
        return self.cur_time.hour, self.cur_time.minute

    def get_datetime(self) -> datetime:
        return self.cur_time

    def get_time(self) -> time:
        return self.cur_time.time()

    def calc_delta(self, end_time: datetime) -> timedelta:
        total = 0.0
        current_time = self.cur_time

        if current_time > end_time:
            end_time += timedelta(days=1)

        while current_time < end_time:
            factor = self.get_accel_factor(current_time)
            day_start = datetime.combine(current_time.date(), DAY_START_TIME)
            day_end = datetime.combine(current_time.date(), DAY_END_TIME)

            if current_time.time() < DAY_START_TIME:
                edge = day_start
            elif current_time.time() < DAY_END_TIME:
                edge = day_end
            else:
                edge = datetime.combine(
                    current_time.date() + timedelta(days=1), DAY_START_TIME
                )

            chunk_end = min(end_time, edge)
            total += (chunk_end - current_time).total_seconds() / factor
            current_time = chunk_end
        return timedelta(seconds=total)


class RemainderClock:
    def __init__(self, emitter: Emitter) -> None:
        self.emitter = emitter
        self.emitter.connect("target_time_changed", self._on_target_time_changed)
        self.emitter.connect("target_time_reset", self._on_target_time_reset)
        self.emitter.connect("local_time_incremented", self._on_local_time_incremented)
        self.reset_time(True)

        self.previous = timedelta(0)

    def reset_time(self, zero_out: bool = False) -> None:
        now = datetime.now()
        second, ms = (0, 0) if zero_out else (now.second, now.microsecond)
        self.time = datetime.combine(
            now, time(hour=0, minute=0, second=second, microsecond=ms)
        )

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

    def _on_target_time_reset(self, emitter: Emitter, time: timedelta) -> None:
        self.reset_time(True)
        self.emitter.emit("remaining_time_changed", self.time)
        # NOTE: restore adjusted time to current time
        self.emitter.emit("adjusted_local_time_changed", datetime.now())

    def _on_target_time_changed(self, emitter: Emitter, time: timedelta) -> None:
        self.reset_time(True)
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

    def get_time(self) -> datetime:
        d = datetime.now()
        return datetime.combine(
            d,
            time(
                hour=self.get_hour(),
                minute=self.get_minute(),
                second=0,
                microsecond=0,
            ),
        )

    def set_time(self, hour: int, minute: int) -> None:
        self.hour_spin.get_adjustment().set_value(hour)
        self.minute_spin.get_adjustment().set_value(minute)


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

        self.icon_indicator = Icon(DAY_ICON)
        self.update_server_icon()

        server_time_box = HBox(10)
        server_time_box.set_halign(Gtk.Align.CENTER)
        server_time_box.extend([self.server_timelabel, self.icon_indicator])

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
        flowbox.add(server_time_box)
        flowbox.add(self.picker)

        self.add(flowbox)

    def update_server_icon(self) -> None:
        icon = DAY_ICON if self.server_time.is_day() else NIGHT_ICON
        self.icon_indicator.set_icon_name(icon)

    def _on_server_clock_increment(self, emitter: Emitter, time_now: datetime) -> None:
        t = time_now.time().strftime("%H:%M")
        self.server_timelabel.set_text(t)
        self.update_server_icon()

    def _on_local_clock_increment(
        self, emitter: Emitter, time_now: datetime, elapsed: timedelta
    ) -> None:
        t = time_now.time().strftime(EXTENDED_TIME_FORMAT)
        self.local_timelabel.set_text(t)

    def _on_calculate_button_clicked(self, button: Gtk.Button) -> None:
        if (self.picker.get_values()) == (self.server_time.get_values()):
            total_time = timedelta(seconds=0)
            self.emitter.emit("target_time_reset", total_time)
        else:
            picker_time = self.picker.get_time()
            total_time = self.server_time.calc_delta(picker_time)
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
