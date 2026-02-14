"""Snap-Fit Cantilever — Generato da Claude CLI
Modulo snap-fit cantilever parametrico per giunzioni a scatto.
Esportabile come parte singola da unire ad altri corpi.
Export: snap_fit in STEP e STL.
"""
import cadquery as cq
import math
import os

# === PARAMETRI PRINCIPALI ===
beam_length  = 12.0    # [mm] lunghezza braccio cantilever
beam_width   = 5.0     # [mm] larghezza braccio
beam_thick   = 1.2     # [mm] spessore braccio
lip_height   = 1.0     # [mm] altezza lip (sporgenza di aggancio)
lip_angle    = 30.0    # [deg] angolo rampa di inserimento

# === PARAMETRI DI STAMPA ===
base_width   = 8.0     # [mm] larghezza base di attacco
base_height  = 4.0     # [mm] altezza base di attacco
base_depth   = 3.0     # [mm] profondità base (spessore parete host)
fillet_r     = 0.5     # [mm] raccordo alla radice del cantilever

# === PARAMETRI DERIVATI ===
lip_ramp = lip_height / math.tan(math.radians(lip_angle))  # [mm] lunghezza rampa

# === OUTPUT ===
out_dir = os.path.dirname(os.path.abspath(__file__))


def make_base():
    """Blocco base di attacco alla parete."""
    base = (
        cq.Workplane("XY")
        .box(base_depth, base_width, base_height)
        .translate((base_depth / 2, 0, base_height / 2))
    )
    return base


def make_cantilever():
    """Braccio cantilever che si estende dalla base."""
    cantilever = (
        cq.Workplane("XY")
        .box(beam_length, beam_width, beam_thick)
        .translate((
            base_depth + beam_length / 2,
            0,
            base_height - beam_thick / 2,
        ))
    )
    return cantilever


def make_lip():
    """Lip di aggancio con rampa all'estremità del cantilever."""
    lip_x = base_depth + beam_length  # [mm] posizione X punta cantilever

    # Profilo lip nel piano XZ: rettangolo + rampa triangolare
    lip_profile = (
        cq.Workplane("XZ")
        .moveTo(lip_x, base_height - beam_thick)
        .lineTo(lip_x, base_height - beam_thick + lip_height)
        .lineTo(lip_x + lip_ramp, base_height - beam_thick)
        .close()
        .extrude(beam_width / 2, both=True)
    )

    # Parte verticale della lip
    lip_block = (
        cq.Workplane("XY")
        .box(beam_thick, beam_width, lip_height)
        .translate((
            lip_x - beam_thick / 2,
            0,
            base_height - beam_thick + lip_height / 2,
        ))
    )

    return lip_block.union(lip_profile)


def make_assembly():
    """Assembla il modulo snap-fit completo."""
    base = make_base()
    cantilever = make_cantilever()
    lip = make_lip()

    # Unione di tutte le parti
    snap = base.union(cantilever).union(lip)

    # Fillet alla radice del cantilever
    # Applicato sugli edge alla giunzione base-cantilever
    try:
        snap = snap.edges("|Y").fillet(fillet_r)
    except Exception:
        pass  # fillet potrebbe fallire su geometrie complesse

    return snap


# === EXPORT ===
result = make_assembly()

step_path = os.path.join(out_dir, "snap_fit.step")
stl_path  = os.path.join(out_dir, "snap_fit.stl")
cq.exporters.export(result, step_path)
cq.exporters.export(result, stl_path)

bb = result.val().BoundingBox()
vol = result.val().Volume()
print(f"SNAP_FIT: {bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm, vol={vol:.0f} mm³")
print(f"Files: {step_path}, {stl_path}")
