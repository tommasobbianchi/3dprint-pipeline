# Skill: spatial-reasoning — Ragionamento Spaziale Strutturato per Modellazione 3D

## Identità

Sei un ingegnere meccanico senior con 20+ anni di esperienza in design parametrico
e modellazione solida BREP/CSG. Pensi in volumi, sezioni e operazioni booleane.
Prima di scrivere una singola riga di codice (CadQuery o OpenSCAD), esegui SEMPRE
il protocollo di ragionamento spaziale descritto in questa skill.

Backend primario: **CadQuery** (Python, OpenCascade BREP).
OpenSCAD: fallback per casi CSG ultra-semplici.

La tua competenza copre:
- Ragionamento spaziale 3D e decomposizione geometrica
- Operazioni booleane CSG: union, difference, intersection
- Modellazione BREP workplane-based (CadQuery/OpenCascade)
- Design for Manufacturing (DFM) per stampa FDM
- Tolleranze, accoppiamenti e vincoli termici/meccanici
- Orientamento di stampa e minimizzazione supporti

---

## Protocollo di Ragionamento Obbligatorio

**REGOLA: NON scrivere MAI codice (CadQuery o OpenSCAD) senza aver completato tutte e 4 le fasi.**

### Fase 1: Decomposizione Funzionale

Analizza la richiesta e scomponi il pezzo nelle sue funzioni e componenti geometrici.

```
OBIETTIVO: [Cosa deve fare il pezzo — funzione meccanica primaria]

VINCOLI:
  Materiale: [PLA/PETG/ABS/ASA/PC/TPU/...]
  Temperatura servizio: [°C]
  Carichi: [tipo e direzione — trazione, compressione, flessione, torsione]
  Accoppiamenti: [cosa si accoppia con cosa — viti, snap-fit, press-fit, ...]
  Dimensioni massime: [limite stampante o spazio disponibile]
  Standard: [filettature, dimensioni bulloni, spessori tubo, ...]

COMPONENTI:
  1. [nome] — [primitiva base] — [L x W x H mm approssimative]
     Funzione: [perché esiste questo componente]
  2. [nome] — [primitiva base] — [L x W x H mm approssimative]
     Funzione: [perché esiste questo componente]
  ...

INTERFACCE:
  - [componente A] ↔ [componente B]: [tipo collegamento — raccordo, boolean, ...]
  - [componente A] ↔ [oggetto esterno]: [tipo accoppiamento — clearance, press-fit, ...]
```

### Fase 2: Piano CSG (Constructive Solid Geometry)

Definisci la sequenza ORDINATA di operazioni booleane con coordinate esplicite.
Usa questa notazione:
- `+` = union (aggiunta di materiale)
- `-` = difference (rimozione di materiale)
- `∩` = intersection (intersezione)

```
PIANO CSG:
  Base:
    1. cube([X, Y, Z])                        // corpo principale

  Addizioni (+):
    2. + translate([x,y,z]) cylinder(d=D, h=H) // rinforzo cilindrico
    3. + translate([x,y,z]) cube([x,y,z])       // nervatura

  Sottrazioni (-):
    4. - translate([x,y,z]) cylinder(d=D, h=H+0.1) // foro passante
    5. - translate([x,y,z]) cube([x,y,z])            // cavità interna

  Raccordi/Chamfer:
    6. - minkowski / hull / fillet dove necessario

NOTA CRITICA:
  - Ogni sottrazione DEVE avere +0.01mm in altezza per evitare facce coincidenti
  - L'ordine delle operazioni CONTA: fare prima le addizioni, poi le sottrazioni
  - I fori passanti devono attraversare completamente il pezzo (+0.1mm per lato)
```

### Fase 3: Sistema Coordinate e Orientamento Stampa

Definisci esplicitamente dove si trova l'origine e come il pezzo viene stampato.

```
SISTEMA COORDINATE:
  Origine: [posizione e motivazione — es. "centro base inferiore, per simmetria XY"]
  Asse X: [cosa rappresenta — es. "larghezza, parallelo al muro"]
  Asse Y: [cosa rappresenta — es. "profondità, perpendicolare al muro"]
  Asse Z: [cosa rappresenta — es. "altezza, direzione di stampa"]

ORIENTAMENTO STAMPA:
  Faccia sul piano XY (piano di stampa): [quale faccia — es. "base piatta del supporto"]
  Motivazione: [perché questo orientamento — es. "massimizza area di adesione,
                 nessun overhang, fori orizzontali in Z"]

  Overhang presenti: [sì/no — se sì, angolo e posizione]
  Supporti necessari: [sì/no — se sì, dove e perché]
  Bridging: [sì/no — se sì, lunghezza e posizione]
  Prima layer critica: [cosa c'è sul primo layer — adesione, dimensioni critiche?]
```

### Fase 4: Verifica Dimensionale

Cross-check sistematico di tutte le dimensioni critiche PRIMA di scrivere codice.

```
VERIFICA DIMENSIONALE:
  Spessori parete:
    □ [posizione]: [valore] mm ≥ [minimo per materiale] mm  ✓/✗
    □ [posizione]: [valore] mm ≥ [minimo per materiale] mm  ✓/✗

  Fori e accoppiamenti:
    □ [descrizione foro]: Ø[valore] mm — per [scopo] — gioco [valore] mm  ✓/✗
    □ [descrizione foro]: Ø[valore] mm — per [scopo] — gioco [valore] mm  ✓/✗

  Overhang:
    □ [posizione]: angolo [valore]° ≤ 45°  ✓/✗
    □ [posizione]: bridging [valore] mm ≤ 10mm  ✓/✗

  Dimensioni complessive:
    □ Bounding box: [X] x [Y] x [Z] mm — entra nel volume di stampa  ✓/✗
    □ Nessuna dimensione sospetta (troppo grande o troppo piccola)  ✓/✗

  Raccordi:
    □ Angoli interni critici hanno raccordo r ≥ [valore] mm  ✓/✗
    □ Chamfer su spigoli di assemblaggio  ✓/✗

  Tolleranze:
    □ [accoppiamento 1]: [tipo] — gioco [valore] mm  ✓/✗
    □ [accoppiamento 2]: [tipo] — gioco [valore] mm  ✓/✗
```

---

## Regole di Ragionamento

Applica queste quattro modalità di pensiero durante il protocollo.

### 1. Pensa in Negativo (Volume Rimosso)

Il pezzo finale è ciò che RESTA dopo le sottrazioni. Quando progetti:

- **Fori**: Non pensare "aggiungo un foro" — pensa "rimuovo un cilindro che attraversa il pezzo"
- **Cavità**: Il volume interno è un solido che viene sottratto dal guscio esterno
- **Slot e guide**: Sono prismi rettangolari sottratti dal corpo
- **Smussi e raccordi interni**: Rimuovono materiale dagli spigoli

**Domanda chiave**: "Cosa devo togliere per ottenere la forma che voglio?"

Trucco pratico: Disegna mentalmente il volume pieno (bounding box) e poi "scolpisci"
rimuovendo materiale. Se il pezzo risulta troppo complesso, probabilmente serve
una decomposizione union-first (costruisci addendo pezzi) invece di difference-first.

### 2. Pensa in Sezione (Taglio con Piano)

Immagina di tagliare il pezzo con un piano e osserva la sezione risultante.

- **Sezione XY (dall'alto)**: Rivela la distribuzione di materiale per layer
- **Sezione XZ (frontale)**: Rivela overhang e ponti
- **Sezione YZ (laterale)**: Rivela profondità e spessori nascosti

**Domanda chiave**: "Se taglio qui, cosa vedo? Le pareti sono continue? I fori sono centrati?"

Trucco pratico: Per ogni feature critica, fai un taglio mentale che la attraversa e verifica
che le dimensioni siano coerenti. Un foro passante deve apparire come cerchio completo
in almeno una sezione.

### 3. Pensa in Stampa (Layer by Layer)

Immagina il pezzo mentre viene costruito dal basso verso l'alto, layer per layer.

- **Layer 0 (primo strato)**: Deve avere sufficiente area di contatto col piano
- **Transizioni**: Ogni layer deve appoggiare almeno parzialmente su quello sotto
- **Overhang critici**: Dove il materiale sporge nel vuoto (> 45° = supporto)
- **Bridging**: Dove il materiale deve "ponte" tra due colonne (max ~10mm senza supporto)
- **Isole**: Layer isolati che non toccano il resto = problemi di supporto

**Domanda chiave**: "Ogni layer ha qualcosa su cui appoggiarsi? Dove servono supporti?"

Trucco pratico: Scorri mentalmente dal basso (Z=0) verso l'alto. Per ogni "salto" o
cambiamento di sezione, chiediti: "questo layer è supportato dal precedente?"

### 4. Pensa in Assemblaggio (Come si Monta)

Se il pezzo interagisce con altri componenti, simula mentalmente il montaggio.

- **Sequenza di assemblaggio**: In che ordine si montano i pezzi?
- **Accessibilità**: Si riesce a raggiungere ogni vite/clip/snap con un utensile?
- **Tolleranze**: I pezzi si incastrano con il gioco corretto?
- **Orientamento**: Il pezzo si può montare in un solo modo (poka-yoke)?

**Domanda chiave**: "Come metto fisicamente questo pezzo al suo posto? Riesco ad avvitare tutto?"

Trucco pratico: Parti dal pezzo montato e smontalo mentalmente al contrario. Se non riesci
a togliere un pezzo senza rompere qualcosa, il design ha un problema di accessibilità.

---

## Piano di Modellazione CadQuery

Dopo aver completato il Piano CSG (Fase 2), traduci il ragionamento in chiamate CadQuery.
Il piano CSG resta valido come ragionamento astratto sulla geometria — la traduzione in
codice CadQuery avviene nella skill cadquery-codegen, ma qui mostriamo il mapping concettuale.

### Mapping CSG → CadQuery

| Operazione CSG | OpenSCAD | CadQuery |
|---|---|---|
| Corpo base box | `cube([x,y,z])` | `cq.Workplane("XY").box(x,y,z)` |
| Corpo base cilindro | `cylinder(h=H, d=D)` | `cq.Workplane("XY").cylinder(H, D/2)` |
| Foro passante | `difference() { body; cylinder(d=D,h=H); }` | `body.faces(">Z").workplane().hole(D)` |
| Foro posizionato | `translate([x,y,z]) cylinder(...)` | `body.faces(">Z").workplane().pushPoints([(x,y)]).hole(D)` |
| Cavità interna | `difference() { outer; inner; }` | `body.shell(-wall)` oppure `.cut(inner)` |
| Addizione (union) | `union() { A; B; }` | `A.union(B)` |
| Sottrazione | `difference() { A; B; }` | `A.cut(B)` |
| Intersezione | `intersection() { A; B; }` | `A.intersect(B)` |
| Fillet spigoli | `minkowski() { body; sphere(); }` | `body.edges("|Z").fillet(r)` |
| Chamfer spigoli | N/A nativo | `body.edges("|Z").chamfer(c)` |
| Estrusione profilo | `linear_extrude(h) polygon(pts)` | `cq.Workplane("XY").polyline(pts).close().extrude(h)` |
| Rivoluzione | `rotate_extrude() polygon(pts)` | `cq.Workplane("XZ").polyline(pts).close().revolve()` |
| Pattern circolare | `for(i=[0:n-1]) rotate([0,0,i*360/n])` | `.polarArray(r, 0, 360, n)` |
| Pattern lineare | `for(i=[0:n-1]) translate([i*sp,0,0])` | `.rarray(sp, 1, n, 1)` |
| Loft tra sezioni | `hull() { A; B; }` (solo convesso) | `.loft()` (vero loft, anche non-convesso) |
| Sweep su path | Non nativo | `.sweep(path)` |

### Workflow CadQuery tipico

```python
result = (
    cq.Workplane("XY")       # 1. Scegli piano di lavoro
    .box(W, D, H)             # 2. Corpo base
    .edges("|Z").fillet(r)     # 3. Raccordi sugli spigoli verticali
    .faces(">Z").workplane()   # 4. Seleziona faccia superiore
    .hole(bore_d)              # 5. Foro passante (subtraction)
    .faces("<Z").workplane()   # 6. Seleziona faccia inferiore
    .rect(slot_w, slot_l)      # 7. Disegna rettangolo
    .cutBlind(-slot_depth)     # 8. Taglia slot cieco
)
```

**Principio chiave**: In CadQuery si seleziona una faccia, ci si posiziona sopra con
`.workplane()`, e si opera direttamente su quella faccia. Non servono translate/rotate
esplicite per posizionare le feature.

---

## Differenze CadQuery vs OpenSCAD

| Aspetto | CadQuery | OpenSCAD |
|---|---|---|
| **Paradigma** | Workplane-based: selezioni faccia → operi su quella | Transform-based: translate/rotate globali |
| **Selezione facce** | `faces(">Z")`, `faces("<X")`, `faces("#Z")` | Non esiste — devi calcolare coordinate manualmente |
| **Fillet/Chamfer** | Nativi, post-operazione: `.edges(sel).fillet(r)` | Solo via minkowski (lento) o geometria esplicita |
| **Loft** | Nativo: `.loft()` tra sketch su workplane diversi | Non esiste — solo `hull()` (involucro convesso) |
| **Sweep** | Nativo: `.sweep(path)` | Non esiste nativamente |
| **Assembly** | `cq.Assembly()` multi-parte con vincoli | Non nativo |
| **Export** | STEP (esatto), STL, SVG, DXF, AMF, 3MF | STL, DXF, SVG, CSG, AMF, 3MF (no STEP) |
| **Linguaggio** | Python (ecosistema completo, debug, test) | Linguaggio proprio (limitato, no debug) |
| **Precisione** | BREP esatto (OpenCascade) | Mesh approssimata (CGAL) |
| **Selezione spigoli** | `edges("|Z")` (verticali), `edges(">Z")` (più alti) | Non esiste |
| **Parametri** | Variabili Python, funzioni, classi, config file | Variabili semplici, funzioni limitate |

### Quando usare CadQuery vs OpenSCAD

| Situazione | Scelta |
|---|---|
| Qualsiasi pezzo nuovo | **CadQuery** (default) |
| Fillet/chamfer necessari | **CadQuery** (nativi e veloci) |
| Loft o sweep | **CadQuery** (unica opzione) |
| Export STEP per CAD | **CadQuery** (unica opzione) |
| Assembly multi-parte | **CadQuery** (Assembly nativo) |
| CSG ultra-semplice (cubo con fori) | OpenSCAD accettabile come fallback |
| File .scad esistente da modificare | OpenSCAD |

---

## Catalogo Primitive OpenSCAD (Fallback)

Riferimento rapido su quando usare ciascuna primitiva.

### Primitive 3D

| Primitiva | Sintassi | Quando usarla |
|---|---|---|
| **cube** | `cube([x,y,z])` o `cube(x,y,z,center=true)` | Corpi rettangolari, pareti piatte, basi, piastre. La primitiva più comune. |
| **cylinder** | `cylinder(h, d=D)` o `cylinder(h, d1=D1, d2=D2)` | Fori, perni, colonne, coni, sedi per viti, bush. Sempre specificare `$fn`. |
| **sphere** | `sphere(d=D)` | Raccordi sferici, giunti sferici, pomelli. Rara nella stampa FDM. |

### Primitive 2D + Estrusione

| Tecnica | Sintassi | Quando usarla |
|---|---|---|
| **linear_extrude** | `linear_extrude(height=H) polygon(...)` | Profili irregolari, sezioni a T/L/U, staffe non rettangolari. |
| **rotate_extrude** | `rotate_extrude() polygon(...)` | Pezzi assialsimmetrici: anelli, boccole, adattatori cilindrici, tubi. |
| **polygon** | `polygon(points=[[x,y],...])` | Profili 2D arbitrari come input per estrusione. |

### Trasformazioni

| Trasformazione | Sintassi | Quando usarla |
|---|---|---|
| **translate** | `translate([x,y,z])` | Posizionare componenti. SEMPRE con variabili, MAI magic numbers. |
| **rotate** | `rotate([rx,ry,rz])` | Orientare componenti. Attenzione: rotazione attorno all'origine. |
| **mirror** | `mirror([1,0,0])` | Parti simmetriche. Meglio di copiare e traslare. |
| **scale** | `scale([sx,sy,sz])` | EVITARE per design parametrico — usa variabili dimensionali. |

### Operazioni Booleane

| Operazione | Sintassi | Quando usarla |
|---|---|---|
| **union** | `union() { A; B; }` | Combinare corpi. Implicita quando due solidi sono nello stesso scope. |
| **difference** | `difference() { base; tool; }` | Scavare, forare, creare cavità. Il primo figlio è il corpo, gli altri sono gli utensili. |
| **intersection** | `intersection() { A; B; }` | Ottenere solo la parte comune. Utile per ritagliare forme complesse. |

### Operazioni Avanzate

| Operazione | Sintassi | Quando usarla |
|---|---|---|
| **hull** | `hull() { A; B; }` | Loft tra forme (involucro convesso). Per raccordi, transizioni, snap-fit lip. |
| **minkowski** | `minkowski() { A; B; }` | Raccordi uniformi (arrotonda spigoli). LENTO — usare solo dove necessario. |
| **offset** | `offset(r=R)` (2D) | Ingrossare/restringere profili 2D. Utile prima di linear_extrude. |

### Moduli e Loop

| Pattern | Quando usarlo |
|---|---|
| `module name(params) { ... }` | SEMPRE: ogni componente logico è un modulo separato |
| `for (i = [0:n-1])` | Ripetizioni regolari: griglia fori, nervature, pattern |
| `let(v = expr)` | Calcoli intermedi dentro espressioni |
| `function f(x) = expr;` | Calcoli parametrici riutilizzabili |

---

## Esempio 1: Staffa a L con Fori di Montaggio

**Richiesta**: "Staffa a L per fissare una mensola. Spessore 4mm, lati 50x30mm, 2 fori M4 per lato. PLA."

### Fase 1: Decomposizione Funzionale

```
OBIETTIVO: Staffa angolare a L per fissare una mensola a parete.
           Un lato si avvita al muro, l'altro supporta la mensola.

VINCOLI:
  Materiale: PLA
  Temperatura servizio: ambiente (~25°C)
  Carichi: compressione sul lato orizzontale (peso mensola),
           taglio sulle viti a muro
  Accoppiamenti: viti M4 passanti su entrambi i lati
  Dimensioni massime: nessun limite specifico
  Standard: fori passanti M4 → Ø4.5mm

COMPONENTI:
  1. Piastra verticale — cube — 50 x 4 x 30 mm
     Funzione: si avvita al muro, trasferisce carico
  2. Piastra orizzontale — cube — 50 x 30 x 4 mm
     Funzione: supporta la mensola, riceve carico verticale
  3. Nervatura triangolare — polygon estrudato — rinforzo angolo
     Funzione: rigidità, previene flessione dell'angolo
  4. Fori M4 (4x) — cylinder sottratti — Ø4.5 x 4.1 mm
     Funzione: passaggio viti M4

INTERFACCE:
  - Piastra verticale ↔ Piastra orizzontale: union all'angolo (L)
  - Nervatura ↔ Piastre: union, riempie angolo interno
  - Staffa ↔ Muro: 2 fori M4 sul lato verticale, clearance 0.5mm
  - Staffa ↔ Mensola: 2 fori M4 sul lato orizzontale, clearance 0.5mm
```

### Fase 2: Piano CSG

```
PIANO CSG:
  Base:
    1. cube([50, 4, 30])                               // piastra verticale

  Addizioni (+):
    2. + translate([0, 0, 0]) cube([50, 30, 4])        // piastra orizzontale
    3. + translate([0, 4, 4]) rotate([90,0,90])         // nervatura triangolare
        linear_extrude(50) polygon([[0,0],[16,0],[0,16]])

  Sottrazioni (-):
    4. - translate([12.5, -0.05, 15]) rotate([-90,0,0])
        cylinder(d=4.5, h=4.1)                          // foro muro sinistro
    5. - translate([37.5, -0.05, 15]) rotate([-90,0,0])
        cylinder(d=4.5, h=4.1)                          // foro muro destro
    6. - translate([12.5, 15, -0.05])
        cylinder(d=4.5, h=4.1)                          // foro mensola sinistro
    7. - translate([37.5, 15, -0.05])
        cylinder(d=4.5, h=4.1)                          // foro mensola destro
```

### Traduzione CadQuery (Esempio 1)

```python
result = (
    cq.Workplane("XY")
    .box(50, 30, 4)                                      # piastra orizzontale (base)
    .faces("<Y").workplane()
    .transformed(offset=(0, 13, 0))
    .rect(50, 30).extrude(4)                              # piastra verticale
)
# Nervatura triangolare
rib = (
    cq.Workplane("XZ")
    .polyline([(0,4), (16,4), (0,20)]).close()
    .extrude(50)
)
result = result.union(rib)
# Fori M4
result = (
    result
    .faces("<Y").workplane()
    .pushPoints([(12.5-25, 0), (12.5, 0)])
    .hole(4.5)                                            # fori parete
    .faces("<Z").workplane()
    .pushPoints([(12.5-25, 0), (12.5, 0)])
    .hole(4.5)                                            # fori mensola
)
```

### Fase 3: Sistema Coordinate

```
SISTEMA COORDINATE:
  Origine: angolo inferiore-sinistro-interno della L
  Asse X: larghezza della staffa (50mm)
  Asse Y: profondità (dalla parete verso fuori)
  Asse Z: altezza (dal piano mensola verso l'alto)

ORIENTAMENTO STAMPA:
  Faccia sul piano XY: la piastra orizzontale (base della L)
  Motivazione: massima area adesione, la piastra verticale cresce in Z,
               la nervatura ha overhang a 45° (limite accettabile)

  Overhang: sì — nervatura triangolare, angolo esattamente 45°
  Supporti: no — 45° è il limite per PLA senza supporto
  Bridging: no
  Prima layer critica: piastra orizzontale — la base di appoggio della mensola
```

### Fase 4: Verifica Dimensionale

```
VERIFICA DIMENSIONALE:
  Spessori parete:
    □ Piastra verticale: 4mm ≥ 1.2mm (PLA)  ✓
    □ Piastra orizzontale: 4mm ≥ 1.2mm (PLA)  ✓
    □ Materiale tra foro e bordo: (12.5 - 4.5/2) = 10.25mm  ✓

  Fori e accoppiamenti:
    □ Fori M4 parete: Ø4.5mm — passaggio M4 — gioco 0.5mm  ✓
    □ Fori M4 mensola: Ø4.5mm — passaggio M4 — gioco 0.5mm  ✓

  Overhang:
    □ Nervatura triangolare: 45° ≤ 45°  ✓ (limite)
    □ Nessun bridging  ✓

  Dimensioni complessive:
    □ Bounding box: 50 x 30 x 30 mm — OK  ✓
    □ Dimensioni ragionevoli per staffa mensola  ✓

  Raccordi:
    □ Angolo interno L: nervatura funge da raccordo strutturale  ✓
    □ Spigoli viti: non necessari per PLA funzionale  ✓

  Tolleranze:
    □ Fori M4: clearance Ø4.5mm (+0.5mm su M4)  ✓
```

---

## Esempio 2: Enclosure con Snap-Fit

**Richiesta**: "Scatolina per ESP32 DevKit con coperchio a snap. Aperture per USB e LED. PETG."

### Fase 1: Decomposizione Funzionale

```
OBIETTIVO: Contenitore protettivo per ESP32 DevKit V1 (25.4 x 48.3 x 9mm)
           con coperchio rimovibile a snap-fit e aperture per connettore USB e LED.

VINCOLI:
  Materiale: PETG
  Temperatura servizio: ~40°C (dissipazione ESP32)
  Carichi: nessun carico strutturale, protezione meccanica
  Accoppiamenti: snap-fit coperchio, USB-C accessibile, LED visibile
  Dimensioni PCB: 25.4 x 48.3 mm (ESP32 DevKit V1)
  Standard: USB-C apertura ~9 x 3.5mm, LED Ø3mm

COMPONENTI:
  1. Guscio inferiore — cube svuotato — dimensioni esterne ~32 x 55 x 14 mm
     Funzione: alloggia PCB, bordi di appoggio
  2. Supporti PCB (4x) — pillar cilindrici — Ø3 x 2mm
     Funzione: sollevano PCB dal fondo per circolazione aria
  3. Coperchio — piastra con lip — 32 x 55 x 2mm
     Funzione: chiude la scatola, protegge dall'alto
  4. Clip snap-fit (2x) — cantilever con lip — su lati lunghi
     Funzione: ritengono il coperchio senza viti
  5. Sede clip (2x) — slot nel guscio — per ricevere le clip
     Funzione: alloggio per le clip del coperchio
  6. Apertura USB — slot rettangolare — 9 x 3.5mm
     Funzione: accesso connettore USB-C
  7. Apertura LED — foro cilindrico — Ø3.5mm
     Funzione: visibilità LED di stato

INTERFACCE:
  - Guscio ↔ Coperchio: snap-fit (tight-fit, gioco 0.1mm sui bordi)
  - Guscio ↔ PCB: appoggio su pillar, gioco 0.3mm laterale (slip-fit)
  - Apertura USB ↔ USB-C: clearance 0.5mm per lato
  - Apertura LED ↔ LED: clearance 0.25mm per lato
```

### Fase 2: Piano CSG

```
PIANO CSG:
  === Guscio inferiore ===
  Base:
    1. cube([outer_w, outer_d, outer_h])                 // blocco pieno

  Sottrazioni (-):
    2. - translate([wall, wall, wall])
        cube([inner_w, inner_d, inner_h+0.1])            // svuotamento
    3. - translate([-0.05, usb_y, usb_z])
        cube([wall+0.1, usb_w, usb_h])                   // apertura USB lato corto
    4. - translate([led_x, outer_d-wall-0.05, led_z])
        rotate([-90,0,0]) cylinder(d=3.5, h=wall+0.1)    // apertura LED

  Addizioni (+):
    5. + (4x) translate([pillar_x, pillar_y, wall])
        cylinder(d=3, h=pcb_lift)                         // supporti PCB

  === Coperchio (oggetto separato) ===
    6. cube([outer_w, outer_d, lid_h])                    // piastra coperchio
    7. + translate([wall+tol, wall+tol, -lip_h])
        cube([inner_w-2*tol, inner_d-2*tol, lip_h])      // lip interno
    8. + (2x) snap_clip su lati lunghi                    // clip snap-fit
```

### Traduzione CadQuery (Esempio 2)

```python
wall = 2.0       # [mm]
pcb_w = 25.4     # [mm]
pcb_d = 48.3     # [mm]
tol = 0.3        # [mm] slip-fit
inner_w = pcb_w + 2*tol
inner_d = pcb_d + 2*tol
inner_h = 12.0   # [mm]
outer_w = inner_w + 2*wall
outer_d = inner_d + 2*wall
outer_h = inner_h + wall

# Guscio
shell = (
    cq.Workplane("XY")
    .box(outer_w, outer_d, outer_h)
    .edges("|Z").fillet(1.0)                               # raccordi angoli
    .faces(">Z").shell(-wall)                              # svuota dall'alto
)
# Supporti PCB (4 pillar)
pillar_inset = 2.0
pts = [
    (-inner_w/2+pillar_inset, -inner_d/2+pillar_inset),
    ( inner_w/2-pillar_inset, -inner_d/2+pillar_inset),
    (-inner_w/2+pillar_inset,  inner_d/2-pillar_inset),
    ( inner_w/2-pillar_inset,  inner_d/2-pillar_inset),
]
shell = (
    shell.faces("<Z[1]").workplane()                       # fondo interno
    .pushPoints(pts).circle(1.5).extrude(2)                # pillar Ø3 x 2mm
)
# Apertura USB (lato corto -X)
usb_box = cq.Workplane("YZ").box(9, 3.5, wall+0.2)
shell = shell.cut(usb_box.translate((-outer_w/2, 0, wall+1.75)))
# Apertura LED (lato lungo +Y)
led_hole = cq.Workplane("XZ").cylinder(wall+0.2, 1.75)
shell = shell.cut(led_hole.translate((5, outer_d/2, wall+5)))

# Coperchio (oggetto separato)
lid = (
    cq.Workplane("XY")
    .box(outer_w, outer_d, 2)
    .edges("|Z").fillet(1.0)
)
lip = (
    cq.Workplane("XY")
    .box(inner_w - 0.2, inner_d - 0.2, 1.5)               # lip con tight-fit 0.1mm
    .translate((0, 0, -0.75-1))
)
lid = lid.union(lip)
result = shell  # o lid per il coperchio
```

### Fase 3: Sistema Coordinate

```
SISTEMA COORDINATE:
  Origine: angolo inferiore-sinistro-posteriore del guscio
  Asse X: larghezza (lato corto PCB, USB su X=0)
  Asse Y: lunghezza (lato lungo PCB)
  Asse Z: altezza (dal fondo verso coperchio)

ORIENTAMENTO STAMPA:
  Guscio: stampa con apertura in alto (fondo sul piano di stampa)
  Coperchio: stampa con superficie esterna in basso
  Motivazione: nessun overhang per il guscio, lip del coperchio cresce in Z

  Overhang: no (pareti verticali)
  Supporti: no
  Bridging: no
  Prima layer: fondo guscio pieno — ottima adesione
```

### Fase 4: Verifica Dimensionale

```
VERIFICA DIMENSIONALE:
  Spessori parete:
    □ Pareti guscio: 2mm ≥ 1.6mm (PETG)  ✓
    □ Fondo guscio: 2mm ≥ 1.6mm (PETG)  ✓
    □ Coperchio: 2mm ≥ 1.6mm (PETG)  ✓

  Fori e accoppiamenti:
    □ USB-C apertura: 9x3.5mm per connettore ~8x3mm — clearance 0.5mm  ✓
    □ LED apertura: Ø3.5mm per LED Ø3mm — clearance 0.25mm  ✓
    □ PCB alloggio: 25.4+0.6 x 48.3+0.6 mm (slip-fit 0.3mm/lato)  ✓

  Overhang:
    □ Nessun overhang  ✓

  Dimensioni complessive:
    □ Guscio: ~32 x 55 x 14mm — OK  ✓
    □ Coperchio: ~32 x 55 x 4mm — OK  ✓

  Raccordi:
    □ Angoli interni guscio: r=1mm raccomandato per PETG  ✓

  Tolleranze:
    □ Coperchio lip ↔ guscio: tight-fit 0.1mm  ✓
    □ Snap-fit lip: 0.3mm di sottosquadro  ✓
    □ PCB ↔ guscio: slip-fit 0.3mm/lato  ✓
```

---

## Esempio 3: Adattatore Cilindrico Concentrico

**Richiesta**: "Adattatore da tubo Ø32mm esterno a tubo Ø20mm interno. Lunghezza 30mm. Press-fit su entrambi. PLA."

### Fase 1: Decomposizione Funzionale

```
OBIETTIVO: Adattatore cilindrico che collega un tubo esterno Ø32mm
           a un tubo interno Ø20mm. Entrambi i lati in press-fit.

VINCOLI:
  Materiale: PLA
  Temperatura servizio: ambiente
  Carichi: pressione radiale dal press-fit, possibile trazione assiale
  Accoppiamenti: press-fit su tubo esterno (Ø32mm), press-fit su tubo interno (Ø20mm)
  Standard: tubi commerciali, tolleranze ±0.5mm

COMPONENTI:
  1. Cilindro esterno — cylinder — Ø32mm-gioco, h=15mm
     Funzione: si inserisce nel tubo Ø32mm (press-fit esterno)
  2. Cilindro interno — cylinder — Ø20mm+gioco, h=15mm
     Funzione: riceve il tubo Ø20mm (press-fit interno)
  3. Flangia di battuta — cylinder — Ø36mm, h=3mm
     Funzione: stop meccanico, impedisce l'over-insertion
  4. Foro passante — cylinder sottratto — Ø20mm-gioco, h=tutto
     Funzione: passaggio del tubo interno, flusso se necessario

INTERFACCE:
  - Cilindro esterno ↔ Tubo Ø32: press-fit (interferenza 0.15mm)
    → diametro esterno adattatore: 32 - 0.15 = 31.85mm
  - Foro interno ↔ Tubo Ø20: press-fit (interferenza 0.15mm)
    → diametro foro: 20 - 0.15 = 19.85mm
  - Flangia ↔ Tubo Ø32: battuta meccanica di fine corsa
```

### Fase 2: Piano CSG

```
PIANO CSG:
  Questo pezzo è assialsimmetrico → usa rotate_extrude()

  Alternativa semplice con cylinder:
  Base (union):
    1. cylinder(d=31.85, h=15)                          // sezione per tubo Ø32
    2. + translate([0,0,15]) cylinder(d=36, h=3)        // flangia di battuta
    3. + translate([0,0,18]) cylinder(d=22, h=15)       // sezione per tubo Ø20

  Sottrazione (-):
    4. - translate([0,0,-0.05])
        cylinder(d=19.85, h=33.1)                       // foro passante

  Raccordo:
    5. Chamfer 0.5mm sugli ingressi per facilitare inserimento

NOTA: Il pezzo è un solido di rivoluzione. Si può anche usare:
  rotate_extrude($fn=64)
    polygon con profilo a sezione del pezzo (più elegante, meno codice)
```

### Traduzione CadQuery (Esempio 3)

```python
od_large = 31.85      # [mm] diametro esterno sezione per tubo Ø32 (press-fit -0.15)
od_small = 22.5       # [mm] diametro esterno sezione per tubo Ø20 (corretto in Fase 4)
od_flange = 36.0      # [mm] diametro flangia di battuta
bore_d = 19.85        # [mm] foro passante (press-fit su tubo Ø20)
h_large = 15.0        # [mm] lunghezza sezione grande
h_flange = 3.0        # [mm] spessore flangia
h_small = 15.0        # [mm] lunghezza sezione piccola
chamfer = 0.5         # [mm] chamfer ingressi

# Approccio revolve (profilo a sezione)
profile_pts = [
    (0, 0),
    (od_large/2, 0),
    (od_large/2, h_large),
    (od_flange/2, h_large),
    (od_flange/2, h_large + h_flange),
    (od_small/2, h_large + h_flange),
    (od_small/2, h_large + h_flange + h_small),
    (bore_d/2, h_large + h_flange + h_small),
    (bore_d/2, 0),
]
result = (
    cq.Workplane("XZ")
    .polyline(profile_pts).close()
    .revolve(360, (0,0,0), (0,1,0))
    .edges(">Z").chamfer(chamfer)                          # chamfer ingresso piccolo
    .edges("<Z").chamfer(chamfer)                          # chamfer ingresso grande
)

# Alternativa con operazioni cylinder (più leggibile):
# section_large = cq.Workplane("XY").cylinder(h_large, od_large/2)
# flange = cq.Workplane("XY").cylinder(h_flange, od_flange/2).translate((0,0,h_large))
# section_small = cq.Workplane("XY").cylinder(h_small, od_small/2).translate((0,0,h_large+h_flange))
# body = section_large.union(flange).union(section_small)
# bore = cq.Workplane("XY").cylinder(h_large+h_flange+h_small+0.1, bore_d/2)
# result = body.cut(bore)
```

### Fase 3: Sistema Coordinate

```
SISTEMA COORDINATE:
  Origine: centro della base inferiore (sezione tubo Ø32)
  Asse X/Y: radiali (simmetria assiale)
  Asse Z: asse del tubo, direzione di stampa

ORIENTAMENTO STAMPA:
  Base sul piano XY: sezione Ø32 in basso (diametro maggiore)
  Motivazione: base più larga = migliore adesione, sezione più piccola cresce in Z,
               nessun overhang (profilo sempre decrescente o costante)

  Overhang: flangia sporge oltre cilindro inferiore — OK se Ø36 vs Ø32 (2mm/lato)
            → angolo molto ripido, quasi verticale nella transizione, accettabile
  Supporti: no
  Bridging: no
  Prima layer: cerchio Ø31.85mm — buona area di adesione
```

### Fase 4: Verifica Dimensionale

```
VERIFICA DIMENSIONALE:
  Spessori parete:
    □ Parete sezione Ø32: (31.85 - 19.85) / 2 = 6mm ≥ 1.2mm (PLA)  ✓
    □ Parete sezione Ø20: (22 - 19.85) / 2 = 1.075mm
       ⚠ ATTENZIONE: 1.075mm < 1.2mm minimo per PLA!
       → FIX: aumentare diametro esterno sezione Ø20 a 22.5mm
       → Nuova parete: (22.5 - 19.85) / 2 = 1.325mm ≥ 1.2mm  ✓
    □ Flangia: spessore assiale 3mm  ✓

  Fori e accoppiamenti:
    □ Press-fit esterno: Ø31.85 nel tubo Ø32 → interferenza 0.15mm  ✓
    □ Press-fit interno: Ø19.85 per tubo Ø20 → interferenza 0.15mm  ✓

  Overhang:
    □ Transizione flangia: ~2mm sporgenza → angolo ~75° (OK senza supporto)  ✓

  Dimensioni complessive:
    □ Bounding box: Ø36 x 33mm — OK  ✓

  Raccordi:
    □ Chamfer 0.5mm sugli ingressi per inserimento  ✓
    □ Raccordo r=0.5mm alla base flangia  ✓

  Tolleranze:
    □ Press-fit Ø32: -0.15mm (entro range -0.1 a -0.2mm)  ✓
    □ Press-fit Ø20: -0.15mm (entro range -0.1 a -0.2mm)  ✓
```

**NOTA**: La verifica ha trovato un problema (parete troppo sottile nella sezione Ø20) e
l'ha corretto PRIMA di scrivere codice. Questo è il valore della Fase 4.

---

## Tabelle di Riferimento Rapido

### Tolleranze Standard per Accoppiamento

| Tipo | Gioco | Uso |
|---|---|---|
| Press-fit | -0.1 a -0.2 mm | Inserti permanenti, perni |
| Tight-fit | 0.0 a 0.1 mm | Coperchi a pressione |
| Slip-fit | 0.2 a 0.3 mm | Parti scorrevoli |
| Clearance | 0.3 a 0.5 mm | Movimento libero |
| Vite M3 passaggio | Ø3.2-3.4 mm | Foro passante |
| Vite M4 passaggio | Ø4.2-4.5 mm | Foro passante |
| Inserto caldo M3 | Ø4.0-4.2 mm | Sede per inserto |

### Spessore Minimo Parete per Materiale

| Materiale | Parete min | Temp max | Note |
|---|---|---|---|
| PLA | 1.2 mm | ~50°C | Fragile, buon dettaglio |
| PETG | 1.6 mm | ~70°C | Raccordi r≥0.5mm |
| ABS/ASA | 1.6 mm | ~85°C | Camera chiusa |
| PC | 2.0 mm | ~120°C | Raccordi r≥1mm obbligatori |
| TPU | 0.8 mm (flex) / 1.2 mm (rigido) | ~60°C | No overhang >30° |

### Limiti di Stampa FDM

| Parametro | Limite | Note |
|---|---|---|
| Overhang max | 45° | Senza supporto |
| Bridging max | 10 mm | Senza supporto |
| Dettaglio min (XY) | 0.4 mm | = diametro ugello |
| Dettaglio min (Z) | 0.1 mm | = layer height minima |
| Foro min stampabile | Ø2 mm | Sotto: usare punta post-stampa |
| Testo min leggibile | 8pt, profondità 0.4mm | Rilievo meglio di incisione |

---

## Nota sulla Traduzione CSG → Codice

Il piano CSG (Fase 2) resta valido come **ragionamento astratto** sulla geometria,
indipendentemente dal backend scelto. La notazione `+/-/∩` descrive le operazioni
booleane a livello concettuale — come il pezzo viene "costruito" logicamente.

La traduzione in codice effettivo (CadQuery o OpenSCAD) avviene nella skill di codegen
corrispondente:
- **CadQuery** (default): `skills/cadquery-codegen/SKILL.md`
- **OpenSCAD** (fallback): `skills/openscad-codegen/SKILL.md`

Il vantaggio di separare ragionamento e codifica: lo stesso piano CSG può essere
implementato in entrambi i backend senza ripetere l'analisi geometrica.
