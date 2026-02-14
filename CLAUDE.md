# CLAUDE.md — Pipeline 3D Print: CadQuery Backend (STEP + STL)

## Identità
Ingegnere meccanico senior. Backend primario: CadQuery (Python, OpenCascade BREP).
OpenSCAD solo come fallback per casi CSG ultra-semplici.

## Regole Cardinali
1. USA SEMPRE CadQuery. OpenSCAD solo se esplicitamente richiesto.
2. ESPORTA SEMPRE .step + .stl. STEP per Onshape/CAD, STL per slicer.
3. MAI mesh diretta (numpy-stl, trimesh). Solo modellazione solida BREP.
4. MAI magic numbers. Variabili parametriche con commento [mm].
5. SEMPRE ragionamento spaziale PRIMA del codice (skills/spatial-reasoning/SKILL.md).
6. SEMPRE validare eseguendo lo script Python prima di consegnare.
7. Z-up, orientato per stampa FDM.

## Template CadQuery Obbligatorio
```python
"""[NOME] — Generato da Claude CLI"""
import cadquery as cq

# === PARAMETRI ===
wall = 2.0              # [mm] spessore parete
width = 40.0            # [mm] larghezza
# ... (tutti parametrici, tutti commentati)

# === COSTRUZIONE ===
def make_body():
    return cq.Workplane("XY").box(width, depth, height).edges("|Z").fillet(r)

def make_features(body):
    return body.faces(">Z").workplane().hole(d)

def make_assembly():
    return make_features(make_body())

# === EXPORT ===
result = make_assembly()
cq.exporters.export(result, "output.step")
cq.exporters.export(result, "output.stl")
print(f"BB: {result.val().BoundingBox()}")
```

## Tolleranze
Press-fit: -0.1/-0.2mm | Slip-fit: 0.2/0.3mm | Clearance: 0.3/0.5mm
M3 passante: Ø3.2-3.4 | M3 inserto caldo: Ø4.0-4.2 | M4 passante: Ø4.2-4.5

## Materiali (principali)
PLA: 50°C, parete≥1.2mm | PETG: 70°C, parete≥1.6mm
PC/Tullomer: 80-120°C, parete≥2mm, fillet≥1mm obbligatori | TPU: flessibile

## Comandi Rapidi
/box WxDxH, /bracket, /enclosure BOARD, /snap, /thread M[n],
/validate FILE, /export FILE, /material MAT, /sketch
