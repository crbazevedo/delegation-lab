"""Role inference: classify node roles from descriptions and metadata.

Heuristic-based classification. Fragile by nature — traces are more reliable.
This bootstraps parameter estimates before trace data is available.
"""

from __future__ import annotations

import re

from minimal_oversight.schema import NodeRole

# Keyword patterns for role classification.
# Order matters: first match wins. More specific patterns first.
#
# The input text is normalized (underscores/hyphens replaced with spaces)
# before matching so \b boundaries work on snake_case and kebab-case names.
# The original \brout pattern was too broad (matched "about"); we now
# require more specific stems like router/routing/route.
_ROLE_PATTERNS: list[tuple[NodeRole, list[str]]] = [
    (NodeRole.HUMAN, [
        r"\bhuman\b", r"\bmanual\b",
        r"\bescalat", r"\boperator\b", r"\bhitl\b",
    ]),
    (NodeRole.ROUTER, [
        r"\brouter\b|\brouting\b|\broute[sd]?\b",
        r"\btriage", r"\bclassif", r"\bdispatch",
        r"\bswitch\b", r"\bbranch", r"\bcondition",
    ]),
    (NodeRole.REVIEWER, [
        r"\breview", r"\bcheck", r"\bvalidat", r"\bverif", r"\baudit",
        r"\bquality\b", r"\bcorrect", r"\blint", r"\btest",
        r"\bsecur", r"\bevaluat", r"\bjudge", r"\bgrade",
        r"\bscore", r"\bcritiqu", r"\bapprov",
    ]),
    (NodeRole.GATE, [
        r"\bmerge", r"\bgate\b", r"\baggregat", r"\bcombine", r"\bjoin\b",
        r"\bfinaliz", r"\bconsolid",
    ]),
    (NodeRole.TOOL, [
        r"\btool", r"\bsearch", r"\bapi\b", r"\bfetch",
        r"\bquery\b|\bquerying\b", r"\bretrieval\b|\bretriev",
        r"\blookup", r"\bweb\b", r"\bdatabase\b",
    ]),
    (NodeRole.GENERATOR, [
        r"\bgenerat", r"\bwrit", r"\bcreat", r"\bdraft", r"\bproduc",
        r"\bcompos", r"\bsynth", r"\bcod(?:e[rs]?|ing)\b",
        r"\brespond", r"\banswer", r"\bassist", r"\bagent\b",
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
    # Normalize underscores and hyphens to spaces so word-boundary patterns
    # work correctly on snake_case and kebab-case identifiers.
    text = text.replace("_", " ").replace("-", " ")

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
