#!/bin/sh
# Fetch only the SKY130 device models this project uses (about 30 MB),
# pinned to one commit so results can be repeated.
set -e
REPO=https://github.com/google/skywater-pdk-libs-sky130_fd_pr
REV=f62031a1be9aefe902d6d54cddd6f59b57627436
DEST="$(dirname "$0")/../pdk/fd_pr"
if [ -d "$DEST/.git" ]; then echo "pdk already present"; exit 0; fi
mkdir -p "$DEST"
git clone --filter=blob:none --no-checkout "$REPO" "$DEST"
cd "$DEST"
git sparse-checkout init --cone
git sparse-checkout set models/parameters cells/nfet_01v8 cells/pfet_01v8_hvt
git checkout "$REV"
