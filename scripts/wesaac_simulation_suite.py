#!/usr/bin/env python3
"""Paper-facing simulation suite for the WESAAC submission.

The suite is intentionally small and explicit. It applies the paper's equations
to concrete workflow graphs, compares oversight-allocation policies under the
same budget, and writes artifacts that can be cited from the paper:

* allocation_benchmark.csv: policy quality across motifs and budgets
* random_dag_benchmark.csv: robustness over randomized workflow DAGs
* trace_identifiability.csv: dual-channel vs corrected-only estimation
* software_delivery_case.csv: cockpit-like SDLC workflow interventions
* summary.md: paper-ready findings
* PNG plots for the main curves

Run from the repository root:
    python3 scripts/wesaac_simulation_suite.py
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from minimal_oversight import _formulae as F  # noqa: E402

try:  # pragma: no cover - optional visualization dependency
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    MPL_AVAILABLE = True
except Exception:  # pragma: no cover
    MPL_AVAILABLE = False
    plt = None  # type: ignore[assignment]


ETA = 10.0
DELTA = 2.0
SIGMA0 = 0.0
P_MIN = 0.70
STEP = 0.05


@dataclass(frozen=True)
class NodeSpec:
    node_id: str
    skill: float
    catch: float
    parents: tuple[str, ...] = ()
    aggregation: str = "product"
    role: str = "agent"


@dataclass(frozen=True)
class WorkflowSpec:
    name: str
    nodes: tuple[NodeSpec, ...]
    p_min: float = P_MIN


@dataclass
class EvalResult:
    quality: float
    raw: dict[str, float]
    corr: dict[str, float]
    sink_quality: dict[str, float]
    bottleneck: str


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def topo_order(workflow: WorkflowSpec) -> list[str]:
    nodes = {n.node_id: n for n in workflow.nodes}
    indeg = {n.node_id: len(n.parents) for n in workflow.nodes}
    children: dict[str, list[str]] = {n.node_id: [] for n in workflow.nodes}
    for node in workflow.nodes:
        for parent in node.parents:
            children[parent].append(node.node_id)

    ready = sorted([node_id for node_id, deg in indeg.items() if deg == 0])
    order: list[str] = []
    while ready:
        node_id = ready.pop(0)
        order.append(node_id)
        for child in sorted(children[node_id]):
            indeg[child] -= 1
            if indeg[child] == 0:
                ready.append(child)
                ready.sort()
    if len(order) != len(nodes):
        raise ValueError(f"workflow is cyclic or disconnected from topo sort: {workflow.name}")
    return order


def sinks(workflow: WorkflowSpec) -> list[str]:
    parents = {p for node in workflow.nodes for p in node.parents}
    return [node.node_id for node in workflow.nodes if node.node_id not in parents]


def descendants(workflow: WorkflowSpec, node_id: str) -> set[str]:
    children: dict[str, list[str]] = {n.node_id: [] for n in workflow.nodes}
    for node in workflow.nodes:
        for parent in node.parents:
            children[parent].append(node.node_id)

    seen: set[str] = set()
    stack = list(children[node_id])
    while stack:
        item = stack.pop()
        if item in seen:
            continue
        seen.add(item)
        stack.extend(children[item])
    return seen


def aggregate(values: list[float], mode: str) -> float:
    if not values:
        return 1.0
    if mode == "min":
        return min(values)
    if mode == "mean":
        return sum(values) / len(values)
    if mode == "product":
        out = 1.0
        for value in values:
            out *= value
        return out
    raise ValueError(f"unknown aggregation mode: {mode!r}")


def evaluate(workflow: WorkflowSpec, budgets: dict[str, float]) -> EvalResult:
    by_id = {node.node_id: node for node in workflow.nodes}
    raw: dict[str, float] = {}
    corr: dict[str, float] = {}

    for node_id in topo_order(workflow):
        node = by_id[node_id]
        parent_corr = [corr[parent] for parent in node.parents]
        skill_eff = node.skill * aggregate(parent_corr, node.aggregation)
        sigma_raw = F.sigma_raw_fixed_point(skill_eff, ETA, DELTA, sigma_0=SIGMA0)
        review_budget = clamp(budgets.get(node_id, 0.0))
        sigma_corr = F.sigma_corr_fixed_point(sigma_raw, node.catch * review_budget, 1.0)
        raw[node_id] = sigma_raw
        corr[node_id] = sigma_corr

    sink_quality = {sink: corr[sink] for sink in sinks(workflow)}
    bottleneck = min(sink_quality, key=sink_quality.get)
    return EvalResult(
        quality=sink_quality[bottleneck],
        raw=raw,
        corr=corr,
        sink_quality=sink_quality,
        bottleneck=bottleneck,
    )


def empty_budget(workflow: WorkflowSpec) -> dict[str, float]:
    return {node.node_id: 0.0 for node in workflow.nodes}


def spend_budget(
    workflow: WorkflowSpec,
    total_budget: float,
    chooser,
    step: float = STEP,
    seed: int = 1,
) -> dict[str, float]:
    rng = random.Random(seed)
    budgets = empty_budget(workflow)
    remaining = max(0.0, total_budget)

    while remaining > 1e-9:
        inc = min(step, remaining)
        candidates = [
            node.node_id
            for node in workflow.nodes
            if budgets[node.node_id] < 1.0 - 1e-9
        ]
        if not candidates:
            break
        chosen = chooser(workflow, budgets, candidates, rng)
        budgets[chosen] = clamp(budgets[chosen] + inc)
        remaining -= inc
    return budgets


def allocate_uniform(workflow: WorkflowSpec, total_budget: float) -> dict[str, float]:
    budgets = empty_budget(workflow)
    nodes = [node.node_id for node in workflow.nodes]
    remaining = max(0.0, total_budget)
    while remaining > 1e-9:
        open_nodes = [node_id for node_id in nodes if budgets[node_id] < 1.0 - 1e-9]
        if not open_nodes:
            break
        inc = min(remaining / len(open_nodes), min(1.0 - budgets[n] for n in open_nodes))
        for node_id in open_nodes:
            budgets[node_id] = clamp(budgets[node_id] + inc)
            remaining -= inc
    return budgets


def allocate_ranked(workflow: WorkflowSpec, total_budget: float, ranking: list[str]) -> dict[str, float]:
    budgets = empty_budget(workflow)
    remaining = max(0.0, total_budget)
    for node_id in ranking:
        if remaining <= 1e-9:
            break
        inc = min(1.0, remaining)
        budgets[node_id] = inc
        remaining -= inc
    return budgets


def choose_mso_marginal(
    workflow: WorkflowSpec,
    budgets: dict[str, float],
    candidates: list[str],
    _rng: random.Random,
) -> str:
    base = evaluate(workflow, budgets).quality
    best: tuple[float, float, str] | None = None
    for node_id in candidates:
        trial = dict(budgets)
        trial[node_id] = clamp(trial[node_id] + STEP)
        result = evaluate(workflow, trial)
        # Gain is primary; lower raw competence is a deterministic tie-breaker.
        score = (result.quality - base, 1.0 - result.raw[node_id], node_id)
        if best is None or score > best:
            best = score
    if best is None:
        raise RuntimeError("no candidate for marginal allocation")
    return best[2]


def choose_weakest_raw(
    workflow: WorkflowSpec,
    budgets: dict[str, float],
    candidates: list[str],
    _rng: random.Random,
) -> str:
    result = evaluate(workflow, budgets)
    return min(candidates, key=lambda node_id: (result.raw[node_id], node_id))


def choose_corrected_only(
    workflow: WorkflowSpec,
    budgets: dict[str, float],
    candidates: list[str],
    _rng: random.Random,
) -> str:
    result = evaluate(workflow, budgets)
    return min(candidates, key=lambda node_id: (result.corr[node_id], node_id))


def choose_random(
    _workflow: WorkflowSpec,
    _budgets: dict[str, float],
    candidates: list[str],
    rng: random.Random,
) -> str:
    return rng.choice(candidates)


def policy_budget(workflow: WorkflowSpec, policy: str, total_budget: float, seed: int = 1) -> dict[str, float]:
    if policy == "mso_marginal":
        return spend_budget(workflow, total_budget, choose_mso_marginal, seed=seed)
    if policy == "uniform":
        return allocate_uniform(workflow, total_budget)
    if policy == "weakest_raw":
        return spend_budget(workflow, total_budget, choose_weakest_raw, seed=seed)
    if policy == "corrected_only":
        return spend_budget(workflow, total_budget, choose_corrected_only, seed=seed)
    if policy == "degree_first":
        ranking = sorted(
            [node.node_id for node in workflow.nodes],
            key=lambda node_id: (len(descendants(workflow, node_id)), node_id),
            reverse=True,
        )
        return allocate_ranked(workflow, total_budget, ranking)
    if policy == "random":
        return spend_budget(workflow, total_budget, choose_random, seed=seed)
    raise ValueError(f"unknown policy: {policy!r}")


def canonical_workflows() -> list[WorkflowSpec]:
    return [
        WorkflowSpec(
            "chain_3",
            (
                NodeSpec("a", 0.68, 0.62),
                NodeSpec("b", 0.62, 0.68, ("a",)),
                NodeSpec("c", 0.58, 0.72, ("b",)),
            ),
            p_min=0.62,
        ),
        WorkflowSpec(
            "fanout_merge",
            (
                NodeSpec("source", 0.66, 0.72),
                NodeSpec("test", 0.72, 0.58, ("source",)),
                NodeSpec("security", 0.60, 0.70, ("source",)),
                NodeSpec("requirements", 0.64, 0.62, ("source",)),
                NodeSpec("merge", 0.82, 0.55, ("test", "security", "requirements"), "mean"),
            ),
            p_min=0.66,
        ),
        WorkflowSpec(
            "diamond_product",
            (
                NodeSpec("source", 0.72, 0.70),
                NodeSpec("branch_a", 0.64, 0.65, ("source",)),
                NodeSpec("branch_b", 0.64, 0.65, ("source",)),
                NodeSpec("merge", 0.78, 0.60, ("branch_a", "branch_b"), "product"),
            ),
            p_min=0.60,
        ),
        WorkflowSpec(
            "merge_3_product",
            (
                NodeSpec("retrieval", 0.72, 0.60),
                NodeSpec("tool", 0.62, 0.72),
                NodeSpec("policy", 0.68, 0.55),
                NodeSpec("delegate", 0.80, 0.62, ("retrieval", "tool", "policy"), "product"),
            ),
            p_min=0.55,
        ),
        software_delivery_workflow(),
    ]


def software_delivery_workflow() -> WorkflowSpec:
    return WorkflowSpec(
        "software_delivery",
        (
            NodeSpec("diff_analysis", 0.72, 0.55, role="analysis"),
            NodeSpec("code_retrieval", 0.78, 0.50, ("diff_analysis",), "mean", role="retrieval"),
            NodeSpec("standards_kb", 0.82, 0.45, ("diff_analysis",), "mean", role="retrieval"),
            NodeSpec(
                "ai_review",
                0.74,
                0.72,
                ("code_retrieval", "standards_kb"),
                "mean",
                role="review",
            ),
            NodeSpec("ci_tests", 0.84, 0.80, ("ai_review",), "mean", role="test"),
            NodeSpec("agent_review", 0.92, 0.70, ("ai_review", "ci_tests"), "min", role="review"),
            NodeSpec("merge", 0.96, 0.35, ("agent_review",), "mean", role="gate"),
        ),
        p_min=0.75,
    )


def random_workflow(seed: int, n_nodes: int = 7) -> WorkflowSpec:
    rng = random.Random(seed)
    nodes: list[NodeSpec] = []
    for i in range(n_nodes):
        node_id = f"n{i}"
        skill = rng.uniform(0.52, 0.86)
        catch = rng.uniform(0.45, 0.82)
        if i == 0:
            parents: tuple[str, ...] = ()
        else:
            parent_count = rng.choice([1, 1, 2, 2, 3 if i >= 3 else 1])
            parent_count = min(parent_count, i)
            parents = tuple(sorted(rng.sample([f"n{j}" for j in range(i)], parent_count)))
        aggregation = rng.choice(["product", "mean", "min"]) if len(parents) > 1 else "product"
        nodes.append(NodeSpec(node_id, skill, catch, parents, aggregation))
    return WorkflowSpec(f"random_{seed:03d}", tuple(nodes), p_min=0.64)


def run_allocation_benchmark(outdir: Path) -> list[dict[str, object]]:
    policies = ["mso_marginal", "uniform", "weakest_raw", "corrected_only", "degree_first", "random"]
    budgets = [round(x, 2) for x in np.arange(0.0, 2.51, 0.25)]
    rows: list[dict[str, object]] = []

    for workflow in canonical_workflows():
        for total_budget in budgets:
            for policy in policies:
                qualities = []
                budget_vectors = []
                seeds = range(1, 21) if policy == "random" else [1]
                for seed in seeds:
                    allocated = policy_budget(workflow, policy, total_budget, seed=seed)
                    result = evaluate(workflow, allocated)
                    qualities.append(result.quality)
                    budget_vectors.append(allocated)
                allocated_first = budget_vectors[0]
                rows.append(
                    {
                        "workflow": workflow.name,
                        "policy": policy,
                        "budget": total_budget,
                        "p_min": workflow.p_min,
                        "quality_mean": mean(qualities),
                        "quality_sd": pstdev(qualities) if len(qualities) > 1 else 0.0,
                        "feasible_rate": sum(q >= workflow.p_min for q in qualities) / len(qualities),
                        "bottleneck": evaluate(workflow, allocated_first).bottleneck,
                        "allocation": json.dumps(allocated_first, sort_keys=True),
                    }
                )

    write_csv(outdir / "allocation_benchmark.csv", rows)
    return rows


def run_random_dag_benchmark(outdir: Path) -> list[dict[str, object]]:
    policies = ["mso_marginal", "uniform", "weakest_raw", "corrected_only", "degree_first", "random"]
    total_budget = 1.50
    rows: list[dict[str, object]] = []

    for seed in range(1, 101):
        workflow = random_workflow(seed)
        quality_by_policy: dict[str, float] = {}
        for policy in policies:
            if policy == "random":
                qualities = [
                    evaluate(workflow, policy_budget(workflow, policy, total_budget, seed=1000 + seed * 37 + i)).quality
                    for i in range(10)
                ]
                quality = mean(qualities)
            else:
                quality = evaluate(workflow, policy_budget(workflow, policy, total_budget, seed=seed)).quality
            quality_by_policy[policy] = quality

        best = max(quality_by_policy.values())
        for policy, quality in quality_by_policy.items():
            rows.append(
                {
                    "seed": seed,
                    "workflow": workflow.name,
                    "policy": policy,
                    "budget": total_budget,
                    "quality": quality,
                    "regret_vs_best": best - quality,
                    "feasible": quality >= workflow.p_min,
                }
            )

    write_csv(outdir / "random_dag_benchmark.csv", rows)
    return rows


def run_trace_identifiability(outdir: Path) -> list[dict[str, object]]:
    rng = np.random.default_rng(7)
    scenarios = [
        ("high_skill_low_review", 0.78, 0.20, 0.30),
        ("low_skill_high_review", 0.50, 0.86, 0.85),
        ("medium_skill_medium_review", 0.63, 0.55, 0.60),
    ]
    rows: list[dict[str, object]] = []
    n = 800

    for name, skill, catch, budget in scenarios:
        sigma_raw = F.sigma_raw_fixed_point(skill, ETA, DELTA, sigma_0=SIGMA0)
        sigma_corr = F.sigma_corr_fixed_point(sigma_raw, catch * budget, 1.0)
        for rep in range(100):
            raw_obs = rng.random(n) < sigma_raw
            repaired = (~raw_obs) & (rng.random(n) < catch * budget)
            corr_obs = raw_obs | repaired
            raw_hat = float(np.mean(raw_obs))
            corr_hat = float(np.mean(corr_obs))
            inferred_catch_if_single_signal = max(0.0, (corr_hat - raw_hat) / max(1.0 - raw_hat, 1e-9))
            rows.append(
                {
                    "scenario": name,
                    "rep": rep,
                    "true_skill": skill,
                    "true_raw": sigma_raw,
                    "true_corr": sigma_corr,
                    "raw_hat_dual": raw_hat,
                    "corr_hat": corr_hat,
                    "single_signal_value": corr_hat,
                    "effective_catch_hat_dual": inferred_catch_if_single_signal,
                    "raw_error_dual": abs(raw_hat - sigma_raw),
                    "raw_error_if_corr_used": abs(corr_hat - sigma_raw),
                }
            )

    write_csv(outdir / "trace_identifiability.csv", rows)
    return rows


def run_software_delivery_case(outdir: Path) -> list[dict[str, object]]:
    workflow = software_delivery_workflow()
    interventions = {
        "no_extra_review": {},
        "final_merge_review": {"merge": 1.0},
        "ai_review_review": {"ai_review": 1.0},
        "retrieval_review": {"code_retrieval": 1.0},
        "ci_review": {"ci_tests": 1.0},
        "mso_budget_1": policy_budget(workflow, "mso_marginal", 1.0),
        "mso_budget_2": policy_budget(workflow, "mso_marginal", 2.0),
        "mso_budget_2_5": policy_budget(workflow, "mso_marginal", 2.5),
        "uniform_budget_2": policy_budget(workflow, "uniform", 2.0),
    }

    rows: list[dict[str, object]] = []
    base = evaluate(workflow, empty_budget(workflow))
    for name, budget in interventions.items():
        budgets = empty_budget(workflow)
        budgets.update(budget)
        result = evaluate(workflow, budgets)
        for node in workflow.nodes:
            rows.append(
                {
                    "intervention": name,
                    "node": node.node_id,
                    "role": node.role,
                    "budget": budgets[node.node_id],
                    "raw": result.raw[node.node_id],
                    "corrected": result.corr[node.node_id],
                    "workflow_quality": result.quality,
                    "delta_vs_base": result.quality - base.quality,
                    "bottleneck": result.bottleneck,
                    "p_min": workflow.p_min,
                    "feasible": result.quality >= workflow.p_min,
                }
            )

    write_csv(outdir / "software_delivery_case.csv", rows)
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def summarize_allocation(rows: list[dict[str, object]]) -> dict[str, dict[str, float]]:
    by_policy: dict[str, list[float]] = {}
    for row in rows:
        if float(row["budget"]) == 1.50:
            by_policy.setdefault(str(row["policy"]), []).append(float(row["quality_mean"]))
    return {
        policy: {
            "mean_quality": mean(values),
            "sd_quality": pstdev(values) if len(values) > 1 else 0.0,
        }
        for policy, values in sorted(by_policy.items())
    }


def summarize_budget_to_target(rows: list[dict[str, object]]) -> dict[str, dict[str, float | None]]:
    by_workflow_policy: dict[tuple[str, str], list[dict[str, object]]] = {}
    for row in rows:
        key = (str(row["workflow"]), str(row["policy"]))
        by_workflow_policy.setdefault(key, []).append(row)

    out: dict[str, dict[str, float | None]] = {}
    for (workflow, policy), items in by_workflow_policy.items():
        items.sort(key=lambda row: float(row["budget"]))
        hit = next((row for row in items if float(row["feasible_rate"]) >= 0.5), None)
        out.setdefault(workflow, {})[policy] = None if hit is None else float(hit["budget"])
    return out


def summarize_random(rows: list[dict[str, object]]) -> dict[str, dict[str, float]]:
    by_policy: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        by_policy.setdefault(str(row["policy"]), []).append(row)
    return {
        policy: {
            "mean_quality": mean(float(row["quality"]) for row in items),
            "mean_regret": mean(float(row["regret_vs_best"]) for row in items),
            "feasible_rate": mean(1.0 if row["feasible"] else 0.0 for row in items),
        }
        for policy, items in sorted(by_policy.items())
    }


def summarize_identifiability(rows: list[dict[str, object]]) -> dict[str, dict[str, float]]:
    by_scenario: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        by_scenario.setdefault(str(row["scenario"]), []).append(row)
    return {
        scenario: {
            "raw_error_dual": mean(float(row["raw_error_dual"]) for row in items),
            "raw_error_if_corr_used": mean(float(row["raw_error_if_corr_used"]) for row in items),
            "error_ratio": mean(float(row["raw_error_if_corr_used"]) for row in items)
            / max(mean(float(row["raw_error_dual"]) for row in items), 1e-9),
        }
        for scenario, items in sorted(by_scenario.items())
    }


def summarize_software(rows: list[dict[str, object]]) -> dict[str, dict[str, float | str]]:
    by_intervention: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        by_intervention.setdefault(str(row["intervention"]), []).append(row)
    out: dict[str, dict[str, float | str]] = {}
    for intervention, items in sorted(by_intervention.items()):
        first = items[0]
        out[intervention] = {
            "quality": float(first["workflow_quality"]),
            "delta_vs_base": float(first["delta_vs_base"]),
            "bottleneck": str(first["bottleneck"]),
            "feasible": 1.0 if first["feasible"] else 0.0,
        }
    return out


def make_plots(outdir: Path, allocation_rows: list[dict[str, object]], random_rows: list[dict[str, object]]) -> None:
    if not MPL_AVAILABLE:
        return

    workflows = sorted({str(row["workflow"]) for row in allocation_rows})
    policies = ["mso_marginal", "uniform", "weakest_raw", "corrected_only", "degree_first", "random"]

    # Human-readable display names so plot titles/legends never leak raw ids.
    workflow_display = {
        "chain_3": "Chain (depth 3)",
        "diamond_product": "Diamond (product merge)",
        "fanout_merge": "Fan-out / merge motif",
        "merge_3_product": "Ternary product merge",
        "software_delivery": "Software-delivery workflow",
    }
    policy_display = {
        "mso_marginal": "MSO marginal",
        "uniform": "Uniform",
        "weakest_raw": "Weakest raw",
        "corrected_only": "Corrected-only",
        "degree_first": "Degree-first",
        "random": "Random",
    }

    for workflow in workflows:
        fig, ax = plt.subplots(figsize=(8.4, 5.0))
        for policy in policies:
            subset = [
                row for row in allocation_rows
                if row["workflow"] == workflow and row["policy"] == policy
            ]
            subset.sort(key=lambda row: float(row["budget"]))
            ax.plot(
                [float(row["budget"]) for row in subset],
                [float(row["quality_mean"]) for row in subset],
                linewidth=2,
                label=policy_display.get(policy, policy),
            )
        p_min = float(next(row["p_min"] for row in allocation_rows if row["workflow"] == workflow))
        ax.axhline(p_min, color="0.4", linestyle="--", linewidth=1, label=r"target $p_\mathrm{min}$")
        ax.set_title(f"Allocation benchmark: {workflow_display.get(workflow, workflow)}")
        ax.set_xlabel("total review budget $B$")
        ax.set_ylabel("delivered workflow quality $Q_G$")
        ax.set_ylim(0.0, 1.02)
        ax.legend(frameon=False, fontsize=8)
        fig.tight_layout()
        fig.savefig(outdir / f"allocation_{workflow}.png", dpi=200)
        plt.close(fig)

    random_summary = summarize_random(random_rows)
    labels = list(random_summary)
    regrets = [random_summary[label]["mean_regret"] for label in labels]
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    ax.bar([policy_display.get(label, label) for label in labels], regrets, color="#4c78a8")
    ax.set_ylabel("mean regret vs. best per-graph policy")
    ax.set_title("Random-DAG robustness: lower regret is better")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    fig.savefig(outdir / "random_dag_regret.png", dpi=200)
    plt.close(fig)


def write_summary(
    outdir: Path,
    allocation_rows: list[dict[str, object]],
    random_rows: list[dict[str, object]],
    ident_rows: list[dict[str, object]],
    software_rows: list[dict[str, object]],
) -> None:
    allocation_summary = summarize_allocation(allocation_rows)
    budget_to_target = summarize_budget_to_target(allocation_rows)
    random_summary = summarize_random(random_rows)
    ident_summary = summarize_identifiability(ident_rows)
    software_summary = summarize_software(software_rows)

    best_random = min(random_summary, key=lambda p: random_summary[p]["mean_regret"])
    best_software = max(software_summary, key=lambda p: float(software_summary[p]["quality"]))

    lines = [
        "# WESAAC Simulation Suite Summary",
        "",
        "## Allocation Benchmark at Budget 1.50",
        "",
        "| Policy | Mean quality | SD |",
        "|---|---:|---:|",
    ]
    for policy, item in allocation_summary.items():
        lines.append(f"| {policy} | {item['mean_quality']:.3f} | {item['sd_quality']:.3f} |")

    lines.extend([
        "",
        "## Minimum Budget to Reach Target",
        "",
        "| Workflow | MSO marginal | Uniform | Weakest raw | Corrected-only | Degree-first | Random |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for workflow, item in sorted(budget_to_target.items()):
        def fmt(policy: str) -> str:
            value = item.get(policy)
            return "--" if value is None else f"{value:.2f}"

        lines.append(
            f"| {workflow} | {fmt('mso_marginal')} | {fmt('uniform')} | "
            f"{fmt('weakest_raw')} | {fmt('corrected_only')} | {fmt('degree_first')} | {fmt('random')} |"
        )

    lines.extend([
        "",
        "## Random DAG Robustness at Budget 1.50",
        "",
        "| Policy | Mean quality | Mean regret | Feasible rate |",
        "|---|---:|---:|---:|",
    ])
    for policy, item in random_summary.items():
        lines.append(
            f"| {policy} | {item['mean_quality']:.3f} | {item['mean_regret']:.3f} | {item['feasible_rate']:.2f} |"
        )

    lines.extend([
        "",
        f"Best average regret policy: `{best_random}`.",
        "",
        "## Trace Identifiability",
        "",
        "| Scenario | Dual raw error | Corrected-as-raw error | Error ratio |",
        "|---|---:|---:|---:|",
    ])
    for scenario, item in ident_summary.items():
        lines.append(
            f"| {scenario} | {item['raw_error_dual']:.3f} | {item['raw_error_if_corr_used']:.3f} | {item['error_ratio']:.1f}x |"
        )

    lines.extend([
        "",
        "## Software Delivery Case",
        "",
        "| Intervention | Quality | Delta vs base | Bottleneck | Feasible |",
        "|---|---:|---:|---|---:|",
    ])
    for intervention, item in software_summary.items():
        lines.append(
            f"| {intervention} | {float(item['quality']):.3f} | {float(item['delta_vs_base']):+.3f} | "
            f"{item['bottleneck']} | {int(float(item['feasible']))} |"
        )

    lines.extend([
        "",
        f"Best software-delivery intervention: `{best_software}`.",
        "",
        "## Paper-facing interpretation",
        "",
        "The simulations turn the framework into decisions: under fixed budget, allocation policy changes delivered quality and feasibility. The motif and random-DAG runs expose where topology alters the value of review. The trace experiment supports the dual-channel logging requirement by showing that corrected-only observations estimate delivered quality but can badly misstate raw competence. The software-delivery case provides a concrete cockpit-style application where upstream review can dominate final-gate hardening.",
    ])

    (outdir / "summary.md").write_text("\n".join(lines) + "\n")
    (outdir / "summary.json").write_text(
        json.dumps(
            {
                "allocation": allocation_summary,
                "budget_to_target": budget_to_target,
                "random_dag": random_summary,
                "identifiability": ident_summary,
                "software_delivery": software_summary,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=REPO / "tmp" / "wesaac_simulations")
    args = parser.parse_args()

    outdir = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    allocation_rows = run_allocation_benchmark(outdir)
    random_rows = run_random_dag_benchmark(outdir)
    ident_rows = run_trace_identifiability(outdir)
    software_rows = run_software_delivery_case(outdir)
    make_plots(outdir, allocation_rows, random_rows)
    write_summary(outdir, allocation_rows, random_rows, ident_rows, software_rows)

    print(f"wrote {outdir / 'allocation_benchmark.csv'}")
    print(f"wrote {outdir / 'random_dag_benchmark.csv'}")
    print(f"wrote {outdir / 'trace_identifiability.csv'}")
    print(f"wrote {outdir / 'software_delivery_case.csv'}")
    print(f"wrote {outdir / 'summary.md'}")
    if MPL_AVAILABLE:
        print(f"wrote plots under {outdir}")
    else:
        print("matplotlib unavailable; skipped plots")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
