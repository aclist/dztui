#!/bin/bash

libs=(
"libgtk-3.so.0"
"libgdk-3.so.0"
"libz.so.1"
"libpangocairo-1.0.so.0"
"libpango-1.0.so.0"
"libharfbuzz.so.0"
"libatk-1.0.so.0"
"libcairo-gobject.so.2"
"libcairo.so.2"
"libgdk_pixbuf-2.0.so.0"
"libgio-2.0.so.0"
"libgobject-2.0.so.0"
"libglib-2.0.so.0"
"libm.so.6"
"libc.so.6"
"libgmodule-2.0.so.0"
"libpangoft2-1.0.so.0"
"libfontconfig.so.1"
"libfribidi.so.0"
"libepoxy.so.0"
"libXi.so.6"
"libX11.so.6"
"libatk-bridge-2.0.so.0"
"libcloudproviders.so.0"
"libtracker-sparql-3.0.so.0"
"libXfixes.so.3"
"libxkbcommon.so.0"
"libwayland-client.so.0"
"libwayland-cursor.so.0"
"libwayland-egl.so.1"
"libXext.so.6"
"libXcursor.so.1"
"libXdamage.so.1"
"libXcomposite.so.1"
"libXrandr.so.2"
"libXinerama.so.1"
"libthai.so.0"
"libfreetype.so.6"
"libgraphite2.so.3"
"libpng16.so.16"
"libXrender.so.1"
"libxcb.so.1"
"libxcb-render.so.0"
"libxcb-shm.so.0"
"libpixman-1.so.0"
"libjpeg.so.8"
"libtiff.so.5"
"libmount.so.1"
"libffi.so.8"
"libpcre.so.1"
"ld-linux-x86-64.so.2"
"libexpat.so.1"
"libdbus-1.so.3"
"libatspi.so.0"
"libstemmer.so.0"
"libicuuc.so.71"
"libicui18n.so.71"
"libsqlite3.so.0"
"libjson-glib-1.0.so.0"
"libxml2.so.2"
"libdatrie.so.1"
"libbz2.so.1.0"
"libbrotlidec.so.1"
"libXau.so.6"
"libXdmcp.so.6"
"libzstd.so.1"
"liblzma.so.5"
"libblkid.so.1"
"libpthread.so.0"
"libsystemd.so.0"
"libicudata.so.71"
"libstdc++.so.6"
"libgcc_s.so.1 "
"libbrotlicommon.so.1"
"liblz4.so.1"
"libcap.so.2"
"libgcrypt.so.20"
"libgpg-error.so.0"
)

file=libs.log

main(){
for i in "${libs[@]}"; do
	ldconfig -p | grep -qw "$i"
	code=$?
	if [[ $code -eq 1 ]]; then
	       echo "$i" >> $file
       else
	       :
	fi
done

[[ -f $file ]] && echo "generated $file" || echo "normal exit"

}

main
