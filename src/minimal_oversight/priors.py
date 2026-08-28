"""Cold-start task-competence priors for MSO.

When a practitioner has no traces yet, they still need *starting* numbers to seed
a pipeline node. This module loads a curated, provenance-bound prior table
(`data/priors.yaml`) and maps a ``(model, task_type)`` cell onto the quantities a
:class:`~minimal_oversight.models.Node` needs:

- generator task-types -> ``sigma_skill`` (via ``sigma_raw_mid / gamma``), so the
  model reproduces the prior's ``sigma_raw`` at the return-operator fixed point;
- the ``review`` task-type -> ``catch_rate`` (how well the model catches an
  upstream node's errors).

Priors are *hypotheses*, not ground truth. Each carries a low/mid/high band and a
source; a wide band means weak evidence. They are meant to be refined by the
user's own logged outcomes — see :mod:`minimal_oversight.estimation`.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import Any

import yaml

REVIEW_TASK = "review"


@dataclass(frozen=True)
class Band:
    """A low/mid/high estimate. ``width`` is a crude evidence-strength proxy."""

    low: float
    mid: float
    high: float

    @property
    def width(self) -> float:
        return self.high - self.low

    @classmethod
    def from_mapping(cls, m: dict[str, float]) -> Band:
        return cls(low=float(m["low"]), mid=float(m["mid"]), high=float(m["high"]))


@dataclass(frozen=True)
class PriorCell:
    """One ``(model, task_type)`` prior with provenance."""

    model: str
    task_type: str
    sigma_raw: Band | None          # generator task-types
    catch_rate: Band | None         # the `review` task-type
    primary_benchmark: str | None
    metric: str | None
    metric_kind: str | None         # "absolute" | "relative"
    reported_value: Any
    sample_size: Any
    observed_date: str | None
    source_url: str | None
    normalization_note: str | None


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


@lru_cache(maxsize=4)
def load_priors(path: str | None = None) -> dict[str, Any]:
    """Load and lightly validate the prior table.

    Returns a dict with ``meta``, ``task_types`` and a ``cells`` map keyed by
    ``(model, task_type)``. Result is cached; pass an explicit ``path`` to bypass
    the packaged file (e.g. in tests).
    """
    if path is None:
        text = resources.files("minimal_oversight.data").joinpath("priors.yaml").read_text()
    else:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    raw = yaml.safe_load(text)

    meta = raw.get("meta", {})
    task_types = list(raw.get("task_types", []))
    gamma = float(meta.get("gamma", 10 / 12))
    if not (0.0 < gamma <= 1.0):
        raise ValueError(f"priors meta.gamma out of range: {gamma}")

    cells: dict[tuple[str, str], PriorCell] = {}
    for row in raw.get("priors", []):
        model = str(row["model"])
        task = str(row["task_type"])
        if task not in task_types:
            raise ValueError(f"unknown task_type {task!r} for model {model!r}")
        sigma = Band.from_mapping(row["sigma_raw"]) if "sigma_raw" in row else None
        catch = Band.from_mapping(row["catch_rate"]) if "catch_rate" in row else None
        if task == REVIEW_TASK and catch is None:
            raise ValueError(f"review cell {model!r} must carry a catch_rate band")
        if task != REVIEW_TASK and sigma is None:
            raise ValueError(f"generator cell {model!r}/{task!r} must carry a sigma_raw band")
        for b in (sigma, catch):
            if b is not None and not (0.0 <= b.low <= b.mid <= b.high <= 1.0):
                raise ValueError(f"non-monotone or out-of-range band for {model!r}/{task!r}")
        key = (model, task)
        if key in cells:
            raise ValueError(f"duplicate prior cell {key}")
        cells[key] = PriorCell(
            model=model,
            task_type=task,
            sigma_raw=sigma,
            catch_rate=catch,
            primary_benchmark=row.get("primary_benchmark"),
            metric=row.get("metric"),
            metric_kind=row.get("metric_kind"),
            reported_value=row.get("reported_value"),
            sample_size=row.get("sample_size"),
            observed_date=row.get("observed_date"),
            source_url=row.get("source_url"),
            normalization_note=row.get("normalization_note"),
        )
    return {"meta": meta, "gamma": gamma, "task_types": task_types, "cells": cells}


def list_models(path: str | None = None) -> list[str]:
    """Sorted distinct model names in the table."""
    return sorted({m for (m, _t) in load_priors(path)["cells"]})


def list_task_types(path: str | None = None) -> list[str]:
    return list(load_priors(path)["task_types"])


def get_cell(model: str, task_type: str, path: str | None = None) -> PriorCell:
    cells = load_priors(path)["cells"]
    try:
        return cells[(model, task_type)]
    except KeyError:
        raise KeyError(f"no prior for model={model!r} task_type={task_type!r}") from None


def seed_node(model: str, task_type: str, path: str | None = None) -> dict[str, Any]:
    """Map a prior cell onto ``Node`` keyword arguments + provenance.

    For generator task-types returns ``sigma_skill`` (so the model reproduces the
    prior's ``sigma_raw`` at the fixed point) and a zero ``catch_rate``. For the
    ``review`` task-type returns the ``catch_rate`` (and no ``sigma_skill``; the
    caller pairs the reviewer with the node it corrects).

    The returned ``provenance`` block carries the band, source, and a
    ``confidence`` proxy (``1 - band_width``) so the UI can render priors as
    hypotheses, never as ground truth.
    """
    data = load_priors(path)
    gamma = data["gamma"]
    cell = get_cell(model, task_type, path)

    out: dict[str, Any] = {"model": model, "task_type": task_type, "is_prior": True}
    if task_type == REVIEW_TASK:
        band = cell.catch_rate
        out["catch_rate"] = _clamp(band.mid, 0.0, 1.0)
        out["seeds"] = "catch_rate"
    else:
        band = cell.sigma_raw
        meta = data["meta"]
        default_catch = float(meta.get("generator_default_catch_rate", 0.0))
        out["sigma_skill"] = _clamp(band.mid / gamma, 0.05, 0.98)
        out["catch_rate"] = default_catch
        out["seeds"] = "sigma_skill"

    out["provenance"] = {
        "band": {"low": band.low, "mid": band.mid, "high": band.high},
        "confidence": round(1.0 - band.width, 3),
        "primary_benchmark": cell.primary_benchmark,
        "metric": cell.metric,
        "metric_kind": cell.metric_kind,
        "observed_date": cell.observed_date,
        "source_url": cell.source_url,
        "normalization_note": cell.normalization_note,
    }
    return out
