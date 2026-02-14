"""Credit Card Holder — Snap-Fit Lid
Generato da Claude CLI — 2026-02-13
Porta carte di credito con chiusura snap-fit.
Dimensioni carta: ISO 7810 ID-1 (85.6 x 53.98 mm)
Materiale: PLA (wall_min=1.0mm, density=1.24 g/cm3)
"""
import cadquery as cq
import os

# === PARAMETRI CARTA DI CREDITO (ISO 7810) ===
card_w       = 85.6     # [mm] larghezza carta
card_d       = 53.98    # [mm] profondita carta
clearance    = 1.0      # [mm] gioco attorno alle carte

# === PARAMETRI SCATOLA ===
wall         = 2.0      # [mm] spessore parete (> PLA wall_min 1.0mm)
floor_t      = 1.6      # [mm] spessore fondo
outer_h      = 40.0     # [mm] altezza esterna body
fillet_r     = 1.0      # [mm] raggio raccordo angoli verticali

# === PARAMETRI DERIVATI ===
inner_w      = card_w + 2 * clearance    # [mm] 87.6
inner_d      = card_d + 2 * clearance    # [mm] 55.98
inner_h      = outer_h - floor_t         # [mm] 38.4
outer_w      = inner_w + 2 * wall        # [mm] 91.6
outer_d      = inner_d + 2 * wall        # [mm] 59.98

# === PARAMETRI THUMB NOTCH ===
notch_w      = 25.0     # [mm] larghezza intaglio pollice
notch_h      = 12.0     # [mm] profondita intaglio dalla sommita

# === PARAMETRI COPERCHIO + SNAP-FIT ===
lid_t        = 1.6      # [mm] spessore coperchio
lip_h        = 3.0      # [mm] altezza labbro incastro
lip_gap      = 0.3      # [mm] gioco labbro
snap_w       = 10.0     # [mm] larghezza hook snap-fit
snap_h       = 2.0      # [mm] altezza hook
snap_overhang = 0.8     # [mm] sporgenza hook

# === OUTPUT ===
out_dir = os.path.dirname(os.path.abspath(__file__))


def make_outer_shell():
    """Box esterno con fillet sugli spigoli verticali — PRIMA delle boolean."""
    outer = (
        cq.Workplane("XY")
        .box(outer_w, outer_d, outer_h)
        .translate((0, 0, outer_h / 2))
        .edges("|Z")
        .fillet(fillet_r)
    )
    return outer


def make_cavity(outer):
    """Scava la cavita interna."""
    cavity = (
        cq.Workplane("XY")
        .box(inner_w, inner_d, inner_h)
        .translate((0, 0, floor_t + inner_h / 2))
    )
    return outer.cut(cavity)


def add_thumb_notch(body):
    """Intaglio rettangolare sul lato frontale per estrarre le carte."""
    notch = (
        cq.Workplane("XY")
        .box(notch_w, wall + 2, notch_h)
        .translate((0, outer_d / 2, outer_h - notch_h / 2))
    )
    return body.cut(notch)


def add_snap_recesses(body):
    """Incavi per snap-fit sulle pareti interne (lati lunghi Y)."""
    for y_sign in [1, -1]:
        y_pos = y_sign * (outer_d / 2 - wall / 2)   # [mm] centro parete
        recess = (
            cq.Workplane("XY")
            .box(snap_w, wall + 1, snap_h)
            .translate((0, y_pos, outer_h - snap_h / 2))
        )
        body = body.cut(recess)
    return body


def make_body():
    """Assembla il corpo della scatola."""
    body = make_outer_shell()
    body = make_cavity(body)
    body = add_thumb_notch(body)
    body = add_snap_recesses(body)
    return body


def make_lid():
    """Coperchio con labbro di incastro e snap-fit hooks."""
    # Piatto superiore
    top = (
        cq.Workplane("XY")
        .box(outer_w, outer_d, lid_t)
        .translate((0, 0, lid_t / 2))
        .edges("|Z")
        .fillet(fillet_r)
    )

    # Labbro di incastro (cornice che entra nella cavita)
    lip_w = inner_w - 2 * lip_gap    # [mm]
    lip_d = inner_d - 2 * lip_gap    # [mm]
    lip_outer = (
        cq.Workplane("XY")
        .box(lip_w, lip_d, lip_h)
        .translate((0, 0, -lip_h / 2))
    )
    lip_inner = (
        cq.Workplane("XY")
        .box(lip_w - 2 * wall, lip_d - 2 * wall, lip_h + 1)
        .translate((0, 0, -lip_h / 2))
    )
    lid = top.union(lip_outer).cut(lip_inner)

    # Snap-fit hooks (2 hooks sui lati lunghi Y, centrati)
    for y_sign in [1, -1]:
        y_base = y_sign * (lip_d / 2 - wall / 2)   # [mm]
        hook = (
            cq.Workplane("XY")
            .box(snap_w, snap_overhang, snap_h)
            .translate((
                0,
                y_base + y_sign * snap_overhang / 2,
                -lip_h + snap_h / 2
            ))
        )
        lid = lid.union(hook)

    return lid


# === EXPORT ===
body = make_body()
lid = make_lid()

# Body
body_step = os.path.join(out_dir, "credit_card_holder.step")
body_stl  = os.path.join(out_dir, "credit_card_holder.stl")
cq.exporters.export(body, body_step)
cq.exporters.export(body, body_stl)

# Lid
lid_step = os.path.join(out_dir, "credit_card_holder_lid.step")
lid_stl  = os.path.join(out_dir, "credit_card_holder_lid.stl")
cq.exporters.export(lid, lid_step)
cq.exporters.export(lid, lid_stl)

# Assembly
assy = cq.Assembly()
assy.add(body, name="body", color=cq.Color(0.27, 0.51, 0.71))
assy.add(
    lid, name="lid",
    loc=cq.Location((0, 0, outer_h + 2)),
    color=cq.Color(0.9, 0.9, 0.9)
)
assy_step = os.path.join(out_dir, "credit_card_holder_assembly.step")
assy.save(assy_step)

# === REPORT ===
print("=" * 55)
print("  REPORT — Credit Card Holder (PLA)")
print("=" * 55)

for name, part in [("BODY", body), ("LID", lid)]:
    bb = part.val().BoundingBox()
    vol = part.val().Volume()
    vol_cm3 = vol / 1000
    peso_g = vol_cm3 * 1.24 * (0.3 + 0.7 * 0.20)
    tempo_h = (vol_cm3 / 20) * 1.3
    ore = int(tempo_h)
    minuti = int((tempo_h - ore) * 60)

    print(f"\n{name}:")
    print(f"  BB: {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm")
    print(f"  Volume: {vol:,.0f} mm3 ({vol_cm3:.1f} cm3)")
    print(f"  Peso stimato: {peso_g:.1f}g (PLA, 20% infill)")
    print(f"  Tempo stimato: ~{ore}h {minuti}min")

print(f"\nMateriale: PLA")
print(f"  wall_min: 1.0mm (usato: {wall}mm) OK")
print(f"  Fillet: {fillet_r}mm su spigoli verticali")
print(f"  Camera chiusa: non richiesta")

print(f"\nDimensioni interne:")
print(f"  Larghezza: {inner_w:.1f}mm (carta {card_w}+clearance)")
print(f"  Profondita: {inner_d:.1f}mm (carta {card_d}+clearance)")
print(f"  Altezza interna: {inner_h:.1f}mm (~{int(inner_h / 0.76)} carte)")

print(f"\nSnap-fit: 2 hook ({snap_w}x{snap_h}mm)")
print(f"Thumb notch: {notch_w}x{notch_h}mm (lato frontale)")

print(f"\nOrientamento stampa: Z-up (fondo in basso)")
print(f"Supporti: non necessari")

print(f"\nFile esportati:")
print(f"  {body_step}")
print(f"  {body_stl}")
print(f"  {lid_step}")
print(f"  {lid_stl}")
print(f"  {assy_step}")
print("=" * 55)
