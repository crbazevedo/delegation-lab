"""Role inference: classify node roles from descriptions and metadata.

Heuristic-based classification. Fragile by nature — traces are more reliable.
This bootstraps parameter estimates before trace data is available.
"""

from __future__ import annotations

import re

from minimal_oversight.schema import NodeRole

# Keyword patterns for role classification.
# Order matters: first match wins. More specific patterns first.
_ROLE_PATTERNS: list[tuple[NodeRole, list[str]]] = [
    (NodeRole.HUMAN, [
        r"human", r"\bmanual\b", r"\bescalat", r"\boperator\b",
        r"\bhitl\b",
    ]),
    (NodeRole.ROUTER, [
        r"\brout", r"\btriage", r"\bclassif", r"\bdispatch", r"\bselect",
        r"\bswitch", r"\bbranch", r"\bcondition",
    ]),
    (NodeRole.REVIEWER, [
        r"\breview", r"\bcheck", r"\bvalidat", r"\bverif", r"\baudit",
        r"\bquality", r"\bcorrect", r"\blint", r"\btest", r"\bsecur",
        r"\beval", r"\bjudge", r"\bgrade", r"\bscore", r"\bcritiqu",
        r"\bapprov",
    ]),
    (NodeRole.GATE, [
        r"\bmerge", r"\bgate\b", r"\baggregat", r"\bcombine", r"\bjoin\b",
        r"\bfinal", r"\bconsolid",
    ]),
    (NodeRole.TOOL, [
        r"\btool", r"\bsearch", r"\bapi\b", r"\bfetch", r"\bquery",
        r"\bretrie", r"\blookup", r"\bweb\b", r"\bdatabase\b",
    ]),
    (NodeRole.GENERATOR, [
        r"\bgenerat", r"\bwrite", r"\bcreat", r"\bdraft", r"\bproduc",
        r"\bcompos", r"\bsynth", r"\bcode", r"\brespond", r"\banswer",
        r"\bassist", r"\bagent\b",
    ]),
]


def infer_role(
    name: str,
    description: str = "",
    framework_type: str | None = None,
) -> NodeRole:
    """Infer a node's role from its name, description, and framework type.

    Uses keyword matching. Returns UNKNOWN if no pattern matches.
    This is a heuristic — trace-based calibration is more reliable.
    """
    text = f"{name} {description} {framework_type or ''}".lower()

    for role, patterns in _ROLE_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, text):
                return role

    return NodeRole.UNKNOWN


def infer_review_edges(
    nodes: list[tuple[str, NodeRole]],
    edges: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    """Identify which edges represent review relationships.

    A review edge is one where the target has a REVIEWER role and the
    source has a GENERATOR role.
    """
    role_map = dict(nodes)
    review_edges = []
    for src, tgt in edges:
        src_role = role_map.get(src, NodeRole.UNKNOWN)
        tgt_role = role_map.get(tgt, NodeRole.UNKNOWN)
        if tgt_role == NodeRole.REVIEWER and src_role == NodeRole.GENERATOR:
            review_edges.append((src, tgt))
    return review_edges
