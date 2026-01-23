import logging
import signal
import warnings

from typing import TYPE_CHECKING, Literal

from dzgui.const.enum import NotebookPage
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
from dzgui.views.pages.log import Log
from dzgui.views.pages.mods import Mods
from dzgui.views.pages.options import Options
from dzgui.views.pages.servers import ServerNotebook
from dzgui.views.pages.thanks import Thanks

from dzgui.views.components.statusbar import Statusbar
from dzgui.views.components.right_panel import RightPanel
from dzgui.views.mixins.scrollable_mixin import ScrollableMixin

if TYPE_CHECKING:
    from dzgui.config.userprefs import UserPrefs

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa E402

logger = logging.getLogger(__name__)
# https://bugzilla.gnome.org/show_bug.cgi?id=708676
warnings.filterwarnings("ignore", ".*g_value_get_int", Warning)

# TODO: move to controller
# kilometer cache; note, user may change measurement it partway through, flush cache
# cache: dict[str, int] = {}

## TODO: move to configs/servers
# def query_history() -> list | None:
#    history_file = MainController.get_prefs().paths.history
#    try:
#        with open(history_file, "r") as f:
#            rows = [row.rstrip("\n") for row in f]
#    except OSError:
#        rows = None
#    return rows
#
# def process_tree_option(choice: RowType) -> None:
#    # server tables
#    if command == RowType.RESOLVE_IP:
#        record = treeview.get_record()
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
#            spawn_dialog("No favorite server currently set", Popup.NOTIFY)
#            return
#
#        record = str_to_record(record)
#        thread_new_with_dialog(
#            treeview.prepare_connection,
#            parse_shell_output,
#            "Querying server",
#            command,
#            [record],
#        )
#        return
#
## TODO: belongs in model
# def str_to_record(record: str) -> Record | None:
#    r = record.split(":")
#    if len(r) != 3:
#        return None
#    return Record(r[0], int(r[1]), int(r[2]))
#
## TODO: ibid
# def record_to_str(record: Record) -> str:
#    return f"{record.ip}:{record.gameport}:{record.qport}"
#
#
# def connect_by_ip(enum: RowType, response: str) -> None:
#    def _prep(response: str) -> None:
#        record = Servers.validate_ip(response)
#        proc = treeview.prepare_connection(record)
#        return proc
#
#    thread_new_with_dialog(
#        _prep, parse_shell_output, "Querying IP", enum, [response]
#    )
#    return
#
#
# def connect_by_id(enum: RowType, uid: str, key: str) -> None:
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
#    #    proc = treeview.prepare_connection(record)
#    #    return proc
#
#    #thread_new_with_dialog(
#    #    _prep, parse_shell_output, "Querying API", enum, [key, response]
#    #)
#    #return
#
#


class OuterWindow(Gtk.Window):
    def __init__(self) -> None:
        super().__init__(title=APP_NAME, border_width=10, icon_name=APP_NAME_LOWER)

        self.hb = AppHeaderBar()
        MainController.register_widget("window", self)

        # NOTE: steam deck taskbar may occlude elements
        if MainController.get_prefs().is_steam_deck is False:
            self.set_titlebar(self.hb)

        self.connect("delete-event", self._on_delete_event)

        self.grid = Grid()
        self.add(self.grid)

        MainController.set_resolution(self)
        self.show_all()

        css.load_css()

        # TODO: first run
        MainController.open_page(NotebookPage.SERVERS)
        MainController.mediator.grid.conpan.lan.set_visible(False)
        self.grid.right_panel.sel_panel.hide()
        # TODO: POC, trigger page change here
        MainController.loaded = True
        MainController.populate_model()

    def _on_delete_event(self, window: "OuterWindow", event: Gdk.EventKey) -> None:
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


class Notebook(ScrollableMixin, Gtk.Notebook):  # type: ignore
    def __init__(self) -> None:
        super().__init__(show_tabs=False)

        self.prior_page: NotebookPage
        self.prior_status: str
        self.is_return = False

        MainController.register_widget("notebook", self)

        self.help = Help(MainController)
        self.clog = Changelog(MainController)

        self.keys = Keybindings()
        self.settings = Options(MainController)

        self.servers = ServerNotebook(MainController)
        self.mods = Mods(MainController)

        self.thanks = Thanks()
        self.log = Log(MainController)
        self.developers = Developers(MainController)

        self.pages = {
            self.help: NotebookPage.HELP,
            self.clog: NotebookPage.CHANGELOG,
            self.keys: NotebookPage.KEYS,
            self.settings: NotebookPage.OPTIONS,
            self.servers: NotebookPage.SERVERS,
            self.mods: NotebookPage.MODS,
            self.log: NotebookPage.LOG,
            self.thanks: NotebookPage.THANKS,
            self.developers: NotebookPage.DEVELOPERS,
        }
        self.indexes = {}

        """
        Note that due to historical reasons, Gtk.Notebook refuses to switch to a page
        unless the child widget is visible. Therefore, it is recommended to show child
        widgets before adding them to a notebook.
        """
        for page in self.pages:
            page.show_all()
            index = self.append_page(page)
            enum = self.pages[page]
            self.indexes[enum] = index

        self.connect_after("switch-page", self._on_page_changed)
        self.connect("key-press-event", self._on_keypress)

    def _on_keypress(self, widget: Gtk.Widget, event: Gdk.EventKey) -> None:
        match event.keyval:
            case Gdk.KEY_Right | Gdk.KEY_l:
                if event.state is Gdk.ModifierType.CONTROL_MASK:
                    return
                MainController.focus_button_box()
            case Gdk.KEY_question:
                self.toggle_keybindings()

    def return_prior(self) -> None:
        """
        Gtk.Notebook focuses the first input field when changing pages;
        this workaround unhighlights the selected region and makes entry
        fields unfocusable prior to the page 'switch-page' signal,
        then makes them focusable again

        Used when switching back from NotebookPage.KEYS to avoid cursor
        getting stuck inside text entry fields
        """
        if self.prior_page is NotebookPage.OPTIONS:
            self.settings.block_text_entry()
            self.set_page_by_enum(self.prior_page)
            self.settings.unblock_text_entry()
            return
        self.is_return = True
        self.set_page_by_enum(self.prior_page)

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
            # self.prior_status = MainController.get_statusbar()
            self.set_page_by_enum(NotebookPage.KEYS)

    def focus_current(self) -> None:
        widget = self.get_page()
        if widget is None:
            return

        if widget is self.servers:
            MainController.grab_active_treeview()
            return

        w = widget.get_children()[0]
        w.grab_focus()

    def get_page(self) -> Gtk.Widget | None:
        ind = self.get_current_page()
        widget = self.get_nth_page(ind)
        if not widget:
            return None
        return widget

    def set_page_by_enum(self, enum: NotebookPage) -> None:
        prior = self.get_page_by_enum()
        if prior is not None:
            self.prior_page = prior
        self.set_current_page(self.indexes[enum])
        self.focus_current()

    def _on_page_changed(
        self, notebook: "Notebook", page: Gtk.Widget, page_num: int
    ) -> None:
        return
        # enum = self.get_page_by_enum()
        # TODO: crumbs signal
        # if enum is not None:
        #     crumbs = enum.dict["crumbs"]
        #     MainController.set_crumbs(crumbs)

        # if self.is_return is True:
        #     MainController.mediator.statusbar.emit(
        #         "notebook_page_returned", self.prior_page
        #     )
        # else:
        #     MainController.mediator.statusbar.emit("notebook_page_changed", enum)
        # self.is_return = False


class Grid(Gtk.Grid):
    def __init__(self) -> None:
        super().__init__(column_homogeneous=True)

        MAX_ROWS = 3
        MAX_COLS = 3
        SINGLE_ROW = 1
        SINGLE_COL = 1

        MainController.register_widget("grid", self)

        self.statusbar = Statusbar(MainController)
        self.right_panel = RightPanel(MainController)
        # self.breadcrumbs = Gtk.Label(halign=Gtk.Align.START)
        # self.set_breadcrumbs(strings.label_main_menu)

        # self.bu = Gtk.Button(label="Shrink to fit", halign=Gtk.Align.END)
        # self.bu.connect("clicked", self._shrink)

        # self.crumb_box.add(self.bu)

        self.notebook = Notebook()
        self.conpan = ConnectPanel(MainController)
        from dzgui.views.components.crumbs import Breadcrumbs

        self.breadcrumbs = Breadcrumbs(MainController)
        self.crumb_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.crumb_box.add(self.breadcrumbs)

        self.attach(self.notebook, 0, 0, MAX_COLS, SINGLE_ROW)

        els = (
            (self.crumb_box, self.notebook, Gtk.PositionType.TOP, MAX_COLS, SINGLE_ROW),
            (self.conpan, self.notebook, Gtk.PositionType.BOTTOM, MAX_COLS, SINGLE_ROW),
            (
                self.statusbar,
                self.conpan,
                Gtk.PositionType.BOTTOM,
                MAX_COLS,
                SINGLE_ROW,
            ),
            (
                self.right_panel,
                self.notebook,
                Gtk.PositionType.RIGHT,
                SINGLE_COL,
                MAX_ROWS,
            ),
        )
        for el, sibling, pos, h_span, v_span in els:
            self.attach_next_to(el, sibling, pos, h_span, v_span)

        self.show_all()

    def _shrink(self, button: Gtk.Button) -> None:
        tv = MainController.get_active_treeview()
        tv.shrink_to_fit()

    def toggle_filter_panel(self, state: bool) -> None:
        self.right_panel.filters_vbox.set_visible(state)

    def toggle_connect_panel(self, state: bool) -> None:
        self.conpan.set_visible(state)

    def toggle_refresh_button(self, state: bool) -> None:
        self.right_panel.refresh_button.set_visible(state)

    # TODO: make this method internal to Statusbar
    def get_breadcrumbs(self) -> str:
        return self.breadcrumbs.get_text()

    def set_breadcrumbs(self, text: str) -> None:
        crumbs = embolden(text)
        self.breadcrumbs.set_markup(crumbs)


class App(Gtk.Application):
    def __init__(self, prefs: "UserPrefs") -> None:
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

        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, self._catch_sigint)
        Gtk.main()

    def _catch_sigint(self) -> Literal[True]:
        self.win.halt_proc_and_quit()
        return True

    def _halt_window_subprocess(
        self,
        accel_group: Gtk.AccelGroup,
        window: "OuterWindow",
        code: Gdk.EventKey,
        flag: Gdk.ModifierType,
    ) -> None:
        self.win.halt_proc_and_quit()


MainController = Controller()

# TODO: icon sanity check, log result
# theme = Gtk.IconTheme.get_default()
# icons = theme.list_icons(None)
# print("steam_tray_mono" in icons)
# FIXME:
