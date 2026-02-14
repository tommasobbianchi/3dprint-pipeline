# 🎯 Esempi di Prompt — Difficoltà Crescente

> Ogni esempio illustra skill diverse della pipeline.
> Usa: `cd ~/projects/3dprint-pipeline && claude`
> Poi: `Leggi skills/3d-print-orchestrator/SKILL.md` prima del prompt.

---

## ⬜ LIVELLO 1 — Primitive Parametriche (solo codegen + validate)

### 1.1 — Cubo forato
```
Crea un cubo 30×30×30mm con un foro passante Ø10mm centrato sulla faccia top.
Materiale PLA. Fillet r=2mm su tutti gli spigoli verticali.
```
**Testa:** fillet nativi, foro passante, export STEP+STL

---

### 1.2 — Rondella / distanziale
```
/box 0
Crea un distanziale cilindrico: diametro esterno 12mm, foro interno Ø5.2mm (passaggio vite M5),
altezza 8mm. Smusso 0.5mm su entrambi i bordi superiore e inferiore.
```
**Testa:** cilindro cavo, chamfer, dimensioni precise per vite

---

### 1.3 — Targhetta nome
```
Crea una targhetta rettangolare 60×20×3mm con gli angoli arrotondati r=3mm.
Aggiungi il testo "TOMMY" in rilievo alto 1mm sulla faccia superiore.
Font semplice, centrato.
```
**Testa:** testo 3D (CadQuery supporta text via Workplane.text()), fillet 2D

---

## 🟨 LIVELLO 2 — Parti Funzionali Semplici (codegen + validate + materials)

### 2.1 — Supporto da parete per tubo
```
Supporto da parete per tubo Ø25mm (tipo tubo idraulico).
Fissaggio al muro con 2 viti M4 (fori a distanza 50mm verticale).
Il tubo deve incastrarsi con un'apertura laterale (clip aperta a C, non cerchio chiuso).
Materiale PETG. Spessore parete 2.5mm.
```
**Testa:** profilo a C (arco non chiuso), fori montaggio, vincoli PETG

---

### 2.2 — Fermaporta a cuneo
```
Fermaporta a cuneo:
- Lunghezza 100mm, larghezza 40mm
- Altezza da 2mm (punta) a 25mm (base)
- Zigrinatura antiscivolo sulla faccia inferiore (griglia di piccoli rilievi 1×1mm, passo 3mm)
- Foro per cordino Ø5mm nella parte alta
Materiale TPU 95A.
```
**Testa:** loft (cuneo rastremato), pattern ripetuto, materiale flessibile

---

### 2.3 — Scatola parametrica con coperchio
```
/box 80x60x40 PETG

Aggiungi:
- Coperchio con incastro maschio/femmina (lip 1.5mm)
- 4 fori per viti M3 autofilettanti agli angoli
- Slot per etichetta 40×15mm incassato 0.5mm sul fronte
- Piedini cilindrici h=2mm Ø8mm sotto i 4 angoli
```
**Testa:** assembly 2 parti (body+lid), lip di incastro con tolleranza, features multiple

---

## 🟧 LIVELLO 3 — Enclosure e Parti Meccaniche (tutte le skill tranne image)

### 3.1 — Enclosure ESP32-CAM con slot SD e foro obiettivo
```
Enclosure per ESP32-CAM:
- PCB: 40.5 × 27 × 4.5mm (senza camera)
- Modulo camera sporgente: 8×8×5mm centrato su un lato corto
- Foro obiettivo Ø8mm allineato alla camera
- Slot Micro-SD accessibile lateralmente
- Slot per connettore FTDI (6 pin, passo 2.54mm) sul lato opposto alla camera
- Snap-fit per chiusura
- Foro per vite M2 di montaggio sul retro
- Materiale: PLA nero

Orientamento stampa: base dell'enclosure sul build plate, no supporti necessari.
```
**Testa:** dimensioni precise, snap-fit, foro circolare per ottica, slot laterali

---

### 3.2 — Staffa a L rinforzata con nervature
```
Staffa a L per montaggio a parete di un profilo in alluminio 20×20mm:
- Braccio orizzontale: 60×40mm con 2 fori Ø5.5mm (passaggio M5) a distanza 30mm
- Braccio verticale: 60×40mm con 2 fori Ø5.5mm simmetrici
- Spessore: 4mm
- 3 nervature triangolari di rinforzo nell'angolo interno (h=15mm, spessore 2mm)
- Fillet r=3mm nell'angolo interno della L
- Fillet r=1mm su tutti gli spigoli esterni
- Materiale: PETG-CF

Deve reggere un carico di ~2kg. Orientamento stampa: braccio verticale sul build plate.
```
**Testa:** nervature (rib), fillet multipli, considerazioni strutturali, materiale composito

---

### 3.3 — Adattatore tubo con loft
```
Adattatore riduttore per tubo aspirapolvere:
- Ingresso: Ø35mm esterno, spessore parete 2mm
- Uscita: Ø25mm esterno, spessore parete 2mm
- Lunghezza transizione: 45mm (loft graduale, no spigoli)
- Lip di 5mm dritto su entrambe le estremità (per innesto nel tubo)
- Fillet r=0.5mm sui bordi delle labbra
- Tolleranza: slip-fit (gioco 0.3mm sul diametro rispetto ai tubi)
- Materiale: PETG

Questo pezzo è IMPOSSIBILE da fare bene in OpenSCAD — il loft è nativo in CadQuery.
```
**Testa:** loft tra 2 cerchi di diametro diverso — feature chiave di CadQuery

---

## 🟥 LIVELLO 4 — Assembly Multi-Parte e Design Complesso

### 4.1 — Cerniera print-in-place
```
Cerniera a 2 parti per sportello:
- Larghezza totale: 40mm
- 3 knuckle alternati (2 su una parte, 1 sull'altra)
- Pin integrato Ø3mm con clearance 0.3mm
- Fori di montaggio: 2 per lato, M3
- Piastre di montaggio 40×15×3mm
- Fillet r=0.5mm su tutti gli spigoli
- Materiale: PLA

Esporta come assembly .step con le 2 parti separate e posizionate.
In più esporta i 2 STL separati per la stampa.
```
**Testa:** cq.Assembly(), export multi-parte, tolleranze accoppiamento rotativo

---

### 4.2 — Dock di ricarica per telefono con cable management
```
Dock di ricarica per smartphone:
- Appoggio inclinato a 70° per schermo visibile
- Larghezza: 80mm (adatto a telefoni fino a 78mm)
- Base stabile: 80×90mm, altezza frontale 5mm, altezza posteriore 60mm
- Scanalatura per cavo USB-C: larghezza 12mm, profondità nello spessore
- Canale per cavo che corre lungo la base e esce dal retro
- Lip frontale alto 8mm per appoggio telefono
- Pad antiscivolo: 4 incavi Ø10mm profondità 1mm sul fondo (per gommini adesivi)
- Testo "CHARGE" inciso 0.3mm sulla base frontale
- Fillet generosi r=3mm su tutti gli spigoli visibili
- Materiale: PLA silk

Stampa senza supporti. Il canale del cavo deve essere accessibile senza smontare nulla.
```
**Testa:** geometria complessa, sweep per canale cavo, inclinazione, estetica

---

### 4.3 — Enclosure Arduino Uno + breadboard + display OLED
```
Enclosure multi-componente:
- Arduino Uno Rev3: 68.6×53.4mm, standoff M3 nelle 4 posizioni esatte
  (13.97,2.54), (66.04,7.62), (66.04,35.56), (15.24,50.8) mm
- Mini breadboard: 47×35mm, accanto all'Arduino
- Display OLED 0.96" I2C: 27×27mm, apertura rettangolare nel coperchio
- Aperture: USB-B (12×10.9mm) e DC jack (9×11mm) sui lati corretti
- Slot laterali per passaggio cavi jumper (2 slot 15×3mm)
- Griglia ventilazione top (esclusa zona display)
- Snap-fit 4 punti per chiusura
- Fillet r=1.5mm spigoli verticali esterni
- Materiale: PETG
- Piedini h=3mm agli angoli

Esporta body e lid come assembly .step + STL separati per stampa.
```
**Testa:** posizionamento preciso multi-componente, assembly, aperture multiple

---

## 🟪 LIVELLO 5 — Da Immagine + Design Ingegneristico (pipeline completa)

### 5.1 — Reverse engineering da foto
```
[ALLEGA FOTO di un pezzo rotto/consumato]

Ricrea questo pezzo basandoti sulla foto.
Il diametro del foro centrale è 8mm (misurato con calibro).
Materiale: PETG.
Deve essere funzionalmente identico all'originale.
```
**Testa:** skill image-to-3d → spatial reasoning → codegen → validate

---

### 5.2 — Da sketch a mano
```
[ALLEGA FOTO di uno sketch su carta]

Trasforma questo sketch in un modello 3D stampabile.
Le dimensioni scritte sullo sketch sono in millimetri.
Dove non ci sono quote, stima proporzionalmente.
Materiale: PLA.
```
**Testa:** interpretazione sketch, stima dimensioni relative, traduzione in CadQuery

---

### 5.3 — Parte meccanica ad alte prestazioni
```
Staffa di supporto per motore NEMA 17 in ambiente a 80°C:
- 4 fori montaggio motore: M3 a interasse 31mm (pattern quadrato NEMA 17 standard)
- Foro centrale Ø22.5mm per sporgenza motore
- 2 fori di fissaggio laterale M4 per montaggio su profilo 2020
- Spessore base: 5mm
- Braccio laterale con angolazione 90° e nervature di rinforzo
- DEVE resistere a 80°C continuativi con carico assiale ~20N
- Materiale: Tullomer (o PC se Tullomer non disponibile)
- Tutti gli angoli interni: fillet r≥1.5mm (obbligatorio per PC/Tullomer)
- Compensazione shrinkage: +0.5% sulle dimensioni critiche (fori montaggio)

Orientamento stampa: base piatta sul build plate, fibre parallele al carico.
Verifica che nessuna parete sia sotto 2.5mm.
```
**Testa:** vincoli termici, materiale composito, compensazione shrinkage, DFM avanzato

---

### 5.4 — Sistema modulare multi-parte
```
Sistema di organizer da scrivania modulare snap-together:
- Modulo base: 80×80mm, altezza 30mm, con bordo di incastro tipo puzzle
  su tutti e 4 i lati (maschio su 2 lati, femmina sugli altri 2)
- Modulo portapenne: stessa base 80×80mm, 6 fori Ø15mm profondità 80mm
- Modulo porta-telefono: stessa base, con slot inclinato a 70°
- Modulo porta-biglietti: stessa base, slot largo 30mm
- Tutti i moduli si connettono lateralmente tramite gli incastri puzzle
- Materiale: PLA
- Fillet r=1mm su tutti gli spigoli visibili

Esporta come assembly completo .step (tutti e 4 i moduli affiancati)
+ 4 STL separati per la stampa.
I connettori puzzle devono avere tolleranza tight-fit (0.1mm).
```
**Testa:** assembly 4 parti, interfaccia di connessione ripetuta, coerenza dimensionale

---

## ⬛ LIVELLO 6 — Stress Test e Edge Cases

### 6.1 — Ingranaggio parametrico
```
Coppia di ingranaggi cilindrici a denti dritti:
- Ingranaggio 1: 20 denti, modulo 1.5
- Ingranaggio 2: 40 denti, modulo 1.5 (rapporto 2:1)
- Larghezza faccia: 8mm
- Foro albero: Ø5mm con cava per chiavetta 2×2mm su entrambi
- Interasse corretto calcolato dal modulo
- Profilo dente involuta semplificato (approssimazione poligonale accettabile)
- Materiale: PLA-CF per rigidità

Esporta assembly con i 2 ingranaggi in posizione corretta.
+ STL separati. Nota le limitazioni di stampabilità dei denti piccoli.
```
**Testa:** geometria matematica complessa, involuta, assembly posizionato

---

### 6.2 — Parte con sweep lungo path
```
Maniglia ergonomica per cassetto:
- Path: arco ellittico, larghezza 120mm, sporgenza max 30mm dal piano
- Sezione: rettangolo 12×20mm con angoli arrotondati r=4mm
- Piedi di montaggio alle estremità: 20×20×5mm con foro M4 ciascuno
- Transizione graduale (loft) tra la sezione della maniglia e i piedi
- Fillet r=2mm sugli spigoli della transizione
- Materiale: PETG

Usa sweep per il corpo e loft per le transizioni.
Entrambe operazioni impossibili in OpenSCAD.
```
**Testa:** sweep lungo path curvo, loft per transizioni, geometria ergonomica

---

### 6.3 — Enclosure IP-rated con guarnizione
```
Enclosure stagno IP54 per sensore outdoor:
- Dimensioni interne: 60×40×25mm
- Parete 3mm
- Scanalatura per O-ring 2mm (sezione 1.5×1.5mm) sul perimetro del coperchio
- Passacavo: foro Ø8mm con rilievo conico per pressacavo PG7
- 4 viti M3 con inserto a caldo per chiusura, pattern rettangolare
- Boss cilindrici interni per PCB mounting (4 standoff M2.5, altezza 5mm)
- Canale di drenaggio: scanalatura 1×1mm sul fondo esterno
- Materiale: ASA (resistenza UV outdoor)
- Fillet r=2mm su tutti gli spigoli esterni

Esporta body + lid come assembly. Include nota sui parametri slicer
per massimizzare la tenuta stagna (100% infill su pareti, 5 perimetri).
```
**Testa:** scanalatura O-ring (feature di precisione), pressacavo, boss interni, DFM avanzato

---

## Tabella Riepilogativa

| Lv | Esempio | Skill Testate | Feature CadQuery Chiave |
|----|---------|---------------|------------------------|
| 1.1 | Cubo forato | codegen, validate | fillet, hole |
| 1.2 | Distanziale | codegen, validate | cilindro cavo, chamfer |
| 1.3 | Targhetta | codegen, validate | text(), fillet 2D |
| 2.1 | Supporto tubo | + materials | arco, clip a C |
| 2.2 | Fermaporta | + materials | loft (cuneo), pattern |
| 2.3 | Scatola+coperchio | + materials | assembly 2 parti, lip |
| 3.1 | Enclosure ESP32 | tutte tranne image | snap-fit, slot, foro ottica |
| 3.2 | Staffa L | tutte tranne image | nervature, fillet multipli |
| 3.3 | Adattatore tubo | tutte tranne image | **loft** (impossibile in OpenSCAD) |
| 4.1 | Cerniera | tutte tranne image | **assembly multi-parte** |
| 4.2 | Dock ricarica | tutte tranne image | **sweep** canale cavo |
| 4.3 | Multi-PCB enclosure | tutte tranne image | posizionamento preciso multi-board |
| 5.1 | Da foto | **TUTTE** | image-to-3d pipeline |
| 5.2 | Da sketch | **TUTTE** | stima dimensioni da sketch |
| 5.3 | Staffa 80°C | **TUTTE** | Tullomer/PC, DFM termico |
| 5.4 | Modulare 4 parti | tutte tranne image | **assembly 4 parti**, puzzle-fit |
| 6.1 | Ingranaggi | tutte tranne image | geometria involuta, rapporto |
| 6.2 | Maniglia sweep | tutte tranne image | **sweep + loft** combinati |
| 6.3 | IP54 enclosure | tutte tranne image | O-ring groove, pressacavo |
