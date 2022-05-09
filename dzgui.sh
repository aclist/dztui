#!/bin/bash

set -eo pipefail
version=0.1.0
aid=221100
game="dayz"
workshop="https://steamcommunity.com/sharedfiles/filedetails/?id="
api="https://api.battlemetrics.com/servers"

#BEGIN CONFIG================
steam_path=""
workshop_dir="$steam_path/steamapps/workshop/content/$aid"
game_dir="$steam_path/steamapps/common/DayZ"
key=""
whitelist=""
fav=""
name="player"
separator="│"
#TODO: ping flag is unimplemented. Table creation requires rigid number of arguments. Add binary switch when constructing table
#ping=1
debug=0
#END CONFIG==================

export dzpipe=/tmp/dzfifo
export tmp=tmp/dz.tmp
[[ -p $dzpipe ]] && rm $dzpipe
mkfifo $dzpipe
exec 3<> $dzpipe
trap cleanup EXIT INT

declare -A deps
deps=([awk]="5.1.1" [curl]="7.80.0" [jq]="1.6" [tr]="9.0" [yad]="12.0")

depcheck(){
	for dep in "${!deps[@]}"; do
		command -v $dep 2>&1>/dev/null || (printf "[ERROR] Requires %s >= %s\n" $dep ${deps[$dep]} ; exit 1)
	done
}

logger(){
	printf "[DZGUI] %s\n" "$1"
}

query_api(){
	logger "Querying BattleMetrics"
	response=$(curl -s "$api" -H "Authorization: Bearer "$key"" -G -d "sort=-players" \
		-d "filter[game]=$game" -d "filter[ids][whitelist]=$whitelist")
	if [[ "$(jq -r 'keys[]' <<< "$response")" == "errors" ]]; then
		code=$(jq -r '.errors[] .status' <<< $response)
		refresh_yad
		#TODO: fix granular api codes
		err "Error $code: malformed API key"
	fi
#	elif [[ -z "$(jq -r '.data[]' <<< "$response")" ]]; then
#		refresh_yad
#		echo "Malformed server IDs" > $dzpipe
#		return 1
#	fi
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
		printf "[DZGUI] [DEBUG] steam -applaunch $aid -connect=$ip -nolauncher -nosplash -skipintro \"-mod=$mods\"\n"
	else
		steam -applaunch $aid -connect=$ip -nolauncher -nosplash -skipintro -name=$name \"-mod=$mods\"
		exit
	fi
}

fetch_mods(){
	remote_mods=$(curl -s "$api" -H "Authorization: Bearer "$key"" -G -d filter[ids][whitelist]="$1" -d "sort=-players" \
	| jq -r '.data[] .attributes .details .modIds[]')
}
#TODO: unimplemented
#symlinks(){
#	for d in "$workshop_dir"/*; do
#		id=$(awk -F"= " '/publishedid/ {print $2}' "$d"/meta.cpp | awk -F\; '{print $1}')
#		mod=$(awk -F\" '/name/ {print $2}' "$d"/meta.cpp | sed -E 's/[^[:alpha:]0-9]+/_/g; s/^_|_$//g')
#		link="@$id-$mod"
#		[[ -h "$game_dir/$link" ]] && : || 
#			printf "[INFO] Creating symlink for $mod\n"
#			ln -fs "$d" "$game_dir/$link"
#	done
#}

check_ping(){
		ping_ip=$(echo "$1" | awk -F'\t' '{print $2}' | awk -F: '{print $1}')
		ms=$(ping -c 1 "$ping_ip" | awk -Ftime= '/time=/ {print $2}')
		[[ -z $ms ]] && echo "Timeout" || echo "$ms"
}
create_array(){
	list=$(cat $tmp) 
	#TODO: improve error handling for null values
	logger "Formatting output"
	while read line; do
		name=$(echo "$line" | awk -F'\t' '{print $1}')
		if [[ $(echo "$name" | wc -m) -gt 30 ]]; then
			name="$(echo $name | awk '{print substr($0,1,30) "..."}')"
		else
			:
		fi
		ip=$(echo "$line" | awk -F'\t' '{print $2}')
		players=$(echo "$line" | awk -F'\t' '{print $3}')
		stat=$(echo "$line" | awk -F'\t' '{print $4}')
		[[ $stat == "online" ]] && stat="<span color='#77ff33'>online</span>" || :
		#TODO: probe offline return codes
		id=$(echo "$line" | awk -F'\t' '{print $5}')
		ping=$(check_ping "$line")
		declare -g -a rows=("${rows[@]}" "$name" "$ip" "$players" "$stat" "$id" "$ping")
	done <<< "$list"
}

parse_json(){
	logger "Checking ping"
	list=$(jq -r '.data[] .attributes | "\(.name)\t\(.ip):\(.port)\t\(.players)/\(.maxPlayers)\t\(.status)\t\(.id)"')
	echo -e "$list" > $tmp
}

refresh(){
	refresh_yad
	placeholder

	##
	query_api
	parse_json <<< "$response"
	create_array
	populate
	##

}
refresh_yad(){
	echo -e '\f' > $dzpipe
}
populate(){
	logger "Writing data to pipe"
	refresh_yad
	echo "${rows[@]}" > $k.tmp
	for f in "${rows[@]}"; do echo -e "$f"; done > $dzpipe
}

placeholder(){
	echo "Fetching data..." > $dzpipe
}
cleanup(){
	#while kill -0 $pid 2>/dev/null; do
	#	:
	#done
	rm -f $dzpipe 
	rm -f $tmp
	unset -f check_ping
	unset -f create_array
	unset -f placeholder
	unset -f populate
	unset -f query_api
	unset -f refresh
	unset -f refresh_yad
	#logger "Removing temp files"
}

export -f check_ping
export -f create_array
export -f placeholder
export -f populate
export -f query_api
export -f refresh
export -f refresh_yad


printsel(){
	#TODO: abstract configs
yad --listen --cycle-read --align=center --separator="" --list --multiple --column="Server":TEXT \
	--column="IP":TEXT --column="Players":TEXT --column="Status":TEXT --column="ID":TEXT --column="Ping":TEXT \
	--buttons-layout=start --button=Cancel:1 --button=Connect:0 --buttons-layout=end --button="Refresh":"bash -c refresh" \
	--text="DZGUI\t$version" --width=1200 --height=500 --separator="$separator" --center --no-escape 2>/dev/null < $dzpipe
}
connect(){
	#TODO: validate inputs with standalone function
	if [[ $? -eq 1 ]]; then 
		kill $spid
	else
		if [[ -z $1 ]]; then
			logger "Exiting with no selection"
			kill $spid
		else
		ip=$(echo "$1" | awk -F"$separator" '{print $2}')
		bid=$(echo "$1" | awk -F"$separator" '{print $5}')
		logger "Connecting to $bid @ $ip"
		fetch_mods "$bid"
		launch

		#TODO: symlink validation, mod validation
		fi
	fi
}
err(){
	printf "[ERROR] %s\n" "$1"
	cleanup
	exit
}
varcheck(){
	[[ -z $key ]] && (err "Missing API key")
	[[ -z $whitelist ]] && (err "Missing server IDs")
	[[ ! -d $workshop_dir ]] && (err "Malformed workshop path")
	[[ ! -d $game_dir ]] && (err "Malformed game path")
	[[ $whitelist =~ [[:space:]] ]] && (err "Separate whitelist values with commas")
	IFS=,
	[[ ! "${whitelist[*]}" =~ ${fav} ]] && (err "Fav key value not in whitelist")
	unset IFS
}
checks() {
	depcheck
	varcheck
}
main(){
	spid=$$
	checks
	refresh_yad
	placeholder
	connect "$(printsel)" &
	pid=$!

	###bundle these
	query_api
	parse_json <<< "$response"
	create_array 
	populate
	###end bundle
	wait $pid

}

main


