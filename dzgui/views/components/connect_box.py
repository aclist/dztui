from dzgui.strings import preconnect
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk  # noqa E402


class ConnectBox(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        self.back = Gtk.Button(
            label=preconnect.back, halign=Gtk.Align.END, hexpand=True
        )

        # TODO: dynamically update this
        self.ok = Gtk.Button(label="Launch", halign=Gtk.Align.END)

        for button in self.back, self.ok:
            self.add(button)

    def get_back_button(self) -> Gtk.Button:
        return self.back

    def get_ok_button(self) -> Gtk.Button:
        return self.ok


class PreconnectBox(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            valign=Gtk.Align.END,
            vexpand=True,
            spacing=5,
        )

        self.button_hbox = ConnectBox()
        self.ok = self.button_hbox.get_ok_button()
        self.ok.set_label(preconnect.update_mods)

        self.connect_last = Gtk.Button(
            label=preconnect.connect_last,
            halign=Gtk.Align.END,
            tooltip_text=preconnect.connect_last_tooltip,
        )
        self.button_hbox.add(self.connect_last)

        self.raise_window = Gtk.CheckButton(
            # TODO: strings
            label="Foreground DZGUI while downloading",
            halign=Gtk.Align.END,
            hexpand=True,
            valign=Gtk.Align.END,
            visible=False,
            has_tooltip=True,
            sensitive=False,
            tooltip_text="Foreground the DZGUI window after mod downloads are queued",
            active=True,
        )
        self.add(self.button_hbox)
        self.add(self.raise_window)

    def get_back_button(self) -> Gtk.Button:
        return self.button_hbox.get_back_button()

    def get_ok_button(self) -> Gtk.Button:
        return self.ok
