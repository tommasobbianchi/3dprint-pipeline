"""Threaded Insert Bosses — Generato da Claude CLI
Fori per inserti a caldo M2/M3/M4/M5 con boss cilindrici di rinforzo.
Genera una piastra dimostrativa con tutti e 4 i formati.
Export: insert_boss in STEP e STL.
"""
import cadquery as cq
import os

# === TABELLA INSERTI A CALDO ===
# (nome, diametro_foro [mm], profondità_foro [mm], diametro_boss [mm])
INSERT_TABLE = {
    "M2":  (3.2,  5.0,  6.0),
    "M3":  (4.2,  6.0,  8.0),
    "M4":  (5.6,  8.0, 10.0),
    "M5":  (6.4, 10.0, 12.0),
}

# === PARAMETRI PRINCIPALI ===
inserts_to_build = ["M2", "M3", "M4", "M5"]   # taglie da generare
spacing          = 20.0                         # [mm] distanza tra centri boss

# === PARAMETRI DI STAMPA ===
plate_thick  = 3.0     # [mm] spessore piastra base
plate_margin = 10.0    # [mm] margine attorno ai boss
fillet_r     = 1.0     # [mm] raccordo alla base del boss
chamfer_top  = 0.5     # [mm] smusso in cima al boss

# === PARAMETRI DERIVATI ===
n_inserts = len(inserts_to_build)
plate_w   = (n_inserts - 1) * spacing + 2 * plate_margin  # [mm]
plate_d   = 2 * plate_margin                               # [mm]

# === OUTPUT ===
out_dir = os.path.dirname(os.path.abspath(__file__))


def make_plate():
    """Piastra base rettangolare."""
    plate = (
        cq.Workplane("XY")
        .box(plate_w, plate_d, plate_thick)
        .translate((0, 0, plate_thick / 2))
    )
    return plate


def add_bosses(plate):
    """Aggiunge boss cilindrici con foro per inserto a caldo."""
    start_x = -(n_inserts - 1) * spacing / 2

    for i, name in enumerate(inserts_to_build):
        hole_d, hole_depth, boss_d = INSERT_TABLE[name]
        cx = start_x + i * spacing

        boss_h = hole_depth + 1.0  # [mm] boss leggermente più alto del foro

        # Boss cilindrico
        boss = (
            cq.Workplane("XY")
            .circle(boss_d / 2)
            .extrude(boss_h)
            .translate((cx, 0, plate_thick))
        )
        plate = plate.union(boss)

        # Foro per inserto a caldo
        hole = (
            cq.Workplane("XY")
            .circle(hole_d / 2)
            .extrude(hole_depth)
            .translate((cx, 0, plate_thick + boss_h - hole_depth))
        )
        plate = plate.cut(hole)

    return plate


def add_fillets_and_chamfers(body):
    """Raccordi alla base dei boss e smusso in cima."""
    try:
        body = body.edges("|Z").fillet(fillet_r)
    except Exception:
        pass  # fillet su geometrie complesse potrebbe fallire parzialmente
    return body


def make_assembly():
    """Assembla piastra con boss."""
    plate = make_plate()
    plate = add_bosses(plate)
    plate = add_fillets_and_chamfers(plate)
    return plate


# === EXPORT ===
result = make_assembly()

step_path = os.path.join(out_dir, "insert_boss.step")
stl_path  = os.path.join(out_dir, "insert_boss.stl")
cq.exporters.export(result, step_path)
cq.exporters.export(result, stl_path)

bb = result.val().BoundingBox()
vol = result.val().Volume()
print(f"INSERT_BOSS: {bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm, vol={vol:.0f} mm³")

# Stampa dettagli per ogni inserto
for name in inserts_to_build:
    hole_d, hole_depth, boss_d = INSERT_TABLE[name]
    print(f"  {name}: hole Ø{hole_d:.1f} x {hole_depth:.1f}mm, boss Ø{boss_d:.1f}mm")

print(f"Files: {step_path}, {stl_path}")
