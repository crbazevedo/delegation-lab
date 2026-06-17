"""Minimal Oversight — governed-delegation analytics for AI pipelines.

The package centers on the Minimum Sufficient Oversight Principle (MSO):
allocate the least sufficient oversight needed to meet a target quality
constraint, then place review where it is most informative.

Companion package to:
    "Minimal Oversight: Uncertainty-Aware Governance for Delegated AI Systems"
    Carlos R. B. Azevedo, 2026.

Quick start::

    from minimal_oversight import analyze_pipeline
    from minimal_oversight.models import PipelineGraph, Node

    graph = PipelineGraph(...)
    report = analyze_pipeline(graph, p_min=0.80)
    print(report)

Framework import::

    # LangGraph
    from minimal_oversight.connectors.langgraph import from_langgraph
    pipeline = from_langgraph(my_compiled_graph)

    # ADK
    from minimal_oversight.connectors.adk import from_adk_config
    pipeline = from_adk_config(agent_config_dict)

    # Or auto-detect:
    report = analyze_pipeline(my_langgraph_or_adk_object, p_min=0.80)
"""

from minimal_oversight._api import analyze_pipeline, recommend_governance_changes

__version__ = "0.1.3"
__all__ = ["analyze_pipeline", "recommend_governance_changes"]
