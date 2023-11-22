#!/usr/bin/env bash

set -o pipefail
version=4.1.0-rc.1

aid=221100
game="dayz"
workshop="steam://url/CommunityFilePage/"
api="https://api.battlemetrics.com/servers"
sd_res="--width=1280 --height=800"
config_path="$HOME/.config/dztui/"
config_file="${config_path}dztuirc"
hist_file="${config_path}history"
tmp=/tmp/dzgui.tmp
fifo=/tmp/table.tmp
debug_log="$PWD/DZGUI_DEBUG.log"
separator="%%"
check_config_msg="Check config values and restart."
issues_url="https://github.com/aclist/dztui/issues"
url_prefix="https://raw.githubusercontent.com/aclist/dztui"
stable_url="$url_prefix/dzgui"
testing_url="$url_prefix/testing"
releases_url="https://github.com/aclist/dztui/releases/download/browser"
help_url="https://aclist.github.io/dzgui/dzgui"
sponsor_url="https://github.com/sponsors/aclist"
freedesktop_path="$HOME/.local/share/applications"
sd_install_path="$HOME/.local/share/dzgui"
helpers_path="$sd_install_path/helpers"
geo_file="$helpers_path/ips.csv"
km_helper="$helpers_path/latlon"
sums_path="$helpers_path/sums.md5"
scmd_file="$helpers_path/scmd.sh"
km_helper_url="$releases_url/latlon"
db_file="$releases_url/ips.csv.gz"
sums_url="$testing_url/helpers/sums.md5"
scmd_url="$testing_url/helpers/scmd.sh"
vdf2json_url="$testing_url/helpers/vdf2json.py"
notify_url="$testing_url/helpers/d.html"
notify_img_url="$testing_url/helpers/d.webp"
forum_url="https://github.com/aclist/dztui/discussions"
version_file="$config_path/versions"
steamsafe_zenity="/usr/bin/zenity"

update_last_seen(){
	mv $config_file ${config_path}dztuirc.old
	nr=$(awk '/seen_news=/ {print NR}' ${config_path}dztuirc.old)
	seen_news="seen_news=\"$sum\""
	awk -v "var=$seen_news" -v "nr=$nr" 'NR==nr {$0=var}{print}' ${config_path}dztuirc.old > $config_file
	source $config_file
}
check_news(){
	logger INFO "${FUNCNAME[0]}"
	echo "# Checking news"
	[[ $branch == "stable" ]] && news_url="$stable_url/news"
	[[ $branch == "testing" ]] && news_url="$testing_url/news"
	local result=$(curl -Ls "$news_url")
	sum=$(echo -n "$result" | md5sum | awk '{print $1}')
	logger INFO "News: $result"
}
print_news(){
	logger INFO "${FUNCNAME[0]}"
	if [[ $sum == $seen_news || -z $result ]]; then
		hchar=""
		news=""
	else
		hchar="─"
		news="$result\n$(awk -v var="$hchar" 'BEGIN{for(c=0;c<90;c++) printf var;}')\n"
		update_last_seen
	fi
}

declare -A deps
deps=([awk]="5.1.1" [curl]="7.80.0" [jq]="1.6" [tr]="9.0" [$steamsafe_zenity]="3.42.1" [fold]="9.0")
changelog(){
	build(){
        local mdbranch
        case "$branch" in
            "stable")
                mdbranch="dzgui"
                ;;
            *)
                mdbranch="testing"
                ;;
        esac
        local md="https://raw.githubusercontent.com/aclist/dztui/${mdbranch}/CHANGELOG.md"
        prefix="This window can be scrolled."
        echo $prefix
        echo ""
        curl -Ls "$md"
    }
	build | $steamsafe_zenity --text-info $sd_res --title="DZGUI" 2>/dev/null
}

depcheck(){
	for dep in "${!deps[@]}"; do
		command -v "$dep" 2>&1>/dev/null || (printf "Requires %s >=%s\n" "$dep" ${deps[$dep]}; exit 1)
	done
}
watcher_deps(){
	logger INFO "${FUNCNAME[0]}"
	if [[ ! $(command -v wmctrl) ]] && [[ ! $(command -v xdotool) ]]; then
		echo "100"
		warn "Missing dependency: requires 'wmctrl' or 'xdotool'.\nInstall from your system's package manager."
		logger ERROR "Missing watcher dependencies"
		exit 1
	fi
}
init_items(){
	#array order determines menu selector; this is destructive
    #change favorite index affects setup() and add_by_fav()
items=(
	"[Connect]"
	"	Server browser"
	"	My servers"
	"	Quick connect to favorite server"
	"	Connect by ID"
	"	Connect by IP"
	"	Recent servers (last 10)"
	"[Manage servers]"
	"	Add server by ID"
	"	Add server by IP"
	"	Add favorite server"
	"	Delete server"
	"[Options]"
	"	List installed mods"
	"	View changelog"
	"	Advanced options"
	"[Help]"
	"	Help file ⧉"
	"	Report bug ⧉"
	"	Forum ⧉"
	"	Sponsor ⧉"
	"	Hall of fame ⧉"
	)
}
warn(){
	$steamsafe_zenity --info --title="DZGUI" --text="$1" --width=500 --icon-name="dialog-warning" 2>/dev/null
}
info(){
	$steamsafe_zenity --info --title="DZGUI" --text="$1" --width=500 2>/dev/null
}
set_api_params(){
	logger INFO "${FUNCNAME[0]}"
	response=$(curl -s "$api" -H "Authorization: Bearer "$api_key"" -G -d "sort=-players" \
		-d "filter[game]=$game" -d "filter[ids][whitelist]=$list_of_ids")
	list_response=$response
	first_entry=1
}
write_config(){
cat	<<-END
#Path to DayZ installation
steam_path="$steam_path"

#Your unique API key
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
	END
}
write_desktop_file(){
cat	<<-END
[Desktop Entry]
Version=1.0
Type=Application
Terminal=false
Exec=$sd_install_path/dzgui.sh
Name=DZGUI
Comment=dzgui
Icon=$sd_install_path/dzgui
Categories=Game
	END
}
freedesktop_dirs(){
	mkdir -p "$sd_install_path"
	mkdir -p "$freedesktop_path"
	curl -s "$version_url" > "$sd_install_path/dzgui.sh"
	chmod +x "$sd_install_path/dzgui.sh"
	img_url="$testing_url/images"
	for i in dzgui grid.png hero.png logo.png; do
		curl -s "$img_url/$i" > "$sd_install_path/$i"
	done
	write_desktop_file > "$freedesktop_path/dzgui.desktop"
	if [[ $is_steam_deck -eq 1 ]]; then
		write_desktop_file > "$HOME/Desktop/dzgui.desktop"
	fi
}
find_library_folder(){
	logger INFO "${FUNCNAME[0]}"
	logger INFO "User picked directory: '$1'"
	steam_path="$(python3 "$helpers_path/vdf2json.py" -i "$1/steamapps/libraryfolders.vdf" | jq -r '.libraryfolders[]|select(.apps|has("221100")).path')"
	logger INFO "Steam path resolved to: $steam_path"
}
file_picker(){
	logger INFO "${FUNCNAME[0]}"
	local path=$($steamsafe_zenity --file-selection --directory 2>/dev/null)
	logger INFO "File picker path resolve to: $path"
	if [[ -z "$path" ]]; then
		logger INFO "Path was empty"
		return
	else
		default_steam_path="$path"
		find_library_folder "$default_steam_path"
	fi
}
create_config(){
	logger INFO "${FUNCNAME[0]}"
	check_pyver
	write_to_config(){
		mkdir -p $config_path
		write_config > $config_file
		info "Config file created at $config_file."
		source $config_file
	}
	while true; do
		player_input="$($steamsafe_zenity --forms --add-entry="Player name (required for some servers)" --add-entry="Steam API key" --add-entry="BattleMetrics API key (optional)" --title="DZGUI" --text="DZGUI" $sd_res --separator="@" 2>/dev/null)"
		#explicitly setting IFS crashes $steamsafe_zenity in loop
		#and mapfile does not support high ascii delimiters
		#so split fields with newline
		readarray -t args < <(echo "$player_input" | sed 's/@/\n/g')
		name="${args[0]}"
		steam_api="${args[1]}"
		api_key="${args[2]}"

		[[ -z $player_input ]] && exit
		if [[ -z $steam_api ]]; then
			warn "Steam API key cannot be empty"
            continue
		elif [[ $(test_steam_api) -eq 1 ]]; then
			warn "Invalid Steam API key"
            continue
        fi
		if [[ -n $api_key ]] && [[ $(test_bm_api $api_key) -eq 1 ]]; then
			warn "Invalid BM API key"
            continue
        fi
        while true; do
            logger INFO "steamsafe_zenity is $steamsafe_zenity"
            if [[ -n $steam_path ]]; then
                write_to_config
                return
            fi
            find_default_path
            find_library_folder "$default_steam_path"
            if [[ -z $steam_path ]]; then
                logger WARN "Steam path was empty"
                zenity --question --text="DayZ not found or not installed at the chosen path." --ok-label="Choose path manually" --cancel-label="Exit"
                if [[ $? -eq 0 ]]; then
                    logger INFO "User selected file picker"
                    file_picker
                else
                    exit
                fi
            else
                write_to_config
                return
            fi
        done
	done

}
err(){
	printf "[ERROR] %s\n" "$1"
}
varcheck(){
	if [[ ! -d $steam_path ]] || [[ ! -d $game_dir ]]; then
		echo 1
	fi
}
run_depcheck(){
	logger INFO "${FUNCNAME[0]}"
	if [[ -n $(depcheck) ]]; then
		echo "100"
		logger ERROR "Missing dependencies, quitting"
		$steamsafe_zenity --warning --ok-label="Exit" --title="DZGUI" --text="$(depcheck)"
		exit
	fi
}
logger(){
	local date="$(date "+%F %T")"
	local tag="$1"
	local string="$2"
	printf "[%s] [%s] %s\n" "$date" "$tag" "$string" >> "$debug_log"
}
check_pyver(){
	pyver=$(python3 --version | awk '{print $2}')
	if [[ -z $pyver ]] || [[ ${pyver:0:1} -lt 3 ]]; then
		warn "Requires python >=3.0" &&
		exit
	fi
}
run_varcheck(){
	logger INFO "${FUNCNAME[0]}"
	source $config_file
	workshop_dir="$steam_path/steamapps/workshop/content/$aid"
	game_dir="$steam_path/steamapps/common/DayZ"
	if [[ $(varcheck) -eq 1 ]]; then
		$steamsafe_zenity --question --cancel-label="Exit" --text="Malformed config file. This is probably user error.\nStart first-time setup process again?" --width=500 2>/dev/null
		code=$?
		if [[ $code -eq 1 ]]; then
			logger ERROR "Malformed config vars"
			exit
		else
			create_config
		fi
	fi
}
config(){
	logger INFO "${FUNCNAME[0]}"
	if [[ ! -f $config_file ]]; then
		logger WARN "Config file missing"
		logger INFO "steamsafe_zenity is $steamsafe_zenity"
		$steamsafe_zenity --width=500 --info --text="Config file not found. Click OK to proceed to first-time setup." 2>/dev/null
		code=$?
		logger INFO "Return code $code"
		#TODO: prevent progress if user hits ESC
		if [[ $code -eq 1 ]]; then
			exit
		else
			create_config
		fi
	else
		source $config_file
	fi

}
steam_deck_mods(){	
	until [[ -z $diff ]]; do
		next=$(echo -e "$diff" | head -n1)
		$steamsafe_zenity --question --ok-label="Open" --cancel-label="Cancel" --title="DZGUI" --text="Missing mods. Click [Open] to open mod $next in Steam Workshop and subscribe to it by clicking the green Subscribe button. After the mod is downloaded, return to this menu to continue validation." --width=500 2>/dev/null
		rc=$?
		if [[ $rc -eq 0 ]]; then
			echo "[DZGUI] Opening ${workshop}$next"
			$steam_cmd steam://url/CommunityFilePage/$next 2>/dev/null &
			$steamsafe_zenity --info --title="DZGUI" --ok-label="Next" --text="Click [Next] to continue mod check." --width=500 2>/dev/null
		else
			return 1
		fi
		compare
	done
}
test_display_mode(){
	pgrep -a gamescope | grep -q "generate-drm-mode"
	[[ $? -eq 0 ]] && gamemode=1
}
foreground(){
	if [[ $(command -v wmctrl) ]]; then
    	wmctrl -a "DZG Watcher"
	else
		local window_id=$(xdotool search --name "DZG Watcher")
		xdotool windowactivate $window_id
	fi
}
manual_mod_install(){
    local ip="$1"
    local gameport="$2"

	[[ $is_steam_deck -eq 1 ]] && test_display_mode
	if [[ $gamemode -eq 1 ]]; then
        popup 1400
        return
	fi
    local ex="/tmp/dzc.tmp"
    [[ -f $ex ]] && rm $ex
    watcher(){	
    readarray -t stage_mods <<< "$diff"
    for((i=0;i<${#stage_mods[@]};i++)); do
        [[ -f $ex ]] && return 1
        local downloads_dir="$steam_path/steamapps/workshop/downloads/$aid"
        local workshop_dir="$steam_path/steamapps/workshop/content/$aid"
        $steam_cmd "steam://url/CommunityFilePage/${stage_mods[$i]}"
        echo "# Opening workshop page for ${stage_mods[$i]}. If you see no progress after subscribing, try unsubscribing and resubscribing again until the download commences."
        sleep 1s
        foreground
        until [[ -d $downloads_dir/${stage_mods[$i]} ]]; do
            [[ -f $ex ]] && return 1
            sleep 0.1s
            if [[ -d $workshop_dir/${stage_mods[$i]} ]]; then
                break
            fi
        done
        foreground
        echo "# Steam is downloading ${stage_mods[$i]} (mod $((i+1)) of ${#stage_mods[@]})"
        until [[ -d $workshop_dir/${stage_mods[$i]} ]]; do
            [[ -f $ex ]] && return 1
            sleep 0.1s
        done
        foreground
        echo "# ${stage_mods[$i]} moved to mods dir"
    done
    echo "100"
    }
    watcher > >($steamsafe_zenity --pulsate --progress --auto-close --title="DZG Watcher" --width=500 2>/dev/null; rc=$?; [[ $rc -eq 1 ]] && touch $ex)
    compare
    if [[ -z $diff ]]; then
        passed_mod_check > >($steamsafe_zenity --pulsate --progress --auto-close --width=500 2>/dev/null)
        launch "$ip" "$gameport"
    else
        return 1
    fi
}
encode(){
	echo "$1" | md5sum | cut -c -8
}
stale_symlinks(){
	logger INFO "${FUNCNAME[0]}"
	for l in $(find "$game_dir" -xtype l); do
		unlink $l
	done
}
legacy_symlinks(){
	for d in "$game_dir"/*; do
		if [[ $d =~ @[0-9]+-.+ ]]; then
			unlink "$d"
		fi
	done
	for d in "$workshop_dir"/*; do
		local id=$(awk -F"= " '/publishedid/ {print $2}' "$d"/meta.cpp | awk -F\; '{print $1}')
		local encoded_id=$(echo "$id" | awk '{printf("%c",$1)}' | base64 | sed 's/\//_/g; s/=//g; s/+/]/g')
		if [[ -h "$game_dir/@$encoded_id" ]]; then
			unlink "$game_dir/@$encoded_id"
		fi
	done
}
symlinks(){
	for d in "$workshop_dir"/*; do
		id=$(awk -F"= " '/publishedid/ {print $2}' "$d"/meta.cpp | awk -F\; '{print $1}')
		encoded_id=$(encode "$id")
		mod=$(awk -F\" '/name/ {print $2}' "$d"/meta.cpp | sed -E 's/[^[:alpha:]0-9]+/_/g; s/^_|_$//g')
		link="@$encoded_id"
		if [[ -h "$game_dir/$link" ]]; then
			:
		else
			printf "[DZGUI] Creating symlink for $mod\n"
			ln -fs "$d" "$game_dir/$link"
		fi
	done
}
passed_mod_check(){
	echo "[DZGUI] Passed mod check"
	echo "# Preparing symlinks"
	legacy_symlinks
	symlinks
	echo "100"

}
auto_mod_install(){
    local ip="$1"
    local gameport="$2"
	popup 300
	rc=$?
	if [[ $rc -eq 1 ]]; then
        manual_mod_install "$ip" "$gameport"
        return
    fi
    log="$default_steam_path/logs/content_log.txt"
    [[ -f "/tmp/dz.status" ]] && rm "/tmp/dz.status"
    touch "/tmp/dz.status"
    console_dl "$diff" &&
    $steam_cmd steam://open/downloads && 2>/dev/null 1>&2
    foreground
    until [[ -z $(comm -23 <(printf "%s\n" "${modids[@]}" | sort) <(ls -1 $workshop_dir | sort)) ]]; do
        local missing=$(comm -23 <(printf "%s\n" "${modids[@]}" | sort) <(ls -1 $workshop_dir | sort) | wc -l)
        echo "# Downloaded $((${#modids[@]}-missing)) of ${#modids[@]} mods. ESC cancels"
    done | $steamsafe_zenity --pulsate --progress --title="DZG Watcher" --auto-close --no-cancel --width=500 2>/dev/null
    compare
    [[ $force_update -eq 1 ]] && { unset force_update; return; }
    if [[ -z $diff ]]; then
        check_timestamps
        passed_mod_check > >($steamsafe_zenity --pulsate --progress --title="DZGUI" --auto-close --width=500 2>/dev/null)
        launch "$ip" "$gameport"
    else
        manual_mod_install "$ip" "$gameport"
    fi
}
get_local_stamps(){
	concat(){
	for ((i=0;i<$max;i++)); do
	   echo "publishedfileids[$i]=${local_modlist[$i]}&"
	done | awk '{print}' ORS=''
	}
	payload(){
		echo -e "itemcount=${max}&$(concat)"
	}
	post(){
		curl -s -X POST -H "Content-Type:application/x-www-form-urlencoded" \
		-d "$(payload)" 'https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/?format=json'
	}
	post
}
update_stamps(){
	for((i=0;i<${#local_modlist[@]};i++)); do
		mod=${local_modlist[$i]}
		stamp=${stamps[$i]}
		printf "%s\t%s\n" "$mod" "$stamp" >> $version_file
	done
}
check_timestamps(){
	readarray -t local_modlist < <(ls -1 $workshop_dir)
	max=${#local_modlist[@]}
	[[ $max -eq 0 ]] && return
	readarray -t stamps < <(get_local_stamps | jq -r '.response.publishedfiledetails[].time_updated')
	if [[ ! -f $version_file ]]; then
		update_stamps
		return
	else
		needs_update=()
		for((i=0;i<${#local_modlist[@]};i++)); do
			mod=${local_modlist[$i]}
			stamp=${stamps[$i]}
			if [[ ! $(awk -v var=$mod '$1 == var' $version_file) ]]; then
				echo -e "$mod\t$stamp" >> $version_file
			elif [[ $(awk -v var=$mod -v var2=$stamp '$1 == var && $2 == var2' $version_file) ]]; then
				:
			else
				awk -v var=$mod -v var2=$stamp '$1 == var {$2=var2;print $1"\t"$2; next;};{print}' $version_file > $version_file.new
				mv $version_file.new $version_file
				needs_update+=($mod)
			fi
		done
	fi
}
merge_modlists(){
    echo "# Aligning modlists"
	[[ $force_update -eq 1 ]] && echo "# Checking mod versions"
	check_timestamps
	if [[ -z "$diff" ]] && [[ ${#needs_update[@]} -gt 0 ]]; then
		diff=$(printf "%s\n" "${needs_update[@]}")
	elif [[ -z "$diff" ]] && [[ ${#needs_update[@]} -eq 0 ]]; then
		diff=
	elif [[ -n "$diff" ]] && [[ ${#needs_update[@]} -eq 0 ]]; then
		:
	else
		diff="$(printf "%s\n%s\n" "$diff" "${needs_update[@]}")"
	fi
	[[ $force_update -eq 1 ]] && echo "100"
}
update_history(){
    local ip="$1"
    local gameport="$2"
    local qport="$3"
	[[ -n $(grep "$ip:$gameport:$qport" $hist_file) ]] && return
	if [[ -f $hist_file ]]; then
		old=$(tail -n9 "$hist_file")
		old="$old\n"
	fi
	echo -e "${old}${ip}:${gameport}:${qport}" > "$hist_file"
}
connect(){
	local ip=$1
	local gameport=$2
    local qport=$3
    logger INFO "Querying $ip:$gameport:$qport"
    connect_dialog(){
        echo "# Querying modlist"
        local remote
        remote=$(a2s "$ip" "$qport" rules)
        if [[ $? -eq 1 ]]; then
            echo "100"
            popup 1200
            return 1
        fi
        logger INFO "Server returned modlist: $(<<< $remote tr '\n' ' ')"
        echo "# Checking for defunct mods"
        query_defunct "$remote"
    }
    (connect_dialog "$ip" "$qport") | pdialog
	rc=$?
	[[ $rc -eq 1 ]] && return
	readarray -t newlist < /tmp/dz.modlist
    compare
    [[ $auto_install -eq 2 ]] && merge_modlists > >(pdialog)
	if [[ -n $diff ]]; then
		case $auto_install in
			1|2) auto_mod_install "$ip" "$gameport" ;;
			*) manual_mod_install "$ip" "$gameport" ;;
		esac
	else
		passed_mod_check > >(pdialog)
		update_history "$ip" "$gameport" "$qport"
		launch "$ip" "$gameport" "$qport"
	fi
}
update_config(){
    mv $config_file ${config_file}.old
    write_config > $config_file
    source $config_file
}
prepare_ip_list(){
    local res="$1"
	local ct=$(<<< "$res" jq '[.response.servers[]]|length' 2>/dev/null)
	if [[ -n $ct ]]; then
		for((i=0;i<$ct;i++));do
            readarray -t json_arr < <(<<< $res jq --arg i $i -r '[.response.servers[]][($i|tonumber)]|"\(.name)\n\(.addr)\n\(.players)\n\(.max_players)\n\(.gameport)\n\(.gametype)"')
            local name=${json_arr[0]}
            local addr=${json_arr[1]}
            local ip=$(<<< $addr awk -F: '{print $1}')
            local qport=$(<<< $addr awk -F: '{print $2}')
            local current=${json_arr[2]}
            local max=${json_arr[3]}
            local players="${current}/${max}"
            local gameport="${json_arr[4]}"
            local gametime="${json_arr[5]}"
            gametime=$(<<< "$gametime" grep -o '[0-9][0-9]:[0-9][0-9]')

			echo "$name"
			echo "${ip}:${gameport}"
			echo "$players"
			echo "$gametime"
			echo "$qport"
		done
	fi
}
ip_table(){
    local sel
    local res="$1"
	while true; do
        sel=$(prepare_ip_list "$res" | $steamsafe_zenity --width 1200 --height 800 --text="Multiple maps found at this server. Select map from the list below" --title="DZGUI" --list --column=Name --column=IP --column=Players --column=Gametime --column=Qport --print-column=1,2,5 --separator=%% 2>/dev/null)
        [[ $? -eq 1 ]] && return 1
        echo "$sel"
        return 0
	done
}
fetch_ip_metadata(){
    local ip="$1"
	source $config_file
	local url="https://api.steampowered.com/IGameServersService/GetServerList/v1/?filter=\appid\221100\gameaddr\\$ip&key=$steam_api"
	curl -Ls "$url"
}

#TODO: local servers
#local_ip(){
#(^127\.)|(^10\.)|(^172\.1[6-9]\.)|(^172\.2[0-9]\.)|(^172\.3[0-1]\.)|(^192\.168\.)
#}
test_steam_api(){
	local url="https://api.steampowered.com/IGameServersService/GetServerList/v1/?filter=\appid\221100&limit=10&key=$steam_api"
	local code=$(curl -ILs "$url" | grep -E "^HTTP")
	[[ $code =~ 403 ]] && echo 1
	[[ $code =~ 200 ]] && echo 0
}
test_bm_api(){
    local api_key="$1"
    [[ -z $api_key ]] && return 1
	local code=$(curl -ILs "$api" -H "Authorization: Bearer "$api_key"" -G \
		-d "filter[game]=$game" | grep -E "^HTTP")
	[[ $code =~ 401 ]] && echo 1
	[[ $code =~ 200 ]] && echo 0
}
add_steam_api(){
		[[ $(test_steam_api) -eq 1 ]] && return 1
		mv $config_file ${config_path}dztuirc.old
		nr=$(awk '/steam_api=/ {print NR}' ${config_path}dztuirc.old)
		steam_api="steam_api=\"$steam_api\""
		awk -v "var=$steam_api" -v "nr=$nr" 'NR==nr {$0=var}{print}' ${config_path}dztuirc.old > ${config_path}dztuirc
		echo "[DZGUI] Added Steam API key"
		$steamsafe_zenity --info --title="DZGUI" --text="Added Steam API key to:\n\n${config_path}dztuirc\nIf errors occur, you can restore the file:\n${config_path}dztuirc.old" --width=500 2>/dev/null
		source $config_file
}
check_steam_api(){
	if [[ -z $steam_api ]]; then
		steam_api=$($steamsafe_zenity --entry --text="Key 'steam_api' not present in config file. Enter Steam API key:" --title="DZGUI" 2>/dev/null)
		if [[ $? -eq 1 ]] ; then
			return
		elif [[ ${#steam_api} -lt 32 ]] || [[ $(test_steam_api) -eq 1 ]]; then
			$steamsafe_zenity --warning --title="DZGUI" --text="Check API key and try again." 2>/dev/null
			return 1
		else
			add_steam_api
		fi
	fi
}
validate_ip(){
	echo "$1" | grep -qP '^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}$'
}
connect_by_id(){
    local ip
    ip=$(add_by_id "connect")
    [[ $? -eq 1 ]] && return
    readarray -t address < <(format_config_address "$ip")
    local ip="${address[0]}"
    local gameport="${address[1]}"
    local qport="${address[2]}"
    unset address

    connect "$ip" "$gameport" "$qport"
}
connect_by_ip(){
    local sel
    sel=$(parse_ips)
    [[ -z $sel ]] && return

    readarray -t address < <(format_table_results "$sel")
    local ip="${address[1]}"
    local gameport="${address[2]}"
    local qport="${address[3]}"

    connect "$ip" "$gameport" "$qport"
}
parse_ips(){
	source $config_file
	check_steam_api
	[[ $? -eq 1 ]] && return
    while true; do
        local ip
        ip=$($steamsafe_zenity --entry --text="Enter server IP (omit port)" --title="DZGUI" 2>/dev/null)
        [[ $? -eq 1 ]] && return 1
        [[ $ip =~ ':' ]] && continue
        if validate_ip "$ip"; then
            local res
            res=$(fetch_ip_metadata "$ip")
            if [[ ! $? -eq 0 ]] || [[ $(<<< $res jq '.response|length') -eq 0 ]]; then
                warn "Failed to retrieve IP metadata. Check IP or API key and try again."
                return 1
            fi
            local ct=$(<<< "$res" jq '.response.servers|length')
            if [[ $ct -eq 1 ]]; then
                local name=$(<<< $res jq -r '.response.servers[].name')
                local address=$(<<< $res jq -r '.response.servers[].addr')
                local ip=$(<<< "$address" awk -F: '{print $1}')
                local qport=$(<<< "$address" awk -F: '{print $2}')
                local gameport=$(<<< $res jq -r '.response.servers[].gameport')
                echo "${name}%%${ip}:${gameport}%%${qport}"
                return 0
            fi
            ip_table "$res"
            return 0
        else
            warn "Invalid IP"
        fi
    done
}
query_defunct(){
	readarray -t modlist <<< "$@"
	local max=${#modlist[@]}
	concat(){
		for ((i=0;i<$max;i++)); do
			echo "publishedfileids[$i]=${modlist[$i]}&"
		done | awk '{print}' ORS=''
	}
	payload(){
		echo -e "itemcount=${max}&$(concat)"
	}
	post(){
		curl -s \
        -X POST \
        -H "Content-Type:application/x-www-form-urlencoded"\
        -d "$(payload)" 'https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/?format=json'
	}
	local result=$(post | jq -r '.[].publishedfiledetails[] | select(.result==1) | "\(.file_size) \(.publishedfileid)"')
    <<< "$result" awk '{print $2}' > /tmp/dz.modlist
}
server_modlist(){
	for i in "${newlist[@]}"; do
		printf "$i\n"
	done
}
compare(){
	diff=$(comm -23 <(server_modlist | sort -u) <(installed_mods | sort))
}

installed_mods(){
	ls -1 "$workshop_dir"
}
concat_mods(){
    readarray -t serv <<< "$(server_modlist)"
    for i in "${serv[@]}"; do
        id=$(awk -F"= " '/publishedid/ {print $2}' "$workshop_dir"/$i/meta.cpp | awk -F\; '{print $1}')
        encoded_id=$(encode $id)
        link="@$encoded_id;"
        echo -e "$link"
    done | tr -d '\n' | perl -ple 'chop'
}
launch(){
    local ip="$1"
    local gameport="$2"
    local qport="$3"
    source $config_file
	mods=$(concat_mods)
    if [[ ! ${ip_list[@]} =~ "$ip:$gameport:$qport" ]]; then
        qdialog "Before connecting, add this server to My Servers?"
        if [[ $? -eq 0 ]]; then
            ip_list+=("$ip:$gameport:$qport")
            update_config
        fi
    fi
	if [[ $debug -eq 1 ]]; then
		launch_options="$steam_cmd -applaunch $aid -connect=$ip:$gameport -nolauncher -nosplash -name=$name -skipintro \"-mod=$mods\""
		print_launch_options="$(printf "This is a dry run.\nThese options would have been used to launch the game:\n\n$launch_options\n" | fold -w 60)"
		$steamsafe_zenity --question --title="DZGUI" --ok-label="Write to file" --cancel-label="Back"\
			--text="$print_launch_options" 2>/dev/null
		if [[ $? -eq 0 ]]; then
			source_script=$(realpath "$0")
			source_dir=$(dirname "$source_script")
			echo "$launch_options" > "$source_dir"/options.log
			echo "[DZGUI] Wrote launch options to $source_dir/options.log"
			$steamsafe_zenity --info --width=500 --title="DZGUI" --text="Wrote launch options to \n$source_dir/options.log" 2>/dev/null
		fi
	else
		$steamsafe_zenity --width=500 --title="DZGUI" --info --text="Launch conditions satisfied.\nDayZ will now launch after clicking [OK]." 2>/dev/null
		$steam_cmd -applaunch $aid -connect=$ip:$gameport -nolauncher -nosplash -skipintro -name=$name \"-mod=$mods\"
	fi
}
browser(){
	if [[ $is_steam_deck -eq 1 ]]; then
		steam steam://openurl/"$1" 2>/dev/null
	elif [[ $is_steam_deck -eq 0 ]]; then
		if [[ -n "$BROWSER" ]]; then
			"$BROWSER" "$1" 2>/dev/null
		else
			xdg-open "$1" 2>/dev/null
		fi
	fi
}
report_bug(){
	browser "$issues_url"
}
forum(){
	browser "$forum_url"
}
help_file(){
	browser "$help_url"
}
sponsor(){
	browser "$sponsor_url"
}
hof(){
	browser "${help_url}#_hall_of_fame"
}
set_mode(){
	logger INFO "${FUNCNAME[0]}"
	if [[ $debug -eq 1 ]]; then
		mode=debug
	else
		mode=normal
	fi
	logger INFO "Mode is $mode"
}
delete_by_ip(){
    local to_delete="$1"
    for (( i=0; i<${#ip_list[@]}; ++i )); do
        if [[ ${ip_list[$i]} == "$to_delete" ]]; then
            unset ip_list[$i]
        fi
    done
    if [[ ${#ip_list} -gt 0 ]]; then
        readarray -t ip_list < <(printf "%s\n" "${ip_list[@]}")
    fi
    update_config
    info "Removed $to_delete from:\n${config_path}dztuirc\nIf errors occur, you can restore the file:\n${config_path}dztuirc.old"
}
format_table_results(){
    local sel="$1"
	local name=$(<<< "$sel" awk -F"%%" '{print $1}')
	local address=$(<<< "$sel" awk -F"%%" '{print $2}')
	local ip=$(<<< "$address" awk -F":" '{print $1}')
	local gameport=$(<<< "$address" awk -F":" '{print $2}')
	local qport=$(<<< "$sel" awk -F"%%" '{print $3}')
    printf "%s\n%s\n%s\n%s\n" "$name" "$ip" "$gameport" "$qport"
}
delete_or_connect(){
    local sel="$1"
    local mode="$2"

    readarray -t address < <(format_table_results "$sel")
    local server_name="${address[0]}"
    local ip="${address[1]}"
    local gameport="${address[2]}"
    local qport="${address[3]}"
    unset address

	case "$mode" in
        "delete")
            qdialog "Delete this server?\n$server_name"
            [[ $? -eq 1 ]] && return

            delete_by_ip "$ip:$gameport:$qport"
            source $config_file

            local str="^$ip:$gameport$"
            local nr=$(awk -v v="$str" '$1 ~ v {print NR}' $tmp)
            local st=$((nr-1))
            local en=$((st+5))
            sed -i "${st},${en}d" $tmp
           # if [[ ${#ip_list[@]} -eq 0 ]]; then
           #     return 1
           # fi
            ;;
	    "connect"|"history")
    		connect "$ip" "$gameport" "$qport"
            return
    esac
}
populate(){
    local switch="$1"
	while true; do
		cols="--column="Server" --column="IP" --column="Players" --column="Gametime" --column="Distance" --column="Qport""
        set_header "$switch"
		rc=$?
		if [[ $rc -eq 0 ]]; then
			if [[ -z $sel ]]; then
				warn "No item was selected."
			else
				delete_or_connect "$sel" "$switch"
			fi
		else
			return 1
		fi
	done
}
list_mods(){
	if [[ -z $(installed_mods) ]] || [[ -z $(find $workshop_dir -maxdepth 2 -name "*.cpp" | grep .cpp) ]]; then
		$steamsafe_zenity --info --text="94: No mods currently installed or incorrect path given" $sd_res 2>/dev/null
	else
		for d in $(find $game_dir/* -maxdepth 1 -type l); do
			dir=$(basename $d)
			awk -v d=$dir -F\" '/name/ {printf "%s\t%s\t", $2,d}' "$gamedir"/$d/meta.cpp
			printf "%s\n" "$(basename $(readlink -f $game_dir/$dir))"
		done | sort -k1
	fi
}
connect_to_fav(){
    #TODO: test with broken/bogus fav
    #TODO: test backing out of connection dialogs
	logger INFO "${FUNCNAME[0]}"

    local fav="$1"
    [[ -z $fav ]] && { popup 1300; return; }

    readarray -t address < <(format_config_address "$fav")
    local ip="${address[0]}"
    local gameport="${address[1]}"
    local qport="${address[2]}"

    unset address
    connect "$ip" "$gameport" "$qport"
    [[ $? -eq 1 ]] && return 1
}
set_header(){
    local switch="$1"
	logger INFO "${FUNCNAME[0]}"
	logger INFO "Header mode is $1"
	print_news
	[[ $auto_install -eq 2 ]] && install_mode="auto"
	[[ $auto_install -eq 1 ]] && install_mode="headless"
	[[ $auto_install -eq 0 ]] && install_mode=manual
    case "$switch" in
        "delete")
        [[ -z $(< $tmp) ]] && return 1
        sel=$(< $tmp $steamsafe_zenity $sd_res --list $cols --title="DZGUI" \
        --text="DZGUI $version | Mode: $mode | Branch: $branch | Mods: $install_mode | Fav: $fav_label" \
        --separator="$separator" --print-column=1,2,6 --ok-label="Delete" 2>/dev/null)
        ;;

        "connect"|"history")
        sel=$(< $tmp $steamsafe_zenity $sd_res --list $cols --title="DZGUI" \
        --text="DZGUI $version | Mode: $mode | Branch: $branch | Mods: $install_mode | Fav: $fav_label" \
        --separator="$separator" --print-column=1,2,6 --ok-label="Connect" 2>/dev/null)
        ;;

        "main_menu")
        sel=$($steamsafe_zenity $sd_res --list --title="DZGUI" \
        --text="${news}DZGUI $version | Mode: $mode | Branch: $branch | Mods: $install_mode | Fav: $fav_label" \
        --cancel-label="Exit" --ok-label="Select" --column="Select launch option" --hide-header "${items[@]}" 2>/dev/null)
        ;;
    esac
}
toggle_branch(){
	mv $config_file ${config_path}dztuirc.old
	nr=$(awk '/branch=/ {print NR}' ${config_path}dztuirc.old)
	if [[ $branch == "stable"  ]]; then
		branch="testing"
	else
		branch="stable"
	fi
	flip_branch="branch=\"$branch\""
	awk -v "var=$flip_branch" -v "nr=$nr" 'NR==nr {$0=var}{print}' ${config_path}dztuirc.old > $config_file
	source $config_file
}
generate_log(){
	cat <<-DOC
	Distro: $(< /etc/os-release grep -w NAME | awk -F\" '{print $2}')
	Kernel: $(uname -mrs)
	Version: $version
	Branch: $branch
	Mode: $mode
	Auto: $auto_hr
	Whitelist: $whitelist
	Steam path: $steam_path
	Workshop path: $workshop_dir
	Game path: $game_dir

	Mods:
	$(list_mods)
	DOC
}
focus_beta_client(){
	steam steam://open/library 2>/dev/null 1>&2 &&
	steam steam://open/console 2>/dev/null 1>&2 &&
	sleep 1s
	wid(){
		wmctrl -ilx |\
			awk 'tolower($3) == "steamwebhelper.steam"' |\
			awk '$5 ~ /^Steam|Steam Games List/' |\
			awk '{print $1}'
	}
	until [[ -n $(wid) ]]; do
		:
	done
	wmctrl -ia $(wid)
	sleep 0.1s
	wid=$(xdotool getactivewindow)
	local geo=$(xdotool getwindowgeometry $wid)
	local pos=$(<<< "$geo" awk 'NR==2 {print $2}' | sed 's/,/ /')
	local dim=$(<<< "$geo" awk 'NR==3 {print $2}' | sed 's/x/ /')
	local pos1=$(<<< "$pos" awk '{print $1}')
	local pos2=$(<<< "$pos" awk '{print $2}')
	local dim1=$(<<< "$dim" awk '{print $1}')
	local dim2=$(<<< "$dim" awk '{print $2}')
	local dim1=$(((dim1/2)+pos1))
	local dim2=$(((dim2/2)+pos2))
	xdotool mousemove $dim1 $dim2
	xdotool click 1
	sleep 0.5s
	xdotool key Tab
}
console_dl(){
	readarray -t modids <<< "$@"
	focus_beta_client
	sleep 1.5s
	for i in "${modids[@]}"; do
		xdotool type --delay 0 "workshop_download_item $aid $i"
		sleep 0.5s
		xdotool key Return
		sleep 0.5s
	done
}
find_default_path(){
	logger INFO "${FUNCNAME[0]}"
	discover(){
		echo "# Searching for Steam"
		default_steam_path=$(find / -type d \( -path "/proc" -o -path "*/timeshift" -o -path \
		"/tmp" -o -path "/usr" -o -path "/boot" -o -path "/proc" -o -path "/root" \
		-o -path "/sys" -o -path "/etc" -o -path "/var" -o -path "/lost+found" \) -prune \
		-o -regex ".*/Steam/ubuntu12_32$" -print -quit 2>/dev/null | sed 's@/ubuntu12_32@@')
	}
	if [[ $is_steam_deck -eq 1 ]]; then
		default_steam_path="$HOME/.local/share/Steam"
	else
		local def_path
		local ub_path
		local flat_path
		def_path="$HOME/.local/share/Steam"
		ub_path="$HOME/.steam/steam"
		flat_path="$HOME/.var/app/com.valvesoftware.Steam/data/Steam"

		if [[ -d "$def_path" ]]; then
			default_steam_path="$def_path"
		elif [[ -d "$ub_path" ]]; then
			default_steam_path="$ub_path"
		elif [[ -d $flat_path ]]; then
			default_steam_path="$flat_path"
		else
			local res=$(echo -e "Let DZGUI auto-discover Steam path (accurate, slower)\nSelect the Steam path manually (less accurate, faster)" | $steamsafe_zenity --list --column="Choice" --title="DZGUI" --hide-header --text="Steam is not installed in a standard location." $sd_res)
			case "$res" in
				*auto*) discover ;;
				*manual*)
					zenity --info --text="\nSelect the top-level entry point to the location where Steam (not DayZ)\nis installed and before entering the \"steamapps\" path.\n\nE.g., if Steam is installed at:\n\"/media/mydrive/Steam\"\n\nCorrect:\n- \"/media/mydrive/Steam\"\n\nIncorrect:\n- \"/media/mydrive/Steam/steamapps/common/DayZ\"\n- \"/media/mydrive/\"" --width=500 &&
					file_picker ;;
			esac
		fi
	fi
}
fold_message(){
	echo "$1" | fold -s -w40
}
popup(){
	pop(){
		$steamsafe_zenity --info --text="$1" --title="DZGUI" --width=500 2>/dev/null
	}
	case "$1" in
		100) pop "This feature requires xdotool and wmctrl.";;
		200) pop "This feature is not supported on Gaming Mode.";;
		300) pop "$(fold_message 'The Steam console will now open and briefly issue commands to download the workshop files, then return to the download progress page. Ensure that the Steam console has keyboard and mouse focus (keep hands off keyboard) while the commands are being issued. Depending on the number if mods, it may take some time to queue the downloads. If a popup or notification window steals focus, it could obstruct the process.')" ;;
		400) pop "$(fold_message 'Automod install enabled. Auto-downloaded mods will not appear in your Steam Workshop subscriptions, but DZGUI will track the version number of downloaded mods internally and trigger an update if necessary.')" ;;
		500) pop "$(fold_message 'Automod install disabled. Switched to manual mode.')" ;;
		600) pop "No preferred servers set." ;;
		700) pop "Toggled to Flatpak Steam." ;;
		800) pop "Toggled to native Steam." ;;
		900) pop "This feature is not supported on Steam Deck." ;;
		1000) pop "No recent history." ;;
		1100) pop "No results found." ;;
		1200) pop "Timed out. Server may be temporarily offline or not responding to queries." ;;
        1300) pop "No favorite server configured." ;;
        1400) pop "DZGUI must be run in Desktop Mode on Steam Deck." ;;
	esac
}
toggle_console_dl(){
	[[ $is_steam_deck -eq 1 ]] && { popup 900; return; }
	[[ ! $(command -v xdotool) ]] && { popup 100; return; }
	[[ ! $(command -v wmctrl) ]] && { popup 100; return; }
	mv $config_file ${config_path}dztuirc.old
	local nr=$(awk '/auto_install=/ {print NR}' ${config_path}dztuirc.old)
	if [[ $auto_install == "2"  ]]; then
		auto_install="0"
		popup 500
	else
		auto_install="2"
		popup 400
	fi
	local flip_state="auto_install=\"$auto_install\""
	awk -v "var=$flip_state" -v "nr=$nr" 'NR==nr {$0=var}{print}' ${config_path}dztuirc.old > $config_file
	source $config_file
}
force_update_mods(){
	if [[ -f $version_file ]]; then
		awk '{OFS="\t"}{$2="000"}1' $version_file > /tmp/versions
		mv /tmp/versions $version_file
	fi
}
toggle_steam_binary(){
	case "$steam_cmd" in
		steam)
			steam_cmd="flatpak run com.valvesoftware.Steam"
			update_steam_cmd
			popup 700
			;;
		flatpak*)
			steam_cmd="steam"
			update_steam_cmd
			popup 800;;
	esac
}
options_menu(){
    init_options_list(){
        source $config_file
        set_mode
        case "$auto_install" in
            0|1|"") auto_hr="OFF"; ;;
            2) auto_hr="ON"; ;;
        esac
        [[ -z $name ]] && name="null"
        debug_list=(
            "Toggle branch [current: $branch]"
            "Toggle debug mode [current: $mode]"
            "Toggle auto mod install [current: $auto_hr]"
            "Change player name [current: $name]"
            "Output system info"
            )
        #TODO: tech debt: drop old flags
        [[ $auto_install -eq 2 ]] || [[ $auto_install -eq 1 ]] && debug_list+=("Force update local mods")
        case "$steam_cmd" in
            steam) steam_hr=Steam ;;
            flatpak*) steam_hr=Flatpak ;;
        esac
        [[ $toggle_steam -eq 1 ]] && debug_list+=("Toggle native Steam or Flatpak [$steam_hr]")
    }
    while true; do
        init_options_list
        debug_sel=$($steamsafe_zenity --list --width=1280 --height=800 --column="Options" --title="DZGUI" --hide-header "${debug_list[@]}" 2>/dev/null)
        [[ -z $debug_sel ]] && return
        case "$debug_sel" in
            Toggle[[:space:]]branch*)
                enforce_dl=1
                toggle_branch &&
                check_version
                ;;
            Toggle[[:space:]]debug*) toggle_debug ;;
            "Output system info")
                    source_script=$(realpath "$0")
                    source_dir=$(dirname "$source_script")
                output(){
                    echo "# Generating log"
                    generate_log > "$source_dir/DZGUI.log"
                }
                (output) | pdialog
                [[ $? -eq 1 ]] && return
                info_dialog "Wrote log file to: $source_dir/DZGUI.log"
                ;;
            Toggle[[:space:]]auto*) toggle_console_dl ;;
            "Force update local mods")
                force_update=1
                force_update_mods
                (merge_modlists) | pdialog
                auto_mod_install
                ;;
            Toggle[[:space:]]native*) toggle_steam_binary ;;
            Change[[:space:]]player[[:space:]]name*) change_name
            ;;
        esac
    done
}
info_dialog(){
    local title="DZGUI"
    $steamsafe_zenity --info --width=500 --title="$title" --text="$1" 2>/dev/null
}
a2s(){
    local ip="$1"
    local qport="$2"
    local mode="$3"
    python3 $helpers_path/query.py "$ip" "$qport" "$mode"
}
format_config_address(){
    local address="$1"
    parse(){
        local ind="$1"
        <<< $address awk -F: "{print \$$ind}"
    }
    local ip=$(parse 1)
    local gameport=$(parse 2)
    local qport=$(parse 3)
    printf "%s\n%s\n%s" "$ip" "$gameport" "$qport"
}
query_and_connect(){
    source $config_file
    local switch="$1"
    local ips="$2"
    case "$switch" in
        "history")
            if [[ -z $2 ]]; then
                warn "No recent servers in history"
                return 1
            fi
            readarray -t ip_arr <<< "$ips"
            ;;
        "connect"|"delete")
            if [[ ${#ip_list[@]} -eq 0 ]]; then
                warn "No servers currently saved"
                return 1
            fi
            ips="$(printf "%s\n" "${ip_list[@]}")"
            readarray -t ip_arr <<< "$ips"
            ;;
    esac
	[[ ${#ip_arr[@]} -lt 1 ]] && { popup 600; return; }
    > $tmp
    q(){
    for (( i = 0; i < ${#ip_arr[@]}; ++i )); do

        local address="${ip_arr[$i]}"
        readarray -t address < <(format_config_address "$address")
        local ip="${address[0]}"
        local gameport="${address[1]}"
        local qport="${address[2]}"
        unset address

        local info
        echo "# Querying $ip:$qport"
        info=$(a2s "$ip" "$qport" info)
        [[ $? -eq 1 ]] && continue
        local keywords=$(<<< $info jq -r '.keywords')
        local vars=("name" "address" "count" "time" "dist" "qport")
        for j in ${vars[@]}; do
            local -n var=$j
            case "$j" in
                "time")
                    var=$(<<< "$keywords" grep -o '[0-9][0-9]:[0-9][0-9]')
                    ;;
                "name")
                    var=$(<<< "$info" jq -r --arg arg $j '.[$arg]')
                    if [[ "${#var}" -gt 50 ]]; then
        			    var="$(<<< "$var" awk '{print substr($0,1,50) "..."}')"
                    fi
                    ;;
                "dist")
                    check_geo_file
                    local_latlon
                    var=$(get_dist $(<<< $address awk -F: '{print $1}'))
                    ;;
                *)
                    var=$(<<< "$info" jq -r --arg arg $j '.[$arg]')
                    ;;
            esac
            printf "%s\n" "$var" >> $tmp
        done
            unset $j
    done
    }

	(q) | pdialog
	[[ $? -eq 1 ]] && return
	populate "$switch"
}
exclude_fpp(){
    response=$(<<< "$response" jq '[.[]|select(.gametype|split(",")|any(. == "no3rd")|not)]')
}
exclude_tpp(){
    response=$(<<< "$response" jq '[.[]|select(.gametype|split(",")|any(. == "no3rd"))]')
}
exclude_full(){
	response=$(echo "$response" | jq '[.[]|select(.players!=.max_players)]')
}
exclude_empty(){
	response=$(echo "$response" | jq '[.[]|select(.players!=0)]')
}
filter_maps(){
	echo "# Filtering maps"
	[[ $ret -eq 98 ]] && return
	local maps=$(echo "$response" | jq -r '.[].map//empty|ascii_downcase' | sort -u) 
	local map_ct=$(echo "$maps" | wc -l)
	local map_sel=$(echo "$maps" | $steamsafe_zenity --list --column="Check" --width=1200 --height=800 2>/dev/null --title="DZGUI" --text="Found $map_ct map types")
	echo "[DZGUI] Selected '$map_sel'"
	if [[ -z $map_sel ]]; then
		ret=97
		return
	fi
	echo "100"
	response=$(echo "$response" | jq --arg map "$map_sel" '[.[]|select(.map)//empty|select(.map|ascii_downcase == $map)]')
}
exclude_daytime(){
	response=$(echo "$response" | jq '[.[]|select(.gametype|test(",[0][6-9]:|,[1][0-6]:")|not)]')
}
exclude_nighttime(){
	response=$(echo "$response" | jq '[.[]|select(.gametype|test(",[1][7-9]:|,[2][0-4]:|[0][0-5]:")|not)]')
}
keyword_filter(){
	response=$(echo "$response" | jq --arg search "$search" '[.[]|select(.name|ascii_downcase | contains($search))]')
}
exclude_lowpop(){
	response=$(echo "$response" | jq '[.[]|select(.players > 9)]')
}
exclude_nonascii(){
	response=$(echo "$response" | jq -r '[.[]|select(.name|test("^([[:ascii:]])*$"))]')
}
strip_null(){
	response=$(echo "$response" | jq -r '[.[]|select(.map//empty)]')
}
local_latlon(){
	if [[ -z $(command -v dig) ]]; then
		local local_ip=$(curl -Ls "https://ipecho.net/plain")
	else
		local local_ip=$(dig -4 +short myip.opendns.com @resolver1.opendns.com)
	fi
	local url="http://ip-api.com/json/$local_ip"
	local res=$(curl -Ls "$url" | jq -r '"\(.lat),\(.lon)"')
	local_lat=$(echo "$res" | awk -F, '{print $1}')
	local_lon=$(echo "$res" | awk -F, '{print $2}')
}
disabled(){
	if [[ -z ${disabled[@]} ]]; then
		printf "%s" "-"
	else
		for((i=0;i<${#disabled[@]};i++)); do
			if [[ $i < $((${#disabled[@]}-1)) ]]; then
				printf "%s, " "${disabled[$i]}"
			else
				printf "%s" "${disabled[$i]}"
			fi

		done
	fi
}
pagination(){
	if [[ ${#qport[@]} -eq 1 ]]; then
		entry=server
	else
		entry=servers
	fi
	printf "DZGUI %s | " "$version"
	printf "Mode: %s |" "$mode"
	printf "Fav: %s " "$fav_label"
	printf "\nIncluded:  %s | " "$filters"
	printf "Excluded: %s " "$(disabled)"
	if [[ -n $search ]]; then
		printf "| Keyword:  %s " "$search"
	fi
	printf "\nReturned: %s %s of %s | " "${#qport[@]}" "$entry" "$total_servers"
	printf "Players in-game: %s" "$players_online"
}
check_geo_file(){
	local gzip="$helpers_path/ips.csv.gz"
	curl -Ls "$sums_url" > "$sums_path"
	cd "$helpers_path"
	md5sum -c "$sums_path" 2>/dev/null 1>&2
	local res=$?
	cd $OLDPWD
    [[ $res -eq 0 ]] && return
    update(){
        mkdir -p "$helpers_path"
        echo "# Fetching new geolocation DB"
        curl -Ls "$db_file" > "$gzip"
        echo "# Extracting coordinates"
        #force overwrite
        gunzip -f "$gzip"
        echo "# Preparing helper file"
        curl -Ls "$km_helper_url" > "$km_helper"
        chmod +x $km_helper
        echo "100"
    }
    update > >(pdialog)
}
choose_filters(){
	if [[ $is_steam_deck -eq 0 ]]; then
		sd_res="--width=1920 --height=1080"
	fi
	sels=$($steamsafe_zenity --title="DZGUI" --text="Server search" --list --checklist --column "Check" --column "Option" --hide-header TRUE "All maps (untick to select from map list)" TRUE "Daytime" TRUE "Nighttime" TRUE "1PP" TRUE "3PP" False "Empty" False "Full" TRUE "Low population" FALSE "Non-ASCII titles" FALSE "Keyword search" $sd_res 2>/dev/null)
	if [[ $sels =~ Keyword ]]; then
		local search
        while true; do
            search=$($steamsafe_zenity --entry --text="Search (case insensitive)" --width=500 --title="DZGUI" 2>/dev/null | awk '{print tolower($0)}')
            [[ $? -eq 1 ]] && return 1
            [[ -z $search ]] && warn "Cannot submit an empty keyword"
            [[ -n $search ]] && break
        done
	fi
	[[ -z $sels ]] && return
	echo "$sels" | sed 's/|/, /g;s/ (untick to select from map list)//'
    echo "$search"
}
get_dist(){
	local given_ip="$1"
	local network="$(<<< "$given_ip" awk -F. '{OFS="."}{print $1"."$2}')"
	local binary=$(grep -E "^$network\." $geo_file)
	local three=$(<<< $given_ip awk -F. '{print $3}')
	local host=$(<<< $given_ip awk -F. '{print $4}')
	local res=$(<<< "$binary" awk -F[.,] -v three=$three -v host=$host '$3 <=three && $7 >= three{if($3>three || ($3==three && $4 > host) || $7 < three || ($7==three && $8 < host)){next}{print}}' | awk -F, '{print $7,$8}')
	local remote_lat=$(<<< "$res" awk '{print $1}')
	local remote_lon=$(<<< "$res" awk '{print $2}')
	if [[ -z $remote_lat ]]; then
		local dist="Unknown"
		echo "$dist"
	else
		local dist=$($km_helper "$local_lat" "$local_lon" "$remote_lat" "$remote_lon")
		LC_NUMERIC=C printf "%05.0f %s" "$dist" "km"
	fi
}
prepare_filters(){
    local sels="$1"
    local search="$2"
	[[ ! "$sels" =~ "Full" ]] && { exclude_full; disabled+=("Full") ; }
	[[ ! "$sels" =~ "Empty" ]] && { exclude_empty; disabled+=("Empty") ; }
	[[ ! "$sels" =~ "Daytime" ]] && { exclude_daytime; disabled+=("Daytime") ; }
	[[ ! "$sels" =~ "Nighttime" ]] && { exclude_nighttime; disabled+=("Nighttime") ; }
	[[ ! "$sels" =~ "Low population" ]] && { exclude_lowpop; disabled+=("Low-pop") ; }
	[[ ! "$sels" =~ "Non-ASCII titles" ]] && { exclude_nonascii; disabled+=("Non-ASCII") ; }
	[[ ! "$sels" =~ "1PP" ]] && { exclude_fpp; disabled+=("FPP") ; }
	[[ ! "$sels" =~ "3PP" ]] && { exclude_tpp; disabled+=("TPP") ; }
	[[ -n "$search" ]] && keyword_filter
	strip_null
}
munge_servers(){
    local sels="$1"
    local search="$2"
    write_fifo(){
        [[ -p $fifo ]] && rm $fifo
        mkfifo $fifo
        local dist
        for((i=0;i<${#qport[@]};i++)); do
            dist=$(get_dist ${addr[$i]})

            printf  "%s\n%s\n%s\n%s\n%03d\n%03d\n%s\n%s:%s\n%s\n" "${name[$i]}" "${map[$i]}" "${fpp[$i]}" "${gametime[$i]}" \
            "${players[$i]}" "${max[$i]}" "$dist" "${addr[$i]}" "${gameport[$i]}" "${qport[$i]}" >> $fifo
        done
    }
	response="$(cat /tmp/dz.servers)"
	if [[ ! "$sels" =~ "All maps" ]]; then
		filter_maps > >(pdialog)
        [[ $? -eq 1 ]] && return
		disabled+=("All maps")
	fi
	[[ $ret -eq 97 ]] && return
	prepare_filters "$sels" "$search"
    [[ $? -eq 1 ]] && return
	if [[ $(echo "$response" | jq 'length') -eq 0 ]]; then
		$steamsafe_zenity --error --text="No matching servers" 2>/dev/null
		return
	fi
	#jq bug #1788, raw output (-r) cannot be used with ASCII
	local name=$(<<< "$response" jq -a '.[].name' | sed 's/\\u[0-9a-z]\{4\}//g;s/^"//;s/"$//')
	local map=$(<<< "$response" jq -r '.[].map|if type == "string" then ascii_downcase else "null" end')
    local gametime=$(<<< "$response" jq -r '.[]|(if .gametype == null then "null" else .gametype end)|scan("[0-9]{2}:[0-9]{2}$")')
    local fpp=$(<<< "$response" jq -r '.[].gametype|split(",")|if any(. == "no3rd") then "1PP" else "3PP" end')
	local players=$(<<< "$response" jq -r '.[].players')
	local max=$(<<< "$response" jq -r '.[].max_players')
	local addr=$(<<< "$response" jq -r '.[].addr|split(":")[0]')
	local gameport=$(<<< "$response" jq -r '.[]|(if .gameport == null then "null" else .gameport end)')
	local qport=$(<<< "$response" jq -r '.[].addr|split(":")[1]')

	readarray -t qport <<< $qport
	readarray -t gameport <<< $gameport
	readarray -t addr <<< $addr
	readarray -t name <<< $name
	readarray -t fpp <<< $fpp
	readarray -t players <<< $players
	readarray -t map <<< $map
	readarray -t max <<< $max
	readarray -t gametime <<< $gametime

	if [[ $is_steam_deck -eq 0 ]]; then
		sd_res="--width=1920 --height=1080"
	fi
	write_fifo &
	pid=$!
	local sel=$($steamsafe_zenity --text="$(pagination)" --title="DZGUI" --list --column=Name --column=Map --column=PP --column=Gametime --column=Players --column=Max --column=Distance --column=IP --column=Qport $sd_res --print-column=1,8,9 --separator=%% 2>/dev/null < <(while true; do cat $fifo; done))
	if [[ -z $sel ]]; then
		rm $fifo
		kill -9 $pid 2>/dev/null
        return 1
	else
		rm $fifo
		kill -9 $pid
		echo $sel
	fi
}
debug_servers(){
	debug_res=$(curl -Ls "https://api.steampowered.com/IGameServersService/GetServerList/v1/?filter=\appid\221100&limit=10&key=$steam_api")
	local len=$(<<< "$debug_res" jq '[.response.servers[]]|length')
	if [[ $len -eq 0 ]]; then
		return 1
	else
		return 0
	fi
}
server_browser(){
    unset ret
    local filters="$(<<< "$1" awk 'NR==1 {print $0}')"
    local keywords="$(<<< "$1" awk 'NR==2 {print $0}')"
    echo "# Checking Steam API"
    check_steam_api
    [[ $? -eq 1 ]] && return
    echo "# Checking geolocation file"
    check_geo_file
    echo "# Calculating server distances"
    local_latlon
	[[ $ret -eq 97 ]] && return

    local limit=20000
    local url="https://api.steampowered.com/IGameServersService/GetServerList/v1/?filter=\appid\221100&limit=$limit&key=$steam_api"

    echo "# Getting server list"
    curl -Ls "$url" | jq -r '.response.servers' > /tmp/dz.servers
	total_servers=$(< /tmp/dz.servers jq 'length' | numfmt --grouping)
	players_online=$(curl -Ls "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid=$aid" \
		| jq '.response.player_count' | numfmt --grouping)
	debug_servers
	[[ $? -eq 1 ]] && { popup 1100; return 1; }

    echo "100"
    local sel=$(munge_servers "$filters" "$keywords")
    if [[ -z $sel ]]; then
        unset filters
        unset search
        ret=98
        sd_res="--width=1280 --height=800"
        return 1
    fi

    readarray -t address < <(format_table_results "$sel")
    local ip="${address[1]}"
    local gameport="${address[2]}"
    local qport="${address[3]}"
    unset address

    connect "$ip" "$gameport" "$qport"
	sd_res="--width=1280 --height=800"
}
mods_disk_size(){
	printf "Total size on disk: %s | " $(du -sh "$workshop_dir" | awk '{print $1}')
	printf "%s mods | " $(ls -1 "$workshop_dir" | wc -l)
	printf "Location: %s/steamapps/workshop/content/221100" "$steam_path"
}
main_menu(){
	logger INFO "${FUNCNAME[0]}"
	logger INFO "Setting mode"
	set_mode
	while true; do
		set_header "main_menu"
		rc=$?
		logger INFO "set_header rc is $rc"
		if [[ $rc -eq 0 ]]; then
			case "$sel" in
				"") warn "No item was selected." ;;
				"	Server browser") 
                        local filters=$(choose_filters)
                        [[ -z $filters ]] && continue
                        (server_browser "$filters") | pdialog ;;
				"	My servers") query_and_connect "connect" ;;
				"	Quick connect to favorite server") connect_to_fav "$fav_server" ;;
				"	Connect by ID") connect_by_id ;;
				"	Connect by IP") connect_by_ip ;;
				"	Recent servers (last 10)") query_and_connect "history" "$(cat $hist_file)" ;;
				"	Add server by ID") add_by_id ;;
				"	Add server by IP") add_by_ip ;;
				"	Add favorite server") add_by_fav ;;
				"	Change favorite server") add_by_fav ;;
				"	Delete server") query_and_connect "delete" ;;
				"	List installed mods")
						list_mods | sed 's/\t/\n/g' | $steamsafe_zenity --list --column="Mod" --column="Symlink" --column="Dir" \
							--title="DZGUI" $sd_res --text="$(mods_disk_size)" \
							--print-column="" 2>/dev/null
						;;
				"	View changelog") changelog ;;
				"	Advanced options")
							options_menu
							main_menu
							return
							;;
				"	Help file ⧉") help_file ;;
				"	Report bug ⧉") report_bug ;;
				"	Forum ⧉") forum ;;
				"	Sponsor ⧉") sponsor ;;
				"	Hall of fame ⧉") hof ;;
			esac
		else
			logger INFO "Returning from main menu"
			return
		fi
	done
}
set_fav(){
    local fav="$1"
	logger INFO "${FUNCNAME[0]}"

    readarray -t address < <(format_config_address "$fav")
    local ip="${address[0]}"
    local gameport="${address[1]}"
    local qport="${address[2]}"
    unset address

    local info=$(a2s "$ip" "$qport" info)
    local name=$(<<< $info jq -r '.name')
    echo "'$name'"
}
check_unmerged(){
	logger INFO "${FUNCNAME[0]}"
	if [[ -f ${config_path}.unmerged ]]; then
		merge_config
		rm ${config_path}.unmerged
	fi
}
merge_config(){
	source $config_file
    legacy_fav
    legacy_ids
	[[ -z $staging_dir ]] && staging_dir="/tmp"
    update_config
	tdialog "Wrote new config format to \n${config_file}\nIf errors occur, you can restore the file:\n${config_file}.old"
}
download_new_version(){
	if [[ $is_steam_deck -eq 1 ]]; then
		freedesktop_dirs
	fi
	source_script=$(realpath "$0")
	source_dir=$(dirname "$source_script")
	mv $source_script $source_script.old
	echo "# Downloading version $upstream"
	curl -Ls "$version_url" > $source_script
	rc=$?
	if [[ $rc -eq 0 ]]; then
		echo "[DZGUI] Wrote $upstream to $source_script"
		chmod +x $source_script
		touch ${config_path}.unmerged
		echo "100"
		$steamsafe_zenity --question --width=500 --title="DZGUI" --text "DZGUI $upstream successfully downloaded.\nTo view the changelog, select Changelog.\nTo use the new version, select Exit and restart." --ok-label="Changelog" --cancel-label="Exit" 2>/dev/null
		code=$?
		if [[ $code -eq 0 ]]; then
            changelog
			exit
		elif [[ $code -eq 1 ]]; then
			exit
		fi
	else
		echo "100"
		mv $source_script.old $source_script
		$steamsafe_zenity --info --title="DZGUI" --text "[ERROR] 99: Failed to download new version." 2>/dev/null
		return
	fi

}
check_branch(){
	logger INFO "${FUNCNAME[0]}"
	if [[ $branch == "stable" ]]; then
		version_url="$stable_url/dzgui.sh"
	elif [[ $branch == "testing" ]]; then
		version_url="$testing_url/dzgui.sh"
	fi
	logger INFO "Branch is $branch"
	upstream=$(curl -Ls "$version_url" | awk -F= '/^version=/ {print $2}')
	logger INFO "Upstream version is $version"
}
enforce_dl(){
	download_new_version > >(pdialog)
}
prompt_dl(){
	$steamsafe_zenity --question --title="DZGUI" --text "Version conflict.\n\nYour branch:\t\t\t$branch\nYour version:\t\t\t$version\nUpstream version:\t\t$upstream\n\nVersion updates introduce important bug fixes and are encouraged.\n\nAttempt to download latest version?" --width=500 --ok-label="Yes" --cancel-label="No" 2>/dev/null
	rc=$?
	if [[ $rc -eq 1 ]]; then
		return
	else
		echo "100"
		download_new_version > >(pdialog)
	fi
}
check_version(){
	logger INFO "${FUNCNAME[0]}"
	[[ -f $config_file ]] && source $config_file
	[[ -z $branch ]] && branch="stable"
	check_branch
	[[ ! -f "$freedesktop_path/dzgui.desktop" ]] && freedesktop_dirs
	if [[ $version == $upstream ]]; then
		logger INFO "Local version is same as upstream"
		check_unmerged
	else
		logger INFO "Local and remote version mismatch"
		if [[ $enforce_dl -eq 1 ]]; then
			enforce_dl
		else
			prompt_dl
		fi
	fi
}
check_architecture(){
	logger INFO "${FUNCNAME[0]}"
	cpu=$(cat /proc/cpuinfo | grep "AMD Custom APU 0405")
	if [[ -n "$cpu" ]]; then
		is_steam_deck=1
		logger INFO "Setting architecture to 'Steam Deck'"
        [[ $is_steam_deck -eq 1 ]] && test_display_mode
        if [[ $gamemode -eq 1 ]]; then
            popup 1400 &&
            exit 1
        fi
	else
		is_steam_deck=0
		logger INFO "Setting architecture to 'desktop'"
	fi
}
print_ip_list(){
    [[ ${#ip_list} -eq 0 ]] &&  return
    printf "\t\"%s\"\n" "${ip_list[@]}"
}
migrate_files(){
    if [[ ! -f $config_path/dztuirc.oldapi ]]; then
        cp $config_file $config_path/dztuirc.oldapi
        rm $hist_file
    fi
}
legacy_fav(){
    source $config_file
    [[ -z $fav ]] && return
    local res=$(map_fav_to_ip "$fav")
    source $config_file
}
legacy_ids(){
    source $config_file
    [[ -z $whitelist ]] && return
    local res=$(map_id_to_ip "$whitelist")
    source $config_file
}
map_fav_to_ip(){
    local to_add="$1"
	fav_server=$(curl -s "$api" -H "Authorization: Bearer "$api_key"" \
        -G -d "sort=-players" \
        -d "filter[game]=$game" \
        -d "filter[ids][whitelist]=$to_add" \
        | jq -r '.data[].attributes|"\(.ip):\(.port):\(.portQuery)"')
    update_config
    fav_label=$(set_fav "$fav_server")
}
map_id_to_ip(){
    local to_add="$1"
    local mode="$2"
	local res=$(curl -s "$api" -H "Authorization: Bearer "$api_key"" \
        -G -d "sort=-players" \
        -d "filter[game]=$game" \
        -d "filter[ids][whitelist]=$to_add")
    local len=$(<<< "$res" jq '.data|length')
    [[ $len -eq 0 ]] && return 1
    local ip=$(<<< "$res" jq -r '.data[].attributes|"\(.ip):\(.port):\(.portQuery)"')
    if [[ $mode == "connect" ]]; then
        echo "$ip"
        return 0
    fi
    for i in $ip; do
        if [[ ${ip_list[@]} =~ $i ]]; then
            [[ ! $len -eq 1 ]] && continue
            warn "This server is already in your list"
            return 2
        fi
        ip_list+=("$i")
        update_config
    done
        echo $i
}
add_by_ip(){
    local sel=$(parse_ips)
    [[ -z $sel ]] && return

    readarray -t address < <(format_table_results "$sel")
    local ip="${address[1]}"
    local gameport="${address[2]}"
    local qport="${address[3]}"
    unset address

    if [[ ${ip_list[@]} =~ "$ip:$gameport:$qport" ]]; then
        warn "This server is already in your favorites"
        return
    fi

    ip_list+=("$ip:$gameport:$qport")
    update_config
    info "Added $ip:$gameport:$qport to:\n${config_path}dztuirc\nIf errors occurred, you can restore the file:\n${config_path}dztuirc.old"
}
pdialog(){
	$steamsafe_zenity --progress --pulsate --auto-close --title="DZGUI" --width=500 2>/dev/null
}
edialog(){
    $steamsafe_zenity --entry --text="$1" --width=500 --title="DZGUI" 2>/dev/null
}
tdialog(){
    $steamsafe_zenity --info --text="$1" --width=500 --title="DZGUI" 2>/dev/null
}
qdialog(){
    $steamsafe_zenity --question --text="$1" --width=500 --title="DZGUI" 2>/dev/null
}
add_by_id(){
    local mode="$1"
    if [[ -z $api_key ]]; then
        qdialog "Requires Battlemetrics API key. Set one now?"
        [[ $? -eq 1 ]] && return 1
        while true; do
            api_key=$(edialog "Battlemetrics API key")
            [[ $? -eq 1 ]] && return 1
            [[ -z $api_key ]] && { warn "Invalid API key"; continue; }
            if [[ $(test_bm_api $api_key) -eq 1 ]]; then
                warn "Invalid API key"
                unset api_key
                continue
            fi
            update_config
            break
        done
    fi
	while true; do
		local id
        id=$(edialog "Enter server ID")
		[[ $? -eq 1 ]] && return 1
        if [[ ! $id =~ ^[0-9]+$ ]]; then
            warn "Invalid ID"
        else
            local ip
            ip=$(map_id_to_ip "$id" "$mode")
            case "$?" in
                1)
                    warn "Invalid ID"
                    continue
                    ;;
                2)
                    continue
                    ;;
                *)
                    if [[ $mode == "connect" ]]; then
                        echo "$ip"
                        return 0
                    fi
                    tdialog "Added $ip to:\n${config_path}dztuirc\nIf errors occurred, you can restore the file:\n${config_path}dztuirc.old"
                    return 0
                    ;;
            esac
        fi
	done
}
toggle_debug(){
	if [[ $debug -eq 1 ]]; then
		debug=0
	else
		debug=1
	fi
    update_config

}
setup(){
	logger INFO "${FUNCNAME[0]}"
	[[ -z $fav_server ]] && return
    items[10]="	Change favorite server"
    [[ -n $fav_label ]] && return
    fav_label=$(set_fav $fav_server)
    update_config
}
check_map_count(){
	logger INFO "${FUNCNAME[0]}"
	[[ $is_steam_deck -eq 1 ]] && return
	local count=1048576
	logger INFO "Checking system map count"
	echo "[DZGUI] Checking system map count"
	if [[ ! -f /etc/sysctl.d/dayz.conf ]]; then
		$steamsafe_zenity --question --width=500 --title="DZGUI" --cancel-label="Cancel" --ok-label="OK" --text "sudo password required to check system vm map count."
		local rc=$?
		logger INFO "Return code is $rc"
		if [[ $rc -eq 0 ]]; then
			local pass
			logger INFO "Prompting user for sudo escalation"
			pass=$($steamsafe_zenity --password)
			local rc	
			logger INFO "Return code is $rc"
			[[ $rc -eq 1 ]] && exit 1
			local ct=$(sudo -S <<< "$pass" sh -c "sysctl -q vm.max_map_count | awk -F'= ' '{print \$2}'")
			local new_ct
			[[ $ct -lt $count ]] && ct=$count
			logger INFO "Updating map count"
			sudo -S <<< "$pass" sh -c "echo 'vm.max_map_count=$ct' > /etc/sysctl.d/dayz.conf"
			sudo sysctl -p /etc/sysctl.d/dayz.conf
		else
			logger INFO "Zenity dialog failed or user exit"
			exit 1
		fi
	fi
}
change_name(){
    while true; do
        local name=$($steamsafe_zenity --entry --text="Enter desired in-game name" --title="DZGUI" 2>/dev/null)
        [[ -z "${name//[[:blank:]]/}" ]] && continue
        update_config
        info "Changed name to: '$name'.\nIf errors occur, you can restore the file '${config_path}dztuirc.old'."
        return
    done
}
add_by_fav(){
    local sel=$(parse_ips)
    [[ -z $sel ]] && return

    readarray -t address < <(format_table_results "$sel")
    local ip="${address[1]}"
    local gameport="${address[2]}"
    local qport="${address[3]}"
    unset address
    fav_server="$ip:$gameport:$qport"
    fav_label=$(set_fav "$fav_server")

    update_config
    info "Added $fav_server to:\n${config_path}dztuirc\nIf errors occurred, you can restore the file:\n${config_path}dztuirc.old"

    items[10]="	Change favorite server"
}
lock(){
	[[ ! -d $config_path ]] && return
	if [[ ! -f ${config_path}.lockfile ]]; then
		touch ${config_path}.lockfile
	fi
	pid=$(cat ${config_path}.lockfile)
	ps -p $pid -o pid= >/dev/null 2>&1
	res=$?
	if [[ $res -eq 0 ]]; then
        info "DZGUI already running ($pid)"
		exit
	elif [[ $pid == $$ ]]; then
		:
	else
		echo $$ > ${config_path}.lockfile
	fi
}
fetch_a2s(){
	[[ -d $helpers_path/a2s ]] && return
	local sha=c7590ffa9a6d0c6912e17ceeab15b832a1090640
	local author="yepoleb"
	local repo="python-a2s"
	local url="https://github.com/$author/$repo/tarball/$sha"
	local prefix="${author^}-$repo-${sha:0:7}"
	local file="$prefix.tar.gz"
	curl -Ls "$url" > "$helpers_path/$file"
	tar xf "$helpers_path/$file" -C "$helpers_path" "$prefix/a2s" --strip=1
	rm "$helpers_path/$file"
}
fetch_dzq(){
	[[ -f $helpers_path/dayzquery.py ]] && return
	local sha=ccc4f71b48610a1885706c9d92638dbd8ca012a5
	local author="yepoleb"
	local repo="dayzquery"
	local url="https://raw.githubusercontent.com/$author/$repo/$sha/$repo.py"
	curl -Ls "$url" > $helpers_path/a2s/$repo.py
}
fetch_query(){
    [[ $(md5sum $helpers_path/query.py | awk '{print $1}') == "7cbae12ae68b526e7ff376b638123cc7" ]] && return
	local author="aclist"
	local repo="dzgui"
	local url="https://raw.githubusercontent.com/$author/dztui/$repo/helpers/query.py"
	curl -Ls "$url" > "$helpers_path/query.py"
}
fetch_helpers(){
	logger INFO "${FUNCNAME[0]}"
	mkdir -p "$helpers_path"
	[[ ! -f "$helpers_path/vdf2json.py" ]] && curl -Ls "$vdf2json_url" > "$helpers_path/vdf2json.py"
    fetch_a2s
    fetch_dzq
    fetch_query
}
update_steam_cmd(){
	preferred_client="$steam_cmd"
    update_config
}
steam_deps(){
	logger INFO "${FUNCNAME[0]}"
	local flatpak steam
	[[ $(command -v flatpak) ]] && flatpak=$(flatpak list | grep valvesoftware.Steam)
	steam=$(command -v steam)
	if [[ -z "$steam" ]] && [[ -z "$flatpak" ]]; then
		warn "Requires Steam or Flatpak Steam"
		logger ERROR "Steam was missing"
		exit
	elif [[ -n "$steam" ]] && [[ -n "$flatpak" ]]; then
		toggle_steam=1
		steam_cmd="steam"
		[[ -n $preferred_client ]] && steam_cmd="$preferred_client"
		[[ -z $preferred_client ]] && update_steam_cmd
	elif [[ -n "$steam" ]]; then
		steam_cmd="steam"
	else
		steam_cmd="flatpak run com.valvesoftware.Steam"
	fi
	logger INFO "steam_cmd set to $steam_cmd"
}
update_steam_cmd(){
	local new_cmd
	preferred_client="$steam_cmd"
	new_cmd="preferred_client=\"$preferred_client\""
	mv $config_file ${config_path}dztuirc.old
	nr=$(awk '/preferred_client=/ {print NR}' ${config_path}dztuirc.old)
	awk -v "var=$new_cmd" -v "nr=$nr" 'NR==nr {$0=var}{print}' ${config_path}dztuirc.old > ${config_path}dztuirc
}
steam_deps(){
	logger INFO "${FUNCNAME[0]}"
	local flatpak steam
	[[ $(command -v flatpak) ]] && flatpak=$(flatpak list | grep valvesoftware.Steam)
	steam=$(command -v steam)
	if [[ -z "$steam" ]] && [[ -z "$flatpak" ]]; then
		warn "Requires Steam or Flatpak Steam"
		logger ERROR "Steam was missing"
		exit
	elif [[ -n "$steam" ]] && [[ -n "$flatpak" ]]; then
		toggle_steam=1
		steam_cmd="steam"
		[[ -n $preferred_client ]] && steam_cmd="$preferred_client"
		[[ -z $preferred_client ]] && update_steam_cmd
	elif [[ -n "$steam" ]]; then
		steam_cmd="steam"
	else
		steam_cmd="flatpak run com.valvesoftware.Steam"
	fi
	logger INFO "steam_cmd set to $steam_cmd"
}
initial_setup(){
	echo "# Initial setup"
	run_depcheck
	watcher_deps
	check_architecture
	check_version
	check_map_count
	fetch_helpers
	config
	steam_deps
	run_varcheck
    migrate_files
	stale_symlinks
	init_items
	setup
	check_news
	echo "100"
}
main(){
    local parent=$(cat /proc/$PPID/comm)
    [[ -f "$debug_log" ]] && rm "$debug_log"
	lock
	local zenv=$(zenity --version 2>/dev/null)
	[[ -z $zenv ]] && { echo "Failed to find zenity"; logger "Missing zenity"; exit 1; }
	initial_setup > >(pdialog)
	main_menu
	#TODO: tech debt: cruddy handling for steam forking
	[[ $? -eq 1 ]] && pkill -f dzgui.sh
}
main
