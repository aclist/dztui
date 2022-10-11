#!/bin/bash

set -o pipefail
version=3.0.1

aid=221100
game="dayz"
workshop="steam://url/CommunityFilePage/"
api="https://api.battlemetrics.com/servers"
sd_res="--width=1280 --height=800"
config_path="$HOME/.config/dztui/"
config_file="${config_path}dztuirc"
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
notify_url="$stable_url/helpers/d.html"
notify_img_url="$stable_url/helpers/d.webp"
forum_url="https://github.com/aclist/dztui/discussions"

update_last_seen(){
	mv $config_file ${config_path}dztuirc.old
	nr=$(awk '/seen_news=/ {print NR}' ${config_path}dztuirc.old)
	seen_news="seen_news=\"$sum\""
	awk -v "var=$seen_news" -v "nr=$nr" 'NR==nr {$0=var}{print}' ${config_path}dztuirc.old > $config_file
	printf "[DZGUI] Updated last seen news item to '$sum'\n"
	source $config_file
}
check_news(){
	[[ $branch == "stable" ]] && news_url="$stable_url/news"
	[[ $branch == "testing" ]] && news_url="$testing_url/news"
	result=$(curl -Ls "$news_url")
	sum=$(echo -n "$result" | md5sum | awk '{print $1}')
}
print_news(){
	check_news
	if [[ $sum == $seen_news || -z $result ]]; then 
		hchar=""
		news=""
	else
		hchar="─"
		news="$result\n$(awk -v var="$hchar" 'BEGIN{for(c=0;c<90;c++) printf var;}')\n"
		update_last_seen
	fi
}
#TODO: prevent connecting to offline servers
#TODO: abstract zenity title params and dimensions

declare -A deps
deps=([awk]="5.1.1" [curl]="7.80.0" [jq]="1.6" [tr]="9.0" [zenity]="3.42.1" [steam]="1.0.0")
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
		command -v $dep 2>&1>/dev/null || (printf "Requires %s >=%s\n" $dep ${deps[$dep]}; exit 1)
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
	"[Manage servers]"
	"	Connect by IP"
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
	"	Become a beta tester ⧉"
	)
}
warn_and_exit(){
	zenity --info --title="DZGUI" --text="$1" --width=500 --icon-name="dialog-warning" 2>/dev/null
	printf "[DZGUI] %s\n" "$check_config_msg"
	exit
}
warn(){
	zenity --info --title="DZGUI" --text="$1" --width=500 --icon-name="dialog-warning" 2>/dev/null
}
info(){
	zenity --info --title="DZGUI" --text="$1" --width=500 2>/dev/null
}
set_api_params(){
	response=$(curl -s "$api" -H "Authorization: Bearer "$api_key"" -G -d "sort=-players" \
		-d "filter[game]=$game" -d "filter[ids][whitelist]=$list_of_ids")
	list_response=$response
	first_entry=1
}
query_api(){
	#TODO: prevent drawing list if null values returned without API error
	if [[ $one_shot_launch -eq 1 ]]; then
		list_of_ids="$fav"
	else
		if [[ -n $fav ]]; then
			list_of_ids="$whitelist,$fav"
		else
			list_of_ids="$whitelist"
		fi
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
	img_url="https://raw.githubusercontent.com/aclist/dztui/testing/images"
	for i in dzgui grid.png hero.png logo.png; do
		curl -s "$img_url/$i" > "$sd_install_path/$i"
	done
	write_desktop_file > "$freedesktop_path/dzgui.desktop"
	if [[ $is_steam_deck -eq 1 ]]; then
		write_desktop_file > "$HOME/Desktop/dzgui.desktop"
	fi
}
file_picker(){
	while true; do
	local path=$(zenity --file-selection --directory 2>/dev/null)
		if [[ -z "$path" ]]; then
			return
		else
			echo "[DZGUI]" Set mod staging path to "$path"
			staging_dir="$path"
			write_config > $config_file
			return
		fi
	done
}
guess_path(){
	echo "# Checking for default DayZ path"
	path=$(find $HOME -type d -regex ".*/steamapps/common/DayZ$" -print -quit)
	if [[ -n "$path" ]]; then
		clean_path=$(echo -e "$path" | awk -F"/steamapps" '{print $1}')
		steam_path="$clean_path"
	else
		echo "# Searching for alternate DayZ path. This may take some time."
		path=$(find / -type d \( -path "/proc" -o -path "*/timeshift" -o -path "/tmp" -o -path "/usr" -o -path "/boot" -o -path "/proc" -o -path "/root" -o -path "/run" -o -path "/sys" -o -path "/etc" -o -path "/var" -o -path "/run" -o -path "/lost+found" \) -prune -o -regex ".*/steamapps/common/DayZ$" -print -quit 2>/dev/null)
			clean_path=$(echo -e "$path" | awk -F"/steamapps" '{print $1}')
			steam_path="$clean_path"
	fi
}
create_config(){
	while true; do
	player_input="$(zenity --forms --add-entry="Player name (required for some servers)" --add-entry="API key" --add-entry="Server 1 (you can add more later)" --title="DZGUI" --text="DZGUI" --add-entry="Server 2" --add-entry="Server 3" --add-entry="Server 4" $sd_res --separator="│" 2>/dev/null)"
	#explicitly setting IFS crashes zenity in loop
	#and mapfile does not support high ascii delimiters
	#so split fields with newline
	readarray -t args < <(echo "$player_input" | sed 's/│/\n/g')
	name="${args[0]}"
	api_key="${args[1]}"
	server_1="${args[2]}"
	server_2="${args[3]}"
	server_3="${args[4]}"
	server_4="${args[5]}"

	[[ -z $player_input ]] && exit
	if [[ -z $api_key ]]; then
		warn "API key: invalid value"
	elif [[ -z $server_1 ]]; then
		warn "Server 1: cannot be empty"
	elif [[ ! $server_1 =~ ^[0-9]+$ ]]; then
		warn "Server 1: only numeric IDs"
	elif [[ -n $server_2 ]] && [[ ! $server_2 =~ ^[0-9]+$ ]]; then
		warn "Server 2: only numeric IDs"
	elif [[ -n $server_3 ]] && [[ ! $server_3 =~ ^[0-9]+$ ]]; then
		warn "Server 3: only numeric IDs"
	elif [[ -n $server_4 ]] && [[ ! $server_3 =~ ^[0-9]+$ ]]; then
		warn "Server 4: only numeric IDs"
	else
	whitelist=$(echo "$player_input" | awk -F"│" '{OFS=","}{print $3,$4,$5,$6}' | sed 's/,*$//g' | sed 's/^,*//g')
	guess_path > >(zenity --width 500 --progress --auto-close --pulsate 2>/dev/null) &&
	echo "[DZGUI] Set path to $steam_path"
	#FIXME: tech debt: gracefully exit if user cancels search process
	mkdir -p $config_path; write_config > $config_file
	info "Config file created at $config_file."
	return
	fi
	done

}
err(){
	printf "[ERROR] %s\n" "$1"
}
varcheck(){
	[[ -z $api_key ]] && (err "Error in key: 'api_key'")
	[[ -z $whitelist ]] && (err "Error in key: 'whitelist'")
	[[ ! -d "$game_dir" ]] && (err "Malformed game path")
	[[ $whitelist =~ [[:space:]] ]] && (err "Separate whitelist values with commas")
}
run_depcheck(){
	if [[ -z $(depcheck) ]]; then 
		:
	else	
		echo "100"
		zenity --warning --ok-label="Exit" --title="DZGUI" --text="$(depcheck)"
		exit
	fi
}
run_varcheck(){
	source $config_file
	workshop_dir="$steam_path/steamapps/workshop/content/$aid"
	game_dir="$steam_path/steamapps/common/DayZ"
	if [[ -z $(varcheck) ]]; then
		:
	else	
		zenity --warning --width 500 --text="$(varcheck)" 2>/dev/null
		printf "[DZGUI] %s\n" "$check_config_msg"
		zenity --question --cancel-label="Exit" --text="Malformed config file. This is probably user error.\nStart first-time setup process again?" --width=500 2>/dev/null
		code=$?
		if [[ $code -eq 1 ]]; then
			exit
		else
			echo "100"
			create_config
		fi
	fi
}
config(){
	if [[ ! -f $config_file ]]; then
		zenity --width 500 --info --text="Config file not found. Click OK to proceed to first-time setup." 2>/dev/null
		code=$?
		#prevent progress if user hits ESC
		if [[ $code -eq 1 ]]; then
			exit
		else
			create_config
		fi
	else
		source $config_file
	fi

}
open_mod_links(){
	link_file=$(mktemp)
	echo "<html>" > $link_file
	echo "<title>DZGUI</title>" >> $link_file
	echo "<h1>DZGUI</h1>" >> $link_file
	echo "<p>Open these links and subscribe to them on the Steam Workshop, then continue with the application prompts.<br><b>Note:</b> it may take some time for mods to synchronize before DZGUI can see them.<br>It can help to have Steam in an adjacent window so that you can see the downloads completing.</p>" >> $link_file
	n=1
	for i in $diff; do
		echo "$n. <a href=\"${workshop}$i\">${workshop}$i</a><br>"
		let n++
	done >> $link_file
	echo "</html>" >> $link_file
	browser "$link_file" 2>/dev/null &

}
steam_deck_mods(){	
	until [[ -z $diff ]]; do
		next=$(echo -e "$diff" | head -n1)
		zenity --question --ok-label="Open" --cancel-label="Cancel" --title="DZGUI" --text="Missing mods. Click [Open] to open mod $next in Steam Workshop and subscribe to it by clicking the green Subscribe button. After the mod is downloaded, return to this menu to continue validation." --width=500 2>/dev/null
		rc=$?
		if [[ $rc -eq 0 ]]; then
			echo "[DZGUI] Opening ${workshop}$next"
			steam steam://url/CommunityFilePage/$next 2>/dev/null &
			zenity --info --title="DZGUI" --ok-label="Next" --text="Click [Next] to continue mod check." --width=500 2>/dev/null
		else
			return 1
		fi
		compare
	done
}
set_term(){
	local term="$1"
	local tterm="term=\"$term\""
	mv $config_file ${config_path}dztuirc.old
	nr=$(awk '/term=/ {print NR}' ${config_path}dztuirc.old)
	awk -v "var=$tterm" -v "nr=$nr" 'NR==nr {$0=var}{print}' ${config_path}dztuirc.old > $config_file
	printf "[DZGUI] Set term to '$term'\n"
	source $config_file
}
sel_term(){
	#only terminals known to support -e flag
	for i in "$TERMINAL" urxvt alacritty konsole gnome-terminal terminator xfce4-terminal xterm tilix; do
		[[ $(command -v $i) ]] && terms+=($i)
	done
	#FIXME: if no terms, error
	local terms=$(printf "%s\n" "${terms[@]}" | sort -u)
	term=$(echo "$terms" | zenity --list --column=Terminal --height=800 --width=1200 --text="Select your preferred terminal emulator to run steamcmd (setting will be saved)" --title=DZGUI 2>/dev/null)
}
calc_mod_sizes(){
	for i in "$diff"; do
	local mods+=$(grep -w "$i" /tmp/modsizes | awk '{print $1}')
	done
	totalmodsize=$(echo -e "${mods[@]}" | awk '{s+=$1}END{print s}')
}
term_params(){
	case $term in
		konsole) $term --hold -e "bash $helpers_path/scmd.sh $totalmodsize $1";;
		urxvt) $term -e bash -c "/$helpers_path/scmd.sh $totalmodsize $1";;
		alacritty) $term -e bash -c "/$helpers_path/scmd.sh $totalmodsize $1";;
		terminator|xterm|tilix|xfce4-terminal) $term -e "bash $helpers_path/scmd.sh $totalmodsize $1";;
	esac
}
auto_mod_install(){
	cmd=$(printf "%q " "$@")
	if [[ -z "$term" ]]; then
		if [[ $is_steam_deck -eq 1 ]]; then
			set_term konsole
			return 0
		else
			sel_term && set_term "$term"
		fi
	fi
	[[ -z "$term" ]] && return 1
	echo "[DZGUI] Kicking off auto mod script"
	calc_mod_sizes
	term_params "$cmd"
	compare
	if [[ -z $diff ]]; then
		passed_mod_check > >(zenity --pulsate --progress --auto-close --width=500 2>/dev/null)
		launch
	else
		warn "Auto mod installation failed or some mods missing.\nReverting to manual mode."
		return 1
	fi
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
			steam "steam://url/CommunityFilePage/${stage_mods[$i]}"
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
		watcher > >(zenity --pulsate --progress --auto-close --title="DZG Watcher" --width=500 2>/dev/null; rc=$?; [[ $rc -eq 1 ]] && touch $ex)
		compare
		if [[ -z $diff ]]; then
			passed_mod_check > >(zenity --pulsate --progress --auto-close --width=500 2>/dev/null)
			launch
		else
			return 1
		fi
	fi
}
#	if [[ $is_steam_deck -eq 0 ]]; then
#		open_mod_links
#		until [[ -z $diff ]]; do
#			zenity --question --title="DZGUI" --ok-label="Next" --cancel-label="Cancel" --text="Opened mod links in browser.\nClick [Next] when all mods have been subscribed to.\nThis dialog may reappear if clicking [Next] too soon\nbefore mods are synchronized in the background." --width=500 2>/dev/null
#			rc=$?
#			if [[ $rc -eq 0 ]]; then
#			compare
#			open_mod_links
#		else
#			return
#			fi
#		done
#	else
#		steam_deck_mods
#		rc=$?
#		[[ $rc -eq 1 ]] && return 1
#	fi
#	passed_mod_check > >(zenity --pulsate --progress --auto-close --width=500 2>/dev/null)
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
	stale_symlinks
	legacy_symlinks
	symlinks
	echo "100"

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
		fetch_mods_sa "$ip" > >(zenity --pulsate --progress --auto-close --no-cancel --width=500 2>/dev/null)
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
	if [[ -n $diff ]]; then
		if [[ $auto_install -eq 1 ]]; then
			auto_mod_install "$diff"
			rc=$?
			[[ $rc -eq 1 ]] && manual_mod_install
		else
			manual_mod_install
		fi
	else
		passed_mod_check > >(zenity --pulsate --progress --auto-close --width=500 2>/dev/null)
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
		zenity --error --title="DZGUI" --width=500 --text="[ERROR] 97: Failed to fetch modlist" 2>/dev/null &&
		ret=96
		return
	fi
	remote_mods=$(echo "$response" | jq -r '.result.mods[].steamWorkshopId')
	qport_arr=()
}
prepare_ip_list(){
	ct=$(< "$1" jq '[.response.servers[]]|length')
	for((i=0;i<$ct;i++));do
		name=$(< $json jq --arg i $i -r '[.servers[]][($i|tonumber)].name')
		addr=$(< $json jq --arg i $i -r '[.servers[]][($i|tonumber)].addr')
		ip=$(echo "$addr" | awk -F: '{print $1}')
		players=$(< $json jq --arg i $i -r '[.servers[]][($i|tonumber)].players')
		max_players=$(< $json jq --arg i $i -r '[.servers[]][($i|tonumber)].max_players')
		gameport=$(< $json jq --arg i $i -r '[.servers[]][($i|tonumber)].gameport')
		ip_port=$(echo "$ip:$gameport")
		time=$(< $json jq --arg i $i -r '[.servers[]][($i|tonumber)].gametype' | grep -oP '(?<!\d)\d{2}:\d{2}(?!\d)')
		echo "$name"
		echo "$ip_port"
		echo "$players/$max_players"
		echo "$time"
	done
}

ip_table(){
	while true; do
	sel=$(prepare_ip_list "$meta_file" | zenity --width 1200 --height 800 --list --column=Name --column=IP --column=Players --column=Gametime --print-column=2 --separator=%% 2>/dev/null)
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
	local meta_file=$(mktemp)
	source $config_file
	url="https://api.steampowered.com/IGameServersService/GetServerList/v1/?filter=\appid\221100\gameaddr\\$ip&key=$steam_api"
	curl -Ls "$url" > $meta_file
	json=$(mktemp)
	< $meta_file jq '.response' > $json
	res=$(< $meta_file jq -er '.response.servers[]' 2>/dev/null)
	if [[ ! $? -eq 0 ]]; then
		warn "[ERROR] 96: Failed to retrieve IP metadata. Check IP or API key and try again."
		echo "[DZGUI] 96: Failed to retrieve IP metadata"

	else
		ip_table
	fi
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
add_steam_api(){
		[[ $(test_steam_api) -eq 1 ]] && return 1
		mv $config_file ${config_path}dztuirc.old
		nr=$(awk '/steam_api=/ {print NR}' ${config_path}dztuirc.old)
		steam_api="steam_api=\"$steam_api\""
		awk -v "var=$steam_api" -v "nr=$nr" 'NR==nr {$0=var}{print}' ${config_path}dztuirc.old > ${config_path}dztuirc
		echo "[DZGUI] Added Steam API key"
		zenity --info --title="DZGUI" --text="Added Steam API key to:\n\n${config_path}dztuirc\nIf errors occur, you can restore the file:\n${config_path}dztuirc.old" 2>/dev/null
		source $config_file
}
check_steam_api(){
	if [[ -z $steam_api ]]; then
		steam_api=$(zenity --entry --text="Key 'steam_api' not present in config file. Enter Steam API key:" --title="DZGUI" 2>/dev/null)
		if [[ $? -eq 1 ]] ; then
			return
		elif [[ ${#steam_api} -lt 32 ]] || [[ $(test_steam_api) -eq 1 ]]; then
			zenity --warning --title="DZGUI" --text="Check API key and try again." 2>/dev/null
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
		ip=$(zenity --entry --text="Enter server IP (omit port)" --title="DZGUI" 2>/dev/null)
		[[ $? -eq 1 ]] && return
		if validate_ip "$ip"; then
			fetch_ip_metadata
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
	diff=$(comm -23 <(server_modlist | sort) <(installed_mods | sort))
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
		launch_options="steam -applaunch $aid -connect=$ip -nolauncher -nosplash -name=$name -skipintro \"-mod=$mods\""
		print_launch_options="$(printf "This is a dry run.\nThese options would have been used to launch the game:\n\n$launch_options\n" | fold -w 60)"
		zenity --question --title="DZGUI" --ok-label="Write to file" --cancel-label="Back"\
			--text="$print_launch_options" 2>/dev/null
		if [[ $? -eq 0 ]]; then
			source_script=$(realpath "$0")
			source_dir=$(dirname "$source_script")
			echo "$launch_options" > "$source_dir"/options.log
			echo "[DZGUI] Wrote launch options to $source_dir/options.log"
			zenity --info --width 500 --title="DZGUI" --text="Wrote launch options to \n$source_dir/options.log" 2>/dev/null
		fi

	else
		echo "[DZGUI] All OK. Launching DayZ"
		zenity --width 500 --title="DZGUI" --info --text="Launch conditions satisfied.\nDayZ will now launch after clicking [OK]." 2>/dev/null
		steam -applaunch $aid -connect=$ip -nolauncher -nosplash -skipintro -name=$name \"-mod=$mods\"
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
	new_whitelist="whitelist=\"$(echo "$whitelist" | sed "s/,$server_id$//;s/^$server_id,//;s/,$server_id,/,/")\""
	mv $config_file ${config_path}dztuirc.old
	nr=$(awk '/whitelist=/ {print NR}' ${config_path}dztuirc.old)
	awk -v "var=$new_whitelist" -v "nr=$nr" 'NR==nr {$0=var}{print}' ${config_path}dztuirc.old > ${config_path}dztuirc
	echo "[DZGUI] Removed $server_id from key 'whitelist'"
	zenity --info --title="DZGUI" --text="Removed "$server_id" from:\n${config_path}dztuirc\nIf errors occur, you can restore the file:\n${config_path}dztuirc.old" --width=500 2>/dev/null
	source $config_file
}
delete_or_connect(){
		if [[ $delete -eq 1 ]]; then
			server_name=$(echo "$sel" | awk -F"%%" '{print $1}')
			server_id=$(echo "$sel" | awk -F"%%" '{print $2}')
			zenity --question --text="Delete this server? \n$server_name"
			if [[ $? -eq 0 ]]; then
				delete_by_id $server_id
			fi
		else
			#hotfix for bug #36
			local lookup_ip=$(echo "$sel" | awk -F%% '{print $1}')
			local lookup_port=$(echo "$lookup_ip" | awk -F: '{print $2}')
			source $config_file
			file=$(mktemp)
			url="https://api.steampowered.com/IGameServersService/GetServerList/v1/?filter=\appid\221100\gameaddr\\$lookup_ip&key=$steam_api"
			curl -Ls "$url" > $file
			local qport_res=$(< $file jq -r --arg port $lookup_port '.response.servers[]|select(.gameport==($port|tonumber)).addr')
			local qport=$(echo "$qport_res" | awk -F: '{print $2}')
			qport_list="$lookup_ip%%$qport"
			connect "$qport_list" "ip"
			
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
		zenity --info --text="94: No mods currently installed or incorrect path given" $sd_res 2>/dev/null
	else
		for d in $(find $game_dir/* -maxdepth 1 -type l); do
			dir=$(basename $d)
			awk -v d=$dir -F\" '/name/ {printf "%s\t%s\n", $2,d}' "$gamedir"/$d/meta.cpp
		done | sort
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
	[[ $auto_install -eq 1 ]] && install_mode=auto
	[[ $auto_install -eq 0 ]] && install_mode=manual
	if [[ $1 == "delete" ]]; then
		sel=$(cat $tmp | zenity $sd_res --list $cols --title="DZGUI" --text="DZGUI $version | Mode: $mode | Branch: $branch | Mods: $install_mode | Fav: $fav_label" \
			--separator="$separator" --print-column=1,2 --ok-label="Delete" 2>/dev/null)
	elif [[ $1 == "populate" ]]; then
		sel=$(cat $tmp | zenity $sd_res --list $cols --title="DZGUI" --text="DZGUI $version | Mode: $mode | Branch: $branch | Mods: $install_mode | Fav: $fav_label" \
			--separator="$separator" --print-column=2,6 2>/dev/null)
	elif [[ $1 == "main_menu" ]]; then
		sel=$(zenity $sd_res --list --title="DZGUI" --text="${news}DZGUI $version | Mode: $mode | Branch: $branch | Mods: $install_mode | Fav: $fav_label" \
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
	Version: $version
	Branch: $branch
	Whitelist: $whitelist
	Path: $steam_path
	Linux: $(uname -mrs)

	Mods:
	$(list_mods)
	DOC
}
automods_prompt(){
cat <<- HERE

Auto-mod installation set to ON. This method is NOT supported in Game Mode (Steam Deck).

READ THIS FIRST:
With this setting on, DZGUI will attempt to download and prepare mods using Valve's steamcmd tool.

The first time this process is run, DZGUI will ask you to select a terminal emulator of your preference to spawn the installation routine. If you don't have a preference or don't know, you can pick any.

Installation will kick off in a separate window and may ask you for input such as your sudo password in order to install system packages and create the steamcmd user.

steamcmd itself will ask for your Steam credentials. This information is used directly by Valve's steamcmd tool to authenticate your account and let you download mods headlessly. steamcmd is an official program created by Valve and communicates only with their servers.

NOTE: it can take some time for large mods to download, and steamcmd will not inform you of activity until each one is finished downloading.

If your distribution is unsupported, you don't have enough disk space to stage all of the mods, or there are other problems, DZGUI will warn you and write a report to $HOME/.local/share/dzgui/helpers/SCMD.log. You can attach this file to a bug report.
HERE
}
toggle_automods(){
	mv $config_file ${config_path}dztuirc.old
	local nr=$(awk '/auto_install=/ {print NR}' ${config_path}dztuirc.old)
	if [[ $auto_install == "1"  ]]; then
		auto_install="0"
	else
		auto_install="1"
	fi
	local flip_state="auto_install=\"$auto_install\""
	awk -v "var=$flip_state" -v "nr=$nr" 'NR==nr {$0=var}{print}' ${config_path}dztuirc.old > $config_file
	printf "[DZGUI] Toggled auto-mod install to '$auto_install'\n"
	source $config_file
	local big_prompt
	[[ $is_steam_deck -eq 1 ]] && big_prompt="--width=800"
	[[ $auto_install == "1" ]] && zenity --info --text="$(automods_prompt)" $big_prompt 2>/dev/null
}
options_menu(){
	debug_list=(
		"Toggle branch"
		"Toggle debug mode"
		"Generate debug log"
		"Toggle auto-mod install (experimental)"
		"Set auto-mod staging directory [$staging_dir]"
		)
	debug_sel=$(zenity --list --width=1280 --height=800 --column="Options" --title="DZGUI" --hide-header "${debug_list[@]}" 2>/dev/null)
	if [[ $debug_sel == "${debug_list[0]}" ]]; then
		enforce_dl=1
		toggle_branch &&
		check_version
	elif [[ $debug_sel == "${debug_list[1]}" ]]; then
		toggle_debug
	elif [[ $debug_sel == "${debug_list[2]}" ]]; then
		source_script=$(realpath "$0")
		source_dir=$(dirname "$source_script")
		generate_log > "$source_dir/log"
		printf "[DZGUI] Wrote log file to %s/log\n" "$source_dir"
		zenity --info --width 500 --title="DZGUI" --text="Wrote log file to \n$source_dir/log" 2>/dev/null
	elif [[ $debug_sel == "${debug_list[3]}" ]]; then
		toggle_automods
	elif [[ $debug_sel == "${debug_list[4]}" ]]; then
		file_picker
	fi
}
query_and_connect(){
	query_api
	parse_json
	#TODO: create logger function
	if [[ ! $delete -eq 1 ]]; then
		echo "[DZGUI] Checking response time of servers"
		create_array | zenity --width 500 --progress --pulsate --title="DZGUI" --auto-close 2>/dev/null
	else
		create_array
	fi
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
	local map_sel=$(echo "$maps" | zenity --list --column="Check" --width=1200 --height=800 2>/dev/null --title="DZGUI" --text="Found $map_ct map types")
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
	printf "Players online: %s" "$players_online"
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
		run > >(zenity --pulsate --progress --auto-close --width=500 2>/dev/null)
	fi 
}
choose_filters(){
	if [[ $is_steam_deck -eq 0 ]]; then
		sd_res="--width=1920 --height=1080"
	fi
	sels=$(zenity --title="DZGUI" --text="Server search" --list --checklist --column "Check" --column "Option" --hide-header TRUE "All maps (untick to select from map list)" TRUE "Daytime" TRUE "Nighttime" False "Empty" False "Full" False "Low population" FALSE "Non-ASCII titles" FALSE "Keyword search" $sd_res 2>/dev/null)
	if [[ $sels =~ Keyword ]]; then
		search=$(zenity --entry --text="Search (case insensitive)" --width=500 --title="DZGUI" 2>/dev/null | awk '{print tolower($0)}')
		[[ -z $search ]] && { ret=97; return; }
	fi	
	[[ -z $sels ]] && return
	filters=$(echo "$sels" | sed 's/|/, /g;s/ (untick to select from map list)//')
	echo "[DZGUI] Filters: $filters"
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
		filter_maps > >(zenity --pulsate --progress --auto-close --width=500 2>/dev/null)
		disabled+=("All maps")
	fi
	[[ $ret -eq 97 ]] && return
	prepare_filters > >(zenity --pulsate --progress --auto-close --width=500 2>/dev/null)
	if [[ $(echo "$response" | jq 'length') -eq 0 ]]; then
		zenity --error --text="No matching servers" 2>/dev/null
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
	local sel=$(zenity --text="$(pagination)" --title="DZGUI" --list --column=Map --column=Name --column=Gametime --column=Players --column=Max --column=Distance --column=IP --column=Qport $sd_res --print-column=7,8 --separator=%% 2>/dev/null < <(while true; do cat $fifo; done))
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
		curl -Ls "$url" > $file
	}
	fetch > >(zenity --pulsate --progress --auto-close --width=500 2>/dev/null)
	response=$(< $file jq -r '.response.servers')
	total_servers=$(echo "$response" | jq 'length')
	players_online=$(echo "$response" | jq '.[].players' | awk '{s+=$1}END{print s}')
	debug_log="$HOME/.local/share/dzgui/DEBUG.log"
	debug_servers
	local sel=$(munge_servers)
	if [[ -z $sel ]]; then
		unset filters
		unset search
		ret=98
		return
	fi
	local sel_ip=$(echo "$sel" | awk -F%% '{print $1}')
	local sel_port=$(echo "$sel" | awk -F%% '{print $2}')
	qport_list="$sel_ip%%$sel_port"
	if [[ -n "$sel_ip" ]]; then
		connect "$sel_ip" "ip"
	else
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
	if [[ -n $fav ]]; then
		items[7]="	Change favorite server"
	fi
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
			:
		elif [[ $sel == "${items[5]}" ]]; then
			connect_by_ip
		elif [[ $sel == "${items[6]}" ]]; then
			add_by_id
		elif [[ $sel == "${items[7]}" ]]; then
			add_by_fav
		elif [[ $sel == "${items[8]}" ]]; then
			delete=1
			query_and_connect
		elif [[ $sel == "${items[9]}" ]]; then
			:
		elif [[ $sel == "${items[10]}" ]]; then
			list_mods | sed 's/\t/\n/g' | zenity --list --column="Mod" --column="Symlink" \
				--title="DZGUI" $sd_res --text="$(mods_disk_size)" \
				--print-column="" 2>/dev/null
		elif [[ $sel == "${items[11]}" ]]; then
			changelog | zenity --text-info $sd_res --title="DZGUI" 2>/dev/null
		elif [[ $sel == "${items[12]}" ]]; then
			options_menu
			main_menu
			return
		elif [[ $sel == "${items[13]}" ]]; then
			:
		elif [[ $sel == "${items[14]}" ]]; then
			help_file
		elif [[ $sel == "${items[15]}" ]]; then
			report_bug
		elif [[ $sel == "${items[16]}" ]]; then
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
	page=$(echo "$list_response" | jq -r '.links.next?')
	if [[ $first_entry -eq 1 ]]; then
		local list=$(echo "$list_response" | jq -r '.data[] .attributes | "\(.name)\t\(.ip):\(.port)\t\(.players)/\(.maxPlayers)\t\(.details.time)\t\(.status)\t\(.id)"')
		idarr+=("$list")
		first_entry=0
	fi
	if [[ "$page" != "null" ]]; then
		local list=$(echo "$list_response" | jq -r '.data[] .attributes | "\(.name)\t\(.ip):\(.port)\t\(.players)/\(.maxPlayers)\t\(.details.time)\t\(.status)\t\(.id)"')
		idarr+=("$list")
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
	list=$(cat $tmp) 
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

		#yad only
		#[[ $stat == "online" ]] && stat="<span color='#77ff33'>online</span>" || :

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
	done <<< "$list"

	for i in "${rows[@]}"; do echo -e "$i"; done > $tmp
}
set_fav(){
	#TODO: test API key here and return errors
	echo "[DZGUI] Querying favorite server"
	query_api
	fav_label=$(curl -s "$api" -H "Authorization: Bearer "$api_key"" -G -d "filter[game]=$game" -d "filter[ids][whitelist]=$fav" \
	| jq -r '.data[] .attributes .name')
	if [[ -z $fav_label ]]; then
		fav_label=null
	fi
	echo "[DZGUI] Setting favorite server to '$fav_label'"
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
	zenity --info --width 500 --title="DZGUI" --text="Wrote new config format to \n${config_path}dztuirc\nIf errors occur, you can restore the file:\n${config_path}dztuirc.old" 2>/dev/null

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
		zenity --question --width 500 --title="DZGUI" --text "DZGUI $upstream successfully downloaded.\nTo view the changelog, select Changelog.\nTo use the new version, select Exit and restart." --ok-label="Changelog" --cancel-label="Exit" 2>/dev/null
		code=$?
		if [[ $code -eq 0 ]]; then
			changelog | zenity --text-info $sd_res --title="DZGUI" 2>/dev/null
			exit
		elif [[ $code -eq 1 ]]; then
			exit
		fi
	else
		echo "100"
		mv $source_script.old $source_script
		zenity --info --title="DZGUI" --text "[ERROR] 99: Failed to download new version." 2>/dev/null
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
	download_new_version > >(zenity --progress --pulsate --auto-close --no-cancel --width=500)
}
prompt_dl(){
	zenity --question --title="DZGUI" --text "Version conflict.\n\nYour branch:\t\t\t$branch\nYour version\t\t\t$version\nUpstream version:\t\t$upstream\n\nVersion updates introduce important bug fixes and are encouraged.\n\nAttempt to download latest version?" --width=500 --ok-label="Yes" --cancel-label="No" 2>/dev/null
	rc=$?
	if [[ $rc -eq 1 ]]; then
		return
	else
		echo "100"
		download_new_version > >(zenity --progress --pulsate --auto-close --no-cancel --width=500)
	fi
}
check_version(){
	[[ -f $config_file ]] && source $config_file
	[[ -z $branch ]] && branch="stable"
	check_branch
	[[ ! -d "$freedesktop_path" ]] && freedesktop_dirs
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
		id=$(zenity --entry --text="Enter server ID" --title="DZGUI" 2>/dev/null)
		rc=$?
		if [[ $rc -eq 1 ]]; then
			return
		else
			if [[ ! $id =~ ^[0-9]+$ ]]; then
				zenity --warning --title="DZGUI" --text="Invalid ID" 2>/dev/null
			else
				new_whitelist="whitelist=\"$whitelist,$id\""
				mv $config_file ${config_path}dztuirc.old
				nr=$(awk '/whitelist=/ {print NR}' ${config_path}dztuirc.old)
				awk -v "var=$new_whitelist" -v "nr=$nr" 'NR==nr {$0=var}{print}' ${config_path}dztuirc.old > ${config_path}dztuirc
				echo "[DZGUI] Added $id to key 'whitelist'"
				zenity --info --title="DZGUI" --text="Added "$id" to:\n${config_path}dztuirc\nIf errors occur, you can restore the file:\n${config_path}dztuirc.old" --width=500 2>/dev/null
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
		items[7]="	Change favorite server"
	fi
}
check_map_count(){
	count=1048576
	echo "[DZGUI] Checking system map count"
	if [[ $(sysctl -q vm.max_map_count | awk -F"= " '{print $2}') -lt $count ]]; then 
		echo "100"
		map_warning=$(zenity --question --width 500 --title="DZGUI" --text "System map count must be $count or higher to run DayZ with Wine. Increase map count and make this change permanent? (will prompt for sudo password)" 2>/dev/null)
		if [[ $? -eq 0 ]]; then
			pass=$(zenity --password)
			sudo -S <<< "$pass" sh -c "echo 'vm.max_map_count=1048576' > /etc/sysctl.d/dayz.conf"
			echo ""

		fi
	fi
}
add_by_fav(){
while true; do
	fav_id=$(zenity --entry --text="Enter server ID" --title="DZGUI" 2>/dev/null)
	rc=$?
	if [[ $rc -eq 1 ]]; then
		return
	else
		if [[ ! $fav_id =~ ^[0-9]+$ ]]; then
			zenity --warning --title="DZGUI" --text="Invalid ID"
		else
			new_fav="fav=\"$fav_id\""
			mv $config_file ${config_path}dztuirc.old
			nr=$(awk '/fav=/ {print NR}' ${config_path}dztuirc.old)
			awk -v "var=$new_fav" -v "nr=$nr" 'NR==nr {$0=var}{print}' ${config_path}dztuirc.old > ${config_path}dztuirc
			echo "[DZGUI] Added $fav_id to key 'fav'"
			zenity --info --title="DZGUI" --text="Added "$fav_id" to:\n${config_path}dztuirc\nIf errors occurred, you can restore the file:\n${config_path}dztuirc.old" 2>/dev/null
			source $config_file
			set_fav
			items[7]="	Change favorite server"
			return
		fi
	fi
done
}
lock(){
	if [[ ! -f $config_path/.lockfile ]]; then
		touch $config_path/.lockfile
	fi
	pid=$(cat $config_path/.lockfile)
	ps -p $pid -o pid= >/dev/null 2>&1
	res=$?
	if [[ $res -eq 0 ]]; then
		echo "[DZGUI] Already running ($pid)"
		zenity --info --text="DZGUI already running (pid $pid)" --width=500 --title="DZGUI" 2>/dev/null
		exit
	elif [[ $pid == $$ ]]; then
		:
	else
		echo $$ > $config_path/.lockfile
	fi
}
fetch_scmd_helper(){
	mkdir -p "$helpers_path"
	curl -Ls "$scmd_url" > "$helpers_path/scmd.sh"
	chmod +x "$helpers_path/scmd.sh"
	[[ ! -f "$helpers_path/d.html" ]] && curl -Ls "$notify_url" > "$helpers_path/d.html"
	[[ ! -f "$helpers_path/d.webp" ]] && curl -Ls "$notify_img_url" > "$helpers_path/d.webp"
}
deprecation_warning(){
	warn(){
	cat <<- HERE
		IMPORTANT ANNOUNCEMENT
		(Steam API key not found)

		A Steam API key is now mandatory to run the app.
		The BM API returns incorrect mod data on some servers
		and cannot be relied upon for up to date information.

		Going forward, we will only use the BM API as a convenience
		function to manage server names and your favorite servers list,
		and migrate to indexing servers on an IP basis.

		This is a backend change. You can continue adding servers by ID,
		but we will retrieve information from Valve instead, as we do for the
		server browser and connect-by-ip methods.

		Click [OK] to open the help page describing how to set up your key.
		After you input a valid key, the app will resume.
		HERE
	}
	if [[ -z $steam_api ]]; then
		echo "100"
		local big_prompt
		[[ $is_steam_deck -eq 1 ]] && big_prompt="--width=800"
		zenity --info --text="$(warn)" $big_prompt
		key_setup_url="https://aclist.github.io/dzgui/dzgui.html#_api_key_server_ids"
		browser "$key_setup_url" 2>/dev/null &
		while true; do
			if [[ $(check_steam_api) ]]; then
				break
			fi
		done
	fi
}
initial_setup(){
	echo "# Initial setup"
	run_depcheck
	watcher_deps
	check_architecture
	check_version
	check_map_count
	config
	fetch_scmd_helper
	run_varcheck
	init_items
	setup
	deprecation_warning
	echo "100"
}
main(){
	lock
	initial_setup > >(zenity --pulsate --progress --auto-close --title="DZGUI" --width=500 2>/dev/null)
	main_menu
	#cruddy handling for steam forking
	[[ $? -eq 1 ]] && pkill -f dzgui.sh
}

main
#trap cleanup EXIT
