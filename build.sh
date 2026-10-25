#!/bin/sh
# Build bomb-yard.nes. Needs cc65 (https://cc65.github.io); set CC65 to its folder if it isn't on PATH.
set -e
cd "$(dirname "$0")"
B=${CC65:-/tmp/cc65}
python3 tools/make_chr.py chr.bin
python3 tools/make_notes.py
$B/bin/cc65 -t nes -Oirs -g --add-source main.c -o main.s
$B/bin/ca65 -t nes -g main.s -o main.o
$B/bin/ca65 -t nes -I $B/asminc crt0.s -o crt0.o
$B/bin/ld65 -C nrom.cfg -o bomb-yard.nes crt0.o main.o $B/lib/nes.lib -m map.txt -Ln labels.txt   # labels.txt: RAM addresses for the test and manual tools
ls -l bomb-yard.nes
