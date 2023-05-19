#!/usr/bin/env bash
curl "https://raw.githubusercontent.com/aclist/dztui/testing/dzgui.sh" > dzgui.sh
chmod +x dzgui.sh
xdg_file="$HOME/.local/share/applications/dzgui.desktop"
share="$HOME/.local/share/dzgui"
conf="$HOME/.config/dztui"
[[ -f $xdg_file ]] && rm $xdg_file
[[ -d $share ]] && rm -rf $share
[[ -d $conf ]] && rm -rf $conf
./dzgui.sh
