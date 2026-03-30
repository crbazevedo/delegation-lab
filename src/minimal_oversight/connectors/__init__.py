"""Connectors: import pipelines from external frameworks.

Each connector translates a framework's native objects into the canonical
schema (schema.py), which is then converted to PipelineGraph for analysis.

Supported frameworks:
    - LangGraph (connectors.langgraph)
    - Google ADK (connectors.adk)
    - Trace formats (connectors.traces)
"""

from minimal_oversight.connectors._bridge import pipeline_from_normalized, traces_from_normalized

__all__ = ["pipeline_from_normalized", "traces_from_normalized"]
