from pathlib import Path

def concat_license() -> str:
    root = Path(__file__).resolve().parents[1]
    licenses = root.joinpath("licenses")
    combined = ""
    for _dir in licenses.iterdir():
        docs = _dir.glob("*.md")
        doc = list(docs)[0]
        header = f"\n--- The verbatim license for bundled dependency '{_dir.name}' follows ---\n\n"
        combined += header
        combined += doc.read_text()
    return combined

