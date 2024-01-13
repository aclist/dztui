#!/usr/bin/env bash
set -o pipefail

version=5.0.0.rc-19

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
deps=([awk]="5.1.1" [curl]="7.80.0" [jq]="1.6" [tr]="9.0" [$steamsafe_zenity]="3.42.1")

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

#CACHE FILES
coords_file="$cache_path/$prefix.coords"

#legacy paths
hist_file="$config_path/history"
version_file="$config_path/versions"

#XDG
freedesktop_path="$HOME/.local/share/applications"

#HELPERS
ui_helper="$helpers_path/ui.py"
geo_file="$helpers_path/ips.csv"
km_helper="$helpers_path/latlon"
sums_path="$helpers_path/sums.md5"
func_helper="$helpers_path/funcs"

#URLS
author="aclist"
repo="dztui"
url_prefix="https://raw.githubusercontent.com/$author/$repo"
stable_url="$url_prefix/dzgui"
testing_url="$url_prefix/testing"
releases_url="https://github.com/$author/$repo/releases/download/browser"
km_helper_url="$releases_url/latlon"
geo_file_url="$releases_url/ips.csv.gz"

logger(){
    local date="$(date "+%F %T,%3N")"
    local tag="$1"
    local string="$2"
    local self="${BASH_SOURCE[0]}"
    local caller="${FUNCNAME[1]}"
    local line="${BASH_LINENO[0]}"
    printf "%s␞%s␞%s::%s()::%s␞%s\n" "$date" "$tag" "$self" "$caller" "$line" "$string" >> "$debug_log"
}
setup_dirs(){
    for dir in "$state_path" "$cache_path" "$share_path" "$helpers_path" "$freedesktop_path" "$config_path" "$log_path"; do
        if [[ ! -d $dir ]]; then
            mkdir -p "$dir"
        fi
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
    local path="$cache_path"
    if find "$path" -mindepth 1 -maxdepth 1 | read; then
        for file in $path/*; do
            rm "$file"
        done
        logger INFO "Wiped cache files"
    fi
}
print_config_vals(){
    local keys=(
    "branch"
    "seen_news"
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
        fdialog "Requires PyGObject"
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

#Last seen news item
seen_news="$seen_news"

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

#DZGUI source path
src_path="$src_path"
END
}
depcheck(){
    for dep in "${!deps[@]}"; do
        command -v "$dep" 2>&1>/dev/null
        if [[ $? -eq 1 ]]; then
            local msg="Requires $dep >= ${deps[$dep]}"
            raise_error_and_quit "$msg"
        fi
    done
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
Comment=$appname
Icon=$share_path/$appname
Categories=Game
END
}
freedesktop_dirs(){
    local version_url=$(format_version_url)
    local img_url="$stable_url/images"
    curl -s "$version_url" > "$script_path"
    chmod +x "$script_path"
    for i in dzgui grid.png hero.png logo.png; do
        curl -s "$img_url/$i" > "$share_path/$i"
    done
    write_desktop_file > "$freedesktop_path/$appname.desktop"
    [[ $is_steam_deck -eq 0 ]] && return
    write_desktop_file > "$HOME/Desktop/$appname.desktop"
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
    local version_url=$(format_version_url)
    local upstream=$(curl -Ls "$version_url" | awk -F= '/^version=/ {print $2}')
    logger INFO "Local branch: '$branch', local version: $version"
    if [[ $branch == "stable" ]]; then
        version_url="$stable_url/dzgui.sh"
    elif [[ $branch == "testing" ]]; then
        version_url="$testing_url/dzgui.sh"
    fi
    local upstream=$(curl -Ls "$version_url" | awk -F= '/^version=/ {print $2}')
    [[ ! -f "$freedesktop_path/$appname.desktop" ]] && freedesktop_dirs
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
    [[ $branch == "stable" ]] && mdbranch="dzgui"
    [[ $branch == "" ]] && mdbranch="testing"
    local md="https://raw.githubusercontent.com/$author/dztui/${mdbranch}/CHANGELOG.md"
    curl -Ls "$md" > "$state_path/CHANGELOG.md"
}
check_architecture(){
    local cpu=$(< /proc/cpuinfo grep "AMD Custom APU 0405")
    if [[ -n "$cpu" ]]; then
        is_steam_deck=1
        logger INFO "Setting architecture to 'Steam Deck'"
    else
        is_steam_deck=0
        logger INFO "Setting architecture to 'desktop'"
    fi
}
check_map_count(){
    [[ $is_steam_deck -eq 1 ]] && return 0
    local count=1048576
    local conf_file="/etc/sysctl.d/dayz.conf"
    if [[ -f $conf_file ]]; then
        logger DEBUG "System map count is already $count or higher"
        return 0
    fi
    qdialog "sudo password required to check system vm map count." "OK" "Cancel"
    if [[ $? -eq 0 ]]; then
        local pass
        logger INFO "Prompting user for sudo escalation"
        pass=$($steamsafe_zenity --password)
        if [[ $? -eq 1 ]]; then
            logger WARN "User aborted password prompt"
            return 1
        fi
        local ct=$(sudo -S <<< "$pass" sh -c "sysctl -q vm.max_map_count | awk -F'= ' '{print \$2}'")
        logger DEBUG "Old map count is $ct"
        local new_ct
        [[ $ct -lt $count ]] && ct=$count
        sudo -S <<< "$pass" sh -c "echo 'vm.max_map_count=$ct' > $conf_file"
        sudo sysctl -p "$conf_file"
        logger DEBUG "Updated map count to $count"
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
    fi
    logger INFO "Migrated old API file"
    [[ ! -f $hist_file ]] && return
    rm $hist_file
    logger INFO "Wiped old history file"
}
stale_symlinks(){
    local game_dir="$steam_path/steamapps/common/DayZ"
    for l in $(find "$game_dir" -xtype l); do
        logger DEBUG "Updating stale symlink '$l'"
        unlink $l
    done
}
check_news(){
    [[ $branch == "stable" ]] && news_url="$stable_url/news"
    [[ $branch == "testing" ]] && news_url="$testing_url/news"
    local result=$(curl -Ls "$news_url")
    local sum=$(<<< "$result" md5sum | awk '{print $1}')
    if [[ $sum != "$seen_news" ]]; then
        logger WARN "Local news checksum '$seen_news' != '$sum'"
        seen_news="$sum"
        update_config
        echo "$result"
    fi
}
local_latlon(){
    if [[ -z $(command -v dig) ]]; then
        local local_ip=$(curl -Ls "https://ipecho.net/plain")
    else
        local local_ip=$(dig -4 +short myip.opendns.com @resolver1.opendns.com)
    fi
    local url="http://ip-api.com/json/$local_ip"
    local res=$(curl -Ls "$url" | jq -r '"\(.lat)\n\(.lon)"')
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
        local msg="DZGUI already running ($pid)"
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
    [[ -d $helpers_path/a2s ]] && { logger INFO "A2S helper is current"; return 0; }
    local sha=c7590ffa9a6d0c6912e17ceeab15b832a1090640
    local author="yepoleb"
    local repo="python-a2s"
    local url="https://github.com/$author/$repo/tarball/$sha"
    local prefix="${author^}-$repo-${sha:0:7}"
    local file="$prefix.tar.gz"
    curl -Ls "$url" > "$helpers_path/$file"
    tar xf "$helpers_path/$file" -C "$helpers_path" "$prefix/a2s" --strip=1
    rm "$helpers_path/$file"
    logger INFO "Updated A2S helper to sha '$sha'"
}
fetch_dzq(){
    local sum="232f42b98a3b50a0dd6e73fee55521b2"
    local file="$helpers_path/a2s/dayzquery.py"
    if [[ -f $file ]] && [[ $(get_hash "$file") == $sum ]]; then
        logger INFO "DZQ is current"
        return 0
    fi
    local sha=ccc4f71b48610a1885706c9d92638dbd8ca012a5
    local author="yepoleb"
    local repo="dayzquery"
    local url="https://raw.githubusercontent.com/$author/$repo/$sha/dayzquery.py"
    curl -Ls "$url" > "$file"
    logger INFO "Updated DZQ to sha '$sha'"
}
fetch_helpers_by_sum(){
    declare -A sums
    sums=(
        ["ui.py"]="67d9b617cf53213965bebfc91aae1e6e"
        ["query_v2.py"]="1822bd1769ce7d7cb0d686a60f9fa197"
        ["vdf2json.py"]="2f49f6f5d3af919bebaab2e9c220f397"
        ["funcs"]="d9b0e6fa68314c18ac7aad565645948f"
    )
    local author="aclist"
    local repo="dztui"
    local branch="$branch"
    local file
    local sum
    local full_path

    for i in "${!sums[@]}"; do
        file="$i"
        sum="${sums[$i]}"
        full_path="$helpers_path/$file"
        url="https://raw.githubusercontent.com/$author/$repo/$branch/helpers/$file"
        if [[ -f "$full_path" ]] && [[ $(get_hash "$full_path") == $sum ]]; then
            logger INFO "'$file' is current"
        else
            logger WARN "File '$full_path' checksum != '$sum'"
            curl -Ls "$url" > "$full_path"
            if [[ ! $? -eq 0 ]]; then
                raise_error_and_quit "Failed to fetch the file '$file'. Possible timeout?"
            fi
            logger INFO "Updated '$full_path' to sum '$sum'"
        fi
        [[ $file == "funcs" ]] && chmod +x "$full_path"
    done
    return 0
}
fetch_geo_file(){
    # for binary releases
    local geo_sum="e7f3b25223ac4dfd5e30a0b55bb3ff6c"
    local km_sum="b038fdb8f655798207bd28de3a004706"
    local gzip="$helpers_path/ips.csv.gz"
    if [[ ! -f $geo_file  ]] || [[ $(get_hash $geo_file) != $geo_sum ]]; then
        curl -Ls "$geo_file_url" > "$gzip"
        #force overwrite
        gunzip -f "$gzip"
    fi
    if [[ ! -f $km_helper ]] || [[ $(get_hash $km_helper) != $km_sum ]]; then
        curl -Ls "$km_helper_url" > "$km_helper"
        chmod +x "$km_helper"
    fi
}
fetch_helpers(){
    fetch_a2s
    fetch_dzq
    fetch_geo_file
    fetch_helpers_by_sum
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
    [[ $code =~ 403 ]] && echo 1
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
        default_steam_path=$(find / -type d \( -path "/proc" -o -path "*/timeshift" -o -path \
            "/tmp" -o -path "/usr" -o -path "/boot" -o -path "/proc" -o -path "/root" \
            -o -path "/sys" -o -path "/etc" -o -path "/var" -o -path "/lost+found" \) -prune \
            -o -regex ".*/Steam/ubuntu12_32$" -print -quit 2>/dev/null | sed 's@/ubuntu12_32@@')
    }
    if [[ $is_steam_deck -eq 1 ]]; then
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

    for i in "$def_path" "$ubuntu_path" "$debian_path" "$flatpak_path"; do
        if [[ -d "$i" ]]; then
            default_steam_path="$i"
            return 0
        fi
    done

    local msg="Let DZGUI auto-discover Steam path (accurate, slower)\nSelect the Steam path manually (less accurate, faster)"
    echo -e "$msg" | $steamsafe_zenity --list \
        --column="Choice" \
        --title="DZGUI" \
        --hide-header \
        --text="Steam is not installed in a standard location." \
        $sd_res

    case "$res" in
        *auto*) discover ;;
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
    if [[ ! $? -eq 0 ]]; then
        logger WARN "Failed to parse Steam path using '$search_path'"
        return 1
    fi
    logger INFO "Steam path resolved to: $steam_path"
}
create_config(){
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
        #and mapfile does not support high ascii delimiters
        #so split fields with newline
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
                zenity --question --text="DayZ not found or not installed at the chosen path." --ok-label="Choose path manually" --cancel-label="Exit"
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
    local msg2="The Steam paths set in your config file appear to be invalid. Restart first-time setup now?"
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
    if [[ ! -d $steam_path ]] || [[ ! -d $game_dir ]]; then
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
    if [[ $src_path != $(realpath "$0") ]]; then
        src_path=$(realpath "$0")
        update_config
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
initial_setup(){
    setup_dirs
    setup_state_files
    depcheck
    check_pyver
    test_gobject
    watcher_deps
    check_architecture
    varcheck
    source "$config_file"
    lock
    legacy_vars
    check_version
    check_map_count
    steam_deps
    migrate_files
    stale_symlinks
    fetch_helpers > >(pdialog "Fetching additional helper files")
    local_latlon
    is_steam_running
    is_dzg_downloading
    print_config_vals
}
main(){
    local zenv=$(zenity --version 2>/dev/null)
    [[ -z $zenv ]] && { echo "Requires zenity <= 3.44.1"; exit 1; }

    printf "Initializing setup...\n"
    initial_setup
    local news=$(check_news)

    printf "All OK. Kicking off UI...\n"
    [[ -z $news ]] && news="null"
    python3 "$ui_helper" "--init-ui" "$news" "$version" "$is_steam_deck"
}
main
#TODO: tech debt: cruddy handling for steam forking
[[ $? -eq 1 ]] && pkill -f dzgui.sh
