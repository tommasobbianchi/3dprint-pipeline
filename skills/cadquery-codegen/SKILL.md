# SKILL: cadquery-codegen — Generazione Codice CadQuery

## Identità
Generatore di codice CadQuery parametrico per stampa 3D FDM.
Produce script Python standalone che esportano .STEP + .STL.

---

## 1. Template Python Obbligatorio

Ogni script generato DEVE seguire questa struttura:

```python
"""[NOME COMPONENTE] — Generato da Claude CLI
Data: YYYY-MM-DD
Descrizione: [breve descrizione del pezzo]
"""
import cadquery as cq

# === PARAMETRI PRINCIPALI ===
width  = 40.0   # [mm] larghezza esterna
depth  = 30.0   # [mm] profondità esterna
height = 20.0   # [mm] altezza esterna

# === PARAMETRI DI STAMPA ===
wall       = 2.0   # [mm] spessore parete
fillet_r   = 1.5   # [mm] raggio raccordo angoli
clearance  = 0.3   # [mm] gioco per accoppiamenti

# === PARAMETRI DERIVATI ===
inner_w = width  - 2 * wall   # [mm] larghezza interna
inner_d = depth  - 2 * wall   # [mm] profondità interna
inner_h = height - wall        # [mm] altezza interna

# === COSTRUZIONE ===
def make_body():
    """Corpo principale del pezzo."""
    return (
        cq.Workplane("XY")
        .box(width, depth, height)
        .edges("|Z")
        .fillet(fillet_r)
    )

def make_features(body):
    """Aggiunge feature al corpo (fori, tasche, ecc.)."""
    return (
        body
        .faces(">Z")
        .workplane()
        .hole(5.0)
    )

def make_assembly():
    """Assembla tutte le parti."""
    body = make_body()
    body = make_features(body)
    return body

# === EXPORT ===
result = make_assembly()

cq.exporters.export(result, "output.step")
cq.exporters.export(result, "output.stl")

bb = result.val().BoundingBox()
print(f"BB: {bb.xmin:.2f},{bb.ymin:.2f},{bb.zmin:.2f} → {bb.xmax:.2f},{bb.ymax:.2f},{bb.zmax:.2f}")
print(f"SIZE: {bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm")
```

---

## 2. Regole Codice

### Naming e Stile
- **snake_case** per tutte le variabili e funzioni
- Ogni parametro con commento `# [mm]` o `# [deg]`
- Funzioni separate per ogni componente logico (`make_body`, `make_lid`, `make_hinge`)
- MAI magic numbers — ogni valore numerico è una variabile parametrica

### Fluent API
- Usa method chaining dove migliora la leggibilità
- Vai a capo per ogni operazione nella chain (una per riga)
- Parentesi tonde esterne per chain multi-riga

```python
# BENE
result = (
    cq.Workplane("XY")
    .box(width, depth, height)
    .edges("|Z")
    .fillet(fillet_r)
    .faces(">Z")
    .workplane()
    .hole(bore_d)
)

# MALE
result = cq.Workplane("XY").box(width, depth, height).edges("|Z").fillet(fillet_r).faces(">Z").workplane().hole(bore_d)
```

### Ordine Operazioni
1. Primitive (box, cylinder, sphere)
2. Operazioni booleane (cut, union, intersect)
3. **Fillet/chamfer DOPO le booleane** — mai prima
4. Feature secondarie (fori, tasche)
5. Export

### Selettori
- Usa selettori faccia espliciti: `">Z"`, `"<Z"`, `">X"`, `"<Y"`, `"|Z"`, `"#Z"`
- Documenta la faccia selezionata con commento se non ovvia
- Preferisci selettori relativi a selettori per indice

### Export
- SEMPRE esportare sia `.step` che `.stl`
- SEMPRE stampare il bounding box a fine script
- Per assembly multi-parte, esportare ogni parte separatamente + assembly completo

---

## 3. Cheat Sheet CadQuery

### 3.1 Creazione Primitive

```python
# Box centrata sull'origine
cq.Workplane("XY").box(length, width, height)

# Box non centrata (centered=(False, False, False))
cq.Workplane("XY").box(length, width, height, centered=(False, False, False))

# Cilindro
cq.Workplane("XY").cylinder(height, radius)

# Sfera
cq.Workplane("XY").sphere(radius)

# Wedge / cuneo
cq.Workplane("XZ").polyline([(0,0), (base,0), (0,height)]).close().extrude(depth)
```

### 3.2 Selettori Facce ed Edge

```python
# Facce per direzione
.faces(">Z")    # faccia superiore (Z max)
.faces("<Z")    # faccia inferiore (Z min)
.faces(">X")    # faccia destra (X max)
.faces("<X")    # faccia sinistra (X min)
.faces(">Y")    # faccia posteriore (Y max)
.faces("<Y")    # faccia anteriore (Y min)

# Edge per orientamento
.edges("|Z")    # edge paralleli a Z (verticali)
.edges("|X")    # edge paralleli a X
.edges("|Y")    # edge paralleli a Y
.edges("#Z")    # edge perpendicolari a Z (orizzontali)

# Combinazioni con filtri
.edges(">Z")           # edge sul bordo superiore
.edges("<Z")           # edge sul bordo inferiore
.faces(">Z").edges()   # tutti gli edge della faccia top

# Selettore per indice (evitare se possibile)
.faces().item(0)

# Selettore near-point
.edges(cq.selectors.NearestToPointSelector((x, y, z)))
```

### 3.3 Operazioni 2D → 3D

```python
# Sketch → Extrude
.rect(w, h).extrude(depth)
.circle(r).extrude(depth)
.polygon(n_sides, diameter).extrude(depth)

# Polyline → Extrude
.polyline([(x1,y1), (x2,y2), ...]).close().extrude(depth)

# Revolve (attorno a un asse)
.polyline([(x1,y1), (x2,y2), ...]).close().revolve(angle_deg, (0,0,0), (0,1,0))

# Loft tra sezioni
.rect(w1, h1)
.workplane(offset=dist)
.rect(w2, h2)
.loft()

# Sweep lungo un percorso
path = cq.Workplane("XZ").spline([(0,0), (10,10), (20,0)])
cq.Workplane("XY").circle(r).sweep(path)
```

### 3.4 Fori

```python
# Foro passante
.hole(diameter)

# Foro cieco (profondità specificata)
.hole(diameter, depth)

# Foro svasato (counterbore)
.cboreHole(diameter, cboreDiameter, cboreDepth)

# Foro conico (countersink)
.cskHole(diameter, cskDiameter, cskAngle)
```

### 3.5 Pattern

```python
# Griglia rettangolare
.rarray(x_spacing, y_spacing, x_count, y_count)

# Pattern polare
.polarArray(radius, start_angle, angle, count)

# Punti espliciti
.pushPoints([(x1,y1), (x2,y2), ...])
```

### 3.6 Fillet e Chamfer

```python
# Fillet su edge specifici
.edges("|Z").fillet(radius)

# Fillet su tutti gli edge
.edges().fillet(radius)

# Chamfer
.edges("|Z").chamfer(length)

# Chamfer asimmetrico
.edges("|Z").chamfer(length1, length2)
```

### 3.7 Operazioni Booleane

```python
# Unione
body = part_a.union(part_b)

# Sottrazione
body = part_a.cut(part_b)

# Intersezione
body = part_a.intersect(part_b)
```

### 3.8 Workplane e Trasformazioni

```python
# Workplane su una faccia
.faces(">Z").workplane()

# Offset workplane
.workplane(offset=10)

# Workplane con centro spostato
.faces(">Z").workplane().center(dx, dy)

# Trasformazioni
.translate((dx, dy, dz))
.rotate((0,0,0), (0,0,1), angle_deg)
.mirror("XY")
```

### 3.9 Shell (svuotamento)

```python
# Shell rimuovendo la faccia top
.faces(">Z").shell(-wall_thickness)

# Shell verso l'esterno
.faces(">Z").shell(wall_thickness)
```

### 3.10 Assembly

```python
assy = cq.Assembly()
assy.add(part_a, name="base", color=cq.Color("gray"))
assy.add(part_b, name="lid", loc=cq.Location((0, 0, height)))
assy.save("assembly.step")
```

### 3.11 Export

```python
# STEP (BREP esatto)
cq.exporters.export(shape, "output.step")

# STL (mesh triangolata)
cq.exporters.export(shape, "output.stl")

# STL con tolleranza custom
cq.exporters.export(shape, "output.stl", tolerance=0.01, angularTolerance=0.1)

# SVG (proiezione 2D)
cq.exporters.export(shape, "output.svg", exportType="SVG")

# DXF (profilo 2D)
cq.exporters.exportDXF(shape, "output.dxf")

# 3MF
cq.exporters.export(shape, "output.3mf")
```

### 3.12 Misure e Debug

```python
# Bounding box
bb = result.val().BoundingBox()
print(f"Size: {bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm")

# Volume
vol = result.val().Volume()
print(f"Volume: {vol:.2f} mm³")

# Area superficiale
area = sum(f.Area() for f in result.val().Faces())
print(f"Surface area: {area:.2f} mm²")

# Conteggio facce/edge
n_faces = len(result.val().Faces())
n_edges = len(result.val().Edges())
```

---

## 4. Anti-Pattern

### 4.1 Magic Numbers
```python
# MALE ❌
result = cq.Workplane("XY").box(40, 30, 20).edges("|Z").fillet(1.5)

# BENE ✅
width    = 40.0   # [mm]
depth    = 30.0   # [mm]
height   = 20.0   # [mm]
fillet_r =  1.5   # [mm]
result = cq.Workplane("XY").box(width, depth, height).edges("|Z").fillet(fillet_r)
```

### 4.2 Fillet Prima delle Booleane
```python
# MALE ❌ — fillet prima del cut, rischio kernel crash
body = cq.Workplane("XY").box(40, 30, 20).edges("|Z").fillet(2)
body = body.cut(cq.Workplane("XY").box(10, 10, 25))

# BENE ✅ — fillet dopo tutte le booleane
body = cq.Workplane("XY").box(40, 30, 20)
body = body.cut(cq.Workplane("XY").box(10, 10, 25))
body = body.edges("|Z").fillet(2)
```

### 4.3 Mesh Diretta
```python
# MALE ❌ — mai usare numpy-stl o trimesh per creare geometria
import numpy as np
from stl import mesh

# BENE ✅ — sempre modellazione solida BREP
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
```

### 4.4 Mancata Esportazione Duale
```python
# MALE ❌ — solo STL
cq.exporters.export(result, "output.stl")

# BENE ✅ — sempre STEP + STL
cq.exporters.export(result, "output.step")
cq.exporters.export(result, "output.stl")
```

### 4.5 Selettori Ambigui
```python
# MALE ❌ — selettore per indice, fragile
.faces().item(2).workplane()

# BENE ✅ — selettore per direzione, robusto
.faces(">Z").workplane()
```

### 4.6 Chain Illeggibili
```python
# MALE ❌ — tutto su una riga
result = cq.Workplane("XY").box(40,30,20).faces(">Z").workplane().rect(20,10).cutBlind(-5).edges("|Z").fillet(2)

# BENE ✅ — una operazione per riga
result = (
    cq.Workplane("XY")
    .box(40, 30, 20)
    .faces(">Z")
    .workplane()
    .rect(20, 10)
    .cutBlind(-5)
    .edges("|Z")
    .fillet(2)
)
```

### 4.7 Nessun Bounding Box in Output
```python
# MALE ❌ — nessuna verifica dimensionale
cq.exporters.export(result, "output.step")

# BENE ✅ — sempre stampare BB per validazione
cq.exporters.export(result, "output.step")
bb = result.val().BoundingBox()
print(f"SIZE: {bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm")
```

### 4.8 Parametri Non Documentati
```python
# MALE ❌
wall = 2
d = 4.2

# BENE ✅
wall = 2.0          # [mm] spessore parete
insert_d = 4.2      # [mm] diametro foro per inserto M3
```

---

## 5. Templates Disponibili

Directory: `skills/cadquery-codegen/templates/`

| Template | Descrizione | Export |
|---|---|---|
| `parametric_box.py` | Scatola con coperchio e snap-fit opzionali | body.step/stl + lid.step/stl |
| `bracket_l.py` | Staffa a L con nervature e fori | bracket.step/stl |
| `enclosure.py` | Enclosure per PCB con standoff | enclosure.step/stl + lid.step/stl |
| `snap_fit.py` | Modulo snap-fit cantilever | snap_fit.step/stl |
| `threaded_insert.py` | Fori per inserti a caldo M2–M5 | insert_boss.step/stl |
| `hinge.py` | Cerniera a 2 parti (pin + knuckle) | assembly.step + parte singola .step/stl |

Ogni template è uno script Python standalone eseguibile con `python3 template.py`.
