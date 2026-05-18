import build
import os
import subprocess
import tarfile

from pathlib import Path

root = Path(__file__).resolve().parents[1]
output = root.joinpath("dist")

pyapp_dir = root.joinpath("pyapp-latest")

builder = build.ProjectBuilder(root)
wheel = builder.build("wheel", output_directory=output)
stem = Path(wheel).stem
tarname = f"{stem}.tar.gz"

metadata = stem.split("-")
appname = metadata[0]
version = metadata[1]

entrypoint = "dzgui.main:main"

env = os.environ
env["PYAPP_PROJECT_VERSION"] = version
env["PYAPP_PROJECT_NAME"] = appname
env["PYAPP_EXEC_SPEC"] = entrypoint
env["PYAPP_PROJECT_PATH"] = wheel
env["PYAPP_DISTRIBUTION_EMBED"] = "true"
env["PYAPP_PYTHON_VERSION"] = "3.13"
env["PYAPP_PASS_LOCATION"] = "true"

proc = subprocess.run(["cargo", "build", "--release"], env=env, cwd=pyapp_dir)
if proc.returncode == 0:
    output_exe = root.joinpath("pyapp-latest/target/release/pyapp")
    release_exe = output.joinpath(appname)
    output_exe.rename(release_exe)
    tarpath = output.joinpath(tarname)
    with tarfile.open(tarpath, "w:gz") as tar:
        tar.add(release_exe, arcname=appname)
    print(f"Wrote tarfile to '{tarpath}'")
