import json
import locale
import logging
import multiprocessing
import os
import re
import signal
import subprocess
import textwrap
import threading
import typing  # noqa
import warnings

#from concurrent.futures import wait
#from concurrent.futures import ThreadPoolExecutor

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from dzgui.const.enum import NotebookPage, VAdjustment
from dzgui.const.constants import NO_EXPAND, NO_FILL
from dzgui.const.constants import APP_NAME, APP_NAME_LOWER
from dzgui.controllers.mc import Controller
from dzgui.util import css, strings
from dzgui.util.format import embolden

# NOTEBOOK ITEMS
# TODO: import notebook only and add components there?
from dzgui.views.pages.changelog import Changelog
from dzgui.views.components.connect_panel import ConnectPanel
from dzgui.views.pages.devs import Developers
from dzgui.views.pages.help import Help
from dzgui.views.pages.keys import Keybindings
from dzgui.views.pages.options import Options
from dzgui.views.pages.servers import ServerNotebook
from dzgui.views.pages.thanks import Thanks

from dzgui.views.components.statusbar import Statusbar
from dzgui.views.components.mod_panel import ModSelectionPanel
from dzgui.views.components.right_panel import RightPanel
from dzgui.views.components.toast import Toast
from dzgui.views.dialogs.generic import GenericDialog
from dzgui.views.mixins.scrollable_mixin import ScrollableMixin

# TREES
from dzgui.views.trees.tree_menu import MenuTreeView
from dzgui.views.trees.tree_log import LogTreeView
from dzgui.views.trees.tree_mods import ModTreeView
from dzgui.views.trees.tree_servers import ServerTreeView

# TODO: not going to be in base anymore
import dzgui.util._json as JSON  # noqa

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa E402

logger = logging.getLogger(__name__)
# https://bugzilla.gnome.org/show_bug.cgi?id=708676
warnings.filterwarnings("ignore", ".*g_value_get_int", Warning)

# TODO: move to controller
#cache: dict[str, int] = {}

## TODO: move to configs/servers
#def query_history() -> list | None:
#    history_file = MainController.get_prefs().paths.history
#    try:
#        with open(history_file, "r") as f:
#            rows = [row.rstrip("\n") for row in f]
#    except OSError:
#        rows = None
#    return rows
#
#def process_tree_option(choice: RowType) -> None:
#    context = AppNav.treeview.view
#    command = choice
#    cmd_string = command.dict["label"]
#    logger.info(f"Parsing tree option '{command}' for the context '{context}'")
#
#    # server tables
#    if command == RowType.RESOLVE_IP:
#        record = AppNav.treeview.get_record()
#        wait_msg = command.dict["wait_msg"]
#        show_wait_dialog = True
#
#        # TODO: needs threading, this is a slow process
#        # TODO: needs saving into config
#        # TODO: used by add/remove servers
#        real_ip = ip.resolve_ip(record)
#        #call_on_thread(
#        #    show_wait_dialog, cmd_string, wait_msg, record, choice=choice
#        #)
#        return
#
#    if command == RowType.QUICK_CONNECT:
#        record = MainController.query_config(Preferences.FAV_SRV)
#        if record == "":
#            AppNav.window.spawn_dialog("No favorite server currently set", Popup.NOTIFY)
#            return
#
#        record = str_to_record(record)
#        thread_new_with_dialog(
#            AppNav.treeview.prepare_connection,
#            parse_shell_output,
#            "Querying server",
#            command,
#            [record],
#        )
#        return
#
## TODO: belongs in model
#def str_to_record(record: str) -> Record | None:
#    r = record.split(":")
#    if len(r) != 3:
#        return None
#    return Record(r[0], int(r[1]), int(r[2]))
#
## TODO: ibid
#def record_to_str(record: Record) -> str:
#    return f"{record.ip}:{record.gameport}:{record.qport}"
#
#
#def connect_by_ip(enum: RowType, response: str) -> None:
#    def _prep(response: str) -> None:
#        record = Servers.validate_ip(response)
#        proc = AppNav.treeview.prepare_connection(record)
#        return proc
#
#    thread_new_with_dialog(
#        _prep, parse_shell_output, "Querying IP", enum, [response]
#    )
#    return
#
#
#def connect_by_id(enum: RowType, uid: str, key: str) -> None:
#    def _prep(key: str, response: str) -> None:
#        # TODO: if response is non numeric, raise dialog
#        if response.isnumeric() is False:
#            pass
#            # raise error
#            # raise BmIdError("ID must be numeric only")
#            # return
#        from dzgui.api.bm import map_id_to_record
#        try:
#            record = map_id_to_record(config, uid)
#        except Exception as e:
#            logger.critical(e)
#            # raise dialog
#            return
#    #    proc = AppNav.treeview.prepare_connection(record)
#    #    return proc
#
#    #thread_new_with_dialog(
#    #    _prep, parse_shell_output, "Querying API", enum, [key, response]
#    #)
#    #return
#
#
#def process_user_input(enum: RowType) -> None:
#    prompt = enum.dict["prompt"]
#    link_label = enum.dict["link_label"]
#    cmd_string = enum.dict["label"]
#
#    if enum == RowType.CONN_BY_ID:
#        key = MainController.query_config(Preferences.BM)
#        if len(key) == 0:
#            AppNav.window.spawn_dialog(
#                "No Battlemetrics API key is set; see Options", Popup.NOTIFY
#            )
#            return
#
#    user_entry = EntryDialog(prompt, Popup.ENTRY, link_label, button_type=enum)
#    response = user_entry.get_input()
#
#    if response is None:
#        logger.info("User aborted entry dialog")
#        return
#    logger.info(f"User entered: '{response}'")
#
#    if enum == RowType.CONN_BY_IP:
#        connect_by_ip(enum, response)
#        return
#
#    if enum == RowType.CONN_BY_ID:
#        connect_by_id(enum, response, key)
#        return
#
#    show_wait_dialog = True
#    wait_msg = "Working"
#    call_on_thread(
#        show_wait_dialog, cmd_string, wait_msg, response, choice=enum
#    )
#    return

class OuterWindow(Gtk.Window):
    def __init__(self) -> None:
        super().__init__(title=APP_NAME, border_width=10, icon_name=APP_NAME_LOWER)

        self.hb = AppHeaderBar()
        MainController.set_mediator(AppNav)
        AppNav.window = self

        # steam deck taskbar may occlude elements
        if MainController.get_prefs().is_steam_deck is False:
            self.set_titlebar(self.hb)

        self.connect("delete-event", self._on_delete_event)
        self.connect("key-press-event", self._on_keypress)

        MainController.set_resolution(self)

        self.grid = Grid()
        self.add(self.grid)

        self.show_all()

        self.grid.right_panel.filters_vbox.set_visible(False)
        self.grid.right_panel.enable_ping_button(False)
        self.grid.sel_panel.set_visible(False)

        css.load_css()
        AppNav.grid.notebook.set_page_by_enum(NotebookPage.SERVERS)

    def _on_keypress(self, widget: Gtk.Widget, event: Gdk.EventKey) -> None:
        if event.state is Gdk.ModifierType.CONTROL_MASK \
                and event.keyval is Gdk.KEY_d:
            if AppNav.right_panel.filters_vbox.keyword_entry.is_focus():
                return
            if AppNav.right_panel.filters_vbox.maps_entry.is_focus():
                return
            AppNav.right_panel.toggle_debug()

    def _on_delete_event(
        self, window: "OuterWindow", event: Gdk.EventKey
    ) -> None:
        self.halt_proc_and_quit()

    def halt_proc_and_quit(self) -> None:
        MainController.terminate_process()
        MainController.save_res_and_quit()


class AppHeaderBar(Gtk.HeaderBar):
    def __init__(self) -> None:
        super().__init__()
        self.props.title = APP_NAME
        self.set_decoration_layout(":minimize,maximize,close")
        self.set_show_close_button(True)


# TODO: deprecated
class ScrollableNote(ScrollableMixin, Gtk.Box):
    def __init__(self, content_box: Gtk.Box, back_button: bool = False):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self.scrollable = Gtk.ScrolledWindow()
        self.scrollable.set_vexpand(True)

        self.back_button = Gtk.Button(
            label="Back", hexpand=True, halign=Gtk.Align.CENTER
        )

        self.gutter = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, valign=Gtk.Align.END
        )
        if back_button:
            self.gutter.add(self.back_button)
            self.back_button.connect("clicked", self._on_back_clicked)

        self.scrollable.add(content_box)
        self.add(self.scrollable)
        self.add(self.gutter)

    def _on_back_clicked(self, button: Gtk.Button) -> None:
        AppNav.notebook.return_prior()


class Notebook(ScrollableMixin, Gtk.Notebook):
    def __init__(self) -> None:
        super().__init__(show_tabs=False, show_border=False)

        AppNav.notebook = self
        self.prior_page: NotebookPage
        self.prior_status: str

        self.help = Help(MainController)
        view = self.help.get_treeview()
        AppNav.menu = view

        self.change = Changelog(MainController)
        self.clog = ScrollableNote(self.change, back_button=False)
        self.clog.scrollable.set_propagate_natural_width(False)

        # TODO: scrollable internally
        self.keys = ScrollableNote(Keybindings())
        self.settings = Options(MainController)

        # TODO: make all treeviews internally scrollable in base class
        # server and quad tables should have hexpand property set to True
        # add all treeviews as page and register them to AppNav and self.indexes
        # when switching to a treeview, update relevant view and just pop that page
        # instead of loading/unloading the model each time
        self.servers = ServerNotebook(MainController)
        AppNav.servers = self.servers

        self.quad = Gtk.ScrolledWindow()

        self.scroll_mod = Gtk.ScrolledWindow()
        # TODO: register this table
        self.quad_table = ModTreeView(MainController)
        AppNav.modtreeview = self.quad_table
        self.scroll_mod.add(self.quad_table)

        self.scroll_log = Gtk.ScrolledWindow()
        self.scroll_log.set_hexpand(True)
        self.log_table = LogTreeView(MainController)
        AppNav.logtreeview = self.log_table
        self.scroll_log.add(self.log_table)

        self.thanks = ScrollableNote(Thanks(), back_button=False)

        developers = Developers(MainController)
        self.developers = ScrollableNote(developers)

        self.pages = {
            self.help: NotebookPage.HELP,
            self.clog: NotebookPage.CHANGELOG,
            self.keys: NotebookPage.KEYS,
            self.settings: NotebookPage.OPTIONS,
            self.servers: NotebookPage.SERVERS,
            self.scroll_mod: NotebookPage.MODS,
            self.scroll_log: NotebookPage.LOG,
            self.thanks: NotebookPage.THANKS,
            self.developers: NotebookPage.DEVELOPERS,
        }
        self.indexes = {}

        """
        Note that due to historical reasons, GtkNotebook refuses to switch to a page
        unless the child widget is visible. Therefore, it is recommended to show child
        widgets before adding them to a notebook.
        """
        for page in self.pages:
            page.show_all()
            index = self.append_page(page)
            enum = self.pages[page]
            crumbs = enum.dict["crumbs"]
            self.indexes[enum] = index

        self.connect_after("switch-page", self._on_page_changed)
        self.connect("key-press-event", self._on_keypress)

    def _on_mods_focus_change(self, widget: ModTreeView, event: Gdk.EventFocus) -> None:
        MainController.toggle_mod_panel(event.in_)

    def _on_keypress(self, widget: Gtk.Widget, event: Gdk.EventKey) -> None:
        page = self.get_page()

        match event.keyval:
            case Gdk.KEY_Return:
                page = self.get_page()
                if page:
                    page.back_button.clicked()
            case Gdk.KEY_Right | Gdk.KEY_l:
                if event.state is Gdk.ModifierType.CONTROL_MASK:
                    return
                AppNav.right_panel.focus_button_box()
            case Gdk.KEY_question:
                self.toggle_keybindings()

        # NOTE: abort on non scrollable pages
        # TODO: this should be an internal property of those pages
        allowed = (NotebookPage.KEYS, NotebookPage.CHANGELOG, NotebookPage.THANKS)
        if self.pages[page] not in allowed:
            return

        match event.keyval:
            case Gdk.KEY_k | Gdk.KEY_Up:
                page._set_adjustment(VAdjustment.UP)
            case Gdk.KEY_Down | Gdk.KEY_j:
                page._set_adjustment(VAdjustment.DOWN)
            case Gdk.KEY_g:
                page._set_adjustment(VAdjustment.TOP)
            case Gdk.KEY_G:
                page._set_adjustment(VAdjustment.BOTTOM)

    def return_prior(self) -> None:
        """
        Gtk.Notebook focuses the first input field when changing pages;
        this workaround unhighlights the selected region and makes entry
        fields unfocusable prior to the page 'switch-page' signal,
        then makes them focusable again

        Used when switching back from NotebookPage.KEYS
        """
        if self.prior_page is NotebookPage.OPTIONS:
            self.settings.block_text_entry()
            self.set_page_by_enum(self.prior_page)
            self.settings.unblock_text_entry()
            return
        self.set_page_by_enum(self.prior_page)
        MainController.set_statusbar(self.prior_status)

    def get_page_by_enum(self) -> NotebookPage | None:
        for k, v in self.indexes.items():
            if v == self.get_current_page():
                return k
        return None

    def toggle_keybindings(self) -> None:
        cur_page = self.get_page_by_enum()
        if cur_page == NotebookPage.KEYS:
            self.return_prior()
        else:
            self.prior_status = MainController.get_statusbar()
            self.set_page_by_enum(NotebookPage.KEYS)

    def focus_current(self) -> None:
        widget = self.get_page()
        if widget is None:
            return

        if widget is self.servers:
            view = self.servers.get_active_treeview()
            view.grab_focus()
            return

        w = widget.get_children()[0]
        try:
            w.focus_first_row()
            w.grab_focus()
        except Exception as e:
            w.grab_focus()

    def get_page(self) -> Gtk.Widget | None:
        ind = self.get_current_page()
        widget = self.get_nth_page(ind)
        if not widget:
            return None
        return widget

    def set_page_by_enum(self, enum: NotebookPage) -> None:
        self.prior_page = self.get_page_by_enum()
        self.set_current_page(self.indexes[enum])
        self.focus_current()

        # TODO: should be an internal property of those pages
        match enum:
            case NotebookPage.KEYS:
                MainController.set_statusbar("")
                AppNav.grid.hide_connect_panel()
            case NotebookPage.SERVERS:
                # TODO: consolidate in mc.py
                AppNav.grid.show_connect_panel()
                self.servers.get_active_treeview().grab_focus()
                MainController.update_server_status()
                crumbs = self.servers.get_cached_label()
                MainController.set_crumbs(crumbs)
            case _:
                AppNav.grid.hide_connect_panel()

    def _on_page_changed(
        self, notebook: "Notebook", page: Gtk.Widget, page_num: int
    ) -> None:
        enum = self.get_page_by_enum()
        is_mods = True if enum is NotebookPage.MODS else False
        MainController.toggle_mod_panel(is_mods)

        # TODO:
        crumbs = enum.dict["crumbs"]
        MainController.set_crumbs(crumbs)


class Grid(Gtk.Grid):
    def __init__(self) -> None:
        super().__init__()
        self.set_column_homogeneous(True)

        self.statusbar = Statusbar(MainController)
        self.breadcrumbs = Gtk.Label(halign=Gtk.Align.START)
        self.set_breadcrumbs(strings.label_main_menu)

        AppNav.statusbar = self.statusbar
        AppNav.grid = self

        # FIXME: do not pass AppNav to right panel
        self.right_panel = RightPanel(AppNav, MainController)
        self.sel_panel = ModSelectionPanel(MainController)
        self.right_panel.pack_start(self.sel_panel, NO_EXPAND, NO_FILL, 0)

        self.notebook = Notebook()

        self.attach(self.notebook, 0, 0, 3, 1)
        self.attach_next_to(
            self.breadcrumbs, self.notebook, Gtk.PositionType.TOP, 3, 1
        )

        self.conpan = ConnectPanel()
        self.attach_next_to(
            self.conpan, self.notebook, Gtk.PositionType.BOTTOM, 3, 1
        )

        self.attach_next_to(
            self.statusbar, self.conpan, Gtk.PositionType.BOTTOM, 3, 1
        )
        self.attach_next_to(
            self.right_panel, self.notebook, Gtk.PositionType.RIGHT, 1, 1
        )
        self.show_all()

    def hide_connect_panel(self) -> None:
        self.conpan.set_visible(False)

    def show_connect_panel(self) -> None:
        self.conpan.set_visible(True)

    def get_breadcrumbs(self) -> str:
        return self.breadcrumbs.get_text()

    def set_breadcrumbs(self, text: str) -> None:
        crumbs = embolden(text)
        self.breadcrumbs.set_markup(crumbs)


class App(Gtk.Application):
    def __init__(self, prefs) -> None:
        GLib.set_prgname(APP_NAME)
        MainController.set_prefs(prefs)

        self.win = OuterWindow()

        accel = Gtk.AccelGroup()
        accel.connect(
            Gdk.KEY_q,
            Gdk.ModifierType.CONTROL_MASK,
            Gtk.AccelFlags.VISIBLE,
            self._halt_window_subprocess,
        )
        self.win.add_accel_group(accel)

        # FIXME: hacky
        AppNav.notebook.servers.notebook.next_page()
        AppNav.notebook.servers.notebook.prev_page()
        MainController.focus_notebook()

        GLib.unix_signal_add(
            GLib.PRIORITY_DEFAULT, signal.SIGINT, self._catch_sigint
        )
        Gtk.main()

    def _catch_sigint(self) -> None:
        self.win.halt_proc_and_quit()

    def _halt_window_subprocess(
        self,
        accel_group: Gtk.AccelGroup,
        window: "OuterWindow",
        code: Gdk.EventKey,
        flag: Gdk.ModifierType,
    ) -> None:
        self.win.halt_proc_and_quit()


class AppNavigation:
    grid: Grid
    window: OuterWindow
    notebook: Notebook
    right_panel: RightPanel
    statusbar: Statusbar
    menu: MenuTreeView
    servers: Gtk.ScrolledWindow
    browser: ServerTreeView
    saved: ServerTreeView
    recent: ServerTreeView
    lan: ServerTreeView
    modtreeview: ModTreeView
    logtreeview: LogTreeView
    # TODO: add tree_log and tree_server views here
    # or obtain via get_treeview()

AppNav = AppNavigation()
MainController = Controller()
