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

locale.setlocale(locale.LC_ALL, '')
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango
from enum import Enum

# 5.6.0
app_name = "DZGUI"

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
#cf. mod_cols, last column holds hex color
mod_store = Gtk.ListStore(str, str, str, float, str)
#cf. log_cols
log_store = Gtk.ListStore(str, str, str, str)
#cf. browser_cols
server_store = Gtk.ListStore(str, str, str, str, int, int, int, str, int)

default_tooltip = "Select a row to see its detailed description"
server_tooltip = [None, None]

user_path = os.path.expanduser('~')
cache_path = '%s/.cache/dzgui' %(user_path)
state_path = '%s/.local/state/dzgui' %(user_path)
helpers_path = '%s/.local/share/dzgui/helpers' %(user_path)
log_path = '%s/logs' %(state_path)
changelog_path = '%s/CHANGELOG.md' %(state_path)
geometry_path = '%s/dzg.cols.json' %(state_path)
funcs = '%s/funcs' %(helpers_path)
mods_temp_file = '%s/dzg.mods_temp' %(cache_path)
stale_mods_temp_file = '%s/dzg.stale_mods_temp' %(cache_path)

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
    "Size (MiB)",
    "Color"
]
log_cols = [
    "Timestamp",
    "Flag",
    "Traceback",
    "Message"
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


class EnumWithAttrs(Enum):

    def __new__(cls, *args, **kwds):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj
    def __init__(self, a):
        self.dict = a


class RowType(EnumWithAttrs):
    @classmethod
    def str2rowtype(cls, str):
        for member in cls:
            if str == member.dict["label"]:
                return member
        return RowType.DYNAMIC

    DYNAMIC = {
            "label": None,
            "tooltip": None,
            }
    RESOLVE_IP = {
            "label": "Resolve IP",
            "tooltip": None,
            "wait_msg": "Resolving remote IP"
            }
    HIGHLIGHT = {
            "label": "Highlight stale",
            "tooltip": None,
            "wait_msg": "Looking for stale mods"
            }
    HANDSHAKE = {
            "label": "Handshake",
            "tooltip": None,
            "wait_msg": "Waiting for DayZ"
            }
    DELETE_SELECTED = {
            "label": "Delete selected mods",
            "tooltip": None,
            "wait_msg": "Deleting mods"
            }
    SERVER_BROWSER = {
            "label": "Server browser",
            "tooltip": "Used to browse the global server list",
            }
    SAVED_SERVERS = {
            "label": "My saved servers",
            "tooltip": "Browse your saved servers. Unreachable/offline servers will be excluded",
            }
    QUICK_CONNECT = {
            "label": "Quick-connect to favorite server",
            "tooltip": "Connect to your favorite server",
            "wait_msg": "Working",
            "default": "unset",
            "alt": None,
            "val": "fav_label"
            }
    RECENT_SERVERS = {
            "label": "Recent servers",
            "tooltip": "Shows the last 10 servers you connected to (includes attempts)",
            }
    CONN_BY_IP = {
            "label": "Connect by IP",
            "tooltip": "Connect to a server by IP",
            "prompt": "Enter IP in IP:Queryport format (e.g. 192.168.1.1:27016)",
            "link_label": None,
            }
    CONN_BY_ID = {
            "label": "Connect by ID",
            "tooltip": "Connect to a server by Battlemetrics ID",
            "prompt": "Enter server ID",
            "link_label": "Open Battlemetrics",
            }
    SCAN_LAN = {
            "label": "Scan LAN servers",
            "tooltip": "Search for servers on your local network"
            }
    ADD_BY_IP = {
            "label": "Add server by IP",
            "tooltip": "Add a server by IP",
            "prompt": "Enter IP in IP:Queryport format (e.g. 192.168.1.1:27016)",
            "link_label": None,
    }
    ADD_BY_ID = {
            "label": "Add server by ID",
            "tooltip": "Add a server by Battlemetrics ID",
            "prompt": "Enter server ID",
            "link_label": "Open Battlemetrics",
    }
    CHNG_FAV = {
            "label": "Change favorite server",
            "tooltip": "Update your quick-connect server",
            "prompt": "Enter IP in IP:Queryport format (e.g. 192.168.1.1:27016)",
            "link_label": None,
            "alt": None,
            "default": "unset",
            "val": "fav_label"
    }
    LIST_MODS = {
            "label": "List installed mods",
            "tooltip": "Browse a list of locally-installed mods",
            "quad_label": "Mods"
    }
    TGL_BRANCH = {
            "label": "Toggle release branch",
            "tooltip": "Switch between stable and testing branches",
            "default": None,
            "val": "branch"
    }
    TGL_INSTALL = {
            "label": "Toggle mod install mode",
            "tooltip": "Switch between manual and auto mod installation",
            "default": "manual",
            "alt": "auto",
            "val": "auto_install"
            }
    TGL_STEAM = {
            "label": "Toggle Steam/Flatpak",
            "tooltip": "Switch the preferred client to use for launching DayZ",
            "alt": None,
            "default": None,
            "val": "preferred_client"
    }
    TGL_FULLSCREEN = {
            "label": "Toggle DZGUI fullscreen boot",
            "tooltip": "Whether to start DZGUI as a maximized window (desktop only)",
            "alt": "true",
            "default": "false",
            "val": "fullscreen"
    }
    CHNG_PLAYER = {
            "label": "Change player name",
            "tooltip": "Update your in-game name (required by some servers)",
            "prompt": "Enter new nickname",
            "link_label": None,
            "alt": None,
            "default": None,
            "val": "name"
    }
    CHNG_STEAM_API = {
            "label": "Change Steam API key",
            "tooltip": "Can be used if you revoked an old API key",
            "prompt": "Enter new API key",
            "link_label": "Open Steam API page",
    }
    CHNG_BM_API = {
            "label": "Change Battlemetrics API key",
            "tooltip": "Can be used if you revoked an old API key",
            "link_label": "Open Battlemetrics API page",
            "prompt": "Enter new API key",
    }
    FORCE_UPDATE = {
            "label": "Force update local mods",
            "tooltip": "Synchronize the signatures of all local mods with remote versions (experimental)",
            "wait_msg": "Updating mods"
            }
    DUMP_LOG = {
            "label": "Output system info to log file",
            "tooltip": "Dump diagnostic data for troubleshooting",
            "wait_msg": "Generating log"
            }
    CHANGELOG = {
            "label": "View changelog",
            "tooltip": "Opens the DZGUI changelog in a dialog window"
            }
    SHOW_LOG = {
            "label": "Show debug log",
            "tooltip": "Read the DZGUI log generated since startup",
            "quad_label": "Debug log"
            }
    DOCS = {
            "label": "Help file ⧉",
            "tooltip": "Opens the DZGUI documentation in a browser"
            }
    BUGS = {
            "label": "Report a bug ⧉",
            "tooltip": "Opens the DZGUI issue tracker in a browser"
            }
    FORUM = {
            "label": "Forum ⧉",
            "tooltip": "Opens the DZGUI discussion forum in a browser"
            }
    SPONSOR = {
            "label": "Sponsor ⧉",
            "tooltip": "Sponsor the developer of DZGUI"
            }
    HOF = {
            "label": "Hall of fame ⧉",
            "tooltip": "A list of significant contributors and testers"
            }


class WindowContext(EnumWithAttrs):
    @classmethod
    def row2con(cls, row):
        m = None
        for member in cls:
            if row in member.dict["rows"]:
                    m = member
            elif row in member.dict["called_by"]:
                    m = member
            else:
                continue
        return m


    MAIN_MENU = {
            "label": "",
            "rows": [
                RowType.SERVER_BROWSER,
                RowType.SAVED_SERVERS,
                RowType.QUICK_CONNECT,
                RowType.RECENT_SERVERS,
                RowType.CONN_BY_IP,
                RowType.CONN_BY_ID,
                RowType.SCAN_LAN
                ],
            "called_by": []
            }
    MANAGE = {
            "label": "Manage",
            "rows": [
                RowType.ADD_BY_IP,
                RowType.ADD_BY_ID,
                RowType.CHNG_FAV
                ],
            "called_by": []
            }
    OPTIONS = {
            "label": "Options",
            "rows":[
                RowType.LIST_MODS,
                RowType.TGL_BRANCH,
                RowType.TGL_INSTALL,
                RowType.TGL_STEAM,
                RowType.TGL_FULLSCREEN,
                RowType.CHNG_PLAYER,
                RowType.CHNG_STEAM_API,
                RowType.CHNG_BM_API,
                RowType.FORCE_UPDATE,
                RowType.DUMP_LOG
                ],
            "called_by": []
            }
    HELP = {
            "label": "Help",
            "rows":[
                RowType.CHANGELOG,
                RowType.SHOW_LOG,
                RowType.DOCS,
                RowType.BUGS,
                RowType.FORUM,
                RowType.SPONSOR,
                RowType.HOF
                ],
            "called_by": []
            }
    # inner server contexts
    TABLE_API = {
            "label": "",
            "rows": [],
            "called_by": [
                RowType.SERVER_BROWSER
                ],
            }
    TABLE_SERVER = {
            "label": "",
            "rows": [],
            "called_by": [
                RowType.SAVED_SERVERS,
                RowType.RECENT_SERVERS,
                RowType.SCAN_LAN
                ],
            }
    TABLE_MODS = {
            "label": "",
            "rows": [],
            "called_by": [
                RowType.LIST_MODS,
                ],
            }
    TABLE_LOG = {
            "label": "",
            "rows": [],
            "called_by": [
                RowType.SHOW_LOG
                ],
            }


class WidgetType(Enum):
    OUTER_WIN = 1
    TREEVIEW = 2
    GRID = 3
    RIGHT_PANEL = 4
    MOD_PANEL = 5
    FILTER_PANEL = 6


class Port(Enum):
    DEFAULT = 1
    CUSTOM = 2


class Popup(Enum):
    WAIT = 1
    NOTIFY = 2
    CONFIRM = 3
    ENTRY = 4


class ButtonType(EnumWithAttrs):
    MAIN_MENU = {"label": "Main menu",
                 "opens": WindowContext.MAIN_MENU
                 }
    MANAGE = {"label": "Manage",
              "opens": WindowContext.MANAGE
              }
    OPTIONS = {"label": "Options",
               "opens": WindowContext.OPTIONS
               }
    HELP = {"label": "Help",
            "opens": WindowContext.HELP
            }
    EXIT = {"label": "Exit",
            "opens": None
            }


class EnumeratedButton(Gtk.Button):
    @GObject.Property
    def button_type(self):
       return self._button_type

    @button_type.setter
    def button_type(self, value):
       self._button_type = value


def relative_widget(child):
    # returns collection of outer widgets relative to source widget
    # chiefly used for transient modals and accessing non-adjacent widget methods
    # positions are always relative to grid sub-children
    # containers and nested buttons should never need to call this function directly

    grid = child.get_parent().get_parent()
    treeview = grid.scrollable_treelist.treeview
    outer = grid.get_parent()

    widgets = {
            'grid': grid,
            'treeview': treeview,
            'outer': outer
            }

    supported = [
            "ModSelectionPanel", # Grid < RightPanel < ModSelectionPanel
            "ButtonBox", # Grid < RightPanel < ButtonBox
            "TreeView" # Grid < ScrollableTree < TreeView
            ]

    if child.__class__.__name__ not in supported:
        raise Exception("Unsupported child widget")

    return widgets


def pluralize(plural, count):
    suffix = plural[-2:]
    if suffix == "es":
        base = plural[:-2]
        return f"%s{'es'[:2*count^2]}" %(base)
    else:
        base = plural[:-1]
        return f"%s{'s'[:count^1]}" %(base)


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
    # Nonetype inherits default GTK color
    try:
        rows = [[row[0], row[1], row[2], locale.atof(row[3], func=float), None] for row in reader if row]
    except IndexError:
        return 1
    for row in rows:
        mod_store.append(row)
        size = float(row[3])
        sum += size
    return [sum, hits]


def parse_server_rows(data):
    lines = data.stdout.splitlines()
    reader = csv.reader(lines, delimiter=delimiter)
    try:
        rows = [[row[0], row[1], row[2], row[3], int(row[4]), int(row[5]), int(row[6]), row[7], int(row[8])] for row in reader if row]
    except IndexError:
        return 1
    for row in rows:
        server_store.append(row)


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
    logger.info("Processing return code '%s' for the input '%s', returned message '%s'" %(code, original_input, msg))
    match code:
        case 0:
            # success with notice popup
            spawn_dialog(transient_parent, msg, Popup.NOTIFY)
        case 1:
            # error with notice popup
            if msg == "":
                msg = "Something went wrong"
            spawn_dialog(transient_parent, msg, Popup.NOTIFY)
        case 2:
            # warn and recurse (e.g. validation failed)
            spawn_dialog(transient_parent, msg, Popup.NOTIFY)
            treeview = transient_parent.grid.scrollable_treelist.treeview
            process_tree_option(original_input, treeview)
        case 4:
            # for BM only
            spawn_dialog(transient_parent, msg, Popup.NOTIFY)
            treeview = transient_parent.grid.scrollable_treelist.treeview
            process_tree_option([treeview.view, RowType.CHNG_BM_API], treeview)
        case 5:
            # for steam only
            # deprecated, Steam is mandatory now
            spawn_dialog(transient_parent, msg, Popup.NOTIFY)
            treeview = transient_parent.grid.scrollable_treelist.treeview
            process_tree_option([treeview.view, RowType.CHNG_STEAM_API], treeview)
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
            spawn_dialog(transient_parent, msg, Popup.NOTIFY)
            return
        case 95:
            # successful mod deletion
            spawn_dialog(transient_parent, msg, Popup.NOTIFY)
            treeview = transient_parent.grid.scrollable_treelist.treeview
            grid = treeview.get_parent().get_parent()
            (model, pathlist) = treeview.get_selection().get_selected_rows()
            for p in reversed(pathlist):
                it = model.get_iter(p)
                model.remove(it)
            total_size = 0
            total_mods = len(model)
            for row in model:
                total_size += row[3]
            size = locale.format_string('%.3f', total_size, grouping=True)
            pretty = pluralize("mods", total_mods)
            grid.update_statusbar(f"Found {total_mods:n} {pretty} taking up {size} MiB")
            # untoggle selection for visibility of other stale rows
            treeview.toggle_selection(False)
        case 96:
            # unsuccessful mod deletion
            spawn_dialog(transient_parent, msg, Popup.NOTIFY)
            # re-block this signal before redrawing table contents
            treeview = transient_parent.grid.scrollable_treelist.treeview
            toggle_signal(treeview, treeview, '_on_keypress', False)
            treeview.update_quad_column(RowType.LIST_MODS)
        case 99:
            # highlight stale mods
            panel = transient_parent.grid.sel_panel
            panel.colorize_cells(True)
            panel.toggle_select_stale_button(True)
        case 100:
            # final handoff before launch
            final_conf = spawn_dialog(transient_parent, msg, Popup.CONFIRM)
            treeview = transient_parent.grid.scrollable_treelist.treeview
            if final_conf == 1 or final_conf is None:
                return
            process_tree_option([treeview.view, RowType.HANDSHAKE], treeview)
        case 255:
            spawn_dialog(transient_parent, "Update complete. Please close DZGUI and restart.", Popup.NOTIFY)
            Gtk.main_quit()


def process_tree_option(input, treeview):
    context = input[0]
    command = input[1]
    cmd_string = command.dict["label"]
    logger.info("Parsing tree option '%s' for the context '%s'" %(command, context))

    widgets = relative_widget(treeview)
    transient_parent = widgets["outer"]
    grid = widgets["grid"]

    def call_on_thread(bool, subproc, msg, args):
        def _background(subproc, args, dialog):
            def _load():
                wait_dialog.destroy()
                out = proc.stdout.splitlines()
                try:
                    msg = out[-1]
                except:
                    msg = ''
                rc = proc.returncode
                logger.info("Subprocess returned code %s with message '%s'" %(rc, msg))
                process_shell_return_code(transient_parent, msg, rc, input)
            proc = call_out(transient_parent, subproc, args)
            GLib.idle_add(_load)
        if bool is True:
            wait_dialog = GenericDialog(transient_parent, msg, Popup.WAIT)
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

    if command == RowType.RESOLVE_IP:
        record = "%s:%s" %(treeview.get_column_at_index(7), treeview.get_column_at_index(8))
        wait_msg = command.dict["wait_msg"]
        call_on_thread(True, cmd_string, wait_msg, record)
        return
    # help pages
    if context == WindowContext.TABLE_MODS and command == RowType.HIGHLIGHT:
        wait_msg = command.dict["wait_msg"]
        call_on_thread(True, cmd_string, wait_msg, '')
        return
    if context == WindowContext.HELP:
        match command:
            case RowType.CHANGELOG:
                diag = ChangelogDialog(transient_parent)
                diag.run()
                diag.destroy()
            case _:
                base_cmd = "Open link"
                arg_string = cmd_string
                subprocess.Popen(['/usr/bin/env', 'bash', funcs, base_cmd, arg_string])
                pass
        return

    # config metadata toggles
    toggle_commands = [
            RowType.TGL_INSTALL,
            RowType.TGL_BRANCH,
            RowType.TGL_STEAM,
            RowType.TGL_FULLSCREEN
            ]

    if command in toggle_commands:
        match command:
            case RowType.TGL_BRANCH:
                wait_msg = "Updating DZGUI branch"
                call_on_thread(False, "toggle", wait_msg, cmd_string)
            case _:
                proc = call_out(transient_parent, "toggle", cmd_string)
                grid.update_right_statusbar()
                tooltip = format_metadata(command.dict["label"])
                transient_parent.grid.update_statusbar(tooltip)
        return

    # entry dialogs
    interactive_commands = [
            RowType.CONN_BY_IP,
            RowType.CONN_BY_ID,
            RowType.ADD_BY_IP,
            RowType.ADD_BY_ID,
            RowType.CHNG_FAV,
            RowType.CHNG_PLAYER,
            RowType.CHNG_STEAM_API,
            RowType.CHNG_BM_API
            ]

    if command in interactive_commands:
        prompt = command.dict["prompt"]
        flag = True
        link_label = command.dict["link_label"]
        wait_msg = "Working"

        user_entry = EntryDialog(transient_parent, prompt, Popup.ENTRY, link_label)
        res = user_entry.get_input()

        if res is None:
            logger.info("User aborted entry dialog")
            return
        logger.info("User entered: '%s'" %(res))

        if command == RowType.CHNG_PLAYER: flag = False
        call_on_thread(flag, cmd_string, wait_msg, res)
        return

    # standalone commands
    misc_commands = [
            RowType.DELETE_SELECTED,
            RowType.HANDSHAKE,
            RowType.DUMP_LOG,
            RowType.FORCE_UPDATE,
            RowType.QUICK_CONNECT
            ]
    if command in misc_commands:
        wait_msg = command.dict["wait_msg"]
        call_on_thread(True, cmd_string, wait_msg, '')
    return

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
    @GObject.Property
    def widget_type(self):
       return self._widget_type

    @widget_type.setter
    def widget_type(self, value):
       self._widget_type = value

    def __init__(self, is_steam_deck, is_game_mode):
        super().__init__(title=app_name)

        self.hb = AppHeaderBar()
        # steam deck taskbar may occlude elements
        if is_steam_deck is False:
            self.set_titlebar(self.hb)

        self.set_property("widget_type", WidgetType.OUTER_WIN)

        self.connect("delete-event", self.halt_proc_and_quit)
        self.set_border_width(10)

        #app > win > grid > scrollable > treeview [row/server/mod store]
        #app > win > grid > vbox > buttonbox > filterpanel > combo [map store]

        self.grid = Grid(is_steam_deck)
        self.add(self.grid)
        if is_game_mode is True:
            self.fullscreen()
        else:
            if query_config(None, "fullscreen")[0] == "true":
                self.maximize()

        # Hide FilterPanel on main menu
        self.show_all()
        self.grid.right_panel.set_filter_visibility(False)
        self.grid.sel_panel.set_visible(False)
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
        self.is_steam_deck = is_steam_deck

        for side_button in ButtonType:
            button = EnumeratedButton(label=side_button.dict["label"])
            button.set_property("button_type", side_button)
            if is_steam_deck is True:
                button.set_size_request(10, 10)
            else:
                button.set_size_request(50,50)
            #TODO: explore a more intuitive way of highlighting the active context
            button.set_opacity(0.6)
            self.buttons.append(button)
            button.connect("clicked", self._on_selection_button_clicked)
            self.pack_start(button, False, False, True)

        self.buttons[0].set_opacity(1.0)

    def _update_single_column(self, context):
        logger.info("Returning from multi-column view to monocolumn view for the context '%s'" %(context))
        widgets = relative_widget(self)

        # only applicable when returning from mod list
        grid = widgets["grid"]
        grid_last_child = grid.right_panel.get_children()[-1]
        if isinstance(grid_last_child, ModSelectionPanel):
            grid.sel_panel.set_visible(False)
        right_panel = self.get_parent()
        right_panel.set_filter_visibility(False)

        treeview = widgets["treeview"]
        treeview.set_selection_mode(Gtk.SelectionMode.SINGLE)

        # Block maps combo when returning to main menu
        toggle_signal(right_panel.filters_vbox, right_panel.filters_vbox.maps_combo, '_on_map_changed', False)
        right_panel.filters_vbox.keyword_entry.set_text("")
        keyword_filter.clear()
        keyword_filter.append("Keyword␞")
        server_store.clear()

        for column in treeview.get_columns():
            treeview.remove_column(column)
        # used as a convenience for Steam Deck if it has no titlebar
        for i, column_title in enumerate([context.dict["label"]]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            treeview.append_column(column)

        if self.is_steam_deck is False:
            treeview.set_headers_visible(False)

        self._populate(context.dict["opens"])
        toggle_signal(treeview, treeview, '_on_keypress', False)
        treeview.set_model(row_store)
        treeview.grab_focus()

    def _populate(self, context):
        widgets = relative_widget(self)
        treeview = widgets["treeview"]
        grid = widgets["grid"]
        window = widgets["outer"]

        # set global window context
        treeview.view = context

        row_store.clear()
        array = context.dict["rows"]

        window.hb.set_subtitle(context.dict["label"])

        for item in array:
            label = item.dict["label"]
            tooltip = item.dict["tooltip"]
            t = (label, )
            row_store.append(t)
        grid.update_statusbar(tooltip)
        treeview.grab_focus()

    def _on_selection_button_clicked(self, button):
        treeview = self.get_treeview()
        toggle_signal(treeview, treeview.selected_row, '_on_tree_selection_changed', False)
        context = button.get_property("button_type")
        logger.info("User clicked '%s'" %(context))

        if context == ButtonType.EXIT:
            logger.info("Normal user exit")
            Gtk.main_quit()
            return
        cols = treeview.get_columns()

        if len(cols) > 1:
            self._update_single_column(context)

        # Highlight the active widget
        for inactive_button in self.buttons:
            inactive_button.set_opacity(0.6)
        button.set_opacity(1.0)

        for col in cols:
            col.set_title(context.dict["label"])

        # get destination WindowContext enum from button
        self._populate(context.dict["opens"])

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
    @GObject.Property
    def widget_type(self):
       return self._widget_type

    @widget_type.setter
    def widget_type(self, value):
       self._widget_type = value

    def __init__(self, is_steam_deck):
        super().__init__()

        self.set_property("widget_type", WidgetType.TREEVIEW)
        self.view = WindowContext.MAIN_MENU

        self.queue = multiprocessing.Queue()
        self.current_proc = None

        # Disables typeahead search
        self.set_enable_search(False)
        self.set_search_column(-1)

        # Populate model with initial context
        for row in WindowContext.MAIN_MENU.dict["rows"]:
            label = row.dict["label"]
            t = (label,)
            row_store.append(t)
        self.set_model(row_store)

        for i, column_title in enumerate(
            ["Main menu"]
        ):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            self.append_column(column)

        if is_steam_deck is False:
            self.set_headers_visible(False)
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
        #TODO: context menus use old stringwise parsing
        # use enumerated contexts
        parent = self.get_outer_window()
        context = self.get_first_col()
        value = self.get_column_at_index(0)
        context_menu_label = menu_item.get_label()
        logger.info("User clicked context menu '%s'" %(context_menu_label))

        match context_menu_label:
            case "Add to my servers" | "Remove from my servers":
                record = "%s:%s" %(self.get_column_at_index(7), self.get_column_at_index(8))
                process_tree_option([self.view, RowType.RESOLVE_IP], self)
                if context == "Name (My saved servers)":
                    iter = self.get_current_iter()
                    server_store.remove(iter)
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
                res = spawn_dialog(parent, conf_msg, Popup.CONFIRM)
                if res != 0:
                    return
                mods = []
                symlink = self.get_column_at_index(1)
                dir = self.get_column_at_index(2)
                concat = symlink + " " + dir + "\n"
                mods.append(concat)
                with open(mods_temp_file, "w") as outfile:
                    outfile.writelines(mods)
                process_tree_option([self.view, RowType.DELETE_SELECTED], self)
            case "Open in Steam Workshop":
                record = self.get_column_at_index(2)
                base_cmd = "open_workshop_page"
                subprocess.Popen(['/usr/bin/env', 'bash', funcs, base_cmd, record])

    def toggle_selection(self, bool):
        l = len(mod_store)
        match bool:
            case True:
                for i in range (0, l):
                    path = Gtk.TreePath(i)
                    self.get_selection().select_path(path)
            case False:
                for i in range (0, l):
                    path = Gtk.TreePath(i)
                    self.get_selection().unselect_path(path)

    def _on_button_release(self, widget, event):
        if event.type is Gdk.EventType.BUTTON_RELEASE and event.button != 3:
            return
        try:
            pathinfo = self.get_path_at_pos(event.x, event.y)
            if pathinfo is None:
                return
            (path, col, cellx, celly) = pathinfo
            self.set_cursor(path,col,0)
        except AttributeError:
            pass

        context = self.get_first_col()
        self.menu = Gtk.Menu()

        mod_context_items = ["Open in Steam Workshop", "Delete mod"]
        subcontext_items = {
                "Server browser":
                            ["Add to my servers", "Copy IP to clipboard", "Show server-side mods", "Refresh player count"],
                  "My saved servers":
                            ["Remove from my servers", "Copy IP to clipboard", "Show server-side mods", "Refresh player count"],
                  "Recent servers":
                            ["Add to my servers", "Remove from history", "Copy IP to clipboard", "Show server-side mods", "Refresh player count"],
                  }
        # submenu hierarchy https://stackoverflow.com/questions/52847909/how-to-add-a-sub-menu-to-a-gtk-menu

        if self.view == WindowContext.TABLE_LOG:
            return
        if self.view == WindowContext.TABLE_MODS:
            items = mod_context_items
            subcontext = "List installed mods"
        elif "Name" in context:
            subcontext = context.split('(')[1].split(')')[0]
            items = subcontext_items[subcontext]
        else:
            return

        for item in items:
            if subcontext == "Server browser" or "Recent servers":
                if item == "Add to my servers":
                    record = "%s:%s" %(self.get_column_at_index(7), self.get_column_at_index(8))
                    proc = call_out(widget, "is_in_favs", record)
                    if proc.returncode == 0:
                        item = "Remove from my servers"
            item = Gtk.MenuItem(label=item)
            item.connect("activate", self._on_menu_click)
            self.menu.append(item)

        self.menu.show_all()

        if event.type is Gdk.EventType.KEY_PRESS and event.keyval is Gdk.KEY_l:
            sel = self.get_selection()
            sels = sel.get_selected_rows()
            (model, pathlist) = sels
            if len(pathlist) < 1:
                return
            self.menu.popup_at_widget(widget, Gdk.Gravity.CENTER, Gdk.Gravity.WEST)
        else:
            self.menu.popup_at_pointer(event)

    def refresh_player_count(self):
        parent = self.get_outer_window()

        cooldown = call_out(self, "test_cooldown", "", "")
        if cooldown.returncode == 1:
            spawn_dialog(self.get_outer_window(), cooldown.stdout, Popup.NOTIFY)
            return 1
        call_out(self, "start_cooldown", "", "")

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
        # no statusbar queue on quad tables

        grid = self.get_outer_grid()
        context = self.get_first_col()
        row_sel = self.get_column_at_index(0)
        logger.info("Tree selection for context '%s' changed to '%s'" %(context, row_sel))
        if self.view == WindowContext.TABLE_MODS or context == "Timestamp":
            return

        if self.current_proc and self.current_proc.is_alive():
            self.current_proc.terminate()

        if self.view == WindowContext.TABLE_API or self.view == WindowContext.TABLE_SERVER:
            addr = self.get_column_at_index(7)
            if addr is None:
                server_tooltip[0] = format_tooltip()
                grid.update_statusbar(server_tooltip[0])
                return
            if addr in cache:
                server_tooltip[0] = format_tooltip()
                dist = format_distance(cache[addr][0])
                ping = format_ping(cache[addr][1])

                tooltip = server_tooltip[0] + dist + ping
                grid.update_statusbar(tooltip)
                return
            self.emit("on_distcalc_started")
            self.current_proc = CalcDist(self, addr, self.queue, cache)
            self.current_proc.start()
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
                    grid.right_panel.filters_vbox.maps_entry.grab_focus()
                case _:
                    return False
        elif keyname.isnumeric() and int(keyname) > 0:
            if self.get_first_col() == "Mod":
                return
            digit = (int(keyname) - 1)
            grid.right_panel.filters_vbox.toggle_check(checks[digit])
        else:
            return False

    def _focus_first_row(self):
        path = Gtk.TreePath(0)
        try:
            it = mod_store.get_iter(path)
            self.get_selection().select_path(path)
        except ValueError:
            pass

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
        wait_dialog = GenericDialog(parent, "Refreshing player count", Popup.WAIT)
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
            if len(server_store) == 0:
                call_out(self, "start_cooldown", "", "")
                api_warn_msg = """\
                    No servers returned. Possible network issue or API key on cooldown?
                    Return to the main menu, wait 60s, and try again.
                    If this issue persists, your API key may be defunct."""
                spawn_dialog(self.get_outer_window(), textwrap.dedent(api_warn_msg), Popup.NOTIFY)

        grid = self.get_outer_grid()
        right_panel = grid.right_panel

        filters = toggled_checks + keyword_filter + selected_map
        data = call_out(self, "dump_servers", mode, *filters)

        toggle_signal(self, self.selected_row, '_on_tree_selection_changed', False)
        parse_server_rows(data)
        server_tooltip[0] = format_tooltip()
        grid.update_statusbar(server_tooltip[0])

        map_data = call_out(self, "get_unique_maps", mode)
        maps = map_data.stdout.splitlines()
        self.set_model(server_store)
        GLib.idle_add(loadTable)

    def _background_quad(self, dialog, mode):
        # currently only used by list mods method
        def load():
            dialog.destroy()
            # suppress button panel if store is empty
            if isinstance(panel_last_child, ModSelectionPanel):
                if total_mods == 0:
                    # do not forcibly remove previously added widgets when reloading in-place
                    grid.sel_panel.set_visible(False)
                    right_panel.set_filter_visibility(False)
                else:
                    grid.sel_panel.set_visible(True)
                    grid.sel_panel.initialize()

            self.set_model(mod_store)
            self.grab_focus()
            size = locale.format_string('%.3f', total_size, grouping=True)
            pretty = pluralize("mods", total_mods)
            grid.update_statusbar(f"Found {total_mods:n} {pretty} taking up {size} MiB")

            toggle_signal(self, self.selected_row, '_on_tree_selection_changed', True)
            toggle_signal(self, self, '_on_keypress', True)
            self._focus_first_row()
            if total_mods == 0:
                logger.info("Nothing to do, spawning notice dialog")
                spawn_dialog(self.get_outer_window(), data.stdout, Popup.NOTIFY)

        widgets = relative_widget(self)
        grid = widgets["grid"]
        right_panel = grid.right_panel
        data = call_out(self, mode.dict["label"], '')
        panel_last_child = right_panel.get_children()[-1]

        # suppress errors if no mods available on system
        if data.returncode == 1:
            logger.info("Failed to find mods on local system")
            total_mods = 0
            total_size = 0
            GLib.idle_add(load)
        else:
            # show button panel missing (prevents duplication when reloading in-place)
            if not isinstance(panel_last_child, ModSelectionPanel):
                grid.sel_panel.set_visible(True)
            result = parse_mod_rows(data)
            total_size = result[0]
            total_mods = result[1]
            logger.info("Found mods on local system")
            logger.info("Total mod size: %s" %(total_size))
            logger.info("Total mod count: %s" %(total_mods))
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
        # steam deck column title workaround
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
        self.set_headers_visible(True)

        toggle_signal(self, self.selected_row, '_on_tree_selection_changed', False)
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

        self.update_first_col(mode.dict["label"])

        widgets = relative_widget(self)
        grid = widgets["grid"]
        window = widgets["outer"]
        window.hb.set_subtitle(mode.dict["label"])

        transient_parent = window

        # Reset map selection
        selected_map.clear()
        selected_map.append("Map=All maps")

        self.set_selection_mode(Gtk.SelectionMode.SINGLE)

        for check in checks:
            toggle_signal(self.get_outer_grid().right_panel.filters_vbox, check, '_on_check_toggle', True)
        toggle_signal(self, self, '_on_keypress', True)

        string = mode.dict["label"]
        if mode == RowType.SCAN_LAN:
            lan_dialog = LanButtonDialog(self.get_outer_window())
            port = lan_dialog.get_selected_port()
            if port is None:
                grid = self.get_outer_grid()
                right_panel = grid.right_panel
                vbox = right_panel.button_vbox
                vbox._update_single_column(ButtonType.MAIN_MENU)
                return
            string = string + ":" + port

        wait_dialog = GenericDialog(transient_parent, "Fetching server metadata", Popup.WAIT)
        wait_dialog.show_all()
        thread = threading.Thread(target=self._background, args=(wait_dialog, string))
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

    def set_selection_mode(self, mode):
        sel = self.get_selection()
        sel.set_mode(mode)

    def update_quad_column(self, mode):
        toggle_signal(self, self.selected_row, '_on_tree_selection_changed', False)
        for column in self.get_columns():
            self.remove_column(column)

        self.set_headers_visible(True)
        mod_store.clear()
        log_store.clear()

        if mode == RowType.LIST_MODS:
            cols = mod_cols
            self.set_model(mod_store)
        else:
            cols = log_cols
            self.set_model(log_store)

        for i, column_title in enumerate(cols):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i, foreground=4)
            if mode == RowType.LIST_MODS:
                if i == 3:
                    column.set_cell_data_func(renderer, self._format_float, func_data=None)
            column.set_sort_column_id(i)
            # hidden color property column
            if i != 4:
                self.append_column(column)

        widgets = relative_widget(self)
        grid = widgets["grid"]
        window = widgets["outer"]
        try:
            window.hb.set_subtitle(mode.dict["quad_label"])
        except KeyError:
            window.hb.set_subtitle(mode.dict["label"])

        if mode == RowType.LIST_MODS:
            self.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        else:
            # short circuit and jump to debug log
            data = call_out(self, "show_log")
            res = parse_log_rows(data)
            toggle_signal(self, self, '_on_keypress', True)
            if res == 1:
                spawn_dialog(self.get_outer_window(), "Failed to load log file, possibly corrupted", Popup.NOTIFY)
            return


        wait_dialog = GenericDialog(window, "Checking mods", Popup.WAIT)
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

        wait_dialog = GenericDialog(transient_parent, "Querying server and aligning mods", Popup.WAIT)
        wait_dialog.show_all()
        thread = threading.Thread(target=self._background_connection, args=(wait_dialog, record))
        thread.start()

    def _on_row_activated(self, treeview, tree_iter, col):
        context = self.get_first_col()
        chosen_row = self.get_column_at_index(0)

        # recycled from ModDialog
        if self.view == WindowContext.TABLE_MODS:
            select = treeview.get_selection()
            sels = select.get_selected_rows()
            (model, pathlist) = sels
            if len(pathlist) < 1:
                return
            path = pathlist[0]
            tree_iter = model.get_iter(path)
            mod_id = model.get_value(tree_iter, 2)
            base_cmd = "open_workshop_page"
            subprocess.Popen(['/usr/bin/env', 'bash', funcs, base_cmd, mod_id])
            return

        dynamic_contexts = [
                WindowContext.TABLE_LOG,
                WindowContext.TABLE_SERVER,
                WindowContext.TABLE_API
                ]

        # if already in table, the row selection is arbitrary
        if self.view in dynamic_contexts:
                cr = RowType.DYNAMIC
        else:
            cr = RowType.str2rowtype(chosen_row)
            wc = WindowContext.row2con(cr)
            self.view = wc

        output = self.view, cr
        logger.info("User selected '%s' for the context '%s'" %(chosen_row, context))

        if self.view == WindowContext.TABLE_LOG and cr == RowType.DYNAMIC:
            return

        outer = self.get_outer_window()
        right_panel = outer.grid.right_panel
        filters_vbox = right_panel.filters_vbox

        server_contexts = [
                          RowType.SCAN_LAN,
                          RowType.SERVER_BROWSER,
                          RowType.RECENT_SERVERS,
                          RowType.SAVED_SERVERS
                          ]

        # server contexts share the same model type
        if cr in server_contexts:
            if cr == RowType.SERVER_BROWSER:
                cooldown = call_out(self, "test_cooldown", "", "")
                if cooldown.returncode == 1:
                    spawn_dialog(outer, cooldown.stdout, Popup.NOTIFY)
                    # reset context to main menu if navigation was blocked
                    self.view = WindowContext.MAIN_MENU
                    return 1
                for check in checks:
                    toggle_signal(filters_vbox, check, '_on_check_toggle', False)
                reinit_checks()
            else:
                for check in checks:
                    toggle_signal(filters_vbox, check, '_on_check_toggle', False)
                    if check.get_label() not in toggled_checks:
                        toggled_checks.append(check.get_label())
                        check.set_active(True)
            self._update_multi_column(cr)

            map_store.clear()
            map_store.append(["All maps"])
            right_panel.set_active_combo()

            toggle_signal(filters_vbox, filters_vbox.maps_combo, '_on_map_changed', True)
            toggle_signal(self, self.selected_row, '_on_tree_selection_changed', True)
            self.grab_focus()
            return

        if self.view == WindowContext.TABLE_MODS or self.view == WindowContext.TABLE_LOG:
            toggle_signal(self, self.selected_row, '_on_tree_selection_changed', False)
            self.update_quad_column(cr)
            toggle_signal(self, self.selected_row, '_on_tree_selection_changed', True)
        elif self.view == WindowContext.TABLE_SERVER or self.view == WindowContext.TABLE_API:
            self._attempt_connection()
        else:
            # implies any other non-server option selected from main menu
            process_tree_option(output, self)


def format_metadata(row_sel):
    for i in RowType:
        if i.dict["label"] == row_sel:
            row = i
            prefix = i.dict["tooltip"]
    vals = {
            "branch": config_vals[0],
            "debug": config_vals[1],
            "auto_install": config_vals[2],
            "name": config_vals[3],
            "fav_label": config_vals[4],
            "preferred_client": config_vals[5],
            "fullscreen": config_vals[6]
            }
    try:
        alt = row.dict["alt"]
        default = row.dict["default"]
        val = row.dict["val"]
    except KeyError:
        return prefix
    try:
        cur_val = vals[val]
        if cur_val == "":
            return "%s | Current: '%s'" %(prefix, default)
        # TODO: migrate to human readable config values
        elif cur_val == "1":
            return "%s | Current: '%s'" %(prefix, alt)
        else:
            return "%s | Current: '%s'" %(prefix, cur_val)
    except KeyError:
        return prefix


def format_tooltip():
    hits = len(server_store)
    players = 0
    for row in server_store:
        players+= row[4]
    hits_pretty = pluralize("matches", hits)
    players_pretty = pluralize("players", players)
    tooltip = f"Found {hits:n} {hits_pretty} with {players:n} {players_pretty}"
    return tooltip


def filter_servers(transient_parent, filters_vbox, treeview, context):
    def filter(dialog):
        def clear_and_destroy():
            parse_server_rows(data)
            server_tooltip[0] = format_tooltip()
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

    dialog = GenericDialog(transient_parent, "Filtering results", Popup.WAIT)
    dialog.show_all()
    server_store.clear()

    thread = threading.Thread(target=filter, args=(dialog,))
    thread.start()


class AppHeaderBar(Gtk.HeaderBar):
    def __init__(self):
        super().__init__()
        self.props.title = app_name
        self.set_decoration_layout(":minimize,maximize,close")
        self.set_show_close_button(True)


class GenericDialog(Gtk.MessageDialog):
    def __init__(self, parent, text, mode):

        def _on_dialog_delete(self, response_id):
            """Passively ignore user-input"""
            return True

        match mode:
            case Popup.WAIT:
                dialog_type = Gtk.MessageType.INFO
                button_type = Gtk.ButtonsType.NONE
                header_text = "Please wait"
            case Popup.NOTIFY:
                dialog_type = Gtk.MessageType.INFO
                button_type = Gtk.ButtonsType.OK
                header_text = "Notice"
            case Popup.CONFIRM:
                dialog_type = Gtk.MessageType.QUESTION
                button_type = Gtk.ButtonsType.OK_CANCEL
                header_text = "Confirmation"
            case Popup.ENTRY:
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
            title="DZGUI - Dialog",
            modal=True,
        )

        if mode == Popup.WAIT:
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
            title="DZGUI - Dialog",
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


def ChangelogDialog(parent):

    text = ''
    mode = "Changelog -- content can be scrolled"
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
    Ctrl-m: jump to maps field
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
        wait_dialog = GenericDialog(parent, "Checking ping", Popup.WAIT)
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

        wait_dialog = GenericDialog(parent, "Fetching modlist", Popup.WAIT)
        wait_dialog.show_all()
        thread = threading.Thread(target=self._background, args=(wait_dialog, parent, record))
        thread.start()

    def _background(self, dialog, parent, record):
        def _load():
            dialog.destroy()
            if data.returncode == 1:
                spawn_dialog(parent, "Server has no mods installed or is unsupported in this mode", Popup.NOTIFY)
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

        if link is not None:
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
        self.sel_panel = ModSelectionPanel()
        self.right_panel.pack_start(self.sel_panel, False, False, 0)
        self.show_all()

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
        server_tooltip[0] = format_tooltip()
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

        GLib.set_prgname(app_name)
        self.win = OuterWindow(is_steam_deck, is_game_mode)
        self.win.set_icon_name("dzgui")

        accel = Gtk.AccelGroup()
        accel.connect(Gdk.KEY_q, Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE, self._halt_window_subprocess)
        self.win.add_accel_group(accel)

        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, Gtk.main_quit)
        Gtk.main()

    def _halt_window_subprocess(self, accel_group, window, code, flag):
        self.win.halt_proc_and_quit(self, None)


class ModSelectionPanel(Gtk.Box):
    def __init__(self):
        super().__init__(spacing=6)
        self.set_orientation(Gtk.Orientation.VERTICAL)

        labels = [
                "Select all",
                "Unselect all",
                "Delete selected",
                "Highlight stale"
                ]

        self.active_button = None

        for l in labels:
            button = Gtk.Button(label=l)
            button.set_margin_start(10)
            button.set_margin_end(10)
            button.connect("clicked", self._on_button_clicked)
            self.pack_start(button, False, True, 0)


    def initialize(self):
        l = len(self.get_children())
        last = self.get_children()[l-1]
        last_label = last.get_label()
        for i in self.get_children():
            match i.get_label():
                case "Select stale":
                    i.destroy()
                case "Unhighlight stale":
                    i.set_label("Highlight stale")


    def _on_button_clicked(self, button):
        self.active_button = button
        label = button.get_label()
        widgets = relative_widget(self)
        parent = widgets["outer"]
        treeview = widgets["treeview"]
        (model, pathlist) = treeview.get_selection().get_selected_rows()
        match label:
            case "Select all":
                treeview.toggle_selection(True)
            case "Unselect all":
                treeview.toggle_selection(False)
            case "Delete selected":
                ct = len(pathlist)
                if ct < 1:
                    return
                self._iterate_mod_deletion(model, pathlist, ct)
            case "Highlight stale":
                process_tree_option([treeview.view, RowType.HIGHLIGHT], treeview)
            case "Unhighlight stale":
                self.colorize_cells(False)
                self._remove_last_button()
            case "Select stale":
                for i in range (0, len(mod_store)):
                    if mod_store[i][4] == "#FF0000":
                        path = Gtk.TreePath(i)
                        treeview.get_selection().select_path(path)


    def toggle_select_stale_button(self, bool):
        if bool is True:
            button = Gtk.Button(label="Select stale")
            button.set_margin_start(10)
            button.set_margin_end(10)
            button.connect("clicked", self._on_button_clicked)
            self.pack_start(button, False, True, 0)
            self.show_all()

    def colorize_cells(self, bool):
        def _colorize(path, color):
            mod_store[path][4] = color
            
        widgets = relative_widget(self)
        parent = widgets["outer"]
        treeview = widgets["treeview"]
        (model, pathlist) = treeview.get_selection().get_selected_rows()

        if bool is False:
            default = None
            for i in range (0, len(mod_store)):
                path = Gtk.TreePath(i)
                it = mod_store.get_iter(path)
                _colorize(path, None)
            self.active_button.set_label("Highlight stale")
            return

        with open(stale_mods_temp_file, "r") as infile:
            lines = [line.rstrip('\n') for line in infile]

        for i in range (0, len(mod_store)):
            red = "#FF0000"
            path = Gtk.TreePath(i)
            it = mod_store.get_iter(path)
            if model.get_value(it, 2) not in lines:
                _colorize(path, red)
            treeview.toggle_selection(False)
            self.active_button.set_label("Unhighlight stale")


    def _iterate_mod_deletion(self, model, pathlist, ct):
        widgets = relative_widget(self)
        parent = widgets["outer"]
        treeview = widgets["treeview"]

        pretty = pluralize("mods", ct)
        conf_msg = f"You are going to delete {ct} {pretty}. Proceed?"
        success_msg = f"Successfully deleted {ct} {pretty}."
        fail_msg = "An error occurred during deletion. Aborting."

        res = spawn_dialog(parent, conf_msg, Popup.CONFIRM)
        if res != 0:
            return

        mods = []
        for i in pathlist:
            it = model.get_iter(i)
            symlink = model.get_value(it, 1)
            path = model.get_value(it, 2)
            concat = symlink + " " + path + "\n"
            mods.append(concat)
        # hedge against large number of arguments passed to shell
        with open(mods_temp_file, "w") as outfile:
            outfile.writelines(mods)
        process_tree_option([treeview.view, RowType.DELETE_SELECTED], treeview)


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
    
        completion = Gtk.EntryCompletion(inline_completion=True)
        completion.set_text_column(0)
        completion.set_minimum_key_length(1)
        completion.connect("match_selected", self._on_completer_match)

        renderer_text = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END)
        self.maps_combo = Gtk.ComboBox.new_with_model_and_entry(map_store)
        self.maps_combo.set_entry_text_column(0)
    
        # instantiate maps completer entry
        self.maps_entry = self.maps_combo.get_child()
        self.maps_entry.set_completion(completion)
        self.maps_entry.set_placeholder_text("Filter by map")
        self.maps_entry.connect("changed", self._on_map_completion, True)
        self.maps_entry.connect("key-press-event", self._on_map_entry_keypress)

        self.maps_combo.pack_start(renderer_text, True)
        self.maps_combo.connect("changed", self._on_map_changed)
        self.maps_combo.connect("key-press-event", self._on_esc_pressed)

        self.pack_start(self.filters_label, False, False, True)
        self.pack_start(self.keyword_entry, False, False, True)
        self.pack_start(self.maps_combo, False, False, True)

        for i, check in enumerate(checks[0:]):
            self.pack_start(checks[i], False, False, True)

    def _on_map_entry_keypress(self, entry, event):
        match event.keyval:
            case Gdk.KEY_Return:
                text = entry.get_text()
                if text is None:
                    return
                # if entry is exact match for value in liststore,
                # trigger map change function
                for i in enumerate(map_store):
                    if text == i[1][0]:
                        self.maps_combo.set_active(i[0])
                        self._on_map_changed(self.maps_combo)
            case Gdk.KEY_Escape:
                GLib.idle_add(self.restore_focus_to_treeview)
                # TODO: this is a workaround for widget.grab_remove()
                # set cursor position to SOL when unfocusing
                text = self.maps_entry.get_text()
                self.maps_entry.set_position(len(text))
            case _:
                return

    def _on_completer_match(self, completion, model, iter):
        self.maps_combo.set_active_iter(iter)

    def _on_map_completion(self, entry, editable):
        text = entry.get_text()
        completion = entry.get_completion()

        if len(text) >= completion.get_minimum_key_length():
            completion.set_model(map_store)
            self._on_map_changed(self.maps_combo)

    def grab_keyword_focus(self):
        self.keyword_entry.grab_focus()

    def restore_focus_to_treeview(self):
        grid = self.get_outer_grid()
        grid.scrollable_treelist.treeview.grab_focus()
        return False

    def _on_esc_pressed(self, entry, event):
        match event.keyval:
            case Gdk.KEY_Escape:
                GLib.idle_add(self.restore_focus_to_treeview)
            case _:
                return False

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
            # take no action if completer query is same as current map sel
            old_sel = selected_map[0].split("Map=")[1]
            model = combo.get_model()
            selection = model[tree_iter][0]
            if selection == old_sel:
                return

            selected_map.clear()
            if selection is not None:
                selected_map.append("Map=" + selection)
                logger.info("User selected map '%s'" %(selection))
                filter_servers(transient_parent, self, treeview, context)
                self.maps_entry.set_text(selection)


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
