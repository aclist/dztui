import logging
import signal
import warnings

from typing import TYPE_CHECKING, Literal

from dzgui.const.constants import APP_NAME, APP_NAME_LOWER, STEAM_ICON
from dzgui.const.enum import NotebookPage
from dzgui.controllers.emitter import Emitter
from dzgui.controllers.mc import Controller
from dzgui.util import css, strings
from dzgui.util.keys import is_ctrl_mask
from dzgui.views.components.connect_panel import ConnectPanel
from dzgui.views.components.crumbs import Breadcrumbs
from dzgui.views.components.right_panel import RightPanel
from dzgui.views.components.statusbar import Statusbar
from dzgui.views.mixins.scrollable_mixin import ScrollableMixin

# TODO: import notebook only and add components there?
from dzgui.views.pages.changelog import Changelog
from dzgui.views.pages.devs import Developers
from dzgui.views.pages.help import Help
from dzgui.views.pages.keys import Keybindings
from dzgui.views.pages.log import Log
from dzgui.views.pages.mods import Mods
from dzgui.views.pages.options import Options
from dzgui.views.pages.preconnect import PreConnectionAssistant
from dzgui.views.pages.servers import ServerNotebook
from dzgui.views.pages.thanks import Thanks

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GLibUnix", "2.0")
from gi.repository import Gtk, GLib, GLibUnix, Gdk  # type: ignore # noqa E402

if TYPE_CHECKING:
    from dzgui.config.userprefs import UserPrefs

logger = logging.getLogger(APP_NAME)

# TODO: drop
# https://bugzilla.gnome.org/show_bug.cgi?id=708676
warnings.filterwarnings("ignore", ".*g_value_get_int", Warning)


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

        MainController.open_page(NotebookPage.SERVERS)
        MainController.set_start_tab()
        self.grid.hide_widgets_on_init()

        # TODO: POC, trigger page change here
        MainController.loaded = True
        MainController.populate_model(MainController.get_active_treeview())

    def _on_delete_event(self, window: "OuterWindow", event: Gdk.EventKey) -> None:
        self.halt_proc_and_quit()

    def halt_proc_and_quit(self) -> None:
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

        MainController.register_widget("notebook", self)

        self.help = Help(MainController)
        self.clog = Changelog(MainController)

        self.keys = Keybindings(MainController)
        self.settings = Options(MainController)

        self.servers = ServerNotebook(MainController)
        self.mods = Mods(MainController)

        self.thanks = Thanks(MainController)
        self.log = Log(MainController)
        self.developers = Developers(MainController)

        self.connection = PreConnectionAssistant(MainController)

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
            self.connection: NotebookPage.CONNECTION,
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

    def _on_keypress(self, widget: Gtk.Widget, event: Gdk.EventKey) -> bool:
        match event.keyval:
            case Gdk.KEY_Right | Gdk.KEY_l:
                if is_ctrl_mask(event):
                    return False
                MainController.get_emitter().emit("request_button_box_focus")
                return True
            case Gdk.KEY_question:
                self.toggle_keybindings()
                return True
            case _:
                return False

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
        self.set_page_by_enum(self.prior_page)

    def get_prior_page(self) -> NotebookPage:
        return self.prior_page

    def get_page_by_enum(self) -> NotebookPage:
        for k, v in self.indexes.items():
            if v == self.get_current_page():
                return k
        raise ValueError("No notebook pages set")

    def toggle_keybindings(self) -> None:
        cur_page = self.get_page_by_enum()
        if cur_page == NotebookPage.KEYS:
            self.return_prior()
        else:
            self.set_page_by_enum(NotebookPage.KEYS)

    def focus_current(self) -> None:
        widget = self.get_page()
        if widget is None:
            return

        if hasattr(widget, "grab_content_area"):
            widget.grab_content_area()

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
        pass


class Grid(Gtk.Grid):
    def __init__(self) -> None:
        super().__init__(column_homogeneous=True)

        MAX_ROWS = 3
        MAX_COLS = 3
        SINGLE_ROW = 1
        SINGLE_COL = 1

        MainController.register_widget("grid", self)

        self.emitter = MainController.get_emitter()

        self.notebook = Notebook()
        self.conpan = ConnectPanel(MainController)

        self.statusbar = Statusbar(MainController)
        self.right_panel = RightPanel(MainController)

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

        self.emitter.connect("server_page_toggled", self.toggle_filter_panels)

    # TODO: drop, use map/signal
    def hide_widgets_on_init(self) -> None:
        self.right_panel.sel_panel.hide()

    def toggle_filter_panels(self, emitter: "Emitter", state: bool) -> None:
        self.right_panel.filters_vbox.set_visible(state)
        self.conpan.set_visible(state)
        self.right_panel.refresh_button.set_visible(state)


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

        self._setup_signals()
        Gtk.main()

    def _setup_signals(self) -> None:
        SIGNAL_ADD = "signal_add"
        SIGNAL_ADD_FULL = "signal_add_full"
        try:
            if SIGNAL_ADD in dir(GLibUnix):
                func = GLibUnix.signal_add
            elif SIGNAL_ADD_FULL in dir(GLibUnix):
                func = GLibUnix.signal_add_full
            else:
                func = GLib.unix_signal_add
            func(GLib.PRIORITY_DEFAULT, signal.SIGINT, self._catch_sigint)
        except Exception as e:
            logger.critical(e)

    def _catch_sigint(self) -> Literal[True]:
        MainController.set_exit_event()
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

theme = Gtk.IconTheme.get_default()
icons = theme.list_icons(None)
if STEAM_ICON not in icons:
    logger.warn(strings.steam_icon_missing)
    warnings.warn(strings.steam_icon_missing, stacklevel=2)
