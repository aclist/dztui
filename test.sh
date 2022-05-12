#!/bin/bash

yad_path="/lib/yad"
yad=$(echo "$(dirname -- ${BASH_SOURCE[0]})${yad_path}")
${yad} --button="Ok":0 --text="\nTesting yad" --text-align=center --center --on-top --width=300
