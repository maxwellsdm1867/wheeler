"""Render the figure set for the kernel analysis."""

from pathlib import Path

FIGDIR = Path("figures")


def ensure_figdir() -> Path:
    FIGDIR.mkdir(exist_ok=True)
    return FIGDIR


def figure_names() -> list[str]:
    return ["fig01_counts.png", "fig02_kernel.png", "fig03_ci.png"]
