"""Tests for the model cost + license registry."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from minimal_oversight import priors as P
from minimal_oversight import registry as R

_REPO = Path(__file__).resolve().parents[1]


def test_js_registry_bundle_is_regenerated():
    """web/mso-registry.js must be freshly generated from model_registry.yaml."""
    spec = importlib.util.spec_from_file_location(
        "gen_registry_js", _REPO / "scripts" / "gen_registry_js.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    generated = mod.build()
    on_disk = (_REPO / "web" / "mso-registry.js").read_text()
    assert generated == on_disk, (
        "web/mso-registry.js is stale — run: python scripts/gen_registry_js.py"
    )

# Roles that are configurations, not real costable models.
_NON_MODELS = {
    "llm-judge-single", "llm-judge-ensemble", "human-reviewer",
    "corrector-no-feedback", "corrector-with-feedback", "corrector-with-oracle",
}


def test_registry_loads():
    models = R.list_models()
    assert models, "expected models in the registry"
    assert R.has_model("gpt-4o")
    assert not R.has_model("no-such-model")


def test_every_real_priors_model_has_a_cost_entry():
    priors_models = {m for (m, _t) in P.load_priors()["cells"]} - _NON_MODELS
    missing = sorted(m for m in priors_models if not R.has_model(m))
    assert not missing, f"priors models without a registry entry: {missing}"


def test_open_source_flags():
    for m in ["llama-3.3-70b", "deepseek-v3", "qwen3-8b", "phi-4", "bge-m3",
              "granite-embedding-r2", "kimi-k2.5"]:
        assert R.is_open_source(m), f"{m} should be open"
    for m in ["gpt-4o", "claude-opus-4", "gemini-2.5-pro", "cohere-embed-v3",
              "o3-pro"]:
        assert not R.is_open_source(m), f"{m} should be proprietary"


def test_mistral_large_is_non_commercial_open():
    # open-weights but research-only license -> not in the commercial-OSS set
    assert not R.is_open_source("mistral-large")
    assert "research" in R.get_model("mistral-large").license_name.lower()


def test_cost_index_in_range_and_monotone():
    cheap = R.get_model("phi-4").cost_index
    mid = R.get_model("gpt-4o").cost_index
    pricey = R.get_model("o3-pro").cost_index
    for ci in (cheap, mid, pricey):
        assert ci is not None and 1 <= ci <= 100
    assert cheap < mid < pricey, "cost index must track blended price"


def test_cost_per_run_math():
    # gpt-4o = $2.5 in / $10 out per Mtok; 2000 in + 500 out
    c = R.cost_per_run("gpt-4o", 2000, 500)
    expected = (2000 * 2.5 + 500 * 10.0) / 1_000_000.0
    assert abs(c - expected) < 1e-12


def test_unpriced_model_is_handled():
    m = R.get_model("fable-5")
    assert not m.priced
    assert R.cost_per_run("fable-5", 1000, 100) is None


def test_open_models_helper():
    opens = set(R.open_models())
    assert "deepseek-v3" in opens and "gpt-4o" not in opens


def test_modality_partition():
    assert "gpt-4o" in R.models_by_modality("llm")
    assert "bge-m3" in R.models_by_modality("embedding")
    assert "cohere-rerank-3" in R.models_by_modality("reranker")
