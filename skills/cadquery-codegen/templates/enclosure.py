"""PCB Enclosure — Generato da Claude CLI
Enclosure generico per PCB con standoff cilindrici e coperchio.
Export: enclosure body + lid in STEP e STL.
"""
import cadquery as cq
import os

# === PARAMETRI PRINCIPALI (PCB) ===
pcb_w       = 70.0    # [mm] larghezza PCB
pcb_d       = 50.0    # [mm] profondità PCB
pcb_thick   = 1.6     # [mm] spessore PCB
pcb_clearance = 1.0   # [mm] gioco attorno al PCB

# === PARAMETRI FORI MONTAGGIO PCB ===
# Posizioni fori relative al centro del PCB
mount_holes = [
    (-30.0, -20.0),   # [mm] angolo inferiore sinistro
    ( 30.0, -20.0),   # [mm] angolo inferiore destro
    (-30.0,  20.0),   # [mm] angolo superiore sinistro
    ( 30.0,  20.0),   # [mm] angolo superiore destro
]
mount_hole_d   = 2.5   # [mm] diametro foro vite (M2.5)
standoff_d     = 5.0   # [mm] diametro esterno standoff
standoff_h     = 5.0   # [mm] altezza standoff (distanza PCB dal fondo)

# === PARAMETRI DI STAMPA ===
wall         = 2.0     # [mm] spessore parete
floor_t      = 1.6     # [mm] spessore fondo
fillet_r     = 2.0     # [mm] raggio raccordo angoli esterni
clearance_h  = 15.0    # [mm] spazio sopra il PCB per componenti

# === PARAMETRI COPERCHIO ===
lid_t        = 1.6     # [mm] spessore coperchio
lip_h        = 2.5     # [mm] altezza labbro incastro
lip_gap      = 0.3     # [mm] gioco labbro

# === PARAMETRI APERTURE ===
# Aperture sui lati: (faccia, x_offset, z_offset, width, height)
# faccia: ">X", "<X", ">Y", "<Y"
apertures = [
    (">X", 0.0, 8.0, 12.0, 8.0),     # USB / connettore
    ("<X", 0.0, 8.0,  8.0, 6.0),      # alimentazione
]

# === PARAMETRI DERIVATI ===
inner_w = pcb_w + 2 * pcb_clearance          # [mm]
inner_d = pcb_d + 2 * pcb_clearance          # [mm]
inner_h = standoff_h + pcb_thick + clearance_h  # [mm]
outer_w = inner_w + 2 * wall                 # [mm]
outer_d = inner_d + 2 * wall                 # [mm]
outer_h = inner_h + floor_t                  # [mm]

# === OUTPUT ===
out_dir = os.path.dirname(os.path.abspath(__file__))


def make_enclosure_body():
    """Corpo enclosure: box con cavità, fillet sugli angoli."""
    outer = (
        cq.Workplane("XY")
        .box(outer_w, outer_d, outer_h)
        .translate((0, 0, outer_h / 2))
        .edges("|Z")
        .fillet(fillet_r)
    )
    cavity = (
        cq.Workplane("XY")
        .box(inner_w, inner_d, inner_h)
        .translate((0, 0, floor_t + inner_h / 2))
    )
    body = outer.cut(cavity)
    return body


def add_standoffs(body):
    """Aggiunge standoff cilindrici per il montaggio PCB."""
    for (mx, my) in mount_holes:
        standoff = (
            cq.Workplane("XY")
            .circle(standoff_d / 2)
            .extrude(standoff_h)
            .translate((mx, my, floor_t))
        )
        body = body.union(standoff)
        # Foro nel standoff
        hole = (
            cq.Workplane("XY")
            .circle(mount_hole_d / 2)
            .extrude(standoff_h + floor_t + 1)
            .translate((mx, my, 0))
        )
        body = body.cut(hole)
    return body


def add_apertures(body):
    """Ritaglia le aperture sui lati."""
    for (face_sel, x_off, z_off, ap_w, ap_h) in apertures:
        # Apertura come box che attraversa la parete
        cut_depth = wall + 2  # [mm] assicura che tagli tutto lo spessore

        if face_sel in (">X", "<X"):
            x_sign = 1 if face_sel == ">X" else -1
            cut_box = (
                cq.Workplane("XY")
                .box(cut_depth, ap_w, ap_h)
                .translate((
                    x_sign * outer_w / 2,
                    x_off,
                    floor_t + z_off + ap_h / 2,
                ))
            )
        else:  # ">Y" or "<Y"
            y_sign = 1 if face_sel == ">Y" else -1
            cut_box = (
                cq.Workplane("XY")
                .box(ap_w, cut_depth, ap_h)
                .translate((
                    x_off,
                    y_sign * outer_d / 2,
                    floor_t + z_off + ap_h / 2,
                ))
            )
        body = body.cut(cut_box)
    return body


def add_fillets(body):
    """Fillet già applicato in make_enclosure_body — noop."""
    return body


def make_lid():
    """Coperchio con labbro di incastro."""
    top = (
        cq.Workplane("XY")
        .box(outer_w, outer_d, lid_t)
        .translate((0, 0, lid_t / 2))
    )
    lip_w = inner_w - 2 * lip_gap    # [mm]
    lip_d = inner_d - 2 * lip_gap    # [mm]
    lip = (
        cq.Workplane("XY")
        .box(lip_w, lip_d, lip_h)
        .translate((0, 0, -lip_h / 2))
    )
    # Svuota il labbro
    lip_cavity = (
        cq.Workplane("XY")
        .box(lip_w - 2 * wall, lip_d - 2 * wall, lip_h + 1)
        .translate((0, 0, -lip_h / 2))
    )
    lid = top.union(lip).cut(lip_cavity)
    lid = lid.edges("|Z").fillet(fillet_r)
    return lid


def make_assembly():
    """Assembla enclosure body e lid."""
    body = make_enclosure_body()
    body = add_standoffs(body)
    body = add_apertures(body)
    body = add_fillets(body)
    lid = make_lid()
    return body, lid


# === EXPORT ===
body, lid = make_assembly()

body_step = os.path.join(out_dir, "enclosure.step")
body_stl  = os.path.join(out_dir, "enclosure.stl")
cq.exporters.export(body, body_step)
cq.exporters.export(body, body_stl)

lid_step = os.path.join(out_dir, "enclosure_lid.step")
lid_stl  = os.path.join(out_dir, "enclosure_lid.stl")
cq.exporters.export(lid, lid_step)
cq.exporters.export(lid, lid_stl)

for name, part in [("ENCLOSURE", body), ("LID", lid)]:
    bb = part.val().BoundingBox()
    vol = part.val().Volume()
    print(f"{name}: {bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm, vol={vol:.0f} mm³")

print(f"Files: {body_step}, {body_stl}, {lid_step}, {lid_stl}")
