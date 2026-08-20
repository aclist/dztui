import argparse
import sys
import warnings

from dzgui.const.constants import APP_NAME
from dzgui.init.libgi import test_libgi_missing
from dzgui.init.prefix import get_version
from dzgui.util.map_count import set_map_count
from dzgui.util.strings import flags

from dzgui.views.dialogs.uninstall import UninstallWizard
from dzgui.config.xdg import get_xdg_paths

parser = argparse.ArgumentParser(description=flags.description)
group = parser.add_mutually_exclusive_group()
group.add_argument("-d", "--debug", action="store_true", help=flags.debug)
group.add_argument("-m", "--map", action="store_true", help=flags.map_count)
group.add_argument("-u", "--uninstall", action="store_true", help=flags.uninstall)
group.add_argument("-v", "--version", action="store_true", help=flags.version)
args = parser.parse_args()


def main() -> None:
    # TODO: isolate single flags
    if args.version is True:
        print(get_version())
        sys.exit(0)
    if args.uninstall is True:
        paths = get_xdg_paths()
        UninstallWizard(False, paths)
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
