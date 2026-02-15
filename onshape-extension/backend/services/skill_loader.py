"""Load SKILL.md files into the system prompt for Claude API calls."""
import sys
from pathlib import Path

from ..config import SKILL_FILES


def load_system_prompt() -> str:
    """Load and concatenate SKILL.md files into the system prompt."""
    parts = []
    for path in SKILL_FILES:
        if not path.exists():
            print(f"WARNING: Skill file not found: {path}", file=sys.stderr)
            continue
        content = path.read_text()
        # Strip frontmatter
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                content = content[end + 3:].strip()
        skill_name = path.parent.name
        parts.append(f"# === SKILL: {skill_name} ===\n\n{content}")
    return "\n\n---\n\n".join(parts)
