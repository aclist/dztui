import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa

class Watcher(Gtk.Dialog):
    def __init__():
        super().__init__()
        pass

    def bump_progress(self):
        self.set_secondary_text("FOO")

#w = Watcher()
#thread = threading()
## compute here
#GLib.idle_add(self._bump_progress)
## raise window:
#Gdk.present_with_time(Gdk.CURRENT_TIME)
