import os
import subprocess

from dzgui.const.constants import APPID_DAYZ
from dzgui.const.enum import RowType
from dzgui.const import endpoints
from dzgui.util.bash import concat_bash_args

links = {
    RowType.DOCS: endpoints.GITHUB_PAGES,
    RowType.DOCS_FALLBACK: endpoints.CODEBERG_PAGES,
    RowType.BUGS: endpoints.GITHUB_ISSUES,
    RowType.FORUM: endpoints.FORUM,
    RowType.SPONSOR: endpoints.SPONSORS,
    RowType.CHNG_STEAM_API: endpoints.STEAM_API_SETUP,
    RowType.CHNG_BM_API: endpoints.BM_API_SETUP,
    RowType.CONN_BY_ID: endpoints.BM_BROWSE,
    RowType.ADD_BY_ID: endpoints.BM_BROWSE,
}


def get_browser() -> str:
    if (browser := os.getenv("BROWSER")) is not None:
        command = browser
    else:
        command = "xdg-open"
    return command


def open_user_workshop(uid: str, client: str) -> None:
    base = f"https://steamcommunity.com/profiles/{uid}/myworkshopfiles/?appid={APPID_DAYZ}&browsefilter=mysubscriptions"
    uri = endpoints.OPEN_URL + base
    args = concat_bash_args(client)
    args.append(uri)
    subprocess.Popen([*args])


def open_link_by_url(url: str) -> None:
    command = get_browser()
    args = concat_bash_args(command)
    args.append(url)
    subprocess.Popen([*args])


def open_link_by_rowtype(enum: RowType) -> None:
    command = get_browser()
    args = concat_bash_args(command)
    try:
        url = links[enum]
    except KeyError:
        return
    args.append(url)
    subprocess.Popen([*args])


def open_workshop_page(uid: str, client: str) -> None:
    uri = endpoints.WORKSHOP + uid
    args = concat_bash_args(client)
    args.append(uri)
    subprocess.Popen([*args])
