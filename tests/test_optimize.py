"""Tests for the cost-aware allocation optimizer.

Assert *properties* (feasibility reached, cost reduced, OSS preferred), not exact
model picks — picks shift as priors/prices are refined, the guarantees should not.
"""

from __future__ import annotations

from minimal_oversight import optimize as O
from minimal_oversight import registry as R


def _draft(model, complexity="moderate", **kw):
    return {"id": kw.get("id", "n"), "role": "generator", "task": "drafting",
            "complexity": complexity, "model": model, "parents": kw.get("parents", [])}


def test_evaluate_reports_cop_cost_feasible():
    e = O.evaluate([_draft("gpt-4o", "easy")], 0.70)
    assert 0.0 <= e.c_op <= 1.0
    assert e.cost > 0
    assert e.feasible == (e.c_op >= 0.70)


def test_candidate_models_excludes_unpriced_and_ranks_by_cost():
    opts = O.candidate_models("drafting", "easy", 0.0, target_sigma=0.0)
    names = [o.model for o in opts]
    assert "fable-5" not in names, "unpriced model must be excluded from candidates"
    # among clearing options, cost index is non-decreasing (cheapest first)
    clearing = [o for o in opts if o.clears]
    idx = [o.cost_index for o in clearing if o.cost_index is not None]
    assert idx == sorted(idx)


def test_prescribe_minimal_model_and_oss_verdict():
    node = {"id": "x", "role": "generator", "task": "drafting", "complexity": "easy"}
    pr = O.prescribe_node(node, target_sigma=0.70)
    assert pr["pick"] is not None and pr["pick"].clears
    assert isinstance(pr["oss_can_do"], bool)
    if pr["oss_can_do"]:
        assert pr["open_pick"] is not None and pr["open_pick"].open


def test_hard_task_needs_stronger_model_than_easy():
    easy = O.prescribe_node({"task": "drafting", "complexity": "easy"}, 0.75)
    hard = O.prescribe_node({"task": "drafting", "complexity": "critical"}, 0.75)
    # the critical-task clearing set is a subset of the easy-task clearing set
    easy_clear = {o.model for o in easy["options"] if o.clears}
    hard_clear = {o.model for o in hard["options"] if o.clears}
    assert hard_clear <= easy_clear


def test_direction_A_reaches_the_bar_from_a_cheap_pipeline():
    nodes = [_draft("qwen3-8b", "moderate")]
    start = O.evaluate(nodes, 0.80)
    assert not start.feasible, "fixture must start infeasible"
    res = O.optimize_allocation(nodes, p_min=0.80, prefer_oss=True)
    assert res.feasible and res.c_op >= 0.80
    assert res.steps, "optimizer should record the moves it made"


def test_direction_B_cuts_cost_from_an_expensive_pipeline():
    nodes = [
        {"id": "a", "role": "generator", "task": "drafting", "complexity": "easy",
         "model": "claude-opus-4", "parents": []},
        {"id": "b", "role": "reviewer", "task": "review", "complexity": "easy",
         "model": "claude-opus-4", "parents": ["a"]},
    ]
    start = O.evaluate(nodes, 0.80)
    assert start.feasible, "fixture must start feasible"
    res = O.optimize_allocation(nodes, p_min=0.80, budget=start.cost * 0.3,
                                prefer_oss=True)
    assert res.feasible and res.c_op >= 0.80, "must hold the quality bar"
    assert res.cost < start.cost, "must reduce cost"
    assert res.within_budget, "should fit the budget here"


def test_optimizer_prefers_open_source_when_it_clears():
    # an easy drafting node where cheap OSS clears the bar -> picks OSS
    nodes = [_draft("claude-opus-4", "easy")]
    res = O.optimize_allocation(nodes, p_min=0.70, prefer_oss=True)
    chosen = res.nodes[0]["model"]
    assert R.is_open_source(chosen), f"expected an OSS pick, got {chosen}"


def test_unpriced_model_never_chosen_by_optimizer():
    nodes = [_draft("claude-opus-4", "easy")]
    res = O.optimize_allocation(nodes, p_min=0.70)
    for n in res.nodes:
        if n.get("model"):
            assert R.get_model(n["model"]).priced, "optimizer chose an unpriced model"
