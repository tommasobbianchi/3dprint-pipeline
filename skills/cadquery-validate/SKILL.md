# SKILL: cadquery-validate — Validazione e Fix Automatico CadQuery

## Identità
Loop automatico di validazione, diagnosi e correzione del codice CadQuery.
Esegue fino a 5 tentativi per produrre un modello BREP valido con export STEP+STL.

---

## 1. Workflow — Loop Fix Automatico

```
per tentativo in 1..5:
    risultato = esegui_python(codice)

    se risultato.successo:
        bb = bounding_box(risultato)
        vol = volume(risultato)

        se bb valido E vol > 0:
            export(STEP + STL)
            stampa REPORT
            return SUCCESSO
        altrimenti:
            codice = fix_geometry(codice, bb, vol)
    altrimenti:
        errore = analizza_traceback(risultato.stderr)
        fix = cerca_in_catalogo(errore)
        codice = applica_fix(codice, fix)

return FALLIMENTO (dopo 5 tentativi)
```

### 1.1 Regole del Loop

1. **Max 5 iterazioni** — se dopo 5 tentativi il codice non funziona, FERMA e riporta tutti gli errori
2. **Un fix alla volta** — non applicare fix multipli nello stesso tentativo (confonde la diagnosi)
3. **Preserva parametri** — non cambiare mai i parametri dell'utente a meno che siano la causa dell'errore
4. **Log ogni tentativo** — traccia errore, fix applicato, risultato
5. **Nessun try/except cieco** — non nascondere errori con `try: ... except: pass`

### 1.2 Integrazione MCP

```
SE tool MCP cadquery_validate disponibile:
    usa cadquery_validate(python_code) → { valid, errors, bounding_box, volume_mm3 }
    usa cadquery_export(python_code, formats, output_dir) → { files, bounding_box }
    usa cadquery_info(python_code) → { bounding_box, volume_mm3, surface_area_mm2 }
ALTRIMENTI:
    esegui `python3 script.py` via bash
    analizza stdout per BB/volume, stderr per errori
```

---

## 2. Catalogo Errori CadQuery — Diagnosi e Fix

### 2.1 Errori di Kernel (OpenCascade)

| # | Errore (traceback) | Causa probabile | Fix automatico |
|---|---|---|---|
| 1 | `StdFail_NotDone` in fillet/chamfer | Raggio fillet > metà dello spessore minimo, oppure edge troppo corto dopo boolean | Riduci raggio a `min(raggio, spessore/2 - 0.1)`. Se fallisce ancora, usa `NearestToPointSelector` per edge specifici invece di selettori broad (`\|Z`, `\|Y`) |
| 2 | `StdFail_NotDone` in boolean (cut/union) | Geometrie tangenti, coincidenti o con facce complanari | Offset una delle geometrie di 0.01mm su un asse. Esempio: `translate((0.01, 0, 0))` |
| 3 | `BRep_API: not done` | Boolean tra solidi con intersezione degenere (edge-on-edge) | Scala leggermente un operando: `* 1.001` o offset 0.01mm |
| 4 | `ShapeAnalysis_Wire: Wire is not closed` | Polyline/sketch non chiuso | Aggiungi `.close()` prima di `.extrude()` |
| 5 | `Shape is null` / `TopoDS_Shape is null` | Operazione produce corpo vuoto (cut rimuove tutto, extrude di altezza 0) | Verifica che dimensioni > 0, che il cut non superi il corpo, che extrude abbia altezza positiva |

### 2.2 Errori di API CadQuery

| # | Errore (traceback) | Causa probabile | Fix automatico |
|---|---|---|---|
| 6 | `ValueError: No pending wires` | `.extrude()` senza sketch 2D precedente | Aggiungi `.rect()`, `.circle()` o altro sketch prima di `.extrude()` |
| 7 | `ValueError: Cannot resolve selector` | Selettore ambiguo dopo boolean (es. `">Z"` con facce multiple alla stessa Z) | Usa `.faces(sel).first().workplane()` oppure `NearestToPointSelector((x,y,z))` |
| 8 | `ValueError: negative or zero` in extrude | Valore di estrusione negativo passato a `.extrude()` | Usa `abs(valore)` o cambia a `.cutBlind(-valore)` se l'intento era una tasca |
| 9 | `ValueError: Unknown color name` | Nome colore CSS non supportato da CadQuery | Sostituisci con `cq.Color(r, g, b)` usando float RGB 0.0-1.0 |
| 10 | `ModuleNotFoundError: No module named 'cadquery'` | CadQuery non installato nell'ambiente Python | Esegui `pip install cadquery` o verifica il virtualenv |

### 2.3 Errori Geometrici (post-esecuzione)

| # | Condizione | Causa probabile | Fix automatico |
|---|---|---|---|
| 11 | Bounding box > 500mm su qualsiasi asse | Errore di scala (unità pollici o metri invece di mm) | Se BB ~25.4x troppo grande: dividi per 25.4 (pollici→mm). Se BB ~1000x: dividi per 1000 (m→mm) |
| 12 | Bounding box < 0.1mm su qualsiasi asse | Pezzo degenere (piatto 2D) o errore di scala | Verifica che tutte le dimensioni siano in mm e > 0.5mm. Se un asse è 0: manca una estrusione |
| 13 | Volume = 0 mm³ | Corpo completamente svuotato da cut, shell troppo sottile, o shape non solido | Verifica che `wall > 0`, che shell non svuoti tutto, che cut non rimuova il corpo intero |
| 14 | Volume negativo o NaN | Shape BREP corrotto | Ricostruisci la geometria dall'inizio con operazioni più semplici |
| 15 | Export fallito (file non creato) | `result` non è un oggetto CadQuery valido, o path non scrivibile | Verifica che `result` sia `cq.Workplane`, non un valore intermedio. Verifica che la directory esista |

### 2.4 Errori di Pattern (codice strutturale)

| # | Pattern rilevato | Problema | Fix automatico |
|---|---|---|---|
| 16 | `.edges("\|Z").fillet()` dopo `.union()` o `.cut()` | Selettore broad cattura edge piccoli creati da boolean | Sposta il fillet PRIMA delle boolean, oppure usa `NearestToPointSelector` |
| 17 | `import numpy` / `from stl import` / `import trimesh` | Mesh diretta invece di modellazione BREP | Rimuovi e riscrivi con CadQuery puro |
| 18 | Nessun `cq.exporters.export()` nel codice | Script non esporta nulla | Aggiungi export STEP+STL alla fine dello script |
| 19 | `result` non definito a livello modulo | Il modello non è accessibile per validazione/export | Assicura che `result = make_assembly()` sia chiamato a livello modulo |
| 20 | `try: ... except: pass` attorno a fillet/chamfer | Nasconde errori kernel | Rimuovi il try/except e applica il fix appropriato dal catalogo |

---

## 3. Albero Decisionale — Fix Strategy

```
ERRORE RICEVUTO
│
├─ Contiene "StdFail_NotDone"?
│   ├─ Stack contiene "fillet" o "chamfer"?
│   │   ├─ Selettore è "|Z", "|Y", "|X"? → Sposta fillet PRIMA di boolean (fix #16)
│   │   ├─ Raggio > min_spessore / 2? → Riduci raggio (fix #1)
│   │   └─ Altrimenti → Usa NearestToPointSelector (fix #1 alternativo)
│   └─ Stack contiene "BRepAlgoAPI" / "boolean"?
│       └─ Offset 0.01mm su un operando (fix #2)
│
├─ Contiene "Wire is not closed"?
│   └─ Aggiungi .close() (fix #4)
│
├─ Contiene "No pending wires"?
│   └─ Aggiungi sketch 2D prima di extrude (fix #6)
│
├─ Contiene "Cannot resolve selector"?
│   └─ Aggiungi .first() o usa NearestToPointSelector (fix #7)
│
├─ Contiene "negative or zero"?
│   └─ abs() o converti in cutBlind (fix #8)
│
├─ Contiene "Unknown color name"?
│   └─ Sostituisci con cq.Color(r, g, b) float (fix #9)
│
├─ Contiene "Shape is null"?
│   └─ Verifica dimensioni e operazioni (fix #5)
│
├─ Contiene "ModuleNotFoundError"?
│   └─ pip install cadquery (fix #10)
│
└─ Nessun match nel catalogo?
    └─ Analizza traceback manualmente, applica fix specifico
```

---

## 4. Post-Validazione — Report Formattato

Dopo una validazione riuscita, genera SEMPRE questo report:

```
✅ Esecuzione Python: OK (tentativo N/5)
✅ Shape BREP: Valido
✅ Bounding box: {X:.1f} × {Y:.1f} × {Z:.1f} mm
📊 Volume: {vol:,.0f} mm³ ({vol/1000:.1f} cm³)
📐 Area superficiale: {area:,.0f} mm²
⚖️ Peso stimato: {peso:.1f}g ({materiale}, {infill}% infill)
⏱️ Tempo stampa stimato: ~{ore}h {min}min
📁 Export: {nome}.step + {nome}.stl
```

### 4.1 Calcolo Peso Stimato

```python
# Densità materiali [g/cm³]
DENSITA = {
    "PLA":  1.24,
    "PETG": 1.27,
    "ABS":  1.04,
    "ASA":  1.07,
    "PC":   1.20,
    "TPU":  1.21,
    "Nylon": 1.14,
}

# Peso = volume_cm3 * densità * fattore_infill
# fattore_infill tiene conto di shell (2-3 perimetri ~0.8-1.2mm) + infill interno
# Approssimazione: shell 100% + core a % infill
# Per pezzi piccoli (< 30mm): quasi tutto shell → fattore ~0.8-0.9
# Per pezzi grandi (> 100mm): più infill → fattore = shell_fraction + (1-shell_fraction) * infill%

def peso_stimato(vol_mm3, materiale="PLA", infill_pct=20):
    vol_cm3 = vol_mm3 / 1000
    densita = DENSITA.get(materiale, 1.24)
    fattore = 0.3 + 0.7 * (infill_pct / 100)  # approssimazione semplice
    return vol_cm3 * densita * fattore
```

### 4.2 Calcolo Tempo Stampa Stimato

```python
# Approssimazione basata su volume e altezza
# Velocità media effettiva: ~15-25 cm³/h per FDM standard
# Fattore layer_height: 0.2mm standard, 0.1mm lento, 0.3mm veloce

def tempo_stampa_stimato(vol_mm3, altezza_mm, layer_h=0.2, velocita_cm3h=20):
    vol_cm3 = vol_mm3 / 1000
    n_layer = altezza_mm / layer_h
    tempo_h = vol_cm3 / velocita_cm3h
    # Aggiungi overhead per movimenti, riscaldamento, retrazioni
    tempo_h *= 1.3
    ore = int(tempo_h)
    minuti = int((tempo_h - ore) * 60)
    return ore, minuti
```

---

## 5. Validazioni Geometriche

### 5.1 Check Bounding Box

```python
bb = result.val().BoundingBox()

# Dimensioni ragionevoli per stampa FDM
assert bb.xlen > 0.1, "Asse X degenere (< 0.1mm)"
assert bb.ylen > 0.1, "Asse Y degenere (< 0.1mm)"
assert bb.zlen > 0.1, "Asse Z degenere (< 0.1mm)"
assert bb.xlen < 500, f"Asse X troppo grande ({bb.xlen:.0f}mm > 500mm)"
assert bb.ylen < 500, f"Asse Y troppo grande ({bb.ylen:.0f}mm > 500mm)"
assert bb.zlen < 500, f"Asse Z troppo grande ({bb.zlen:.0f}mm > 500mm)"
```

### 5.2 Check Volume

```python
vol = result.val().Volume()

assert vol > 0, "Volume = 0 (corpo vuoto o non solido)"
assert vol < 1e9, f"Volume irrealistico ({vol:.0f}mm³ = {vol/1e6:.0f}L)"

# Check proporzione (volume vs bounding box)
bb_vol = bb.xlen * bb.ylen * bb.zlen
fill_ratio = vol / bb_vol if bb_vol > 0 else 0
assert fill_ratio > 0.001, f"Fill ratio troppo basso ({fill_ratio:.4f}) — possibile shape degenere"
```

### 5.3 Check Printability

```python
# Spessori minimi per FDM
MIN_WALL = 0.8  # [mm] — sotto questo la stampante non riesce

# Altezza massima senza supporti
MAX_UNSUPPORTED = 300  # [mm]

# Warning (non errore) se troppo alto
if bb.zlen > MAX_UNSUPPORTED:
    print(f"⚠️ Altezza {bb.zlen:.0f}mm — potrebbe richiedere supporti o suddivisione")
```

---

## 6. Esempio Completo — Fix Loop in Azione

### Input: script con fillet troppo grande

```python
"""Box con fillet — intenzionalmente rotto"""
import cadquery as cq

width  = 40.0   # [mm]
depth  = 30.0   # [mm]
height = 5.0    # [mm] — molto sottile!
fillet = 4.0    # [mm] — TROPPO: > height/2

result = (
    cq.Workplane("XY")
    .box(width, depth, height)
    .edges("|Z")
    .fillet(fillet)
)
```

### Tentativo 1: ERRORE
```
StdFail_NotDone: fillet radius (4.0) > half minimum dimension (2.5)
```

### Fix applicato (catalogo #1):
```python
# fillet ridotto: min(4.0, 5.0/2 - 0.1) = 2.4
fillet = 2.4    # [mm] — ridotto da 4.0 (era > height/2)
```

### Tentativo 2: SUCCESSO
```
✅ Esecuzione Python: OK (tentativo 2/5)
✅ Shape BREP: Valido
✅ Bounding box: 40.0 × 30.0 × 5.0 mm
📊 Volume: 5,544 mm³ (5.5 cm³)
📁 Export: box.step + box.stl
```

---

## 7. Checklist Pre-Consegna

Prima di dichiarare il modello valido e consegnare all'utente:

- [ ] Script Python esegue senza errori
- [ ] Bounding box ha dimensioni > 0.1mm su tutti gli assi
- [ ] Bounding box ha dimensioni < 500mm su tutti gli assi
- [ ] Volume > 0 mm³
- [ ] Fill ratio > 0.001 (volume / bb_volume)
- [ ] File .step esportato e verificato esistente
- [ ] File .stl esportato e verificato esistente
- [ ] Nessun `try: except: pass` nel codice finale
- [ ] Tutti i parametri con commento `[mm]` o `[deg]`
- [ ] Nessun magic number nel codice
- [ ] Report post-validazione stampato
