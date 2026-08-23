from pathlib import Path


def iterate(search_str: str) -> None:
    # TODO: exclude files from .gitignore
    print()
    print(f"Searching for '{search_str}'")
    print()
    files = Path(".").rglob("*")
    ignore = [
        "scripts/",
        ".git",
        "egg",
        "CHANGELOG",
        ".mypy",
        "build/",
        "test.py",
        "bugs",
        "pyproject.toml",
    ]
    for file in files:
        if file.is_dir():
            continue
        if any(s in str(file) for s in ignore):
            continue
        try:
            text = file.read_text()
            if search_str in text:
                c = text.count(search_str)
                if 0 < c < 2:
                    print(file, c)
        except Exception:
            continue


imports = ["Pango", "GObject", "GLib", "Gdk", "Gtk"]
for i in imports:
    iterate(i)
