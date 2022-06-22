#!/bin/bash
set -eo pipefail
version=0.7.1
release_url="https://raw.githubusercontent.com/aclist/dztui/main/dztui.sh"
aid=221100
game="dayz"
workshop="https://steamcommunity.com/sharedfiles/filedetails/?id="
api="https://api.battlemetrics.com/servers"

#BEGIN CONFIG================
steam_path="/path/to/steam"
workshop_dir="$steam_path/steamapps/workshop/content/$aid"
game_dir="$steam_path/steamapps/common/DayZ"
key="APIKEY"
whitelist=""
fav=""
name="player"
separator="│"
ping=1
debug=0
#END CONFIG================

#STEAMCMD CONFIG===========
auto_install_mods=1
steamcmd_user="steam"
steam_username="STEAMUSER"
staging_dir="/tmp"
#END STEAMCMD CONFIG=======

declare -A deps
deps=([awk]="5.1.1" [curl]="7.80.0" [jq]="1.6" [column]="2.37.2" [tr]="9.0" [comm]="9.0")
max_range=$(awk -F, '{print NF}' <<< $whitelist)
[[ $debug -eq 0 ]] && mode=Normal || mode=Debug

err(){
	printf "[ERROR] %s\n" "$1"
	return 1
}
download_new_version(){
	source_script=$(realpath "$0")
	source_dir=$(dirname "$source_script")
	mv $source_script $source_script.old
	curl -Ls "$release_url" > $source_script
	rc=$?
	if [[ $rc -eq 0 ]]; then
		printf "[INFO] Wrote %s to %s\n" $upstream "$source_script"
		printf "[INFO] Restart app to use new version\n"
		chmod +x $source_script
		exit
	else
		mv $source_script.old $source_script
		err "Failed to download new version. Reverting to prior version and quitting."
		exit
	fi
}
version_check(){
	upstream=$(curl -Ls "$release_url" | awk -F= 'NR==3 {print $2}')
	printf "[INFO] Checking for new version\n"
	if [[ ! $upstream == "$version" ]]; then
		printf "[INFO] A newer version of DZTUI is available (%s)\n" $upstream
		while true; do 
			read -p "Attempt to download new version? [Y/n] " response
			if [[ $response == "Y" ]]; then 
				download_new_version
			elif [[ $response == "n" ]]; then
				break
			else 
			       :
			fi
		done
	fi
}
depcheck(){
	for dep in "${!deps[@]}"; do
		command -v $dep 2>&1>/dev/null || (printf "[ERROR] Requires %s >= %s\n" $dep ${deps[$dep]} ; exit 1)
	done
}
column_check(){
	echo foo | column -o$'\t' &>/dev/null || err "column version >= 2.37.2 required"
}
varcheck(){
	[[ -z $key ]] && (err "Missing API key")
	[[ -z $whitelist ]] && (err "Missing server IDs")
	[[ ! -d $workshop_dir ]] && (err "Malformed workshop path")
	[[ ! -d $game_dir ]] && (err "Malformed game path")
	[[ $whitelist =~ [[:space:]] ]] && (err "Separate whitelist values with commas")
	IFS=,
	[[ ! "${whitelist[*]}" =~ "${fav}" ]] && (err "Fav key value not in whitelist")
	unset IFS
}
checks() {
	depcheck
	column_check
	version_check
	varcheck
}
check_ping(){
	if [[ $ping -eq 1 ]]; then
		ping_ip=$(echo -e "$i" | awk -F'\t' '{print $2}' | awk -F: '{print $1}')
		ms=$(ping -c 1 -W 1 "$ping_ip" | awk -Ftime= '/time=/ {print $2}')
		[[ -z $ms ]] && ms="Timeout" || :
		printf "%s\t%s\n" "$i" "$ms"
	else
		printf "%s\n" "$i"
	fi
}
parse_json(){
	list=$(jq -r '.data[] .attributes | "\(.name)\t\(.ip):\(.port)\t\(.players)/\(.maxPlayers)\t\(.status)\t\(.id)"')
	readarray -t list <<< $list
	for i in "${list[@]}"; do
		check_ping
	done
}
encode(){
	echo "$1" | awk '{printf("%c",$1)}' | base64 | sed 's/\//_/g; s/=//g; s/+/]/g'
}
legacy_symlinks(){
	for d in "$game_dir"/*; do
		if [[ $d =~ @[0-9]+-.+ ]]; then
			unlink "$d"
		fi
	done
}
symlinks(){
	for d in "$workshop_dir"/*; do
		id=$(awk -F"= " '/publishedid/ {print $2}' "$d"/meta.cpp | awk -F\; '{print $1}')
		encoded_id=$(encode "$id")
		mod=$(awk -F\" '/name/ {print $2}' "$d"/meta.cpp | sed -E 's/[^[:alpha:]0-9]+/_/g; s/^_|_$//g')
		link="@$encoded_id"
		[[ -h "$game_dir/$link" ]] && : || 
			printf "[INFO] Creating symlink for $mod\n"
			ln -fs "$d" "$game_dir/$link"
	done
}
installed_mods(){
	ls -1 "$workshop_dir"
}

list_mods(){
	printf "Installed mods: "
	for d in $(installed_mods); do
		awk -F\" '/name/ {print $2}' "$workshop_dir"/$d/meta.cpp
	done | sort | awk 'NR > 1 { printf(", ") } {printf("%s",$0)}'
	printf "\n"
}

columnize(){
       	column -t -s$'\t' -o$" $separator "
}
test_fav(){
	if [[ -n $fav ]]; then
		if [[ $(echo -e "${tabled[$i]}" | awk -F'\t' -v fav=$fav '$5 == fav') ]] ; then
			printf "%s│▶%s\n" "$i" "${tabled[$i]}"
		else
			printf "%s│ %s\n" "$i" "${tabled[$i]}"
		fi
	else
		printf "%s│ %s\n" "$i" "${tabled[$i]}"
	fi
}
table(){
	range=$((${#tabled[@]} - 1))
	for ((i=0;i<="$range";i++)); do
		test_fav
	done 
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
	mods=$(concat_mods)
	ip=$(echo -e "${tabled[$sel]}" | awk -F'\t' '{print $2}')
	printf "[INFO] Connecting to: $connecting_to\n"
	if [[ $debug -eq 1 ]]; then
		printf "[DEBUG] steam -applaunch $aid -connect=$ip -nolauncher -nosplash -skipintro \"-mod=$mods\"\n"
	else
		steam -applaunch $aid -connect=$ip -nolauncher -nosplash -skipintro -name=$name \"-mod=$mods\"
		printf "Good luck out there. DZTUI $version\n"
		exit
	fi
}
launch_fav(){
	if [[ -n $fav ]]; then
		sorted_id=$fav
		sel=$(table | awk -F'\t' -v fav=$fav '$5 == fav {print substr($1,1,1)}')
		connect
	else
		printf "[INFO] No favorite set\n"
	fi
}
manual_mod_install(){
	printf "[ERROR] Missing mods. Open these links and subscribe to each one, then reconnect\n"
	for i in $(diff); do
		printf "%s%s\n" "$workshop" $i
	done
}
steamcmd_modlist(){
	for i in $(diff); do
	printf "+workshop_download_item %s %s validate " $aid $i
	done
}
move_files(){
	sudo chown -R $USER:$gid "$staging_dir"/steamapps
	cp -R "$staging_dir"/steamapps/workshop/content/$aid/* "$workshop_dir"
	rm -r "$staging_dir"/steamapps
}
auto_mod_download(){
	if [[ -d "$staging_dir/steamapps" ]]; then
		sudo chown -R $USER:$gid "$staging_dir"/steamapps
		rm -r "$staging_dir"/steamapps
	fi
	until [[ -z $(diff) ]]; do
	printf "[INFO] Downloading missing mods\n"
	sudo -iu steam bash -c "$steamcmd_path +force_install_dir $staging_dir +login $steam_username $(steamcmd_modlist) +quit" $steamcmd_user
	printf "\n"
	[[ "$(ls -A $staging_dir/steamapps)" ]] && move_files || return 1
	done
}
find_steam_cmd(){
	for i in  "/home/steam" "/usr/share" "/usr/bin" "/"; do
		steamcmd_path=$(sudo find "$i" -name steamcmd.sh 2>/dev/null | grep -v linux32 | head -n1)
		if [[ -n "$steamcmd_path" ]]; then
			printf "[INFO] Found steamcmd at '$steamcmd_path'\n"
			return 0
		else
			return 1
		fi
	done 
}
auto_mod_install(){
	printf "[ERROR] Missing mods. Checking for steamcmd user '$steamcmd_user'\n"
	if [[ -z $steamcmd_user ]]; then 
		err "steamcmd user value was empty. Reverting to manual mode"
	elif
		id $steamcmd_user &>/dev/null
		[[ $? -eq 1 ]]; then
		err "Invalid steamcmd user. Reverting to manual mode"
	else
		printf "[INFO] Found steamcmd user '$steamcmd_user'\n"
	fi
	find_steam_cmd
	if [[ $? -eq 1 ]]; then
		err "steamcmd not found. See: https://developer.valvesoftware.com/wiki/SteamCMD"
	else
		revert_msg="Something went wrong. Reverting to manual mode"
		auto_mod_download
		if [[ $? -eq 0 ]]; then 
			printf "\n"
			passed_mod_check
		else
			err "$revert_msg"
		fi
	fi

}
failed_mod_check(){
	disksize=$(df $staging_dir --output=avail | tail -n1)
	bytewise=$((disksize * 1024))
	hr=$(echo $(numfmt --to=iec --format "%8.1f" $bytewise $totalmodsize) | sed 's/ /\//')
	if [[ $auto_install_mods -eq 1 ]]; then
		if [[ $totalmodsize -gt $bytewise ]]; then 
			printf "[ERROR] Not enough space in /tmp to automatically stage mods: %s\n" $hr
			manual_mod_install
		else
			auto_mod_install
		fi
	fi
	
}
passed_mod_check(){
	printf "[INFO] Mod check passed\n"
	connecting_to=$(echo -e "${tabled[$sel]}" | awk -F'\t' '{print $1,$2}')
	legacy_symlinks
	symlinks
	launch

}
query_defunct(){
	max=${#modlist[@]}
	printf "[INFO] Verifying integrity of server modlist manifest\n"
	tput cnorm
	#printf "\n"
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
	readarray -t newlist <<< $(echo -e "$result" | awk '{print $2}')
	totalmodsize=$(echo -e "$result" | awk '{s+=$1}END{print s}')
}
validate_mods(){
	url="https://steamcommunity.com/sharedfiles/filedetails/?id="
	aid=221100
	tput civis
	newlist=()
	readarray -t modlist <<< $remote_mods
	query_defunct
}
server_modlist(){
	for i in "${newlist[@]}"; do
		printf "$i\n"
	done
}
diff(){
	comm -23 <(server_modlist | sort) <(installed_mods | sort)
}
compare(){
	fetch_mods
	validate_mods
}
connect(){
	compare
	if [[ -n $(diff) ]]; then
		failed_mod_check
	else
		passed_mod_check
	fi
}
fetch_mods(){
	remote_mods=$(curl -s "$api" -H "Authorization: Bearer "$key"" -G -d filter[ids][whitelist]="$sorted_id" -d "sort=-players" \
	| jq -r '.data[] .attributes .details .modIds[]')
}
query_api(){
	response=$(curl -s "$api" -H "Authorization: Bearer "$key"" -G -d "sort=-players" \
		-d "filter[game]=$game" -d "filter[ids][whitelist]=$whitelist")
	if [[ "$(jq -r 'keys[]' <<< $response)" == "errors" ]]; then
		printf "\n"
		printf "[ERROR] %s: check API key\n" "$(jq -r '.errors[] .status' <<< $response)"
		tput cnorm
		return 1
	elif 
		[[ -z "$(jq -r '.data[]' <<< $response)" ]]; then
		printf "[ERROR] Check server ID\n"
		tput cnorm
		return 1
	fi
}
init_table(){
	tput civis
	printf "[INFO] Polling servers. Please wait.\n"
	query_api
	readarray -t tabled <<< $(parse_json <<< $response)
	tput cnorm
	tput cuu1
	tput el
	printf "\n"
	table | columnize
}
get_sorted_id(){
	sorted_id=$(echo -e "${tabled[$sel]}" | awk -F'\t' '{print $5}')
}
menu(){
	printf "\n"
	printf "f$separator Launch favorite\n"
	printf "l$separator List installed mods\n"
	printf "r$separator Refresh\n"
	if [[ $debug -eq 1 ]]; then
	printf "d$separator Debug options\n"
	fi
	printf "q$separator Quit\n"
	printf "\n"
}
exit_msg(){
	exit
}
forced_exit(){
	tput cnorm
	printf "\n"
	exit_msg
}
list_mod_names(){
	cd $game_dir
	for i in $(find * -maxdepth 1 -type l); do
		awk -F"[=;]" -v var="$i" '{OFS="\t"}/name/ {a=$2}END{print var,a}' "$i"/meta.cpp \
			| sed 's/;$//g' 
	done | column -t -s$'\t' -o$'\t' | less
}
debug_options(){
	if [[ $debug -eq 1 ]]; then
		while true; do
			printf "\n"
			printf "1$separator List human readable mod paths\n"
			printf "q$separator Back\n"
			printf "\n"
			read -p "Selection: " option
			if [[ $option == 1 ]]; then
				list_mod_names
			elif [[ $option == q ]]; then
				return
			else
				:
			fi
		done
	else
		:
	fi
}
main(){
	checks
	init_table
	while true; do
		menu
		printf "[DZTUI $version/$mode]\n"
		read -p "Selection: " sel
		if [[ $sel =~ ^[0-9]+$ ]]; then
			if [[ $sel -gt $max_range ]]; then
				:
			else
				get_sorted_id
				connect
			fi
		else
			case $sel in
				r) init_table ;;
				f) launch_fav ;;
				l) list_mods ;;
				d) debug_options;;
				q) exit_msg ;;
				*) : ;;
			esac
		fi
	done
}
trap forced_exit INT
main
