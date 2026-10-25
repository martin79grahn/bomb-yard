# Bomb Yard för NES

En NES-version av Bomb Yard med två lägen:

- **1 spelare:** du är Bit och ska spränga de två monstren i sex levels: The Yard, Sand Pit, Frost Cave, Lava Peak, Cloud Nine och Deep Sea. Varje level har sina egna monster som passar temat: Kraxar (svarta fåglar) i The Yard, kobror (`ASP`) i Sand Pit, små yetis i Frost Cave, eldsdjävlar (`IMP`) på Lava Peak, änglar på Cloud Nine och orange clownfiskar i Deep Sea. Varje level har två minuter på klockan. Innan spelet väljer du hur många liv du har, 3, 5 eller 10, och vilken figur du vill spela som: Bit (vit), Ruby (röd), Sky (blå) eller Nova (gul). Varje gång du dör förlorar du ett liv och försöker banan igen, och när liven är slut är det game over.

  Efter varje level kommer en **bossbana** på samma bana som du just klarat, med en boss som hör till temat: Krax-kungen med krona i The Yard, en jätteskorpion i Sand Pit, en ullig mammut i Frost Cave, en drake på Lava Peak, ett argt åskmoln med blixtar på Cloud Nine och en haj i Deep Sea. Efter hajen kommer den sjunde och sista bossen, **den gröna bombaren**, som du möter hemma i The Yard igen. Varje boss är svårare än den förra: den första tål 3 träffar, lägger 2 bomber åt gången med sprängräckvidd 5, och den sista, den gröna bombaren, tål 8 träffar och lägger 4 bomber med räckvidd 8 och är snabbast och tänker kortast mellan bomberna. Halvvägs blir bossen arg: rödare, snabbare och med en bomb till. När den gröna bombaren är besegrad har du vunnit. Den blinkar en stund efter varje träff och kan inte skadas då. Att nudda bossen är ofarligt, det är bomberna du ska akta dig för. Bossen skadas inte av sina egna bomber, bara av dina.
- **Boss rush:** bara de sju bossarna, en efter en, utan monsterbanorna. Du väljer liv, antal power-ups och figur som i 1-spelarläget, och dina power-ups följer med från boss till boss. Klarar du alla sju har du vunnit. På webben är det knappen **Boss rush** i menyn.
- **Debugläge:** du går genom väggar och kan inte dö, varken av eld, monster eller när tiden tar slut (klockan stannar på noll).
- **2 spelare:** spräng varandra på en slumpad bana. Spelare 2 (röd) använder handkontroll 2. Tar tiden slut blir rundan oavgjord. Innan matchen väljer du på en inställningsskärm:
  - **Level:** The Yard, Sand Pit, Frost Cave, Lava Peak, Cloud Nine eller Deep Sea.
  - **Monsters:** på eller av. När de är på går två av banans monster runt, och den som nuddar ett är ute.
  - **Wins:** hur många vunna rundor som krävs för att vinna matchen, 3, 5 eller 10.
  - **P1 och P2:** vilken figur varje spelare har, Bit, Ruby, Sky eller Nova. Två spelare kan inte välja samma.

Under stenarna på varje bana göms bomb-power-ups, eld-power-ups och skor, och i 1-spelarläget också 1 hjärta som ger ett extra liv. Hur många av varje sort (1–7, normalt 5) väljer du på raden ITEMS på inställningsskärmen, och i webbversionen med knappen Power-ups. Hjärtat är alltid ett och går inte att ändra. Det finns ingen övre gräns för hur många bomber eller hur lång eld du kan samla på dig, men skorna slutar ge fart efter 4.

Varje bana gömmer också 2 **penetratorbomber** (en bomb med en pil genom). Med en penetrator spränger dina bomber rakt igenom stenblocken, så att alla block inom räckvidden går sönder på en gång i stället för bara det första. Den gäller för alla dina bomber tills du dör, då förlorar du den. Den följer med till nästa bana om du klarar banan.

Varje bana gömmer också 2 **remotes** (en bomb med antenn som sänder radiovågor). Med en remote smäller dina bomber inte av sig själva. De ligger kvar tills du trycker på den andra knappen, och då smäller alla dina remotebomber på en gång. På NES lägger du bomber med A och spränger dem med B, och på Mega Drive lägger du med A eller C och spränger med B. Remotebomberna har en antenn med en lampa och ett band runt magen, så att de syns från vanliga bomber. Andra explosioner sätter fortfarande igång dem. Remoten försvinner när du dör, precis som penetratorn, och de bomber du redan lagt börjar då ticka som vanliga bomber. Den följer med till nästa bana om du klarar banan.

Explosionerna slocknar efter ungefär en halv sekund. När ett stenblock sprängs brinner det en kort stund där blocket stod och stoppar andra explosioner, men den elden är ofarlig, så du dör inte om du går in i rutan direkt.

Överst på skärmen står `B` för antal bomber (`P` när du har penetratorn), `F` för sprängräckvidd och `S` för hur många skor (fart) du har plockat, och ett `R` när du har remoten. I 1-spelarläget står också hur många liv du har kvar och på bossbanan hur många träffar bossen tål (`BOSS 3`), och i 2-spelarläget vunna rundor av hur många som krävs, till exempel `P1 2/5`.

Varje bana har egen musik: djungeltrummor med bongotrummor i The Yard, orientalisk musik i Sand Pit (skalan D hijaz, med vibrato och maqsum-rytm) lugn, atmosfärisk musik med eko och vind i Frost Cave, en långsam, dyster och lite läskig klagosång i frygisk skala med mullrande bas och hjärtslag på Lava Peak, en psalm som spelas som en kyrkorgel på Cloud Nine, och i Deep Sea svepande arpeggion som vågor med eko, havsbrus och bubblor som stiger. Lava Peak har svart och glödande röd sten, Cloud Nine himmelsblå moln och gyllene block, och Deep Sea mörkt turkos havsbotten med korallrosa block. När det är 20 sekunder kvar går musiken upp ett halvt tonsteg och blir snabbare, och en klocka börjar ticka.

## Spela

Öppna `bomb-yard.nes` i en NES-emulator, till exempel [Mesen](https://www.mesen.ca) eller [FCEUX](https://fceux.com). På en riktig NES fungerar den med ett flashkort som klarar mapper 0 (NROM), till exempel Everdrive N8.

| Knapp | Gör |
| --- | --- |
| Styrkorset | Gå. På titelskärmen: välj 1 eller 2 spelare |
| A eller B | Lägg bomb. Med remote: A lägger bomb och B spränger dina bomber |
| Upp/ner, vänster/höger (inställningar) | Välj rad och ändra värde. B går tillbaka |
| Start | Börja, pausa och fortsätt (båda spelarna kan pausa) |
| Upp/ner (på titelskärmen) | Välj 1 PLAYER, 2 PLAYERS eller BOSS RUSH |
| Select (på titelskärmen) | Slå på eller av debugläget, där du går genom väggar och inte kan dö (bara 1 spelare) |

Spelare 1 använder handkontroll 1 och har den vita dräkten. Spelare 2 använder handkontroll 2 och har den röda.

Styrningen hjälper dig in i gångarna, både på NES och i webben. Trycker du en riktning en liten stund innan du når en korsning, svänger figuren dit när den kommer fram. Trycker du lite för sent, upp till fem pixlar efter korsningen, dras figuren tillbaka och svänger ändå. Motsatt riktning vänder direkt, mitt i ett steg.

Explosionerna ritas som sammanhängande strålar som bara är rundade i ändarna.

## Webbversionen

`web/bomb-yard.html` är originalspelet för webbläsaren, som hela spelet i en enda fil. Öppna den i en webbläsare på dator eller mobil. Den har tvåspelarläge på samma telefon med knappar för båda, en större bana på 16×16 rutor och knappar på skärmen för mobilen. Musiken är samma låtar som i NES-versionen.

På tangentbordet lägger du bomber med Mellanslag eller X och spränger remotebomber med Z eller C. I tvåspelarläget har spelare 1 Mellanslag för bomb och E för remote, och spelare 2 Enter för bomb och höger Shift för remote. På mobilen finns en mindre knapp, **BOOM**, bredvid **BOMB**. Den lyser grönt när du har en remote och spränger då dina remotebomber, och annars lägger den en bomb precis som BOMB-knappen.

Knapparna **P1** och **P2** i menyn väljer figur: Bit, Ruby, Sky eller Nova. Valet sparas till nästa gång.

### Classic mode och New enhanced mode

I webbversionens meny väljer du utseende innan du startar. Valet sparas till nästa gång.

- **Classic mode:** originalet med PICO-8-cartens pixelgrafik och chiptune-musiken.
- **New enhanced mode:** samma regler i ny grafik, sedd snett ovanifrån med lite isometrisk vinkel. Blocken är tredimensionella, och det finns skuggor, glödande eld, partiklar och skakande skärm vid explosioner. Varje bana har eget tema: grönska i The Yard, sandsten i Sand Pit is och snö i Frost Cave, svart lavasten med glödande sprickor och uppstigande gnistor på Lava Peak, och moln, gyllene block och glittrande ljus på Cloud Nine, och havsbotten med koraller, snäckklädda stenar och bubblor som stiger i Deep Sea. Bossarna är samma som i Classic mode, ritade i ny stil.
  - **Luta banan:** dra med fingret (eller musen på dator) på spelplanen för att ändra vinkeln. Upp och ner gör att du ser banan brantare uppifrån eller mer från sidan, vänster och höger ändrar snedheten. Dubbeltryck eller dubbelklicka för att återställa. Vinkeln sparas till nästa gång, och knapparna på mobilen fungerar som vanligt medan du drar.
  - **Monster efter tema:** The Yard har en Krax som hoppar omkring och en skalbagge, Sand Pit en kobra och en skarabé, Frost Cave två yetis och ett isbloss, Lava Peak två eldsdjävlar och en magmaklump, Cloud Nine två änglar och ett irrbloss med vingar och gloria, och Deep Sea tre clownfiskar. Kraxar, yetis, klumpar och fiskar vandrar runt, kobror och skalbaggar rusar mot dig när de ser dig längs en gång, och eldsdjävlar, änglar och irrbloss flyger efter dig.
  - **Ny musik:** modern instrumental musik med syntetiserade trummor, bas, synthmattor och eko. Tropical house i The Yard, ökeninspirerad deep house med darbuka och oud-liknande melodi i Sand Pit, lugn ambient synthwave med klockarpeggio i Frost Cave, en mörk och dyster klagosång med klämtande klocka, hjärtslag och mullrande ljud på Lava Peak, kyrkorgel med kör som sjunger melodin på Cloud Nine, och i Deep Sea flytande klockarpeggion, vågor som sköljer in och ut och bubblande ljud.

## Manual

Hela spelmanualen finns som PDF i [`manual/bomb-yard-manual.pdf`](manual/bomb-yard-manual.pdf), 13 sidor. Den beskriver alla lägen: NES-versionen för 1 och 2 spelare, banorna med sina monster och bossar, webbversionens Classic mode och New enhanced mode med kontroller för tangentbord och mobil, och Mega Drive-versionen. Den finns också som en sida i Claude (Bomb Yard NES Manual).

Sidornas källfiler ligger i `manual/project/` och bilderna i `manual/images/`. `manual/tools/build.py` ritar om alla bilder från spelen (sprites ur `chr.bin`, skärmbilder från NES-ROM:en i emulatorn cynes och från webbversionen i Firefox) och bygger PDF:en. Bygg NES-ROM:en först, eftersom verktyget läser RAM-adresserna ur `labels.txt`.

## Bygga

Du behöver [cc65](https://cc65.github.io) och Python 3.

```
CC65=/sökväg/till/cc65 ./build.sh
```

| Fil | Innehåll |
| --- | --- |
| `main.c` | Spelet, inklusive musikmotorn och låtarna för de sex banorna |
| `crt0.s` | Uppstart och NMI-rutin, som kopierar grafik till PPU:n under vblank |
| `nrom.cfg` | Minneskarta för NROM: 32 KB program och 8 KB grafik |
| `tools/make_chr.py` | Gör NES-grafik (`chr.bin`) och typsnitt (`font.h`) från PICO-8-cartens sprites |
| `tools/make_notes.py` | Gör nottabellen för musiken (`notes.h`) |

## Mega Drive-versionen

I mappen `md/` finns en Mega Drive-version med samma regler som NES-versionen men ny grafik, FM-musik och samplade ljudeffekter. ROM-filen är `md/bomb-yard.bin`. Se `md/README.md`.
