# SKILL: print-profiles — Selezione Materiale, Vincoli di Stampa e Profili Stampante

## Identità
Consulente materiali e processo FDM. Seleziona il materiale ottimale per il caso d'uso,
applica vincoli geometrici al design CadQuery, stima peso e tempo, e verifica compatibilità stampante.

---

## 1. Selezione Materiale per Caso d'Uso

### 1.1 Matrice Decisionale

| Caso d'uso | Materiale primario | Alternativa | Motivo |
|---|---|---|---|
| Prototipo rapido, nessun carico | PLA | PLA-CF | Economico, facile, nessun requisito speciale |
| Pezzo meccanico indoor | PETG | PA12 | Buon compromesso resistenza/stampabilità |
| Pezzo meccanico outdoor | ASA | PETG | UV-resistente, resistenza termica >85°C |
| Alta temperatura (80-120°C) | PC | Tullomer | Resistenza termica eccellente |
| Alta temperatura + leggero | PC-CF | PA-CF | Massima rigidità e resistenza termica |
| Resistenza chimica (solventi, oli) | PA6 | PA-CF | Nylon eccelle in resistenza chimica |
| Parti flessibili, guarnizioni | TPU 85A | TPU 95A | Elastomero, assorbe vibrazioni |
| Clip a scatto, cerniere vive | PA12 | PETG | Fatica eccellente, non fragile |
| Food-safe | PLA | Tullomer | Certificati food contact |
| Ingranaggi, boccole | PA-CF | PA12 | Resistenza usura + rigidità |
| Staffature, jig, tooling | PA-CF | PC-CF | Massima resistenza meccanica |
| Enclosure elettronica outdoor | ASA | PC | UV + termica + chimici |
| Parti strutturali auto/moto | PC-CF | PA-CF | Rigidità, temperatura, impatto |
| Supporti solubili (con PLA/PETG) | PVA | — | Solubile in acqua |
| Supporti solubili (con ABS/ASA) | HIPS | — | Solubile in D-Limonene |

### 1.2 Albero Decisionale

```
CASO D'USO
│
├─ Temperatura esercizio > 80°C?
│   ├─ Sì → Serve leggerezza/rigidità?
│   │   ├─ Sì → PC-CF o PA-CF
│   │   └─ No → PC o Tullomer
│   └─ No → continua ▼
│
├─ Esposto a UV / outdoor?
│   ├─ Sì → ASA (o PETG se T < 70°C)
│   └─ No → continua ▼
│
├─ Serve flessibilità?
│   ├─ Sì → TPU 85A (morbido) o TPU 95A (semi-rigido)
│   └─ No → continua ▼
│
├─ Resistenza chimica critica?
│   ├─ Sì → PA6 o PA-CF
│   └─ No → continua ▼
│
├─ Carichi meccanici significativi?
│   ├─ Sì → PETG (indoor) o ASA (outdoor) o PA-CF (estremo)
│   └─ No → PLA (prototipo) o PETG (produzione)
│
└─ Food-safe richiesto?
    ├─ Sì → PLA o Tullomer
    └─ No → seleziona per temperatura/carico
```

### 1.3 Caricamento Database Materiali

```python
import json, os

MATERIALS_PATH = os.path.join(os.path.dirname(__file__), "materials.json")

def load_materials():
    with open(MATERIALS_PATH) as f:
        return json.load(f)

def get_material(name):
    """Ritorna le proprietà di un materiale specifico."""
    materials = load_materials()
    key = name.upper().replace(" ", "_").replace("-", "_")
    # Cerca match esatto o parziale
    if key in materials:
        return materials[key]
    for k, v in materials.items():
        if name.lower() in k.lower() or name.lower() in v.get("full_name", "").lower():
            return v
    return None
```

---

## 2. Applicazione Vincoli al Design CadQuery

### 2.1 Verifica Spessore Parete

Ogni materiale in `materials.json` ha un campo `wall_min_mm`. Prima di generare il codice CadQuery,
verificare che tutti gli spessori di parete siano >= wall_min_mm del materiale selezionato.

```
SE materiale.wall_min_mm > parete_design:
    AVVISO: "Parete {parete_design}mm troppo sottile per {materiale}.
             Minimo: {wall_min_mm}mm. Aumento automatico."
    parete_design = materiale.wall_min_mm
```

**Regole per materiale:**

| Materiale | wall_min_mm | Motivo |
|---|---|---|
| PLA | 1.0 | Fragile sotto 1mm |
| PETG | 1.2 | Stringing rende pareti sottili irregolari |
| ABS / ASA | 1.2 | Warping crea stress su pareti sottili |
| PC / Tullomer | 1.6 – 2.0 | Ritiro + stress interlayer richiedono pareti robuste |
| PA6 / PA12 | 1.2 | Ritiro elevato, pareti sottili si deformano |
| PA-CF / PC-CF | 1.4 – 1.8 | Fibre richiedono spessore per allinearsi |
| TPU 85A | 1.0 | Flessibile, tollera pareti sottili |
| TPU 95A | 1.2 | Semi-rigido |

### 2.2 Compensazione Ritiro (Shrinkage)

Per materiali ad alto ritiro (ABS, PA6, PC), suggerire compensazione dimensionale:

```python
def compensate_shrinkage(dimension_mm, material):
    """Compensa il ritiro del materiale scalando la dimensione."""
    shrink_avg = (material["shrinkage_pct"]["min"] + material["shrinkage_pct"]["max"]) / 2 / 100
    return dimension_mm * (1 + shrink_avg)
```

**Quando applicare la compensazione:**

| Situazione | Azione |
|---|---|
| Tolleranze strette (press-fit, incastri) | SEMPRE compensare |
| Dimensioni generiche (enclosure, bracket) | NON compensare (slicer compensa) |
| Fori per viti | Compensare SOLO se diametro critico |
| Accoppiamento con parti metalliche | SEMPRE compensare |

**Tabella ritiro medio:**

| Materiale | Ritiro medio | Compensazione su 100mm |
|---|---|---|
| PLA | 0.4% | +0.4mm |
| PETG | 0.45% | +0.45mm |
| ABS | 0.65% | +0.65mm |
| ASA | 0.55% | +0.55mm |
| PA6 | 1.1% | +1.1mm |
| PA12 | 0.75% | +0.75mm |
| PC | 0.65% | +0.65mm |
| Tullomer | 0.6% | +0.6mm |

### 2.3 Camera Chiusa — Avvisi

```
SE materiale.chamber_required == true:
    AVVISO: "{materiale} richiede camera chiusa (enclosed chamber).
             Stampanti compatibili: Bambu X1C, Voron 2.4, Prusa XL (opzionale).
             Stampanti NON compatibili: Bambu A1, Ender 3, Prusa MK4 (senza enclosure)."
```

### 2.4 Asciugatura — Avvisi

```
SE materiale.drying_required == true:
    INFO: "{materiale} richiede asciugatura prima della stampa.
           Temperatura: {drying_temp_hours.temp_c}°C per {drying_temp_hours.hours}h.
           Usare drybox durante la stampa per materiali igroscopici (PA, PVA)."
```

### 2.5 Ugello Hardened Steel — Avvisi

```
SE materiale contiene "CF" nel nome:
    AVVISO: "{materiale} contiene fibre abrasive.
             Ugello in acciaio temprato (hardened steel) OBBLIGATORIO.
             Un ugello in ottone si consuma in poche ore."
```

---

## 3. Formule di Stima

### 3.1 Peso Stimato

```python
def peso_stimato(vol_mm3, materiale="PLA", infill_pct=20):
    """
    Stima il peso del pezzo stampato.

    Formula: peso = volume_cm3 × densità × fattore_infill
    fattore_infill = shell_fraction + (1 - shell_fraction) × (infill_pct / 100)

    Approssimazione: shell_fraction = 0.3 (media per pezzi tipici FDM)
    Per pezzi piccoli (<30mm): shell_fraction ≈ 0.6-0.8
    Per pezzi grandi (>100mm): shell_fraction ≈ 0.15-0.25
    """
    materials = load_materials()
    mat = materials.get(materiale, materials.get("PLA"))
    densita = mat["density_g_cm3"]

    vol_cm3 = vol_mm3 / 1000.0
    fattore = 0.3 + 0.7 * (infill_pct / 100.0)
    peso_g = vol_cm3 * densita * fattore

    return round(peso_g, 1)
```

### 3.2 Tempo di Stampa Stimato

```python
def tempo_stampa_stimato(vol_mm3, altezza_mm, layer_h=0.2, nozzle_d=0.4,
                          speed_mm_s=60, overhead=1.3):
    """
    Stima il tempo di stampa.

    Formula base: tempo_h = (volume_mm3 / (layer_h × nozzle_d × speed_mm_s)) / 3600
    Corretto con fattore overhead (movimenti, retrazioni, riscaldamento).

    Parametri default: layer 0.2mm, ugello 0.4mm, velocità 60mm/s, overhead 30%.
    """
    # Volume rate effettivo [mm³/s]
    flow_rate = layer_h * nozzle_d * speed_mm_s

    # Tempo base [s]
    tempo_s = vol_mm3 / flow_rate

    # Overhead: movimenti non-print, riscaldamento, retrazioni, layer change
    tempo_s *= overhead

    # Overhead aggiuntivo per altezza (più layer = più layer change e z-hop)
    n_layers = altezza_mm / layer_h
    tempo_s += n_layers * 1.5  # ~1.5s per layer change

    tempo_h = tempo_s / 3600.0
    ore = int(tempo_h)
    minuti = int((tempo_h - ore) * 60)

    return ore, minuti
```

### 3.3 Costo Filamento Stimato

```python
# Prezzi medi filamento [EUR/kg] — aggiornamento 2026
PREZZI_FILAMENTO = {
    "PLA":      20,   "PLA-CF":   35,
    "PETG":     22,   "PETG-CF":  38,
    "ABS":      20,   "ASA":      25,
    "PC":       35,   "PC-CF":    55,
    "PA6":      40,   "PA12":     35,
    "PA-CF":    60,   "TPU_85A":  35,
    "TPU_95A":  30,   "Tullomer": 45,
    "PVA":      40,   "HIPS":     22,
}

def costo_stimato(peso_g, materiale="PLA"):
    prezzo_kg = PREZZI_FILAMENTO.get(materiale, 25)
    return round(peso_g * prezzo_kg / 1000, 2)
```

### 3.4 Report Completo

```
📊 STIMA STAMPA — {nome_pezzo}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📐 Volume:          {vol:,.0f} mm³ ({vol/1000:.1f} cm³)
⚖️  Peso stimato:    {peso:.1f}g ({materiale}, {infill}% infill)
⏱️  Tempo stimato:   ~{ore}h {min}min (layer {layer_h}mm, {speed}mm/s)
💰 Costo filamento: ~€{costo:.2f} ({materiale} @ €{prezzo}/kg)
🌡️  Ugello:          {temp_nozzle_min}-{temp_nozzle_max}°C
🛏️  Piatto:          {temp_bed_min}-{temp_bed_max}°C
📦 Camera chiusa:   {"RICHIESTA" if chamber else "Non necessaria"}
💧 Asciugatura:     {"RICHIESTA ({dry_t}°C × {dry_h}h)" if drying else "Non necessaria"}
```

---

## 4. Regole Speciali: Tullomer e Policarbonato

### 4.1 Regole Comuni PC e Tullomer

Sia PC che Tullomer sono materiali ingegneristici ad alta temperatura con requisiti speciali:

| Regola | Valore | Motivo |
|---|---|---|
| Parete minima | ≥ 2.0mm | Stress interlayer elevato, pareti sottili delaminano |
| Fillet interni | ≥ 1.0mm su TUTTI gli angoli | Concentrazione di stress provoca cricche |
| Camera chiusa | OBBLIGATORIA (>50°C) | Warping severo, delaminazione |
| Hotend | All-metal | Temperature >250°C, PTFE si degrada |
| Asciugatura | Critica | Bolle, stringing, delaminazione se umido |
| Velocità max | 40-60 mm/s | Adesione interlayer richiede tempo |
| Ventola pezzo | 0-30% | Raffreddamento rapido causa warping e delaminazione |

### 4.2 Orientamento Fibre vs Carichi (materiali -CF)

Per materiali rinforzati con fibre (PLA-CF, PETG-CF, PC-CF, PA-CF):

```
REGOLA: Le fibre corte si allineano nella DIREZIONE DI STAMPA (asse X/Y del layer).

La resistenza meccanica è ANISOTROPA:
  - Direzione XY (nel piano del layer): 100% della resistenza nominale
  - Direzione Z (tra layer): 30-50% della resistenza nominale

CONSEGUENZA SUL DESIGN:
  ✅ Carichi di trazione/compressione nel piano XY → forte
  ❌ Carichi di trazione lungo Z (tra layer) → debole
  ✅ Flessione con asse neutro nel piano XY → forte
  ❌ Flessione con asse neutro lungo Z → debole
```

**Regole di orientamento:**

| Tipo di carico | Orientamento stampa consigliato |
|---|---|
| Trazione lungo l'asse più lungo | Stampare con asse lungo in X o Y |
| Flessione (trave) | Layer perpendicolari all'asse neutro |
| Compressione assiale | Z-up (layer perpend. al carico) |
| Torsione | Layer paralleli all'asse di torsione |
| Carico multi-asse | Privilegiare la direzione del carico principale |

### 4.3 Creep a 80°C — Verifica Tullomer e PC

```
SE materiale IN (Tullomer, PC) E temperatura_esercizio > 60°C E carico_sostenuto:
    AVVISO: "A {temp}°C con carico sostenuto, verificare il creep.
             Ridurre lo stress ammissibile del 40-60% rispetto ai dati a 23°C.
             Considerare:
             - Aumentare sezione resistente (+50%)
             - Ridurre temperatura di esercizio se possibile
             - Usare PC-CF o PA-CF per migliore resistenza al creep"
```

**Fattori di riduzione per creep:**

| Temperatura | Fattore su tensile strength |
|---|---|
| 23°C (ambiente) | 1.0 (valore nominale) |
| 50°C | 0.8 |
| 60°C | 0.65 |
| 80°C | 0.45 |
| 100°C | 0.30 |
| 120°C (solo PC) | 0.20 |

### 4.4 Checklist CadQuery per PC/Tullomer

Prima di generare codice CadQuery per pezzi in PC o Tullomer, verificare:

- [ ] `wall >= 2.0` mm in tutto il modello
- [ ] Fillet ≥ 1.0mm su TUTTI gli angoli interni (`.fillet(1.0)`)
- [ ] Nessun angolo vivo interno (stress concentrator)
- [ ] Spessori uniformi dove possibile (evitare transizioni brusche)
- [ ] Fori con svasatura o raccordo d'ingresso
- [ ] Nervature con draft angle ≥ 1° se possibile
- [ ] Orientamento di stampa scelto per massimizzare adesione interlayer nella direzione del carico
- [ ] Brim ≥ 8mm nel profilo slicer

---

## 5. Profili Stampante

### 5.1 Database Stampanti

| Stampante | Volume (mm) | Velocità max | Camera | Multi-mat | Ugello | Note |
|---|---|---|---|---|---|---|
| **Bambu X1C** | 256×256×256 | 500 mm/s | Chiusa (riscaldata) | AMS 4 slot | 0.4 default | Top gamma. ABS/PC/PA senza problemi. |
| **Bambu P1S** | 256×256×256 | 500 mm/s | Chiusa (non riscaldata) | AMS 4 slot | 0.4 default | Come X1C ma camera non riscaldata attivamente. OK per ABS/ASA. |
| **Bambu A1** | 256×256×256 | 500 mm/s | Aperta | AMS lite 4 slot | 0.4 default | Solo PLA/PETG/TPU. NO ABS/PC/PA (no camera). |
| **Bambu A1 Mini** | 180×180×180 | 500 mm/s | Aperta | AMS lite 4 slot | 0.4 default | Volume ridotto. Solo PLA/PETG/TPU. |
| **Prusa MK4S** | 250×210×220 | 200 mm/s | Aperta (enclosure opz.) | MMU3 5 slot | 0.4 default | Affidabile. Con enclosure DIY: ABS possibile. |
| **Prusa XL** | 360×360×360 | 200 mm/s | Aperta (enclosure opz.) | 5 toolhead | 0.4 default | Volume enorme. Multi-tool vero. Enclosure opzionale per ABS. |
| **Creality Ender 3 V3** | 220×220×250 | 300 mm/s | Aperta | No | 0.4 default | Entry-level. Solo PLA/PETG. |
| **Creality K1** | 220×220×250 | 600 mm/s | Chiusa | No | 0.4 default | Veloce. Camera chiusa per ABS/ASA. |
| **Voron 2.4** | 350×350×340 | 500 mm/s | Chiusa (riscaldata) | No (opz.) | 0.4 default | DIY CoreXY. Camera chiusa riscaldata fino a 60°C. Ideale per PC/PA/CF. |

### 5.2 Compatibilità Materiale-Stampante

```
PER OGNI materiale selezionato:
    SE materiale.chamber_required:
        stampanti_ok = [X1C, P1S, K1, Voron 2.4]
        stampanti_con_mod = [Prusa MK4S+enclosure, Prusa XL+enclosure]
        stampanti_no = [Bambu A1, A1 Mini, Ender 3]
    ALTRIMENTI:
        stampanti_ok = tutte
```

**Matrice di compatibilità rapida:**

| Materiale | X1C | P1S | A1 | MK4S | XL | Ender 3 | K1 | Voron |
|---|---|---|---|---|---|---|---|---|
| PLA | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| PLA-CF | ✅¹ | ✅¹ | ✅¹ | ✅¹ | ✅¹ | ✅¹ | ✅¹ | ✅¹ |
| PETG | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| ABS | ✅ | ✅ | ❌ | ⚠️² | ⚠️² | ❌ | ✅ | ✅ |
| ASA | ✅ | ✅ | ❌ | ⚠️² | ⚠️² | ❌ | ✅ | ✅ |
| PC | ✅ | ⚠️³ | ❌ | ❌ | ⚠️² | ❌ | ⚠️³ | ✅ |
| PC-CF | ✅¹ | ⚠️¹³ | ❌ | ❌ | ⚠️¹² | ❌ | ⚠️¹³ | ✅¹ |
| PA6 | ✅ | ⚠️³ | ❌ | ❌ | ⚠️² | ❌ | ⚠️³ | ✅ |
| PA-CF | ✅¹ | ⚠️¹³ | ❌ | ❌ | ⚠️¹² | ❌ | ⚠️¹³ | ✅¹ |
| TPU 85A | ✅⁴ | ✅⁴ | ✅⁴ | ✅⁴ | ✅⁴ | ⚠️⁵ | ✅⁴ | ✅⁴ |
| TPU 95A | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️⁵ | ✅ | ✅ |
| Tullomer | ✅ | ⚠️³ | ❌ | ❌ | ⚠️² | ❌ | ⚠️³ | ✅ |

**Note:**
1. ¹ Ugello hardened steel obbligatorio
2. ² Richiede enclosure aftermarket/DIY
3. ³ Camera non riscaldata attivamente — possibile con precauzioni, rischio warping
4. ⁴ Velocità ridotta (20-30 mm/s per 85A, 30-40 mm/s per 95A)
5. ⁵ Ender 3 è bowden — TPU 85A molto difficile, 95A possibile lentamente

### 5.3 Verifica Volume di Stampa

```
SE pezzo.bounding_box > stampante.volume:
    ERRORE: "Il pezzo ({bb.x}×{bb.y}×{bb.z}mm) non entra nel volume
             di stampa della {stampante.nome} ({vol.x}×{vol.y}×{vol.z}mm).
             Opzioni:
             1. Scegliere stampante più grande (es. Prusa XL: 360×360×360)
             2. Suddividere il pezzo con tagli e incastri
             3. Ruotare il pezzo (se una dimensione è dominante)"
```

### 5.4 Profili Slicer Raccomandati

| Scenario | Layer | Velocità | Infill | Perimetri | Note |
|---|---|---|---|---|---|
| Prototipo veloce | 0.28mm | 150 mm/s | 10% | 2 | Solo PLA |
| Standard | 0.20mm | 80 mm/s | 20% | 3 | Default per la maggior parte |
| Meccanico | 0.16mm | 60 mm/s | 40% | 4 | Pezzi sotto carico |
| Precisione | 0.12mm | 40 mm/s | 30% | 3 | Tolleranze strette |
| Strutturale | 0.16mm | 40 mm/s | 60% | 5 | Massima resistenza |
| Flessibile (TPU) | 0.20mm | 25 mm/s | 20% | 3 | Retrazione 0-1mm |
| PC / Tullomer | 0.20mm | 40 mm/s | 30% | 4 | Ventola 0-20%, camera chiusa |

---

## 6. Integrazione con Pipeline CadQuery

### 6.1 Flusso di Lavoro

```
1. Utente specifica caso d'uso + condizioni operative
2. print-profiles seleziona materiale (Sezione 1)
3. print-profiles applica vincoli al design (Sezione 2):
   - wall_min_mm → verifica/aggiorna parametri CadQuery
   - shrinkage_pct → compensazione su dimensioni critiche
   - chamber_required → avviso compatibilità stampante
   - fillet obbligatori per PC/Tullomer
4. cadquery-codegen genera il codice con vincoli applicati
5. cadquery-validate esegue e verifica
6. print-profiles genera report (Sezione 3):
   - Peso stimato
   - Tempo stimato
   - Costo filamento
   - Note stampa specifiche
```

### 6.2 Esempio di Applicazione Vincoli

```python
# Input utente: enclosure per outdoor, temp 60°C
# Selezione: ASA (outdoor + UV + 90°C service)

# Vincoli applicati automaticamente:
materiale = "ASA"
wall = max(user_wall, 1.2)        # wall_min_mm ASA = 1.2
# Compensazione ritiro su dimensioni critiche:
# pcb_clearance += compensate_shrinkage(pcb_clearance, 0.55%)
# Avviso camera chiusa: ASA richiede camera chiusa

# Nel report finale:
# ⚠️ CAMERA CHIUSA RICHIESTA — stampanti compatibili: X1C, P1S, K1, Voron
# ⚠️ ASCIUGATURA: 65°C × 4h prima della stampa
# 📊 Peso stimato: 45.2g (ASA, 20% infill)
# ⏱️ Tempo stimato: ~3h 15min
```

---

## 7. Checklist Pre-Stampa

Prima di dichiarare il modello pronto per la stampa:

- [ ] Materiale selezionato e giustificato per il caso d'uso
- [ ] `wall >= materiale.wall_min_mm` verificato su tutto il modello
- [ ] Fillet ≥ 1mm su angoli interni (se PC/Tullomer)
- [ ] Compensazione ritiro applicata su dimensioni critiche
- [ ] Volume di stampa verificato per la stampante target
- [ ] Compatibilità stampante-materiale verificata (Sezione 5.2)
- [ ] Asciugatura segnalata se necessaria
- [ ] Camera chiusa segnalata se necessaria
- [ ] Ugello hardened steel segnalato se materiale -CF
- [ ] Report peso/tempo/costo generato
- [ ] Profilo slicer raccomandato indicato
