"""L-Bracket with Gussets — Generato da Claude CLI
Staffa a L con nervature triangolari di rinforzo e fori di montaggio.
Export: bracket in STEP e STL.
"""
import cadquery as cq
import os

# === PARAMETRI PRINCIPALI ===
arm_h      = 50.0    # [mm] altezza braccio verticale
arm_w      = 40.0    # [mm] larghezza braccio orizzontale
thickness  = 4.0     # [mm] spessore staffa
depth      = 30.0    # [mm] profondità (asse Y)

# === PARAMETRI FORI ===
n_holes_v  = 2       # numero fori braccio verticale
n_holes_h  = 2       # numero fori braccio orizzontale
hole_d     = 3.4     # [mm] diametro foro passante (M3 clearance)
hole_margin = 10.0   # [mm] distanza primo foro dal bordo

# === PARAMETRI DI STAMPA ===
fillet_r   = 2.0     # [mm] raggio raccordo angoli esterni
inner_r    = 3.0     # [mm] raggio raccordo angolo interno L

# === PARAMETRI NERVATURE ===
n_gussets    = 2       # numero nervature triangolari
gusset_h     = 15.0    # [mm] altezza nervatura sul braccio verticale
gusset_w     = 15.0    # [mm] estensione nervatura sul braccio orizzontale
gusset_thick = 3.0     # [mm] spessore nervatura

# === OUTPUT ===
out_dir = os.path.dirname(os.path.abspath(__file__))


def make_l_profile():
    """Crea il profilo a L come estrusione 2D."""
    # Profilo L nel piano XZ
    profile = (
        cq.Workplane("XZ")
        .moveTo(0, 0)
        .lineTo(arm_w, 0)
        .lineTo(arm_w, thickness)
        .lineTo(thickness, thickness)
        .lineTo(thickness, arm_h)
        .lineTo(0, arm_h)
        .close()
        .extrude(depth)
    )
    return profile


def make_inner_fillet(body):
    """Applica raccordo all'angolo interno della L (prima dei gusset)."""
    # Seleziona solo l'edge dell'angolo interno (x=thickness, z=thickness)
    inner_edge_pt = (thickness, depth / 2, thickness)
    body = (
        body
        .edges(cq.selectors.NearestToPointSelector(inner_edge_pt))
        .fillet(inner_r)
    )
    return body


def add_holes_vertical(body):
    """Fori sul braccio verticale (faccia >X verso la parete)."""
    if n_holes_v == 0:
        return body
    spacing = (arm_h - 2 * hole_margin) / max(n_holes_v - 1, 1)
    pts = [(0, hole_margin + i * spacing) for i in range(n_holes_v)]
    body = (
        body
        .faces("<X")
        .workplane()
        .center(depth / 2, 0)
        .pushPoints(pts)
        .hole(hole_d)
    )
    return body


def add_holes_horizontal(body):
    """Fori sul braccio orizzontale (faccia inferiore)."""
    if n_holes_h == 0:
        return body
    spacing = (arm_w - 2 * hole_margin) / max(n_holes_h - 1, 1)
    pts = [(hole_margin + i * spacing, 0) for i in range(n_holes_h)]
    body = (
        body
        .faces("<Z")
        .workplane()
        .center(-arm_w / 2, depth / 2)
        .pushPoints(pts)
        .hole(hole_d)
    )
    return body


def add_gussets(body):
    """Aggiunge nervature triangolari di rinforzo nell'angolo."""
    if n_gussets == 0:
        return body
    gusset_spacing = depth / (n_gussets + 1)
    for i in range(n_gussets):
        y_pos = gusset_spacing * (i + 1)
        gusset = (
            cq.Workplane("XZ")
            .moveTo(thickness, thickness)
            .lineTo(thickness + gusset_w, thickness)
            .lineTo(thickness, thickness + gusset_h)
            .close()
            .extrude(gusset_thick)
            .translate((0, y_pos - gusset_thick / 2, 0))
        )
        body = body.union(gusset)
    return body


def make_assembly():
    """Assembla la staffa completa."""
    body = make_l_profile()
    body = make_inner_fillet(body)   # fillet PRIMA dei gusset
    body = add_gussets(body)
    body = add_holes_vertical(body)
    body = add_holes_horizontal(body)
    return body


# === EXPORT ===
result = make_assembly()

step_path = os.path.join(out_dir, "bracket.step")
stl_path  = os.path.join(out_dir, "bracket.stl")
cq.exporters.export(result, step_path)
cq.exporters.export(result, stl_path)

bb = result.val().BoundingBox()
vol = result.val().Volume()
print(f"BRACKET: {bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm, vol={vol:.0f} mm³")
print(f"Files: {step_path}, {stl_path}")
