import build
import os
import subprocess
import sys
import tarfile

from pathlib import Path

from concat_licenses import concat_license
from parse_toml import get_entrypoint
from prebuild import get_pyapp, rebuild_cpython


def update_uname(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uname = "dzgui"
    info.gname = "users"
    return info


root = Path(__file__).resolve().parents[1]
dist_dir = root.joinpath("dist")
build_dir = root.joinpath("build")

builder = build.ProjectBuilder(root)
wheel = builder.build("wheel", output_directory=dist_dir)
stem = Path(wheel).stem

metadata = stem.split("-")
appname = metadata[0]
version = metadata[1]

pyapp_dir = build_dir.joinpath("pyapp-latest")
if pyapp_dir.is_dir() is False:
    get_pyapp()

# TODO: get resulting filename from this function
packaged_version = rebuild_cpython()
assert packaged_version == version
cpython = build_dir.joinpath("airgapped.tar.gz")

entrypoint = get_entrypoint()
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
build_name = f"{appname}-{version}-{platform}"
tarname = f"{build_name}.tar.gz"
tarpath = dist_dir.joinpath(tarname)

build_params = [
    "cargo",
    "build",
    "--release",
    "--target",
    platform,
]

proc = subprocess.run(
    build_params,
    env=env,
    cwd=pyapp_dir,
)

if proc.returncode != 0:
    sys.exit(1)

subfolder = dist_dir.joinpath(build_name)
subfolder.mkdir(parents=True)

output_exe = pyapp_dir.joinpath(f"target/{platform}/release/pyapp")
release_exe = subfolder.joinpath(appname)
output_exe.rename(release_exe)

combined_licenses = concat_license()
license_file = subfolder.joinpath("LICENSE")
license_file.write_text(combined_licenses)

with tarfile.open(tarpath, "w:gz") as tar:
    info = tar.gettarinfo(subfolder)
    tar.add(subfolder, arcname=appname, filter=update_uname)
    print(f"Wrote tarfile to '{tarpath}'")

proc = subprocess.run([release_exe, "-v"], capture_output=True, text=True)
assert proc.stdout.rstrip() == version

# TODO: clean up staging directory
release_exe.unlink()
license_file.unlink()
subfolder.rmdir()
Path(wheel).unlink()
