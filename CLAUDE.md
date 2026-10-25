# Bomb Yard: notes for Claude

Martin writes in Swedish; answer in Swedish. The README is in Swedish too.

## What's here

- `main.c`, `crt0.s`, `nrom.cfg`: the NES game (cc65, mapper 0 / NROM, 32 KB PRG + 8 KB CHR). 1 player vs Krax monsters over five levels (The Yard, Sand Pit, Frost Cave, Lava Peak, Cloud Nine) with a boss stage (an AI bomber in player slot 1) between levels 1 and 2, or 2 players (controller 2) with an options screen for the level, Krax on/off and wins needed (3, 5 or 10). Per-level music engine and songs live in `main.c`.
- `tools/make_chr.py`, `tools/make_notes.py`: generate `chr.bin`, `font.h` (from the PICO-8 cart's sprites) and `notes.h`. New font glyphs go in `FONT` and `FONT_ORDER` in `make_chr.py`.
- `bomb-yard.nes`: the built ROM, committed so it can be played straight from the repo.
- `md/`: the Mega Drive version (SGDK 2.x in Podman via `md/build.sh`). `md/src/main.c` is the NES game logic ported; `md/tools/make_gfx.py` draws all graphics into `src/gen/gfx.c`, `make_music.py` writes VGM songs (FM ch1-5 + PSG; ch6 is left for PCM) and `make_sfx.py` WAV effects, both turned into XGM2 by rescomp. `md/bomb-yard.bin` is the committed ROM. Test headless with `md/tools/retro.py` and the Genesis Plus GX libretro core (`~/emu/Genesis-Plus-GX`); `MDRam` reads variables via `out/symbol.txt`.
- `web/bomb-yard.html`: the browser game, one self-contained file. The menu offers **Classic mode** (pixel art, chiptunes matching the NES songs) and **New enhanced mode** (tilted 3D canvas renderer, slime/beetle/wisp monsters, modern WebAudio music). Both share the same game rules and code paths; `style` picks the look.

## Building and testing

- cc65 isn't installed by default: `git clone --depth 1 https://github.com/cc65/cc65 /tmp/cc65 && make -C /tmp/cc65 -j8`, then `CC65=/tmp/cc65 ./build.sh`.
- Check RAM after a build: BSS must end below `$0700` in `map.txt`.
- Test the ROM headlessly with the jsnes emulator core (bundle `src/nes.js` + `src/controller.js` from github.com/bfirsh/jsnes with bun), run frames in node, save screenshots, and record audio to check the music.
- Test the web page with Playwright/Chromium at phone (390x844, touch) and desktop sizes; no console errors.

## Published pages (Claude artifacts, update in place)

- Bomb Yard (web game): https://claude.ai/code/artifact/fc14e5ea-575c-4493-be2a-7361e9c41712 — publish `web/bomb-yard.html` to this URL.
- Bomb Yard NES (phone player): https://claude.ai/artifact/5NaWzE5d5b9eJmkY4WbMvA — `bomb-yard.nes` embedded in a jsnes page with touch controls and an optional second controller. Rebuild and republish it whenever the ROM changes.
- Bomb Yard NES Manual: https://claude.ai/code/artifact/3f78e4b3-4df7-4c07-91d9-e114d4948299 — a Design canvas (13 pages: NES 1 and 2 players, Mega Drive, web Classic and New enhanced mode, web controls). Its page sources are copied to `manual/project/`; images are `/_blob/` uploads that live only in the artifact. Edit the copies there and publish them to the artifact (root `manual`), then commit. Update it when modes or controls change.

## Working agreement

- After each change: build, test, commit to `main`, push, and republish whichever pages changed.
- Keep the README (Swedish) in step with features and controls.
