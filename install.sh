#!/usr/bin/env bash
curl "https://raw.githubusercontent.com/aclist/dztui/testing/dzgui.sh" > dzgui.sh
chmod +x dzgui.sh
xdg_file="$HOME/.local/share/applications/dzgui.desktop"
share="$HOME/.local/share/dzgui"
[[ -f $xdg_file ]] && rm $xdg_file
[[ -d $share ]] && rm -rf "$share"
./dzgui.sh
