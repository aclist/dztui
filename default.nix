{ pkgs, lib, stdenv, fetchFromGitHub, makeWrapper }:
stdenv.mkDerivation rec {
  pname = "dzgui";
  version = "0.1";

  src = ./.;

  nativeBuildInputs = [ makeWrapper ];

  runtimeDeps = with pkgs; [
    curl
    jq
    python3
    wmctrl
    xdotool
    gnome.zenity

    ## Here we don't declare steam as a dependency because
    ## we could either use the native or flatpack version
    ## and also so this does not become a non-free package
    # steam
  ];

  patchPhase = ''
    sed -i \
      -e 's|/usr/bin/zenity|${pkgs.gnome.zenity}/bin/zenity|' \
      -e 's|2>/dev/null||' \
      dzgui.sh
  '';

  installPhase = ''
    install -Dm777 -T dzgui.sh $out/bin/.dzgui-unwrapped_
    makeWrapper $out/bin/.dzgui-unwrapped_ $out/bin/dzgui \
      --prefix PATH ':' ${lib.makeBinPath runtimeDeps}
  '';

  meta = with lib; {
    homepage = "https://github.com/pronovic/banner";
    description = "DayZ TUI/GUI server browser";
    license = licenses.gpl3;

    longDescription = ''
      DZGUI allows you to connect to both official and modded/community DayZ
      servers on Linux and provides a graphical interface for doing so.
    '';

    platforms = platforms.all;
  };
}
