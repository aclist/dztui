import argparse
import sys
import warnings

from dzgui.const.constants import APP_NAME
from dzgui.init.libgi import test_libgi_missing
from dzgui.init.prefix import get_version
from dzgui.util.map_count import set_map_count
from dzgui.util.strings import flags

parser = argparse.ArgumentParser(description=flags.description)
parser.add_argument("-d", "--debug", action="store_true", help=flags.debug)
parser.add_argument("-m", "--map", action="store_true", help=flags.map_count)
parser.add_argument("-u", "--uninstall", action="store_true", help=flags.uninstall)
parser.add_argument("-v", "--version", action="store_true", help=flags.version)
args = parser.parse_args()


def uninstall() -> None:
    # TODO: uninstall data files (-u)
    # -u removes state, log, freedesktop
    # XDG_SHARE_HOME/dzgui
    # XDG_STATE_HOME/dzgui
    # XDG_DATA_HOME/dzgui
    pass


def main() -> None:
    # TODO: isolate single flags
    if args.version is True:
        print(get_version())
        sys.exit(0)
    if args.uninstall is True:
        uninstall()
        sys.exit(0)
    if args.debug is True:
        warnings.filterwarnings("default", category=DeprecationWarning)
    if args.map is True:
        set_map_count()
        sys.exit(0)

    version = get_version()

    print(f"{APP_NAME} {version}")
    test_libgi_missing()

    # NOTE: only import ligbirepository modules after the above check
    from dzgui.app_init import load_gui

    load_gui(version, args.debug)
