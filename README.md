# Bomb Yard för NES

En NES-version av Bomb Yard med två lägen:

- **1 spelare:** du är Bit och ska spränga de två Kraxarna i tre levels, The Yard, Sand Pit och Frost Cave. Varje level har en minut på klockan.
- **2 spelare:** spräng varandra på en slumpad bana. Spelare 2 (röd) använder handkontroll 2. Tar tiden slut blir rundan oavgjord. Innan matchen väljer du på en inställningsskärm:
  - **Level:** The Yard, Sand Pit eller Frost Cave.
  - **Monsters:** på eller av. När de är på går två Kraxar runt på banan, och den som nuddar en är ute.
  - **Wins:** hur många vunna rundor som krävs för att vinna matchen, 3, 5 eller 10.

Överst på skärmen står `B` för antal bomber, `F` för sprängräckvidd och `S` för hur många skor (fart) du har plockat. I 2-spelarläget står också vunna rundor av hur många som krävs, till exempel `P1 2/5`.

## Spela

Öppna `bomb-yard.nes` i en NES-emulator, till exempel [Mesen](https://www.mesen.ca) eller [FCEUX](https://fceux.com). På en riktig NES fungerar den med ett flashkort som klarar mapper 0 (NROM), till exempel Everdrive N8.

| Knapp | Gör |
| --- | --- |
| Styrkorset | Gå |
| A eller B | Lägg bomb |
| Upp/ner (på titelskärmen) | Välj 1 eller 2 spelare |
| Upp/ner, vänster/höger (inställningar) | Välj rad och ändra värde. B går tillbaka |
| Start | Börja, pausa och fortsätt |
| Select (på titelskärmen) | Slå på eller av debugläget, där du går genom väggar (bara 1 spelare) |

## Webbversionen

`web/bomb-yard.html` är originalspelet för webbläsaren, som hela spelet i en enda fil. Öppna den i en webbläsare på dator eller mobil. Den har några saker som NES-versionen saknar: en större bana på 16×16 rutor, tvåspelarläge på samma telefon och knappar på skärmen för mobilen.

## Bygga

Du behöver [cc65](https://cc65.github.io) och Python 3.

```
CC65=/sökväg/till/cc65 ./build.sh
```

| Fil | Innehåll |
| --- | --- |
| `main.c` | Spelet |
| `crt0.s` | Uppstart och NMI-rutin, som kopierar grafik till PPU:n under vblank |
| `nrom.cfg` | Minneskarta för NROM: 32 KB program och 8 KB grafik |
| `tools/make_chr.py` | Gör NES-grafik (`chr.bin`) och typsnitt (`font.h`) från PICO-8-cartens sprites |
| `tools/make_notes.py` | Gör nottabellen för musiken (`notes.h`) |
