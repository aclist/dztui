import csv
import gi
import json
import locale
import logging
import math
import multiprocessing
import os
import re
import signal
import subprocess
import sys
import textwrap
import threading
import time

locale.setlocale(locale.LC_ALL, '')
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango
from enum import Enum

# 5.3.3
app_name = "DZGUI"

start_time = 0

cache = {}
config_vals = []
stored_keys = []
toggled_checks = []
server_filters = []
delimiter = "␞"
selected_map = ["Map=All maps"]
keyword_filter = ["Keyword%s" %(delimiter)]

checks = list()
map_store = Gtk.ListStore(str)
row_store = Gtk.ListStore(str)
modlist_store = Gtk.ListStore(str, str, str)
#cf. mod_cols
mod_store = Gtk.ListStore(str, str, str, float)
#cf. log_cols
log_store = Gtk.ListStore(str, str, str, str)
#cf. browser_cols
server_store = Gtk.ListStore(str, str, str, str, int, int, int, str, int)

default_tooltip = "Select a row to see its detailed description"
server_tooltip = [None, None]

user_path = os.path.expanduser('~')
state_path = '%s/.local/state/dzgui' %(user_path)
helpers_path = '%s/.local/share/dzgui/helpers' %(user_path)
log_path = '%s/logs' %(state_path)
changelog_path = '%s/CHANGELOG.md' %(state_path)
geometry_path = '%s/dzg.cols.json' %(state_path)
funcs = '%s/funcs' %(helpers_path)

logger = logging.getLogger(__name__)
log_file = '%s/DZGUI_DEBUG.log' %(log_path)
system_log = '%s/DZGUI_SYSTEM.log' %(log_path)
FORMAT = "%(asctime)s␞%(levelname)s␞%(filename)s::%(funcName)s::%(lineno)s␞%(message)s"
logging.basicConfig(filename=log_file,
   format=FORMAT,
level=logging.DEBUG)

browser_cols = [
    "Name",
    "Map",
    "Perspective",
    "Gametime",
    "Players",
    "Maximum",
    "Queue",
    "IP",
    "Qport",
]
mod_cols = [
    "Mod",
    "Symlink",
    "Dir",
    "Size (MiB)"
]
log_cols = [
    "Timestamp",
    "Flag",
    "Traceback",
    "Message"
]
connect = [
    ("Server browser",),
    ("My saved servers",),
    ("Quick-connect to favorite server",),
    ("Recent servers",),
    ("Connect by IP",),
    ("Connect by ID",),
    ("Scan LAN servers",)
]
manage = [
    ("Add server by IP",),
    ("Add server by ID",),
    ("Change favorite server",),
]
options = [
    ("List installed mods",),
    ("Toggle release branch",),
    ("Toggle mod install mode",),
    ("Toggle Steam/Flatpak",),
    ("Change player name",),
    ("Change Steam API key",),
    ("Change Battlemetrics API key",),
    ("Force update local mods",),
    ("Output system info to log file",)
]
help = [
    ("View changelog",),
    ("Show debug log",),
    ("Help file ⧉",),
    ("Report a bug ⧉",),
    ("Forum ⧉",),
    ("Sponsor ⧉",),
    ("Hall of fame ⧉",),
]
filters = {
    "1PP": True,
    "3PP": True,
    "Day": True,
    "Night": True,
    "Empty": False,
    "Full": False,
    "Low pop": True,
    "Non-ASCII": False,
    "Duplicate": False
}
side_buttons = [
    "Main menu",
    "Manage",
    "Options",
    "Help",
    "Exit"
]
status_tooltip = {
    "Server browser": "Used to browse the global server list",
    "My saved servers": "Browse your saved servers. Unreachable/offline servers will be excluded",
    "Quick-connect to favorite server": "Connect to your favorite server",
    "Recent servers": "Shows the last 10 servers you connected to (includes attempts)",
    "Connect by IP": "Connect to a server by IP",
    "Connect by ID": "Connect to a server by Battlemetrics ID",
    "Scan LAN servers": "Search for servers on your local network",
    "Add server by IP": "Add a server by IP",
    "Add server by ID": "Add a server by Battlemetrics ID",
    "Change favorite server": "Update your quick-connect server",
    "List installed mods": "Browse a list of locally-installed mods",
    "Toggle release branch": "Switch between stable and testing branches",
    "Toggle mod install mode": "Switch between manual and auto mod installation",
    "Toggle Steam/Flatpak": "Switch the preferred client to use for launching DayZ",
    "Change player name": "Update your in-game name (required by some servers)",
    "Change Steam API key": "Can be used if you revoked an old API key",
    "Change Battlemetrics API key": "Can be used if you revoked an old API key",
    "Force update local mods": "Synchronize the signatures of all local mods with remote versions (experimental)",
    "Output system info to log file": "Generates a system log for troubleshooting",
    "View changelog": "Opens the DZGUI changelog in a dialog window",
    "Show debug log": "Read the DZGUI log generated since startup",
    "Help file ⧉": "Opens the DZGUI documentation in a browser",
    "Report a bug ⧉": "Opens the DZGUI issue tracker in a browser",
    "Forum ⧉": "Opens the DZGUI discussion forum in a browser",
    "Sponsor ⧉": "Sponsor the developer of DZGUI",
    "Hall of fame ⧉": "A list of significant contributors and testers",
}


def format_ping(ping):
    ms = " | Ping: %s" %(ping)
    return ms

def format_distance(distance):
    if distance == "Unknown":
        distance = "| Distance: %s" %(distance)
    else:
        d = int(distance)
        formatted = f'{d:n}'
        distance = "| Distance: %s km" %(formatted)
    return distance


def set_surrounding_margins(widget, margin):
    widget.set_margin_top(margin)
    widget.set_margin_start(margin)
    widget.set_margin_end(margin)


def parse_modlist_rows(data):
    lines = data.stdout.splitlines()
    hits = len(lines)
    reader = csv.reader(lines, delimiter=delimiter)
    try:
        rows = [[row[0], row[1], row[2]] for row in reader if row]
    except IndexError:
        return 1
    for row in rows:
        modlist_store.append(row)
    return hits

def parse_log_rows(data):
    lines = data.stdout.splitlines()
    reader = csv.reader(lines, delimiter=delimiter)
    try:
        rows = [[row[0], row[1], row[2], row[3]] for row in reader if row]
    except IndexError:
        return 1
    for row in rows:
        log_store.append(row)

def parse_mod_rows(data):
    # GTK pads trailing zeroes on floats
    # https://stackoverflow.com/questions/26827434/gtk-cellrenderertext-with-format
    sum = 0
    lines = data.stdout.splitlines()
    hits = len(lines)
    reader = csv.reader(lines, delimiter=delimiter)
    try:
        rows = [[row[0], row[1], row[2], locale.atof(row[3], func=float)] for row in reader if row]
    except IndexError:
        return 1
    for row in rows:
        mod_store.append(row)
        size = float(row[3])
        sum += size
    return [sum, hits]


def parse_server_rows(data):
    sum = 0
    lines = data.stdout.splitlines()
    reader = csv.reader(lines, delimiter=delimiter)
    hits = len(lines)
    try:
        rows = [[row[0], row[1], row[2], row[3], int(row[4]), int(row[5]), int(row[6]), row[7], int(row[8])] for row in reader if row]
    except IndexError:
        return 1
    for row in rows:
        server_store.append(row)
        players = int(row[4])
        sum += players
    return [sum, hits]


def query_config(widget, key=""):
    proc = call_out(widget, "query_config", key)
    config = list(proc.stdout.splitlines())
    return (config)


def call_out(widget, command, *args):
    if widget is not None:
        widget_name = widget.get_name()
        try:
            widget_name = widget_name.split('+')[1]
            match widget_name:
                case "TreeView":
                    context = widget.get_first_col()
                case "ScrollableTree":
                    context = widget.treeview.get_first_col()
                case "OuterWindow":
                    context = widget.grid.scrollable_treelist.treeview.get_first_col()
                case "Grid":
                    context = widget.scrollable_treelist.treeview.get_first_col()
        except IndexError:
            context = "Generic"
    else:
        context = "Generic"

    arg_ar = []
    for i in args:
        arg_ar.append(i)
    logger.info("Context '%s' calling subprocess '%s' with args '%s'" %(context, command, arg_ar))
    proc = subprocess.run(["/usr/bin/env", "bash", funcs, command] + arg_ar, capture_output=True, text=True)
    return proc


def spawn_dialog(transient_parent, msg, mode):
    dialog = GenericDialog(transient_parent, msg, mode)
    response = dialog.run()
    dialog.destroy()
    match response:
        case Gtk.ResponseType.OK:
            logger.info("User confirmed dialog with message '%s'" %(msg))
            return 0
        case Gtk.ResponseType.CANCEL | Gtk.ResponseType.DELETE_EVENT:
            logger.info("User aborted dialog with message '%s'" %(msg))
            return 1


def process_shell_return_code(transient_parent, msg, code, original_input):
    match code:
            #TODO: add logger output to each
        case 0:
            # success with notice popup
            spawn_dialog(transient_parent, msg, "NOTIFY")
        case 1:
            # error with notice popup
            if msg == "":
                msg = "Something went wrong"
            spawn_dialog(transient_parent, msg, "NOTIFY")
        case 2:
            # warn and recurse (e.g. validation failed)
            spawn_dialog(transient_parent, msg, "NOTIFY")
            treeview = transient_parent.grid.scrollable_treelist.treeview
            process_tree_option(original_input, treeview)
        case 4:
            # for BM only
            spawn_dialog(transient_parent, msg, "NOTIFY")
            treeview = transient_parent.grid.scrollable_treelist.treeview
            process_tree_option(["Options", "Change Battlemetrics API key"], treeview)
        case 5:
            # for steam only
            spawn_dialog(transient_parent, msg, "NOTIFY")
            treeview = transient_parent.grid.scrollable_treelist.treeview
            process_tree_option(["Options", "Change Steam API key"], treeview)
        case 6:
            # return silently
            pass
        case 90:
            # used to update configs and metadata in-place
            treeview = transient_parent.grid.scrollable_treelist.treeview
            col = treeview.get_column_at_index(0)
            config_vals.clear()
            for i in query_config(None):
                config_vals.append(i)
            tooltip = format_metadata(col)
            transient_parent.grid.update_statusbar(tooltip)
            spawn_dialog(transient_parent, msg, "NOTIFY")
            return
        case 100:
            # final handoff before launch
            final_conf = spawn_dialog(transient_parent, msg, "CONFIRM")
            treeview = transient_parent.grid.scrollable_treelist.treeview
            if final_conf == 1 or final_conf is None:
                return
            process_tree_option(["Handshake", ""], treeview)
        case 255:
            spawn_dialog(transient_parent, "Update complete. Please close DZGUI and restart.", "NOTIFY")
            Gtk.main_quit()


def process_tree_option(input, treeview):
    context = input[0]
    command = input[1]
    logger.info("Parsing tree option '%s' for the context '%s'" %(command, context))

    transient_parent = treeview.get_outer_window()
    toggle_contexts = ["Toggle mod install mode", "Toggle release branch", "Toggle Steam/Flatpak"]

    def call_on_thread(bool, subproc, msg, args):
        def _background(subproc, args, dialog):
            def _load():
                wait_dialog.destroy()
                out = proc.stdout.splitlines()
                msg = out[-1]
                rc = proc.returncode
                logger.info("Subprocess returned code %s with message '%s'" %(rc, msg))
                process_shell_return_code(transient_parent, msg, rc, input)
            proc = call_out(transient_parent, subproc, args)
            GLib.idle_add(_load)
        if bool is True:
            wait_dialog = GenericDialog(transient_parent, msg, "WAIT")
            wait_dialog.show_all()
            thread = threading.Thread(target=_background, args=(subproc, args, wait_dialog))
            thread.start()
        else:
            # False is used to bypass wait dialogs
            proc = call_out(transient_parent, subproc, args)
            rc = proc.returncode
            out = proc.stdout.splitlines()
            msg = out[-1]
            process_shell_return_code(transient_parent, msg, rc, input)


    match context:
        case "Help":
            if command == "View changelog":
                diag = ChangelogDialog(transient_parent, '', "Changelog -- content can be scrolled")
                diag.run()
                diag.destroy()
            else:
                # non-blocking subprocess
                subprocess.Popen(['/usr/bin/env', 'bash', funcs, "Open link", command])
        case "Handshake":
            call_on_thread(True, context, "Waiting for DayZ", command)
        case _:
            if command == "Output system info to log file":
                call_on_thread(True, "gen_log", "Generating log", "")
            elif command == "Force update local mods":
                call_on_thread(True, "force_update", "Updating mods", "")
            elif command == "Quick-connect to favorite server":
                call_on_thread(True, command, "Working", "")
            elif command in toggle_contexts:
                if command == "Toggle release branch":
                    call_on_thread(False, "toggle", "Updating DZGUI branch", command)
                else:
                    proc = call_out(transient_parent, "toggle", command)
                    grid = treeview.get_parent().get_parent()
                    grid.update_right_statusbar()
                    tooltip = format_metadata(command)
                    transient_parent.grid.update_statusbar(tooltip)
            else:
                # This branch is only used by interactive dialogs
                match command:
                    case "Connect by IP" | "Add server by IP" | "Change favorite server":
                        flag = True
                        link_label = ""
                        prompt = "Enter IP in IP:Queryport format (e.g. 192.168.1.1:27016)"
                    case "Connect by ID" | "Add server by ID":
                        flag = True
                        link_label = "Open Battlemetrics"
                        prompt = "Enter server ID"
                    case "Change player name":
                        flag = False
                        link_label = ""
                        prompt = "Enter new nickname"
                    case "Change Steam API key":
                        flag = True
                        link_label = "Open Steam API page"
                        prompt = "Enter new API key"
                    case "Change Battlemetrics API key":
                        flag = True
                        link_label = "Open Battlemetrics API page"
                        prompt = "Enter new API key"

                user_entry = EntryDialog(transient_parent, prompt, "ENTRY", link_label)
                res = user_entry.get_input()
                if res is None:
                    logger.info("User aborted entry dialog")
                    return
                logger.info("User entered: '%s'" %(res))

                call_on_thread(flag, command, "Working", res)


def reinit_checks():
    toggled_checks.clear()
    for check in checks:
        label = check.get_label()
        if filters[label] is True:
            check.set_active(True)
            toggled_checks.append(label)
        else:
            check.set_active(False)


class OuterWindow(Gtk.Window):
    def __init__(self, is_steam_deck, is_game_mode):
        super().__init__(title=app_name)

        self.connect("delete-event", self.halt_proc_and_quit)
        # Deprecated in GTK 4.0
        self.set_border_width(10)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)

        """
        app > win > grid > scrollable > treeview [row/server/mod store]
        app > win > grid > vbox > buttonbox > filterpanel > combo [map store]
        """
        self.grid = Grid(is_steam_deck)
        self.add(self.grid)
        if is_game_mode is True:
            self.fullscreen()
        else:
            self.maximize()

        # Hide FilterPanel on main menu
        self.show_all()
        self.grid.right_panel.set_filter_visibility(False)
        self.grid.scrollable_treelist.treeview.grab_focus()

    def halt_proc_and_quit(self, window, event):
        self.grid.terminate_treeview_process()
        Gtk.main_quit()


class ScrollableTree(Gtk.ScrolledWindow):
    def __init__(self, is_steam_deck):
        super().__init__()

        self.treeview = TreeView(is_steam_deck)
        self.add(self.treeview)


class RightPanel(Gtk.Box):
    def __init__(self, is_steam_deck):
        super().__init__(spacing=6)
        self.set_orientation(Gtk.Orientation.VERTICAL)

        self.button_vbox = ButtonBox(is_steam_deck)
        self.filters_vbox = FilterPanel()
        toggle_signal(self.filters_vbox, self.filters_vbox.maps_combo, '_on_map_changed', False)

        self.pack_start(self.button_vbox, False, False, 0)
        self.pack_start(self.filters_vbox, False, False, 0)

        self.debug_toggle = Gtk.ToggleButton(label="Debug mode")
        if query_config(None, "debug")[0] == '1':
            self.debug_toggle.set_active(True)
        self.debug_toggle.connect("toggled", self._on_button_toggled, "Toggle debug mode")
        set_surrounding_margins(self.debug_toggle, 10)

        self.question_button = Gtk.Button(label="?")
        self.question_button.set_margin_top(10)
        self.question_button.set_margin_start(50)
        self.question_button.set_margin_end(50)
        self.question_button.connect("clicked", self._on_button_clicked)

        self.pack_start(self.debug_toggle, False, True, 0)
        if is_steam_deck is False:
            self.pack_start(self.question_button, False, True, 0)

    def _on_button_toggled(self, button, command):
        grid = self.get_parent()
        transient_parent = grid.get_parent()
        call_out(transient_parent, "toggle", command)
        grid.update_right_statusbar()
        grid.scrollable_treelist.treeview.grab_focus()

    def _on_button_clicked(self, button):
        grid = self.get_parent()
        grid.scrollable_treelist.treeview.spawn_keys_dialog(button)

    def set_filter_visibility(self, bool):
        self.filters_vbox.set_visible(bool)

    def focus_button_box(self):
        self.button_vbox.focus_button(0)

    def set_active_combo(self):
        self.filters_vbox.set_active_combo()


class ButtonBox(Gtk.Box):
    def __init__(self, is_steam_deck):
        super().__init__(spacing=6)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        set_surrounding_margins(self, 10)

        self.buttons = list()
        for side_button in side_buttons:
            button = Gtk.Button(label=side_button)
            if is_steam_deck is True:
                button.set_size_request(10, 10)
            else:
                button.set_size_request(50,50)
            button.set_opacity(0.6)
            self.buttons.append(button)
            button.connect("clicked", self._on_selection_button_clicked)
            self.pack_start(button, False, False, True)

        self.buttons[0].set_opacity(1.0)

    def _update_single_column(self, context):
        logger.info("Returning from multi-column view to monocolumn view for the context '%s'" %(context))
        treeview = self.get_treeview()
        right_panel = self.get_parent()
        right_panel.set_filter_visibility(False)

        """Block maps combo when returning to main menu"""
        toggle_signal(right_panel.filters_vbox, right_panel.filters_vbox.maps_combo, '_on_map_changed', False)
        right_panel.filters_vbox.keyword_entry.set_text("")
        keyword_filter.clear()
        keyword_filter.append("Keyword␞")
        server_store.clear()

        for column in treeview.get_columns():
            treeview.remove_column(column)
        for i, column_title in enumerate([context]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            treeview.append_column(column)
        self._populate(context)
        treeview.set_model(row_store)
        treeview.grab_focus()

    def _populate(self, context):
        match context:
            case 'Manage': array_context = manage
            case 'Main menu': array_context = connect
            case 'Options': array_context = options
            case 'Help': array_context = help
        row_store.clear()
        status = array_context[0][0]
        treeview = self.get_treeview()
        grid = self.get_parent().get_parent()

        for items in array_context:
            row_store.append(list(items))
        grid.update_statusbar(status_tooltip[status])
        treeview.grab_focus()

    def _on_selection_button_clicked(self, button):
        treeview = self.get_treeview()
        toggle_signal(treeview, treeview.selected_row, '_on_tree_selection_changed', False)
        context = button.get_label()
        logger.info("User clicked '%s'" %(context))

        if context == "Exit":
            logger.info("Normal user exit")
            Gtk.main_quit()
        cols = treeview.get_columns()

        if len(cols) > 1:
            self._update_single_column(context)

        # Highlight the active widget
        for inactive_button in self.buttons:
            inactive_button.set_opacity(0.6)
        button.set_opacity(1.0)

        for col in cols:
            col.set_title(context)

        self._populate(context)

        toggle_signal(treeview, treeview.selected_row, '_on_tree_selection_changed', True)

    def focus_button(self, index):
        self.buttons[index].grab_focus()

    def get_treeview(self):
        grid = self.get_parent().get_parent()
        treeview = grid.scrollable_treelist.treeview
        return treeview


class CalcDist(multiprocessing.Process):
    def __init__(self, widget, addr, result_queue, cache):
        super().__init__()

        self.widget = widget
        self.result_queue = result_queue
        self.addr = addr
        self.ip = addr.split(':')[0]

    def run(self):
        if self.addr in cache:
            logger.info("Address '%s' already in cache" %(self.addr))
            self.result_queue.put([self.addr, cache[self.addr][0], cache[self.addr][1]])
            return
        proc = call_out(self.widget, "get_dist", self.ip)
        proc2 = call_out(self.widget, "test_ping", self.ip)
        km = proc.stdout
        ping = proc2.stdout
        self.result_queue.put([self.addr, km, ping])


class TreeView(Gtk.TreeView):
    __gsignals__ = {"on_distcalc_started": (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self, is_steam_deck):
        super().__init__()

        self.queue = multiprocessing.Queue()
        self.current_proc = None

        # Disables typeahead search
        self.set_enable_search(False)
        self.set_search_column(-1)

        # Populate model with initial context
        for rows in connect:
            row_store.append(list(rows))
        self.set_model(row_store)

        for i, column_title in enumerate(
            ["Main menu"]
        ):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            self.append_column(column)

        self.connect("row-activated", self._on_row_activated)
        self.connect("key-press-event", self._on_keypress)
        self.connect("key-press-event", self._on_keypress_main_menu)
        toggle_signal(self, self, '_on_keypress', False)

        self.selected_row = self.get_selection()
        self.selected_row.connect("changed", self._on_tree_selection_changed)
        self.connect("button-release-event", self._on_button_release)

    def terminate_process(self):
        if self.current_proc and self.current_proc.is_alive():
            self.current_proc.terminate()

    def _on_menu_click(self, menu_item):
        parent = self.get_outer_window()
        context = self.get_first_col()
        value = self.get_column_at_index(0)
        context_menu_label = menu_item.get_label()
        logger.info("User clicked context menu '%s'" %(context_menu_label))

        match context_menu_label:
            case "Add to my servers" | "Remove from my servers":
                record = "%s:%s" %(self.get_column_at_index(7), self.get_column_at_index(8))
                proc = call_out(parent, context_menu_label, record)
                if context == "Name (My saved servers)":
                    iter = self.get_current_iter()
                    server_store.remove(iter)
                msg = proc.stdout
                res = spawn_dialog(parent, msg, "NOTIFY")
            case "Remove from history":
                record = "%s:%s" %(self.get_column_at_index(7), self.get_column_at_index(8))
                call_out(parent, context_menu_label, record)
                iter = self.get_current_iter()
                server_store.remove(iter)
            case "Copy IP to clipboard":
                self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
                addr = self.get_column_at_index(7)
                qport = self.get_column_at_index(8)
                ip = addr.split(':')[0]
                record = "%s:%s" %(ip, qport)
                self.clipboard.set_text(record, -1)
            case "Refresh player count":
                self.refresh_player_count()
            case "Show server-side mods":
                record = "%s:%s" %(self.get_column_at_index(7), self.get_column_at_index(8))
                dialog = ModDialog(parent, "Enter/double click a row to open in Steam Workshop. ESC exits this dialog", "Modlist", record)
                modlist_store.clear()
            case "Delete mod":
                conf_msg = "Really delete the mod '%s'?" %(value)
                success_msg = "Successfully deleted the mod '%s'." %(value)
                fail_msg = "An error occurred during deletion. Aborting."
                res = spawn_dialog(parent, conf_msg, "CONFIRM")
                symlink = self.get_column_at_index(1)
                dir = self.get_column_at_index(2)
                if res == 0:
                    proc = call_out(parent, "delete", symlink, dir)
                    if proc.returncode == 0:
                        spawn_dialog(parent, success_msg, "NOTIFY")
                        self._update_quad_column("List installed mods")
                    else:
                        spawn_dialog(parent, fail_msg, "NOTIFY")
            case "Open in Steam Workshop":
                record = self.get_column_at_index(2)
                call_out(parent, "open_workshop_page", record)

    def _on_button_release(self, widget, event):
        try:
            pathinfo = self.get_path_at_pos(event.x, event.y)
            if pathinfo is None:
                return
            (path, col, cellx, celly) = pathinfo
            self.set_cursor(path,col,0)
        except AttributeError:
            pass

        if event.type is Gdk.EventType.BUTTON_RELEASE and event.button != 3:
            return
        context = self.get_first_col()
        self.menu = Gtk.Menu()

        mod_context_items = ["Open in Steam Workshop", "Delete mod"]
        subcontext_items = {"Server browser": ["Add to my servers", "Copy IP to clipboard", "Show server-side mods", "Refresh player count"],
                  "My saved servers": ["Remove from my servers", "Copy IP to clipboard", "Show server-side mods", "Refresh player count"],
                  "Recent servers": ["Remove from history", "Copy IP to clipboard", "Show server-side mods", "Refresh player count"],
                  }
        # submenu hierarchy https://stackoverflow.com/questions/52847909/how-to-add-a-sub-menu-to-a-gtk-menu
        if context == "Mod":
            items = mod_context_items
            subcontext = "List installed mods"
        elif "Name" in context:
            subcontext = context.split('(')[1].split(')')[0]
            items = subcontext_items[subcontext]
        else:
            return

        for item in items:
            if subcontext == "Server browser" and item == "Add to my servers":
                record = "%s:%s" %(self.get_column_at_index(7), self.get_column_at_index(8))
                proc = call_out(widget, "is_in_favs", record)
                if proc.returncode == 0:
                    item = "Remove from my servers"
            item = Gtk.MenuItem(label=item)
            item.connect("activate", self._on_menu_click)
            self.menu.append(item)

        self.menu.show_all()

        if event.type is Gdk.EventType.KEY_PRESS and event.keyval is Gdk.KEY_l:
            self.menu.popup_at_widget(widget, Gdk.Gravity.CENTER, Gdk.Gravity.WEST)
        else:
            self.menu.popup_at_pointer(event)

    def refresh_player_count(self):
        parent = self.get_outer_window()

        global start_time
        then = start_time
        now = time.monotonic()
        diff = now - then
        cooldown = 30 - math.floor(diff)
        if ((start_time > 0) and (now - then) < 30):
            spawn_dialog(parent, "Global refresh cooldown not met. Wait %s second(s)." %(str(cooldown)), "NOTIFY")
            return
        start_time = now

        thread = threading.Thread(target=self._background_player_count, args=())
        thread.start()

    def get_outer_window(self):
        win = self.get_parent().get_parent().get_parent()
        return win

    def get_outer_grid(self):
        grid = self.get_parent().get_parent()
        return grid

    def get_current_iter(self):
        iter = self.get_selection().get_selected()[1]
        return iter

    def get_current_index(self):
        index = treeview.get_selection().get_selected_rows()[1][0][0]
        return index

    def _on_tree_selection_changed(self, selection):
        grid = self.get_outer_grid()
        context = self.get_first_col()
        row_sel = self.get_column_at_index(0)
        if context == "Mod" or context == "Timestamp":
            return
        logger.info("Tree selection for context '%s' changed to '%s'" %(context, row_sel))

        if self.current_proc and self.current_proc.is_alive():
            self.current_proc.terminate()

        if "Name" in context:
            addr = self.get_column_at_index(7)
            if addr is None:
                return
            if addr in cache:
                dist = format_distance(cache[addr][0])
                ping = format_ping(cache[addr][1])

                tooltip = server_tooltip[0] + dist + ping
                grid.update_statusbar(tooltip)
                return
            self.emit("on_distcalc_started")
            self.current_proc = CalcDist(self, addr, self.queue, cache)
            self.current_proc.start()
        elif None:
            return
        else:
            tooltip = format_metadata(row_sel)
            grid.update_statusbar(tooltip)

    def spawn_keys_dialog(self, widget):
        diag = KeysDialog(self.get_outer_window(), '', "Keybindings")
        diag.run()
        diag.destroy()
        self.grab_focus()

    def _on_keypress_main_menu(self, treeview, event):
        window = self.get_outer_window()
        grid = self.get_outer_grid()
        match event.keyval:
            case Gdk.KEY_d:
                debug = grid.right_panel.debug_toggle
                if debug.get_active():
                    debug.set_active(False)
                else:
                    debug.set_active(True)
            case Gdk.KEY_Right:
                grid.right_panel.focus_button_box()
            case Gdk.KEY_question:
                if event.state is Gdk.ModifierType.SHIFT_MASK:
                    self.spawn_keys_dialog(None)
            case Gdk.KEY_f:
                if event.state is Gdk.ModifierType.CONTROL_MASK:
                    return True
            case _:
                return False

    def _on_keypress(self, treeview, event):
        keyname = Gdk.keyval_name(event.keyval)
        grid = self.get_outer_grid()
        cur_proc = grid.scrollable_treelist.treeview.current_proc
        if event.state is Gdk.ModifierType.CONTROL_MASK:
            match event.keyval:
                case Gdk.KEY_l:
                    self._on_button_release(self, event)
                case Gdk.KEY_r:
                    self.refresh_player_count()
                case Gdk.KEY_f:
                    if self.get_first_col() == "Mod":
                        return
                    grid.right_panel.filters_vbox.grab_keyword_focus()
                case Gdk.KEY_m:
                    if self.get_first_col() == "Mod":
                        return
                    grid.right_panel.filters_vbox.maps_combo.grab_focus()
                    grid.right_panel.filters_vbox.maps_combo.popup()
                case _:
                    return False
        elif keyname.isnumeric() and int(keyname) > 0:
            if self.get_first_col() == "Mod":
                return
            digit = (int(keyname) - 1)
            grid.right_panel.filters_vbox.toggle_check(checks[digit])
        else:
            return False

    def get_column_at_index(self, index):
        select = self.get_selection()
        sels = select.get_selected_rows()
        (model, pathlist) = sels
        if len(pathlist) < 1:
            return
        path = pathlist[0]
        tree_iter = model.get_iter(path)
        value = model.get_value(tree_iter, index)
        return value

    def _background_player_count(self):
        def _load():
            lines = data.stdout.splitlines()
            #update players
            server_store[path][4] = int(lines[0])
            #update queue
            server_store[path][6] = int(lines[1])
            wait_dialog.destroy()

        parent = self.get_outer_window()
        wait_dialog = GenericDialog(parent, "Refreshing player count", "WAIT")
        wait_dialog.show_all()
        select = self.get_selection()
        sels = select.get_selected_rows()
        (model, pathlist) = sels
        if len(pathlist) < 1:
            return
        path = pathlist[0]
        tree_iter = model.get_iter(path)
        addr = server_store[path][7]
        qport = server_store[path][8]
        ip = addr.split(':')[0]
        qport = str(qport)

        data = call_out(self, "get_player_count", ip, qport)
        if data.returncode == 1:
            wait_dialog.destroy()
            return
        GLib.idle_add(_load)

    def _background(self, dialog, mode):
        def loadTable():
            for map in maps:
                map_store.append([map])
            toggle_signal(self, self.selected_row, '_on_tree_selection_changed', True)
            right_panel.set_filter_visibility(True)
            dialog.destroy()
            self.grab_focus()
            for column in self.get_columns():
                column.connect("notify::width", self._on_col_width_changed)
            if hits == 0:
                call_out(self, "start_cooldown", "", "")
                api_warn_msg = """\
                    No servers returned. Possible network issue or API key on cooldown?
                    Return to the main menu, wait 60s, and try again.
                    If this issue persists, your API key may be defunct."""
                spawn_dialog(self.get_outer_window(), textwrap.dedent(api_warn_msg), "NOTIFY")

        grid = self.get_outer_grid()
        right_panel = grid.right_panel

        filters = toggled_checks + keyword_filter + selected_map
        data = call_out(self, "dump_servers", mode, *filters)

        toggle_signal(self, self.selected_row, '_on_tree_selection_changed', False)
        row_metadata = parse_server_rows(data)
        sum = row_metadata[0]
        hits = row_metadata[1]
        server_tooltip[0] = format_tooltip(sum, hits)
        grid.update_statusbar(server_tooltip[0])

        map_data = call_out(self, "get_unique_maps", mode)
        maps = map_data.stdout.splitlines()
        self.set_model(server_store)
        GLib.idle_add(loadTable)

    def _background_quad(self, dialog, mode):
        def load():
            dialog.destroy()
            self.set_model(mod_store)
            self.grab_focus()
            size = locale.format_string('%.3f', total_size, grouping=True)
            grid.update_statusbar("Found %s mods taking up %s MiB" %(f'{total_mods:n}', size))
            toggle_signal(self, self, '_on_keypress', True)

        grid = self.get_outer_grid()
        right_panel = grid.right_panel

        right_panel.set_filter_visibility(False)
        data = call_out(self, "list_mods", mode)
        result = parse_mod_rows(data)
        total_size = result[0]
        total_mods = result[1]
        GLib.idle_add(load)

    def _on_col_width_changed(self, col, width):

        def write_json(title, size):
            data = {"cols": { title: size } }
            j = json.dumps(data, indent=2)
            with open(geometry_path, "w") as outfile:
                outfile.write(j)
            logger.info("Wrote initial column widths to '%s'" %(geometry_path))

        title = col.get_title()
        size = col.get_width()
        if "Name" in title:
            title = "Name"

        if os.path.isfile(geometry_path):
            with open(geometry_path, "r") as infile:
                try:
                    data = json.load(infile)
                    data["cols"][title] = size
                    with open(geometry_path, "w") as outfile:
                        outfile.write(json.dumps(data, indent=2))
                except json.decoder.JSONDecodeError:
                    logger.critical("JSON decode error in '%s'" %(geometry_path))
                    write_json(title, size)
        else:
            write_json(title, size)

    def _update_multi_column(self, mode):
        # Local server lists may have different filter toggles from remote list
        # FIXME: tree selection updates twice here. attach signal later
        toggle_signal(self, self.selected_row, '_on_tree_selection_changed', False)
        # toggle_signal(self, self.selected_row, '_on_check_toggled', False)
        for column in self.get_columns():
            self.remove_column(column)
        row_store.clear()

        if os.path.isfile(geometry_path):
            with open(geometry_path, "r") as infile:
                try:
                    data = json.load(infile)
                    valid_json = True
                except json.decoder.JSONDecodeError:
                    logger.critical("JSON decode error in '%s'" %(geometry_path))
                    valid_json = False
        else:
            valid_json = False

        for i, column_title in enumerate(browser_cols):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            column.set_resizable(True)
            column.set_sort_column_id(i)

            if valid_json:
                if "Name" in column_title:
                    column_title = "Name"
                saved_size = data["cols"][column_title]
                column.set_fixed_width(saved_size)
            else:
                if ("Name" in column_title):
                    column.set_fixed_width(800)
                if (column_title == "Map"):
                    column.set_fixed_width(300)

            self.append_column(column)

        self.update_first_col(mode)
        transient_parent = self.get_outer_window()

        for check in checks:
            toggle_signal(self.get_outer_grid().right_panel.filters_vbox, check, '_on_check_toggle', True)
        toggle_signal(self, self, '_on_keypress', True)

        if mode == "Scan LAN servers":
            lan_dialog = LanButtonDialog(self.get_outer_window())
            port = lan_dialog.get_selected_port()
            if port is None:
                grid = self.get_outer_grid()
                right_panel = grid.right_panel
                vbox = right_panel.button_vbox
                vbox._update_single_column("Main menu")
                return
            mode = mode + ":" + port

        wait_dialog = GenericDialog(transient_parent, "Fetching server metadata", "WAIT")
        wait_dialog.show_all()
        thread = threading.Thread(target=self._background, args=(wait_dialog, mode))
        thread.start()

    def update_first_col(self, title):
        for col in self.get_columns():
            old_title = col.get_title()
            col.set_title("%s (%s)" %(old_title, title))
            break

    def get_first_col(self):
        for col in self.get_columns():
            cur_col = col.get_title()
            break
        return cur_col

    def _format_float(self, column, cell, model, iter, data):
        # https://docs.huihoo.com/pygtk/2.0-tutorial/sec-CellRenderers.html
        val = model[iter][3]
        formatted = locale.format_string('%.3f', val, grouping=True)
        cell.set_property('text', formatted)
        return

    def _update_quad_column(self, mode):
        # toggle_signal(self, self.selected_row, '_on_tree_selection_changed', False)
        for column in self.get_columns():
            self.remove_column(column)

        mod_store.clear()
        log_store.clear()

        if mode == "List installed mods":
            cols = mod_cols
            self.set_model(mod_store)
        else:
            cols = log_cols
            self.set_model(log_store)

        for i, column_title in enumerate(cols):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            if mode == "List installed mods":
                if i == 3:
                    column.set_cell_data_func(renderer, self._format_float, func_data=None)
            column.set_sort_column_id(i)
            #if (column_title == "Name"):
            #    column.set_fixed_width(600)
            self.append_column(column)

        if mode == "List installed mods":
            pass
        else:
            data = call_out(self, "show_log")
            res = parse_log_rows(data)
            if res == 1:
                spawn_dialog(self.get_outer_window(), "Failed to load log file, possibly corrupted", "NOTIFY")
            return

        transient_parent = self.get_outer_window()

        wait_dialog = GenericDialog(transient_parent, "Checking mods", "WAIT")
        wait_dialog.show_all()
        thread = threading.Thread(target=self._background_quad, args=(wait_dialog, mode))
        thread.start()

    def _background_connection(self, dialog, record):
        def load():
            dialog.destroy()
            transient = self.get_outer_window()
            out = proc.stdout.splitlines()
            msg = out[-1]
            process_shell_return_code(transient, msg, proc.returncode, record)

        proc = call_out(self, "Connect from table", record)
        GLib.idle_add(load)


    def _attempt_connection(self):
        transient_parent = self.get_outer_window()
        addr = self.get_column_at_index(7)
        qport = self.get_column_at_index(8)
        record = "%s:%s" %(addr, str(qport))

        wait_dialog = GenericDialog(transient_parent, "Querying server and aligning mods", "WAIT")
        wait_dialog.show_all()
        thread = threading.Thread(target=self._background_connection, args=(wait_dialog, record))
        thread.start()

    def _on_row_activated(self, treeview, tree_iter, col):
        context = self.get_first_col()
        chosen_row = self.get_column_at_index(0)
        output = context, chosen_row
        if context == "Mod" or context == "Timestamp":
            return
        logger.info("User selected '%s' for the context '%s'" %(chosen_row, context))

        outer = self.get_outer_window()
        right_panel = outer.grid.right_panel
        filters_vbox = right_panel.filters_vbox

        valid_contexts = ["Server browser", "My saved servers", "Recent servers", "Scan LAN servers"]
        if chosen_row in valid_contexts:
            # server contexts share the same model type
            for check in checks:
                toggle_signal(filters_vbox, check, '_on_check_toggle', False)

            if chosen_row == "Server browser":
                reinit_checks()
                cooldown = call_out(self, "test_cooldown", "", "")
                if cooldown.returncode == 1:
                    spawn_dialog(self.get_outer_window(), cooldown.stdout, "NOTIFY")
                    return 1
            else:
                for check in checks:
                    if check.get_label() not in toggled_checks:
                        toggled_checks.append(check.get_label())
                        check.set_active(True)
            self._update_multi_column(chosen_row)

            map_store.clear()
            map_store.append(["All maps"])
            right_panel.set_active_combo()

            toggle_signal(filters_vbox, filters_vbox.maps_combo, '_on_map_changed', True)
            toggle_signal(self, self.selected_row, '_on_tree_selection_changed', True)
            self.grab_focus()
        elif chosen_row == "List installed mods" or chosen_row == "Show debug log":
            toggle_signal(self, self.selected_row, '_on_tree_selection_changed', False)
            self._update_quad_column(chosen_row)
            toggle_signal(self, self.selected_row, '_on_tree_selection_changed', True)
        elif any(map(context.__contains__, valid_contexts)):
            # implies activated row on any server list subcontext
            self._attempt_connection()
        else:
            # implies any other non-server option selected from main menu
            process_tree_option(output, self)


def format_metadata(row_sel):
    prefix = status_tooltip[row_sel]
    vals = {
            "branch": config_vals[0],
            "debug": config_vals[1],
            "auto_install": config_vals[2],
            "name": config_vals[3],
            "fav_label": config_vals[4],
            "preferred_client": config_vals[5]
            }
    match row_sel:
        case "Quick-connect to favorite server" | "Change favorite server":
            default = "unset"
            val = "fav_label"
        case "Change player name":
            val = "name"
        case "Toggle mod install mode":
            default = "manual"
            alt = "auto"
            val = "auto_install"
        case "Toggle debug mode":
            default = "normal"
            alt = "debug"
            val = "debug"
        case "Toggle release branch":
            val = "branch"
        case "Toggle Steam/Flatpak":
            val = "preferred_client"
        case _:
            return prefix

    try:
        cur_val = vals[val]
        if cur_val == "":
            return "%s | Current: %s" %(prefix, default)
        # TODO: migrate to human readable config values
        elif cur_val == "1":
            return "%s | Current: %s" %(prefix, alt)
        else:
            return "%s | Current: '%s'" %(prefix, cur_val)
    except KeyError:
        return prefix


def format_tooltip(sum, hits):
    if hits == 1:
        hit_suffix = "match"
    else:
        hit_suffix = "matches"
    if sum == 1:
        player_suffix = "player"
    else:
        player_suffix = "players"
    tooltip = "Found %s %s with %s %s" %(f'{hits:n}', hit_suffix, f'{sum:n}', player_suffix)
    return tooltip


def filter_servers(transient_parent, filters_vbox, treeview, context):
    def filter(dialog):
        def clear_and_destroy():
            row_metadata = parse_server_rows(data)
            sum = row_metadata[0]
            hits = row_metadata[1]
            server_tooltip[0] = format_tooltip(sum, hits)
            transient_parent.grid.update_statusbar(server_tooltip[0])

            toggle_signal(treeview, treeview.selected_row, '_on_tree_selection_changed', True)
            toggle_signal(filters_vbox, filters_vbox, '_on_button_release', True)
            toggle_signal(filters_vbox, filters_vbox.maps_combo, '_on_map_changed', True)
            dialog.destroy()
            treeview.grab_focus()

        server_filters = toggled_checks + keyword_filter + selected_map
        data = call_out(transient_parent, "filter", context, *server_filters)
        GLib.idle_add(clear_and_destroy)

    # block additional input on FilterPanel while filters are running
    toggle_signal(treeview, treeview.selected_row, '_on_tree_selection_changed', False)
    toggle_signal(filters_vbox, filters_vbox, '_on_button_release', False)
    toggle_signal(filters_vbox, filters_vbox.maps_combo, '_on_map_changed', False)

    dialog = GenericDialog(transient_parent, "Filtering results", "WAIT")
    dialog.show_all()
    server_store.clear()

    thread = threading.Thread(target=filter, args=(dialog,))
    thread.start()


class AppHeaderBar(Gtk.HeaderBar):
    def __init__(self):
        super().__init__()
        self.props.title = app_name
        self.set_decoration_layout("menu:minimize,maximize,close")
        self.set_show_close_button(True)

class Port(Enum):
    # Contains enums for LanButtonDialog ports
    DEFAULT = 1
    CUSTOM = 2

class GenericDialog(Gtk.MessageDialog):
    def __init__(self, parent, text, mode):

        def _on_dialog_delete(self, response_id):
            """Passively ignore user-input"""
            return True

        match mode:
            case "WAIT":
                dialog_type = Gtk.MessageType.INFO
                button_type = Gtk.ButtonsType.NONE
                header_text = "Please wait"
            case "NOTIFY":
                dialog_type = Gtk.MessageType.INFO
                button_type = Gtk.ButtonsType.OK
                header_text = "Notice"
            case "CONFIRM":
                dialog_type = Gtk.MessageType.QUESTION
                button_type = Gtk.ButtonsType.OK_CANCEL
                header_text = "Confirmation"
            case "ENTRY":
                dialog_type = Gtk.MessageType.QUESTION
                button_type = Gtk.ButtonsType.OK_CANCEL
                header_text = "User input required"
            case _:
                dialog_type = Gtk.MessageType.INFO
                button_type = Gtk.ButtonsType.OK
                header_text = mode

        Gtk.MessageDialog.__init__(
            self,
            transient_for=parent,
            flags=0,
            message_type=dialog_type,
            text=header_text,
            secondary_text=textwrap.fill(text, 50),
            buttons=button_type,
            title=app_name,
            modal=True,
        )

        if mode == "WAIT":
            dialogBox = self.get_content_area()
            spinner = Gtk.Spinner()
            dialogBox.pack_end(spinner, False, False, 0)
            spinner.start()
            self.connect("delete-event", _on_dialog_delete)

        self.set_default_response(Gtk.ResponseType.OK)
        self.set_size_request(500, 0)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

    def update_label(self, text):
        self.format_secondary_text(text)


class LanButtonDialog(Gtk.Window):
    def __init__(self, parent):
        super().__init__()

        self.buttonBox = Gtk.Box()

        header_label = "Scan LAN servers"
        buttons = [
           ( "Use default query port (27016)", Port.DEFAULT ),
           ( "Enter custom query port", Port.CUSTOM ),
           ]

        self.buttonBox.set_orientation(Gtk.Orientation.VERTICAL)
        self.buttonBox.active_button = None

        for i in enumerate(buttons):

            string = i[1][0]
            enum = i[1][1]

            button = Gtk.RadioButton(label=string)
            button.port = enum
            button.connect("toggled", self._on_button_toggled)

            if i[0] == 0:
                self.buttonBox.active_button = button
            else:
                button.join_group(self.buttonBox.active_button)

            self.buttonBox.add(button)

        self.entry = Gtk.Entry()
        self.buttonBox.add(self.entry)
        self.entry.set_no_show_all(True)

        self.label = Gtk.Label()
        self.label.set_text("Invalid port")
        self.label.set_no_show_all(True)
        self.buttonBox.add(self.label)

        self.dialog = LanDialog(parent, header_label, self.buttonBox, self.entry, self.label)
        self.dialog.run()
        self.dialog.destroy()

    def get_selected_port(self):
        return self.dialog.p

    def _on_button_toggled(self, button):
        if button.get_active():
            self.buttonBox.active_button = button

            match button.port:
                case Port.DEFAULT:
                    self.entry.set_visible(False)
                case Port.CUSTOM:
                    self.entry.set_visible(True)
                    self.entry.grab_focus()

    def get_active_button():
        return self.buttonBox.active_button

class LanDialog(Gtk.MessageDialog):
    # Custom dialog class that performs integer validation and blocks input if invalid port
    # Returns None if user cancels the dialog
    def __init__(self, parent, text, child, entry, label):
        super().__init__(transient_for=parent,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=text,
            secondary_text="Select the query port",
            title=app_name,
            modal=True,
        )

        self.outer = self.get_content_area()
        self.outer.pack_start(child, False, False, 0)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.set_size_request(500, 0)
        self.outer.set_margin_start(30)
        self.outer.set_margin_end(30)
        self.outer.show_all()

        self.connect("response", self._on_dialog_response, child, entry)
        self.connect("key-press-event", self._on_keypress, entry)
        self.connect("key-release-event", self._on_key_release, entry, label)

        self.child = child

        self.p = None

    def _on_key_release(self, dialog, event, entry, label):
        label.set_visible(False)
        if entry.is_visible() == False or entry.get_text() == "":
            return
        if self._is_invalid(entry.get_text()):
            label.set_visible(True)
        else:
            label.set_visible(False)

    def _on_keypress(self, a, event, entry):
        if event.keyval == Gdk.KEY_Return:
            self.response(Gtk.ResponseType.OK)
        if event.keyval == Gdk.KEY_Up:
            entry.set_text("")
            self.child.get_children()[0].grab_focus()

    def _on_dialog_response(self, dialog, resp, child, entry):
        match resp:
            case Gtk.ResponseType.CANCEL:
                return
            case Gtk.ResponseType.DELETE_EVENT:
                return

        string = entry.get_text()
        port = child.active_button.port

        match port:
            case Port.DEFAULT:
                self.p = "27016"
            case Port.CUSTOM:
                if self._is_invalid(string):
                    self.stop_emission_by_name("response")
                else:
                    self.p = string

    def _is_invalid(self, string):
        if string.isdigit() == False \
            or int(string) == 0 \
            or int(string[0]) == 0 \
            or int(string) > 65535:
                return True
        return False

def ChangelogDialog(parent, text, mode):

    dialog = GenericDialog(parent, text, mode)
    dialogBox = dialog.get_content_area()
    dialog.set_default_response(Gtk.ResponseType.OK)
    dialog.set_size_request(1000, 600)

    with open(changelog_path, 'r') as f:
        changelog = f.read()

    scrollable = Gtk.ScrolledWindow()
    label = Gtk.Label()
    label.set_markup(changelog)
    scrollable.add(label)
    dialogBox.pack_end(scrollable, True, True, 0)
    set_surrounding_margins(dialogBox, 30)

    dialog.show_all()
    return dialog


def KeysDialog(parent, text, mode):

    dialog = GenericDialog(parent, text, mode)
    dialogBox = dialog.get_content_area()
    dialog.set_default_response(Gtk.ResponseType.OK)
    dialog.set_size_request(700, 0)

    keybindings = """
    <b>Basic navigation</b>
    Ctrl-q: quit
    Enter/Space/Double click: select row item
    Up, Down: navigate through row items
    ?: open this dialog

    <b>Button navigation</b>
    Right: jump from main view to side buttons
    Left: jump from side buttons to main view
    Up, Down: navigate up and down through side buttons
    Tab, Shift-Tab: navigate forward/back through menu elements

    <b>Any server browsing context</b>
    Enter/Space/Double click: connect to server
    Right-click on row/Ctrl-l: displays additional context menus
    Ctrl-f: jump to keyword field
    Ctrl-m: jump to maps dropdown
    Ctrl-d: toggle dry run (debug) mode
    Ctrl-r: refresh player count for active row
    1-9: toggle filter ON/OFF
    ESC: jump back to main view from keyword/maps
    """

    label = Gtk.Label()
    label.set_markup(keybindings)
    dialogBox.pack_end(label, False, False, 0)
    dialog.show_all()
    return dialog


class PingDialog(GenericDialog):
    def __init__(self, parent, text, mode, record):
        super().__init__(parent, text, mode)
        dialogBox = self.get_content_area()
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_size_request(500, 200)
        wait_dialog = GenericDialog(parent, "Checking ping", "WAIT")
        wait_dialog.show_all()
        thread = threading.Thread(target=self._background, args=(wait_dialog, parent, record))
        thread.start()

    def _background(self, dialog, parent, record):
        def _load():
            dialog.destroy()
            self.show_all()
            ping = data.stdout
            self.format_secondary_text("Ping to remote server: %s" %(ping))
            res = self.run()
            self.destroy()

        addr = record.split(':')
        ip = addr[0]
        qport = addr[2]
        data = call_out(parent, "test_ping", ip, qport)
        GLib.idle_add(_load)

class ModDialog(GenericDialog):
    def __init__(self, parent, text, mode, record):
        super().__init__(parent, text, mode)

        dialogBox = self.get_content_area()
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_size_request(800, 500)

        self.scrollable = Gtk.ScrolledWindow()
        self.view = Gtk.TreeView()
        self.scrollable.add(self.view)
        set_surrounding_margins(self.scrollable, 20)

        self.view.connect("row-activated", self._on_row_activated)

        for i, column_title in enumerate(
            ["Mod", "ID", "Installed"]
        ):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            self.view.append_column(column)
            column.set_sort_column_id(i)
        dialogBox.pack_end(self.scrollable, True, True, 0)

        wait_dialog = GenericDialog(parent, "Fetching modlist", "WAIT")
        wait_dialog.show_all()
        thread = threading.Thread(target=self._background, args=(wait_dialog, parent, record))
        thread.start()

    def _background(self, dialog, parent, record):
        def _load():
            dialog.destroy()
            if data.returncode == 1:
                spawn_dialog(parent, "Server has no mods installed", "NOTIFY")
                return
            self.show_all()
            self.set_markup("Modlist (%s mods)" %(mod_count))
            res = self.run()
            self.destroy()

        addr = record.split(':')
        ip = addr[0]
        qport = addr[2]
        data = call_out(parent, "show_server_modlist", ip, qport)
        mod_count = parse_modlist_rows(data)
        self.view.set_model(modlist_store)
        GLib.idle_add(_load)

    def popup(self):
        pass

    def _on_row_activated(self, treeview, tree_iter, col):
        select = treeview.get_selection()
        sels = select.get_selected_rows()
        (model, pathlist) = sels
        if len(pathlist) < 1:
            return
        path = pathlist[0]
        tree_iter = model.get_iter(path)
        mod_id = model.get_value(tree_iter, 1)
        subprocess.Popen(['/usr/bin/env', 'bash', funcs, "open_workshop_page", mod_id])

class EntryDialog(GenericDialog):
    def __init__(self, parent, text, mode, link):
        super().__init__(parent, text, mode)

        """ Returns user input as a string or None """
        """ If user does not input text it returns None, NOT AN EMPTY STRING. """

        self.dialog = GenericDialog(parent, text, mode)
        self.dialogBox = self.dialog.get_content_area()
        self.dialog.set_default_response(Gtk.ResponseType.OK)
        self.dialog.set_size_request(500, 0)

        self.userEntry = Gtk.Entry()
        set_surrounding_margins(self.userEntry, 20)
        self.userEntry.set_margin_top(0)
        self.userEntry.set_size_request(250, 0)
        self.userEntry.set_activates_default(True)
        self.dialogBox.pack_start(self.userEntry, False, False, 0)

        if link != "":
            button = Gtk.Button(label=link)
            button.set_margin_start(60)
            button.set_margin_end(60)
            button.connect("clicked", self._on_button_clicked)
            self.dialogBox.pack_end(button, False, False, 0)

    def _on_button_clicked(self, button):
        label = button.get_label()
        subprocess.Popen(['/usr/bin/env', 'bash', funcs, "Open link", label])

    def get_input(self):
        self.dialog.show_all()
        response = self.dialog.run()
        text = self.userEntry.get_text()
        self.dialog.destroy()
        if (response == Gtk.ResponseType.OK) and (text != ''):
            return text
        else:
            return None


class Grid(Gtk.Grid):
    def __init__(self, is_steam_deck):
        super().__init__()
        self.set_column_homogeneous(True)
        #self.set_row_homogeneous(True)

        self._version = "%s %s" %(app_name, sys.argv[2])

        self.scrollable_treelist = ScrollableTree(is_steam_deck)
        if is_steam_deck is True:
            self.scrollable_treelist.set_hexpand(False)
            self.scrollable_treelist.set_vexpand(True)
        else:
            self.scrollable_treelist.set_hexpand(True)
            self.scrollable_treelist.set_vexpand(True)

        self.right_panel = RightPanel(is_steam_deck)


        self.bar = Gtk.Statusbar()
        self.scrollable_treelist.treeview.connect("on_distcalc_started", self._on_calclat_started)

        GLib.timeout_add(200, self._check_result_queue)

        self.update_statusbar(default_tooltip)
        self.status_right_label = Gtk.Label(label="")
        self.bar.add(self.status_right_label)
        self.update_right_statusbar()

        if is_steam_deck is True:
            self.attach(self.scrollable_treelist, 0, 0, 4, 1)
            self.attach_next_to(self.bar, self.scrollable_treelist, Gtk.PositionType.BOTTOM, 4, 1)
            self.attach_next_to(self.right_panel, self.scrollable_treelist, Gtk.PositionType.RIGHT, 1, 1)
        else:
            self.attach(self.scrollable_treelist, 0, 0, 7, 5)
            self.attach_next_to(self.bar, self.scrollable_treelist, Gtk.PositionType.BOTTOM, 7, 1)
            self.attach_next_to(self.right_panel, self.scrollable_treelist, Gtk.PositionType.RIGHT, 1, 1)

    def update_right_statusbar(self):
        config_vals.clear()
        for i in query_config(self):
            config_vals.append(i)
        _branch = config_vals[0]
        _branch = _branch.upper()
        _debug = config_vals[1]
        if _debug == "":
            _debug = "NORMAL"
        else:
            _debug = "DEBUG"
        concat_label = "%s | %s | %s" %(_branch, _debug, self._version)
        self.status_right_label.set_text(concat_label)

    def terminate_treeview_process(self):
        self.scrollable_treelist.treeview.terminate_process()

    def _on_calclat_started(self, treeview):
        server_tooltip[1] = server_tooltip[0] + "| Distance: calculating..."
        self.update_statusbar(server_tooltip[1])

    def _check_result_queue(self):
        latest_result = None
        result_queue = self.scrollable_treelist.treeview.queue
        while not result_queue.empty():
            latest_result = result_queue.get()

        if latest_result is not None:
            addr = latest_result[0]
            km = latest_result[1]
            ping = latest_result[2]

            cache[addr] = km, ping

            ping = format_ping(ping)
            dist = format_distance(km)
            tooltip = server_tooltip[1] = server_tooltip[0] + dist + ping
            self.update_statusbar(tooltip)

        return True

    def update_statusbar(self, string):
        meta = self.bar.get_context_id("Statusbar")
        self.bar.push(meta, string)


def toggle_signal(owner, widget, func_name, bool):
    func = getattr(owner, func_name)
    if (bool):
        logger.debug("Unblocking %s for %s" %(func_name, widget))
        widget.handler_unblock_by_func(func)
    else:
        logger.debug("Blocking %s for %s" %(func_name, widget))
        widget.handler_block_by_func(func)


class App(Gtk.Application):
    def __init__(self):

        _isd = int(sys.argv[3])
        if _isd == 1:
            is_steam_deck = True
            is_game_mode = False
        elif _isd == 2:
            is_steam_deck = True
            is_game_mode = True
        else:
            is_steam_deck = False
            is_game_mode = False

        self.win = OuterWindow(is_steam_deck, is_game_mode)
        self.win.set_icon_name("dzgui")

        accel = Gtk.AccelGroup()
        accel.connect(Gdk.KEY_q, Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE, self._halt_window_subprocess)
        self.win.add_accel_group(accel)

        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, Gtk.main_quit)
        Gtk.main()

    def _halt_window_subprocess(self, accel_group, window, code, flag):
        self.win.halt_proc_and_quit(self, None)


class FilterPanel(Gtk.Box):
    def __init__(self):
        super().__init__(spacing=6)

        for check in filters.keys():
            checkbutton = Gtk.CheckButton(label=check)
            label = checkbutton.get_children()

            label[0].set_ellipsize(Pango.EllipsizeMode.END)
            if filters[check] is True:
                checkbutton.set_active(True)
                toggled_checks.append(check)
            checkbutton.connect("toggled", self._on_check_toggle)
            checks.append(checkbutton)

        self.connect("button-release-event", self._on_button_release)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        set_surrounding_margins(self, 10)
        self.set_margin_top(1)

        self.filters_label = Gtk.Label(label="Filters")

        self.keyword_entry = Gtk.Entry()
        self.keyword_entry.set_placeholder_text("Filter by keyword")
        self.keyword_entry.connect("activate", self._on_keyword_enter)
        self.keyword_entry.connect("key-press-event", self._on_esc_pressed)

        renderer_text = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END)
        self.maps_combo = Gtk.ComboBox.new_with_model(map_store)
        self.maps_combo.pack_start(renderer_text, True)
        self.maps_combo.add_attribute(renderer_text, "text", 0)
        self.maps_combo.connect("changed", self._on_map_changed)
        self.maps_combo.connect("key-press-event", self._on_esc_pressed)


        self.pack_start(self.filters_label, False, False, True)
        self.pack_start(self.keyword_entry, False, False, True)
        self.pack_start(self.maps_combo, False, False, True)

        for i, check in enumerate(checks[0:]):
            self.pack_start(checks[i], False, False, True)


    def grab_keyword_focus(self):
        self.keyword_entry.grab_focus()

    def restore_focus_to_treeview(self):
        grid = self.get_outer_grid()
        grid.scrollable_treelist.treeview.grab_focus()
        return False

    def _on_esc_pressed(self, entry, event):
        keyname = Gdk.keyval_name(event.keyval)
        if keyname == "Escape":
            GLib.idle_add(self.restore_focus_to_treeview)

    def get_outer_grid(self):
        panel = self.get_parent()
        grid = panel.get_parent()
        return grid

    def get_outer_window(self):
        grid = self.get_outer_grid()
        outer_window = grid.get_parent()
        return outer_window

    def _on_keyword_enter(self, keyword_entry):
        win = self.get_outer_window()
        win.set_keep_below(False)
        keyword = keyword_entry.get_text()
        old_keyword = keyword_filter[0].split(delimiter)[1]
        if keyword == old_keyword:
            return
        logger.info("User filtered by keyword '%s'" %(keyword))
        keyword_filter.clear()
        keyword_filter.append("Keyword␞" + keyword)
        transient_parent = self.get_outer_window()
        grid = self.get_outer_grid()
        treeview = grid.scrollable_treelist.treeview
        context = grid.scrollable_treelist.treeview.get_first_col()
        filter_servers(transient_parent, self, treeview, context)

    def _on_button_release(self, window, button):
        return True

    def set_active_combo(self):
        self.maps_combo.set_active(0)

    def toggle_check(self, button):
        if button.get_active():
            button.set_active(False)
        else:
            button.set_active(True)

    def _on_check_toggle(self, button):
        grid = self.get_outer_grid()
        treeview = grid.scrollable_treelist.treeview
        context = grid.scrollable_treelist.treeview.get_first_col()
        label = button.get_label()
        state = button.get_active()

        if context == "Mod":
            return
        if state is True:
            toggled_checks.append(label)
        else:
            toggled_checks.remove(label)

        logger.info("User toggled button '%s' to %s" %(label, state))
        transient_parent = self.get_outer_window()
        filter_servers(transient_parent, self, treeview, context)

    def _on_map_changed(self, combo):
        grid = self.get_outer_grid()
        transient_parent = self.get_outer_window()
        treeview = grid.scrollable_treelist.treeview
        context = grid.scrollable_treelist.treeview.get_first_col()

        tree_iter = combo.get_active_iter()
        if tree_iter is not None:
            selected_map.clear()
            model = combo.get_model()
            selection = model[tree_iter][0]
            selected_map.append("Map=" + selection)
            logger.info("User selected map '%s'" %(selection))
            filter_servers(transient_parent, self, treeview, context)


def main():

    def usage():
        text = "UI constructor must be run via DZGUI"
        logger.critical(text)
        print(text)
        sys.exit(1)

    expected_flag = "--init-ui"
    if len(sys.argv) < 2:
        usage()
    if sys.argv[1] != expected_flag:
        usage()

    logger.info("Spawned UI from DZGUI setup process")
    App()


if __name__ == '__main__':
    main()
