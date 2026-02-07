import os
import subprocess
import sys

cmd = ["git", "ls-files", "--others", "--exclude-standard"]
result = subprocess.Popen(
    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
)
with open(".gitignore", "r") as f:
    ignored = [line.rstrip() for line in f]

untracked = [os.path.basename(line.rstrip()) for line in result.stdout]
for file in untracked:
    if not any(file in item for item in ignored):
        res = input(f"File '{file}' is untracked. Proceed anyway? [Y/n] ")
        if res.lower() in ("", "y"):
            sys.exit(0)
        else:
            sys.exit(1)
