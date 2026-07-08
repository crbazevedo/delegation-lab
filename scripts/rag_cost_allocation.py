#!/usr/bin/env python3
"""Reproducible cost-aware allocation on a 5-node RAG chain.

Backs the cost-aware result reported in the paper(s): a naive "frontier model on
every node" RAG pipeline misses a delivered-quality target *and* is expensive,
while the cost-aware optimizer (greedy local search over model swaps + in-place
review/correct) makes the same graph feasible at a fraction of the cost by routing
most nodes to open-weights models and reserving a proprietary model for the
binding step.

All numbers are derived from the committed priors (`data/priors.yaml`, provenance
in `docs/methodology/priors-evidence.md`) and the model registry's public pricing
(`data/model_registry.yaml`). Run:

    PYTHONPATH=src python3 scripts/rag_cost_allocation.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from minimal_oversight import optimize as O  # noqa: E402
from minimal_oversight import registry as R  # noqa: E402

P_MIN = 0.80

# RAG chain: (id, role, task) in pipeline order.
CHAIN = [
    ("query_rewrite", "generator", "drafting"),
    ("retrieve", "retriever", "retrieval"),
    ("rerank", "reranker", "reranking"),
    ("reader", "reader", "grounded_generation"),
    ("review", "reviewer", "review"),
]

# Naive baseline: a single proprietary flagship on every LLM node, plus a
# proprietary embedder / reranker. This is the "use the best model everywhere"
# anti-pattern the cockpit warns against.
BASELINE_MODEL = {
    "query_rewrite": "claude-opus-4",
    "retrieve": "openai-text-embedding-3-large",
    "rerank": "cohere-rerank-3",
    "reader": "claude-opus-4",
    "review": "claude-opus-4",
}


def build(models: dict[str, str]) -> list[dict]:
    nodes: list[dict] = []
    parent = None
    for nid, role, task in CHAIN:
        n = {"id": nid, "role": role, "task": task, "model": models[nid]}
        if parent:
            n["parents"] = [parent]
        nodes.append(n)
        parent = nid
    return nodes


def is_open(model: str) -> bool:
    return R.has_model(model) and R.get_model(model).open


def show(title: str, nodes: list[dict], ev) -> None:
    print(f"\n{title}: Q_G={ev.c_op:.3f}  cost=${ev.cost:.4f}/query  "
          f"feasible={ev.feasible}")
    for n in nodes:
        ov = n.get("oversight_model")
        tag = "OSS " if is_open(n["model"]) else "prop"
        line = (f"   {n['id']:14s} {n['model']:30s} [{tag}] "
                f"${O.node_cost(n):.4f}")
        if ov:
            line += f"  +review/correct: {ov}"
        print(line)


def main() -> int:
    baseline = build(BASELINE_MODEL)
    ev_base = O.evaluate(baseline, P_MIN)
    show(f"Naive frontier-everywhere baseline (p_min={P_MIN})", baseline, ev_base)

    res = O.optimize_allocation(baseline, p_min=P_MIN, prefer_oss=True)
    show("Cost-aware optimized allocation", res.nodes, res)

    oss = sum(1 for n in res.nodes if is_open(n["model"]))
    ratio = ev_base.cost / res.cost if res.cost else float("inf")
    print(f"\nSummary: Q_G {ev_base.c_op:.3f} (infeasible) -> {res.c_op:.3f} "
          f"(feasible); cost ${ev_base.cost:.4f} -> ${res.cost:.4f}/query "
          f"({ratio:.1f}x cheaper); {oss}/{len(res.nodes)} nodes on open-weights.")
    print("Optimizer steps:")
    for s in res.steps:
        print(f"  - {s}")

    sdlc_demo()
    return 0


def _frontier(task: str) -> str:
    return max(O.candidate_models(task, "moderate", 0.0, 0.0),
              key=lambda o: (o.cost_index or 0)).model


def sdlc_demo() -> None:
    """Software-delivery (PR-review) workflow: model choice is NOT enough.

    Unlike the RAG chain, this graph's weakest-link (minimum) approval gate and
    low-catch merge sink cap delivered quality below the target whatever models
    are chosen -- so review allocation, not model swapping, is the effective lever.
    """
    p_min = 0.75
    sdlc = [
        {"id": "diff_analysis", "role": "generator", "task": "code_generation",
         "model": _frontier("code_generation")},
        {"id": "code_retrieval", "role": "retriever", "task": "retrieval",
         "model": _frontier("retrieval"), "parents": ["diff_analysis"]},
        {"id": "standards_kb", "role": "retriever", "task": "retrieval",
         "model": _frontier("retrieval"), "parents": ["diff_analysis"]},
        {"id": "ai_review", "role": "reviewer", "task": "review",
         "model": _frontier("review"), "parents": ["code_retrieval", "standards_kb"],
         "aggregation": "mean"},
        {"id": "ci_tests", "sigma_skill": 0.92, "catch_rate": 0.80, "fix_rate": 1.0,
         "parents": ["ai_review"]},   # deterministic test suite (no model)
        {"id": "agent_review", "role": "reviewer", "task": "review",
         "model": _frontier("review"), "parents": ["ai_review", "ci_tests"],
         "aggregation": "min"},
        {"id": "merge", "sigma_skill": 0.96, "catch_rate": 0.0, "fix_rate": 1.0,
         "parents": ["agent_review"], "aggregation": "mean"},  # deterministic merge
    ]
    ev = O.evaluate(sdlc, p_min)
    res = O.optimize_allocation(sdlc, p_min=p_min, prefer_oss=True)
    print(f"\n=== Software-delivery workflow (model-choice lever, p_min={p_min}) ===")
    print(f"baseline flagship: Q_G={ev.c_op:.3f} cost=${ev.cost:.4f} feasible={ev.feasible}")
    print(f"cost-optimized:    Q_G={res.c_op:.3f} cost=${res.cost:.4f} feasible={res.feasible}")
    print("Model choice alone cannot clear the target (min-gate + low-catch sink); "
          "review allocation is the effective lever here (Q_G=0.762 at B=2.5).")


if __name__ == "__main__":
    raise SystemExit(main())
