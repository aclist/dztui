import gzip
import logging
import re
import requests
import shutil

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


def get_ipdb(ips_path: Path) -> None:
    try:
        url = find_download_url(DB_IP)
        if url is None:
            return

        date = find_date(url)
        month_file = ips_path.parent / ".month"
        if ips_path.exists() and month_file.exists():
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

        print("here")
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
    alt_path = path.parent.joinpath("stripped.csv")
    with open(path, "r") as f, open(alt_path, "w") as out:
        for line in f:
            reg = r"^\d{1,3}\..*"
            m = re.match(reg, line)
            if not m:
                continue
            els = line.split(",")
            final = ",".join([els[0], els[1], els[6], els[7]])
            out.write(final)
    path.unlink()
    alt_path.rename(path.name)
