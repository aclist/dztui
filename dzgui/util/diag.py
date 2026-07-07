import logging
import os
import platform

from datetime import datetime
from pathlib import Path

from dzgui.api.mods import get_local_mod_ids, get_local_mod_path
from dzgui.const.constants import APP_NAME
from dzgui.const.enum import Preferences
from dzgui.config.query import lookup
from dzgui.init.prefix import get_version
from dzgui.util.redact import redact_home

logger = logging.getLogger(APP_NAME)


def get_cpu_model() -> str:
    cpuinfo = Path("/proc/cpuinfo")
    text = cpuinfo.read_text()
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("model name"):
            model = line.split(": ")[1]
            return model
    return ""


def print_servers(servers: list[str]) -> str:
    s = ""
    for server in servers:
        s += server + "\n"
    return s


def print_mods(mods: list[int]) -> str:
    s = ""
    for mod in mods:
        s += str(mod) + "\n"
    return s


def write_diagnostic(config: Path, outfile: Path) -> None:
    # TODO: test availability on other distros
    date = datetime.now().isoformat()

    try:
        distro = platform.freedesktop_os_release()["ID_LIKE"]
    except Exception as e:
        logger.warn(e)
        distro = "Unknown"

    kernel = os.uname().release
    cpu = get_cpu_model()
    version = get_version()

    debug = lookup(config, Preferences.DEBUG)
    install = lookup(config, Preferences.INSTALL)
    default = lookup(config, Preferences.DEFAULT)

    steam_path = Path(default)
    workshop_path = get_local_mod_path(steam_path)

    steam_redacted = redact_home(default)
    workshop_redacted = redact_home(str(workshop_path))

    mods = get_local_mod_ids(steam_path)
    mods_pretty = print_mods(mods)

    servers = lookup(config, Preferences.IP_LIST)
    servers_pretty = print_servers(servers)

    # FIXME: extraneous newlines in lists of mods
    template = f"""\
    {APP_NAME} version {version}
    Date: {date}
    ===============================
    Distribution: {distro}
    Kernel: {kernel}
    CPU: {cpu}

    Debug: {debug}
    Auto-install: {install}
    Steam path: {steam_redacted}
    Workshop path: {workshop_redacted}

    Mods:
    {mods_pretty}
    Servers:
    {servers_pretty}
    """

    output = "\n".join([line.lstrip() for line in template.split("\n")])
    outfile.write_text(output)
