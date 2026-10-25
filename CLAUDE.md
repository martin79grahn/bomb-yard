# Bomb Yard: notes for Claude

Martin writes in Swedish; answer in Swedish. The README is in Swedish too.

## What's here

- `main.c`, `crt0.s`, `nrom.cfg`: the NES game (cc65, mapper 0 / NROM, 32 KB PRG + 8 KB CHR). 1 player vs themed monsters over six levels (The Yard: Krax, Sand Pit: asps, Frost Cave: yetis, Lava Peak: imps, Cloud Nine: angels, Deep Sea: fish) with a boss stage after every level (an AI in player slot 1, tougher each time, drawn as the level's creature: Krax King, scorpion, mammoth, dragon, storm cloud, shark), then a seventh, final boss, the green bomber, in the Yard (`fin`, `BI`), a penetrator bomb power-up (2 per arena) whose blasts go through stone, and a remote power-up (2 per arena: bombs wait until B sets them off; lost on dying). Rounds last two minutes, and the fire left where a stone broke (`RUBBLE`) can't hurt, or 2 players (controller 2) with an options screen for the level, Krax on/off and wins needed (3, 5 or 10). Per-level music engine and songs live in `main.c`.
- `tools/creatures.py`: the themed monsters and bosses as role grids (outline, main, second, accent), drawn from shapes so one drawing serves the NES (`make_chr.py`), the Mega Drive (`md/tools/make_gfx.py`, shaded, 32×24 bosses) and the web's classic look (`tools/make_web_art.py` writes them into the page between the creatures markers; rerun it after changing a drawing). `tools/manual_icons.py` cuts them from `chr.bin` for the manual.
- `tools/make_chr.py`, `tools/make_notes.py`: generate `chr.bin`, `font.h` (from the PICO-8 cart's sprites) and `notes.h`. New font glyphs go in `FONT` and `FONT_ORDER` in `make_chr.py`.
- `bomb-yard.nes`: the built ROM, committed so it can be played straight from the repo.
- `md/`: the Mega Drive version (SGDK 2.x in Podman via `md/build.sh`). `md/src/main.c` is the NES game logic ported; `md/tools/make_gfx.py` draws all graphics into `src/gen/gfx.c`, `make_music.py` writes VGM songs (FM ch1-5 + PSG; ch6 is left for PCM) and `make_sfx.py` WAV effects, both turned into XGM2 by rescomp. `md/bomb-yard.bin` is the committed ROM. Test headless with `md/tools/retro.py` and the Genesis Plus GX libretro core (`~/emu/Genesis-Plus-GX`); `MDRam` reads variables via `out/symbol.txt`.
- `web/bomb-yard.html`: the browser game, one self-contained file. The menu offers **Classic mode** (pixel art, chiptunes matching the NES songs) and **New enhanced mode** (tilted 3D canvas renderer, themed monsters and bosses, modern WebAudio music). Both share the same game rules and code paths; `style` picks the look.

## Building and testing

- cc65 isn't installed by default: `git clone --depth 1 https://github.com/cc65/cc65 /tmp/cc65 && make -C /tmp/cc65 -j8`, then `CC65=/tmp/cc65 ./build.sh`.
- Check RAM after a build: BSS must end below `$0700` in `map.txt`.
- Test the ROM headlessly with the jsnes emulator core (bundle `src/nes.js` + `src/controller.js` from github.com/bfirsh/jsnes with bun), run frames in node, save screenshots, and record audio to check the music.
- Test the web page with Playwright/Chromium at phone (390x844, touch) and desktop sizes; no console errors.

## Published pages (Claude artifacts, update in place)

- Bomb Yard (web game): https://claude.ai/code/artifact/fc14e5ea-575c-4493-be2a-7361e9c41712 — publish `web/bomb-yard.html` to this URL.
- Bomb Yard NES (phone player): https://claude.ai/artifact/5NaWzE5d5b9eJmkY4WbMvA — `bomb-yard.nes` embedded in a jsnes page with touch controls and an optional second controller. Rebuild and republish it whenever the ROM changes.
- Bomb Yard NES Manual: https://claude.ai/code/artifact/3f78e4b3-4df7-4c07-91d9-e114d4948299 — a Design canvas (14 pages: NES 1 and 2 players, the levels, web Classic and New enhanced mode, web controls, Mega Drive, and the cartridge specs on page 12, Specs.dc.html; update its numbers when ROM or RAM use changes). Its page sources are copied to `manual/project/`; the pictures are embedded as data: URIs (`data-img` holds the picture's id, the file in `manual/images/`). Edit the copies there and publish them to the artifact (root `manual`), then commit. `manual/tools/build.py` redraws those pictures into `manual/images/<blob id>.png` from the games and renders `manual/bomb-yard-manual.pdf` (the copy on GitHub); rerun it after manual or game changes (needs cynes, Pillow, Firefox and a fresh `labels.txt` from `./build.sh`). Update it when modes or controls change.

## Working agreement

- After each change: build, test, commit to `main`, push, and republish whichever pages changed.
- Keep the README (Swedish) in step with features and controls.
