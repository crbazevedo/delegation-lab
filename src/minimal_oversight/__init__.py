"""Minimal Oversight — governed-delegation analytics and decision-support toolkit.

Companion package to:
    "Minimal Oversight: A Theory of Principled Autonomy Delegation"
    Carlos R. B. Azevedo, 2026.

Quick start::

    from minimal_oversight import analyze_pipeline
    from minimal_oversight.models import PipelineGraph, Node

    graph = PipelineGraph(...)
    report = analyze_pipeline(graph, p_min=0.80)
    print(report)
"""

from minimal_oversight._api import analyze_pipeline, recommend_governance_changes

__version__ = "0.1.0"
__all__ = ["analyze_pipeline", "recommend_governance_changes"]
