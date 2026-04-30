"""Configuration — environment variables and path resolution."""
import os
import shutil
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # 3dprint-pipeline/
SKILLS_DIR = PROJECT_ROOT / "skills"
MATERIALS_FILE = SKILLS_DIR / "print-profiles" / "materials.json"
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# SKILL.md files that form the system prompt
SKILL_FILES = [
    SKILLS_DIR / "spatial-reasoning" / "SKILL.md",
    SKILLS_DIR / "cadquery-codegen" / "SKILL.md",
]

# Claude CLI (uses Max subscription, no API key needed)
CLAUDE_CLI = os.environ.get("CLAUDE_CLI", shutil.which("claude") or "claude")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "sonnet")
CLAUDE_TIMEOUT = int(os.environ.get("CLAUDE_TIMEOUT", "120"))  # [s]

# CadQuery execution
EXEC_TIMEOUT = int(os.environ.get("EXEC_TIMEOUT", "60"))  # [s]

# Onshape API keys (loaded from file)
ONSHAPE_KEYS_FILE = Path(os.environ.get(
    "ONSHAPE_KEYS_FILE",
    Path.home() / ".config" / "onshape-cadgen" / "api-keys.txt",
))
ONSHAPE_API_BASE = os.environ.get("ONSHAPE_API_BASE", "https://cad.onshape.com/api/v6")

# Server
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8420"))
