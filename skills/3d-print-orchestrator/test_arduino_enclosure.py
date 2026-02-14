"""Arduino Uno Rev3 Enclosure — Test End-to-End Pipeline 3D Print
Generato da Claude CLI — 2026-02-13
Enclosure per Arduino Uno Rev3 + mini breadboard 47x35mm.
Snap-fit closure, griglia ventilazione, aperture USB-B e DC jack.
Materiale: PETG (wall_min=1.2mm, density=1.27 g/cm³)
"""
import cadquery as cq
import os

# === PARAMETRI PCB ARDUINO UNO REV3 ===
pcb_w       = 68.6     # [mm] larghezza PCB Arduino
pcb_d       = 53.4     # [mm] profondita PCB Arduino
pcb_thick   = 1.6      # [mm] spessore PCB
comp_h      = 15.0     # [mm] altezza max componenti sopra PCB
pcb_clearance = 1.0    # [mm] gioco attorno al PCB

# === PARAMETRI MINI BREADBOARD ===
bb_w        = 47.0     # [mm] larghezza mini breadboard
bb_d        = 35.0     # [mm] profondita mini breadboard
bb_gap      = 3.0      # [mm] gap tra Arduino e breadboard

# === PARAMETRI FORI MONTAGGIO ARDUINO ===
# Posizioni relative all'angolo inferiore-sinistro del PCB
arduino_holes = [
    (13.97,  2.54),     # [mm] foro 1
    (66.04,  7.62),     # [mm] foro 2
    (66.04, 35.56),     # [mm] foro 3
    (15.24, 50.80),     # [mm] foro 4
]
mount_hole_d   = 3.2    # [mm] diametro foro passante M3
standoff_od    = 6.0    # [mm] diametro esterno standoff
standoff_h     = 5.0    # [mm] altezza standoff

# === PARAMETRI DI STAMPA (PETG) ===
wall         = 2.0      # [mm] spessore parete (> PETG wall_min 1.2mm)
floor_t      = 1.6      # [mm] spessore fondo
fillet_r     = 1.5      # [mm] raggio raccordo angoli verticali esterni
clearance    = 0.3      # [mm] gioco generico

# === PARAMETRI APERTURE ===
# USB-B: sul lato corto dove X = pcb_w (lato destro Arduino)
usb_w        = 12.0     # [mm] larghezza apertura USB-B
usb_h        = 10.9     # [mm] altezza apertura USB-B
usb_y_center = 31.5     # [mm] centro USB-B dal bordo inferiore del PCB

# DC jack: stesso lato del USB-B
dc_w         = 9.0      # [mm] larghezza apertura DC jack
dc_h         = 11.0     # [mm] altezza apertura DC jack
dc_y_center  = 7.0      # [mm] centro DC jack dal bordo inferiore del PCB

# === PARAMETRI COPERCHIO + SNAP-FIT ===
lid_t        = 1.6      # [mm] spessore coperchio
lip_h        = 3.0      # [mm] altezza labbro incastro
lip_gap      = 0.3      # [mm] gioco labbro
snap_w       = 8.0      # [mm] larghezza hook snap-fit
snap_h       = 2.0      # [mm] altezza hook
snap_depth   = 1.0      # [mm] profondita undercut snap
snap_overhang = 0.8     # [mm] sporgenza hook

# === PARAMETRI VENTILAZIONE ===
vent_slot_w  = 2.0      # [mm] larghezza singola fessura
vent_slot_l  = 30.0     # [mm] lunghezza fessure
vent_gap     = 3.0      # [mm] passo tra fessure (centro-centro)
vent_n       = 8        # numero fessure

# === PARAMETRI DERIVATI ===
# Layout interno: [Arduino] [gap] [breadboard]
inner_w = pcb_w + bb_gap + bb_w + 2 * pcb_clearance          # [mm]
inner_d = max(pcb_d, bb_d) + 2 * pcb_clearance               # [mm]
inner_h = standoff_h + pcb_thick + comp_h                      # [mm]
outer_w = inner_w + 2 * wall                                   # [mm]
outer_d = inner_d + 2 * wall                                   # [mm]
outer_h = inner_h + floor_t                                    # [mm]

# Offset Arduino PCB: centrato in Y, spostato a sinistra in X
# Arduino occupa X da 0 a pcb_w, breadboard da pcb_w+gap a pcb_w+gap+bb_w
# Il centro della cavita interna e a inner_w/2
# Arduino centra PCB: offset X dal centro = -(inner_w/2) + pcb_clearance + pcb_w/2
arduino_x_offset = -(inner_w / 2) + pcb_clearance + pcb_w / 2   # [mm]
arduino_y_offset = 0.0  # [mm] centrato in Y (PCB centrato nella profondita)

# Posizioni fori in coordinate assolute (centro enclosure = 0,0)
hole_positions = [
    (arduino_x_offset - pcb_w / 2 + hx,
     arduino_y_offset - pcb_d / 2 + hy)
    for hx, hy in arduino_holes
]

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


def add_standoffs(body):
    """Aggiunge 4 standoff M3 nelle posizioni esatte del PCB Arduino."""
    for (mx, my) in hole_positions:
        # Standoff cilindrico
        standoff = (
            cq.Workplane("XY")
            .circle(standoff_od / 2)
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
    """Ritaglia aperture USB-B e DC jack sul lato destro (X positivo del PCB Arduino)."""
    cut_depth = wall + 2  # [mm] per tagliare tutta la parete

    # Il lato USB/DC e dove X del PCB = pcb_w, cioe X assoluto = arduino_x_offset + pcb_w/2
    # Questo corrisponde al bordo destro dell'Arduino
    # L'apertura va sulla parete esterna a X = outer_w/2
    wall_x = outer_w / 2  # [mm] centro del taglio sulla parete destra

    # USB-B
    usb_z_center = floor_t + standoff_h + pcb_thick + usb_h / 2  # [mm] centro Z
    usb_y_abs = arduino_y_offset - pcb_d / 2 + usb_y_center       # [mm] centro Y assoluto
    usb_cut = (
        cq.Workplane("XY")
        .box(cut_depth, usb_w, usb_h)
        .translate((wall_x, usb_y_abs, usb_z_center))
    )
    body = body.cut(usb_cut)

    # DC jack
    dc_z_center = floor_t + standoff_h + pcb_thick + dc_h / 2  # [mm]
    dc_y_abs = arduino_y_offset - pcb_d / 2 + dc_y_center       # [mm]
    dc_cut = (
        cq.Workplane("XY")
        .box(cut_depth, dc_w, dc_h)
        .translate((wall_x, dc_y_abs, dc_z_center))
    )
    body = body.cut(dc_cut)

    return body


def add_snap_recesses(body):
    """Aggiunge incavi per snap-fit sulle pareti interne del body (lati lunghi)."""
    # 2 snap per lato lungo (totale 4)
    snap_positions_x = [-inner_w / 4, inner_w / 4]  # [mm]

    for sx in snap_positions_x:
        for y_sign in [1, -1]:
            y_pos = y_sign * (outer_d / 2 - wall / 2)  # [mm]
            recess = (
                cq.Workplane("XY")
                .box(snap_w, wall + 1, snap_h)
                .translate((sx, y_pos, outer_h - snap_h / 2))
            )
            body = body.cut(recess)
    return body


def make_body():
    """Assembla il corpo dell'enclosure."""
    body = make_outer_shell()
    body = make_cavity(body)
    body = add_standoffs(body)
    body = add_apertures(body)
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

    # Labbro di incastro
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

    # Snap-fit hooks (4 hooks sui lati lunghi)
    snap_positions_x = [-inner_w / 4, inner_w / 4]  # [mm]

    for sx in snap_positions_x:
        for y_sign in [1, -1]:
            y_base = y_sign * (lip_d / 2 - wall / 2)  # [mm]
            # Hook: blocchetto che sporge verso l'esterno
            hook = (
                cq.Workplane("XY")
                .box(snap_w, snap_overhang, snap_h)
                .translate((
                    sx,
                    y_base + y_sign * snap_overhang / 2,
                    -lip_h + snap_h / 2
                ))
            )
            lid = lid.union(hook)

    return lid


def add_vent_grid(lid):
    """Griglia di ventilazione sul coperchio: fessure rettangolari."""
    start_x = -(vent_n - 1) * vent_gap / 2  # [mm] posizione prima fessura

    for i in range(vent_n):
        x_pos = start_x + i * vent_gap  # [mm]
        slot = (
            cq.Workplane("XY")
            .box(vent_slot_w, vent_slot_l, lid_t + 2)
            .translate((x_pos, 0, lid_t / 2))
        )
        lid = lid.cut(slot)
    return lid


def make_lid_complete():
    """Coperchio con ventilazione."""
    lid = make_lid()
    lid = add_vent_grid(lid)
    return lid


# === EXPORT ===
body = make_body()
lid = make_lid_complete()

# Body
body_step = os.path.join(out_dir, "arduino_enclosure.step")
body_stl  = os.path.join(out_dir, "arduino_enclosure.stl")
cq.exporters.export(body, body_step)
cq.exporters.export(body, body_stl)

# Lid
lid_step = os.path.join(out_dir, "arduino_enclosure_lid.step")
lid_stl  = os.path.join(out_dir, "arduino_enclosure_lid.stl")
cq.exporters.export(lid, lid_step)
cq.exporters.export(lid, lid_stl)

# Assembly
assy = cq.Assembly()
assy.add(body, name="body", color=cq.Color(0.27, 0.51, 0.71))  # blu acciaio
assy.add(
    lid, name="lid",
    loc=cq.Location((0, 0, outer_h + 2)),  # sollevato per visualizzazione
    color=cq.Color(0.9, 0.9, 0.9)  # grigio chiaro
)
assy_step = os.path.join(out_dir, "arduino_enclosure_assembly.step")
assy.save(assy_step)

# === REPORT ===
print("=" * 55)
print("  REPORT — Arduino Uno Rev3 Enclosure (PETG)")
print("=" * 55)

for name, part in [("BODY", body), ("LID", lid)]:
    bb = part.val().BoundingBox()
    vol = part.val().Volume()
    vol_cm3 = vol / 1000
    peso_g = vol_cm3 * 1.27 * (0.3 + 0.7 * 0.20)  # PETG, 20% infill
    tempo_h = (vol_cm3 / 20) * 1.3
    ore = int(tempo_h)
    minuti = int((tempo_h - ore) * 60)

    print(f"\n{name}:")
    print(f"  BB: {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm")
    print(f"  Volume: {vol:,.0f} mm3 ({vol_cm3:.1f} cm3)")
    print(f"  Peso stimato: {peso_g:.1f}g (PETG, 20% infill)")
    print(f"  Tempo stimato: ~{ore}h {minuti}min")

print(f"\nMateriale: PETG")
print(f"  wall_min: 1.2mm (usato: {wall}mm) OK")
print(f"  Fillet: {fillet_r}mm su spigoli verticali")
print(f"  Camera chiusa: non richiesta")
print(f"  Essiccazione: 65C x 4h consigliata")

print(f"\nDimensioni interne:")
print(f"  Larghezza: {inner_w:.1f}mm (Arduino {pcb_w}+gap {bb_gap}+breadboard {bb_w}+clearance)")
print(f"  Profondita: {inner_d:.1f}mm (PCB {pcb_d}+clearance)")
print(f"  Altezza: {inner_h:.1f}mm (standoff {standoff_h}+PCB {pcb_thick}+comp {comp_h})")

print(f"\nFori M3: {len(hole_positions)} posizioni")
for i, (hx, hy) in enumerate(hole_positions):
    print(f"  Foro {i+1}: ({hx:.2f}, {hy:.2f})")

print(f"\nFile esportati:")
print(f"  {body_step}")
print(f"  {body_stl}")
print(f"  {lid_step}")
print(f"  {lid_stl}")
print(f"  {assy_step}")
print("=" * 55)
