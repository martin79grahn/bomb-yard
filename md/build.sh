#!/bin/sh
# Build out/rom.bin, the Mega Drive version of Bomb Yard. Needs Python 3 with Pillow and
# Podman (or Docker) for the SGDK container. EXTRA_FLAGS goes to the compiler, for example
# EXTRA_FLAGS="-DTEST_CLEAR" (run "./build.sh clean" first).
set -e
cd "$(dirname "$0")"
ENGINE=${ENGINE:-podman}
python3 tools/make_gfx.py src/gen
python3 tools/make_music.py res/music
python3 tools/make_sfx.py res/sfx
if [ "$ENGINE" = podman ]; then USERNS="--userns=keep-id:uid=100,gid=101"; else USERNS="-u $(id -u):$(id -g)"; fi
$ENGINE run --rm $USERNS -e EXTRA_FLAGS -v "$PWD":/src:Z ghcr.io/stephane-d/sgdk:latest "$@"
ls -l out/rom.bin
