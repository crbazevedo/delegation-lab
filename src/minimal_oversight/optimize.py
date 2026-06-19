"""Cost-aware allocation optimizer.

Given a workflow (nodes with a task, complexity and an assigned model), a quality
target ``p_min`` and an optional cost ``budget``, search for a cheaper allocation
that still clears the bar — or, starting from an all-expensive pipeline, the
cheapest allocation that fits the budget while holding the bar.

The search is a **greedy structural local-search** over three move types:

1. **Model swap** — change a node's model to another that has a prior for its
   task (cheapest that clears the node's bar; open-source preferred on ties).
2. **Add oversight** — insert a reviewer+corrector node after a weak node
   (detect *and* repair; the meaningful oversight unit, per *reviewer ≠
   corrector*).
3. **Loop** — add a rework pass on a reviewed node (compounds the catch rate).

Both directions fall out of the same loop: from a cheap, infeasible pipeline it
*invests* (the move with the best ΔC_op per dollar) until feasible; from an
expensive, feasible one it *divests* (the biggest cost cut that keeps C_op ≥
p_min and ≤ budget). It is a heuristic — greedy local-search, not a global
optimum — but it is transparent and every step is costed.

Node spec (a plain dict, mirroring the cockpit pipeline):

    {id, role, task, complexity, tool_misuse, model, parents,
     aggregation, in_tok, out_tok, calls}

``role`` ∈ {generator, retriever, reranker, reader, classifier, reviewer,
corrector}. ``task`` is a priors task-type. Generator-family roles seed
σ_skill from their model's prior; reviewers seed a catch rate; correctors a
fix rate.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from minimal_oversight import priors as P
from minimal_oversight import registry as R
from minimal_oversight.complexity import effective_sigma, required_prior_sigma
from minimal_oversight.models import AggregationType, Node, PipelineGraph
from minimal_oversight import _formulae as F

GAMMA = 10.0 / 12.0
GENERATOR_ROLES = {"generator", "retriever", "reranker", "reader", "classifier"}

# Default per-call token volumes by role (input, output) — overridable per node.
DEFAULT_TOKENS = {
    "generator": (1500, 500),
    "reader": (3000, 600),
    "classifier": (800, 50),
    "retriever": (1000, 0),
    "reranker": (4000, 0),
    "reviewer": (1500, 300),
    "corrector": (1800, 600),
}

_AGG = {
    "product": AggregationType.PRODUCT,
    "min": AggregationType.WEAKEST_LINK,
    "mean": AggregationType.WEIGHTED_MEAN,
}


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


# ---------------------------------------------------------------------------
# Per-node parameters from (model × task × complexity)
# ---------------------------------------------------------------------------

def _prior_mid(model: str, task: str) -> float | None:
    """The prior band mid for (model, task), or None if absent."""
    try:
        cell = P.get_cell(model, task)
    except KeyError:
        return None
    if cell.sigma_raw is not None:
        return cell.sigma_raw.mid
    if cell.catch_rate is not None:
        return cell.catch_rate.mid
    if cell.fix_rate is not None:
        return cell.fix_rate.mid
    return None


def node_params(node: dict) -> tuple[float, float, float]:
    """Derive (sigma_skill, catch_rate, fix_rate) for a node from its model+role."""
    role = node.get("role", "generator")
    task = node.get("task")
    model = node.get("model")
    complexity = node.get("complexity", "moderate")
    misuse = float(node.get("tool_misuse", 0.0))

    if role == "reviewer":
        base = _prior_mid(model, "review") if model else None
        base = 0.62 if base is None else base
        catch = effective_sigma(base, complexity, misuse)
        return 0.92, catch, 1.0
    if role == "corrector":
        # fix scales with the corrector model's general competence (vs a 0.85 ref),
        # anchored on the "with-feedback" prior (~0.70).
        comp = _prior_mid(model, "drafting") if model else None
        comp = 0.85 if comp is None else comp
        fix = _clamp(0.70 * (comp / 0.85), 0.10, 0.95)
        fix = effective_sigma(fix, complexity, misuse)
        return 0.92, 0.0, fix
    if role == "oversight":
        # a combined reviewer+corrector unit: it BOTH detects (catch) and
        # repairs (fix). This is the meaningful structural oversight investment —
        # a corrector alone (catch=0) lifts nothing (reviewer ≠ corrector).
        cbase = _prior_mid(model, "review") if model else None
        cbase = 0.62 if cbase is None else cbase
        catch = effective_sigma(cbase, complexity, misuse)
        comp = _prior_mid(model, "drafting") if model else None
        comp = 0.85 if comp is None else comp
        fix = _clamp(0.70 * (comp / 0.85), 0.10, 0.95)
        return 0.92, catch, fix

    # generator family
    base = _prior_mid(model, task) if (model and task) else None
    base = 0.50 if base is None else base
    sigma_raw = effective_sigma(base, complexity, misuse)
    sigma_skill = _clamp(sigma_raw / GAMMA, 0.05, 0.98)
    # in-place oversight: a reviewer+corrector attached AT this node (review the
    # node's own output — no new delegation hop, so no skill-damping). This is
    # the faithful "invest in review" lever: σ_corr = σ_raw + (1−σ_raw)·c·f.
    ov = node.get("oversight_model")
    if ov:
        cbase = _prior_mid(ov, "review") or 0.62
        catch = effective_sigma(cbase, complexity, misuse)
        comp = _prior_mid(ov, "drafting") or 0.85
        fix = _clamp(0.70 * (comp / 0.85), 0.10, 0.95)
        return sigma_skill, catch, fix
    return sigma_skill, 0.0, 1.0


def node_cost(node: dict) -> float:
    """USD per run for a node (cost_per_run × calls). 0 if unpriced/no model."""
    model = node.get("model")
    if not model or not R.has_model(model):
        return 0.0
    in_tok = node.get("in_tok")
    out_tok = node.get("out_tok")
    if in_tok is None or out_tok is None:
        d = DEFAULT_TOKENS.get(node.get("role", "generator"), (1500, 400))
        in_tok = d[0] if in_tok is None else in_tok
        out_tok = d[1] if out_tok is None else out_tok
    base = R.cost_per_run(model, in_tok, out_tok)
    if base is None:
        return 0.0
    calls = float(node.get("calls", 1.0)) * float(node.get("rework", 1) or 1)
    cost = base * calls
    # in-place oversight adds a detect pass + a correct pass at this node
    ov = node.get("oversight_model")
    if ov and R.has_model(ov):
        ovc = R.cost_per_run(ov, in_tok, out_tok)
        if ovc is not None:
            cost += ovc * 2.0
    return cost


def _to_graph(nodes: list[dict]) -> PipelineGraph:
    objs = []
    for n in nodes:
        skill, catch, fix = node_params(n)
        # a review loop compounds the catch rate: 1-(1-c)^k
        k = int(n.get("rework", 1) or 1)
        if k > 1 and catch > 0:
            catch = 1.0 - (1.0 - catch) ** k
        objs.append(Node(
            n["id"], sigma_skill=skill, catch_rate=catch, fix_rate=fix,
            aggregation=_AGG.get(n.get("aggregation", "product"), AggregationType.PRODUCT),
        ))
    g = PipelineGraph(objs)
    for n in nodes:
        for p in n.get("parents", []):
            g.add_edge(p, n["id"])
    return g


def _c_op(nodes: list[dict]) -> float:
    g = _to_graph(nodes)
    caps: dict[str, float] = {}
    corr: dict[str, float] = {}
    for name in g.topological_order():
        node = g.get_node(name)
        parents = g.parents(name)
        if parents:
            pc = [corr.get(p, 1.0) for p in parents]
            skill_eff = F.effective_skill(node.sigma_skill, pc, node.aggregation.value)
        else:
            skill_eff = node.sigma_skill
        sr = F.sigma_raw_fixed_point(skill_eff, 10, 2, 0.0)
        sc = F.sigma_corr_fixed_point(sr, node.catch_rate, node.fix_rate)
        corr[name] = sc
        caps[name] = sc
    sinks = g.sinks()
    return min((caps[s] for s in sinks), default=0.0)


def total_cost(nodes: list[dict]) -> float:
    return sum(node_cost(n) for n in nodes)


@dataclass
class Evaluation:
    c_op: float
    cost: float
    feasible: bool
    within_budget: bool


def evaluate(nodes: list[dict], p_min: float, budget: float | None = None) -> Evaluation:
    c = _c_op(nodes)
    cost = total_cost(nodes)
    return Evaluation(
        c_op=c, cost=cost, feasible=c >= p_min,
        within_budget=(budget is None or cost <= budget),
    )


# ---------------------------------------------------------------------------
# Candidate models / per-node prescription
# ---------------------------------------------------------------------------

@dataclass
class ModelOption:
    model: str
    sigma_eff: float       # competence achieved at this node
    cost_index: int | None
    blended_usd: float | None
    open: bool
    clears: bool           # σ_eff ≥ the node's bar


def candidate_models(
    task: str,
    complexity: str = "moderate",
    tool_misuse: float = 0.0,
    target_sigma: float = 0.0,
    prefer_oss: bool = True,
) -> list[ModelOption]:
    """Models with a prior for ``task``, scored at this node and ranked by cost.

    Ranking: clears-the-bar first, then by cost (cheapest first), with open-source
    preferred on near-ties (within one cost-index point).
    """
    opts: list[ModelOption] = []
    for model in R.models_by_modality("llm") + R.models_by_modality("embedding") + R.models_by_modality("reranker"):
        base = _prior_mid(model, task)
        if base is None:
            continue
        m = R.get_model(model)
        if m.blended_usd_per_mtok is None:
            continue  # unpriced model can't be cost-optimized — exclude
        seff = effective_sigma(base, complexity, tool_misuse)
        opts.append(ModelOption(
            model=model, sigma_eff=seff, cost_index=m.cost_index,
            blended_usd=m.blended_usd_per_mtok, open=m.open,
            clears=seff >= target_sigma,
        ))

    def sort_key(o: ModelOption):
        ci = o.cost_index if o.cost_index is not None else 999
        # cheaper first; among near-equal cost, open-source first
        return (0 if o.clears else 1, ci, 0 if o.open else 1, -o.sigma_eff)

    opts.sort(key=sort_key)
    return opts


def prescribe_node(
    node: dict,
    target_sigma: float,
    prefer_oss: bool = True,
) -> dict[str, Any]:
    """The minimal-cost model that makes the cut for a node, with an OSS verdict.

    Returns ``{pick, oss_can_do, open_pick, proprietary_pick, options}``.
    """
    task = node.get("task")
    opts = candidate_models(
        task, node.get("complexity", "moderate"),
        float(node.get("tool_misuse", 0.0)), target_sigma, prefer_oss,
    )
    clearing = [o for o in opts if o.clears]
    pick = clearing[0] if clearing else (opts[0] if opts else None)
    open_pick = next((o for o in clearing if o.open), None)
    prop_pick = next((o for o in clearing if not o.open), None)
    return {
        "pick": pick,
        "oss_can_do": open_pick is not None,
        "open_pick": open_pick,
        "proprietary_pick": prop_pick,
        "needs_proprietary": (open_pick is None and prop_pick is not None),
        "options": opts,
    }


# ---------------------------------------------------------------------------
# The greedy optimizer
# ---------------------------------------------------------------------------

@dataclass
class AllocationResult:
    nodes: list[dict]
    c_op: float
    cost: float
    feasible: bool
    within_budget: bool
    p_min: float
    budget: float | None
    steps: list[str] = field(default_factory=list)


def _node_bar(nodes: list[dict], target_node_id: str, p_min: float) -> float:
    """A rough per-node σ bar: the pipeline target (a conservative shared floor)."""
    return p_min


def _gen_nodes(nodes: list[dict]) -> list[dict]:
    return [n for n in nodes if n.get("role", "generator") in GENERATOR_ROLES]


def _swappable(nodes: list[dict]) -> list[dict]:
    """Nodes whose task has priced candidate models (generators AND reviewers)."""
    out = []
    for n in nodes:
        task = n.get("task")
        if task and candidate_models(task, n.get("complexity", "moderate"),
                                     float(n.get("tool_misuse", 0.0))):
            out.append(n)
    return out


def _strong_oversight_model() -> str:
    """The reviewer model with the highest catch (for Phase A's add-oversight)."""
    best, best_sig = "deepseek-v3", -1.0
    for o in candidate_models("review", "moderate", 0.0, 0.0):
        if o.sigma_eff > best_sig:
            best, best_sig = o.model, o.sigma_eff
    return best


def _swap_options(node: dict, p_min: float, prefer_oss: bool) -> list[ModelOption]:
    bar = required_prior_sigma(p_min, node.get("complexity", "moderate"),
                               float(node.get("tool_misuse", 0.0)))
    # express the bar back as an effective-σ target for ranking
    return candidate_models(node.get("task"), node.get("complexity", "moderate"),
                            float(node.get("tool_misuse", 0.0)),
                            target_sigma=min(p_min, 0.99), prefer_oss=prefer_oss)


def optimize_allocation(
    nodes: list[dict],
    p_min: float = 0.80,
    budget: float | None = None,
    prefer_oss: bool = True,
    max_steps: int = 60,
) -> AllocationResult:
    """Greedy both-directions allocation search. Returns the improved pipeline."""
    nodes = copy.deepcopy(nodes)
    steps: list[str] = []

    # assign a default model to any generator node missing one (cheapest clearing)
    for n in _gen_nodes(nodes):
        if not n.get("model"):
            opts = candidate_models(n.get("task"), n.get("complexity", "moderate"),
                                    float(n.get("tool_misuse", 0.0)), p_min, prefer_oss)
            if opts:
                n["model"] = opts[0].model
                steps.append(f"seed {n['id']} → {opts[0].model}")

    def ev() -> Evaluation:
        return evaluate(nodes, p_min, budget)

    # ---- Phase A: invest until feasible (max ΔC_op; cheaper breaks ties) ----
    for _ in range(max_steps):
        e = ev()
        if e.feasible:
            break
        best = None  # (key, trial, desc)
        base_c = e.c_op
        base_cost = e.cost
        # model upgrades on each swappable node (generators AND reviewers)
        for n in _swappable(nodes):
            cur = n.get("model")
            for o in candidate_models(n.get("task"), n.get("complexity", "moderate"),
                                      float(n.get("tool_misuse", 0.0)), p_min, prefer_oss):
                if o.model == cur:
                    continue
                trial = copy.deepcopy(nodes)
                for t in trial:
                    if t["id"] == n["id"]:
                        t["model"] = o.model
                de = evaluate(trial, p_min, budget)
                dgain = de.c_op - base_c
                if dgain > 1e-6:
                    key = (round(dgain, 6), -(de.cost - base_cost))
                    if best is None or key > best[0]:
                        best = (key, trial, f"upgrade {n['id']} → {o.model}")
        # invest in-place oversight (review + correct) at any generator missing it
        om = _strong_oversight_model()
        for n in _gen_nodes(nodes):
            if n.get("oversight_model"):
                continue
            trial = copy.deepcopy(nodes)
            for t in trial:
                if t["id"] == n["id"]:
                    t["oversight_model"] = om
            de = evaluate(trial, p_min, budget)
            dgain = de.c_op - base_c
            if dgain > 1e-6:
                key = (round(dgain, 6), -(de.cost - base_cost))
                if best is None or key > best[0]:
                    best = (key, trial, f"add review+correct at {n['id']} ({om})")
        if best is None:
            break
        nodes = best[1]
        steps.append(best[2])

    # ---- Phase B: divest while staying feasible (biggest cost cut) ----
    for _ in range(max_steps):
        e = ev()
        if not e.feasible:
            break
        best = None  # (saving, trial, desc)
        base_cost = e.cost
        for n in _swappable(nodes):
            cur = n.get("model")
            for o in candidate_models(n.get("task"), n.get("complexity", "moderate"),
                                      float(n.get("tool_misuse", 0.0)), p_min, prefer_oss):
                if o.model == cur:
                    continue
                trial = copy.deepcopy(nodes)
                for t in trial:
                    if t["id"] == n["id"]:
                        t["model"] = o.model
                de = evaluate(trial, p_min, budget)
                saving = base_cost - de.cost
                if de.feasible and saving > 1e-9:
                    # prefer OSS swaps on near-equal saving
                    bonus = 1e-9 if o.open else 0.0
                    if best is None or (saving + bonus) > best[0]:
                        best = (saving + bonus, trial, f"downgrade {n['id']} → {o.model}")
        # trim in-place oversight: drop it where no longer needed, or move it to a
        # cheaper reviewer model, as long as the pipeline stays feasible.
        for n in nodes:
            if not n.get("oversight_model"):
                continue
            # removal
            trial = copy.deepcopy(nodes)
            for t in trial:
                if t["id"] == n["id"]:
                    t.pop("oversight_model", None)
            de = evaluate(trial, p_min, budget)
            saving = base_cost - de.cost
            if de.feasible and saving > 1e-9 and (best is None or saving > best[0]):
                best = (saving, trial, f"drop review+correct at {n['id']}")
            # cheaper oversight model
            for o in candidate_models("review", n.get("complexity", "moderate"),
                                      float(n.get("tool_misuse", 0.0)), 0.0, prefer_oss):
                if o.model == n.get("oversight_model"):
                    continue
                trial = copy.deepcopy(nodes)
                for t in trial:
                    if t["id"] == n["id"]:
                        t["oversight_model"] = o.model
                de = evaluate(trial, p_min, budget)
                saving = base_cost - de.cost
                if de.feasible and saving > 1e-9 and (best is None or saving > best[0]):
                    best = (saving, trial, f"cheaper review at {n['id']} → {o.model}")
        if best is None:
            break
        nodes = best[1]
        steps.append(best[2])

    e = ev()
    return AllocationResult(
        nodes=nodes, c_op=e.c_op, cost=e.cost, feasible=e.feasible,
        within_budget=e.within_budget, p_min=p_min, budget=budget, steps=steps,
    )
