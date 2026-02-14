# 🏭 Pipeline AI → 3D Print: Piano di Sviluppo Skills per Claude CLI

## Obiettivo

Riprodurre e superare la pipeline di Gemini Deep Think per la generazione di codice OpenSCAD funzionale e stampabile in 3D, implementata come sistema di skills + MCP server per Claude Code CLI (Opus).

---

## Architettura del Sistema

```
┌─────────────────────────────────────────────────────────┐
│                    CLAUDE CODE CLI                        │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │ Skill 1  │  │ Skill 2  │  │ Skill 3  │  │ Skill 4 │ │
│  │ Spatial   │→ │ OpenSCAD │→ │ Validate │→ │ Export  │ │
│  │ Reasoning │  │ CodeGen  │  │ & Fix    │  │ & Slice │ │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘ │
│       ↑                                         │        │
│  ┌──────────┐                              ┌─────────┐  │
│  │ Skill 5  │                              │ MCP     │  │
│  │ Image    │                              │ Server  │  │
│  │ Analyze  │                              │OpenSCAD │  │
│  └──────────┘                              └─────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Piano di Sviluppo: 6 Skill + 1 MCP Server

### FASE 1 — Fondamenta (Skill 1-2)

#### Skill 1: `spatial-reasoning` — Ragionamento Spaziale Strutturato
**Scopo:** Forzare Claude a ragionare step-by-step sulla geometria 3D prima di scrivere codice.

**Contenuto chiave:**
- Template di "pensiero spaziale" con coordinate esplicite
- Decomposizione CSG (Constructive Solid Geometry) in passi atomici
- Checklist di validazione dimensionale pre-codice
- Catalogo di primitive e operazioni booleane OpenSCAD
- Regole per orientamento assi (Z-up per stampa 3D)

**Deliverable:** `skills/spatial-reasoning/SKILL.md`

---

#### Skill 2: `openscad-codegen` — Generazione Codice OpenSCAD
**Scopo:** Generare codice OpenSCAD parametrico, pulito e stampabile.

**Contenuto chiave:**
- Libreria di pattern OpenSCAD (fori, filetti, snap-fit, pareti, nervature)
- Regole di codice: variabili parametriche obbligatorie, no magic numbers
- Template strutturato: header parametri → moduli → assembly → render
- Vincoli di stampa FDM (spessore minimo parete, angoli overhang, bridging)
- Tolleranze standard per accoppiamenti (press-fit, slip-fit, clearance)
- Regole `$fn` per qualità curve vs tempo di render
- Anti-pattern da evitare (unrolled loops, mesh diretta, loft non supportato)

**Deliverable:** `skills/openscad-codegen/SKILL.md` + `skills/openscad-codegen/templates/`

---

### FASE 2 — Validazione (Skill 3 + MCP Server)

#### Skill 3: `openscad-validate` — Validazione e Correzione Iterativa
**Scopo:** Loop automatico di compilazione, analisi errori, e fix.

**Contenuto chiave:**
- Workflow: genera → compila → analizza stderr → correggi → ricompila
- Parsing errori OpenSCAD comuni e strategie di fix
- Validazione manifold (mesh chiusa, no self-intersection)
- Controllo dimensioni output (bounding box ragionevole)
- Max 5 iterazioni di fix automatico, poi escalation a utente

**Deliverable:** `skills/openscad-validate/SKILL.md`

---

#### MCP Server: `openscad-mcp` — Bridge OpenSCAD CLI
**Scopo:** Dare a Claude accesso diretto a OpenSCAD via MCP.

**Tools esposti:**
```
openscad.render     → Compila .scad → .stl + log errori
openscad.preview    → Genera preview PNG del modello
openscad.validate   → Check manifold + bounding box
openscad.export     → Export STL/3MF/AMF
openscad.version    → Info versione e capabilities
```

**Deliverable:** `mcp-openscad-server/` (Node.js o Python)

---

### FASE 3 — Input Avanzati (Skill 4-5)

#### Skill 4: `image-to-3d` — Da Immagine/Sketch a Modello
**Scopo:** Analizzare immagini (foto, sketch, disegni tecnici) ed estrarre geometria.

**Contenuto chiave:**
- Prompt di analisi immagine: identificare forme, dimensioni relative, simmetrie
- Workflow sketch → descrizione strutturata → OpenSCAD
- Stima dimensioni da oggetti di riferimento nell'immagine
- Gestione viste multiple (front, side, top)
- Template per reverse-engineering visuale

**Deliverable:** `skills/image-to-3d/SKILL.md`

---

#### Skill 5: `print-profiles` — Profili di Stampa e Materiali
**Scopo:** Adattare il design ai vincoli del materiale e della stampante.

**Contenuto chiave:**
- Database materiali (PLA, PETG, ABS, ASA, PC, Nylon, TPU, compositi)
- Vincoli per materiale: temp, shrinkage, anisotropia, layer adhesion
- Profili stampante comuni (Bambu, Prusa, Ender, Voron)
- Regole di design per materiale (es. PC necessita raccordi generosi)
- Parametri Tullomer/PC wrapping (specifici per il tuo workflow)

**Deliverable:** `skills/print-profiles/SKILL.md` + `skills/print-profiles/materials.json`

---

### FASE 4 — Orchestrazione (Skill 6)

#### Skill 6: `3d-print-orchestrator` — Pipeline Completa
**Scopo:** Skill master che orchestra tutte le altre in sequenza.

**Workflow orchestrato:**
```
1. Ricevi richiesta (testo e/o immagine)
2. → [image-to-3d] se c'è un'immagine
3. → [spatial-reasoning] decomposizione geometrica
4. → [print-profiles] seleziona vincoli materiale
5. → [openscad-codegen] genera codice parametrico
6. → [openscad-validate] compila + fix loop via MCP
7. → Export STL finale + report
```

**Deliverable:** `skills/3d-print-orchestrator/SKILL.md`

---

## Struttura Directory Finale

```
~/.claude/skills/
├── spatial-reasoning/
│   └── SKILL.md
├── openscad-codegen/
│   ├── SKILL.md
│   └── templates/
│       ├── enclosure.scad
│       ├── bracket.scad
│       ├── snap-fit.scad
│       └── parametric-box.scad
├── openscad-validate/
│   └── SKILL.md
├── image-to-3d/
│   └── SKILL.md
├── print-profiles/
│   ├── SKILL.md
│   └── materials.json
└── 3d-print-orchestrator/
    └── SKILL.md

~/.claude/mcp-servers/
└── openscad-mcp/
    ├── package.json
    ├── src/
    │   └── index.ts
    └── README.md
```

---

## Ordine di Implementazione e Dipendenze

```
Fase 1 (parallelo):  Skill 1 + Skill 2          [nessuna dipendenza]
Fase 2 (sequenziale): MCP Server → Skill 3       [dipende da MCP]
Fase 3 (parallelo):  Skill 4 + Skill 5           [nessuna dipendenza]
Fase 4:              Skill 6                      [dipende da tutte]
```

**Tempo stimato:** ~2-3 sessioni Claude CLI intensive per completare tutto.

---

## Test Cases per Validazione

| # | Test | Complessità | Skill testate |
|---|------|-------------|---------------|
| 1 | Scatola parametrica con coperchio | Bassa | 1, 2, 3 |
| 2 | Supporto per telefono | Media | 1, 2, 3, 5 |
| 3 | Enclosure per Arduino Uno | Media | 1, 2, 3, 5 |
| 4 | Da foto di oggetto rotto → ricambio | Alta | 1, 2, 3, 4 |
| 5 | Staffa composita per 80°C (Tullomer/PC) | Alta | 1, 2, 3, 5 |
| 6 | Da sketch a mano → parte funzionale | Alta | Tutte |
