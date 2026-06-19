"""Model cost + license registry for the allocation optimizer.

Loads ``data/model_registry.yaml`` — each model's public API price (USD per
million tokens, input/output) and license — and derives a 1..100 **cost index**
(log-scale) so the cockpit can show either dollars or a relative scale.

The registry answers three questions the optimizer needs:

- *How much does this model cost per run?* → :func:`cost_per_run`.
- *Is it open-source (and commercially usable)?* → :func:`is_open_source`.
- *Which models are cheaper / pricier?* → ``cost_index`` and :func:`blended_cost`.

Costs are *priors*, not invoices — prices change, batch/cached tiers differ, and
open-weights self-host economics differ from hosted-API prices. Refine from your
provider's actual bill.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import Any

import yaml


@dataclass(frozen=True)
class ModelCost:
    """Cost + license for one model."""

    name: str
    provider: str
    modality: str                  # llm | embedding | reranker
    license_name: str
    open: bool                     # open-weights AND commercially usable
    input_usd_per_mtok: float | None
    output_usd_per_mtok: float | None
    blended_usd_per_mtok: float | None
    cost_index: int | None         # 1..100, log-scale; None if unpriced
    note: str | None

    @property
    def priced(self) -> bool:
        return self.blended_usd_per_mtok is not None


def _index(blended: float | None, lo: float, hi: float) -> int | None:
    """Map a blended $/Mtok onto a 1..100 log-scale cost index."""
    if blended is None or blended <= 0:
        return None
    b = max(lo, min(hi, blended))
    frac = (math.log(b) - math.log(lo)) / (math.log(hi) - math.log(lo))
    return int(round(1 + 99 * frac))


@lru_cache(maxsize=4)
def load_registry(path: str | None = None) -> dict[str, Any]:
    """Load and lightly validate the model registry.

    Returns ``{"meta": ..., "models": {name: ModelCost}}``. Cached; pass an
    explicit ``path`` to bypass the packaged file (e.g. in tests).
    """
    if path is None:
        text = resources.files("minimal_oversight.data").joinpath(
            "model_registry.yaml"
        ).read_text()
    else:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    raw = yaml.safe_load(text)

    meta = raw.get("meta", {})
    blend = meta.get("blend", {"input": 0.6, "output": 0.4})
    anchors = meta.get("index_anchors", {"min": 0.05, "max": 60.0})
    lo, hi = float(anchors["min"]), float(anchors["max"])
    wi, wo = float(blend["input"]), float(blend["output"])

    models: dict[str, ModelCost] = {}
    for row in raw.get("models", []):
        name = str(row["name"])
        if name in models:
            raise ValueError(f"duplicate model in registry: {name!r}")
        cost = row.get("cost", {})
        ci = cost.get("input")
        co = cost.get("output")
        ci = None if ci is None else float(ci)
        co = None if co is None else float(co)
        blended = None if (ci is None or co is None) else wi * ci + wo * co
        lic = row.get("license", {})
        models[name] = ModelCost(
            name=name,
            provider=str(row.get("provider", "unknown")),
            modality=str(row.get("modality", "llm")),
            license_name=str(lic.get("name", "unknown")),
            open=bool(lic.get("open", False)),
            input_usd_per_mtok=ci,
            output_usd_per_mtok=co,
            blended_usd_per_mtok=blended,
            cost_index=_index(blended, lo, hi),
            note=row.get("note"),
        )
    return {"meta": meta, "models": models}


def list_models(path: str | None = None) -> list[str]:
    return sorted(load_registry(path)["models"])


def get_model(name: str, path: str | None = None) -> ModelCost:
    models = load_registry(path)["models"]
    try:
        return models[name]
    except KeyError:
        raise KeyError(f"no registry entry for model {name!r}") from None


def has_model(name: str, path: str | None = None) -> bool:
    return name in load_registry(path)["models"]


def is_open_source(name: str, path: str | None = None) -> bool:
    """True if the model is open-weights AND commercially usable."""
    return get_model(name, path).open


def blended_cost(name: str, path: str | None = None) -> float | None:
    """Blended $/Mtok (0.6*input + 0.4*output by default)."""
    return get_model(name, path).blended_usd_per_mtok


def cost_per_run(
    name: str,
    input_tokens: float,
    output_tokens: float = 0.0,
    path: str | None = None,
) -> float | None:
    """USD cost of one invocation given token volumes.

    ``(input_tokens * $in + output_tokens * $out) / 1e6``. Returns None for an
    unpriced model (e.g. a model with no public price).
    """
    m = get_model(name, path)
    if m.input_usd_per_mtok is None or m.output_usd_per_mtok is None:
        return None
    return (input_tokens * m.input_usd_per_mtok
            + output_tokens * m.output_usd_per_mtok) / 1_000_000.0


def models_by_modality(modality: str, path: str | None = None) -> list[str]:
    return sorted(
        n for n, m in load_registry(path)["models"].items() if m.modality == modality
    )


def open_models(path: str | None = None) -> list[str]:
    return sorted(
        n for n, m in load_registry(path)["models"].items() if m.open
    )
