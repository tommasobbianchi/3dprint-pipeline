# CADPrompt Benchmark Test Suite

Measures the accuracy of the 3D print pipeline against the **CADPrompt** dataset
(ICLR 2025, Alrashedy et al.) — 200 3D objects from DeepCAD with human-written
text descriptions, ground truth STLs, and reference CadQuery code.

Paper: [Generating CAD Code with Vision-Language Models for 3D Designs](https://openreview.net/pdf?id=BLWaTeucYX)

## Dataset

The CADPrompt dataset is in `cadprompt_repo/` (git-cloned from
[Kamel773/CAD_Code_Generation](https://github.com/Kamel773/CAD_Code_Generation)).

Each of the 200 samples contains:
- `Natural_Language_Descriptions_Prompt.txt` — short text prompt
- `Natural_Language_Descriptions_Prompt_with_specific_measurements.txt` — prompt with dimensions
- `Python_Code.py` — reference CadQuery code (expert-written)
- `Ground_Truth.stl` / `Ground_Truth.obj` — ground truth mesh
- `Ground_Truth.json` — ground truth geometric properties

Categories (from `Data_Stratification.xlsx`):
- **Mesh complexity**: Simple (99) / Complex (101)
- **Semantic complexity**: Simple (17) / Moderate (39) / Complex (87) / Very Complex (57)

## Quick Start

```bash
# Run on 5 samples with reference code
python tests/run_benchmark.py --mode code-only --limit 5

# Run all simple samples
python tests/run_benchmark.py --mode code-only --category simple

# Run specific samples
python tests/run_benchmark.py --mode code-only --ids 00000007,00031303

# Run with longer timeout
python tests/run_benchmark.py --mode code-only --timeout 60
```

## Modes

### code-only (default)
Executes the reference `Python_Code.py` from each sample. Validates that the
dataset code runs correctly under our CadQuery environment and computes geometric
metrics against the ground truth STL.

### end-to-end
Passes the text prompt to `generate_cadquery.py` (stub). Edit that file to connect
your actual pipeline (e.g., Claude API with cadquery-codegen skills).

```bash
python tests/run_benchmark.py --mode end-to-end --limit 10
```

## Metrics

| Metric | Description | Ideal |
|--------|-------------|-------|
| **Invalid Rate (IR)** | % of scripts that fail to execute | 0% |
| **Chamfer Distance (CD)** | Surface distance between generated and ground truth mesh (normalized by GT bbox diagonal) | 0.0 |
| **BBox Similarity** | Bounding box dimension match (1 - mean relative error per axis) | 100% |
| **Volume Ratio** | Generated volume / ground truth volume | 1.0 |

Chamfer Distance uses 10,000 surface samples per mesh. Requires `trimesh` and `scipy`.

## Output Structure

```
tests/
├── results/
│   └── YYYYMMDD_HHMMSS/     # per-run directory
│       ├── summary.json       # aggregate metrics
│       ├── 00000007/
│       │   ├── code.py        # executed script (with export redirect)
│       │   ├── result.json    # per-sample metrics
│       │   ├── output.stl     # generated mesh
│       │   └── output.step    # generated CAD solid
│       └── ...
└── reports/
    └── report_YYYYMMDD_HHMMSS.md  # markdown report
```

## Dependencies

```bash
pip install trimesh numpy scipy openpyxl
```

CadQuery must be installed (`cadquery` package).
If `trimesh` is unavailable, geometric metrics (CD, BBox, Volume) are skipped —
only execution success/failure is reported.
