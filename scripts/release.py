import build
import os
import subprocess
import tarfile

from pathlib import Path
from prebuild import get_pyapp, rebuild_cpython

root = Path(__file__).resolve().parents[1]
dist_dir = root.joinpath("dist")
build_dir = root.joinpath("build")

builder = build.ProjectBuilder(root)
wheel = builder.build("wheel", output_directory=dist_dir)
stem = Path(wheel).stem
tarname = f"{stem}.tar.gz"


metadata = stem.split("-")
appname = metadata[0]
version = metadata[1]

pyapp_dir = build_dir.joinpath("pyapp-latest")
if pyapp_dir.is_dir() is False:
    get_pyapp()

# TODO: rename version and filepath from subscript
packaged_version = rebuild_cpython()
assert packaged_version == version
cpython = build_dir.joinpath("airgapped.tar.gz")

entrypoint = "dzgui.main:main"
env = os.environ
env["PYAPP_PROJECT_VERSION"] = version
env["PYAPP_PROJECT_NAME"] = appname
env["PYAPP_EXEC_SPEC"] = entrypoint
env["PYAPP_PROJECT_PATH"] = wheel
env["PYAPP_PASS_LOCATION"] = "true"

# NOTE: explicitly install all dependencies into distribution
env["PYAPP_SKIP_INSTALL"] = "true"
env["PYAPP_DISTRIBUTION_EMBED"] = "true"
env["PYAPP_FULL_ISOLATION"] = "true"
env["PYAPP_DISTRIBUTION_PATH"] = str(cpython)
env["PYAPP_DISTRIBUTION_PYTHON_PATH"] = "python/bin/python3"

platform = "x86_64-unknown-linux-musl"
build_params = ["cargo", "build", "--release", "--target-dir", str(dist_dir), "--target", platform]

proc = subprocess.run(
    build_params,
    env=env,
    cwd=pyapp_dir,
)

# TODO: set proper release tags on tarfile
if proc.returncode == 0:
    output_exe = dist_dir.joinpath("pyapp")
    release_exe = dist_dir.joinpath(appname)
    output_exe.rename(release_exe)

    tarpath = dist_dir.joinpath(tarname)
    with tarfile.open(tarpath, "w:gz") as tar:
        info = tar.gettarinfo(release_exe)
        info.uname = appname
        info.name = appname
        with open(release_exe, "rb") as f:
            tar.addfile(info, f)
    print(f"Wrote tarfile to '{tarpath}'")

proc = subprocess.run([release_exe, "-v"], capture_output=True, text=True)
assert proc.stdout.rstrip() == version

release_exe.unlink()
Path(wheel).unlink()
