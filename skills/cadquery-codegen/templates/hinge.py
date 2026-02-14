"""Hinge — 2-Part Pin & Knuckle — Generato da Claude CLI
Cerniera a 2 parti: parte A (knuckle) e parte B (knuckle) collegate da pin.
Export: assembly .step + parti singole .step/.stl.
"""
import cadquery as cq
import os

# === PARAMETRI PRINCIPALI ===
hinge_width   = 40.0    # [mm] larghezza totale cerniera
pin_d         = 3.0     # [mm] diametro pin
n_knuckles    = 5       # numero totale knuckle (dispari: 3 su A, 2 su B)
knuckle_gap   = 0.3     # [mm] gioco tra knuckle adiacenti

# === PARAMETRI DI STAMPA ===
leaf_w        = 15.0    # [mm] larghezza foglia (braccio piatto)
leaf_thick    = 2.0     # [mm] spessore foglia
knuckle_od    = 6.0     # [mm] diametro esterno knuckle
fillet_r      = 0.8     # [mm] raccordo giunzione foglia-knuckle
hole_d        = 3.4     # [mm] diametro fori montaggio (M3 clearance)
n_mount_holes = 2       # fori montaggio per foglia
mount_margin  = 8.0     # [mm] margine primo foro dal bordo

# === PARAMETRI DERIVATI ===
knuckle_total_len = hinge_width - (n_knuckles - 1) * knuckle_gap  # [mm]
knuckle_len = knuckle_total_len / n_knuckles                       # [mm] lunghezza singolo knuckle
pin_r = pin_d / 2                                                   # [mm]
knuckle_r = knuckle_od / 2                                          # [mm]

# === OUTPUT ===
out_dir = os.path.dirname(os.path.abspath(__file__))


def make_leaf(side="A"):
    """Crea la foglia piatta con fori di montaggio.
    side='A': foglia a X positivo, side='B': foglia a X negativo.
    """
    x_sign = 1 if side == "A" else -1

    leaf = (
        cq.Workplane("XY")
        .box(leaf_w, hinge_width, leaf_thick)
        .translate((
            x_sign * (leaf_w / 2 + knuckle_r),
            0,
            leaf_thick / 2,
        ))
    )

    # Fori di montaggio
    if n_mount_holes > 0:
        hole_spacing = (hinge_width - 2 * mount_margin) / max(n_mount_holes - 1, 1)
        pts = [
            (0, -hinge_width / 2 + mount_margin + i * hole_spacing)
            for i in range(n_mount_holes)
        ]
        leaf = (
            leaf
            .faces(">Z")
            .workplane()
            .center(x_sign * (leaf_w / 2 + knuckle_r), 0)
            .pushPoints(pts)
            .hole(hole_d)
        )

    return leaf


def make_knuckles(side="A"):
    """Crea i knuckle cilindrici per un lato.
    side='A': knuckle dispari (0, 2, 4, ...), side='B': knuckle pari (1, 3, ...).
    """
    result = None
    for i in range(n_knuckles):
        # A prende indici pari, B prende indici dispari
        if side == "A" and i % 2 != 0:
            continue
        if side == "B" and i % 2 != 1:
            continue

        y_start = -hinge_width / 2 + i * (knuckle_len + knuckle_gap)

        knuckle = (
            cq.Workplane("XZ")
            .circle(knuckle_r)
            .extrude(knuckle_len)
            .translate((0, y_start, knuckle_r))
        )

        if result is None:
            result = knuckle
        else:
            result = result.union(knuckle)

    return result


def make_pin_holes(body):
    """Fora i knuckle per il passaggio del pin."""
    pin_hole = (
        cq.Workplane("XZ")
        .circle(pin_r + 0.1)  # [mm] leggero gioco per il pin
        .extrude(hinge_width + 2)
        .translate((0, -hinge_width / 2 - 1, knuckle_r))
    )
    return body.cut(pin_hole)


def make_pin():
    """Crea il pin cilindrico."""
    pin = (
        cq.Workplane("XZ")
        .circle(pin_r)
        .extrude(hinge_width - 1.0)  # leggermente più corto
        .translate((0, -hinge_width / 2 + 0.5, knuckle_r))
    )
    return pin


def make_half(side="A"):
    """Assembla una metà della cerniera (foglia + knuckle + fori pin)."""
    leaf = make_leaf(side)
    knuckles = make_knuckles(side)

    half = leaf.union(knuckles)
    half = make_pin_holes(half)

    return half


def make_assembly():
    """Assembla entrambe le metà + pin."""
    half_a = make_half("A")
    half_b = make_half("B")
    pin = make_pin()
    return half_a, half_b, pin


# === EXPORT ===
half_a, half_b, pin = make_assembly()

# Parti singole
for name, part in [("hinge_A", half_a), ("hinge_B", half_b), ("hinge_pin", pin)]:
    step_path = os.path.join(out_dir, f"{name}.step")
    stl_path  = os.path.join(out_dir, f"{name}.stl")
    cq.exporters.export(part, step_path)
    cq.exporters.export(part, stl_path)

# Assembly STEP
assy = cq.Assembly()
assy.add(half_a, name="half_A", color=cq.Color(0.27, 0.51, 0.71))
assy.add(half_b, name="half_B", color=cq.Color(1.0, 0.65, 0.0))
assy.add(pin, name="pin", color=cq.Color(0.75, 0.75, 0.75))
assy_path = os.path.join(out_dir, "hinge_assembly.step")
assy.save(assy_path)

# Info
for name, part in [("HALF_A", half_a), ("HALF_B", half_b), ("PIN", pin)]:
    bb = part.val().BoundingBox()
    vol = part.val().Volume()
    print(f"{name}: {bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm, vol={vol:.0f} mm³")

print(f"Assembly: {assy_path}")
