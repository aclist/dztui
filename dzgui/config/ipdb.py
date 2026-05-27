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
    """Can be IO intensive and cause visual lag on UI frames
    running in the main thread even when run in its own thread;
    lines are batched into memory-manageable chunks to reduce
    disk writes. Raw file can be 8M+ records long, so it is
    not read into memory at once.

    Relative size is reduced by ~100MB by pruning unwanted columns
    """
    # NOTE: "^::," is the boundary line between IPv4 and IPv6
    # NOTE: deprecated regex matching (slower by 5s)
    #reg = r"^\d{1,3}\..*"
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
    alt_path.rename(path.name)
