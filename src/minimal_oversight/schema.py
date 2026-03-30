"""Canonical schema for framework-agnostic pipeline representation.

This is the stable internal contract between connectors and analytics.
Every connector translates its framework's native objects into these types.
The analytics layer never touches framework-specific objects directly.

Design principle: connectors are thin wrappers over this schema.
When frameworks change their APIs, only the connector breaks — not the analytics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeRole(Enum):
    """Inferred or declared role of a node in a delegation pipeline.

    Used to assign default parameter ranges when traces are not yet available.
    """

    GENERATOR = "generator"      # produces primary outputs
    REVIEWER = "reviewer"        # reviews/corrects another node's output
    ROUTER = "router"            # routes items to different branches
    GATE = "gate"                # merge/gate node that combines inputs
    TOOL = "tool"                # tool-calling node (search, API, etc.)
    HUMAN = "human"              # human-in-the-loop node
    UNKNOWN = "unknown"          # role not determined


class EventType(Enum):
    """Types of events in a normalized execution trace."""

    TASK_START = "task_start"
    TASK_END = "task_end"
    NODE_ENTER = "node_enter"
    NODE_EXIT = "node_exit"
    REVIEW_START = "review_start"
    REVIEW_END = "review_end"
    HANDOFF = "handoff"
    ESCALATION = "escalation"
    TOOL_CALL = "tool_call"
    ROUTING_DECISION = "routing_decision"
    HUMAN_INTERVENTION = "human_intervention"
    ERROR = "error"


class OutcomeType(Enum):
    """Outcome of a node's processing."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


@dataclass
class NormalizedNode:
    """A node in the canonical pipeline representation.

    Attributes:
        id: Unique identifier (from framework or generated).
        name: Human-readable name.
        role: Inferred or declared role.
        description: Agent description / system prompt summary.
        model: LLM model identifier if applicable.
        framework_type: Original type in the source framework.
        framework_metadata: Arbitrary framework-specific data preserved for debugging.
    """

    id: str
    name: str
    role: NodeRole = NodeRole.UNKNOWN
    description: str = ""
    model: str | None = None
    framework_type: str | None = None
    framework_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedEdge:
    """A directed edge in the canonical pipeline representation.

    Attributes:
        source_id: ID of the source node.
        target_id: ID of the target node.
        condition: Routing condition (if conditional edge).
        is_handoff: Whether this edge represents a delegation handoff.
        is_review: Whether this edge connects a node to its reviewer.
        framework_metadata: Framework-specific edge data.
    """

    source_id: str
    target_id: str
    condition: str | None = None
    is_handoff: bool = False
    is_review: bool = False
    framework_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedEvent:
    """A single event in a normalized execution trace.

    Attributes:
        event_type: What happened.
        node_id: Which node this event belongs to.
        timestamp: When it happened (seconds since trace start, or absolute).
        task_id: Which task/item this event belongs to.
        outcome: Outcome if this is an exit event.
        pre_correction: Whether this captures pre-correction state.
        post_correction: Whether this captures post-correction state.
        payload: Arbitrary event data (tool args, routing decision, etc.).
    """

    event_type: EventType
    node_id: str
    timestamp: float
    task_id: str = ""
    outcome: OutcomeType = OutcomeType.UNKNOWN
    pre_correction: bool = False
    post_correction: bool = False
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedOutcome:
    """Paired pre/post-correction outcome for a single task at a single node.

    This is the fundamental observation unit for estimation.
    """

    task_id: str
    node_id: str
    raw_outcome: float      # pre-correction: 1.0 = correct, 0.0 = error
    corrected_outcome: float  # post-correction
    was_reviewed: bool = False
    reviewer_id: str | None = None
    timestamp: float | None = None


@dataclass
class NormalizedTrace:
    """A complete normalized execution trace.

    Contains both the event stream (for process entropy estimation)
    and the paired outcomes (for sigma estimation).
    """

    trace_id: str
    events: list[NormalizedEvent] = field(default_factory=list)
    outcomes: list[NormalizedOutcome] = field(default_factory=list)
    framework_source: str = ""  # "langgraph", "adk", "crewai", etc.
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedPipeline:
    """A complete normalized pipeline definition.

    This is the canonical intermediate representation that connectors produce
    and that `analyze_pipeline()` consumes.
    """

    nodes: list[NormalizedNode]
    edges: list[NormalizedEdge]
    framework_source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def node_ids(self) -> list[str]:
        return [n.id for n in self.nodes]

    def get_node(self, node_id: str) -> NormalizedNode | None:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def children_of(self, node_id: str) -> list[str]:
        return [e.target_id for e in self.edges if e.source_id == node_id]

    def parents_of(self, node_id: str) -> list[str]:
        return [e.source_id for e in self.edges if e.target_id == node_id]


# ---------------------------------------------------------------------------
# Role inference defaults
# ---------------------------------------------------------------------------

# Default parameter ranges by role, from the paper's estimates.
# Used to bootstrap when traces are not yet available.
ROLE_DEFAULTS: dict[NodeRole, dict[str, float]] = {
    NodeRole.GENERATOR: {
        "sigma_skill": 0.55,
        "catch_rate": 0.65,
        "review_capacity": 0.50,
    },
    NodeRole.REVIEWER: {
        "sigma_skill": 0.60,
        "catch_rate": 0.75,
        "review_capacity": 0.70,
    },
    NodeRole.ROUTER: {
        "sigma_skill": 0.70,
        "catch_rate": 0.50,
        "review_capacity": 0.30,
    },
    NodeRole.GATE: {
        "sigma_skill": 0.55,
        "catch_rate": 0.65,
        "review_capacity": 0.50,
    },
    NodeRole.TOOL: {
        "sigma_skill": 0.80,
        "catch_rate": 0.50,
        "review_capacity": 0.30,
    },
    NodeRole.HUMAN: {
        "sigma_skill": 0.85,
        "catch_rate": 0.90,
        "review_capacity": 1.00,
    },
    NodeRole.UNKNOWN: {
        "sigma_skill": 0.55,
        "catch_rate": 0.65,
        "review_capacity": 0.50,
    },
}


def defaults_for_role(role: NodeRole) -> dict[str, float]:
    """Get default parameter estimates for a given node role."""
    return dict(ROLE_DEFAULTS.get(role, ROLE_DEFAULTS[NodeRole.UNKNOWN]))
