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
        r"\breview", r"\bcheck(?:er|ing|s)?\b", r"\bvalidat", r"\bverif",
        r"\baudit", r"\bquality\b", r"\bcorrect(?:or|ion|ing|s)?\b",
        r"\blint(?:er|ing|s)?\b", r"\btest(?:er|ing|s)?\b",
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

    Uses keyword matching. The node *name* is checked first (last matching
    component wins, since English compounds put the head noun last —
    "test_generator" is a generator, not a tester). If no role is found
    from the name alone, the description and framework_type are checked
    with first-match-wins.

    Returns UNKNOWN if no pattern matches.
    This is a heuristic — trace-based calibration is more reliable.
    """
    # --- Phase 1: classify from the node name (head-noun priority) ---
    name_text = name.lower().replace("_", " ").replace("-", " ")

    # HUMAN is a hard override — if the name contains "human", "hitl",
    # "escalat", etc., it's always a human node regardless of other keywords.
    for pattern in _ROLE_PATTERNS[0][1]:  # HUMAN is first in the list
        if re.search(pattern, name_text):
            return NodeRole.HUMAN

    # For all other roles, find ALL matching roles across name components;
    # keep the last match position so the head noun (rightmost) wins.
    # e.g. "test_generator" → "generator" wins over "test".
    best_role: NodeRole | None = None
    best_pos: int = -1
    for role, patterns in _ROLE_PATTERNS[1:]:  # skip HUMAN (handled above)
        for pattern in patterns:
            for m in re.finditer(pattern, name_text):
                if m.start() > best_pos:
                    best_pos = m.start()
                    best_role = role
    if best_role is not None:
        return best_role

    # --- Phase 2: fall back to description + framework_type (first match) ---
    desc_text = f"{description} {framework_type or ''}".lower()
    desc_text = desc_text.replace("_", " ").replace("-", " ")
    for role, patterns in _ROLE_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, desc_text):
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
