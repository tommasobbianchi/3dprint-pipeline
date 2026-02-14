"""Parametric Box with Lid — Generato da Claude CLI
Scatola parametrica con coperchio a incastro e snap-fit opzionale.
Export: body + lid in STEP e STL.
"""
import cadquery as cq
import os

# === PARAMETRI PRINCIPALI ===
inner_w  = 60.0    # [mm] larghezza interna
inner_d  = 40.0    # [mm] profondità interna
inner_h  = 25.0    # [mm] altezza interna

# === PARAMETRI DI STAMPA ===
wall     = 2.0     # [mm] spessore parete
floor_t  = 1.6     # [mm] spessore fondo
lid_t    = 1.6     # [mm] spessore coperchio
fillet_r = 2.0     # [mm] raggio raccordo angoli verticali
lip_h    = 3.0     # [mm] altezza labbro incastro coperchio
lip_gap  = 0.3     # [mm] gioco labbro (clearance)

# === PARAMETRI SNAP-FIT ===
snap_fit     = True    # abilita/disabilita snap-fit
snap_w       = 4.0     # [mm] larghezza linguetta snap-fit
snap_h       = 2.0     # [mm] altezza linguetta
snap_lip     = 0.8     # [mm] sporgenza lip dello snap
snap_thick   = 1.2     # [mm] spessore linguetta

# === PARAMETRI DERIVATI ===
outer_w  = inner_w + 2 * wall              # [mm]
outer_d  = inner_d + 2 * wall              # [mm]
outer_h  = inner_h + floor_t               # [mm] altezza esterna body
lid_outer_h = lid_t + lip_h                # [mm] altezza totale coperchio

# === OUTPUT ===
out_dir = os.path.dirname(os.path.abspath(__file__))


def make_body():
    """Corpo scatola: box esterna - cavità interna + fillet."""
    outer = (
        cq.Workplane("XY")
        .box(outer_w, outer_d, outer_h)
        .translate((0, 0, outer_h / 2))
    )
    cavity = (
        cq.Workplane("XY")
        .box(inner_w, inner_d, inner_h)
        .translate((0, 0, floor_t + inner_h / 2))
    )
    body = outer.cut(cavity)
    body = body.edges("|Z").fillet(fillet_r)
    return body


def make_body_snap(body):
    """Aggiunge slot per snap-fit sulle pareti lunghe del body."""
    if not snap_fit:
        return body
    # Slot rettangolari nelle pareti Y (lati lunghi)
    for y_sign in [1, -1]:
        y_pos = y_sign * (outer_d / 2)
        slot = (
            cq.Workplane("XZ")
            .center(0, floor_t + inner_h - snap_h / 2)
            .rect(snap_w + 0.4, snap_h + 0.4)
            .extrude(wall + 1)
            .translate((0, y_pos - y_sign * (wall / 2 + 0.5), 0))
        )
        body = body.cut(slot)
    return body


def make_lid():
    """Coperchio con labbro di incastro."""
    # Parte piatta superiore
    top = (
        cq.Workplane("XY")
        .box(outer_w, outer_d, lid_t)
        .translate((0, 0, lid_t / 2))
    )
    # Labbro che entra nella scatola
    lip_w = inner_w - 2 * lip_gap   # [mm]
    lip_d = inner_d - 2 * lip_gap   # [mm]
    lip = (
        cq.Workplane("XY")
        .box(lip_w, lip_d, lip_h)
        .translate((0, 0, -lip_h / 2))
    )
    # Svuota il labbro per risparmiare materiale
    lip_cavity = (
        cq.Workplane("XY")
        .box(lip_w - 2 * wall, lip_d - 2 * wall, lip_h + 1)
        .translate((0, 0, -lip_h / 2))
    )
    lid = top.union(lip).cut(lip_cavity)
    lid = lid.edges("|Z").fillet(fillet_r)
    return lid


def make_lid_snap(lid):
    """Aggiunge linguette snap-fit al coperchio."""
    if not snap_fit:
        return lid
    lip_d_actual = inner_d - 2 * lip_gap  # [mm]
    for y_sign in [1, -1]:
        y_base = y_sign * (lip_d_actual / 2 - wall)
        # Linguetta: piccola sporgenza sul labbro
        tab = (
            cq.Workplane("XZ")
            .center(0, -lip_h + snap_h / 2)
            .rect(snap_w, snap_h)
            .extrude(snap_lip)
            .translate((0, y_base + y_sign * snap_lip / 2, 0))
        )
        lid = lid.union(tab)
    return lid


def make_assembly():
    """Assembla body e lid."""
    body = make_body()
    body = make_body_snap(body)
    lid = make_lid()
    lid = make_lid_snap(lid)
    return body, lid


# === EXPORT ===
body, lid = make_assembly()

# Body
body_step = os.path.join(out_dir, "body.step")
body_stl  = os.path.join(out_dir, "body.stl")
cq.exporters.export(body, body_step)
cq.exporters.export(body, body_stl)

# Lid
lid_step = os.path.join(out_dir, "lid.step")
lid_stl  = os.path.join(out_dir, "lid.stl")
cq.exporters.export(lid, lid_step)
cq.exporters.export(lid, lid_stl)

# Info
for name, part in [("BODY", body), ("LID", lid)]:
    bb = part.val().BoundingBox()
    vol = part.val().Volume()
    print(f"{name}: {bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm, vol={vol:.0f} mm³")

print(f"Files: {body_step}, {body_stl}, {lid_step}, {lid_stl}")
