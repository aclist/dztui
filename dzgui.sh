#!/usr/bin/env bash

set -o pipefail
version=3.3.0

aid=221100
game="dayz"
workshop="steam://url/CommunityFilePage/"
api="https://api.battlemetrics.com/servers"
sd_res="--width=1280 --height=800"
config_path="$HOME/.config/dztui/"
config_file="${config_path}dztuirc"
hist_file="${config_path}/history"
tmp=/tmp/dzgui.tmp
fifo=/tmp/table.tmp
separator="%%"
check_config_msg="Check config values and restart."
issues_url="https://github.com/aclist/dztui/issues"
url_prefix="https://raw.githubusercontent.com/aclist/dztui"
stable_url="$url_prefix/dzgui"
testing_url="$url_prefix/testing"
releases_url="https://github.com/aclist/dztui/releases/download/browser"
help_url="https://aclist.github.io/dzgui/dzgui"
freedesktop_path="$HOME/.local/share/applications"
sd_install_path="$HOME/.local/share/dzgui"
helpers_path="$sd_install_path/helpers"
geo_file="$helpers_path/ips.csv"
km_helper="$helpers_path/latlon"
sums_path="$helpers_path/sums.md5"
scmd_file="$helpers_path/scmd.sh"
km_helper_url="$releases_url/latlon"
db_file="$releases_url/ips.csv.gz"
sums_url="$stable_url/helpers/sums.md5"
scmd_url="$stable_url/helpers/scmd.sh"
vdf2json_url="$stable_url/helpers/vdf2json.py"
notify_url="$stable_url/helpers/d.html"
notify_img_url="$stable_url/helpers/d.webp"
forum_url="https://github.com/aclist/dztui/discussions"
version_file="$config_path/versions"
steamsafe_zenity="/usr/bin/zenity"

#TODO: prevent connecting to offline servers
#TODO: abstract zenity title params and dimensions

update_last_seen(){
	mv $config_file ${config_path}dztuirc.old
	nr=$(awk '/seen_news=/ {print NR}' ${config_path}dztuirc.old)
	seen_news="seen_news=\"$sum\""
	awk -v "var=$seen_news" -v "nr=$nr" 'NR==nr {$0=var}{print}' ${config_path}dztuirc.old > $config_file
	printf "[DZGUI] Updated last seen news item to '$sum'\n"
	source $config_file
}
check_news(){
	echo "# Checking news"
	[[ $branch == "stable" ]] && news_url="$stable_url/news"
	[[ $branch == "testing" ]] && news_url="$testing_url/news"
	result=$(curl -Ls "$news_url")
	sum=$(echo -n "$result" | md5sum | awk '{print $1}')
}
print_news(){
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
deps=([awk]="5.1.1" [curl]="7.80.0" [jq]="1.6" [tr]="9.0" [$steamsafe_zenity]="3.42.1")
changelog(){
	if [[ $branch == "stable" ]]; then
		md="https://raw.githubusercontent.com/aclist/dztui/dzgui/changelog.md"
	else
		md="https://raw.githubusercontent.com/aclist/dztui/testing/changelog.md"
	fi
	prefix="This window can be scrolled."
	echo $prefix
	echo ""
	curl -Ls "$md" | awk '/Unreleased/ {flag=1}flag'
}

depcheck(){
	for dep in "${!deps[@]}"; do
		command -v "$dep" 2>&1>/dev/null || (printf "Requires %s >=%s\n" "$dep" ${deps[$dep]}; exit 1)
	done
}
watcher_deps(){
	if [[ ! $(command -v wmctrl) ]] && [[ ! $(command -v xdotool) ]]; then
		echo "100"
		warn "Missing dependency: requires 'wmctrl' or 'xdotool'.\nInstall from your system's package manager."
		exit 1
	fi
}
init_items(){
	#array order determines menu selector; this is destructive
items=(
	"[Connect]"
	"	Server browser"
	"	My servers"
	"	Quick connect to favorite server"
	"	Connect by IP"
	"	Recent servers (last 10)"
	"[Manage servers]"
	"	Add server by ID"
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
	)
}
warn(){
	$steamsafe_zenity --info --title="DZGUI" --text="$1" --width=500 --icon-name="dialog-warning" 2>/dev/null
}
info(){
	$steamsafe_zenity --info --title="DZGUI" --text="$1" --width=500 2>/dev/null
}
set_api_params(){
	response=$(curl -s "$api" -H "Authorization: Bearer "$api_key"" -G -d "sort=-players" \
		-d "filter[game]=$game" -d "filter[ids][whitelist]=$list_of_ids")
	list_response=$response
	first_entry=1
}
query_api(){
	echo "# Querying API"
	#TODO: prevent drawing list if null values returned without API error
	if [[ $one_shot_launch -eq 1 ]]; then
		list_of_ids="$fav"
	else
		list_of_ids="$whitelist"
	fi
	set_api_params
	if [[ "$(jq -r 'keys[]' <<< "$response")" == "errors" ]]; then
		code=$(jq -r '.errors[] .status' <<< $response)
		#TODO: fix granular api codes
		if [[ $code -eq 401 ]]; then
			warn "Error $code: malformed API key"
			return
		elif [[ $code -eq 500 ]]; then
			warn "Error $code: malformed server list"
			return
		fi

	fi
	if [[ -z $(echo $response | jq '.data[]') ]]; then
		warn "95: API returned empty response. Check config file."
		return
	fi
}
write_config(){
cat	<<-END
#Path to DayZ installation
steam_path="$steam_path"

#Your unique API key
api_key="$api_key"

#Comma-separated list of server IDs
whitelist="$whitelist"

#Favorite server to fast-connect to (limit one)
fav="$fav"

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

#Terminal emulator
term="$term"

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
	#TODO: update url
	curl -s "$version_url" > "$sd_install_path/dzgui.sh"
	chmod +x "$sd_install_path/dzgui.sh"
	img_url="$stable_url/images"
	for i in dzgui grid.png hero.png logo.png; do
		curl -s "$img_url/$i" > "$sd_install_path/$i"
	done
	write_desktop_file > "$freedesktop_path/dzgui.desktop"
	if [[ $is_steam_deck -eq 1 ]]; then
		write_desktop_file > "$HOME/Desktop/dzgui.desktop"
	fi
}
find_library_folder(){
	echo "ENTERED: ${FUNCNAME[0]}" >> /tmp/dzdebug.log
	echo "RECEIVED ARG: $1" >> /tmp/dzdebug.log
	steam_path="$(python3 "$helpers_path/vdf2json.py" -i "$1/steamapps/libraryfolders.vdf" | jq -r '.libraryfolders[]|select(.apps|has("221100")).path')"
	echo "STEAM PATH RESOLVED TO: $steam_path" >> /tmp/dzdebug.log
}
file_picker(){
	echo "${FUNCNAME[0]}" >> /tmp/dzdebug.log
	local path=$($steamsafe_zenity --file-selection --directory 2>/dev/null)
	echo "FILE PICKER PATH RESOLVED TO: $path" >> /tmp/dzdebug.log
	if [[ -z "$path" ]]; then
		echo "PATH WAS EMPTY" >> /tmp/dzdebug.log
		return
	else
		default_steam_path="$path"
		find_library_folder "$default_steam_path"
	fi
}
create_config(){
	debug "ENTERED ${FUNCNAME[0]}"
	check_pyver
	write_to_config(){
		mkdir -p $config_path
		write_config > $config_file
		info "Config file created at $config_file."
		source $config_file
		return
	}
	while true; do
		player_input="$($steamsafe_zenity --forms --add-entry="Player name (required for some servers)" --add-entry="BattleMetrics API key" --add-entry="Steam API key" --title="DZGUI" --text="DZGUI" $sd_res --separator="@" 2>/dev/null)"
		#explicitly setting IFS crashes $steamsafe_zenity in loop
		#and mapfile does not support high ascii delimiters
		#so split fields with newline
		readarray -t args < <(echo "$player_input" | sed 's/@/\n/g')
		name="${args[0]}"
		api_key="${args[1]}"
		steam_api="${args[2]}"

		[[ -z $player_input ]] && exit
		if [[ -z $api_key ]] || [[ -z $steam_api ]]; then
			warn "API key cannot be empty"
		#TODO: test BM key
		elif [[ $(test_steam_api) -eq 1 ]]; then
			warn "Invalid Steam API key"
		elif [[ $(test_bm_api) -eq 1 ]]; then
			warn "Invalid BM API key"
		else
			while true; do
				debug "STEAMSAFEZENITY: $steamsafe_zenity"
				[[ -n $steam_path ]] && { write_to_config; return; }
				find_default_path
				find_library_folder "$default_steam_path"
				if [[ -z $steam_path ]]; then
					debug "STEAM PATH WAS EMPTY"
					zenity --question --text="DayZ not found or not installed at the chosen path." --ok-label="Choose path manually" --cancel-label="Exit"
					if [[ $? -eq 0 ]]; then
						debug "USER SELECTED FILE PICKER"
						file_picker
					else
						exit
					fi
				else
					write_to_config
				fi
			done
		fi
	done

}
err(){
	printf "[ERROR] %s\n" "$1"
}
varcheck(){
	if [[ -z $api_key ]] || [[ ! -d $steam_path ]] || [[ ! -d $game_dir ]]; then
		echo 1
	fi
}
run_depcheck(){
	if [[ -n $(depcheck) ]]; then
		echo "100"
		$steamsafe_zenity --warning --ok-label="Exit" --title="DZGUI" --text="$(depcheck)"
		exit
	fi
}
debug(){
	echo "$*" >> /tmp/dzdebug.log
}
check_pyver(){
	debug "ENTERED ${FUNCNAME[0]}"
	pyver=$(python3 --version | awk '{print $2}')
	debug "PYVER is $pyver"
	if [[ -z $pyver ]] || [[ ${pyver:0:1} -lt 3 ]]; then
		warn "Requires python >=3.0" &&
		exit
	fi
}
run_varcheck(){
	source $config_file
	workshop_dir="$steam_path/steamapps/workshop/content/$aid"
	game_dir="$steam_path/steamapps/common/DayZ"
	if [[ $(varcheck) -eq 1 ]]; then
		$steamsafe_zenity --question --cancel-label="Exit" --text="Malformed config file. This is probably user error.\nStart first-time setup process again?" --width=500 2>/dev/null
		code=$?
		if [[ $code -eq 1 ]]; then
			exit
		else
			create_config
		fi
	fi
}
config(){
	debug "ENTERED ${FUNCNAME[0]}"
	if [[ ! -f $config_file ]]; then
		debug "CONFIG FILE MISSING"
		debug "STEAMSAFEZENITY is $steamsafe_zenity"
		$steamsafe_zenity --width 500 --info --text="Config file not found. Click OK to proceed to first-time setup." 2>/dev/null
		code=$?
		debug "RETURN CODE WAS $code"
		#TODO: prevent progress if user hits ESC
		if [[ $code -eq 1 ]]; then
			debug "RECEIVED EXIT CODE 1"
			exit
		else
			debug "CREATING CONFIG"
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
calc_mod_sizes(){
	for i in "$diff"; do
	local mods+=$(grep -w "$i" /tmp/modsizes | awk '{print $1}')
	done
	totalmodsize=$(echo -e "${mods[@]}" | awk '{s+=$1}END{print s}')
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
	[[ $is_steam_deck -eq 1 ]] && test_display_mode
	if [[ $gamemode -eq 1 ]]; then
		steam_deck_mods
	else
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
			launch
		else
			return 1
		fi
	fi
}
encode(){
	echo "$1" | md5sum | cut -c -8
}
stale_symlinks(){
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
	[[ -z $(is_steam_running) ]] && { $steamsafe_zenity --info --text "Steam must be running to use this feature."; return; }
	popup 300
	rc=$?
	if [[ $rc -eq 0 ]]; then
		calc_mod_sizes
		local total_size=$(numfmt --to=iec $totalmodsize)
		log="$default_steam_path/logs/content_log.txt"
		[[ -f "/tmp/dz.status" ]] && rm "/tmp/dz.status"
		touch "/tmp/dz.status"
		console_dl "$diff" &&
		$steam_cmd steam://open/downloads && 2>/dev/null 1>&2
		win=$(xdotool search --name "DZG Watcher")
		xdotool windowactivate $win
		until [[ -z $(comm -23 <(printf "%s\n" "${modids[@]}" | sort) <(ls -1 $workshop_dir | sort)) ]]; do
			local missing=$(comm -23 <(printf "%s\n" "${modids[@]}" | sort) <(ls -1 $workshop_dir | sort) | wc -l)
			echo "# Downloaded $((${#modids[@]}-missing)) of ${#modids[@]} mods. ESC cancels"
		done | $steamsafe_zenity --pulsate --progress --title="DZG Watcher" --auto-close --no-cancel --width=500 2>/dev/null
		compare
		[[ $force_update -eq 1 ]] && { unset force_update; return; }
		if [[ -z $diff ]]; then
			check_timestamps
			passed_mod_check > >($steamsafe_zenity --pulsate --progress --title="DZGUI" --auto-close --width=500 2>/dev/null)
			launch
		else
			manual_mod_install
		fi
	else
		manual_mod_install
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
	[[ -n $(grep "$ip" $hist_file) ]] && return
	if [[ -f $hist_file ]]; then
		old=$(tail -n9 "$hist_file")
		old="$old\n"
	fi
	echo -e "${old}${ip}" > "$hist_file"
}
is_steam_running(){
	xdotool search --onlyvisible --name "Steam"
}
connect(){
	#TODO: sanitize/validate input
	readarray -t qport_arr <<< "$qport_list"
	if [[ -z ${qport_arr[@]} ]]; then
		err "98: Failed to obtain query ports"
		return
	fi
	ip=$(echo "$1" | awk -F"$separator" '{print $1}')
	bid=$(echo "$1" | awk -F"$separator" '{print $2}')
	if [[ $2 == "ip" ]]; then
		fetch_mods_sa "$ip" > >($steamsafe_zenity --pulsate --progress --auto-close --no-cancel --width=500 2>/dev/null)
	else
		fetch_mods "$bid"
	fi
	if [[ $ret -eq 96 ]]; then
	       unset ret
	       return
	fi
	validate_mods
	rc=$?
	[[ $rc -eq 1 ]] && return
	compare
	[[ $auto_install -eq 2 ]] && merge_modlists
	if [[ -n $diff ]]; then
		case $auto_install in
			1|2) auto_mod_install ;;
			*) manual_mod_install ;;
		esac
	else
		passed_mod_check > >($steamsafe_zenity --pulsate --progress --auto-close --width=500 2>/dev/null)
		update_history
		launch
	fi
}
fetch_mods(){
	remote_mods=$(curl -s "$api" -H "Authorization: Bearer "$api_key"" -G -d filter[ids][whitelist]="$1" -d "sort=-players" \
	| jq -r '.data[] .attributes .details .modIds[]')
}
fetch_mods_sa(){
	sa_ip=$(echo "$1" | awk -F: '{print $1}')
	for i in ${qport_arr[@]}; do
		if [[ -n $(echo "$i" | awk -v ip=$ip '$0 ~ ip') ]]; then
			sa_port=$(echo $i | awk -v ip=$ip -F$separator '$0 ~ ip {print $2}')
		fi
	done
	echo "[DZGUI] Querying modlist on ${sa_ip}:${sa_port}"
	echo "# Querying modlist on ${sa_ip}:${sa_port}"
	local response=$(curl -Ls "https://dayzsalauncher.com/api/v1/query/$sa_ip/$sa_port")
	local status=$(echo "$response" | jq '.status')
	if [[ $status -eq 1 ]]; then
		echo "100"
		err "97: Failed to fetch modlist"
		$steamsafe_zenity --error --title="DZGUI" --width=500 --text="[ERROR] 97: Failed to fetch modlist" 2>/dev/null &&
		ret=96
		return
	fi
	remote_mods=$(echo "$response" | jq -r '.result.mods[].steamWorkshopId')
	qport_arr=()
}
prepare_ip_list(){
	ct=$(< "$1" jq '[.response.servers[]]|length' 2>/dev/null)
	#old servers may become stale and return nothing
	if [[ -n $ct ]]; then
		for((i=0;i<$ct;i++));do
			name=$(< $json jq --arg i $i -r '[.servers[]][($i|tonumber)].name')
			addr=$(< $json jq --arg i $i -r '[.servers[]][($i|tonumber)].addr')
			ip=$(echo "$addr" | awk -F: '{print $1}')
			local qport=$(awk -F: '{print $2}' <<< $addr)
			players=$(< $json jq --arg i $i -r '[.servers[]][($i|tonumber)].players')
			max_players=$(< $json jq --arg i $i -r '[.servers[]][($i|tonumber)].max_players')
			gameport=$(< $json jq --arg i $i -r '[.servers[]][($i|tonumber)].gameport')
			ip_port=$(echo "$ip:$gameport")
			time=$(< $json jq --arg i $i -r '[.servers[]][($i|tonumber)].gametype' | grep -oP '(?<!\d)\d{2}:\d{2}(?!\d)')
			echo "$name"
			echo "$ip_port"
			echo "$players/$max_players"
			echo "$time"
			echo "$qport"
		done
	fi
}
history_table(){
	[[ -f /tmp/dz.hist ]] && rm /tmp/dz.hist
	for i in $(cat $hist_file); do
		echo "# Getting metadata for $i"
		local meta_file=$(mktemp)
		source $config_file
		local url="https://api.steampowered.com/IGameServersService/GetServerList/v1/?filter=\appid\221100\gameaddr\\$i&key=$steam_api"
		curl -Ls "$url" > $meta_file
		json=$(mktemp)
		< $meta_file jq '.response' > $json
		res=$(< $meta_file jq -er '.response.servers[]' 2>/dev/null)
		prepare_ip_list "$meta_file" >> /tmp/dz.hist
		sleep 0.5s
	done | $steamsafe_zenity --pulsate --progress --auto-close --title="DZGUI" --width=500 --no-cancel 2>/dev/null
	[[ $? -eq 1 ]] && return
	while true; do
	sel=$(cat /tmp/dz.hist | $steamsafe_zenity --width 1200 --height 800 --title="DZGUI" --text="Recent servers" --list --column=Name --column=IP --column=Players --column=Gametime --column=Qport --print-column=2,5 --separator=%% 2>/dev/null)
	if [[ $? -eq 1 ]]; then
		return_from_table=1
		rm /tmp/dz.hist
		return
	fi
		if [[ -z $sel ]]; then
			echo "No selection"
		else
			local addr="$(echo "$sel" | awk -F"%%" '{print $1}')"
			local qport="$(echo "$sel" | awk -F"%%" '{print $2}')"
			local ip=$(awk -F: '{print $1}' <<< $addr)
			local gameport=$(awk -F: '{print $2}' <<< $addr)
			local sa_ip=$(echo "$ip:$gameport%%$qport")
			qport_list="$sa_ip"
			connect "$sel" "ip"
		fi
	done
	rm /tmp/dz.hist
}

ip_table(){
	while true; do
	sel=$(prepare_ip_list "$meta_file" | $steamsafe_zenity --width 1200 --height 800 --text="Multiple maps found at this server. Select map from the list below" --title="DZGUI" --list --column=Name --column=IP --column=Players --column=Gametime --column=Qport --print-column=2 --separator=%% 2>/dev/null)
	if [[ $? -eq 1 ]]; then
		return_from_table=1
		return
	fi
		if [[ -z $sel ]]; then
			echo "No selection"
		else
			local gameport="$(echo "$sel" | awk -F: '{print $2}')"
			local ip="$(echo "$sel" | awk -F: '{print $1}')"
			local addr=$(< $json jq -r --arg gameport $gameport '.servers[]|select(.gameport == ($gameport|tonumber)).addr')
			local qport=$(echo "$addr" | awk -F: '{print $2}')
			local sa_ip=$(echo "$ip:$gameport%%$qport")
			qport_list="$sa_ip"
			connect "$sel" "ip"
		fi
	done
}
fetch_ip_metadata(){
	meta_file=$(mktemp)
	source $config_file
	url="https://api.steampowered.com/IGameServersService/GetServerList/v1/?filter=\appid\221100\gameaddr\\$ip&key=$steam_api"
	curl -Ls "$url" > $meta_file
	json=$(mktemp)
	< $meta_file jq '.response' > $json
	res=$(< $meta_file jq -er '.response.servers[]' 2>/dev/null)
}

#TODO: local servers
#local_ip(){
#(^127\.)|(^10\.)|(^172\.1[6-9]\.)|(^172\.2[0-9]\.)|(^172\.3[0-1]\.)|(^192\.168\.)
#}
test_steam_api(){
	local code=$(curl -ILs "https://api.steampowered.com/IGameServersService/GetServerList/v1/?filter=\appid\221100&limit=10&key=$steam_api" \
		| grep -E "^HTTP")
	[[ $code =~ 403 ]] && echo 1
	[[ $code =~ 200 ]] && echo 0
}
test_bm_api(){
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
connect_by_ip(){
	source $config_file
	check_steam_api
	[[ $? -eq 1 ]] && return
	while true; do
		if [[ $return_from_table -eq 1 ]]; then
			return_from_table=0
			return
		fi
		ip=$($steamsafe_zenity --entry --text="Enter server IP (omit port)" --title="DZGUI" 2>/dev/null)
		[[ $? -eq 1 ]] && return
		if validate_ip "$ip"; then
			fetch_ip_metadata
			if [[ ! $? -eq 0 ]]; then
				warn "[ERROR] 96: Failed to retrieve IP metadata. Check IP or API key and try again."
				echo "[DZGUI] 96: Failed to retrieve IP metadata"
			else
				ip_table
			fi
		else
			continue
		fi
	done
}
fetch_mods(){
	remote_mods=$(curl -s "$api" -H "Authorization: Bearer "$api_key"" -G -d filter[ids][whitelist]="$1" -d "sort=-players" \
	| jq -r '.data[] .attributes .details .modIds[]')
}
query_defunct(){
	max=${#modlist[@]}
	concat(){
	for ((i=0;i<$max;i++)); do
	   echo "publishedfileids[$i]=${modlist[$i]}&"
	done | awk '{print}' ORS=''
	}
	payload(){
		echo -e "itemcount=${max}&$(concat)"
	}
	post(){
		curl -s -X POST -H "Content-Type:application/x-www-form-urlencoded" -d "$(payload)" 'https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/?format=json'
	}
	result=$(post | jq -r '.[].publishedfiledetails[] | select(.result==1) | "\(.file_size) \(.publishedfileid)"')
	echo "$result" > /tmp/modsizes
	readarray -t newlist <<< $(echo -e "$result" | awk '{print $2}')
}
validate_mods(){
	url="https://steamcommunity.com/sharedfiles/filedetails/?id="
	newlist=()
	readarray -t modlist <<< $remote_mods
	query_defunct
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
	if [[ -z ${remote_mods[@]} ]]; then
		return 1
	else
		readarray -t serv <<< "$(server_modlist)"
		for i in "${serv[@]}"; do
			id=$(awk -F"= " '/publishedid/ {print $2}' "$workshop_dir"/$i/meta.cpp | awk -F\; '{print $1}')
			encoded_id=$(encode $id)
			link="@$encoded_id;"
			echo -e "$link"
		done | tr -d '\n' | perl -ple 'chop'
	fi
}
launch(){
	mods=$(concat_mods)
	if [[ $debug -eq 1 ]]; then
		launch_options="$steam_cmd -applaunch $aid -connect=$ip -nolauncher -nosplash -name=$name -skipintro \"-mod=$mods\""
		print_launch_options="$(printf "This is a dry run.\nThese options would have been used to launch the game:\n\n$launch_options\n" | fold -w 60)"
		$steamsafe_zenity --question --title="DZGUI" --ok-label="Write to file" --cancel-label="Back"\
			--text="$print_launch_options" 2>/dev/null
		if [[ $? -eq 0 ]]; then
			source_script=$(realpath "$0")
			source_dir=$(dirname "$source_script")
			echo "$launch_options" > "$source_dir"/options.log
			echo "[DZGUI] Wrote launch options to $source_dir/options.log"
			$steamsafe_zenity --info --width 500 --title="DZGUI" --text="Wrote launch options to \n$source_dir/options.log" 2>/dev/null
		fi

	else
		echo "[DZGUI] All OK. Launching DayZ"
		$steamsafe_zenity --width 500 --title="DZGUI" --info --text="Launch conditions satisfied.\nDayZ will now launch after clicking [OK]." 2>/dev/null
		$steam_cmd -applaunch $aid -connect=$ip -nolauncher -nosplash -skipintro -name=$name \"-mod=$mods\"
		exit
	fi
		one_shot_launch=0
}
browser(){
	if [[ -n "$BROWSER" ]]; then
		"$BROWSER" "$1" 2>/dev/null
	else
		xdg-open "$1" 2>/dev/null
	fi
}
report_bug(){
	echo "[DZGUI] Opening issues page in browser"
	if [[ $is_steam_deck -eq 1 ]]; then
		steam steam://openurl/"$issues_url" 2>/dev/null
	elif [[ $is_steam_deck -eq 0 ]]; then
		browser "$issues_url" 2>/dev/null &
	fi
}
forum(){
	echo "[DZGUI] Opening forum in browser"
	if [[ $is_steam_deck -eq 1 ]]; then
		steam steam://openurl/"$forum_url" 2>/dev/null
	elif [[ $is_steam_deck -eq 0 ]]; then
		browser "$forum_url" 2>/dev/null &
	fi
}
help_file(){
	echo "[DZGUI] Opening help file in browser"
	if [[ $is_steam_deck -eq 1 ]]; then
		steam steam://openurl/"$help_url" 2>/dev/null
	elif [[ $is_steam_deck -eq 0 ]]; then
		browser "$help_url" 2>/dev/null &
	fi
}
set_mode(){
	if [[ $debug -eq 1 ]]; then
		mode=debug
	else
		mode=normal
	fi
}
delete_by_id(){
	new_whitelist="whitelist=\"$(echo "$whitelist" | sed "s/,$server_id$//;s/^$server_id,//;s/,$server_id,/,/;s/^$server_id$//")\""
	mv $config_file ${config_path}dztuirc.old
	nr=$(awk '/whitelist=/ {print NR}' ${config_path}dztuirc.old)
	awk -v "var=$new_whitelist" -v "nr=$nr" 'NR==nr {$0=var}{print}' ${config_path}dztuirc.old > ${config_path}dztuirc
	echo "[DZGUI] Removed $server_id from key 'whitelist'"
	$steamsafe_zenity --info --title="DZGUI" --text="Removed "$server_id" from:\n${config_path}dztuirc\nIf errors occur, you can restore the file:\n${config_path}dztuirc.old" --width=500 2>/dev/null
	source $config_file
}
delete_or_connect(){
	if [[ $delete -eq 1 ]]; then
		server_name=$(echo "$sel" | awk -F"%%" '{print $1}')
		server_id=$(echo "$sel" | awk -F"%%" '{print $2}')
		$steamsafe_zenity --question --text="Delete this server? \n$server_name" --title="DZGUI" --width=500 2>/dev/null
		if [[ $? -eq 0 ]]; then
			delete_by_id $server_id
		fi
		source $config_file
		unset delete
	else
		local lookup_ip=$(echo "$sel" | awk -F: '{print $1}')
		ip=$lookup_ip
		fetch_ip_metadata
		if [[ ! $? -eq 0 ]]; then
			warn "[ERROR] 96: Failed to retrieve IP metadata. Check IP or API key and try again."
			echo "[DZGUI] 96: Failed to retrieve IP metadata"
		else
			local jad=$(echo "$res" | jq -r '.addr')
			if [[ $(<<< "$jad" wc -l ) -gt 1 ]]; then
				ip_table
			elif [[ $(<<< "$jad" wc -l ) -eq 1 ]]; then
				local gameport="$(echo "$res" | jq -r '.gameport')"
				local ip="$(echo "$jad" | awk -F: '{print $1}')"
				local qport=$(echo "$jad" | awk -F: '{print $2}')
				local sa_ip=$(echo "$ip:$gameport%%$qport")
				qport_list="$sa_ip"
				local sel="$ip:$gameport%%$qport"
				connect "$sel" "ip"
			fi
		fi
	fi
}
populate(){
	while true; do
		if [[ $delete -eq 1 ]]; then
			cols="--column="Server" --column="ID""
			set_header "delete"
		else
			cols="--column="Server" --column="IP" --column="Players" --column="Gametime" --column="Status" --column="ID" --column="Ping""
			set_header ${FUNCNAME[0]}
		fi
		rc=$?
		if [[ $rc -eq 0 ]]; then
			if [[ -z $sel ]]; then
				warn "No item was selected."
			else
				delete_or_connect
				return
			fi
		else
			delete=0
			return
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
fetch_query_ports(){
	qport_list=$(echo "$response" | jq -r '.data[] .attributes | "\(.ip):\(.port)%%\(.portQuery)"')
}
connect_to_fav(){
	if [[ -n $fav ]]; then
		one_shot_launch=1
		query_api
		fetch_query_ports
		echo "[DZGUI] Attempting connection to $fav_label"
		connect "$qport_list" "ip"
		one_shot_launch=0
	else
		warn "93: No fav server configured"
	fi

}
set_header(){
	[[ $auto_install -eq 2 ]] && install_mode="auto"
	[[ $auto_install -eq 1 ]] && install_mode="headless"
	[[ $auto_install -eq 0 ]] && install_mode=manual
	if [[ $1 == "delete" ]]; then
		sel=$(cat $tmp | $steamsafe_zenity $sd_res --list $cols --title="DZGUI" --text="DZGUI $version | Mode: $mode | Branch: $branch | Mods: $install_mode | Fav: $fav_label" \
			--separator="$separator" --print-column=1,2 --ok-label="Delete" 2>/dev/null)
	elif [[ $1 == "populate" ]]; then
		sel=$(cat $tmp | $steamsafe_zenity $sd_res --list $cols --title="DZGUI" --text="DZGUI $version | Mode: $mode | Branch: $branch | Mods: $install_mode | Fav: $fav_label" \
			--separator="$separator" --print-column=2,6 2>/dev/null)
	elif [[ $1 == "main_menu" ]]; then
		sel=$($steamsafe_zenity $sd_res --list --title="DZGUI" --text="${news}DZGUI $version | Mode: $mode | Branch: $branch | Mods: $install_mode | Fav: $fav_label" \
		--cancel-label="Exit" --ok-label="Select" --column="Select launch option" --hide-header "${items[@]}" 2>/dev/null)
	fi
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
	printf "[DZGUI] Toggled branch to '$branch'\n"
	source $config_file
}
generate_log(){
	cat <<-DOC
	Linux: $(uname -mrs)
	Version: $version
	Branch: $branch
	Whitelist: $whitelist
	Steam path: $steam_path
	Workshop path: $workshop_dir
	Game path: $game_dir

	Mods:
	$(list_mods)
	DOC
}
console_dl(){
	readarray -t modids <<< "$@"
	steam steam://open/console 2>/dev/null 1>&2 &&
	sleep 1s
	#https://github.com/jordansissel/xdotool/issues/67
	#https://dwm.suckless.org/patches/current_desktop/
	local wid=$(xdotool search --onlyvisible --name Steam)
	#xdotool windowactivate $wid
	sleep 1.5s
	for i in "${modids[@]}"; do
		xdotool type --delay 0 "workshop_download_item $aid $i"
		sleep 0.5s
		xdotool key --window $wid Return
		sleep 0.5s
	done
}
find_default_path(){
	echo "ENTER: ${FUNCNAME[0]}" >> /tmp/dzdebug.log
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
popup(){
	pop(){
		$steamsafe_zenity --info --text="$1" --title="DZGUI" --width=500 2>/dev/null
	}
	case "$1" in
		100) pop "This feature requires xdotool and wmctrl.";;
		200) pop "This feature is not supported on Gaming Mode.";;
		300) pop "\nThe Steam console will now open and briefly issue commands to\ndownload the workshop files, then return to the download progress page.\n\nEnsure that the Steam console has keyboard and mouse focus\n(keep hands off keyboard) while the commands are being issued.\n\nDepending on the number if mods, it may take some time to queue the downloads,\nbut if a popup or notification window steals focus, it could obstruct\nthe process." ;;
		400) pop "Automod install enabled. Auto-downloaded mods will not appear\nin your Steam Workshop subscriptions, but DZGUI will\ntrack the version number of downloaded mods internally\nand trigger an update if necessary." ;;
		500) pop "Automod install disabled.\nSwitched to manual mode." ;;
		600) pop "No preferred servers set." ;;
		700) pop "Toggled to Flatpak Steam." ;;
		800) pop "Toggled to native Steam." ;;
		900) pop "This feature is not supported on Steam Deck."
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
	printf "[DZGUI] Set mod install to '$auto_install'\n"
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
	case "$auto_install" in
		0|1|"") auto_hr="OFF"; ;;
		2) auto_hr="ON"; ;;
	esac
	debug_list=(
		"Toggle branch"
		"Toggle debug mode"
		"Generate debug log"
		"Toggle auto mod install [$auto_hr]"
		)
	#TODO: tech debt: drop old flags
	[[ $auto_install -eq 2 ]] || [[ $auto_install -eq 1 ]] && debug_list+=("Force update local mods")
	case "$steam_cmd" in
		steam) steam_hr=Steam ;;
		flatpak*) steam_hr=Flatpak ;;
	esac
	[[ $toggle_steam -eq 1 ]] && debug_list+=("Toggle native Steam or Flatpak [$steam_hr]")
	debug_sel=$($steamsafe_zenity --list --width=1280 --height=800 --column="Options" --title="DZGUI" --hide-header "${debug_list[@]}" 2>/dev/null)
	[[ -z $debug_sel ]] && return
	case "$debug_sel" in
		"Toggle branch")
			enforce_dl=1
			toggle_branch &&
			check_version
			;;
		"Toggle debug mode") toggle_debug ;;
		"Generate debug log")
			source_script=$(realpath "$0")
			source_dir=$(dirname "$source_script")
			generate_log > "$source_dir/DZGUI.log"
			printf "[DZGUI] Wrote log file to %s/log\n" "$source_dir"
			$steamsafe_zenity --info --width 500 --title="DZGUI" --text="Wrote log file to \n$source_dir/log" 2>/dev/null
			;;
		Toggle[[:space:]]auto*) toggle_console_dl ;;
		"Force update local mods")
			force_update=1
			force_update_mods
			merge_modlists > >($steamsafe_zenity --pulsate --progress --no-cancel --auto-close --title="DZGUI" --width=500 2>/dev/null)
			auto_mod_install
			;;
		Toggle[[:space:]]native*) toggle_steam_binary ;;
	esac
}
query_and_connect(){
	[[ -z $whitelist ]] && { popup 600; return; }
	q(){
		query_api
		parse_json
		create_array
	}
	q | $steamsafe_zenity --width 500 --progress --pulsate --title="DZGUI" --auto-close 2>/dev/null
	rc=$?
	if [[ $rc -eq 1 ]]; then
		:
	else
		populate
	fi
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
		local local_ip=$(dig +short myip.opendns.com @resolver1.opendns.com)
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
	if [[ $res -eq 1 ]]; then
		run(){
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
		run > >($steamsafe_zenity --pulsate --progress --auto-close --width=500 2>/dev/null)
	fi 
}
choose_filters(){
	if [[ $is_steam_deck -eq 0 ]]; then
		sd_res="--width=1920 --height=1080"
	fi
	sels=$($steamsafe_zenity --title="DZGUI" --text="Server search" --list --checklist --column "Check" --column "Option" --hide-header TRUE "All maps (untick to select from map list)" TRUE "Daytime" TRUE "Nighttime" False "Empty" False "Full" TRUE "Low population" FALSE "Non-ASCII titles" FALSE "Keyword search" $sd_res 2>/dev/null)
	if [[ $sels =~ Keyword ]]; then
		search=$($steamsafe_zenity --entry --text="Search (case insensitive)" --width=500 --title="DZGUI" 2>/dev/null | awk '{print tolower($0)}')
		[[ -z $search ]] && { ret=97; return; }
	fi	
	[[ -z $sels ]] && return
	filters=$(echo "$sels" | sed 's/|/, /g;s/ (untick to select from map list)//')
}
get_dist(){
	local given_ip="$1"
	local network="$(echo "$given_ip" | awk -F. '{OFS="."}{print $1"."$2}')"
	local binary=$(grep -E "^$network\." $geo_file)
	local three=$(echo $given_ip | awk -F. '{print $3}')
	local host=$(echo $given_ip | awk -F. '{print $4}')
	local res=$(echo "$binary" | awk -F[.,] -v three=$three -v host=$host '$3 <=three && $7 >= three{if($3>three || ($3==three && $4 > host) || $7 < three || ($7==three && $8 < host)){next}{print}}' | awk -F, '{print $7,$8}')
	local remote_lat=$(echo "$res" | awk '{print $1}')
	local remote_lon=$(echo "$res" | awk '{print $2}')
	if [[ -z $remote_lat ]]; then
		local dist="Unknown"
		echo "$dist"
	else
		local dist=$($km_helper "$local_lat" "$local_lon" "$remote_lat" "$remote_lon")
		printf "%05.0f %s" "$dist" "km"
	fi
}
prepare_filters(){
	echo "# Filtering list"
	[[ ! "$sels" =~ "Full" ]] && { exclude_full; disabled+=("Full") ; }
	[[ ! "$sels" =~ "Empty" ]] && { exclude_empty; disabled+=("Empty") ; }
	[[ ! "$sels" =~ "Daytime" ]] && { exclude_daytime; disabled+=("Daytime") ; }
	[[ ! "$sels" =~ "Nighttime" ]] && { exclude_nighttime; disabled+=("Nighttime") ; }
	[[ ! "$sels" =~ "Low population" ]] && { exclude_lowpop; disabled+=("Low-pop") ; }
	[[ ! "$sels" =~ "Non-ASCII titles" ]] && { exclude_nonascii; disabled+=("Non-ASCII") ; }
	[[ -n "$search" ]] && keyword_filter
	strip_null
	echo "100"
}
write_fifo(){
	[[ -p $fifo ]] && rm $fifo
	mkfifo $fifo
	for((i=0;i<${#qport[@]};i++)); do
		printf  "%s\n%s\n%s\n%03d\n%03d\n%s\n%s:%s\n%s\n" "${map[$i]}" "${name[$i]}" "${gametime[$i]}" \
		"${players[$i]}" "${max[$i]}" "$(get_dist ${addr[$i]})" "${addr[$i]}" "${gameport[$i]}" "${qport[$i]}" >> $fifo
		done 
}
munge_servers(){
	if [[ ! "$sels" =~ "All maps" ]]; then
		filter_maps > >($steamsafe_zenity --pulsate --progress --auto-close --width=500 2>/dev/null)
		disabled+=("All maps")
	fi
	[[ $ret -eq 97 ]] && return
	prepare_filters > >($steamsafe_zenity --pulsate --progress --auto-close --width=500 2>/dev/null)
	if [[ $(echo "$response" | jq 'length') -eq 0 ]]; then
		$steamsafe_zenity --error --text="No matching servers" 2>/dev/null
		return
	fi
	local addr=$(echo "$response" | jq -r '.[].addr' | awk -F: '{print $1}')
	local gameport=$(echo "$response" | jq -r '.[].gameport')
	local qport=$(echo "$response" | jq -r '.[].addr' | awk -F: '{print $2}')
	#jq bug #1788, raw output cannot be used with ASCII
	local name=$(echo "$response" | jq -a '.[].name' | sed 's/\\u[0-9a-z]\{4\}//g;s/^"//;s/"$//')
	local players=$(echo "$response" | jq -r '.[].players')
	local max=$(echo "$response" | jq -r '.[].max_players')
	local map=$(echo "$response" | jq -r '.[].map|ascii_downcase')
	local gametime=$(echo "$response" | jq -r '.[].gametype' | grep -oE '[0-9]{2}:[0-9]{2}$')
	readarray -t qport <<< $qport
	readarray -t gameport <<< $gameport
	readarray -t addr <<< $addr
	readarray -t name <<< $name
	readarray -t players <<< $players
	readarray -t map <<< $map
	readarray -t max <<< $max
	readarray -t gametime <<< $gametime
	if [[ $is_steam_deck -eq 0 ]]; then
		sd_res="--width=1920 --height=1080"
	fi
	
	write_fifo &
	pid=$!
	local sel=$($steamsafe_zenity --text="$(pagination)" --title="DZGUI" --list --column=Map --column=Name --column=Gametime --column=Players --column=Max --column=Distance --column=IP --column=Qport $sd_res --print-column=7,8 --separator=%% 2>/dev/null < <(while true; do cat $fifo; done))
	if [[ -z $sel ]]; then
		rm $fifo
		kill -9 $pid
	else
		rm $fifo
		kill -9 $pid
		echo $sel
	fi
}
debug_servers(){
	[[ -f $debug_log ]] && rm $debug_log
	if [[ -n $steam_api ]]; then
		exists=true
	else
		exists=false
	fi
	key_len=${#steam_api}
	first_char=${steam_api:0:1}
	last_char=${steam_api:0-1}
	debug_res=$(curl -Ls "https://api.steampowered.com/IGameServersService/GetServerList/v1/?filter=\appid\221100&limit=10&key=$steam_api")
	debug_len=$(echo "$debug_res" | jq '[.response.servers[]]|length')
	[[ -z $debug_len ]] && debug_len=0
	cat <<-DOC > $debug_log
	======START DEBUG======
	Key exists: $exists
	First char: $first_char
	Last char: $last_char
	Key length: $key_len
	======Short query======
	Expected: 10
	Found: $debug_len
	Response follows---->
	$debug_res
	======END DEBUG=======
	DOC
}
server_browser(){
	check_steam_api
	[[ $? -eq 1 ]] && return

	unset ret
	file=$(mktemp)
	local limit=20000
	local url="https://api.steampowered.com/IGameServersService/GetServerList/v1/?filter=\appid\221100&limit=$limit&key=$steam_api"
	check_geo_file
	local_latlon
	choose_filters
	[[ -z $sels ]] && return
	[[ $ret -eq 97 ]] && return
	#TODO: some error handling here
	fetch(){
		echo "# Getting server list"
		response=$(curl -Ls "$url" | jq -r '.response.servers')
	}
	fetch > >($steamsafe_zenity --pulsate --progress --auto-close --width=500 2>/dev/null)
	total_servers=$(echo "$response" | jq 'length' | numfmt --grouping)
	players_online=$(curl -Ls "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid=$aid" \
		| jq '.response.player_count' | numfmt --grouping)
	debug_log="$HOME/.local/share/dzgui/DEBUG.log"
	debug_servers
	local sel=$(munge_servers)
	if [[ -z $sel ]]; then
		unset filters
		unset search
		ret=98
		sd_res="--width=1280 --height=800"
		return
	fi
	local sel_ip=$(echo "$sel" | awk -F%% '{print $1}')
	local sel_port=$(echo "$sel" | awk -F%% '{print $2}')
	qport_list="$sel_ip%%$sel_port"
	if [[ -n "$sel_ip" ]]; then
		connect "$sel_ip" "ip"
		sd_res="--width=1280 --height=800"
	else
		sd_res="--width=1280 --height=800"
		return
	fi
}

mods_disk_size(){
	printf "Total size on disk: %s | " $(du -sh "$game_dir" | awk '{print $1}')
	printf "%s mods | " $(ls -1 "$game_dir" | wc -l)
	printf "Location: %s/steamapps/workshop/content/221100" "$steam_path"
}
main_menu(){
	print_news
	set_mode
	while true; do
		set_header ${FUNCNAME[0]}
	rc=$?
	if [[ $rc -eq 0 ]]; then
		if [[ -z $sel ]]; then
			warn "No item was selected."
		elif [[ $sel == "${items[0]}" ]]; then
			:
		elif [[ $sel == "${items[1]}" ]]; then
			server_browser
		elif [[ $sel == "${items[2]}" ]]; then
			query_and_connect
		elif [[ $sel == "${items[3]}" ]]; then
			connect_to_fav
		elif [[ $sel == "${items[4]}" ]]; then
			connect_by_ip
		elif [[ $sel == "${items[5]}" ]]; then
			history_table
		elif [[ $sel == "${items[6]}" ]]; then
			:
		elif [[ $sel == "${items[7]}" ]]; then
			add_by_id
		elif [[ $sel == "${items[8]}" ]]; then
			add_by_fav
		elif [[ $sel == "${items[9]}" ]]; then
			delete=1
			query_and_connect
		elif [[ $sel == "${items[10]}" ]]; then
			:
		elif [[ $sel == "${items[11]}" ]]; then
			list_mods | sed 's/\t/\n/g' | $steamsafe_zenity --list --column="Mod" --column="Symlink" --column="Dir" \
				--title="DZGUI" $sd_res --text="$(mods_disk_size)" \
				--print-column="" 2>/dev/null
		elif [[ $sel == "${items[12]}" ]]; then
			changelog | $steamsafe_zenity --text-info $sd_res --title="DZGUI" 2>/dev/null
		elif [[ $sel == "${items[13]}" ]]; then
			options_menu
			main_menu
			return
		elif [[ $sel == "${items[14]}" ]]; then
			:
		elif [[ $sel == "${items[15]}" ]]; then
			help_file
		elif [[ $sel == "${items[16]}" ]]; then
			report_bug
		elif [[ $sel == "${items[17]}" ]]; then
			forum
		else
			warn "This feature is not yet implemented."
		fi
	else
		return
	fi
	done
}
page_through(){
	list_response=$(curl -s "$page")
	list=$(echo "$list_response" | jq -r '.data[] .attributes | "\(.name)\t\(.ip):\(.port)\t\(.players)/\(.maxPlayers)\t\(.details.time)\t\(.status)\t\(.id)"')
	idarr+=("$list")
	parse_json
}
parse_json(){
	echo "# Parsing servers"
	page=$(echo "$list_response" | jq -r '.links.next?')
	if [[ $first_entry -eq 1 ]]; then
		local list=$(echo "$list_response" | jq -r '.data[] .attributes | "\(.name)\t\(.ip):\(.port)\t\(.players)/\(.maxPlayers)\t\(.details.time)\t\(.status)\t\(.id)"')
		idarr+=("$list")
		first_entry=0
	fi
	if [[ "$page" != "null" ]]; then
		page_through
	else
		printf "%s\n" "${idarr[@]}" > $tmp
		idarr=()
		fetch_query_ports
	fi
}
check_ping(){
	ping_ip=$(echo "$1" | awk -F'\t' '{print $2}' | awk -F: '{print $1}')
	ms=$(ping -c 1 -W 1 "$ping_ip" | awk -Ftime= '/time=/ {print $2}')
	if [[ -z $ms ]]; then
		echo "Timeout"
	else	
		echo "$ms"
	fi
}
create_array(){
	rows=()
	#TODO: improve error handling for null values
	lc=1
	while read line; do
		name=$(echo "$line" | awk -F'\t' '{print $1}')
		#truncate names
		if [[ $(echo "$name" | wc -m) -gt 50 ]]; then
			name="$(echo "$name" | awk '{print substr($0,1,50) "..."}')"
		else
			:
		fi
		ip=$(echo "$line" | awk -F'\t' '{print $2}')
		players=$(echo "$line" | awk -F'\t' '{print $3}')
		time=$(echo "$line" | awk -F'\t' '{print $4}')
		stat=$(echo "$line" | awk -F'\t' '{print $5}')

		#TODO: probe offline return codes
		id=$(echo "$line" | awk -F'\t' '{print $6}')
		tc=$(awk 'END{print NR}' $tmp)
		if [[ $delete -eq 1 ]]; then
			declare -g -a rows=("${rows[@]}" "$name" "$id")
		else
			echo "# Checking ping: $lc/$tc"
			ping=$(check_ping "$line")
			declare -g -a rows=("${rows[@]}" "$name" "$ip" "$players" "$time" "$stat" "$id" "$ping")
		fi
		let lc++
	done < <(cat "$tmp" | sort -k1)

	for i in "${rows[@]}"; do echo -e "$i"; done > $tmp
}
set_fav(){
	echo "[DZGUI] Querying favorite server"
	query_api
	fav_label=$(curl -s "$api" -H "Authorization: Bearer "$api_key"" -G -d "filter[game]=$game" -d "filter[ids][whitelist]=$fav" \
	| jq -r '.data[] .attributes .name')
	if [[ -z $fav_label ]]; then
		fav_label=null
	else
		fav_label="'$fav_label'"
	fi
}
check_unmerged(){
	if [[ -f ${config_path}.unmerged ]]; then
		printf "[DZGUI] Found new config format, merging changes\n"
		merge_config
		rm ${config_path}.unmerged
	fi
}
merge_config(){
	source $config_file
	mv $config_file ${config_path}dztuirc.old
	[[ -z $staging_dir ]] && staging_dir="/tmp"
	write_config > $config_file
	printf "[DZGUI] Wrote new config file to %sdztuirc\n" $config_path
	$steamsafe_zenity --info --width 500 --title="DZGUI" --text="Wrote new config format to \n${config_path}dztuirc\nIf errors occur, you can restore the file:\n${config_path}dztuirc.old" 2>/dev/null

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
		$steamsafe_zenity --question --width 500 --title="DZGUI" --text "DZGUI $upstream successfully downloaded.\nTo view the changelog, select Changelog.\nTo use the new version, select Exit and restart." --ok-label="Changelog" --cancel-label="Exit" 2>/dev/null
		code=$?
		if [[ $code -eq 0 ]]; then
			changelog | $steamsafe_zenity --text-info $sd_res --title="DZGUI" 2>/dev/null
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
	if [[ $branch == "stable" ]]; then
		version_url="$stable_url/dzgui.sh"
	elif [[ $branch == "testing" ]]; then
		version_url="$testing_url/dzgui.sh"
	fi
	upstream=$(curl -Ls "$version_url" | awk -F= '/^version=/ {print $2}')
}
enforce_dl(){
	download_new_version > >($steamsafe_zenity --progress --pulsate --auto-close --no-cancel --width=500)
}
prompt_dl(){
	$steamsafe_zenity --question --title="DZGUI" --text "Version conflict.\n\nYour branch:\t\t\t$branch\nYour version:\t\t\t$version\nUpstream version:\t\t$upstream\n\nVersion updates introduce important bug fixes and are encouraged.\n\nAttempt to download latest version?" --width=500 --ok-label="Yes" --cancel-label="No" 2>/dev/null
	rc=$?
	if [[ $rc -eq 1 ]]; then
		return
	else
		echo "100"
		download_new_version > >($steamsafe_zenity --progress --pulsate --auto-close --no-cancel --width=500)
	fi
}
check_version(){
	[[ -f $config_file ]] && source $config_file
	[[ -z $branch ]] && branch="stable"
	check_branch
	[[ ! -f "$freedesktop_path/dzgui.desktop" ]] && freedesktop_dirs
	if [[ $version == $upstream ]]; then
		check_unmerged
	else
#		echo "100"
		echo "[DZGUI] Upstream ($upstream) != local ($version)"
		if [[ $enforce_dl -eq 1 ]]; then
			enforce_dl
		else
			prompt_dl
		fi
	fi
}
check_architecture(){
	cpu=$(cat /proc/cpuinfo | grep "AMD Custom APU 0405")
	if [[ -n "$cpu" ]]; then
		is_steam_deck=1
		echo "[DZGUI] Setting architecture to 'Steam Deck'"
	else
		is_steam_deck=0
		echo "[DZGUI] Setting architecture to 'desktop'"
	fi
}
add_by_id(){
	#FIXME: prevent redundant creation of existent IDs (for neatness)
	while true; do
		id=$($steamsafe_zenity --entry --text="Enter server ID" --title="DZGUI" 2>/dev/null)
		rc=$?
		if [[ $rc -eq 1 ]]; then
			return
		else
			if [[ ! $id =~ ^[0-9]+$ ]]; then
				$steamsafe_zenity --warning --title="DZGUI" --text="Invalid ID" 2>/dev/null
			else
				[[ -z $whitelist ]] && new_whitelist="whitelist=\"$id\""
				[[ -n $whitelist ]] && new_whitelist="whitelist=\"$whitelist,$id\""
				mv $config_file ${config_path}dztuirc.old
				nr=$(awk '/whitelist=/ {print NR}' ${config_path}dztuirc.old)
				awk -v "var=$new_whitelist" -v "nr=$nr" 'NR==nr {$0=var}{print}' ${config_path}dztuirc.old > ${config_path}dztuirc
				$steamsafe_zenity --info --title="DZGUI" --text="Added "$id" to:\n${config_path}dztuirc\nIf errors occur, you can restore the file:\n${config_path}dztuirc.old" --width=500 2>/dev/null
				source $config_file
				return
			fi
		fi
	done
}
toggle_debug(){
	mv $config_file ${config_path}dztuirc.old
	nr=$(awk '/debug=/ {print NR}' ${config_path}dztuirc.old)
	if [[ $debug -eq 1 ]]; then
		debug=0
	else
		debug=1
	fi
	flip_debug="debug=\"$debug\""
	awk -v "var=$flip_debug" -v "nr=$nr" 'NR==nr {$0=var}{print}' ${config_path}dztuirc.old > $config_file
	printf "[DZGUI] Toggled debug flag to '$debug'\n"
	source $config_file

}
setup(){
	if [[ -n $fav ]]; then
		set_fav
		items[8]="	Change favorite server"
	fi
}
check_map_count(){
	local count=1048576
	echo "[DZGUI] Checking system map count"
	if [[ ! -f /etc/sysctl.d/dayz.conf ]]; then
		$steamsafe_zenity --question --width 500 --title="DZGUI" --cancel-label="Cancel" --ok-label="OK" --text "sudo password required to check system vm map count." 2>/dev/null
		if [[ $? -eq 0 ]]; then
			local pass
			pass=$($steamsafe_zenity --password)
			[[ $? -eq 1 ]] && exit 1
			local ct=$(sudo -S <<< "$pass" sh -c "sysctl -q vm.max_map_count | awk -F'= ' '{print \$2}'")
			local new_ct
			[[ $ct -lt $count ]] && ct=$count
			sudo -S <<< "$pass" sh -c "echo 'vm.max_map_count=$ct' > /etc/sysctl.d/dayz.conf"
			sudo sysctl -p /etc/sysctl.d/dayz.conf
		else
			exit 1
		fi
	fi
}
add_by_fav(){
while true; do
	fav_id=$($steamsafe_zenity --entry --text="Enter server ID" --title="DZGUI" 2>/dev/null)
	rc=$?
	if [[ $rc -eq 1 ]]; then
		return
	else
		if [[ ! $fav_id =~ ^[0-9]+$ ]]; then
			$steamsafe_zenity --warning --title="DZGUI" --text="Invalid ID"
		else
			new_fav="fav=\"$fav_id\""
			mv $config_file ${config_path}dztuirc.old
			nr=$(awk '/fav=/ {print NR}' ${config_path}dztuirc.old)
			awk -v "var=$new_fav" -v "nr=$nr" 'NR==nr {$0=var}{print}' ${config_path}dztuirc.old > ${config_path}dztuirc
			echo "[DZGUI] Added $fav_id to key 'fav'"
			$steamsafe_zenity --info --title="DZGUI" --text="Added "$fav_id" to:\n${config_path}dztuirc\nIf errors occurred, you can restore the file:\n${config_path}dztuirc.old" 2>/dev/null
			source $config_file
			set_fav
			items[8]="	Change favorite server"
			return
		fi
	fi
done
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
		echo "[DZGUI] Already running ($pid)"
		$steamsafe_zenity --info --text="DZGUI already running (pid $pid)" --width=500 --title="DZGUI" 2>/dev/null
		exit
	elif [[ $pid == $$ ]]; then
		:
	else
		echo $$ > ${config_path}.lockfile
	fi
}
fetch_helpers(){
	mkdir -p "$helpers_path"
	[[ ! -f "$helpers_path/vdf2json.py" ]] && curl -Ls "$vdf2json_url" > "$helpers_path/vdf2json.py"
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
	local flatpak steam
	[[ $(command -v flatpak) ]] && flatpak=$(flatpak list | grep valvesoftware.Steam)
	steam=$(command -v steam)
	if [[ -z "$steam" ]] && [[ -z "$flatpak" ]]; then
		warn "Requires Steam or Flatpak Steam"
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
	stale_symlinks
	init_items
	setup
	check_news
	echo "100"
}
main(){
	lock
	initial_setup > >($steamsafe_zenity --pulsate --progress --auto-close --title="DZGUI" --no-cancel --width=500 2>/dev/null)
	main_menu
	#TODO: tech debt: cruddy handling for steam forking
	[[ $? -eq 1 ]] && pkill -f dzgui.sh
}
parent=$(cat /proc/$PPID/comm)
main
