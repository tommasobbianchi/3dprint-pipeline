# SKILL: image-to-3d — Analisi Immagini e Specifiche Strutturate per CadQuery

## Identità
Analizzatore visuale specializzato in reverse-engineering da immagini a specifiche 3D strutturate.
Riceve un'immagine (sketch, foto, disegno tecnico, screenshot CAD), la analizza, e produce
un output strutturato che alimenta la skill spatial-reasoning per la modellazione CadQuery.

---

## 1. Classificazione Input

Prima di analizzare l'immagine, classifica il tipo di input. La classificazione determina
il protocollo di analisi, il livello di confidenza e le domande da porre all'utente.

### 1.1 Tipi di Input

| Tipo | Caratteristiche | Confidenza dimensionale | Azione richiesta |
|---|---|---|---|
| **A. Sketch a mano** | Tratti imprecisi, proporzioni approssimative, possibili annotazioni | BASSA — chiedi dimensioni | Estrai forme e topologia, chiedi TUTTE le quote |
| **B. Foto oggetto** | Prospettiva, distorsione, possibili riferimenti dimensionali | MEDIA — stima da riferimenti | Identifica riferimenti noti, stima rapporti dimensionali |
| **C. Disegno tecnico** | Viste ortogonali, quote, tolleranze, sezioni | ALTA — leggi direttamente | Estrai quote, sezioni, viste; verifica coerenza tra viste |
| **D. Screenshot CAD** | Modello 3D renderizzato, possibili quote overlay | ALTA — leggi se presenti | Identifica features, estrai quote se visibili |
| **E. Immagine prodotto** | Foto catalogo/ecommerce, sfondo pulito, angoli noti | MEDIA — stima da categoria | Identifica categoria prodotto, stima da standard |

### 1.2 Albero Decisionale Classificazione

```
IMMAGINE RICEVUTA
│
├─ Ha quote/misure numeriche scritte?
│   ├─ Viste ortogonali (fronte, lato, pianta)? → TIPO C: Disegno tecnico
│   └─ Singola vista con annotazioni? → TIPO D: Screenshot CAD (o TIPO A se sketch)
│
├─ Tratti a mano/disegnati?
│   └─ → TIPO A: Sketch a mano
│
├─ Foto reale (texture, ombre, sfondo)?
│   ├─ Sfondo bianco/catalogo? → TIPO E: Immagine prodotto
│   └─ Sfondo reale/ambiente? → TIPO B: Foto oggetto
│
└─ Rendering 3D / wireframe?
    └─ → TIPO D: Screenshot CAD
```

---

## 2. Protocollo di Analisi

### 2.1 Prompt di Analisi Strutturato

Per ogni immagine, esegui questa analisi in sequenza:

```
ANALISI IMMAGINE
================

TIPO INPUT: [A/B/C/D/E] — [nome tipo]
CONFIDENZA DIMENSIONALE: [BASSA/MEDIA/ALTA]

STEP 1 — IDENTIFICAZIONE FORME PRIMITIVE
  Forme rilevate:
    1. [nome] — [primitiva: box/cilindro/tubo/lastra/cono/sfera/profilo L/profilo U/...]
       Posizione: [dove nel pezzo — base, top, lato, centro]
       Dimensioni stimate: [L x W x H mm] (confidenza: [alta/media/bassa])
    2. [...]

STEP 2 — OPERAZIONI RILEVATE
  Operazioni booleane e features:
    1. [tipo: foro/tasca/slot/raccordo/smusso/nervatura/boss/snap-fit/...]
       Posizione: [su quale forma, dove]
       Dimensioni stimate: [Ø, profondità, raggio, ...]
    2. [...]

STEP 3 — SIMMETRIE E PATTERN
  Simmetrie:
    □ Simmetria assiale (rivoluzione): [sì/no] — asse: [X/Y/Z]
    □ Simmetria speculare: [sì/no] — piano: [XY/XZ/YZ]
    □ Pattern circolare: [sì/no] — N elementi, raggio
    □ Pattern lineare: [sì/no] — N elementi, passo

STEP 4 — RAPPORTI DIMENSIONALI
  Se le dimensioni assolute non sono note:
    - Rapporto L:W:H ≈ [a : b : c]
    - Dimensione di riferimento: [elemento noto] = [valore] mm
    - Scala derivata: 1 unità immagine ≈ [X] mm

STEP 5 — FEATURES FUNZIONALI
  Scopo probabile: [cosa fa il pezzo — supporto, contenitore, adattatore, ...]
  Interfacce esterne:
    1. [dove si collega] — [tipo: vite, snap, incastro, appoggio]
    2. [...]
  Vincoli funzionali:
    - [es. deve resistere a carico, deve essere impermeabile, deve condurre calore, ...]
```

### 2.2 Domande Obbligatorie per Tipo

#### Tipo A — Sketch a mano

Chiedi SEMPRE:
1. Dimensioni complessive (L x W x H)
2. Spessore pareti (se contenitore o guscio)
3. Diametro fori e tipo (passante/cieco, filettato/liscio)
4. Materiale e uso previsto
5. Tolleranze critiche (accoppiamenti)

#### Tipo B — Foto oggetto

Chiedi SE MANCANO riferimenti:
1. C'e un oggetto noto nell'immagine per scala? (moneta, USB, dito, ...)
2. Dimensione di almeno un elemento noto
3. Materiale del pezzo originale
4. Funzione e accoppiamenti

#### Tipo C — Disegno tecnico

Chiedi SOLO SE ambiguo:
1. Scala del disegno (se non indicata)
2. Tolleranze generali (se non a norma)
3. Materiale (se non indicato nel cartiglio)

#### Tipo D — Screenshot CAD

Chiedi SOLO SE mancanti:
1. Quote non visibili nello screenshot
2. Features nascoste (fori ciechi, cavita interne)

#### Tipo E — Immagine prodotto

Chiedi SE non determinabile:
1. Categoria precisa del prodotto
2. Dimensione di un elemento noto
3. Funzione e contesto d'uso

---

## 3. Tabella Riferimenti Dimensionali

### 3.1 Oggetti Comuni per Scala

| Riferimento | Dimensione | Uso |
|---|---|---|
| Moneta 1 cent EUR | Ø 16.25 mm | Piccoli oggetti |
| Moneta 10 cent EUR | Ø 19.75 mm | Piccoli oggetti |
| Moneta 50 cent EUR | Ø 24.25 mm | Oggetti medi |
| Moneta 1 EUR | Ø 23.25 mm | Oggetti medi |
| Moneta 2 EUR | Ø 25.75 mm | Oggetti medi |
| Carta di credito | 85.6 x 53.98 mm | Oggetti piatti |
| Foglio A4 | 210 x 297 mm | Oggetti grandi |
| Penna Bic standard | Ø 7 mm, L 150 mm | Scala lineare |
| Dito indice adulto | ~18 mm larghezza, ~75 mm lunghezza | Stima rapida |
| Dito mignolo adulto | ~14 mm larghezza | Dettagli piccoli |
| Palmo mano adulto | ~85 mm larghezza | Oggetti medi |

### 3.2 Connettori Standard

| Connettore | Dimensioni apertura | Note |
|---|---|---|
| USB-A | 12.0 x 4.5 mm | Connettore rettangolare classico |
| USB-C | 8.34 x 2.56 mm | Ovale, simmetrico |
| USB-B | 12.0 x 10.9 mm | Quasi quadrato, rastremato |
| USB Micro-B | 6.85 x 1.80 mm | Trapezoidale sottile |
| USB Mini-B | 6.8 x 3.0 mm | Trapezoidale |
| HDMI standard | 14.0 x 4.55 mm | Trapezoidale |
| HDMI mini | 10.42 x 2.42 mm | Trapezoidale piccolo |
| HDMI micro | 6.4 x 2.8 mm | Simile a micro-USB |
| Ethernet RJ45 | 11.68 x 13.54 mm | Quadrato con clip |
| Jack audio 3.5mm | Ø 3.5 mm | Foro tondo |
| Barrel jack 5.5/2.1 | Ø 5.5 mm esterno | Alimentazione DC |
| SD card | 24.0 x 32.0 x 2.1 mm | Slot con guida |
| MicroSD | 11.0 x 15.0 x 1.0 mm | Slot piccolo |

### 3.3 Schede Elettroniche

| Scheda | Dimensioni PCB | Fori montaggio | Note |
|---|---|---|---|
| Arduino Uno R3 | 68.6 x 53.4 mm | 4x Ø3.2, posizioni non regolari | USB-B + barrel jack |
| Arduino Nano | 18.0 x 45.0 mm | 2x Ø1.6 (o nessuno) | Mini-USB o USB-C |
| Arduino Mega 2560 | 101.6 x 53.3 mm | 4x Ø3.2 | USB-B + barrel jack |
| Raspberry Pi 4B | 85.0 x 56.0 mm | 4x M2.5, 58x49mm pattern | 2x USB-A + 2x micro-HDMI + USB-C |
| Raspberry Pi Zero 2W | 65.0 x 30.0 mm | 4x Ø2.75 | Mini-HDMI + micro-USB |
| Raspberry Pi Pico | 21.0 x 51.0 mm | 4x Ø2.1, 11.4x47mm pattern | Micro-USB o USB-C |
| ESP32 DevKit V1 | 51.0 x 28.0 mm | nessuno (breadboard pin) | Micro-USB, antenne ai lati |
| ESP32-S3 DevKit | 69.0 x 26.0 mm | nessuno | USB-C |
| ESP8266 NodeMCU | 49.0 x 26.0 mm | nessuno (breadboard pin) | Micro-USB |
| STM32 Blue Pill | 53.0 x 23.0 mm | nessuno (breadboard pin) | Micro-USB |

### 3.4 Viteria Standard

| Elemento | Dimensione | Uso nella stima |
|---|---|---|
| Vite M2 testa cilindrica | Ø testa 3.8 mm | Elettronica piccola |
| Vite M2.5 testa cilindrica | Ø testa 4.5 mm | RPi, elettronica |
| Vite M3 testa cilindrica | Ø testa 5.5 mm | Uso generico |
| Vite M3 testa svasata | Ø testa 6.0 mm | Superfici piatte |
| Vite M4 testa cilindrica | Ø testa 7.0 mm | Strutturale |
| Vite M5 testa cilindrica | Ø testa 8.5 mm | Strutturale pesante |
| Dado M3 | 5.5 mm chiave, 2.4 mm alto | Estremamente comune |
| Dado M4 | 7.0 mm chiave, 3.2 mm alto | Strutturale |
| Dado M5 | 8.0 mm chiave, 4.0 mm alto | Strutturale pesante |
| Rondella M3 | Ø est 7.0, Ø int 3.2, sp 0.5 mm | Distribuzione carico |
| Rondella M4 | Ø est 9.0, Ø int 4.3, sp 0.8 mm | Distribuzione carico |
| Inserto caldo M3 | Ø 4.0-4.2 mm sede | Filettatura in plastica |
| Inserto caldo M4 | Ø 5.6-6.0 mm sede | Filettatura in plastica |

### 3.5 Profili e Tubi Standard

| Elemento | Dimensioni | Note |
|---|---|---|
| Tubo tondo 15mm | Ø est 15, sp 1.0 mm | Aste piccole |
| Tubo tondo 20mm | Ø est 20, sp 1.5 mm | Tende, strutture leggere |
| Tubo tondo 25mm | Ø est 25, sp 1.5 mm | Appendiabiti |
| Tubo tondo 32mm | Ø est 32, sp 2.0 mm | Idraulica, strutture |
| Profilo alluminio 2020 | 20 x 20 mm | Slot 6mm, V-slot o T-slot |
| Profilo alluminio 3030 | 30 x 30 mm | Slot 8mm |
| Profilo alluminio 4040 | 40 x 40 mm | Slot 8mm, strutture pesanti |
| Barra tonda 8mm | Ø 8 mm | Guide lineari, perni |
| Barra tonda 10mm | Ø 10 mm | Guide, alberi |

---

## 4. Output Strutturato

L'output dell'analisi immagine alimenta direttamente la Fase 1 (Decomposizione Funzionale)
della skill spatial-reasoning. Formato:

```
IMAGE-TO-3D OUTPUT
==================

TIPO INPUT: [A/B/C/D/E] — [nome tipo]
CONFIDENZA: [BASSA/MEDIA/ALTA]
RIFERIMENTO SCALA: [oggetto usato] = [dimensione] mm

OBIETTIVO: [funzione del pezzo — cosa fa, dove si monta, perche serve]

VINCOLI:
  Materiale suggerito: [PLA/PETG/ABS/ASA/PC/TPU] — [motivazione]
  Temperatura servizio: [°C]
  Carichi: [tipo e direzione]
  Accoppiamenti: [elenco interfacce]
  Dimensioni massime: [vincolo stampante o spazio]

COMPONENTI:
  1. [nome] — [primitiva CadQuery: box/cylinder/polyline+extrude/revolve/loft]
     Dimensioni: [L x W x H mm] (confidenza: [alta/media/bassa])
     Funzione: [perche esiste]
     CadQuery: [hint operazione — es. "cq.Workplane('XY').box(40, 30, 5)"]
  2. [...]

FEATURES:
  1. [tipo: hole/pocket/slot/fillet/chamfer/shell/boss/rib/snap_clip]
     Su: [componente N]
     Dimensioni: [Ø, profondita, raggio, ...]
     CadQuery: [hint — es. ".faces('>Z').workplane().hole(3.4)"]
  2. [...]

SIMMETRIE SFRUTTABILI:
  - [tipo simmetria] → [operazione CadQuery: .mirror() / .polarArray() / .rarray()]

OPERAZIONI BOOLEANE:
  Ordine suggerito:
    1. [componente base]
    2. + [addizione]: [componente N]
    3. - [sottrazione]: [feature N]
    4. fillet/chamfer: [dove, raggio] — PRIMA delle boolean se broad selector

ORIENTAMENTO STAMPA SUGGERITO:
  Piano XY: [quale faccia sul piatto]
  Motivazione: [perche]
  Supporti: [si/no — dove se si]

DOMANDE PER L'UTENTE (se confidenza < ALTA):
  1. [domanda specifica con opzioni se possibile]
  2. [...]
```

### 4.1 Mapping Forme Visive → Primitive CadQuery

| Forma vista nell'immagine | Primitiva CadQuery | Note |
|---|---|---|
| Rettangolo / blocco | `cq.Workplane("XY").box(w, d, h)` | Forma piu comune |
| Cilindro / tubo | `cq.Workplane("XY").cylinder(h, r)` | Se cavo: `.circle(r_ext).circle(r_int).extrude(h)` |
| Sfera | `cq.Workplane("XY").sphere(r)` | Rara in FDM |
| Profilo a L / T / U | `cq.Workplane("XZ").polyline(pts).close().extrude(d)` | Sketch 2D + estrusione |
| Pezzo assial-simmetrico | `cq.Workplane("XZ").polyline(pts).close().revolve()` | Boccole, adattatori, pomelli |
| Transizione tra sezioni | `loft()` tra sketch su workplane diversi | Transizioni di forma |
| Guscio / contenitore | `.box().shell(-wall)` o `box.cut(cavity)` | Shell piu pulito se uniforme |
| Forma organica curva | NON gestibile — segnala come limitazione | Suggerisci sculpting |

### 4.2 Mapping Features Visive → Operazioni CadQuery

| Feature vista | Operazione CadQuery | Note |
|---|---|---|
| Foro passante tondo | `.faces(sel).workplane().hole(d)` | Seleziona faccia corretta |
| Foro cieco | `.faces(sel).workplane().circle(r).cutBlind(-depth)` | Profondita negativa |
| Foro oblungo / slot | `.faces(sel).workplane().slot2D(length, d).cutBlind(-depth)` | O polyline+cutBlind |
| Tasca rettangolare | `.faces(sel).workplane().rect(w, l).cutBlind(-depth)` | Tasca quadrata |
| Raccordo (raggio costante) | `.edges(sel).fillet(r)` | ATTENZIONE: prima delle boolean! |
| Smusso | `.edges(sel).chamfer(c)` | Su spigoli di ingresso/assemblaggio |
| Nervatura / rib | `.union(rib_body)` con polyline triangolare | Rinforzo strutturale |
| Boss cilindrico | `.union(cylinder)` | Per viti, standoff |
| Clip snap-fit | Cantilever con lip — sketch + extrude + cut | Vedi template snap_fit |
| Pattern di fori | `.pushPoints(pts).hole(d)` | O `.rarray()` / `.polarArray()` |
| Grigliatura / ventilazione | Pattern di tagli rettangolari | `.pushPoints().rect().cutThruAll()` |
| Testo in rilievo/inciso | `.text("...", fontsize, depth)` | Rilievo meglio di incisione in FDM |

---

## 5. Vantaggi CadQuery per Reverse Engineering

### 5.1 Mapping Diretto Immagine → CadQuery

| Se nell'immagine vedi... | In CadQuery usa... | Perche meglio di OpenSCAD |
|---|---|---|
| Raccordi/arrotondamenti | `.fillet(r)` nativo | OpenSCAD richiede `minkowski()` lento o geometria esplicita |
| Transizione tra diametri | `.loft()` tra sezioni | OpenSCAD: `hull()` solo convesso, nessun vero loft |
| Profilo che segue un percorso | `.sweep(path)` | Non esiste in OpenSCAD |
| Parti multiple assemblate | `cq.Assembly()` | OpenSCAD: nessun assembly nativo |
| Guscio con spessore uniforme | `.shell(-wall)` | OpenSCAD: `offset()` 2D o differenza manuale |
| Selezione feature su facce | `.faces(">Z").workplane()` | OpenSCAD: calcolo manuale coordinate |
| Fori su facce inclinate | `.faces(sel).workplane().hole(d)` | OpenSCAD: `rotate()` + `translate()` manuale |
| Foratura su pattern irregolare | `.pushPoints(pts).hole(d)` | OpenSCAD: loop con translate individuali |

### 5.2 Strategia per Tipo di Pezzo

| Tipo di pezzo | Strategia CadQuery | Approccio |
|---|---|---|
| **Box / enclosure** | `box` + `shell` + features | Modella esterno, svuota, aggiungi dettagli |
| **Staffa / bracket** | `polyline` + `extrude` + fori | Profilo 2D a L/T/U, estrudi, fora |
| **Adattatore cilindrico** | `revolve` di profilo sezione | Un unico profilo 2D ruotato = pezzo intero |
| **Coperchio / piastra** | `box` sottile + features | Base piatta, aggiungi lip, fori, testo |
| **Supporto / mount** | `box` + `cut` + nervature | Forma base, ritaglia dove serve, rinforza |
| **Connettore / giunto** | `cylinder` + boolean | Cilindri concentrici con tagli |
| **Clip / snap-fit** | `box` + cantilever sketch | Corpo base + linguetta flessibile |
| **Ingranaggio / gear** | NON CadQuery puro | Suggerisci libreria `cq_gears` o import STEP |

---

## 6. Procedura Stima Dimensionale da Foto

### 6.1 Con Riferimento Noto

```
PROCEDURA STIMA CON RIFERIMENTO:

1. IDENTIFICA riferimento nell'immagine
   - Oggetto noto: [nome] = [dimensione reale] mm
   - Misura in pixel nell'immagine: [N] px

2. CALCOLA scala
   - Scala = dimensione_reale / pixel_riferimento
   - Es: moneta 1 EUR (23.25mm) = 150px → scala = 0.155 mm/px

3. MISURA target in pixel
   - [dimensione 1] = [N] px → [N * scala] mm
   - [dimensione 2] = [N] px → [N * scala] mm
   - [...]

4. CORREGGI per prospettiva
   - Se oggetto e riferimento sullo stesso piano: nessuna correzione
   - Se piani diversi: SEGNALA incertezza, aggiungi ±15%
   - Se angolo di vista obliquo: SEGNALA, dimensioni perpendiculari all'asse ottico piu affidabili

5. ARROTONDA a valori sensati
   - Dimensioni < 10mm: arrotonda a 0.5mm
   - Dimensioni 10-50mm: arrotonda a 1mm
   - Dimensioni > 50mm: arrotonda a 5mm
   - Se vicino a valore standard (Ø20, Ø25, Ø32, ...): usa valore standard

CONFIDENZA RISULTANTE:
  - Riferimento stesso piano, buona illuminazione: ±5%
  - Riferimento piano diverso: ±15%
  - Nessun riferimento (stima da categoria): ±30%
```

### 6.2 Senza Riferimento — Stima da Categoria

| Categoria oggetto | Range dimensionale tipico | Base di stima |
|---|---|---|
| Clip / fermaglio | 15-40 mm | Dimensione dito |
| Supporto smartphone | 60-100 mm larghezza | Larghezza telefono ~75mm |
| Enclosure elettronica | 30-120 mm | Dimensione PCB (vedi 3.3) |
| Staffa / bracket | 30-80 mm | Fori montaggio visibili |
| Adattatore tubo | 15-50 mm Ø | Diametro tubo standard |
| Pomello / maniglia | 20-50 mm | Dimensione mano |
| Vaso / contenitore | 50-150 mm | Proporzione con mano/tavolo |
| Modello architettonico | 100-300 mm | Scala 1:100 o 1:200 |

---

## 7. Limitazioni e Fallback

### 7.1 Casi NON Gestibili

| Caso | Problema | Suggerimento |
|---|---|---|
| Forme organiche (scultura, anatomia) | CadQuery e BREP parametrico, non mesh sculpting | Usa Blender/ZBrush → export STL, importa come mesh |
| Superfici NURBS complesse (carrozzeria auto) | Troppo complesse per modellazione procedurale | Usa Fusion360/Onshape per modellazione diretta |
| Immagine troppo sfocata/buia | Non si distinguono forme e dimensioni | Chiedi foto migliore o sketch quotato |
| Troppo poco dettaglio | Impossibile determinare features interne | Chiedi foto aggiuntive (altri angoli, sezione) |
| Pezzo con filettature visibili | CadQuery non ha thread nativi | Usa inserto caldo (foro Ø4.0 per M3) o libreria `cq_bolts` |
| Pezzo con texture/pattern decorativi | Impossibile da riprodurre in BREP | Semplifica: liscia la superficie, ignora texture |
| Pezzo molto grande (>300mm) | Fuori volume stampa tipico | Suggerisci suddivisione in parti con giunzioni |

### 7.2 Quando Chiedere Aiuto all'Utente

```
CHIEDI SEMPRE SE:
  - Confidenza dimensionale < MEDIA e nessun riferimento nell'immagine
  - Pezzo ha features interne non visibili (cavita, canali, sottosquadri)
  - Immagine ambigua (potrebbe essere 2+ interpretazioni geometriche)
  - Funzione del pezzo non chiara (influenza materiale e tolleranze)
  - Accoppiamenti critici (press-fit, snap-fit) senza quote

NON PROCEDERE MAI senza conferma su:
  - Dimensioni assolute (almeno una quota nota)
  - Materiale (influenza spessori minimi e raccordi)
  - Funzione (influenza carichi e tolleranze)
```

### 7.3 Richiesta Foto Aggiuntive

Se una singola immagine non basta, chiedi specificamente:

```
RICHIESTA FOTO AGGIUNTIVE:

Per completare il modello 3D ho bisogno di:

□ Foto frontale (se manca vista principale)
□ Foto laterale (per profondita/spessori)
□ Foto dall'alto (per forma in pianta)
□ Foto dal basso (per features nascoste — fori, cavita)
□ Foto dettaglio di: [feature specifica]
□ Foto con riferimento dimensionale (moneta, righello, USB)
□ Sketch quotato (anche a mano) con le dimensioni critiche
```

---

## 8. Esempio Completo — Foto Staffa con Moneta

### Input
Foto di una staffa metallica a L con fori, accanto a una moneta da 1 EUR.

### Analisi

```
ANALISI IMMAGINE
================

TIPO INPUT: B — Foto oggetto
CONFIDENZA DIMENSIONALE: MEDIA (moneta 1 EUR come riferimento)

STEP 1 — IDENTIFICAZIONE FORME PRIMITIVE
  Forme rilevate:
    1. Piastra verticale — box — posizione: braccio sinistro
       Dimensioni stimate: 45 x 25 x 3 mm (confidenza: media)
    2. Piastra orizzontale — box — posizione: braccio destro/basso
       Dimensioni stimate: 35 x 25 x 3 mm (confidenza: media)
    3. Nervatura triangolare — profilo triangolare — angolo interno
       Dimensioni stimate: base 15mm, altezza 15mm, spessore 3mm (confidenza: bassa)

STEP 2 — OPERAZIONI RILEVATE
  1. Foro passante tondo — su piastra verticale, centro
     Dimensioni stimate: Ø 4-5mm (probabilmente M4)
  2. Foro passante tondo — su piastra verticale, centro basso
     Dimensioni stimate: Ø 4-5mm (probabilmente M4)
  3. Foro passante oblungo — su piastra orizzontale
     Dimensioni stimate: 5 x 8mm (slot per regolazione)
  4. Raccordo — angolo esterno L
     Raggio stimato: ~2mm

STEP 3 — SIMMETRIE E PATTERN
  □ Simmetria assiale: no
  □ Simmetria speculare: si — piano YZ (la L e simmetrica in profondita)
  □ Pattern circolare: no
  □ Pattern lineare: no (fori non equidistanti)

STEP 4 — RAPPORTI DIMENSIONALI
  Riferimento: moneta 1 EUR = 23.25mm = 142px nell'immagine
  Scala: 0.164 mm/px
  Braccio verticale: 275px → 45.1mm → arrotondato 45mm
  Braccio orizzontale: 213px → 34.9mm → arrotondato 35mm
  Profondita: 153px → 25.1mm → arrotondato 25mm

STEP 5 — FEATURES FUNZIONALI
  Scopo: staffa di fissaggio a muro/superficie per supporto
  Interfacce: viti M4 su entrambi i bracci
  Vincoli: deve reggere carico verticale (peso oggetto supportato)
```

### Output Strutturato

```
IMAGE-TO-3D OUTPUT
==================

TIPO INPUT: B — Foto oggetto
CONFIDENZA: MEDIA
RIFERIMENTO SCALA: moneta 1 EUR (Ø 23.25mm)

OBIETTIVO: Staffa a L per fissaggio a muro, due fori verticali + slot orizzontale

VINCOLI:
  Materiale suggerito: PETG — carico strutturale, buona resistenza
  Temperatura servizio: ambiente
  Carichi: compressione su braccio orizzontale, taglio su viti
  Accoppiamenti: viti M4 passanti
  Dimensioni massime: ~45 x 35 x 25 mm

COMPONENTI:
  1. Profilo L — polyline 2D nel piano XZ + extrude in Y
     Dimensioni: 35(X) x 25(Y) x 45(Z) mm, spessore 3mm
     Funzione: corpo strutturale
     CadQuery: cq.Workplane("XZ").polyline(pts).close().extrude(25)
  2. Nervatura — triangolo nel piano XZ + extrude
     Dimensioni: base 15 x altezza 15 x spessore 3mm
     Funzione: rinforzo angolo
     CadQuery: cq.Workplane("XZ").polyline(tri_pts).close().extrude(3)

FEATURES:
  1. hole — Ø 4.5mm (M4 clearance) — su braccio verticale, 2 posizioni
     CadQuery: .faces("<X").workplane().pushPoints(pts).hole(4.5)
  2. slot — 5 x 8mm — su braccio orizzontale
     CadQuery: .faces("<Z").workplane().slot2D(8, 5).cutThruAll()
  3. fillet — r=2mm — spigoli verticali esterni
     CadQuery: .edges("|Z").fillet(2) — PRIMA della union con nervatura

SIMMETRIE SFRUTTABILI:
  - Simmetria speculare YZ → modella meta + .mirror("YZ") (se appropriato)

OPERAZIONI BOOLEANE:
  1. Base: profilo L (extrude)
  2. fillet r=2mm su edge angolo interno (NearestToPointSelector)
  3. + union: nervatura
  4. - cut: fori M4 su braccio verticale
  5. - cut: slot su braccio orizzontale

ORIENTAMENTO STAMPA SUGGERITO:
  Piano XY: braccio orizzontale sul piatto (base della L)
  Motivazione: massima adesione, nervatura a 45° accettabile
  Supporti: no (nervatura esattamente 45°)

DOMANDE PER L'UTENTE:
  1. Spessore staffa — stimo 3mm, corretto? (o misura diversa?)
  2. Fori sul braccio verticale — M4 (Ø4.5mm)? O taglia diversa?
  3. Lo slot e per regolazione posizione? Confermi dimensioni ~5x8mm?
  4. Materiale: PETG va bene o preferisci altro?
```

---

## 9. Checklist Pre-Output

Prima di consegnare l'output strutturato alla skill spatial-reasoning:

- [ ] Tipo input classificato correttamente
- [ ] Tutte le forme primitive identificate con dimensioni
- [ ] Tutte le features (fori, tasche, raccordi) elencate
- [ ] Simmetrie identificate e sfruttabili
- [ ] Almeno un riferimento dimensionale usato (o dimensioni chieste all'utente)
- [ ] Operazioni booleane ordinate correttamente (fillet PRIMA di boolean)
- [ ] Orientamento stampa suggerito con motivazione
- [ ] Materiale suggerito con motivazione
- [ ] Domande per l'utente formulate (se confidenza < ALTA)
- [ ] Nessuna forma organica/NURBS tentata (segnalata come limitazione)
- [ ] Output nel formato strutturato della sezione 4
