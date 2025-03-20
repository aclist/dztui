import gi
import signal
import subprocess
import sys
import textwrap
import threading
import time
import os

user_path = os.path.expanduser('~')
fifo_path = '%s/.local/state/dzgui/dzg.fifo' %(user_path)
pid_path = "%s/.local/state/dzgui/dzg.pid" %(user_path)
FIFO = fifo_path

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango

main_app = "DZGUI"
app = "DZGUI Loader"
version = "5.6.0"


class Dialog(Gtk.MessageDialog):
    def __init__(self, parent):
        Gtk.MessageDialog.__init__(
                self,
                transient_for=parent,
                buttons=Gtk.ButtonsType.OK,
                flags=0,
                text="Some text",
                title=app,
                modal=True,
                )
        self.connect("delete-event", self._on_dialog_delete)
        self.set_size_request(1000, 0)
        self.set_title(app)

        self.set_default_response(Gtk.ResponseType.OK)

    def _on_dialog_delete(self, resp_id, some):
        return True


class OuterWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title=app)

        self.set_border_width(10)
        outervbox = Gtk.Box()
        outervbox.set_margin_top(50)
        outervbox.set_margin_start(50)
        outervbox.set_margin_end(50)
        outervbox.set_orientation(Gtk.Orientation.VERTICAL)

        self.model = Gtk.ListStore(str, str, str)
        self.treeview = Gtk.TreeView(model=self.model)
        columns = ["Process", "Result", "Color"]

        for i, column_title in enumerate(columns):
            renderer = Gtk.CellRendererText()
            if i == 1:
                renderer.set_property("weight", Pango.Weight.BOLD)
                column = Gtk.TreeViewColumn(column_title, renderer, text=i, foreground=2)
            else:
                column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            column.set_fixed_width(400)
            if i != 2:
                self.treeview.append_column(column)
        self.treeview.set_headers_visible(False)
        self.treeview.get_selection().set_select_function(self.select_function)

        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_propagate_natural_width(True)
        self.scrolled.set_vexpand(True)
        self.scrolled.set_hexpand(True)

        # vbox > label > button box > left buttons > right button
        self.early_cancel_box = Gtk.Box()
        self.early_cancel_box.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.cancel = Gtk.Button(label="Cancel")
        self.early_cancel_box.add(self.cancel)
        self.cancel.connect("clicked", self._on_cancel_clicked)

        self.box = Gtk.Box(halign=Gtk.Align.FILL)
        self.box.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.box2 = Gtk.Box(hexpand=True, halign=Gtk.Align.END)

        self.aa = Gtk.Button(label="Submit a bug report ⧉")
        self.cc = Gtk.Button(label="Exit")
        self.cc.connect("clicked", self._on_exit_clicked)
        self.box.add(self.aa)
        self.box.add(self.box2)
        self.box2.add(self.cc)
        self.box.set_spacing(10)
        self.box.set_margin_top(10)

        self.scrolled.add(self.treeview)
        self.label = Gtk.Label()
        self.label.set_text(main_app + " " + version)
        self.label2 = Gtk.Label()
        self.label2.set_text(main_app + " is starting up")
        self.label2.set_margin_top(10)
        self.label2.set_margin_bottom(10)
        self.spinner = Gtk.Spinner()
        self.spinner.start()

        self.aa.connect("clicked", self._on_button_clicked)

        self.spinner_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.spinner_box.add(self.label)
        self.spinner_box.add(Gtk.Separator())
        self.spinner_box.add(self.label2)
        self.spinner_box.add(self.spinner)
        self.pg = Gtk.ProgressBar()

        self.grid = Gtk.Grid()
        #self.grid.set_column_homogeneous(True)
        #self.grid.set_row_homogeneous(True)
        self.grid.attach(self.spinner_box, 0, 0, 4, 1)
        #self.grid.attach(self.scrolled, 0, 1, 4, 1)

        self.errors = Gtk.Box()
        self.errors_label = Gtk.Label()
        self.errors.add(self.errors_label)


        self.grid.attach_next_to(self.scrolled, self.spinner_box, Gtk.PositionType.BOTTOM, 4, 20)
        self.grid.attach_next_to(self.early_cancel_box, self.scrolled, Gtk.PositionType.BOTTOM, 4, 1)
        self.grid.attach_next_to(self.errors, self.scrolled, Gtk.PositionType.BOTTOM, 4, 1)
        self.grid.attach_next_to(self.box, self.early_cancel_box, Gtk.PositionType.BOTTOM, 4, 1)

        self.grid.set_row_spacing(20)
        self.add(self.grid)

        self.show_all()
        self.box.set_visible(False)
        self.errors.set_visible(False)

        self.thread = threading.Thread(target=self.log, args=())
        self.thread.start()

    def _on_cancel_clicked(self, button):
        with open (pid_path) as f:
            pid = int(f.read())
        os.kill(pid, signal.SIGUSR1)
        self.destroy()
        os.remove(FIFO)
        Gtk.main_quit()
        #self._on_exit_clicked(button)

    def _on_exit_clicked(self, button):
        self.destroy()
        os.remove(FIFO)
        Gtk.main_quit()

    def select_function(self, treeselection, model, path, current):
        state = True

    def scroll_to_end(self):
        adj = self.scrolled.get_vadjustment()
        adj.set_value(adj.get_upper() + adj.get_page_size())

    def log(self):
        d = ""
        def update_gui():
            tip = len(self.model)
            if (tip - 1) < 0:
                tip = 0
            else:
                tip = tip -1
            s = d.split("␞")
            label = s[1]
            match s[0]:
                case "RESULT":
                    if s[1] == "OK":
                        color = "#00FF00"
                        self.model[tip][1] = label
                        self.model[tip][2] = color
                    elif s[1] == "FAIL":
                        self.box.set_visible(True)
                        self.errors.set_visible(True)
                        color = "#FF0000"
                        self.model[tip][1] = label
                        self.model[tip][2] = color
                        self.early_cancel_box.set_visible(False)
                        self.errors_label.set_text(textwrap.fill(s[2], 100))
                        self.label2.set_text("Errors occurred: see details below.")
                        self.spinner.stop()
                    else:
                        color = "ORANGE"
                        self.model[tip][1] = label
                        self.model[tip][2] = color
                case "STATUS":
                    self.model.append([label, "", "#FF0000"])
                case "PROGRESS":
                    self.label2.set_text(s[1])
                case _:
                    return
            #FIXME: not scrolling down on failure msg
            self.scroll_to_end();

        while True:
            with open(FIFO) as fifo:
                newdata = fifo.read()
                if len(newdata) == 0:
                    break
                else:
                    d = newdata
                if d.startswith("EXIT"):
                    #TODO: some GTK errors when exiting and launching UI
                    self.destroy()
                    os.remove(FIFO)
                    Gtk.main_quit()
                    break
                else:
                    GLib.idle_add(update_gui)


    def _on_button_clicked(self, button):
        url="https://github.com/aclist/dztui/issues/new/choose"
        subprocess.Popen(['/usr/bin/env', 'bash', "xdg-open", url])


class App(Gtk.Application):
    def __init__(self):
        GLib.set_prgname("DZGUI Loader")

        self.win = OuterWindow()
        GLib.set_prgname("DZGUI Loader")

        Gtk.main()

def main():
    App()

if __name__ == '__main__':
    main()

