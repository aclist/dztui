#!/usr/bin/env bash

echo "$PWD"
url="https://github.com/ofek/pyapp/releases/latest/download/source.tar.gz"
output="${PWD}/pyapp-source.tar.gz"
curl "$url" -Lo "$output"
tar -xzf "$output"
mv ${PWD}/pyapp-v* ${PWD}/pyapp-latest
rm "$output"
