"""Reference Object Library — load relevant dimensions based on prompt keywords.

Scans the user prompt for keywords and returns matching reference categories
formatted as text to inject into the Claude prompt. Only loads relevant
categories, not the entire database.
"""
import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

DATA_FILE = Path(__file__).parent.parent / "data" / "reference_objects.json"

_db: dict | None = None


def _load_db() -> dict:
    global _db
    if _db is None:
        if not DATA_FILE.exists():
            log.warning("Reference database not found at %s", DATA_FILE)
            _db = {"categories": {}}
        else:
            _db = json.loads(DATA_FILE.read_text())
            total = sum(len(c["items"]) for c in _db.get("categories", {}).values())
            log.info("Loaded reference database: %d objects in %d categories",
                     total, len(_db.get("categories", {})))
    return _db


def find_matching_references(prompt: str, max_items_per_category: int = 15) -> str:
    """Find reference objects relevant to the prompt and format as text.

    Returns a formatted string with relevant reference dimensions,
    or empty string if no matches found.
    """
    db = _load_db()
    prompt_lower = prompt.lower()
    matches = []

    for cat_name, cat in db.get("categories", {}).items():
        keywords = cat.get("keywords", [])
        # Check if any keyword appears in the prompt
        matched_kws = [kw for kw in keywords if kw in prompt_lower]
        if not matched_kws:
            continue

        # Score by number of keyword matches
        items = cat["items"]

        # Limit items per category
        if len(items) > max_items_per_category:
            items = items[:max_items_per_category]

        if items:
            matches.append({
                "category": cat_name,
                "description": cat.get("description", ""),
                "score": len(matched_kws),
                "items": items,
            })

    if not matches:
        return ""

    # Sort by relevance score
    matches.sort(key=lambda m: m["score"], reverse=True)

    # Format as text
    lines = ["REFERENCE DIMENSIONS (from Reference Object Library — use these exact values):"]
    for m in matches:
        lines.append(f"\n### {m['description']}")
        for item in m["items"]:
            name = item.get("name", "")
            dims = _format_dims(item)
            lines.append(f"- {name}: {dims}")

    return "\n".join(lines)


def _format_dims(item: dict) -> str:
    """Format a reference item's dimensions as a compact string."""
    parts = []

    # Physical dimensions (L x W x H/T)
    if "length_mm" in item and "width_mm" in item:
        t_key = next((k for k in ["thickness_mm", "height_mm"] if k in item), None)
        if t_key:
            parts.append(f"{item['length_mm']} x {item['width_mm']} x {item[t_key]} mm")
        else:
            parts.append(f"{item['length_mm']} x {item['width_mm']} mm")
    elif "diameter_mm" in item:
        if "length_mm" in item:
            parts.append(f"dia {item['diameter_mm']} x {item['length_mm']} mm")
        elif "thickness_mm" in item:
            parts.append(f"dia {item['diameter_mm']} x {item['thickness_mm']} mm thick")
        else:
            parts.append(f"dia {item['diameter_mm']} mm")

    # Face size for motors
    if "face_mm" in item:
        parts.append(f"face {item['face_mm']}x{item['face_mm']} mm")

    # Bearing-specific
    if "inner_dia_mm" in item and "outer_dia_mm" in item:
        w = item.get("width_mm", item.get("length_mm", ""))
        parts.append(f"ID {item['inner_dia_mm']} x OD {item['outer_dia_mm']}"
                     + (f" x W {w} mm" if w else " mm"))

    # Fastener-specific
    if "thread_dia_mm" in item and "head_dia_mm" in item:
        parts.append(f"thread M{item['thread_dia_mm']}, head dia {item['head_dia_mm']}mm")
    if "through_hole_mm" in item:
        parts.append(f"through-hole: {item['through_hole_mm']}mm")
    if "pilot_hole_mm" in item:
        parts.append(f"pilot hole: {item['pilot_hole_mm']}mm, depth: {item.get('depth_mm', '?')}mm")
    if "across_flats_mm" in item:
        parts.append(f"AF {item['across_flats_mm']}mm, h {item.get('height_mm', '?')}mm")
    if "pocket_af_mm" in item:
        parts.append(f"pocket AF: {item['pocket_af_mm']}mm")

    # Connector-specific
    if "cutout_width_mm" in item:
        parts.append(f"cutout: {item['cutout_width_mm']}x{item.get('cutout_height_mm', '?')}mm")
    if "cutout_diameter_mm" in item:
        parts.append(f"cutout: dia {item['cutout_diameter_mm']}mm")

    # Mounting info
    if "mounting_holes" in item:
        parts.append(f"mounting: {item['mounting_holes']}")
    if "hole_pattern_mm" in item:
        parts.append(f"pattern: {item['hole_pattern_mm']}mm")
    if "bolt_pattern_mm" in item:
        parts.append(f"bolt pattern: {item['bolt_pattern_mm']}mm, {item.get('bolt_size', '')}")

    # Weight
    if "weight_g" in item:
        parts.append(f"{item['weight_g']}g")

    # Notes
    if "notes" in item:
        parts.append(item["notes"])

    # Enclosure defaults
    if "wall_mm" in item:
        parts.append(f"wall: {item['wall_mm']}mm")
    if "lip_mm" in item:
        parts.append(f"lip: {item['lip_mm']}mm")
    if "clearance_mm" in item:
        parts.append(f"clearance: {item['clearance_mm']}mm")

    return ", ".join(parts) if parts else json.dumps(item)
