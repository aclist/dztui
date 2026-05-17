import build
import os
import subprocess

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
filename = f"{APP_NAME_LOWER}-{version}-{interpreter}-{arch}-{target}.whl"

wheel = str(output.joinpath(filename))
entrypoint = "dzgui.main:main"

env = os.environ
env["PYAPP_PROJECT_VERSION"] = version
env["PYAPP_PROJECT_NAME"] = APP_NAME_LOWER
env["PYAPP_EXEC_SPEC"] = entrypoint
env["PYAPP_PROJECT_PATH"] = wheel
env["PYAPP_DISTRIBUTION_EMBED"] = "1"
env["PYAPP_PYTHON_VERSION"] = "3.13"

proc = subprocess.run(["cargo", "build", "--release"], env=env, cwd=pyapp_dir)
if proc.returncode == 0:
    output_exe = root.joinpath("pyapp-latest/target/release/pyapp")
    release_exe = output.joinpath("dzgui")
    output_exe.rename(release_exe)
    print(f"Wrote output to '{release_exe}'")
