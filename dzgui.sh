#!/bin/bash

set -eo pipefail
version=1.0.1
aid=221100
game="dayz"
workshop="https://steamcommunity.com/sharedfiles/filedetails/?id="
api="https://api.battlemetrics.com/servers"
sd_res="--width=1280 --height=800"
config_path="$HOME/.config/dztui/"
config_file="${config_path}dztuirc"
tmp=/tmp/dztui.tmp
separator="%%"


declare -A deps
deps=([awk]="5.1.1" [curl]="7.80.0" [jq]="1.6" [tr]="9.0" [zenity]="3.42.1")

depcheck(){
	for dep in "${!deps[@]}"; do
		command -v $dep 2>&1>/dev/null || (printf "[ERROR] Requires %s >= %s\n" $dep ${deps[$dep]} ; exit 1)
	done
}

items=(
	"Launch server list"
	"Connect to favorite server (not implemented)"
	"Add server from ID (not implemented)"
	"List mods (not implemented)"
	"Open mod page (TEST)"
	"List system browser (TEST)"
	)

warn(){
	zenity --info --title="DZGUI" --text="$1" --icon-name="dialog-warning" 2>/dev/null
}
info(){
	zenity --info --title="DZGUI" --text="$1" --icon-name="network-wireless" 2>/dev/null
}
launch_in_bg(){
	info "$msg" &
	#TODO: use less brittle method
	msg_pid=$(pgrep zenity)
	${1} &
	pid=$!  
	while kill -0 $pid; do
		:
	done
	#TODO: suppress output
	#TODO: pid could be released to other process
	if [[ -n $msd_pid ]]; then
		kill -9 $msg_pid 1 >/dev/null 2>&1
	else
		:
	fi

}
query_api(){
	response=$(curl -s "$api" -H "Authorization: Bearer "$api_key"" -G -d "sort=-players" \
		-d "filter[game]=$game" -d "filter[ids][whitelist]=$whitelist")
	if [[ "$(jq -r 'keys[]' <<< "$response")" == "errors" ]]; then
		code=$(jq -r '.errors[] .status' <<< $response)
		#TODO: fix granular api codes
		#TODO: put into copiable text info box
		warn "Error $code: malformed API key"
	fi
}

#TODO: find default SD path
write_config(){
cat	<<-'END'

#Path to DayZ installation (change if using multiple SD cards)
steam_path="/home/deck/.local/share/Steam"
workshop_dir="$steam_path/steamapps/workshop/content/$aid"
game_dir="$steam_path/steamapps/common/DayZ"

#Your unique API key
api_key=""

#Comma-separated list of server IDs
whitelist=""

#Favorite server to fast-connect to (limit one)
fav=""

#Custom player name (optional, required by some servers)
name="player"

#Set to 1 to perform dry-run and print launch options
debug=0

#(Not implemented) Set to 0 to suppress ping attempt
ping=1

	END
}
create_config(){
	mkdir -p $config_path; write_config > $config_file
	info "Config file created at $config_file.\nFill in values and relaunch."
	exit

}
err(){
	printf "[ERROR] %s\n" "$1"
}
varcheck(){
	[[ -z $api_key ]] && (err "Error in key: 'api_key'")
	[[ -z $whitelist ]] && (err "Error in key: 'whitelist'")
	[[ ! -d $workshop_dir ]] && (err "Malformed workshop path")
	[[ ! -d $game_dir ]] && (err "Malformed game path")
	[[ $whitelist =~ [[:space:]] ]] && (err "Separate whitelist values with commas")
	IFS=,
	[[ ! "${whitelist[*]}" =~ ${fav} ]] && (err "Fav key value not in whitelist")
	unset IFS
}
checks() {
	if [[ -z $(depcheck) ]]; then 
		:
	else	
		zenity $sd_res --text-info --cancel-label="Exit" <<< $(depcheck)
	fi
	if [[ -z $(varcheck) ]]; then 
		:
	else	
		zenity $sd_res --text-info --cancel-label="Exit" <<< $(varcheck)
	fi
}
config(){
	if [[ ! -f $config_file ]]; then
		zenity --question --cancel-label="Exit" --text="Config file not found. Should DZGUI create one for you?"
		code=$?
		if [[ $code -eq 1 ]]; then
			exit
		else
			create_config
		fi
	else
		source $config_file
	fi

}
connect(){
		#TODO: sanitize/validate input, return if failing
		ip=$(echo "$1" | awk -F"$separator" '{print $1}')
		bid=$(echo "$1" | awk -F"$separator" '{print $2}')
		fetch_mods "$bid"
		launch

		#TODO: symlink validation, mod validation
}
fetch_mods(){
	remote_mods=$(curl -s "$api" -H "Authorization: Bearer "$api_key"" -G -d filter[ids][whitelist]="$1" -d "sort=-players" \
	| jq -r '.data[] .attributes .details .modIds[]')
}
concat_mods(){
	readarray -t serv <<< "$remote_mods"
	for i in "${serv[@]}"; do
		id=$(awk -F"= " '/publishedid/ {print $2}' "$workshop_dir"/$i/meta.cpp | awk -F\; '{print $1}')
		mod=$(awk -F\" '/name/ {print $2}' "$workshop_dir"/$i/meta.cpp | sed -E 's/[^[:alpha:]0-9]+/_/g; s/^_|_$//g')
		link="@$id-$mod;"
		echo -e "$link"
	done | tr -d '\n' | perl -ple 'chop'
}
launch(){
	mods=$(concat_mods)
	if [[ $debug -eq 1 ]]; then
		printf "[DEBUG] steam -applaunch $aid -connect=$ip -nolauncher -nosplash -skipintro \"-mod=$mods\"\n" | zenity --text-info $sd_res --title="DZGUI debug output"
	else
		steam -applaunch $aid -connect=$ip -nolauncher -nosplash -skipintro -name=$name \"-mod=$mods\"
		exit
	fi
}
test_mod_page(){
	steam steam://url/CommunityFilePage/498101407
}
test_browser(){
	#echo $BROWSER | zenity --text-info $sd_res
	steam steam://openurl/https://github.com/aclist/dztui/issues/9
}
set_mode(){
	if [[ $debug -eq 1 ]]; then
		mode=DEBUG
	else
		mode=normal
	fi
}
main_menu(){
	while true; do
	set_mode
	sel=$(zenity --width=1280 --height=800 --list --title="DZGUI" --text="DZGUI $version | Mode: $mode | Fav: (not implemented)" --cancel-label="Exit" --ok-label="Select" --column="Select launch option" "${items[@]}" 2>/dev/null)
	if [[ $? -eq 1 ]]; then
		exit
	elif [[ -z $sel ]]; then
		warn "No item was selected."
	elif [[ $sel == "Launch server list" ]]; then
		query_api
		parse_json <<< "$response"
		msg="Retrieving server list. This may take some time.\nThis window will close automatically if left open."
		launch_in_bg "create_array"
		populate
		return
	elif [[ $sel == "Open mod page (TEST)" ]]; then
		test_mod_page
	elif [[ $sel == "List system browser (TEST)" ]]; then
		test_browser
	else
		warn "This feature is not yet implemented."
	fi
	done
}
parse_json(){
	list=$(jq -r '.data[] .attributes | "\(.name)\t\(.ip):\(.port)\t\(.players)/\(.maxPlayers)\t\(.status)\t\(.id)"')
	echo -e "$list" > $tmp
}
check_ping(){
		ping_ip=$(echo "$1" | awk -F'\t' '{print $2}' | awk -F: '{print $1}')
		ms=$(ping -c 1 "$ping_ip" | awk -Ftime= '/time=/ {print $2}')
		if [[ -z $ms ]]; then
			echo "Timeout"
		else	
			echo "$ms"
		fi
}
populate(){
	while true; do
		#TODO: add boolean statement for ping flag; affects all column ordinal output
		cols="--column="Server" --column="IP" --column="Players" --column="Status" --column="ID" --column="Ping""
		sel=$(cat $tmp | zenity $sd_res --list $cols --separator=$separator --print-column=2,5 2>/dev/null)
		if [[ $? -eq 1 ]]; then 
			echo "should return to main menu"
			#TODO: drop back to main menu
			:
		elif [[ -z $sel ]]; then
			warn "No item was selected."
		else
			connect $sel
			return
		fi
	done
}
create_array(){
	list=$(cat $tmp) 
	#TODO: improve error handling for null values
	while read line; do
		name=$(echo "$line" | awk -F'\t' '{print $1}')
		#truncate names
		if [[ $(echo "$name" | wc -m) -gt 30 ]]; then
			name="$(echo $name | awk '{print substr($0,1,30) "..."}')"
		else
			:
		fi
		ip=$(echo "$line" | awk -F'\t' '{print $2}')
		players=$(echo "$line" | awk -F'\t' '{print $3}')
		stat=$(echo "$line" | awk -F'\t' '{print $4}')
		#yad only
		#[[ $stat == "online" ]] && stat="<span color='#77ff33'>online</span>" || :
		#TODO: probe offline return codes
		id=$(echo "$line" | awk -F'\t' '{print $5}')
		ping=$(check_ping "$line")
		declare -g -a rows=("${rows[@]}" "$name" "$ip" "$players" "$stat" "$id" "$ping")
	done <<< "$list"
	for i in "${rows[@]}"; do echo -e "$i"; done > $tmp
}
main(){
	#TODO: check for upstream version and prompt to download
	config
	checks
	main_menu
}

main
