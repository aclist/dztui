from enum import Enum
from typing import Any, Self

from dzgui.util import strings


class Port(Enum):
    DEFAULT = 1
    CUSTOM = 2


class ServerTab(Enum):
    BROWSER = 0
    SAVED = 1
    RECENT = 2
    LAN = 3


class Popup(Enum):
    WAIT = 1
    NOTIFY = 2
    CONFIRM = 3
    ENTRY = 4
    MODLIST = 6
    DETAILS = 7
    QUIT = 8


class VAdjustment(Enum):
    UP = 1
    DOWN = 2
    TOP = 3
    BOTTOM = 4


class CursorPosition(Enum):
    UP = 1
    DOWN = 2
    TOP = 3
    BOTTOM = 4


class FilterMode(Enum):
    INITIAL = 1
    TOGGLE_OFF = 2
    TOGGLE_ON = 3


class EnumWithAttrs(Enum):
    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    def __init__(self, d: dict):
        self.dict = d


class Preferences(EnumWithAttrs):
    STEAM = {
        "key": "steam_api",
    }
    CLIENT = {
        "key": "client",
    }
    WINDOW = {
        "key": "fullscreen",
    }
    DIST = {
        "key": "use_miles",
    }
    NAME = {
        "key": "name",
    }
    DEFAULT = {
        "key": "default_steam_path",
    }
    FAV_LBL = {
        "key": "fav_label",
    }
    FAV_SRV = {
        "key": "fav_server",
    }
    IP_LIST = {
        "key": "ip_list",
    }
    START_TAB = {
        "key": "start_tab",
    }


class NotebookPage(EnumWithAttrs):
    OFFLINE = {"crumbs": strings.crumbs.offline, "statusbar": True}
    CHANGELOG = {"crumbs": strings.crumbs.changelog, "statusbar": True}
    DEVELOPERS = {"crumbs": strings.crumbs.developers, "statusbar": False}
    HELP = {"crumbs": strings.crumbs._help, "statusbar": True}
    KEYS = {"crumbs": strings.crumbs.keys, "statusbar": True}
    LOG = {"crumbs": strings.crumbs.log, "statusbar": True}
    MODS = {"crumbs": strings.crumbs.mods, "statusbar": True}
    OPTIONS = {"crumbs": strings.crumbs.options, "statusbar": False}
    SERVERS = {"crumbs": strings.crumbs.servers, "statusbar": True}
    THANKS = {"crumbs": strings.crumbs.thanks, "statusbar": True}
    CONNECTION = {"crumbs": "Connect", "statusbar": True}


class RowType(EnumWithAttrs):
    # TODO: strings
    CHANGELOG = {
        "label": "View changelog",
        "tooltip": "Opens the DZGUI changelog",
    }
    SHOW_LOG = {
        "label": "Show debug log",
        "tooltip": "Read the DZGUI log generated since startup",
    }
    SEPARATOR = {
        "label": "SEPARATOR",
        "tooltip": "",
    }
    DUMP_LOG = {
        "label": "Output system info to log file",
        "tooltip": "Dump diagnostic data for troubleshooting",
    }
    DOCS = {
        "label": "Documentation/help files (GitHub) ⧉",
        "tooltip": "Open the DZGUI documentation in a browser",
    }
    DOCS_FALLBACK = {
        "label": "Documentation/help files (Codeberg mirror) ⧉",
        "tooltip": "Open the DZGUI documentation in a browser",
    }
    BUGS = {
        "label": "Report a bug (GitHub) ⧉",
        "tooltip": "Open the DZGUI issue tracker in a browser",
    }
    FORUM = {
        "label": "DZGUI Subreddit ⧉",
        "tooltip": "Open the DZGUI discussion forum in a browser",
    }
    SPONSOR = {
        "label": "Sponsor (GitHub) ⧉",
        "tooltip": "Sponsor development of the DZGUI project",
    }
    THANKS = {
        "label": "Special thanks",
        "tooltip": "A list of contributors, testers, and sponsors",
    }


# TODO: rename to ContextMenuItem
class ContextMenu(EnumWithAttrs):
    ADD_NOTE = {"label": strings.add_note}
    ADD_SERVER = {"label": strings.add}
    CONNECT = {"label": strings.connect}
    COPY_LOG_CLIPBOARD = {"label": strings.copy_log}
    COPY_SERVER_IP = {"label": strings.copy_ip}
    COPY_SERVER_NAME = {"label": strings.copy_name}
    UNSUB_MOD = {"label": strings.unsub_mod}
    OPEN_WORKSHOP = {"label": strings.open_workshop}
    REFRESH_PLAYERS = {"label": strings.refresh_players}
    REMOVE_HISTORY = {"label": strings.remove_history}
    REMOVE_SERVER = {"label": strings.remove}
    SET_FAV = {"label": strings.add_fav}
    SHOW_DETAILS = {"label": strings.show_details}
    SHOW_MODS = {"label": strings.show_mods}


class ContextMenuGroup(Enum):
    """
    Groupings of context menu items
    """

    SERVER_MOD = (ContextMenu.OPEN_WORKSHOP,)
    MOD = (ContextMenu.OPEN_WORKSHOP, ContextMenu.UNSUB_MOD)
    MOD_OFFLINE = (None,)
    LOG = (ContextMenu.COPY_LOG_CLIPBOARD,)
    SERVER_BROWSER = (
        ContextMenu.CONNECT,
        ContextMenu.ADD_SERVER,
        ContextMenu.SET_FAV,
        ContextMenu.COPY_SERVER_NAME,
        ContextMenu.COPY_SERVER_IP,
        ContextMenu.ADD_NOTE,
        ContextMenu.SHOW_MODS,
        ContextMenu.SHOW_DETAILS,
        ContextMenu.REFRESH_PLAYERS,
    )
    SCAN_LAN = (
        ContextMenu.CONNECT,
        ContextMenu.SET_FAV,
        ContextMenu.COPY_SERVER_NAME,
        ContextMenu.COPY_SERVER_IP,
        ContextMenu.ADD_NOTE,
        ContextMenu.SHOW_MODS,
        ContextMenu.SHOW_DETAILS,
        ContextMenu.REFRESH_PLAYERS,
    )
    SAVED = (
        ContextMenu.CONNECT,
        ContextMenu.SET_FAV,
        ContextMenu.REMOVE_SERVER,
        ContextMenu.COPY_SERVER_NAME,
        ContextMenu.COPY_SERVER_IP,
        ContextMenu.ADD_NOTE,
        ContextMenu.SHOW_MODS,
        ContextMenu.SHOW_DETAILS,
        ContextMenu.REFRESH_PLAYERS,
    )
    RECENT = (
        ContextMenu.CONNECT,
        ContextMenu.ADD_SERVER,
        ContextMenu.SET_FAV,
        ContextMenu.REMOVE_HISTORY,
        ContextMenu.COPY_SERVER_NAME,
        ContextMenu.COPY_SERVER_IP,
        ContextMenu.ADD_NOTE,
        ContextMenu.SHOW_MODS,
        ContextMenu.SHOW_DETAILS,
        ContextMenu.REFRESH_PLAYERS,
    )


class ModButton(EnumWithAttrs):
    SELECT_ALL = {
        "label": strings.mod_panel.select_all,
        "tooltip": strings.mod_panel.select_all_tooltip,
    }
    UNSELECT_ALL = {
        "label": strings.mod_panel.unselect_all,
        "tooltip": strings.mod_panel.unselect_all_tooltip,
    }
    HIGHLIGHT_STALE = {
        "label": strings.mod_panel.highlight_stale,
        "tooltip": strings.mod_panel.highlight_stale_tooltip,
    }
    UNHIGHLIGHT_STALE = {
        "label": strings.mod_panel.unhighlight_stale,
        "tooltip": strings.mod_panel.unhighlight_stale_tooltip,
    }
    UNSUB_SELECTED = {
        "label": strings.mod_panel.unsub_selected,
        "tooltip": strings.mod_panel.unsub_selected_tooltip,
    }
    SELECT_STALE = {
        "label": strings.mod_panel.select_stale,
        "tooltip": strings.mod_panel.select_stale_tooltip,
    }


class ButtonType(EnumWithAttrs):
    SERVERS = {
        "label": strings.buttons.servers_label,
        "tooltip": strings.buttons.servers_tooltip,
        "opens": NotebookPage.SERVERS,
    }
    MODS = {
        "label": strings.buttons.mods_label,
        "tooltip": strings.buttons.mods_tooltip,
        "opens": NotebookPage.MODS,
    }
    OPTIONS = {
        "label": strings.buttons.options_label,
        "tooltip": strings.buttons.options_tooltip,
        "opens": NotebookPage.OPTIONS,
    }
    HELP = {
        "label": strings.buttons.help_label,
        "tooltip": strings.buttons.help_tooltip,
        "opens": NotebookPage.HELP,
    }
    EXIT = {
        "label": strings.buttons.exit_label,
        "tooltip": strings.buttons.exit_tooltip,
        "opens": None,
    }


HELP_MENU_ROWS = (
    RowType.CHANGELOG,
    RowType.SHOW_LOG,
    RowType.DUMP_LOG,
    RowType.SEPARATOR,
    RowType.DOCS,
    RowType.DOCS_FALLBACK,
    RowType.BUGS,
    RowType.FORUM,
    RowType.SPONSOR,
    RowType.SEPARATOR,
    RowType.THANKS,
)
