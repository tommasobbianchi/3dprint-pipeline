"""Geometric comparison metrics for CADPrompt benchmark.

Computes: Chamfer Distance, Bounding Box Similarity, Volume Ratio.
Trimesh is optional — if unavailable, geometric metrics return None.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import numpy as np
    import trimesh
    from scipy.spatial import cKDTree

    HAS_TRIMESH = True
except ImportError:
    HAS_TRIMESH = False
    logger.warning("trimesh/scipy not available — geometric metrics disabled")


@dataclass
class MetricsResult:
    """All metrics for a single test case."""

    chamfer_distance: Optional[float] = None
    bbox_similarity: Optional[float] = None
    volume_ratio: Optional[float] = None
    gt_volume: Optional[float] = None
    gen_volume: Optional[float] = None
    gt_bbox: Optional[list[float]] = None
    gen_bbox: Optional[list[float]] = None
    error: Optional[str] = None


def _load_mesh(path: Path) -> "trimesh.Trimesh":
    """Load an STL/OBJ file and return a single trimesh."""
    mesh = trimesh.load(path, force="mesh")
    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError(f"Expected single mesh, got {type(mesh).__name__}")
    return mesh


def _sample_points(mesh: "trimesh.Trimesh", n: int = 10_000) -> "np.ndarray":
    """Uniformly sample points on mesh surface."""
    points, _ = trimesh.sample.sample_surface(mesh, n)
    return points


def chamfer_distance(
    gt_path: Path, gen_path: Path, n_samples: int = 10_000, normalize: bool = True
) -> float:
    """Bidirectional Chamfer Distance between two meshes.

    Args:
        gt_path: Ground truth mesh file.
        gen_path: Generated mesh file.
        n_samples: Points to sample on each mesh.
        normalize: If True, divide by ground truth bounding box diagonal.

    Returns:
        Chamfer distance (lower is better). Normalized if requested.
    """
    if not HAS_TRIMESH:
        raise RuntimeError("trimesh required for chamfer_distance")

    gt_mesh = _load_mesh(gt_path)
    gen_mesh = _load_mesh(gen_path)

    pts_gt = _sample_points(gt_mesh, n_samples)
    pts_gen = _sample_points(gen_mesh, n_samples)

    tree_gt = cKDTree(pts_gt)
    tree_gen = cKDTree(pts_gen)

    dist_gen_to_gt, _ = tree_gt.query(pts_gen, k=1)
    dist_gt_to_gen, _ = tree_gen.query(pts_gt, k=1)

    cd = float(np.mean(dist_gen_to_gt**2) + np.mean(dist_gt_to_gen**2))

    if normalize:
        diag = float(np.linalg.norm(gt_mesh.bounds[1] - gt_mesh.bounds[0]))
        if diag > 1e-8:
            cd /= diag**2

    return cd


def bbox_similarity(gt_path: Path, gen_path: Path) -> tuple[float, list[float], list[float]]:
    """Bounding box dimension similarity.

    Returns:
        (score, gt_dims, gen_dims) where score in [0, 1] (1 = identical).
    """
    if not HAS_TRIMESH:
        raise RuntimeError("trimesh required for bbox_similarity")

    gt_mesh = _load_mesh(gt_path)
    gen_mesh = _load_mesh(gen_path)

    gt_dims = (gt_mesh.bounds[1] - gt_mesh.bounds[0]).tolist()
    gen_dims = (gen_mesh.bounds[1] - gen_mesh.bounds[0]).tolist()

    errors = []
    for g, p in zip(gt_dims, gen_dims):
        if abs(g) < 1e-8:
            errors.append(0.0 if abs(p) < 1e-8 else 1.0)
        else:
            errors.append(min(abs(g - p) / abs(g), 1.0))

    score = max(0.0, 1.0 - sum(errors) / len(errors))
    return score, gt_dims, gen_dims


def volume_ratio(gt_path: Path, gen_path: Path) -> tuple[float, float, float]:
    """Volume ratio between generated and ground truth meshes.

    Returns:
        (ratio, gt_vol, gen_vol). Ideal ratio = 1.0.
    """
    if not HAS_TRIMESH:
        raise RuntimeError("trimesh required for volume_ratio")

    gt_mesh = _load_mesh(gt_path)
    gen_mesh = _load_mesh(gen_path)

    gt_vol = abs(float(gt_mesh.volume)) if gt_mesh.is_watertight else 0.0
    gen_vol = abs(float(gen_mesh.volume)) if gen_mesh.is_watertight else 0.0

    if gt_vol < 1e-12:
        ratio = 0.0
    else:
        ratio = gen_vol / gt_vol

    return ratio, gt_vol, gen_vol


def compute_all_metrics(gt_path: Path, gen_path: Path) -> MetricsResult:
    """Compute all available geometric metrics.

    Returns MetricsResult with whatever metrics are computable.
    Never raises — errors stored in result.error.
    """
    result = MetricsResult()

    if not HAS_TRIMESH:
        result.error = "trimesh not available"
        return result

    if not gen_path.exists():
        result.error = f"Generated file not found: {gen_path}"
        return result

    if not gt_path.exists():
        result.error = f"Ground truth file not found: {gt_path}"
        return result

    try:
        result.chamfer_distance = chamfer_distance(gt_path, gen_path)
    except Exception as e:
        logger.warning("Chamfer distance failed for %s: %s", gen_path.name, e)

    try:
        score, gt_dims, gen_dims = bbox_similarity(gt_path, gen_path)
        result.bbox_similarity = score
        result.gt_bbox = gt_dims
        result.gen_bbox = gen_dims
    except Exception as e:
        logger.warning("BBox similarity failed for %s: %s", gen_path.name, e)

    try:
        ratio, gt_vol, gen_vol = volume_ratio(gt_path, gen_path)
        result.volume_ratio = ratio
        result.gt_volume = gt_vol
        result.gen_volume = gen_vol
    except Exception as e:
        logger.warning("Volume ratio failed for %s: %s", gen_path.name, e)

    return result
