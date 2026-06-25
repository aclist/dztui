import platform
import sys

from ctypes.util import find_library
from warnings import deprecated

LIB = "libgirepository-2.0"


@deprecated("currently unused")
def is_debian() -> bool:
    """
    cf.

    NAME="Debian GNU/Linux"
    ID=debian

    NAME="Ubuntu"
    ID=ubuntu
    ID_LIKE=debian

    NAME="Linux Mint"
    ID=linuxmint
    ID_LIKE="ubuntu debian"

    NAME="Pop!_OS"
    ID=pop
    ID_LIKE="ubuntu debian"
    """
    release = platform.freedesktop_os_release()
    strings = ["ubuntu debian", "debian"]
    try:
        self_id = release["ID"]
        if self_id == "debian":
            return True
        id_like = release["ID_LIKE"]
        return id_like in strings
    except Exception:
        return False


def has_libgi() -> bool:
    return bool(find_library("girepository-2.0"))


def test_libgi_missing() -> None:
    msg = f"System is missing the required library '{LIB}'. Install it via your system package manager."
    if has_libgi() is False:
        print(msg)
        sys.exit(1)
