import textwrap

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402

class EarlyAlertDialog(Gtk.MessageDialog):
    def __init__(self, string):
        # TODO: strings
        super().__init__(
            title="DZGUI - Dialog",
            flags=0,
            text="ERROR",
            transient_for=None,
            buttons=Gtk.ButtonsType.OK
        )
        ok = self.action_area.get_children()[0]
        ok.set_label("OK")
        ok.connect("clicked", Gtk.main_quit)

        msg = textwrap.fill(string, 50)
        self.format_secondary_text(msg)

        self.action_area.set_margin_bottom(20)
        self.outer = self.get_content_area()
        self.outer.set_margin_start(30)
        self.outer.set_margin_end(30)

        self.set_default_size(250, 100)

        self.connect("delete-event", Gtk.main_quit)
        self.connect("destroy", Gtk.main_quit)

        self.show_all()
        Gtk.main()
