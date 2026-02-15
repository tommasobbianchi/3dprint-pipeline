"""Stub generator for end-to-end benchmark mode.

Replace the body of `generate()` with your actual pipeline
(e.g., call Claude API with spatial-reasoning + cadquery-codegen skills).
"""
from __future__ import annotations


def generate(prompt: str) -> str:
    """Generate CadQuery Python code from a text prompt.

    Args:
        prompt: Natural language description of the 3D object.

    Returns:
        Complete Python script string that produces output.step and output.stl.

    TODO: Connect to your actual pipeline (e.g., Anthropic API with skill prompts).
    """
    raise NotImplementedError(
        "End-to-end generation not yet connected. "
        "Implement generate() in tests/generate_cadquery.py "
        "or use --mode code-only to test with reference code."
    )
