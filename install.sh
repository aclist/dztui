#!/usr/bin/env bash
curl -L "https://codeberg.org/aclist/dzgui/raw/branch/dzgui/dzgui.sh" > dzgui.sh
chmod +x dzgui.sh
xdg_file="$HOME/.local/share/applications/dzgui.desktop"
share="$HOME/.local/share/dzgui"
[[ -f $xdg_file ]] && rm $xdg_file
[[ -d $share ]] && rm -rf "$share"
./dzgui.sh
