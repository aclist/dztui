import build
import os
import subprocess
import tarfile

from importlib import metadata
from pathlib import Path

from dzgui.const.constants import APP_NAME_LOWER

root = Path(__file__).resolve().parents[1]
output = root.joinpath("dist")

pyapp_dir = root.joinpath("pyapp-latest")

builder = build.ProjectBuilder(root)
builder.build("wheel", output_directory=output)

interpreter = "py3"
arch = "none"
target = "any"
version = metadata.version(APP_NAME_LOWER)
wheelname = f"{APP_NAME_LOWER}-{version}-{interpreter}-{arch}-{target}.whl"
tarname = f"{APP_NAME_LOWER}-{version}.tar.gz"

wheel = str(output.joinpath(wheelname))
entrypoint = "dzgui.main:main"

env = os.environ
env["PYAPP_PROJECT_VERSION"] = version
env["PYAPP_PROJECT_NAME"] = APP_NAME_LOWER
env["PYAPP_EXEC_SPEC"] = entrypoint
env["PYAPP_PROJECT_PATH"] = wheel
env["PYAPP_DISTRIBUTION_EMBED"] = "true"
env["PYAPP_PYTHON_VERSION"] = "3.13"
env["PYAPP_PASS_LOCATION"] = "true"

proc = subprocess.run(["cargo", "build", "--release"], env=env, cwd=pyapp_dir)
if proc.returncode == 0:
    output_exe = root.joinpath("pyapp-latest/target/release/pyapp")
    release_exe = output.joinpath(APP_NAME_LOWER)
    output_exe.rename(release_exe)
    tarpath = output.joinpath(tarname)
    with tarfile.open(tarpath, "w:gz") as tar:
        tar.add(release_exe)
    print(f"Wrote tarfile to '{tarpath}'")
