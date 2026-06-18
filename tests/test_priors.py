"""Tests for the cold-start priors loader and the (model, task) -> Node seeding."""

from __future__ import annotations

import textwrap

import pytest

from minimal_oversight import priors as P


def test_table_loads_and_lists():
    models = P.list_models()
    tasks = P.list_task_types()
    assert models, "expected at least one model in the prior table"
    assert "review" in tasks
    assert "code_generation" in tasks


def test_generator_seed_reproduces_sigma_raw_at_fixed_point():
    """sigma_skill is set so gamma * sigma_skill == the prior's sigma_raw mid."""
    data = P.load_priors()
    gamma = data["gamma"]
    for (model, task), cell in data["cells"].items():
        if task == "review":
            continue
        seed = P.seed_node(model, task)
        assert seed["seeds"] == "sigma_skill"
        assert 0.05 <= seed["sigma_skill"] <= 0.98
        assert seed["catch_rate"] == 0.0  # a generator does not correct its parent
        # round-trips unless the mid was clamped at the [0.05, 0.98] rails
        unclamped = cell.sigma_raw.mid / gamma
        if 0.05 <= unclamped <= 0.98:
            assert gamma * seed["sigma_skill"] == pytest.approx(cell.sigma_raw.mid, abs=1e-9)


def test_review_seed_yields_catch_rate():
    review_cells = [(m, t) for (m, t) in P.load_priors()["cells"] if t == "review"]
    assert review_cells, "expected at least one review cell"
    for model, _ in review_cells:
        seed = P.seed_node(model, "review")
        assert seed["seeds"] == "catch_rate"
        assert 0.0 <= seed["catch_rate"] <= 1.0
        assert "sigma_skill" not in seed


def test_provenance_block_is_well_formed():
    for (model, task) in P.load_priors()["cells"]:
        prov = P.seed_node(model, task)["provenance"]
        assert 0.0 <= prov["confidence"] <= 1.0
        b = prov["band"]
        assert 0.0 <= b["low"] <= b["mid"] <= b["high"] <= 1.0
        assert prov["metric_kind"] in {"absolute", "relative", None}


def test_unknown_cell_raises():
    with pytest.raises(KeyError):
        P.seed_node("no_such_model", "code_generation")


def _write(tmp_path, body: str) -> str:
    p = tmp_path / "priors.yaml"
    p.write_text(textwrap.dedent(body))
    return str(p)


def test_loader_rejects_nonmonotone_band(tmp_path):
    path = _write(tmp_path, """
        meta: {schema_version: 1, gamma: 0.8333333333333334, status: test}
        task_types: [code_generation, review]
        priors:
          - model: m
            task_type: code_generation
            sigma_raw: {low: 0.8, mid: 0.5, high: 0.9}
    """)
    with pytest.raises(ValueError):
        P.load_priors(path)


def test_loader_rejects_review_without_catch_rate(tmp_path):
    path = _write(tmp_path, """
        meta: {schema_version: 1, gamma: 0.8333333333333334, status: test}
        task_types: [code_generation, review]
        priors:
          - model: m
            task_type: review
            sigma_raw: {low: 0.4, mid: 0.6, high: 0.8}
    """)
    with pytest.raises(ValueError):
        P.load_priors(path)


def test_loader_rejects_unknown_task_type(tmp_path):
    path = _write(tmp_path, """
        meta: {schema_version: 1, gamma: 0.8333333333333334, status: test}
        task_types: [code_generation]
        priors:
          - model: m
            task_type: telepathy
            sigma_raw: {low: 0.4, mid: 0.6, high: 0.8}
    """)
    with pytest.raises(ValueError):
        P.load_priors(path)
