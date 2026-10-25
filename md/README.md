# Bomb Yard för Mega Drive

En Mega Drive-version av NES-spelet, med samma regler men ny grafik, ny musik och nya ljudeffekter. ROM-filen är `bomb-yard.bin` och går att köra i en Mega Drive-emulator, till exempel ares eller Genesis Plus GX.

## Spelet

Allt från NES-versionen finns med:

- **1 spelare:** fem banor (The Yard, Sand Pit, Frost Cave, Lava Peak och Cloud Nine) med två Kraxar på varje, och en bossbana mellan bana 1 och bana 2. Du väljer 3, 5 eller 10 liv innan spelet, och vilken figur du spelar som: Bit, Ruby, Sky eller Nova, med var sina färger. Bossen kan lägga 2 bomber åt gången med sprängräckvidd 5 och tål 3 träffar. Efter 2 träffar blir den röd och snabbare och kan lägga 3 bomber. Den skadas inte av sina egna bomber, bara av dina.
- **2 spelare:** välj bana, om Kraxar ska vara med och hur många vunna rundor som krävs (3, 5 eller 10) och vilken figur var och en har. Två spelare kan inte välja samma. Spelare 2 använder handkontroll 2.
- Under stenarna på varje bana göms bomb-power-ups, eld-power-ups, skor och, med 1 spelare, 1 hjärta som ger ett extra liv. Raden ITEMS på inställningsskärmen väljer hur många av varje sort (1–7, normalt 5); hjärtat är alltid ett. Bomber och eld har ingen övre gräns.
- Styrhjälpen från NES-versionen: ett tryck strax före en korsning sparas, ett tryck upp till 5 pixlar för sent svänger ändå, och motsatt riktning vänder direkt.
- Tre minuter per bana. De sista 20 sekunderna går musiken fortare och en klocka tickar.

## Knappar

| Knapp | Gör |
| --- | --- |
| Styrkorset | Gå. I menyerna: välj |
| A, B eller C | Lägg bomb |
| Start | Börja, pausa och fortsätt |
| B (i inställningarna) | Tillbaka |
| C (på titelskärmen) | Debugläge, där du går genom väggar (1 spelare) |

## Grafik och ljud

- Grafiken ritas av `tools/make_gfx.py` pixel för pixel, med ljus från övre vänstra hörnet och mörk kontur. Gubbarna har visir och ögon, bossen har horn och Kraxarna är små svarta fåglar med orange näbb. Blocken kastar skugga på golvet, eldstrålarna flimrar och tunnas ut innan de slocknar, och bomberna blinkar rött strax innan de smäller. Varje bana har egna färger, och bossbanan är mörklila.
- Musiken skrivs av `tools/make_music.py` som VGM-filer för FM-synten: NES-melodierna arrangerade med bas, ackordarpeggio, eko i stereo och trummor, plus ny musik för titelskärmen och bossen, en dyster klagosång med körröster, klämtande klocka och hjärtslag för Lava Peak, en psalm med FM-orgel och kör för Cloud Nine, och korta jinglar när du klarar en bana, vinner eller får game over.
- Ljudeffekterna syntetiseras av `tools/make_sfx.py` och spelas som samplingar: explosion, bomb, power-up, hjärta, död, bossträff, klocktick och menyljud.

Manualen har två sidor om Mega Drive-versionen (sida 10 och 11). De skrivs av `tools/manual_pages.py`, som ritar bilderna med spelets egen grafikkod.

## Bygga

Du behöver Python 3 med Pillow och Podman (eller Docker). SGDK körs i en container.

```sh
./build.sh
```

ROM-filen hamnar i `out/rom.bin`. Testbygget `EXTRA_FLAGS="-DTEST_CLEAR" ./build.sh` (kör `./build.sh clean` först) klarar varje bana med Kraxar efter två sekunder, så att du snabbt kommer till bossen.
