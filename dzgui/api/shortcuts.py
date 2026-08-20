import binascii
import ctypes
import logging
import shutil
import vdf  # type: ignore

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

from dzgui.api.steam import find_user_id_32
from dzgui.const.constants import APP_NAME, APP_NAME_LOWER, IMAGES_PATH
from dzgui.util.dirs import copy_dzgui_to_xdg_data
from dzgui.util.strings import unknown

logger = logging.getLogger(APP_NAME)


@dataclass(slots=True, frozen=True)
class ShortcutMetadata:
    appname: str
    appid: int
    exe_path: str
    start_dir: str
    icon: str


class Shortcuts:
    def __init__(self, steam_path: Path) -> None:
        self.user_config_path: Path
        self.shortcuts_path = self.find_shortcuts_path(steam_path)
        self._load_shortcuts(self.shortcuts_path)

    @classmethod
    def gen_bpid(cls, uid: str) -> int:
        u = uid.encode()
        encoded = binascii.crc32(u)
        return encoded | 0x80000000

    @classmethod
    def gen_signed_appid(cls, appid: int) -> int:
        return ctypes.c_int(appid).value

    @classmethod
    def gen_exe_uid(cls, appname: str, exe: Path) -> str:
        wrapped_exe = f'"{exe}"'
        return appname + wrapped_exe

    def find_appname_by_unsigned_id(self, appid: int) -> str:
        # NOTE: bitmask signed int back to 32-bit CRC
        # varying client versions treat case sensitivity differently
        try:
            for key in self.shortcuts["shortcuts"].keys():
                if self.shortcuts["shortcuts"][key]["appid"] & 0xFFFFFFFF == appid:
                    try:
                        return str(self.shortcuts["shortcuts"][key]["appname"])
                    except Exception as e:
                        logger.debug(e)
                    try:
                        return str(self.shortcuts["shortcuts"][key]["AppName"])
                    except Exception as e:
                        logger.debug(e)
                    return unknown
        except Exception as e:
            logger.debug(e)
        return unknown

    def get_shortcuts(self) -> Any:
        return self.shortcuts

    def _load_shortcuts(self, path: Path) -> None:
        try:
            with open(path, "rb") as f:
                shortcuts = vdf.binary_load(f)
            self.shortcuts = shortcuts
            logger.debug("Loaded shortcuts file")
        except Exception as e:
            logger.critical(e)
            raise e

    def find_shortcuts_path(self, steam_path: Path) -> Path:
        uid = find_user_id_32(steam_path)
        self.user_config_path = steam_path.joinpath(f"userdata/{uid}/config")
        return self.user_config_path.joinpath("shortcuts.vdf")

    def add_shortcut(
        self, appname: str, start_dir: Path, exe_path: Path, icon: Path
    ) -> None:
        uid = self.gen_exe_uid(appname, exe_path)
        self.bpid = self.gen_bpid(uid)
        self.signed_appid = self.gen_signed_appid(self.bpid)

        meta = ShortcutMetadata(
            appname, self.signed_appid, str(exe_path), str(start_dir), str(icon)
        )
        entry = self._create_entry(meta)
        self._insert_at_last_index(entry)

    def add_grid_images(self, images: Path) -> None:
        """
        {BPID}_hero.png: hero (splash)
        {BPID}p.ping: portrait boxart in library
        {BPID}_logo.png: logo overlay on top of hero
        {BPID}.png: legacy Big Picture/landscape image
        """

        grid_path = self.user_config_path.joinpath("grid")
        for img in ("_hero", "p", "_logo"):
            filename = str(self.bpid) + img
            dest = grid_path.joinpath(filename).with_suffix(".png")
            b = images.joinpath(img).with_suffix(".png").read_bytes()
            dest.write_bytes(b)

        # NOTE: legacy Big Picture header
        b = images.joinpath("_hero.png").read_bytes()
        dest = grid_path.joinpath(str(self.bpid)).with_suffix(".png")
        dest.write_bytes(b)

    def _insert_at_last_index(self, entry: dict[str, Any]) -> None:
        try:
            last = list(self.shortcuts["shortcuts"].keys())[-1]
            n = int(last) + 1
        except Exception:
            n = 0
        self.shortcuts["shortcuts"][str(n)] = entry

    @classmethod
    def _create_entry(cls, meta: ShortcutMetadata) -> dict[str, Any]:
        """
        https://developer.valvesoftware.com/wiki/Add_Non-Steam_Game
        https://developer.valvesoftware.com/wiki/Steam_Library_Shortcuts

        Key case is not internally consistent and varies between client versions
        Most keys use Pascal case, but some do not

        appid: signed int CRC
        Exe: absolute path to the executable, must be wrapped in literal quotes
        StartDir: directory the executable starts in, generally the parent
        """

        NEW_ENTRY: dict[str, Any] = {}
        NEW_ENTRY["appid"] = meta.appid
        NEW_ENTRY["AppName"] = meta.appname
        NEW_ENTRY["Exe"] = f'"{meta.exe_path}"'
        NEW_ENTRY["StartDir"] = f"{meta.start_dir}"
        NEW_ENTRY["icon"] = meta.icon
        NEW_ENTRY["ShortcutPath"] = ""
        NEW_ENTRY["LaunchOptions"] = ""
        NEW_ENTRY["IsHidden"] = 0
        NEW_ENTRY["AllowDesktopConfig"] = 1
        NEW_ENTRY["AllowOverlay"] = 1
        NEW_ENTRY["OpenVR"] = 0
        NEW_ENTRY["Devkit"] = 0
        NEW_ENTRY["DevkitGameID"] = ""
        NEW_ENTRY["DevkitOverrideAppID"] = 0
        NEW_ENTRY["LastPlayTime"] = 0
        NEW_ENTRY["FlatpakAppID"] = ""
        NEW_ENTRY["sortas"] = ""
        NEW_ENTRY["tags"] = {}
        return NEW_ENTRY

    def delete_shortcut(self, start_path: Path) -> None:
        shortcuts = self.shortcuts["shortcuts"]
        for s in shortcuts:
            if shortcuts[s]["StartDir"] == str(start_path):
                del shortcuts[s]
                break
        self.save_shortcuts()

    def save_shortcuts(self) -> None:
        try:
            backup = self.shortcuts_path.with_suffix(".vdf.bak")
            shutil.copy(self.shortcuts_path, backup)
            with open(self.shortcuts_path, "wb") as f:
                vdf.binary_dump(self.shortcuts, f)
        except Exception as e:
            logger.critical(e)


def add_steam_shortcut(steam_path: Path, exe_path: Path) -> None:
    try:
        start_dir = exe_path.parent

        traversable = resources.files(APP_NAME_LOWER).joinpath(IMAGES_PATH)
        images = Path(str(traversable))
        icon = images.joinpath("icon.png")

        shortcuts = Shortcuts(Path(steam_path))
        shortcuts.add_shortcut(APP_NAME, start_dir, exe_path, icon)
        shortcuts.save_shortcuts()
        shortcuts.add_grid_images(images)

        copy_dzgui_to_xdg_data(exe_path)
        logger.debug("Finished creating Steam shortcut")
    except Exception as e:
        logger.critical(e)
