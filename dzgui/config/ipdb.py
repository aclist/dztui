import gzip
import logging
import re
import requests
import shutil

from pathlib import Path

from dzgui.const.constants import REQUEST_TIMEOUT
from dzgui.const.endpoints import DB_IP

logger = logging.getLogger(__name__)

def find_download_url(url: str) -> str | None:
    res = requests.get(url, timeout=REQUEST_TIMEOUT)
    res.raise_for_status()
    reg = r'ref=[\'"]([^\'">]+.csv.gz)'
    urls = re.findall(reg, res.text)
    if len(urls) < 1:
        return None
    return str(urls[0])

def get_ipdb(ips_path: Path) -> None:
    url = find_download_url(DB_IP)
    if url is None:
        return

    date = find_date(url)
    month_file = ips_path.parent / ".month"
    if month_file.exists() is True:
        old_date = month_file.read_text().rstrip("\n")
        if old_date == date:
            logger.info(f"IP DB date matches: {date}")
            return

    # TODO: log additional output
    logger.info(f"Fetching IPDB for {date} from {url}")
    try:
        tmp = serialize(url)
    except Exception as e:
        logger.critical(e)
        return

    logger.info(f"Extracting {tmp}")
    unzip(tmp, ips_path)

    logger.info("Stripping IPv6 records")
    try:
        strip_ipv6(ips_path)
    except Exception as e:
        logger.critical(e)
        return

    with open(month_file, "w") as f:
        f.write(date)
    logger.info(f"Wrote {date} to {month_file}")


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


# TODO: optimize this function
# consider using grep
# cf. grep -vE "^[a-z0-9]{4}:" | grep -v "::" > "$ip_file"
def strip_ipv6(path: Path) -> None:
    ips = []
    with open(path, "r") as f:
        s = f.read()

    reg = r"^\d{1,3}\..*"
    ips = re.findall(reg, s, re.MULTILINE)
    assert ips[0].split(",")[0] == "0.0.0.0"
    assert ips[-1].split(",")[0] == "224.0.0.0"

    with open(path, "w") as f:
        for ip in ips:
            f.write(ip + "\n")
