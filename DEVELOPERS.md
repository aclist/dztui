# TODO: link to here from sphinx docs

## Installing from source

### Fetch submodules
git submodule update --recursive --init

### Install with dev dependencies
uv pip install -e '.[dev]'

This includes all dependencies for building, linting, testing, and checking in code.
If you optionally want to install only a subset of dev tools, replace 'dev' with the following flag:

build: package release deps
docs: documentation tools
lint: code linting, fixing, and type checking
test: unit and integration tests

## Miscellaneous

### Setting up precommit hooks
pre-commit install

### Building documentation
sphinx-build -M html source build -a

### Building standalone release binaries
1. Set up the build target: `rustup target add x86_64-unknown-linux-musl`
2. Run `python3 scripts/release.py`
3. Generate a release and tag against the resulting tarfile generated in `dist`
