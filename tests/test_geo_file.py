from dzgui.config.ipdb import get_ipdb
from pathlib import Path
import os
import pytest
import tempfile


@pytest.mark.slow
def test_stripping():
    d = tempfile.TemporaryDirectory()
    path = Path(d.name).joinpath("ips.csv")
    get_ipdb(path)
    with open(path, "rb") as f:
        first = f.readline().decode().rstrip()
        try:
            f.seek(-2, os.SEEK_END)
            while f.read(1) != b"\n":
                f.seek(-2, os.SEEK_CUR)
        except OSError:
            f.seek(0)
        last = f.read().decode().rstrip()

        first_els = first.split(",")
        last_els = last.split(",")

        assert first_els[0] == "0.0.0.0"
        assert last_els[0] == "224.0.0.0"
