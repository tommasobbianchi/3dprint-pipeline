# Prompt di Implementazione per Claude CLI

> Copia e incolla questo prompt in Claude CLI per avviare la costruzione della pipeline.
> Eseguilo dalla root del progetto (es. `~/projects/3dprint-pipeline/`)

---

## PROMPT 1: Setup Progetto + MCP Server

```
Leggi il file CLAUDE.md in questa directory e il piano in openscad-pipeline-plan.md.

Il tuo compito è implementare la pipeline AI→3D Print. Inizia con:

1. SETUP PROGETTO
   - Crea la struttura directory completa come da piano
   - Verifica che OpenSCAD sia installato (`openscad --version`), se no installalo
   - Verifica Node.js e npm disponibili

2. MCP SERVER `openscad-mcp`
   Crea un MCP server in TypeScript che espone questi tools:
   
   - `openscad_render`: Riceve codice OpenSCAD come stringa, lo salva in un file temp,
     esegue `openscad -o output.stl input.scad 2>&1`, ritorna:
     { success: bool, stdout: string, stderr: string, stl_path: string|null, 
       bounding_box: {x,y,z}|null }
   
   - `openscad_preview`: Come render ma genera PNG con:
     `openscad --camera=0,0,0,55,0,25,200 --imgsize=800,600 -o preview.png input.scad`
     Ritorna { success: bool, image_path: string }
   
   - `openscad_validate`: Compila e verifica che l'STL sia manifold.
     Usa `openscad -o output.stl input.scad 2>&1` e controlla stderr per
     "WARNING" o "ERROR". Ritorna { valid: bool, warnings: string[], errors: string[] }
   
   - `openscad_export`: Come render ma con formato specificabile (stl, 3mf, amf).
     Ritorna il path del file esportato.
   
   Usa il SDK MCP ufficiale (@modelcontextprotocol/sdk).
   Il server deve gestire file temporanei in /tmp/openscad-mcp/ con cleanup automatico.
   Testa ogni tool con un cubo semplice `cube([10,10,10]);` per verificare che funzioni.
   
   Genera anche la configurazione per ~/.claude/mcp_servers.json.

Procedi step by step. Per ogni componente creato, testalo prima di andare avanti.
```

---

## PROMPT 2: Skill 1 — Spatial Reasoning

```
Ora implementa la Skill 1: spatial-reasoning.

Crea il file skills/spatial-reasoning/SKILL.md con queste sezioni:

1. IDENTITÀ: Definisci Claude come ingegnere meccanico esperto in CSG e ragionamento spaziale 3D.

2. PROTOCOLLO DI RAGIONAMENTO OBBLIGATORIO:
   Prima di qualsiasi codice OpenSCAD, Claude DEVE completare un blocco di ragionamento
   strutturato con:
   
   a) DECOMPOSIZIONE FUNZIONALE
      - Obiettivo del pezzo
      - Vincoli (meccanici, termici, di assemblaggio)  
      - Lista componenti con forma base e dimensioni approssimative
   
   b) PIANO CSG ESPLICITO
      - Sequenza ordinata di operazioni booleane
      - Coordinate esplicite per ogni translate/rotate
      - Indicazione di cosa ogni operazione "fa" nel mondo reale
   
   c) SISTEMA COORDINATE
      - Posizione origine e perché
      - Orientamento per stampa (quale faccia su build plate)
      - Identificazione assi principali
   
   d) VERIFICA DIMENSIONALE
      - Cross-check ogni dimensione critica
      - Verifica che i fori siano passanti (h > spessore + epsilon)
      - Verifica che le pareti abbiano lo spessore minimo
      - Verifica clearance tra parti adiacenti

3. REGOLE DI RAGIONAMENTO:
   - "Pensa in negativo": per ogni feature sotttrattiva, visualizza il volume rimosso
   - "Pensa in sezione": immagina di tagliare il pezzo con un piano e descrivi cosa vedi
   - "Pensa in stampa": immagina il pezzo layer by layer dal basso verso l'alto
   - "Pensa in assemblaggio": se ci sono più parti, descrivi come si montano

4. CATALOGO PRIMITIVI con cheat-sheet OpenSCAD e quando usare ciascuno.

5. ESEMPI: Includi 3 esempi completi di ragionamento spaziale per:
   - Una staffa a L con fori
   - Un enclosure con snap-fit
   - Un adattatore cilindrico concentrico

Testa la skill creando un prompt di esempio e verifica che il ragionamento prodotto sia
coerente e che porti a codice OpenSCAD corretto.
```

---

## PROMPT 3: Skill 2 — OpenSCAD CodeGen

```
Implementa la Skill 2: openscad-codegen.

Crea skills/openscad-codegen/SKILL.md che definisce le regole per generare codice
OpenSCAD di alta qualità. Deve includere:

1. TEMPLATE OBBLIGATORIO per ogni file .scad (come in CLAUDE.md ma più dettagliato):
   - Header con metadata
   - Sezione parametri principali (con tipo, range, commento [mm])
   - Sezione parametri di stampa
   - Sezione parametri derivati (calcolati, con commento formula)
   - Moduli separati per ogni componente logico
   - Modulo assembly() che compone tutto
   - Chiamata render finale

2. REGOLE DI CODICE:
   - Ogni variabile: nome_descrittivo_snake_case
   - Ogni dimensione: commento con unità [mm] o [deg]
   - Ogni modulo: commento che spiega cosa rappresenta fisicamente
   - Usa for() per ripetizioni, MAI copia-incolla
   - Offset boolean di 0.01mm per evitare z-fighting
   - Parametri $fn: 32 per preview, 64 per produzione, 128 per filetti/ingranaggi
   
3. LIBRERIA PATTERN: Crea file template separati in templates/:
   - templates/parametric_box.scad — Scatola con coperchio, snap-fit opzionale
   - templates/bracket_l.scad — Staffa a L con nervature e fori
   - templates/enclosure.scad — Enclosure per PCB con aperture
   - templates/snap_fit.scad — Modulo snap-fit cantilever
   - templates/threaded_insert.scad — Foro per inserto a caldo M2/M3/M4/M5
   - templates/hinge.scad — Cerniera print-in-place
   
   Ogni template deve essere 100% parametrico e funzionare standalone.

4. TABELLA TOLLERANZE completa per ogni tipo di accoppiamento.

5. ANTI-PATTERN con spiegazione di perché falliscono e cosa fare invece.

Implementa tutti i template files e verifica che ciascuno compili senza errori
con `openscad -o /dev/null template.scad 2>&1`.
```

---

## PROMPT 4: Skill 3 — Validate & Fix Loop

```
Implementa la Skill 3: openscad-validate.

Questa skill definisce il loop automatico di validazione e correzione.
Crea skills/openscad-validate/SKILL.md con:

1. WORKFLOW DI VALIDAZIONE:
   
   ```
   genera_codice()
   for i in 1..5:
       result = compila(codice)
       if result.success:
           if result.warnings:
               codice = fix_warnings(codice, result.warnings)
           else:
               return SUCCESS(codice, result.stl)
       else:
           codice = fix_errors(codice, result.errors)
   return FAILURE("Max iterazioni raggiunte", ultimo_errore)
   ```

2. CATALOGO ERRORI COMUNI con fix automatici:
   
   | Errore OpenSCAD | Causa | Fix |
   |---|---|---|
   | "No top-level geometry" | Manca render() o assembly() | Aggiungi chiamata |
   | "Object may not be a valid 2-manifold" | Mesh non chiusa | Aggiungi offset 0.01 |
   | "undefined variable" | Variabile mancante | Cerca nel contesto, definisci |
   | "WARNING: ... undefined operation" | Operazione non supportata | Sostituisci con equivalente |
   | "minkowski: child 0 is empty" | Geometria vuota in minkowski | Verifica dimensioni child |
   | Bounding box assurdo (>1000mm o <0.1mm) | Errore di scala/unità | Ricalcola dimensioni |
   
3. POST-VALIDAZIONE CHECKS:
   - Bounding box ragionevole (alert se >300mm su qualsiasi asse)
   - Volume > 0 (non è un oggetto vuoto)
   - Stima peso e tempo stampa
   - Verifica orientamento per stampa (suggerisci rotazione se necessario)

4. OUTPUT FORMAT:
   ```
   ✅ Compilazione: OK
   ✅ Manifold: OK  
   ✅ Bounding box: 45 x 30 x 25 mm
   📊 Volume: 12.3 cm³
   ⚖️ Peso stimato: 15.1g (PLA, 20% infill)
   ⏱️ Tempo stampa stimato: ~1h 20min (0.2mm layer, 50mm/s)
   📐 Orientamento consigliato: base piatta su build plate
   ```

Se il server MCP openscad è disponibile, usalo. Se no, definisci i comandi bash 
equivalenti come fallback.
```

---

## PROMPT 5: Skill 4 — Image to 3D

```
Implementa la Skill 4: image-to-3d.

Crea skills/image-to-3d/SKILL.md che definisce come analizzare immagini (foto, sketch,
disegni tecnici) per estrarre geometria e produrre codice OpenSCAD.

1. WORKFLOW ANALISI IMMAGINE:
   
   a) CLASSIFICAZIONE INPUT:
      - Sketch a mano libera → estrai forme approssimative, chiedi dimensioni
      - Foto di oggetto reale → reverse-engineering, stima dimensioni da riferimenti
      - Disegno tecnico → estrai quote, viste, sezioni
      - Screenshot CAD → identifica features e parametri
   
   b) ESTRAZIONE GEOMETRICA:
      - Identifica forme primitive (box, cilindri, sfere, coni)
      - Identifica operazioni booleane (fori, tasche, raccordi)
      - Identifica simmetrie (specchiatura, pattern circolari/lineari)
      - Stima rapporti dimensionali tra features
   
   c) STIMA DIMENSIONI:
      - Se presenti oggetti di riferimento (moneta, mano, PCB noto) → calcola scala
      - Se dimensioni note parzialmente → deduci il resto dai rapporti
      - Se nessun riferimento → chiedi all'utente le dimensioni critiche
   
   d) OUTPUT STRUTTURATO:
      Genera un blocco di specifiche strutturate che alimenta il ragionamento spaziale:
      ```
      OGGETTO: [nome/descrizione]
      DIMENSIONI STIMATE: [W x D x H mm]
      FORMA BASE: [primitiva principale]
      FEATURES:
        1. [tipo] at [posizione relativa] — [dimensioni]
        2. ...
      SIMMETRIE: [assi di simmetria]
      NOTE: [particolarità, sottosquadri, parti mobili]
      ```

2. PROMPT DI ANALISI (template da usare con l'immagine):
   
   "Analizza questa immagine per generare un modello 3D stampabile:
   
   1. Che tipo di oggetto è? Qual è la sua funzione?
   2. Quali forme geometriche primitive compongono l'oggetto?
   3. Quali sono le dimensioni approssimative? (usa riferimenti visibili)
   4. Quali features funzionali ci sono? (fori, slot, clip, raccordi)
   5. Ci sono simmetrie sfruttabili?
   6. Come si orienta per la stampa FDM?
   7. Ci sono parti che richiedono supporti?"

3. GESTIONE MULTI-VISTA:
   Se l'utente fornisce più foto/viste dello stesso oggetto, combina le informazioni
   per costruire un modello 3D più accurato. Mappa le features tra le viste.

4. LIMITAZIONI ESPLICITE:
   - Forme organiche complesse (sculture, volti) → NON gestibile con OpenSCAD
   - Superfici NURBS → Suggerisci Fusion360/FreeCAD
   - Texture/pattern superficiali complessi → Suggerisci approccio bitmap2surface
```

---

## PROMPT 6: Skill 5 — Print Profiles & Materials

```
Implementa la Skill 5: print-profiles.

Crea skills/print-profiles/SKILL.md e skills/print-profiles/materials.json.

1. materials.json — Database strutturato:

{
  "PLA": {
    "temp_max_service": 50,
    "temp_nozzle": [190, 220],
    "temp_bed": [50, 60],
    "wall_min_mm": 1.2,
    "shrinkage_pct": [0.3, 0.5],
    "density_g_cm3": 1.24,
    "tensile_strength_mpa": 50,
    "impact_resistance": "low",
    "chemical_resistance": "low",
    "uv_resistance": "low",
    "food_safe": false,
    "chamber_required": false,
    "notes": "Facile da stampare, buon dettaglio, fragile"
  },
  // PETG, ABS, ASA, PC, Nylon (PA6, PA12), TPU (85A, 95A),
  // PLA-CF, PETG-CF, PA-CF, Tullomer, PC+CF
  // ... (completa tutti)
}

2. SKILL.md deve:
   - Dato un materiale e un utilizzo, applicare automaticamente i vincoli corretti
   - Suggerire il materiale migliore dato un caso d'uso
   - Calcolare peso stimato: volume * density * infill_factor
   - Calcolare tempo stampa stimato basato su volume e velocità
   - Includere regole specifiche per compositi (Tullomer + PC wrapping):
     * Orientamento fibre rispetto ai carichi
     * Temperature di esercizio e deformazione
     * Adesione inter-layer critica
   - Profili stampante per:
     * Bambu Lab X1C / P1S / A1
     * Prusa MK4 / XL
     * Creality Ender 3 / K1
     * Voron 2.4 / Trident
     Con volumi di stampa, velocità max, features speciali

3. COMANDI MATERIALE:
   `/material PLA` → mostra scheda + applica vincoli
   `/material compare PLA PETG` → tabella comparativa
   `/material suggest outdoor load-bearing` → raccomanda materiale
```

---

## PROMPT 7: Skill 6 — Orchestrator + Test Finale

```
Implementa la Skill 6: 3d-print-orchestrator.

Questa è la skill master che orchestra tutte le altre. 
Crea skills/3d-print-orchestrator/SKILL.md che:

1. DEFINISCE IL WORKFLOW COMPLETO:
   
   Input utente (testo e/o immagine)
   │
   ├─ [Se immagine presente]
   │  └→ Leggi skills/image-to-3d/SKILL.md → Analisi immagine
   │     Output: specifica strutturata dell'oggetto
   │
   ├→ Leggi skills/spatial-reasoning/SKILL.md → Ragionamento spaziale
   │  Output: piano CSG dettagliato
   │
   ├→ Leggi skills/print-profiles/SKILL.md → Selezione materiale + vincoli
   │  Output: vincoli dimensionali e di design applicati
   │
   ├→ Leggi skills/openscad-codegen/SKILL.md → Generazione codice
   │  Output: file .scad parametrico completo
   │
   ├→ Leggi skills/openscad-validate/SKILL.md → Validazione + fix loop
   │  │  (usa MCP openscad se disponibile, altrimenti bash)
   │  Output: .scad validato + .stl
   │
   └→ Report finale con:
      - File .scad (parametrico, commentato)
      - File .stl (pronto per slicer)
      - Bounding box, volume, peso stimato
      - Istruzioni per slicer (orientamento, supporti, infill)
      - Note su limitazioni e possibili miglioramenti

2. GESTIONE COMANDI RAPIDI (/box, /bracket, /enclosure, ecc.)
   Ogni comando bypassa l'analisi e va diretto alla generazione con parametri predefiniti.

3. MODALITÀ INTERATTIVA:
   Se le informazioni sono insufficienti, chiedi in modo strutturato:
   "Per completare il design, ho bisogno di:
    □ Dimensioni esterne o interne? [mm]
    □ Materiale? [PLA/PETG/PC/...]  
    □ Quale faccia è la più importante esteticamente?
    □ Ci sono accoppiamenti con altre parti? Se sì, quali dimensioni?"

4. TEST FINALE:
   Dopo aver creato tutto, testa la pipeline completa con questo caso:
   
   "Crea un enclosure per Arduino Uno Rev3 con:
   - Aperture per USB-B e DC jack
   - Fori per montaggio M3 (4 angoli, compatibili con i fori del PCB)
   - Griglia di ventilazione sul top
   - Snap-fit per chiusura senza viti
   - Materiale: PETG
   - Spazio per un piccolo breadboard accanto all'Arduino"
   
   Verifica che il codice compili, che l'STL sia valido, e che le dimensioni
   siano corrette per un Arduino Uno reale (68.6 x 53.4 mm PCB).
   
   Se tutto funziona, la pipeline è completa.
```

---

## Note di Esecuzione

### Come usare questi prompt:

1. Crea il progetto: `mkdir -p ~/projects/3dprint-pipeline && cd $_`
2. Copia `CLAUDE-3dprint.md` come `CLAUDE.md` nella root
3. Copia `openscad-pipeline-plan.md` nella root
4. Apri Claude CLI: `claude`
5. Esegui i prompt in ordine (1→7)
6. Ogni prompt è autocontenuto e testabile indipendentemente
7. Il prompt 7 testa la pipeline end-to-end

### Tempo stimato:
- Prompt 1 (Setup + MCP): ~30-45 min
- Prompt 2-5 (Skills): ~15-20 min ciascuno
- Prompt 6 (Profiles + DB): ~20-30 min
- Prompt 7 (Orchestrator + Test): ~30-45 min
- **Totale: ~2.5-3.5 ore**

### Se qualcosa fallisce:
- Il MCP server è opzionale: il fallback bash funziona perfettamente
- Ogni skill è indipendente: puoi saltarne una e tornarci dopo
- I template .scad sono i più importanti: testali sempre prima
