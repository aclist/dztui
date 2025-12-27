#!/usr/bin/env bash
get_response_code(){
    local url="$1"
    curl -Ls -I -o /dev/null -w "%{http_code}" "$url"
}
abort(){
    printf "Remote resource not available. Try again later.\n"
    exit 1
}
fetch(){
    local file="dzgui.sh"
    local author="aclist"
    local repo="dztui"
    local branch="dzgui"
    local url
    local res
    gh_url="https://raw.githubusercontent.com/$author/$repo/$branch/$file"
    cb_url="https://codeberg.org/$author/$repo/raw/branch/$branch/$file"

    url="$gh_url"
    printf "Checking the remote resource at '%s'\n" "$url"
    res=$(get_response_code "$url")
    if [[ $res -ne 200 ]]; then
        url="$cb_url"
        printf "Checking the remote resource at '%s'\n" "$url"
        res=$(get_response_code "$url")
        if [[ $res -ne 200 ]]; then
            abort
        fi
    fi

    curl -L "$url" > dzgui.sh
    chmod +x dzgui.sh
    xdg_file="$HOME/.local/share/applications/dzgui.desktop"
    share="$HOME/.local/share/dzgui"
    [[ -f $xdg_file ]] && rm $xdg_file
    [[ -d $share ]] && rm -rf "$share"
    ./dzgui.sh
}

fetch
