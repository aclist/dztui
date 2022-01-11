#!/bin/bash
set -eo pipefail
version=0.2.2
aid=221100
game="dayz"
workshop="https://steamcommunity.com/sharedfiles/filedetails/?id="
api="https://api.battlemetrics.com/servers"

#BEGIN CONFIG================
steam_path="/path/to/steam"
workshop_dir="$steam_path/steamapps/workshop/content/$aid"
game_dir="$steam_path/steamapps/common/DayZ"
key="APIKEY"
whitelist="8039514,8789747,4363928,8199330,11359652,12862329"
fav="8789747"
name="player"
separator="│"
ping=1
debug=0
#END CONFIG================

#STEAMCMD CONFIG===========
auto_install_mods=0
steamcmd_user="steam"
steam_username="STEAMUSER"
staging_dir="/tmp"
#END STEAMCMD CONFIG=======

declare -A deps
deps=([awk]="5.1.1" [curl]="7.80.0" [jq]="1.6" [column]="2.37.2" [tr]="9.0" [comm]="9.0")
max_range=$(awk -F, '{print NF}' <<< $whitelist)

depcheck(){
	for dep in "${!deps[@]}"; do
		command -v $dep 2>&1>/dev/null || (printf "[ERROR] Requires %s >= %s\n" $dep ${deps[$dep]} ; exit 1)
	done
}
err(){
	printf "[ERROR] %s\n" "$1"
	return 1
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
	varcheck
}
check_ping(){
	if [[ $ping -eq 1 ]]; then
		ping_ip=$(echo -e "$i" | awk -F'\t' '{print $2}' | awk -F: '{print $1}')
		ms=$(ping -c 1 "$ping_ip" | awk -Ftime= '/time=/ {print $2}')
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
symlinks(){
	for d in "$workshop_dir"/*; do
		id=$(awk -F"= " '/publishedid/ {print $2}' "$d"/meta.cpp | awk -F\; '{print $1}')
		mod=$(awk -F\" '/name/ {print $2}' "$d"/meta.cpp | sed -E 's/[^[:alpha:]0-9]+/_/g; s/^_|_$//g')
		link="@$id-$mod"
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
	for i in $diff; do
		printf "%s%s\n" "$workshop" $i
	done
}
steamcmd_modlist(){
	for i in $diff; do
	printf "+workshop_download_item %s %s " $aid $i
	done
}
move_files(){
	sudo chown -R $USER:$gid "$staging_dir"/steamapps
	mv "$staging_dir"/steamapps/workshop/content/$aid/* "$workshop_dir"
	rm -r "$staging_dir"/steamapps
}
auto_mod_download(){
	sudo -u $steamcmd_user steamcmd "steamcmd +force_install_dir $staging_dir +login $steam_username $(steamcmd_modlist) +quit"
	[[ "$(ls -A $staging_dir/steamapps)" ]] && move_files || return 1
}
auto_mod_install(){
	printf "[ERROR] Missing mods. Invoking steamcmd for user $steamcmd_user\n"
	if [[ -z $steamcmd_user ]]; then 
		err "steamcmd user value was empty. Reverting to manual mode"
	elif
		id $steamcmd_user &>/dev/null
		[[ $? -eq 1 ]]; then
		err "Invalid steamcmd user. Reverting to manual mode"
	elif
		command -v steamcmd &>/dev/null
		[[ $? -eq 1 ]]; then
		err "steamcmd not found. See: https://developer.valvesoftware.com/wiki/SteamCMD"
	else
		printf "[INFO] Found steamcmd user. Downloading mods\n"
		revert_msg="Something went wrong. Reverting to manual mode"
		auto_mod_download
		[[ $? -eq 0 ]] && printf "\n"; init_table || err "$revert_msg"
	fi

}
failed_mod_check(){
	[[ $auto_install_mods -eq 1 ]] && auto_mod_install || manual_mod_install
}
passed_mod_check(){
	printf "[INFO] Mod check passed\n"
	connecting_to=$(echo -e "${tabled[$sel]}" | awk -F'\t' '{print $1,$2}')
	symlinks
	launch

}
compare(){
	fetch_mods
	diff=$(comm -23 <(echo -e "$remote_mods" | sort) <(installed_mods | sort))
}
connect(){
	compare
	if [[ -n $diff ]]; then
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
		printf "[ERROR] %s: check API key\n" "$(jq -r '.errors[] .status' <<< $response)"
		return 1
	elif 
		[[ -z "$(jq -r '.data[]' <<< $response)" ]]; then
		printf "[ERROR] Check server ID\n"
		return 1
	fi
}
init_table(){
	printf "\n[INFO] Polling servers. Please wait.\n"
	query_api
	readarray -t tabled <<< $(parse_json <<< $response)
	tput cuu1
	tput el
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
	printf "q$separator Quit\n"
	printf "\n"
}
exit_msg(){
	printf "DZTUI $version\n"
	exit
}
main(){
	checks
	init_table
	while true; do
		printf "\n"
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
				q) exit ;;
				*) : ;;
			esac
		fi
	done
}
main
