#!/usr/bin/env bash
set -o pipefail

src_path=$(realpath "$0")

version=6.0.1.beta-2
reference_branch="prerelease/6.0.1-beta.1"

#CONSTANTS
aid=221100
game="dayz"
app_name="dzgui"
app_name_upper="DZGUI"
workshop="steam://url/CommunityFilePage/"
sd_res="--width=1280 --height=800"
steamsafe_zenity="/usr/bin/zenity"
zenity_flags=("--width=500" "--title=DZGUI")
declare -A deps
deps=([awk]="5.1.1" [curl]="7.80.0" [jq]="1.6" [tr]="9.0" [$steamsafe_zenity]="3.44.1")

#CONFIG
config_path="$HOME/.config/dztui"
config_file="$config_path/dztuirc"

#PATHS
state_path="$HOME/.local/state/$app_name"
cache_path="$HOME/.cache/$app_name"
share_path="$HOME/.local/share/$app_name"
script_path="$share_path/dzgui.sh"
helpers_path="$share_path/helpers"

#LOGS
log_path="$state_path/logs"
debug_log="$log_path/DZGUI_DEBUG.log"

#STATE FILES
prefix="dzg"
history_file="$state_path/$prefix.history"
versions_file="$state_path/$prefix.versions"
lock_file="$state_path/$prefix.lock"
cols_file="$state_path/$prefix.cols.json"

#CACHE FILES
coords_file="$cache_path/$prefix.coords"

#legacy paths
hist_file="$config_path/history"
version_file="$config_path/versions"

#XDG
freedesktop_path="$HOME/.local/share/applications"

#HELPERS
ui_helper="$helpers_path/ui.py"
km_helper="$helpers_path/latlon"
func_helper="$helpers_path/funcs"
geo_helper="$helpers_path/ips.csv"

#REMOTE
remote_host=gh
author="aclist"
repo="dztui"
url_prefix="https://raw.githubusercontent.com/$author/$repo"
stable_url="$url_prefix/dzgui"
testing_url="$url_prefix/testing"
releases_url="https://github.com/$author/$repo/releases/download/browser"
km_helper_url="$releases_url/latlon"

set_im_module(){
    #TODO: drop pending SteamOS changes
    if pgrep -a gamescope | grep -q "generate-drm-mode"; then
        unset GTK_IM_MODULE
        logger INFO "Detected Steam Deck (Game Mode), unsetting GTK_IM_MODULE"
    fi
}

redact(){
    sed 's@\(/home/\)[^/]*@\1REDACTED@g'
}
logger(){
    local date="$(date "+%F %T,%3N")"
    local tag="$1"
    local string="$2"
    local self="${BASH_SOURCE[0]}"
    local caller="${FUNCNAME[1]}"
    local line="${BASH_LINENO[0]}"
    printf "%s␞%s␞%s::%s()::%s␞%s\n" "$date" "$tag" "$self" "$caller" "$line" "$string" \
        | redact >> "$debug_log"
}

setup_dirs(){
    directories=()
    directories+=("$state_path")
    directories+=("$cache_path")
    directories+=("$share_path")
    directories+=("$helpers_path")
    directories+=("$freedesktop_path")
    directories+=("$config_path")
    directories+=("$log_path")
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
    done
}

setup_state_files(){
    if [[ -f "$debug_log" ]]; then
        rm "$debug_log" && touch $debug_log
        logger INFO "Initializing DZGUI version $version"
    fi
    if [[ -f "$version_file" ]]; then
        mv "$version_file" "$versions_file" &&
        logger INFO "Migrating legacy version file"
    fi
    # wipe cache files
    if [[ $(ls -A "$cache_path") ]]; then
        for file in "$cache_path"/*; do
            rm "$file"
        done
        logger INFO "Wiped cache files"
    fi
}
print_config_vals(){
    local keys=(
    "branch"
    "name"
    "fav_server"
    "fav_label"
    "auto_install"
    "steam_path"
    "default_steam_path"
    "preferred_client"
    )
    for i in "${keys[@]}"; do
        logger INFO "Read key '$i': '${!i}'"
    done
    if [[ ${#ip_list[@]} -lt 1 ]]; then
        logger WARN "No IPs in saved server list"
    fi

}
test_gobject(){
    python3 -c "import gi"
    if [[ ! $? -eq 0 ]]; then
        logger CRITICAL "Missing PyGObject"
        fdialog "Requires PyGObject (python-gobject)"
        exit 1
    fi
    logger INFO "Found PyGObject in Python env"
}
update_config(){
    # handling for legacy files
    [[ -z $branch ]] && branch="stable"
    [[ -f $config_file ]] && mv $config_file ${config_file}.old
    write_config > $config_file && return 90 || return 1
    logger INFO "Updated config file at '$config_file'"
}
setup_steam_client(){
    local flatpak
    local steam
    local steam_cmd
    [[ -n $preferred_client ]] && return 0
    [[ $(command -v flatpak) ]] && flatpak=$(flatpak list | grep valvesoftware.Steam)
    steam=$(command -v steam)
    if [[ -z "$steam" ]] && [[ -z "$flatpak" ]]; then
        raise_error_and_quit "Requires Steam or Flatpak Steam"
    elif [[ -n "$steam" ]] && [[ -n "$flatpak" ]]; then
        preferred_client="steam"
    elif [[ -n "$steam" ]]; then
        preferred_client="steam"
    else
        steam_cmd="flatpak run com.valvesoftware.Steam"
    fi
    update_config && logger INFO "Preferred client set to '$steam_cmd'" || return 1
}
print_ip_list(){
    [[ ${#ip_list[@]} -eq 0 ]] && return 1
    printf "\t\"%s\"\n" "${ip_list[@]}"
}
write_config(){
cat <<-END
#Path to DayZ installation
steam_path="$steam_path"

#Battlemetrics API key
api_key="$api_key"

#Favorited server IP:PORT array
ip_list=(
$(print_ip_list)
)

#Favorite server to fast-connect to (limit one)
fav_server="$fav_server"

#Favorite server label (human readable)
fav_label="$fav_label"

#Custom player name (optional, required by some servers)
name="$name"

#Set to 1 to perform dry-run and print launch options
debug="$debug"

#Toggle stable/testing branch
branch="$branch"

#Start in fullscreen
fullscreen="$fullscreen"

#Steam API key
steam_api="$steam_api"

#Auto-install mods
auto_install="$auto_install"

#Automod staging directory
staging_dir="$staging_dir"

#Path to default Steam client
default_steam_path="$default_steam_path"

#Preferred Steam launch command (for Flatpak support)
preferred_client="$preferred_client"
END
}
depcheck(){
    for dep in "${!deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            local msg="Requires $dep >= ${deps[$dep]}"
            raise_error_and_quit "$msg"
        fi
    done
    local jqmsg="jq must be compiled with support for oniguruma"
    local jqtest
    jqtest=$(echo '{"test": "foo"}' | jq '.test | test("^foo$")')
    [[ $? -ne 0 ]] && raise_error_and_quit "$jqmsg"
    logger INFO "Initial dependencies satisfied"
}
check_pyver(){
    local pyver=$(python3 --version | awk '{print $2}')
    local minor=$(<<< $pyver awk -F. '{print $2}')
    if [[ -z $pyver ]] || [[ ${pyver:0:1} -lt 3 ]] || [[ $minor -lt 10 ]]; then
        local msg="Requires Python >=3.10"
        raise_error_and_quit "$msg"
    fi
    logger INFO "Found Python version: $pyver"
}
watcher_deps(){
    if [[ ! $(command -v wmctrl) ]] && [[ ! $(command -v xdotool) ]]; then
        raise_error_and_quit "Missing dependency: requires 'wmctrl' or 'xdotool'"
        exit 1
    fi
    logger INFO "Found DZG Watcher dependencies"
}
format_version_url(){
    [[ -z "$branch" ]] && branch="stable"
    case "$branch" in
        "stable")
            version_url="$stable_url/dzgui.sh"
            ;;
        "testing")
            version_url="$testing_url/dzgui.sh"
            ;;
    esac
    echo "$version_url"
}
write_desktop_file(){
cat <<-END
[Desktop Entry]
Version=1.0
Type=Application
Terminal=false
Exec=$share_path/dzgui.sh
Name=$app_name_upper
Comment=$app_name
Icon=$share_path/$app_name
Categories=Game
END
}
freedesktop_dirs(){
    local version_url=$(format_version_url)
    local img_url="$stable_url/images"
    curl -s "$version_url" > "$script_path"
    chmod +x "$script_path"
    for i in dzgui grid.png hero.png logo.png icon.png; do
        curl -s "$img_url/$i" > "$share_path/$i"
    done
    write_desktop_file > "$freedesktop_path/$app_name.desktop"
    [[ $is_steam_deck -eq 0 ]] && return
    write_desktop_file > "$HOME/Desktop/$app_name.desktop"
}
legacy_vars(){
    local suffix="fav"
    local hr_msg="Config file contains values based on old API. Please update and re-run setup."
    local msg="Config file contains legacy API value: '$suffix'"
    if [[ -n $fav ]]; then
        logger WARN "$msg"
        fdialog "$hr_msg"
        exit 1
    fi
    if [[ -n $whitelist ]]; then
        suffix="whitelist"
        logger WARN "$msg"
        fdialog "$hr_msg"
        exit 1
    fi
}
merge_config(){
    [[ -z $staging_dir ]] && staging_dir="/tmp"
    update_config
    tdialog "Wrote new config format to \n${config_file}\nIf errors occur, you can restore the file:\n${config_file}.old"
}
check_unmerged(){
    if [[ -f ${config_path}.unmerged ]]; then
        merge_config
        rm ${config_path}.unmerged
    fi
}
check_version(){
    [[ -n $reference_branch ]] && return
    local version_url=$(format_version_url)
    local upstream=$(curl -Ls "$version_url" | awk -F= '/^version=/ {print $2}')
    local res=$(get_response_code "$version_url")
    [[ $res -ne 200 ]] && raise_error_and_quit "Remote resource unavailable: '$version_url'"
    logger INFO "Local branch: '$branch', local version: $version"
    if [[ $branch == "stable" ]]; then
        version_url="$stable_url/dzgui.sh"
    elif [[ $branch == "testing" ]]; then
        version_url="$testing_url/dzgui.sh"
    fi
    [[ ! -f "$freedesktop_path/$app_name.desktop" ]] && freedesktop_dirs
    if [[ $version == $upstream ]]; then
        logger INFO "Local version is same as upstream"
        check_unmerged
    else
        logger WARN "Local and remote version mismatch: $version != $upstream"
        prompt_dl
    fi
}
download_new_version(){
    local version_url="$(format_version_url)"
    logger INFO "Version URL is '$version_url'"
    logger INFO "$src_path"
    mv "$src_path" "$src_path.old"
    curl -L "$version_url" > "$src_path" 2>$debug_log
    rc=$?
    if [[ $rc -eq 0 ]]; then
        dl_changelog
        logger INFO "Wrote new version to $src_path"
        chmod +x "$src_path"
        touch "${config_path}.unmerged"
        fdialog "DZGUI $upstream successfully downloaded. To use the new version, select Exit and restart."
        logger INFO "User exited after version upgrade"
        exit 0
    else
        mv "$src_path.old" "$src_path"
        logger WARN "curl failed to fetch new version. Rolling back"
        fdialog "Failed to download the new version. Restoring old version"
        return 1
    fi
}
prompt_dl(){
    _text(){
	cat <<-EOF
	Version conflict.

	Your branch: $branch
	Your version: $version
	Upstream version: $upstream
	
	Version updates introduce important bug fixes and are encouraged. Attempt to download the latest version?
	EOF
    }
    qdialog "$(_text)" "Yes" "No"
    if [[ $? -eq 1 ]]; then
        return 0
    else
        download_new_version
    fi
}
dl_changelog(){
    local mdbranch
    local md
    [[ $branch == "stable" ]] && mdbranch="dzgui"
    [[ $branch == "testing" ]] && mdbranch="testing"
    local md="$url_prefix/${mdbranch}/$file"
    curl -Ls "$md" > "$state_path/CHANGELOG.md"
}
test_display_mode(){
    pgrep -a gamescope | grep -q "generate-drm-mode"
    if [[ $? -eq 0 ]]; then
        echo gm
    else
        echo dm
    fi
}
check_architecture(){
    local cpu=$(< /proc/cpuinfo awk -F": " '/AMD Custom APU [0-9]{4}$/ {print $2; exit}')
    read -a APU_MODEL <<< "$cpu"
    if [[ ${APU_MODEL[3]} != "0932" ]] && [[ ${APU_MODEL[3]} != "0405" ]]; then
        is_steam_deck=0
        logger INFO "Setting architecture to 'desktop'"
        return
    fi

    if [[ $(test_display_mode) == "gm" ]]; then
        is_steam_deck=2
    else
        is_steam_deck=1
    fi
    logger INFO "Setting architecture to 'Steam Deck'"
}
check_map_count(){
    [[ $is_steam_deck -gt 0 ]] && return 0
    local map_count_file="/proc/sys/vm/max_map_count"
    local min_count=1048576
    local conf_file="/etc/sysctl.d/dayz.conf"
    local current_count
    if [[ ! -f ${map_count_file} ]]; then
        logger WARN "File '${map_count_file}' doesn't exist!"
        return 1
    fi
    current_count=$(cat ${map_count_file})
    if [[ $current_count -ge $min_count ]]; then
        logger DEBUG "System map count is set to ${current_count}"
        return 0
    fi
    qdialog "sudo password required to set system vm map count." "OK" "Cancel"
    if [[ $? -eq 0 ]]; then
        local pass
        logger INFO "Prompting user for sudo escalation"
        pass=$($steamsafe_zenity --password)
        if [[ $? -eq 1 ]]; then
            logger WARN "User aborted password prompt"
            return 1
        fi
        logger DEBUG "Old map count is $current_count"
        [[ $current_count -lt $min_count ]] && current_count=$min_count
        sudo -S <<< "$pass" sh -c "echo 'vm.max_map_count=${current_count}' > $conf_file"
        sudo sysctl -p "$conf_file"
        logger DEBUG "Updated map count to $min_count"
    else
        logger WARN "User aborted map count prompt"
        return 1
    fi
}
qdialog(){
    local text="$1"
    local ok="$2"
    local cancel="$3"
    $steamsafe_zenity --question --text="$1" --ok-label="$ok" --cancel-label="$cancel" "${zenity_flags[@]}"
}
pdialog(){
    $steamsafe_zenity --progress --pulsate --auto-close "${zenity_flags[@]}" --text="$1"
}
fdialog(){
    $steamsafe_zenity --warning --ok-label="Exit" --text="$1" "${zenity_flags[@]}"
}
tdialog(){
    $steamsafe_zenity --info --text="$1" "${zenity_flags[@]}"
}
steam_deps(){
    local flatpak
    local steam
    [[ $(command -v flatpak) ]] && flatpak=$(flatpak list | grep valvesoftware.Steam)
    steam=$(command -v steam)
    if [[ -z "$steam" ]] && [[ -z "$flatpak" ]]; then
        local msg="Found neither Steam nor Flatpak Steam"
        raise_error_and_quit "$msg"
        exit 1
    elif [[ -n "$steam" ]] && [[ -n "$flatpak" ]]; then
        [[ -n $preferred_client ]] && return 0
        if [[ -z $preferred_client ]]; then
            preferred_client="steam"
        fi
    elif [[ -n "$steam" ]]; then
        preferred_client="steam"
    else
        preferred_client="flatpak"
    fi
    update_config
    logger INFO "Preferred client set to '$preferred_client'"
}
migrate_files(){
    if [[ ! -f $config_path/dztuirc.oldapi ]]; then
        cp $config_file $config_path/dztuirc.oldapi
        logger INFO "Migrated old API file"
    fi
    [[ ! -f $hist_file ]] && return
    rm $hist_file
    logger INFO "Wiped old history file"
}
stale_symlinks(){
    local game_dir="$steam_path/steamapps/common/DayZ"
    for l in $(find "$game_dir" -xtype l); do
        logger DEBUG "Updating stale symlink '$l'"
        unlink "$l"
    done
}

check_availability() {
    if [[ -z $1 ]]; then
        return 1
    fi
    local url=$1
    local timeout_sec="3"
    if [[ $2 ]]; then
        timeout_sec=$2
    fi
    if ! ping -w "$timeout_sec" "$url" > /dev/null 2>&1; then
        logger WARN "Failed to reach $url, service may be down."
        return 1
    fi
}

local_latlon(){
    if [[ -z $(command -v dig) ]]; then
        local url_ipecho="https://ipecho.net/plain"
        if ! check_availability "ipecho.net"; then
            logger WARN "Failed to get external ip address, ipecho.net service may be down."
            return 1
        fi
        local local_ip=$(curl -Ls "$url_ipecho")
    else
        # TODO : implement checking remote
        local local_ip=$(dig -4 +short myip.opendns.com @resolver1.opendns.com)
    fi
    local url_ip_api="http://ip-api.com/json/$local_ip"
    if ! check_availability "ip-api.com"; then
        logger WARN "Failed to get local coordinates, ip-api.com service may be down."
        return 1
    fi
    local res=$(curl -Ls "$url_ip_api" | jq -r '"\(.lat)\n\(.lon)"')
    if [[ -z "$res" ]]; then
        logger WARN "Failed to get local coordinates"
        return 1
    fi
    echo "$res" > "$coords_file"
}

lock(){
    [[ ! -f $lock_file ]] && touch $lock_file
    local pid=$(cat $lock_file)
    ps -p $pid -o pid= >/dev/null 2>&1
    res=$?
    if [[ $res -eq 0 ]]; then
        local msg="DZGUI is already running ($pid)"
        raise_error_and_quit "$msg"
    elif [[ $pid == $$ ]]; then
        :
    else
        echo $$ > $lock_file
    fi
}
get_hash(){
    local file="$1"
    md5sum "$1" | awk '{print $1}'
}
fetch_a2s(){
    # this file is currently monolithic
    [[ -d $helpers_path/a2s ]] && { logger INFO "A2S helper is current"; return 0; }
    local sha=c7590ffa9a6d0c6912e17ceeab15b832a1090640
    local author="yepoleb"
    local repo="python-a2s"
    local url="https://github.com/$author/$repo/tarball/$sha"
    local prefix="${author^}-$repo-${sha:0:7}"
    local file="$prefix.tar.gz"
    local res=$(get_response_code "$url")
    [[ $res -ne 200 ]] && raise_error_and_quit "Remote resource unavailable: '$file'"
    curl -Ls "$url" > "$helpers_path/$file"
    tar xf "$helpers_path/$file" -C "$helpers_path" "$prefix/a2s" --strip=1
    rm "$helpers_path/$file"
    logger INFO "Updated A2S helper to sha '$sha'"
}
fetch_dzq(){
    local sum="0a334e1e144e76e560419d155435c91e"
    local file="$helpers_path/a2s/dayzquery.py"
    if [[ -f $file ]] && [[ $(get_hash "$file") == $sum ]]; then
        logger INFO "DZQ is current"
        return 0
    fi
    local sha=a22a9f428cbe075d7dda62f78000296955eea92a
    local author="yepoleb"
    local repo="dayzquery"
    local url="https://raw.githubusercontent.com/$author/$repo/$sha/dayzquery.py"
    local res=$(get_response_code "$url")
    [[ $res -ne 200 ]] && raise_error_and_quit "Remote resource unavailable: 'dayzquery.py'"
    curl -Ls "$url" > "$file"
    logger INFO "Updated DZQ to sha '$sha'"
}
fetch_icons(){
    res=(
            "16"
            "24"
            "32"
            "48"
            "64"
            "96"
            "128"
            "256"
    )
    url="$stable_url/images/icons"
    for i in "${res[@]}"; do
        size="${i}x${i}"
        dir="$HOME/.local/share/icons/hicolor/$size/apps"
        icon="$dir/$app_name.png"
        [[ -f $icon ]] && return
        if [[ ! -d $dir ]]; then
            mkdir -p "$dir"
        fi
        logger INFO "Updating $size Freedesktop icon"
        curl -Ls "${url}/${i}.png" > "$icon"
    done
}
fetch_helpers_by_sum(){
    [[ -f "$config_file" ]] && source "$config_file"
    declare -A sums
    sums=(
        ["funcs"]="5d7d92b7b8a9c788b133ce5271a76553"
        ["query_v2.py"]="55d339ba02512ac69de288eb3be41067"
        ["servers.py"]="ed442c3aecf33f777d59dcf53650d263"
        ["ui.py"]="2476397883a4272eaf940403ba5a6575"
        ["vdf2json.py"]="2f49f6f5d3af919bebaab2e9c220f397"
        ["pefile.py"]="21531f2c0d9dfa5f110cf6779f9d22c0"
    )
    local author="aclist"
    local repo="dztui"
    local realbranch
    local file
    local sum
    local full_path

    # first time setup
    if [[ -z $branch ]]; then
        realbranch="dzgui"
    else
        realbranch="$branch"
    fi
    if [[ $realbranch == "stable" ]]; then
        realbranch="dzgui"
    fi

    if [[ -n $reference_branch ]]; then
        realbranch="$reference_branch"
    fi

    for i in "${!sums[@]}"; do
        file="$i"
        sum="${sums[$i]}"
        full_path="$helpers_path/$file"

        url="${url_prefix}/$realbranch/helpers/$file"

        if [[ -f "$full_path" ]] && [[ $(get_hash "$full_path") == $sum ]]; then
            logger INFO "$file is current"
        else
            logger WARN "File '$full_path' checksum != '$sum'"
            local res=$(get_response_code "$url")
            [[ $res -ne 200 ]] && raise_error_and_quit "Remote resource unavailable: '$url'"
            curl -Ls "$url" > "$full_path"
            if [[ ! $? -eq 0 ]]; then
                raise_error_and_quit "Failed to fetch the file '$file'. Possible timeout?"
            fi
            if [[ $(get_hash $full_path) != $sum ]]; then
                logger WARN "Downloaded new '$file', but checksum != '$sum'"
            fi
            logger INFO "Updated '$full_path' to sum '$sum'"
        fi
        [[ $file == "funcs" ]] && chmod +x "$full_path"
    done
    return 0
}
fetch_km_helper(){
    local km_sum="b038fdb8f655798207bd28de3a004706"
    if [[ ! -f $km_helper ]] || [[ $(get_hash $km_helper) != $km_sum ]]; then
        local res=$(get_response_code "$km_helper_url")
        [[ $res -ne 200 ]] && raise_error_and_quit "Remote resource unavailable: '$km_helper_url'"
        curl -Ls "$km_helper_url" > "$km_helper"
        chmod +x "$km_helper"
    fi
}
get_response_code(){
    local url="$1"
    curl -Ls -I -o /dev/null -w "%{http_code}" "$url"
}
raise_error_and_quit(){
    echo "$1"
    exit 1
}
fetch_ip_db(){
    parse_dl_url(){
        curl -Ls "$url" \
        | grep "csv.gz" \
        | awk -F"['']" '{print $2}'
    }

    parse_dl_url_date(){
        local url="$1"
        <<< "$url" \
        awk -F/ '{print $5}' \
        | awk -F"dbip-city-lite-" '{print $2}' \
        | awk -F'.csv.gz' '{print $1}'
    }

    fetch(){
        logger INFO "Triggering fetch routine"
        local url="$1"

        curl -Ls "$url" > "$base_file"
        if [[ $? -ne 0 ]]; then
            logger WARN "Abnormal exit while accessing '$url'"
            return
        fi

        gunzip -f "$base_file"
        if [[ $? -ne 0 ]]; then
            rm "$base_file"
            logger WARN "Abnormal exit while unpacking gzip '$base_file'"
            return
        fi

        < "$extracted_file" grep -vE "^[a-z0-9]{4}:" | grep -v "::" > "$ip_file"
        if [[ $? -ne 0 ]]; then
            logger WARN "Abnormal exit while parsing IPs"
            return
        fi
        rm "${state_path}/${month}.csv"

        readarray -t records < <(cat $ip_file | awk -F, 'NR==1 {print $1} END {print $1}')
        if [[ ${records[0]} != "0.0.0.0" ]] && [[ ${records[1]} != "224.0.0.0" ]]; then
            logger WARN "Anchor records missing in '$ip_file', possibly malformed"
            rm "$ip_file"
            return
        fi

        mv "$ip_file" "$geo_helper"
        if [[ $? -ne 0 ]]; then
            logger WARN "Abnormal exit while moving '$ip_file' to '$helpers_path'"
            rm "$ip_file"
        fi

        echo "$month" > "$month_file"
        logger INFO "Wrote '$month' to stub '$month_file'"
        logger INFO "Updated '$ip_file'"
    }

    local url="https://db-ip.com/db/download/ip-to-city-lite"
    local month_file="${state_path}/.month"
    local ip_file="${state_path}/ips.csv"

    # test main url
    local res=$(get_response_code "$url")
    if [[ $res -ne 200 ]]; then
        logger WARN "Failed to retrieve remote resource: '$url' ($res)"
        return
    fi
    logger INFO "Resolved remote URL: '$url'"

    # test dl url
    local dl_url="$(parse_dl_url)"
    local res=$(get_response_code "$dl_url")
    if [[ $res -ne 200 ]]; then
        logger WARN "Remote resource unavailable: '$dl_url' ($res)"
        return
    fi
    logger INFO "Resolved download URL: '$dl_url'"

    local month=$(parse_dl_url_date "$dl_url")
    local base_file="${state_path}/${month}.csv.gz"
    local extracted_file="${state_path}/${month}.csv"

    # no stub file
    if [[ ! -f $month_file ]]; then
        logger WARN "No stub file '$month_file' present"
        fetch "$dl_url"
        return
    fi

    # local needs update
    local last_month=$(< "$month_file")
    if [[ $last_month != "$month" ]]; then
        logger WARN "Local stub '$last_month' does not match remote stub '$month'"
        fetch "$dl_url"
        return
    fi

    # if stub is same date, abort
    logger INFO "Local stub '$last_month' is identical to remote, skipping"
}
fetch_helpers(){
    fetch_a2s
    fetch_dzq
    fetch_km_helper
    fetch_ip_db
    fetch_helpers_by_sum
    [[ ! -f $share_path/icon.png ]] && freedesktop_dirs
    fetch_icons
}
raise_error_and_quit(){
    local msg="$1"
    logger CRITICAL "$msg"
    fdialog "$msg"
    exit 1
}
test_steam_api(){
    local key="$1"
    [[ -z $key ]] && return 1
    local url="https://api.steampowered.com/IGameServersService/GetServerList/v1/?filter=\appid\221100&limit=10&key=$key"
    local code=$(curl -ILs "$url" | grep -E "^HTTP")
    [[ ! $code =~ 200 ]] && echo 1
    [[ $code =~ 200 ]] && echo 0
}
test_bm_api(){
    local bm_api="https://api.battlemetrics.com/servers"
    local key="$1"
    [[ -z $key ]] && return 1
    local code=$(curl -ILs "$bm_api" \
        -H "Authorization: Bearer "$key"" -G \
        -d "filter[game]=$game" \
        | grep -E "^HTTP")
    [[ $code =~ 401 ]] && echo 1
    [[ $code =~ 200 ]] && echo 0
}
find_default_path(){
    _discover(){
        readarray -t paths < <(find / -type d \( -path "/proc" -o -path "*/timeshift" -o -path \
                    "/tmp" -o -path "/usr" -o -path "/boot" -o -path "/proc" -o -path "/root" \
                    -o -path "/sys" -o -path "/etc" -o -path "/var" -o -path "/lost+found" \) -prune \
                    -o -regex ".*Steam/config/libraryfolders.vdf$" -print 2>/dev/null | sed 's@/config/libraryfolders.vdf@@')

        if [[ "${#paths[@]}" -gt 1 ]]; then
            echo "100"
            default_steam_path=$(printf "%s\n" "${paths[@]}" | $steamsafe_zenity --list --column="paths" --hide-header --text="Found multiple valid Steam paths. Select your default Steam installation." --title="DZGUI")
            [[ -z "$default_steam_path" ]] && exit 1
        else
            default_steam_path="${paths[0]}"
        fi
    }
    if [[ $is_steam_deck -gt 0 ]]; then
        default_steam_path="$HOME/.local/share/Steam"
        logger INFO "Set default Steam path to $default_steam_path"
        return 0
    fi
    local def_path
    local ubuntu_path
    local flatpak_path
    local debian_path
    def_path="$HOME/.local/share/Steam"
    ubuntu_path="$HOME/.steam/steam"
    debian_path="$HOME/.steam/debian-installation"
    flatpak_path="$HOME/.var/app/com.valvesoftware.Steam/data/Steam"

    #ubuntu path must precede default path because
    #both exist on ubuntu systems, but only ubuntu path contains library data
    for i in "$ubuntu_path" "$def_path" "$debian_path" "$flatpak_path"; do
        if [[ -d "$i" ]]; then
            default_steam_path="$i"
            return 0
        fi
    done

    local msg="Let DZGUI auto-discover Steam path (accurate, slower)\nSelect the Steam path manually (less accurate, faster)"
    local res=$(echo -e "$msg" | $steamsafe_zenity --list \
        --column="Choice" \
        --title="DZGUI" \
        --hide-header \
        --text="Steam is not installed in a standard location." \
        $sd_res)

    case "$res" in
        *auto*) _discover > >(pdialog "Scanning paths") ;;
        *manual*)
            zenity --info --text="\nSelect the top-level entry point to the location where Steam (not DayZ)\nis installed and before entering the \"steamapps\" path.\n\nE.g., if Steam is installed at:\n\"/media/mydrive/Steam\"\n\nCorrect:\n- \"/media/mydrive/Steam\"\n\nIncorrect:\n- \"/media/mydrive/Steam/steamapps/common/DayZ\"\n- \"/media/mydrive/\"" --width=500 &&
            file_picker ;;
        esac
}
file_picker(){
    local path=$($steamsafe_zenity --file-selection --directory)
    logger INFO "File picker path resolved to: $path"
    if [[ -z "$path" ]]; then
        logger WARN "Steam path selection was empty"
        return
    else
        default_steam_path="$path"
    fi
}
find_library_folder(){
    local search_path="$1"
    steam_path="$(python3 "$helpers_path/vdf2json.py" -i "$1/steamapps/libraryfolders.vdf" \
        | jq -r '.libraryfolders[]|select(.apps|has("221100")).path')"
    if [[ ! $? -eq 0 ]] || [[ -z $steam_path ]]; then
        logger WARN "Failed to parse Steam path using '$search_path'"
        return 1
    fi
    logger INFO "Steam path resolved to: $steam_path"
}
create_config(){
    #if old path is malformed and this function is forcibly called,
    #wipe paths from memory before entering the loop to force path rediscovery
    unset default_steam_path
    unset steam_path

    while true; do
        local player_input="$($steamsafe_zenity \
            --forms \
            --add-entry="Player name (required for some servers)" \
            --add-entry="Steam API key" \
            --add-entry="BattleMetrics API key (optional)" \
            --title="DZGUI" \
            --text="DZGUI" $sd_res \
            --separator="@")"
        #explicitly setting IFS crashes $steamsafe_zenity in loop
        #and mapfile does not support high ascii delimiters, so split fields with newline
        readarray -t args < <(<<< "$player_input" sed 's/@/\n/g')
        name="${args[0]}"
        steam_api="${args[1]}"
        api_key="${args[2]}"

        if [[ -z $player_input ]]; then
            logger WARN "User aborted setup process"
            exit 1
        fi
        if [[ -z $steam_api ]]; then
            tdialog "Steam API key canot be empty"
            continue
        elif [[ "${#steam_api}" -lt 32 ]] || [[ $(test_steam_api "$steam_api") -eq 1 ]]; then
            tdialog "Invalid Steam API key"
            continue
        fi
        if [[ -n $api_key ]] && [[ $(test_bm_api $api_key) -eq 1 ]]; then
            tdialog "Invalid BM API key"
            continue
        fi
        while true; do
            if [[ -n $steam_path ]]; then
                write_config
                [[ $? -eq 0 ]] && logger INFO "Successfully created config file"
                return 0
            fi
            find_default_path
            find_library_folder "$default_steam_path"
            if [[ -z $steam_path ]]; then
                logger raise_error "Steam path was empty"
                zenity --question --text="DayZ not found or not installed at the Steam library given. NOTE: if you recently installed DayZ or moved its location, you MUST restart Steam first for these changes to synch." --ok-label="Choose path manually" --cancel-label="Exit"
                if [[ $? -eq 0 ]]; then
                    logger INFO "User selected file picker"
                    file_picker
                    find_library_folder "$default_steam_path"
                else
                    fdialog "Failed to find Steam at the provided location"
                    exit 1
                fi
            else
                branch="stable"
                update_config
                logger INFO "Wrote config to '$config_file'"
                return 0
            fi
        done
    done
}
varcheck(){
    local msg="Config file '$config_file' missing. Start first-time setup now?"
    local msg2="The Steam paths set in your config file appear to be invalid (DayZ was moved or uninstalled). Restart first-time setup now?"
    if [[ ! -f $config_file ]]; then
        qdialog "$msg" "Yes" "Exit"
        if [[ $? -eq 1 ]]; then
            logger CRITICAL "Config file missing, but user aborted setup"
            exit 1
        fi
        create_config
    fi
    source "$config_file"
    local workshop_dir="$steam_path/steamapps/workshop/content/$aid"
    local game_dir="$steam_path/steamapps/common/DayZ"
    if [[ ! -d $steam_path ]] || [[ ! -d $game_dir ]] || [[ ! $(find $game_dir -type f) ]]; then
        logger WARN "DayZ path resolved to '$game_dir'"
        logger WARN "Workshop path resolved to '$workshop_dir'"
        qdialog "$msg2" "Yes" "Exit"
        if [[ $? -eq 1 ]]; then
            logger CRITICAL "Malformed Steam path, but user aborted setup"
            exit 1
        fi
        create_config
        return 0
    fi
}
is_dzg_downloading(){
    if [[ -d $steam_path ]] && [[ -d $steam_path/downloading/$aid ]]; then
        logger WARN "DayZ may be scheduling updates"
        return 0
    fi
}
is_steam_running(){
    local res=$(ps aux | grep "steamwebhelper" | grep -v grep)
    if [[ -z $res ]]; then
        logger WARN "Steam may not be running"
        tdialog "Is Steam running? For best results, make sure Steam is open in the background."
        return 0
    fi
}
get_response_code(){
    local url="$1"
    curl -Ls -I -o /dev/null -w "%{http_code}" "$url"
}
test_connection(){
    declare -A hr
    local res1
    local res2
    local str="No connection could be established to the remote server"
    hr=(
        ["github.com"]="https://github.com/$author"
        ["codeberg.org"]="https://codeberg.org/$author"
    )

    res=$(get_response_code "${hr["github.com"]}")
    if [[ $res -ne 200 ]]; then
        logger WARN "Remote host '${hr["github.com"]}' unreachable', trying fallback"
        remote_host=cb
        logger INFO "Set remote host to '${hr["codeberg.org"]}'"
        res=$(get_response_code "${hr["codeberg.org"]}")
        [[ $res -ne 200 ]] && raise_error_and_quit "$str (${hr["codeberg.org"]})"
    fi
    if [[ $remote_host == "cb" ]]; then
        url_prefix="https://codeberg.org/$author/$repo/raw/branch"
        releases_url="https://codeberg.org/$author/$repo/releases/download/browser"
        stable_url="$url_prefix/dzgui"
        testing_url="$url_prefix/testing"
        km_helper_url="$releases_url/latlon"
    fi
}
legacy_cols(){
    [[ ! -f $cols_file ]] && return
    local has=$(< "$cols_file" jq '.cols|has("Queue")')
    [[ $has == "true" ]] && return
    < $cols_file jq '.cols += { "Queue": 120 }' > $cols_file.new &&
    mv $cols_file.new $cols_file
}
stale_mod_signatures(){
    [[ ! -f "$versions_file" ]] && return
    local workshop_dir="$steam_path/steamapps/workshop/content/$aid"
    if [[ -d $workshop_dir ]]; then
        readarray -t old_mod_ids < <(awk -F, '{print $1}' $versions_file)
        for ((i=0; i<${#old_mod_ids[@]}; ++i)); do
            if [[ ! -d $workshop_dir/${old_mod_ids[$i]} ]]; then
                "$func_helper" "align_local" "${old_mod_ids[$i]}"
            fi
        done
    fi

}
create_new_links(){
    "$func_helper" "update_symlinks"
}
initial_setup(){
    setup_dirs
    setup_state_files
    depcheck
    check_pyver
    test_gobject
    watcher_deps
    check_architecture
    test_connection
    fetch_helpers > >(pdialog "Checking helper files")
    varcheck
    source "$config_file"
    lock
    legacy_vars
    legacy_cols
    check_version
    check_map_count
    steam_deps
    migrate_files
    stale_symlinks
    stale_mod_signatures
    create_new_links
    local_latlon
    is_steam_running
    is_dzg_downloading
    print_config_vals
}
uninstall(){
    _full(){
        for i in "$config_path" "$state_path" "$cache_path" "$share_path"; do
            echo "Deleting the path '$i'"
            rm -rf "$i"
        done
    }
    _partial(){
        for i in "$cache_path" "$share_path"; do
            echo "Deleting the path '$i'"
            rm -rf "$i"
        done
    }
    local choice=$($steamsafe_zenity \
        --list \
        --radiolist \
        --column="a" \
        --column="b" \
        --hide-header \
        --text="Choose an uninstall routine below." \
        TRUE "Keep user config files" \
        FALSE "Delete all DZGUI files" \
        --title="DZGUI"
        )

    case "$choice" in
        "Keep user config files")
            _partial
            ;;
        "Delete all DZGUI files")
            _full
            ;;
        "")
            echo "User aborted uninstall process"
            exit 1
            ;;
    esac
    local self="$(realpath "$0")"
    echo "Deleting '$self'"
    rm "$self"
    echo "Uninstall routine complete"
}

usage(){
cat <<- EOM
DZGUI - Free and Open Source DayZ launcher

Usage:

  dzgui.sh [options]

Description:

  When no option is provided, the script launches DZGUI.

Options:

  -u, --uninstall:
      Uninstalls the software

  -v, --version:
      Prints the version

  -h, --help:
      Prints this message
EOM
}

main(){
    # setup zenity environment
    local zenv=""
    zenv=$(zenity --version 2>/dev/null)
    [[ -z $zenv ]] && { echo "Requires zenity >= ${deps[$steamsafe_zenity]}"; exit 1; }

    # parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            "--uninstall" | "-u")
                uninstall
                exit 0
                # shift
                ;;
            "--version" | "-v")
                echo $version
                exit 0
                # shift
                ;;
            "--help" | "-h")
                usage
                exit 0
                # shift
                ;;
            *)
                echo "Unrecognized command!"
                return 1
        esac
    done

    set_im_module

    printf "Initializing setup...\n"
    initial_setup

    printf "All OK. Kicking off UI...\n"
    python3 "$ui_helper" "--init-ui" "$version" "$is_steam_deck"

}

if [[ $(basename "$0") == "dzgui.sh" ]]; then
   main "$@"

   #TODO: tech debt: cruddy handling for steam forking
   [[ $? -eq 1 ]] && pkill -f dzgui.sh
fi
