import gzip
import logging
import re
import requests
import shutil
import socket
import sqlite3
import time

from pathlib import Path

from dzgui.const.constants import APP_NAME, REQUEST_TIMEOUT
from dzgui.const.endpoints import DB_IP

logger = logging.getLogger(APP_NAME)


def find_download_url(url: str) -> str | None:
    res = requests.get(url, timeout=REQUEST_TIMEOUT)
    res.raise_for_status()
    reg = r'ref=[\'"]([^\'">]+.csv.gz)'
    urls = re.findall(reg, res.text)
    if len(urls) < 1:
        return None
    return str(urls[0])


def get_ipdb(db_path: Path) -> None:
    try:
        url = find_download_url(DB_IP)
        if url is None:
            return

        ips_path = db_path.with_suffix(".csv")
        month_file = db_path.parent / ".month"
        date = find_date(url)
        if db_path.exists() and month_file.exists():
            old_date = month_file.read_text().rstrip("\n")
            if old_date == date:
                logger.info(f"IP DB date matches: {date}")
                return

        # TODO: log additional output
        logger.info(f"Fetching IPDB for {date} from {url}")
        tmp = serialize(url)
        logger.info(f"Extracting {tmp}")
        unzip(tmp, ips_path)

        logger.info("Stripping IPv6 records")
        strip_ipv6(ips_path)

        create_table(db_path, ips_path)
        ips_path.unlink()

        with open(month_file, "w") as f:
            f.write(date)
        logger.info(f"Wrote {date} to {month_file}")
    except Exception as e:
        # NOTE: in the event of failure, geolocation calc is simply not performed
        logger.critical(e)
        return


def find_date(url: str) -> str:
    date = re.sub(r"(dbip-city-lite-)(.*)(.csv.gz)", r"\2", url)
    date = date.split("/")[-1]
    return date


def unzip(tmp: Path, ips_path: Path) -> None:
    with gzip.open(tmp, "rb") as f:
        with open(ips_path, "wb") as outfile:
            shutil.copyfileobj(f, outfile)
    tmp.unlink()


def serialize(url: str) -> Path:
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        filename = "ips.csv.gz"
        tmp = Path("/tmp") / filename
        with open(tmp, "wb") as f:
            shutil.copyfileobj(r.raw, f)
    return tmp


def strip_ipv6(path: Path) -> None:
    """Can be IO intensive and cause visual lag on UI frames
    running in the main thread even when run in its own thread;
    lines are batched into memory-manageable chunks to reduce
    disk writes. Raw file can be 8M+ records long, so it is
    not read into memory at once.

    Relative size is reduced by ~100MB by pruning unwanted columns
    """
    # NOTE: "^::," is the boundary line between IPv4 and IPv6
    # NOTE: deprecated regex matching (slower by 5s)
    # reg = r"^\d{1,3}\..*"
    alt_path = path.parent.joinpath("ips_stripped.csv")
    merged = ""
    its = 0
    with open(path, "r") as f, open(alt_path, "w") as out:
        for line in f:
            els = line.split(",")
            if "." not in els[0]:
                break
            final = ",".join([els[0], els[1], els[-2], els[-1]])
            merged += final
            its += 1
            if its == 500:
                out.write(merged)
                its = 0
                merged = ""
        if its > 0:
            out.write(merged)
    path.unlink()
    alt_path.rename(path)


def ip_to_int(ip: str) -> int:
    return int.from_bytes(socket.inet_aton(ip), "big")


def marshal_rows(ip_file: Path) -> list[tuple[int, int, str, str]]:
    YIELD = 0.003
    SLEEP = 0.001
    with open(ip_file, "r") as f:
        rows: list[tuple[int, int, str, str]] = []
        # NOTE: yield to GIL periodically to reduce load on spinner
        last_yield = time.monotonic()
        for row in f:
            start, end, lat, lon = row.rstrip("\n").split(",")
            int_start = ip_to_int(start)
            int_end = ip_to_int(end)
            rows.append((int_start, int_end, lat, lon))

            now = time.monotonic()
            if (now - last_yield) >= YIELD:
                time.sleep(SLEEP)
                last_yield = time.monotonic()
    return rows


def create_table(db_file: Path, ip_file: Path) -> None:
    create = """
    CREATE TABLE IF NOT EXISTS ips (
    start_range INTEGER PRIMARY KEY,
    end_range INTEGER,
    latitude REAL,
    longitude REAL
    ) WITHOUT ROWID;
    """
    insert = """
        INSERT INTO ips
        (start_range, end_range, latitude, longitude)
        values(?, ?, ?, ?)
    """

    if db_file.exists():
        db_file.unlink()

    conn = sqlite3.connect(":memory:")
    c = conn.cursor()

    try:
        c.execute(create)
        rows = marshal_rows(ip_file)
        c.executemany(insert, rows)
        logger.info(f"Inserted {len(rows)} IP records into database")
        conn.commit()
        with sqlite3.connect(db_file) as dest:
            conn.backup(dest)
        logger.info(f"Serialized IP records to database: '{db_file}'")
        conn.close()
    except Exception as e:
        logger.critical(e)


def read_from_table(db_path: Path, ip: str) -> tuple[float, float]:
    if not db_path.exists():
        raise FileNotFoundError(f"No file found at the location '{db_path}")

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    int_ip = ip_to_int(ip)

    query = """
    SELECT end_range, latitude, longitude
    FROM ips
    WHERE start_range <= ?
    ORDER BY start_range DESC
    LIMIT 1
    """
    index = """
    CREATE INDEX IF NOT EXISTS start_index
    ON ips(start_range);
    """
    try:
        c.execute(index)
        conn.commit()
        c.execute(query, (int_ip,))
        row = c.fetchone()
        end, lat, lon = row
        conn.close()
        return lat, lon
    except Exception as e:
        logger.critical(e)
        raise e
