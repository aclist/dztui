#!/usr/bin/env bash
# TODO: move this into package data dir
prefix="dzgui"
tag="$1"
prefix="$2"
dir="/tmp/dzgui-${tag}"

mkdir -p "$dir"

git clone -C "$dir" git@github.com:aclist/dzgui.git --branch "${tag}"
git -C "$dir" submodule update --recursive --init

if [[ ! $(which python3.13) ]]; then
    echo "Missing python3.13"
    exit 1
fi

python3.13 -m venv "${prefix}"
source "$prefix/bin/activate"

rm -rf "$dir"
if [[ $(which uv) ]]; then
    uv --directory "$dir" pip install .
else
    cd "$dir"
    pip install -r requirements.txt
    echo "Setup complete. Re-launch DZGUI via the command 'dzgui'"
fi
