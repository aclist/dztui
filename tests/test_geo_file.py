import os
import sqlite3
import pytest
import tempfile

from pathlib import Path

from dzgui.const.endpoints import DB_IP
from dzgui.config.ipdb import (
    create_table,
    find_download_url,
    serialize,
    strip_ipv6,
    unzip,
)


def get_db_len(path: Path) -> int:
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) from ips")
    db_len = c.fetchone()[0]
    return db_len


@pytest.fixture
def csv() -> Path:
    csv = Path(tempfile.NamedTemporaryFile().name)
    url = find_download_url(DB_IP)
    tmp = serialize(url)
    unzip(tmp, csv)
    strip_ipv6(csv)
    return csv

@pytest.mark.slow
def test_stripping(csv):
    with open(csv, "rb") as f:
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


@pytest.mark.slow
def test_row_parity(csv) -> None:
    rows = csv.read_text().splitlines()

    db = Path(tempfile.NamedTemporaryFile().name)
    create_table(db, csv)

    csv_len = len(rows)
    db_len = get_db_len(db)

    assert csv_len == db_len
