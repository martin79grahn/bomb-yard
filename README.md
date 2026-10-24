# Bomb Yard för NES

En NES-version av Bomb Yard med två lägen:

- **1 spelare:** Du är Bit och ska spränga de två Kraxarna i tre levels: The Yard, Sand Pit och Frost Cave. Varje level har tre minuter på klockan.
- **2 spelare:** Två handkontroller, spelare mot spelare. Den som först vinner 3 rundor vinner matchen. Banan byts varje runda: The Yard, Sand Pit, Frost Cave och sedan runt igen. Tar tiden slut blir rundan oavgjord.

Varje bana har egen musik: djungeltrummor med bongotrummor i The Yard, orientalisk musik i Sand Pit (skalan D hijaz, med vibrato och maqsum-rytm) och lugn, atmosfärisk musik med eko och vind i Frost Cave. När det är 20 sekunder kvar går musiken upp ett halvt tonsteg och blir snabbare.

## Spela

Öppna `bomb-yard.nes` i en NES-emulator, till exempel [Mesen](https://www.mesen.ca) eller [FCEUX](https://fceux.com). På en riktig NES fungerar den med ett flashkort som klarar mapper 0 (NROM), till exempel Everdrive N8.

| Knapp | Gör |
| --- | --- |
| Styrkorset | Gå. På titelskärmen: välj 1 eller 2 spelare |
| A eller B | Lägg bomb |
| Start | Börja, pausa och fortsätt (båda spelarna kan pausa) |
| Select (på titelskärmen) | Slå på eller av debugläget, där spelare 1 går genom väggar |

Spelare 1 använder handkontroll 1 och har den vita dräkten. Spelare 2 använder handkontroll 2 och har den röda.

## Webbversionen

`web/bomb-yard.html` är originalspelet för webbläsaren, som hela spelet i en enda fil. Öppna den i en webbläsare på dator eller mobil. Den har tvåspelarläge på samma telefon med knappar för båda, en större bana på 16×16 rutor och knappar på skärmen för mobilen. Musiken är samma låtar som i NES-versionen, och i tvåspelarläget byts banan varje runda precis som på NES.

## Bygga

Du behöver [cc65](https://cc65.github.io) och Python 3.

```
CC65=/sökväg/till/cc65 ./build.sh
```

| Fil | Innehåll |
| --- | --- |
| `main.c` | Spelet, inklusive musikmotorn och låtarna för de tre banorna |
| `crt0.s` | Uppstart och NMI-rutin, som kopierar grafik till PPU:n under vblank |
| `nrom.cfg` | Minneskarta för NROM: 32 KB program och 8 KB grafik |
| `tools/make_chr.py` | Gör NES-grafik (`chr.bin`) och typsnitt (`font.h`) från PICO-8-cartens sprites |
| `tools/make_notes.py` | Gör nottabellen för musiken (`notes.h`) |
