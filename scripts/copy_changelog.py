import shutil
import subprocess
from pathlib import Path

par = Path(__file__).parent.parent
clog = par / "CHANGELOG.md"
target = par / "dzgui/data/CHANGELOG.md"

shutil.copy(clog, target)

subprocess.call(["git", "add", target])
