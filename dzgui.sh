#!/bin/bash

set -o pipefail
version=2.4.0-rc.13
aid=221100
game="dayz"
workshop="steam://url/CommunityFilePage/"
api="https://api.battlemetrics.com/servers"
sd_res="--width=1280 --height=800"
config_path="$HOME/.config/dztui/"
config_file="${config_path}dztuirc"
tmp=/tmp/dztui.tmp
separator="%%"
git_url="https://github.com/aclist/dztui/issues"
stable_url="https://raw.githubusercontent.com/aclist/dztui/dzgui/dzgui.sh"
testing_url="https://raw.githubusercontent.com/aclist/dztui/testing/dzgui.sh"
help_url="https://aclist.github.io/dzgui/dzgui"
check_config_msg="Check config values and restart."
news_url="https://raw.githubusercontent.com/aclist/dztui/dzgui/news"
freedesktop_path="$HOME/.local/share/applications"

update_last_seen(){
	mv $config_file ${config_path}dztuirc.old
	nr=$(awk '/seen_news=/ {print NR}' ${config_path}dztuirc.old)
	seen_news="seen_news=\"$sum\""
	awk -v "var=$seen_news" -v "nr=$nr" 'NR==nr {$0=var}{print}' ${config_path}dztuirc.old > $config_file
	printf "[DZGUI] Updated last seen news item to '$sum'\n"
	source $config_file
}
check_news(){
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
#TODO: abstract zenity title params

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
init_items(){
	#array order determines menu selector; this is destructive
items=(
	"Launch server list"
	"Quick connect to favorite server"
	"Add server by ID"
	"Add favorite server"
	"Delete server"
	"List installed mods"
	"Toggle debug mode"
	"Report bug (opens in browser)"
	"Help file (opens in browser)"
	"View changelog"
	)
}
exit_and_cleanup(){
	#TODO: this is currently unused
	rm $tmp
	rm $link_file
}
warn_and_exit(){
	zenity --info --title="DZGUI" --text="$1" --icon-name="dialog-warning" 2>/dev/null
	printf "[DZGUI] %s\n" "$check_config_msg"
	exit
}
warn(){
	zenity --info --title="DZGUI" --text="$1" --icon-name="dialog-warning" 2>/dev/null
}
info(){
	zenity --info --title="DZGUI" --text="$1" 2>/dev/null
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
	response=$(curl -s "$api" -H "Authorization: Bearer "$api_key"" -G -d "sort=-players" \
		-d "filter[game]=$game" -d "filter[ids][whitelist]=$list_of_ids")
	if [[ "$(jq -r 'keys[]' <<< "$response")" == "errors" ]]; then
		code=$(jq -r '.errors[] .status' <<< $response)
		#TODO: fix granular api codes
		if [[ $code -eq 401 ]]; then
			warn_and_exit "Error $code: malformed API key"
		elif [[ $code -eq 500 ]]; then
			warn_and_exit "Error $code: malformed server list"
		fi

	fi
	if [[ -z $(echo $response | jq '.data[]') ]]; then
		warn_and_exit "API returned empty response. Check config file."
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
	END
}
write_desktop_file(){
cat	<<-END
[Desktop Entry]
Version=1.0
Type=Application
Terminal=false
Exec=/home/deck/Downloads/dzgui.sh
Name=DZGUI
Comment=dzgui
Icon=$HOME/.local/share/dzgui/dzgui
Categories=Game
	END
}
guess_path(){
	if [[ $is_steam_deck -eq 1 ]]; then
		mkdir -p $HOME/.local/share/dzgui
		mkdir -p "$freedesktop_path"
		#TODO: update url
		img_url="https://github.com/aclist/dztui/raw/testing/images"
		for i in dzgui grid.png hero.png logo.png; do
			curl -s "$img_url/$i" > "$HOME/.local/share/dzgui/$i"
		done
		write_desktop_file > "$freedesktop_path/dzgui.desktop"
		write_desktop_file > "$HOME/Desktop/dzgui.desktop"
		steam_path="$HOME/.local/share/Steam"
	else
		echo "# Checking for default DayZ path"
		path=$(find $HOME -path "*.local/share/Steam/steamapps/common/DayZ" | wc -c)
		if [[ ! $path -eq 0 ]]; then
			steam_path="$HOME/.local/share/Steam"
		else
			echo "# Searching for alternate DayZ path"
			path=$(find / -path "*/steamapps/common/DayZ" 2>/dev/null)
			if [[ $(echo "$path" | wc -l) -gt 1 ]]; then
				path_sel=$(echo -e "$path" | zenity --list --title="DZGUI" --text="Multiple paths found. Select correct DayZ path" --column="Paths" --width 1200 --height 800)
				clean_path=$(echo -e "$path_sel" | awk -F"/steamapps" '{print $1}')
				steam_path="$clean_path"
			elif [[ ! $(echo $path | wc -c) -eq 0 ]]; then
				clean_path=$(echo -e "$path" | awk -F"/steamapps" '{print $1}')
				steam_path="$clean_path"
			else
				steam_path=""
			fi
		fi
	fi
		echo "[DZGUI] Set Steam path to $steam_path"
}
create_config(){
	while true; do
	player_input="$(zenity --forms --add-entry="Player name (required for some servers)" --add-entry="API key" --add-entry="Server 1 (you can add more later)" --title=DZGUI --text=DZGUI --add-entry="Server 2" --add-entry="Server 3" --add-entry="Server 4" $sd_res --separator="│")"
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
	elif [[ ! $server_1 =~ ^[0-9]+$ ]]; then
		warn "Server 1: invalid server ID"
	elif [[ -n $server_2 ]] && [[ ! $server_2 =~ ^[0-9]+$ ]]; then
		warn "Server 2: invalid server ID"
	elif [[ -n $server_3 ]] && [[ ! $server_3 =~ ^[0-9]+$ ]]; then
		warn "Server 3: invalid server ID"
	elif [[ -n $server_4 ]] && [[ ! $server_3 =~ ^[0-9]+$ ]]; then
		warn "Server 4: invalid server ID"
	else
	whitelist=$(echo "$player_input" | awk -F"│" '{OFS=","}{print $3,$4,$5,$6}' | sed 's/,*$//g' | sed 's/^,*//g')
	guess_path > >(zenity --progress --auto-close --pulsate)
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
	[[ ! -d $game_dir ]] && (err "Malformed game path")
	[[ $whitelist =~ [[:space:]] ]] && (err "Separate whitelist values with commas")
}
run_depcheck() {
	if [[ -z $(depcheck) ]]; then 
		:
	else	
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
		zenity --warning $sd_res --ok-label="Exit" --text="$(varcheck)" 2>/dev/null
		printf "[DZGUI] %s\n" "$check_config_msg"
		exit
	fi
}
config(){
	if [[ ! -f $config_file ]]; then
		zenity --question --cancel-label="Exit" --text="Config file not found. Should DZGUI create one for you?" 2>/dev/null
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
	browser "$link_file" &

}
steam_deck_mods(){	
	until [[ -z $diff ]]; do
		next=$(echo -e "$diff" | head -n1)
		zenity --question --ok-label="Open" --cancel-label="Cancel" --title="DZGUI" --text="Missing mods. Click [Open] to open mod $next in Steam Workshop and subscribe to it by clicking the green Subscribe button. After the mod is downloaded, return to this menu to continue validation." 2>/dev/null
		rc=$?
		if [[ $rc -eq 0 ]]; then
			echo "[DZGUI] Opening ${workshop}$next"
			steam steam://url/CommunityFilePage/$next 2>/dev/null &
			zenity --info --title="DZGUI" --ok-label="Next" --text="Click [Next] to continue mod check." 2>/dev/null
		else
			return
		fi
		compare
	done
}
manual_mod_install(){
	l=0
	if [[ $is_steam_deck -eq 0 ]]; then
		open_mod_links
		until [[ -z $diff ]]; do
			zenity --question --title="DZGUI" --ok-label="Next" --cancel-label="Cancel" --text="Opened mod links in browser. Click [Next] when all mods have been subscribed to. This dialog may reappear if clicking [Next] too soon before mods are synchronized in the background." 2>/dev/null
			rc=$?
			if [[ $rc -eq 0 ]]; then
			compare
			open_mod_links
		else
			return
			fi
		done
	else
		steam_deck_mods
	fi
	passed_mod_check
}
encode(){
	echo "$1" | awk '{printf("%c",$1)}' | base64 | sed 's/\//_/g; s/=//g; s/+/]/g'
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
	stale_symlinks
	legacy_symlinks
	symlinks
	launch

}
connect(){
	#TODO: sanitize/validate input
	readarray -t qport_arr <<< "$qport_list"
	if [[ -z ${qport_arr[@]} ]]; then
		err "Failed to process favorite server"
		return
	fi
	ip=$(echo "$1" | awk -F"$separator" '{print $1}')
	#TODO: deprecated (for now)
	bid=$(echo "$1" | awk -F"$separator" '{print $2}')
	fetch_mods_sa "$ip"
	validate_mods
	rc=$?
	[[ $rc -eq 1 ]] && return
	compare
	if [[ -n $diff ]]; then
		manual_mod_install
	else
		passed_mod_check
	fi
}

fetch_mods_sa(){
	sa_ip=$(echo $ip | awk -F: '{print $1}')
	for i in ${qport_arr[@]}; do
		if [[ -n $(echo "$i" | awk -v ip=$ip '$0 ~ ip') ]]; then
			sa_port=$(echo $i | awk -v ip=$ip -F$separator '$0 ~ ip {print $2}')
		fi
	done
	echo "[DZGUI] Querying modlist on ${sa_ip}:${sa_port}"
	remote_mods=$(curl -Ls "https://dayzsalauncher.com/api/v1/query/$sa_ip/$sa_port" | jq -r '.result.mods[].steamWorkshopId')
	rc=$?
	if [[ $rc -eq 1 ]]; then
		err "Failed to fetch modlist"
		return
	fi
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
	readarray -t newlist <<< $(post | jq -r '.[].publishedfiledetails[] | select(.result==1) .publishedfileid')
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
		launch_options="steam -applaunch $aid -connect=$ip -nolauncher -nosplash -skipintro \"-mod=$mods\""
		print_launch_options="$(printf "[DEBUG] This is a dry run. These options would have been used to launch the game:\n\n$launch_options\n" | fold -w 60)"
		zenity --question --title="DZGUI" --ok-label="Write to file" --cancel-label="Back"\
			--text="$print_launch_options" 2>/dev/null
		if [[ $? -eq 0 ]]; then
			source_script=$(realpath "$0")
			source_dir=$(dirname "$source_script")
			echo "$launch_options" > "$source_dir"/options.log
			echo "[DZGUI] Wrote 'options.log' to $source_dir"
		fi

	else
		echo "[DZGUI] All OK. Launching DayZ"
		zenity --title="DZGUI" --info --text="Launch conditions satisfied.\nDayZ will now launch after clicking [OK]." 2>/dev/null
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
		steam steam://openurl/"$git_url" 2>/dev/null
	elif [[ $is_steam_deck -eq 0 ]]; then
		browser "$git_url" 2>/dev/null &
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
	zenity --info --title="DZGUI" --text="Removed "$server_id" from:\n${config_path}dztuirc\nIf errors occur, you can restore the file:\n${config_path}dztuirc.old" 2>/dev/null
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
			connect $sel
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
	if [[ -z $(installed_mods) || -z $(find $workshop_dir -maxdepth 2 -name "*.cpp" | grep .cpp) ]]; then
		zenity --info --text="No mods currently installed or incorrect path given" $sd_res 2>/dev/null
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
		connect "$qport_list"
		one_shot_launch=0
	else
		warn "No fav server configured"
	fi

}
set_header(){
	if [[ $1 == "delete" ]]; then
		sel=$(cat $tmp | zenity $sd_res --list $cols --title="DZGUI" --text="DZGUI $version | Mode: $mode | Branch: $branch | Fav: $fav_label" \
			--separator="$separator" --print-column=1,2 --ok-label="Delete" 2>/dev/null)
	elif [[ $1 == "populate" ]]; then
		sel=$(cat $tmp | zenity $sd_res --list $cols --title="DZGUI" --text="DZGUI $version | Mode: $mode | Branch: $branch | Fav: $fav_label" \
			--separator="$separator" --print-column=2,6 2>/dev/null)
	elif [[ $1 == "main_menu" ]]; then
		sel=$(zenity $sd_res --list --title="DZGUI" --text="${news}DZGUI $version | Mode: $mode | Branch: $branch | Fav: $fav_label" \
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
debug_menu(){
	debug_list=(
		"Toggle branch"
		"Generate debug log"
		)
	debug_sel=$(zenity --list --width=1280 --height=800 --column="Options" --title="DZGUI" --hide-header "${debug_list[@]}" 2>/dev/null)
	if [[ $debug_sel == "${debug_list[0]}" ]]; then
		enforce_dl=1
		toggle_branch &&
		check_version
	elif [[ $debug_sel == "${debug_list[1]}" ]]; then
		source_script=$(realpath "$0")
		source_dir=$(dirname "$source_script")
		generate_log > "$source_dir"
		exit
	fi
}
query_and_connect(){
	query_api
	parse_json <<< "$response"
	#TODO: create logger function
	echo "[DZGUI] Checking response time of servers"
	create_array | zenity --progress --pulsate --title="DZGUI" --auto-close 2>/dev/null
	rc=$?
	if [[ $rc -eq 1 ]]; then
		:
	else
		populate
	fi
}

main_menu(){
	print_news
	set_mode
	if [[ $debug -eq 1 ]]; then
		items+=("Debug options")
	fi
	if [[ -n $fav ]]; then
		items[3]="Change favorite server"
	fi
	while true; do
		set_header ${FUNCNAME[0]}
	rc=$?
	if [[ $rc -eq 0 ]]; then
		if [[ -z $sel ]]; then
			warn "No item was selected."
		elif [[ $sel == "${items[0]}" ]]; then
			query_and_connect
		elif [[ $sel == "${items[1]}" ]]; then
			connect_to_fav
		elif [[ $sel == "${items[2]}" ]]; then
			add_by_id
		elif [[ $sel == "${items[3]}" ]]; then
			add_by_fav
		elif [[ $sel == "${items[4]}" ]]; then
			delete=1
			query_and_connect
		elif [[ $sel == "${items[5]}" ]]; then
			list_mods | sed 's/\t/\n/g' | zenity --list --column="Mod" --column="Symlink" --title="DZGUI" $sd_res --print-column="" 2>/dev/null
		elif [[ $sel == "${items[6]}" ]]; then
			toggle_debug
			main_menu
			return
		elif [[ $sel == "${items[7]}" ]]; then
			report_bug
		elif [[ $sel == "${items[8]}" ]]; then
			help_file
		elif [[ $sel == "${items[9]}" ]]; then
			changelog | zenity --text-info $sd_res --title="DZGUI" 2>/dev/null
		elif [[ $sel == "${items[10]}" ]]; then
			debug_menu
		else
			warn "This feature is not yet implemented."
		fi
	else
		return
	fi
	done
}
parse_json(){
	list=$(jq -r '.data[] .attributes | "\(.name)\t\(.ip):\(.port)\t\(.players)/\(.maxPlayers)\t\(.details.time)\t\(.status)\t\(.id)"')
	fetch_query_ports
	#qport_list=$(echo "$response" | jq -r '.data[] .attributes | "\(.ip):\(.port)%%\(.portQuery)"')
	echo -e "$list" > $tmp
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
	list=$(cat $tmp) 
	#TODO: improve error handling for null values
	lc=1
	while read line; do
		name=$(echo "$line" | awk -F'\t' '{print $1}')
		#truncate names
		if [[ $(echo "$name" | wc -m) -gt 50 ]]; then
			name="$(echo $name | awk '{print substr($0,1,50) "..."}')"
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
			echo "$lc/$tc"
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
	write_config > $config_file
	printf "[DZGUI] Wrote new config file to %sdztuirc\n" $config_path
	zenity --info --title="DZGUI" --text="Wrote new config format to \n${config_path}dztuirc\nIf errors occur, you can restore the file:\n${config_path}dztuirc.old" 2>/dev/null

}
download_new_version(){
	source_script=$(realpath "$0")
	source_dir=$(dirname "$source_script")
	mv $source_script $source_script.old
	curl -Ls "$version_url" > $source_script
	rc=$?
	if [[ $rc -eq 0 ]]; then
		echo "[DZGUI] Wrote $upstream to $source_script"
		chmod +x $source_script
		touch ${config_path}.unmerged
		zenity --question --title="DZGUI" --text "DZGUI $upstream successfully downloaded.\nTo view the changelog, select Changelog.\nTo use the new version, select Exit and restart." --ok-label="Changelog" --cancel-label="Exit" 2>/dev/null
		code=$?
		if [[ $code -eq 0 ]]; then
			changelog | zenity --text-info $sd_res --title="DZGUI" 2>/dev/null
			exit
		elif [[ $code -eq 1 ]]; then
			exit
		fi
	else
		mv $source_script.old $source_script
		zenity --info --title="DZGUI" --text "Failed to download new version." 2>/dev/null
		return
	fi

}
check_branch(){
	if [[ $branch == "stable" ]]; then
		version_url="$stable_url"
	elif [[ $branch == "testing" ]]; then
		version_url="$testing_url"
	fi
	upstream=$(curl -Ls "$version_url" | awk -F= '/^version=/ {print $2}')
}
enforce_dl(){
		download_new_version
}
prompt_dl(){    
	zenity --question --title="DZGUI" --text "Version conflict.\n\nYour branch:\t\t$branch\nYour version\t\t$version\nUpstream version:\t\t$upstream\n\nVersion updates introduce important bug fixes and are encouraged.\n\nAttempt to download latest version?" --width=500 --ok-label="Yes" --cancel-label="No" 2>/dev/null
	rc=$?
	if [[ $rc -eq 1 ]]; then
		return
	else
		download_new_version
	fi
}
check_version(){
	if [[ ! -f $config_file ]]; then : ; else source $config_file; fi
	if [[ -z $branch ]]; then
		branch="stable"
	fi
	check_branch
	if [[ $version == $upstream ]]; then
		check_unmerged
	else
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
				zenity --info --title="DZGUI" --text="Added "$id" to:\n${config_path}dztuirc\nIf errors occur, you can restore the file:\n${config_path}dztuirc.old" 2>/dev/null
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
		items=()
		init_items
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
		items[3]="Change favorite server"
	fi
}
check_map_count(){
	count=1048576
	if [[ $(sysctl -q vm.max_map_count | awk -F"= " '{print $2}') -ne $count ]]; then 
		map_warning=$(zenity --question --title="DZGUI" --text "System map count must be $count or higher to run DayZ with Wine. Increase map count and make this change permanent? (will prompt for sudo password)" 2>/dev/null)
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
			items[3]="Change favorite server"
			return
		fi
	fi
done
}
main(){
	run_depcheck
	check_version
	check_architecture
	check_map_count
	config
	run_varcheck
	init_items
	setup
	main_menu
}

main
