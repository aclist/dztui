import logging
import re

from collections.abc import Iterator
from pathlib import Path
from typing import Any
from warnings import deprecated

from dzgui.const.constants import APP_NAME

logger = logging.getLogger(APP_NAME)


class ACF:
    def __init__(self, file: Path) -> None:
        super().__init__()

        self.dict: dict[str, Any]
        self.load(file)

    def as_dict(self) -> dict[str, Any]:
        return self.dict

    def load(self, file: Path) -> None:
        delimiter = r"\t\t"
        lines = []
        # TODO: illegal file handling
        with open(file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                els = re.split(delimiter, line, maxsplit=1)
                lines.append(els)
        self.dict = self.parse(iter(lines))

    @classmethod
    def enquote(cls, s: str) -> str:
        return f'"{s}"'

    @classmethod
    def dequote(cls, s: str) -> str:
        return s.rstrip('"').lstrip('"')

    def parse(self, lines: Iterator[list[str]]) -> dict[str, str]:
        acf: dict[str, Any] = {}
        try:
            while True:
                line = next(lines)
                if len(line) == 1:
                    key = line[0]
                    if key == "{":
                        continue
                        return acf
                    elif key == "}":
                        return acf
                    else:
                        key = self.dequote(key)
                        acf[key] = self.parse(lines)
                elif len(line) == 2:
                    k, v = line
                    k = self.dequote(k)
                    v = self.dequote(v)
                    try:
                        n = list(acf.keys())[-1]
                        acf[n][k] = v
                    except Exception:
                        acf[k] = v
        except StopIteration:
            return acf

    def get_allows_downloads(self) -> int | None:
        try:
            # TODO: consider coercing strs to ints on initial import
            flag = int(self.dict["AppState"]["AllowOtherDownloadsWhileRunning"])
            return flag
        except Exception as e:
            logger.critical(e)
            return None


@deprecated(
    "Serializing workshop files is no longer supported, use dzgui.api.steam.unsubscribe"
)
class WorkshopACF(ACF):
    def __init__(self, file: Path) -> None:
        super().__init__(file)

    def unpack(self, d: dict, lines: list[Any] = []) -> str:
        t1 = "AppWorkshop"
        t2 = ("WorkshopItemsInstalled", "WorkshopItemDetails")
        for k, v in d.items():
            if type(v) is dict:
                if k in t1:
                    self.indent = 0
                elif k in t2:
                    self.indent = 1
                else:
                    self.indent = 2
                pref = "\t" * self.indent
                lines.append(pref + self.enquote(k))
                lines.append(pref + "{")
                self.unpack(v, lines)
                lines.append(pref + "}")
            else:
                pref = "\t" * (self.indent + 1)
                lines.append(pref + self.enquote(k) + "\t\t" + self.enquote(v))
        s = ""
        for line in lines:
            s += line + "\n"
        return s

    def to_file(self, file: Path) -> None:
        s = self.unpack(self.dict)
        file.write_text(s)

    def delete(self, modid: int) -> None:
        del self.dict["AppWorkshop"]["WorkshopItemsInstalled"][modid]
        del self.dict["AppWorkshop"]["WorkshopItemDetails"][modid]
