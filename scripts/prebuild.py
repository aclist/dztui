import os
import requests
import subprocess
import tarfile

from pathlib import Path
from urllib.parse import unquote

BUILD = "3.13.9"
DATE = "20251014"
CPYTHON_BUILD = f"cpython-{BUILD}"

root = Path(__file__).resolve().parents[1]
build_dir = root.joinpath("build")
cpython_dir = build_dir.joinpath(CPYTHON_BUILD)


def fetch(url: str, destination: str) -> None:
    print(f"Fetching URL '{url}'")
    res = requests.get(url)
    code = res.status_code
    if code != 200:
        raise Exception(f"URL '{url}' returned status code {code}")
    with open(build_dir.joinpath(destination), "wb") as f:
        f.write(res.content)


def get_cpython() -> None:
    source = f"https://github.com/astral-sh/python-build-standalone/releases/download/{DATE}/"
    build = f"{CPYTHON_BUILD}%2B{DATE}-x86_64_v3-unknown-linux-gnu-install_only_stripped.tar.gz"
    url = f"{source}{build}"
    outfile = unquote(build)
    fetch(url, outfile)
    version = build.split("%")[0]
    untar(outfile, "python", version)


def get_pyapp() -> None:
    url = "https://github.com/ofek/pyapp/releases/latest/download/source.tar.gz"
    outfile = "pyapp-latest.tar.gz"
    fetch(url, outfile)
    untar(outfile, "pyapp-*", "pyapp-latest")


def untar(file: str, glob: str, renamed: str) -> None:
    full_path = build_dir.joinpath(file)
    with tarfile.open(full_path, "r:gz") as tar:
        tar.extractall(path=build_dir)
    full_path.unlink()
    for _dir in build_dir.glob(glob):
        os.rename(_dir, build_dir.joinpath(renamed))


def install_deps() -> None:
    pip = build_dir.joinpath(f"{CPYTHON_BUILD}/bin/pip")
    subprocess.run([pip, "install", root])


def repackage() -> None:
    print("Preparing tar archive...")
    outfile = build_dir.joinpath("airgapped.tar.gz")
    with tarfile.open(outfile, "w:gz") as tar:
        tar.add(build_dir.joinpath(CPYTHON_BUILD), arcname="python")


def rebuild_cpython() -> None:
    if cpython_dir.is_dir() is False:
        get_cpython()
    install_deps()
    repackage()
    return get_packaged_version()


def get_packaged_version() -> str:
    proc = subprocess.run(
        [cpython_dir.joinpath("bin/dzgui"), "-v"],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.rstrip()
