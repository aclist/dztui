# TODO: link to here from sphinx docs

# Installing dev dependencies
uv pip install -e .[dev]

# Setting up precommit hooks
pre-commit install

# Fetching submodules
git submodule update --recursive --init

# Building documentation
sphinx-build -M html source build -a

# Building standalone DZGUI release binaries
1. Set up the build target: `rustup target add x86_64-unknown-linux-musl`
2. Run `python3 scripts/release.py`
3. Generate a release and tag against the bundled `dzgui` executable
