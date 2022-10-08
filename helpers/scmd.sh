#!/bin/bash

conf=$HOME/.config/dztui/dztuirc
source $conf
[[ -z $staging_dir ]] && staging_dir="/tmp"
aid=221100
steamcmd_user=steam
workshop_dir="$steam_path/steamapps/workshop/content/$aid"

log(){
	printf "$(tput setaf 3)[INFO]$(tput sgr0) %s\n" "$1"
}
pass(){
	printf "$(tput setaf 2)[PASS]$(tput sgr0) %s\n" "$1"
}
fail(){
	printf "$(tput setaf 1)[FAIL]$(tput sgr0) %s\n" "$1"
}
steamcmd_modlist(){
	printf "force_install_dir %s\n" "$staging_dir"
	printf "login %s\n" "$steam_username"
	for i in "${ids[@]}"; do
	printf "workshop_download_item %s %s validate\n" $aid $i
	done
	printf "quit"
}
move_files(){
	printf "\n"
	log "Moving mods from $staging_dir to $workshop_dir"
	if [[ $staging_dir == "/tmp" ]]; then
		sudo chown -R $USER:$gid "$staging_dir"/steamapps
	fi
	cp -R "$staging_dir"/steamapps/workshop/content/$aid/* "$workshop_dir"
	if [[ $dist == "steamos" ]]; then
		rm -rf "$staging_dir"/steamapps
	else
		sudo rm -rf "$staging_dir"/steamapps
	fi
}
#tutorial(){
#cat <<- HERE
#
#INSTRUCTIONS
#
#Keep this window adjacent to your terminal as a guide.
#
#1. In the steamcmd prompt, enter "login [id] [pass] [2FA]" (if applicable) 
#and type Enter. E.g., if the user is Billy, pass is Banana, and 2FA token is 777:
#
#login Billy Banana 777 [Enter]
#
#2. Then enter: runscript /tmp/mods.txt and type Enter
#
#3. The auto-mod process will begin to headlessly download the mods.
#
#Valve uses a long-lived token to cache credentials, 
#so you may be able to simply type [id] and "quit"
#on subsequent invocations, but it expires after some time.
#HERE
#}
#ctdw(){
#	for((i=3;i>0;i--)); do
#		printf  "[INFO] Downloading mods in %i\r" "$i"
#		sleep 1s
#	done
#}
test_dir(){
	if [[ $dist == "steamos" ]]; then
	       staging_dir="$HOME/.local/share/dzgui/mods"
	       mkdir -p $staging_dir
	       return 0
	fi
	sudo -u steam test -w "$staging_dir"
	rc=$?
	if [[ $rc -eq 1 ]]; then
		fail "User '$steamcmd_user' does not have write access to $staging_dir. Reverting to /tmp"
		staging_dir="/tmp"
		return 0
	fi
}
auto_mod_download(){
	while true; do
	read -p 'Enter Steam login name: ' steam_username
	[[ -z $steam_username ]] && { fail "Username can't be empty"; continue; }
	[[ -n $steam_username ]] && break
	done
	if [[ -d "$staging_dir/steamapps" ]]; then
		log "Sanitizing $staging_dir"
		if [[ $staging_dir == "/tmp" ]]; then
			sudo chown -R $USER:$gid "$staging_dir"/steamapps
		fi
		if [[ $dist == "steamos" ]]; then
			rm -rf "$staging_dir"/steamapps
		else
			sudo rm -rf "$staging_dir"/steamapps
		fi
	fi
		tput civis
		[[ ${#ids[@]} -gt 1 ]] && s=s
		tput cnorm
		test_dir
		log "Staging dir is $staging_dir"
		steamcmd_modlist > "/tmp/mods.txt"
		log "Preparing to download ${#ids[@]} mod$s. This may take some time. Abort with Ctrl+c."
		if [[ $dist == "steamos" ]]; then
			$steamcmd_path +runscript /tmp/mods.txt
		else
			sudo -iu $steamcmd_user bash -c "$steamcmd_path +runscript /tmp/mods.txt"
		fi
		rc=$?
		rm "/tmp/mods.txt"
		if [[ $rc -eq 0 ]]; then
			move_files
		else
			return 1
		fi
}
find_steam_cmd(){
	for i in  "/home/steam" "/usr/bin" "/usr/local/bin" "/usr/games"; do
		if [[ -f "$i/steamcmd" ]]; then
			steamcmd_path="$i/steamcmd"
			pass "Found steamcmd: $steamcmd_path"
			return 0
		fi
	done
	fail "Failed to find steamcmd"
	return 1
}
create_user(){
	log "Creating steamcmd user"
	sudo useradd -m steam
	rc=$?
	if [[ $rc -eq 0 ]]; then
		log "Set a password for the headless steamcmd user"
		sudo passwd steam
	else
		return 1
	fi
}
check_user(){
	id $steamcmd_user &>/dev/null
	rc=$?
	if [[ $rc -eq 1 ]]; then
		fail "steamcmd user missing"
		create_user
		rc=$?
		[[ $rc -eq 1 ]] && return 1
	else
		pass "Found user: $steamcmd_user"
	fi
	while true; do
		local stat=$(sudo passwd $steamcmd_user --status | awk '{print $2}')
		if
			[[ $stat == "L" ]] || [[ $stat == "NP" ]]; then
			fail "steamcmd user has a locked or empty password"
			sudo passwd $steamcmd_user
		else
			return 0
		fi
	done
}
generic_install(){
	fail "Unrecognized distro: $dist."
	log "Please report this upstream for whitelisting and attach your SCMD.log"
	log "Location: $HOME/.local/share/dzgui/helpers/SCMD.log"
	return 1
}
fedora_install(){
	#TODO
	:
}
#ubuntu related
#    dep: debconf
#        Debian configuration management system 
#
#    dep: debconf (>= 0.5)
#        Debian configuration management system 
#    or debconf-2.0
#        virtual package provided by cdebconf, cdebconf-udeb, debconf 
#
#    dep: libc6 (>= 2.12)
#        GNU C Library: Shared libraries
#        also a virtual package provided by libc6-udeb 
#
#    dep: libstdc++6
#        GNU Standard C++ Library v3 
#
#    sug: steam
#        Valve's Steam digital software delivery system 
#
deb_install(){
	check_user
	rc=$?
	[[ $rc -eq 1 ]] && return 1
	find_steam_cmd
	rc=$?
	if [[ $rc -eq 1 ]]; then
	log "Installing distribution steamcmd packages"
		sudo add-apt-repository -y multiverse
		sudo apt install -y software-properties-common
		sudo dpkg --add-architecture i386
		sudo apt update
		sudo apt install -y steamcmd
		find_steam_cmd
	fi
	dpkg -s lib32gcc-s1 1>/dev/null
	rc=$?
	if [[ $rc -eq 1 ]]; then
		fail "Missing deps: lib32-gcc-libs"
		sudo apt install -y lib32gcc-s1
	else
		pass "Found deps: lib32-gcc-libs"
	fi

}
deck_install(){
	pacman -Qi lib32-gcc-libs 2>/dev/null 1>&2
	rc=$?
	[[ ! $rc -eq 0 ]] && return 1
	if [[ ! -f $HOME/.local/share/dzgui/helpers/steamcmd ]]; then
		local tarball="steamcmd_linux.tar.gz"
		mkdir -p $HOME/.local/share/dzgui/helpers/steamcmd
		curl -Ls "https://steamcdn-a.akamaihd.net/client/installer/$tarball" > $HOME/.local/share/dzgui/helpers/steamcmd/$tarball
		$(cd $HOME/.local/share/dzgui/helpers/steamcmd; tar xvf $tarball)
	fi
	steamcmd_path="$HOME/.local/share/dzgui/helpers/steamcmd/steamcmd.sh"
}
arch_install(){
	check_user
	rc=$?
	[[ $rc -eq 1 ]] && return 1
	find_steam_cmd
	rc=$?
	if [[ $rc -eq 1 ]]; then
		log "Checking prerequisites"
		for i in makepkg git; do
			if [[ ! $(command -v $i) ]]; then
				fail "Missing package: $i"
				info "Script will fetch build tools now. Partial upgrades on Arch Linux are discouraged, so triggering a full update.\n
				Type any key to proceed."
				read -n1 key
				case $key in
					*) sudo pacman -Syu base-devel git lib32-gcc-libs --noconfirm
				esac
				break
			else
				pass "Found deps: $i"
			fi
		done
		log "Installing steamcmd from distribution"
		[[ -d /tmp/steamcmd ]] && rm -rf /tmp/steamcmd
		git clone https://aur.archlinux.org/steamcmd.git /tmp/steamcmd
		cd /tmp/steamcmd && makepkg -si --noconfirm && cd $OLDPWD
		#TODO: check symlink
		log "Symlinking steamcmd"
		sudo ln -s /usr/bin/steamcmd /home/steam/steamcmd
		rm -rf /tmp/steamcmd
		find_steam_cmd
	fi
	sudo pacman -Qi lib32-gcc-libs 2>/dev/null 1>&2
	rc=$?
	if [[ $rc -eq 1 ]]; then
		fail "Missing deps: lib32-gcc-libs"
		info "Script will fetch build tools now. Partial upgrades on Arch Linux are discouraged, so triggering a full update.\n
		Type any key to proceed."
		read -n1 key
		case $key in
			*) sudo pacman -Syu lib32-gcc-libs --noconfirm
		esac
	else
		pass "Found deps: lib32-gcc-libs"
	fi
}
check_dist(){
		os=/etc/os-release
		dist=$(awk -F= '/^ID=/ {print $2}' $os)
		pass "Found OS: $dist"
		case $dist in
			ubuntu|linuxmint|pop|debian) deb_install ;;
			arch|antergos|manjaro) arch_install ;;
			steamos) deck_install ;;
			fedora) generic_install ;;
			*) generic_install ;;
		esac
}
return_to_dzg(){
	if [[ $ret -eq 1 ]]; then
		fail "Errors occurred. Type any key to return to DZGUI and kick off manual install."
		read -n1 key
		case $key in
			*) exit 1 ;;
		esac
	else
		$(cd $HOME/.local/share/dzgui/helpers; zenity --text-info --html --width=390 --height=452 --filename="d.html" 2>/dev/null)
		return 0
	fi
}
cleanup(){
	tput cnorm
	exit
}
abort(){
	tput cnorm
	printf "\n"
	log "Keyboard interrupt"
	exit
}
check_disks(){
	disksize=$(df $staging_dir --output=avail | tail -n1)
	disk_bytewise=$((disksize * 1024))
	hr=$(echo $(numfmt --to=iec --format "%.2f" $totalmodsize $disk_bytewise) | sed 's/ /\//')
	[[ ${#ids[@]} -gt 1 ]] && s=s
	if [[ $disk_bytewise -lt $totalmodsize ]]; then
		fail "Required/actual: $hr. Installation will quit after /tmp reaches capacity."
	else
		pass "Required/actual: $hr"
	fi
}
[[ -f $PWD/SCMD.log ]] && rm SCMD.log
if [[ -z $1 ]] || [[ -z $2 ]]; then
	fail "Missing mod arguments"
	ret=1
	return_to_dzg
fi
totalmodsize="$1"
shift
for i in $@; do
	ids+=("$i")
done
main(){
	echo ""
	echo "────────DZGUI automod helper────────"
	log "Preparing environment"
	check_disks
	check_dist
	if [[ $? -eq 1 ]]; then
		ret=1
		return_to_dzg
	else
		pass "All OK. Starting mod auto install process"
		auto_mod_download
		rc=$?
		[[ $rc -eq 1 ]] && ret=1
		return_to_dzg
	fi
}
trap cleanup EXIT
trap abort SIGINT
main | tee -a SCMD.log
