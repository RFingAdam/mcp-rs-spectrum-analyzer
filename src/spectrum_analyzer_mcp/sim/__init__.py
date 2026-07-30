"""Offline spectrum analyzer simulator.

The engine is :mod:`scpi_core.sim`; everything analyzer-specific is the node map
in ``nodes/spectrum.yaml``. This package holds only that map and the console
script that preselects it, so ``spectrum-simulator`` needs no arguments to stand
in for a bench instrument.
"""

from pathlib import Path

#: Node map this server's simulator serves by default.
NODE_MAP = Path(__file__).parent / "nodes" / "spectrum.yaml"

__all__ = ["NODE_MAP"]
