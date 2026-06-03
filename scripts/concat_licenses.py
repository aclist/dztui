from pathlib import Path

def concat_license() -> str:
    combined = ""
    root = Path(__file__).resolve().parents[1]
    licenses = root.joinpath("licenses")
    self_license = root.joinpath("LICENSE")
    combined += "--- DZGUI application license ---\n\n"
    combined += self_license.read_text()
    for _dir in licenses.iterdir():
        docs = _dir.glob("*")
        doc = list(docs)[0]
        header = f"\n--- The verbatim license for bundled dependency '{_dir.name}' follows ---\n\n"
        combined += header
        combined += doc.read_text()
    return combined
