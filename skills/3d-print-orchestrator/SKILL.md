# SKILL: 3d-print-orchestrator — Orchestratore Pipeline 3D Print

## Identità
Orchestratore centrale della pipeline 3D Print. Riceve richieste in linguaggio naturale
(testo e/o immagini), coordina tutte le skill specializzate e produce output pronto per la stampa.

---

## 1. Workflow Completo

```
INPUT (testo / immagine / combo)
│
├─ [se immagine allegata]
│   └─ skills/image-to-3d/SKILL.md
│      → Classificazione input (sketch/foto/disegno tecnico/screenshot/prodotto)
│      → Specifica strutturata (forme, dimensioni, features, materiale suggerito)
│
├─ [se materiale specificato o da selezionare]
│   └─ skills/print-profiles/SKILL.md
│      → Selezione materiale per caso d'uso
│      → Vincoli: wall_min, shrinkage, chamber, drying, nozzle
│      → Profilo stampante e compatibilità
│
├─ skills/spatial-reasoning/SKILL.md
│   → Fase 1: Decomposizione funzionale
│   → Fase 2: Piano di modellazione (primitivi, booleane, ordine)
│   → Fase 3: DFM check (spessori, overhang, supporti, orientamento)
│   → Fase 4: Coordinate e dimensioni finali
│
├─ skills/cadquery-codegen/SKILL.md
│   → Script Python parametrico (template obbligatorio)
│   → Tutte le dimensioni in variabili commentate [mm]
│   → Funzioni separate: make_body(), make_features(), make_assembly()
│   → Export STEP + STL
│
├─ skills/cadquery-validate/SKILL.md
│   → Esecuzione script Python
│   → Validazione BREP (bounding box, volume, fill ratio)
│   → Fix loop automatico (max 5 tentativi, catalogo 20 errori)
│   → Export finale .step + .stl
│
└─ OUTPUT
   → Script .py (parametrico, commentato, standalone)
   → File .step (importabile in Onshape/Fusion360/FreeCAD)
   → File .stl (per slicer: Bambu Studio, PrusaSlicer, OrcaSlicer)
   → Report completo (vedi §4)
```

### 1.1 Regole di Orchestrazione

1. **Ordine obbligatorio** — Le fasi vanno eseguite nell'ordine indicato. Non saltare fasi.
2. **Ragionamento PRIMA del codice** — Mai scrivere CadQuery senza aver completato spatial-reasoning.
3. **Un materiale alla volta** — Se l'utente non specifica, suggerisci il materiale e chiedi conferma.
4. **Vincoli materiale → codice** — I vincoli da print-profiles (wall_min, fillet) DEVONO essere applicati nel codice CadQuery.
5. **Validazione obbligatoria** — Mai consegnare codice non eseguito. Sempre passare per cadquery-validate.
6. **Fix automatico** — Se la validazione fallisce, il loop fix di cadquery-validate gestisce fino a 5 tentativi.
7. **Output completo** — Ogni consegna include .py + .step + .stl + report.

### 1.2 Gestione Errori tra Fasi

```
ERRORE in una fase
│
├─ image-to-3d fallisce (immagine illeggibile/ambigua)
│   → Chiedi all'utente: "Puoi descrivere a parole il pezzo?"
│   → Procedi con input testuale
│
├─ print-profiles: materiale non compatibile con stampante
│   → Mostra matrice compatibilità
│   → Suggerisci alternativa
│
├─ spatial-reasoning: geometria troppo complessa
│   → Scomponi in sotto-assembly
│   → Genera parti separate, poi assembla
│
├─ cadquery-codegen: pattern non coperto dai template
│   → Genera codice custom seguendo il template obbligatorio
│   → Riferisci ai 6 template come base
│
└─ cadquery-validate: 5 tentativi esauriti
    → Riporta tutti gli errori all'utente
    → Suggerisci semplificazione geometrica
    → Mai consegnare codice non funzionante
```

---

## 2. Comandi Rapidi

Scorciatoie per richieste frequenti. Ogni comando attiva il workflow completo
ma con parametri pre-impostati.

| Comando | Descrizione | Template base | Esempio |
|---|---|---|---|
| `/box WxDxH [materiale]` | Scatola parametrica con coperchio | `parametric_box.py` | `/box 80x60x40 PETG` |
| `/bracket [materiale]` | Staffa a L con gusset | `bracket_l.py` | `/bracket PC` |
| `/enclosure BOARD [materiale]` | Enclosure per PCB | `enclosure.py` | `/enclosure "Arduino Uno" PETG` |
| `/snap` | Modulo snap-fit dimostrativo | `snap_fit.py` | `/snap` |
| `/thread M[n]` | Foro per inserto a caldo | `threaded_insert.py` | `/thread M3` |
| `/hinge [materiale]` | Cerniera a pin | `hinge.py` | `/hinge PA12` |
| `/validate FILE` | Valida ed esporta script esistente | — | `/validate enclosure.py` |
| `/export FILE` | Export STEP+STL da script | — | `/export enclosure.py` |
| `/material MAT` | Mostra vincoli e proprietà materiale | — | `/material PETG` |
| `/sketch` | Analizza immagine allegata | — | `/sketch` (con immagine) |

### 2.1 Parsing Comandi

```
COMANDO RICEVUTO
│
├─ Inizia con "/"?
│   ├─ Match con comando noto → Esegui con parametri
│   └─ No match → "Comando non riconosciuto. Comandi disponibili: ..."
│
└─ Testo libero?
    ├─ Contiene immagine → Fase image-to-3d → workflow completo
    ├─ Contiene dimensioni esplicite → spatial-reasoning → workflow
    └─ Descrizione generica → Chiedi dettagli (§3 modalità interattiva)
```

---

## 3. Modalita Interattiva

Quando le informazioni sono insufficienti, chiedi in modo strutturato.

### 3.1 Informazioni Minime Richieste

| Informazione | Obbligatoria | Default se non fornita |
|---|---|---|
| Tipo di pezzo | SI | — (chiedi sempre) |
| Dimensioni principali | SI | — (chiedi sempre) |
| Materiale | NO | PLA |
| Spessore parete | NO | Da materiale (wall_min) |
| Fillet/raccordi | NO | 1.0 mm |
| Fori di montaggio | NO | Nessuno |
| Aperture | NO | Nessuna |
| Stampante | NO | Generica (250x250x250mm) |

### 3.2 Domande Strutturate

Quando mancano informazioni, chiedi con formato preciso:

```
Per procedere ho bisogno di:
1. **Dimensioni** — Larghezza × Profondità × Altezza in mm?
2. **Materiale** — Quale materiale? (PLA, PETG, ABS, ASA, PC, PA, TPU...)
3. **Fori montaggio** — Servono fori? Se sì: diametro, posizioni, tipo (passante/inserto)?
4. **Aperture** — Servono aperture sui lati? Se sì: dimensioni e posizione?
```

### 3.3 Regole di Interazione

1. **Chiedi tutto insieme** — Non fare una domanda alla volta. Raggruppa.
2. **Proponi default** — "Se non specificato, userò PLA con parete 2mm."
3. **Conferma dimensioni critiche** — Per enclosure di PCB, conferma sempre le posizioni fori.
4. **Non indovinare materiale per parti meccaniche** — Chiedi sempre per pezzi strutturali.

---

## 4. Output Standard

Ogni richiesta completata produce questo output.

### 4.1 File Generati

| File | Formato | Scopo |
|---|---|---|
| `{nome}.py` | Python | Script CadQuery parametrico, standalone, eseguibile |
| `{nome}.step` | STEP AP214 | Import in CAD (Onshape, Fusion360, FreeCAD, SolidWorks) |
| `{nome}.stl` | STL binario | Import in slicer (Bambu Studio, PrusaSlicer, OrcaSlicer) |
| `{nome}_report.txt` | Testo | Report completo (opzionale, stampato a console) |

Per assembly multi-parte:

| File | Scopo |
|---|---|
| `{nome}_body.step/.stl` | Corpo principale |
| `{nome}_lid.step/.stl` | Coperchio (se presente) |
| `{nome}_assembly.step` | Assembly completo (colori per parte) |

### 4.2 Report Completo

Dopo ogni consegna, stampa SEMPRE:

```
═══════════════════════════════════════════════
  REPORT — {NOME COMPONENTE}
═══════════════════════════════════════════════

✅ Esecuzione Python: OK (tentativo N/5)
✅ Shape BREP: Valido

📐 Geometria:
   Bounding box: {X:.1f} × {Y:.1f} × {Z:.1f} mm
   Volume:       {vol:,.0f} mm³ ({vol/1000:.1f} cm³)
   Area sup.:    {area:,.0f} mm²

⚖️ Stampa:
   Materiale:     {materiale}
   Peso stimato:  {peso:.1f}g (infill {infill}%)
   Tempo stimato: ~{ore}h {min}min
   Costo mat.:    ~€{costo:.2f}

🖨️ Stampante:
   Compatibile:   {lista stampanti compatibili}
   Volume stampa: {check ✅ o ⚠️}
   Camera chiusa: {richiesta/non richiesta}

📦 Orientamento stampa:
   Asse Z-up:     {descrizione orientamento}
   Supporti:      {necessari/non necessari}
   Note slicer:   {eventuali note}

📁 File esportati:
   {lista file .py + .step + .stl}

═══════════════════════════════════════════════
```

### 4.3 Calcoli per il Report

```python
import json, os

# Carica materiali
mat_path = os.path.join(os.path.dirname(__file__), "..", "print-profiles", "materials.json")
with open(mat_path) as f:
    MATERIALI = json.load(f)

def report(result, materiale="PLA", infill_pct=20, layer_h=0.2):
    """Genera report completo per un risultato CadQuery."""
    bb = result.val().BoundingBox()
    vol_mm3 = result.val().Volume()
    vol_cm3 = vol_mm3 / 1000

    mat = MATERIALI[materiale]
    densita = mat["density_g_cm3"]
    fattore = 0.3 + 0.7 * (infill_pct / 100)
    peso_g = vol_cm3 * densita * fattore

    # Tempo: approssimazione basata su volume
    velocita_cm3h = 20  # [cm³/h] media FDM
    tempo_h = (vol_cm3 / velocita_cm3h) * 1.3  # overhead 30%
    ore = int(tempo_h)
    minuti = int((tempo_h - ore) * 60)

    # Costo materiale (€/kg medio)
    PREZZI = {"PLA": 20, "PETG": 22, "ABS": 22, "ASA": 28,
              "PC": 35, "PA6": 40, "PA12": 45, "TPU_85A": 35,
              "TPU_95A": 30, "PLA-CF": 35, "PETG-CF": 38,
              "PC-CF": 55, "PA-CF": 60, "Tullomer": 50,
              "PVA": 45, "HIPS": 22}
    costo = peso_g / 1000 * PREZZI.get(materiale, 25)

    print(f"BB: {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm")
    print(f"Volume: {vol_mm3:,.0f} mm³ ({vol_cm3:.1f} cm³)")
    print(f"Peso: {peso_g:.1f}g ({materiale}, {infill_pct}% infill)")
    print(f"Tempo: ~{ore}h {minuti}min")
    print(f"Costo materiale: ~€{costo:.2f}")
```

---

## 5. Integrazione con Template CadQuery

I 6 template in `skills/cadquery-codegen/templates/` sono il punto di partenza per categorie note.

| Richiesta utente | Template | Personalizzazioni tipiche |
|---|---|---|
| Scatola, contenitore, box | `parametric_box.py` | Dimensioni, divisori interni, coperchio |
| Staffa, supporto, angolare | `bracket_l.py` | Dimensioni bracci, fori, gusset |
| Enclosure PCB, case elettronica | `enclosure.py` | Dimensioni PCB, standoff, aperture, ventilazione |
| Clip, gancio, chiusura a scatto | `snap_fit.py` | Dimensioni hook, deflessione, clearance |
| Foro filettato, inserto a caldo | `threaded_insert.py` | Taglia M2-M8, profondità, pattern |
| Cerniera, perno, articolazione | `hinge.py` | Larghezza, n. knuckle, diametro pin |

### 5.1 Quando NON usare un template

- Pezzo completamente custom → Genera da zero seguendo il template strutturale di CLAUDE.md
- Combinazione di pattern → Combina elementi da template diversi
- Assembly complesso → Scomponi in parti, ciascuna con il suo pattern

---

## 6. Fasi Dettagliate — Cosa Fare in Ogni Fase

### 6.1 Fase image-to-3d (solo se immagine allegata)

1. Classifica il tipo di input (A-E)
2. Estrai forme, dimensioni, features
3. Identifica materiale suggerito
4. Produci specifica strutturata
5. Se dimensioni mancanti → chiedi all'utente

### 6.2 Fase print-profiles

1. Carica `materials.json`
2. Seleziona materiale per caso d'uso (o usa quello richiesto)
3. Estrai vincoli: `wall_min_mm`, `shrinkage_pct`, `chamber_required`
4. Verifica compatibilità stampante (se specificata)
5. Prepara parametri per il codice CadQuery

### 6.3 Fase spatial-reasoning

1. **Decomposizione funzionale** — Elenca componenti e funzioni
2. **Piano di modellazione** — Primitivi, ordine operazioni booleane, ordine fillet
3. **DFM check** — Spessori ≥ wall_min, overhang < 45°, orientamento stampa
4. **Coordinate finali** — Tabella con tutte le dimensioni e posizioni

**Regola critica:** Il fillet sugli spigoli verticali esterni (`edges("|Z")`) va applicato
PRIMA delle operazioni booleane (cut per cavità, union per standoff). Vedi memory #55.

### 6.4 Fase cadquery-codegen

1. Scegli template base (se applicabile)
2. Personalizza parametri
3. Struttura: header → parametri → costruzione → export
4. Applica vincoli materiale (wall_min, fillet)
5. Genera script Python completo e standalone

### 6.5 Fase cadquery-validate

1. Esegui lo script Python
2. Verifica: no errori, BB valido, volume > 0
3. Se errore → applica fix dal catalogo (max 5 tentativi)
4. Export .step + .stl
5. Genera report

---

## 7. Esempi di Richieste e Routing

| Richiesta utente | Fasi attivate | Template |
|---|---|---|
| "Crea una scatola 80x60x40 in PLA" | profiles → spatial → codegen → validate | `parametric_box.py` |
| [immagine di un bracket] | image-to-3d → profiles → spatial → codegen → validate | `bracket_l.py` |
| "Enclosure per Raspberry Pi 4" | profiles → spatial → codegen → validate | `enclosure.py` |
| `/box 100x80x50 PETG` | profiles → spatial → codegen → validate | `parametric_box.py` |
| `/validate my_part.py` | validate (solo) | — |
| `/material ASA` | profiles (solo) | — |
| "Crea un pezzo che resista a 100°C" | profiles (selezione) → interattivo → spatial → codegen → validate | custom |

---

## 8. Checklist Pre-Consegna

Prima di consegnare all'utente, verifica TUTTI questi punti:

- [ ] Ragionamento spaziale completato (4 fasi documentate)
- [ ] Vincoli materiale applicati (wall_min, fillet, shrinkage)
- [ ] Script Python esegue senza errori
- [ ] Bounding box dimensioni > 0.1mm e < 500mm su tutti gli assi
- [ ] Volume > 0 mm³
- [ ] File .step esportato e verificato
- [ ] File .stl esportato e verificato
- [ ] Nessun `try: except: pass` nel codice
- [ ] Tutti i parametri con commento `[mm]` o `[deg]`
- [ ] Nessun magic number
- [ ] Report completo stampato
- [ ] Orientamento stampa indicato (Z-up)
