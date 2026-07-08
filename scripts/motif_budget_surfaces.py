#!/usr/bin/env python3
"""Motif-specific competence surfaces for the Competence Calibration Operator.

This script turns the paper's equations into a small experiment suite:

* budget -> raw competence delta curves for chain and merge motifs
* skill/budget contour surfaces at several observation/decay settings
* diamond fragility as a separate topology effect

The main point is intentionally not masking. Masking falls out of the same
signals, but the experiment focuses on how topology and oversight budget move
the central node's raw competence.

Outputs are written to ``tmp/motif_surfaces`` by default.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from minimal_oversight import _formulae as F  # noqa: E402

try:  # pragma: no cover - optional plotting dependency
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    MPL_AVAILABLE = True
except Exception:  # pragma: no cover - plotting is optional
    MPL_AVAILABLE = False
    plt = None  # type: ignore[assignment]


@dataclass(frozen=True)
class MotifSpec:
    """Minimal motif descriptor for the analytic experiment."""

    name: str
    family: str  # "chain" or "merge"
    depth: int = 1
    fan_in: int = 1
    aggregation: str = "product"


def observation_share(eta: float, delta: float) -> float:
    """Calibration-operator observation share a = eta / (eta + delta)."""

    denom = eta + delta
    if denom <= 0:
        raise ValueError("eta + delta must be positive")
    return eta / denom


def baseline_raw(skill: float, eta: float, delta: float, sigma0: float) -> float:
    """Raw competence of an isolated node."""

    return F.sigma_raw_fixed_point(skill, eta, delta, sigma_0=sigma0)


def oversight_strength(
    budget: float,
    catch_rate: float,
    fix_rate: float,
) -> float:
    """Effective oversight strength c_eff * B."""

    b = float(np.clip(budget, 0.0, 1.0))
    return float(np.clip(catch_rate * fix_rate * b, 0.0, 1.0))


def corrected_quality(raw: float, budget: float, catch_rate: float, fix_rate: float) -> float:
    """Corrected quality from a raw signal under the oversight budget."""

    c_eff = oversight_strength(budget, catch_rate, fix_rate)
    return raw + (1.0 - raw) * c_eff


def chain_raw_and_corr(
    depth: int,
    skill: float,
    budget: float,
    eta: float,
    delta: float,
    sigma0: float,
    catch_rate: float,
    fix_rate: float,
) -> tuple[float, float]:
    """Recursive chain: final layer raw and corrected quality."""

    corr_prev = 1.0
    raw = 0.0
    corr = 1.0

    for _ in range(depth):
        raw = F.sigma_raw_fixed_point(skill * corr_prev, eta, delta, sigma_0=sigma0)
        corr = corrected_quality(raw, budget, catch_rate, fix_rate)
        corr_prev = corr

    return raw, corr


def merge_raw_and_corr(
    fan_in: int,
    skill: float,
    budget: float,
    eta: float,
    delta: float,
    sigma0: float,
    catch_rate: float,
    fix_rate: float,
    aggregation: str = "product",
) -> tuple[float, float]:
    """Symmetric fan-in motif: final node raw and corrected quality."""

    parent_raw = baseline_raw(skill, eta, delta, sigma0)
    parent_corr = corrected_quality(parent_raw, budget, catch_rate, fix_rate)

    if aggregation == "product":
        parent_factor = parent_corr**fan_in
    elif aggregation in {"min", "mean"}:
        parent_factor = parent_corr
    else:
        raise ValueError(f"unknown aggregation: {aggregation!r}")

    raw = F.sigma_raw_fixed_point(skill * parent_factor, eta, delta, sigma_0=sigma0)
    corr = corrected_quality(raw, budget, catch_rate, fix_rate)
    return raw, corr


def diamond_fragility(shared_source_catch_rate: float, fan_in: int = 2) -> float:
    """Conditional fragility for a symmetric diamond motif.

    In the paper's mean-field approximation this is topology-sensitive while the
    average raw competence surface matches the corresponding symmetric merge.
    """

    r = float(np.clip(shared_source_catch_rate, 0.0, 0.999999))
    return 1.0 / ((1.0 - r) ** fan_in)


def motif_final_raw(
    spec: MotifSpec,
    skill: float,
    budget: float,
    eta: float,
    delta: float,
    sigma0: float,
    catch_rate: float,
    fix_rate: float,
) -> tuple[float, float]:
    if spec.family == "chain":
        return chain_raw_and_corr(
            spec.depth, skill, budget, eta, delta, sigma0, catch_rate, fix_rate
        )
    if spec.family == "merge":
        return merge_raw_and_corr(
            spec.fan_in, skill, budget, eta, delta, sigma0, catch_rate, fix_rate,
            aggregation=spec.aggregation,
        )
    raise ValueError(f"unknown motif family: {spec.family!r}")


def contour_surface(
    spec: MotifSpec,
    sigma0: float,
    catch_rate: float,
    fix_rate: float,
    a_values: list[float],
    skills: np.ndarray,
    budgets: np.ndarray,
) -> tuple[list[tuple[str, np.ndarray]], np.ndarray, np.ndarray]:
    """Compute delta surfaces for a motif across (skill, budget)."""

    surfaces: list[tuple[str, np.ndarray]] = []
    skill_grid, budget_grid = np.meshgrid(skills, budgets, indexing="xy")

    for a in a_values:
        eta_slice = a
        delta_slice = 1.0 - a
        delta_grid = np.zeros_like(skill_grid)
        for i in range(budget_grid.shape[0]):
            for j in range(budget_grid.shape[1]):
                skill = float(skill_grid[i, j])
                budget = float(budget_grid[i, j])
                raw, _corr = motif_final_raw(
                    spec, skill, budget, eta_slice, delta_slice, sigma0, catch_rate, fix_rate
                )
                base = baseline_raw(skill, eta_slice, delta_slice, sigma0)
                delta_grid[i, j] = raw - base
        surfaces.append((f"a={a:.2f}", delta_grid))

    return surfaces, skill_grid, budget_grid


def plot_curves(
    outdir: Path,
    specs: list[MotifSpec],
    eta: float,
    delta: float,
    sigma0: float,
    catch_rate: float,
    fix_rate: float,
    skill: float,
    budgets: np.ndarray,
) -> Path | None:
    if not MPL_AVAILABLE:
        return None

    fig, ax = plt.subplots(figsize=(9, 5))
    for spec in specs:
        deltas = []
        for b in budgets:
            raw, _corr = motif_final_raw(
                spec, skill, float(b), eta, delta, sigma0, catch_rate, fix_rate
            )
            base = baseline_raw(skill, eta, delta, sigma0)
            deltas.append(raw - base)
        ax.plot(budgets, deltas, linewidth=2, label=spec.name)

    ax.axhline(0.0, color="0.5", linewidth=1)
    ax.set_xlabel("Oversight budget B")
    ax.set_ylabel("Raw competence delta")
    ax.set_title(f"Motif-specific delta at skill={skill:.2f}")
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    path = outdir / "delta_vs_budget.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def plot_surface_grid(
    outdir: Path,
    spec: MotifSpec,
    sigma0: float,
    catch_rate: float,
    fix_rate: float,
    a_values: list[float],
    skills: np.ndarray,
    budgets: np.ndarray,
) -> Path | None:
    if not MPL_AVAILABLE:
        return None

    surfaces, skill_grid, budget_grid = contour_surface(
        spec, sigma0, catch_rate, fix_rate, a_values, skills, budgets
    )

    fig, axes = plt.subplots(
        1,
        len(surfaces),
        figsize=(5.0 * len(surfaces), 4.2),
        sharex=True,
        sharey=True,
        constrained_layout=True,
    )
    if len(surfaces) == 1:
        axes = [axes]

    levels = np.linspace(
        min(surface.min() for _label, surface in surfaces),
        max(surface.max() for _label, surface in surfaces),
        13,
    )

    last_mappable = None
    for ax, (label, surface) in zip(axes, surfaces):
        last_mappable = ax.contourf(skill_grid, budget_grid, surface, levels=levels, cmap="viridis")
        contour = ax.contour(skill_grid, budget_grid, surface, levels=levels[::2], colors="white", linewidths=0.6, alpha=0.8)
        ax.clabel(contour, fmt="%.2f", fontsize=7)
        ax.set_title(label)
        ax.set_xlabel("skill")
        ax.set_xlim(skills.min(), skills.max())
        ax.set_ylim(budgets.min(), budgets.max())

    axes[0].set_ylabel("budget")
    fig.suptitle(f"Raw competence delta surface: {spec.name}")
    if last_mappable is not None:
        fig.colorbar(last_mappable, ax=axes, shrink=0.9, pad=0.02, label="delta raw")

    path = outdir / f"surface_{spec.name.replace(' ', '_')}.png"
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_diamond_fragility(
    outdir: Path,
    fan_ins: list[int],
    shared_source_grid: np.ndarray,
) -> Path | None:
    if not MPL_AVAILABLE:
        return None

    fig, ax = plt.subplots(figsize=(8.2, 5))
    for k in fan_ins:
        vals = [diamond_fragility(r, fan_in=k) for r in shared_source_grid]
        ax.plot(shared_source_grid, vals, linewidth=2, label=f"fan-in={k}")

    ax.set_xlabel("shared-source catch rate")
    ax.set_ylabel("conditional fragility")
    ax.set_title("Diamond fragility rises with shared upstream correction")
    ax.legend(frameon=False)
    fig.tight_layout()
    path = outdir / "diamond_fragility.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def write_csv(
    outdir: Path,
    specs: list[MotifSpec],
    eta: float,
    delta: float,
    sigma0: float,
    catch_rate: float,
    fix_rate: float,
    skill_grid: np.ndarray,
    budget_grid: np.ndarray,
) -> Path:
    path = outdir / "motif_surface_data.csv"
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "motif",
                "family",
                "depth",
                "fan_in",
                "aggregation",
                "skill",
                "budget",
                "eta",
                "delta",
                "sigma0",
                "catch_rate",
                "fix_rate",
                "baseline_raw",
                "final_raw",
                "delta_raw",
                "final_corr",
                "delta_corr",
            ],
        )
        writer.writeheader()
        for spec in specs:
            for skill in skill_grid:
                for budget in budget_grid:
                    raw, corr = motif_final_raw(
                        spec, float(skill), float(budget), eta, delta, sigma0, catch_rate, fix_rate
                    )
                    base = baseline_raw(float(skill), eta, delta, sigma0)
                    writer.writerow(
                        {
                            "motif": spec.name,
                            "family": spec.family,
                            "depth": spec.depth,
                            "fan_in": spec.fan_in,
                            "aggregation": spec.aggregation,
                            "skill": round(float(skill), 6),
                            "budget": round(float(budget), 6),
                            "eta": eta,
                            "delta": delta,
                            "sigma0": sigma0,
                            "catch_rate": catch_rate,
                            "fix_rate": fix_rate,
                            "baseline_raw": round(base, 8),
                            "final_raw": round(raw, 8),
                            "delta_raw": round(raw - base, 8),
                            "final_corr": round(corr, 8),
                            "delta_corr": round(corr - base, 8),
                        }
                    )
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=REPO / "tmp" / "motif_surfaces")
    parser.add_argument("--eta", type=float, default=10.0)
    parser.add_argument("--delta", type=float, default=2.0)
    parser.add_argument("--sigma0", type=float, default=0.0)
    parser.add_argument("--catch-rate", type=float, default=0.70)
    parser.add_argument("--fix-rate", type=float, default=1.0)
    parser.add_argument("--skill-min", type=float, default=0.20)
    parser.add_argument("--skill-max", type=float, default=0.95)
    parser.add_argument("--skill-steps", type=int, default=81)
    parser.add_argument("--budget-steps", type=int, default=81)
    parser.add_argument("--skill-for-lines", type=float, default=0.55)
    args = parser.parse_args()

    outdir = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    skills = np.linspace(args.skill_min, args.skill_max, args.skill_steps)
    budgets = np.linspace(0.0, 1.0, args.budget_steps)

    specs = [
        MotifSpec("chain_depth_1", family="chain", depth=1),
        MotifSpec("chain_depth_2", family="chain", depth=2),
        MotifSpec("chain_depth_3", family="chain", depth=3),
        MotifSpec("merge_k_2_product", family="merge", fan_in=2, aggregation="product"),
        MotifSpec("merge_k_3_product", family="merge", fan_in=3, aggregation="product"),
        MotifSpec("merge_k_2_mean", family="merge", fan_in=2, aggregation="mean"),
        MotifSpec("merge_k_2_min", family="merge", fan_in=2, aggregation="min"),
    ]

    csv_path = write_csv(
        outdir,
        specs,
        args.eta,
        args.delta,
        args.sigma0,
        args.catch_rate,
        args.fix_rate,
        skills,
        budgets,
    )

    a_values = [0.33, 0.50, 0.83]
    surface_paths: list[Path] = []
    for spec in [
        MotifSpec("chain_depth_2", family="chain", depth=2),
        MotifSpec("merge_k_2_product", family="merge", fan_in=2, aggregation="product"),
        MotifSpec("merge_k_3_product", family="merge", fan_in=3, aggregation="product"),
    ]:
        path = plot_surface_grid(
            outdir,
            spec,
            args.sigma0,
            args.catch_rate,
            args.fix_rate,
            a_values,
            skills,
            budgets,
        )
        if path is not None:
            surface_paths.append(path)

    curve_path = plot_curves(
        outdir,
        [
            MotifSpec("chain_depth_1", family="chain", depth=1),
            MotifSpec("chain_depth_2", family="chain", depth=2),
            MotifSpec("chain_depth_3", family="chain", depth=3),
            MotifSpec("merge_k_2_product", family="merge", fan_in=2, aggregation="product"),
            MotifSpec("merge_k_3_product", family="merge", fan_in=3, aggregation="product"),
        ],
        args.eta,
        args.delta,
        args.sigma0,
        args.catch_rate,
        args.fix_rate,
        args.skill_for_lines,
        budgets,
    )

    fragility_path = plot_diamond_fragility(outdir, [2, 3, 4], np.linspace(0.0, 0.8, 200))

    a = observation_share(args.eta, args.delta)
    sample_budget = 0.50
    sample_skill = args.skill_for_lines
    sample_specs = [
        MotifSpec("chain_depth_1", family="chain", depth=1),
        MotifSpec("chain_depth_2", family="chain", depth=2),
        MotifSpec("chain_depth_3", family="chain", depth=3),
        MotifSpec("merge_k_2_product", family="merge", fan_in=2, aggregation="product"),
        MotifSpec("merge_k_3_product", family="merge", fan_in=3, aggregation="product"),
    ]

    print(f"observation_share a = {a:.6f}")
    print(f"baseline raw at skill={sample_skill:.2f}: {baseline_raw(sample_skill, args.eta, args.delta, args.sigma0):.6f}")
    print(f"sample budget B = {sample_budget:.2f}, catch_rate = {args.catch_rate:.2f}, fix_rate = {args.fix_rate:.2f}")
    for spec in sample_specs:
        raw, corr = motif_final_raw(
            spec, sample_skill, sample_budget, args.eta, args.delta, args.sigma0,
            args.catch_rate, args.fix_rate,
        )
        base = baseline_raw(sample_skill, args.eta, args.delta, args.sigma0)
        print(f"{spec.name:>20s}  raw={raw:.6f}  delta={raw - base:+.6f}  corr={corr:.6f}")

    print(f"wrote {csv_path}")
    for p in surface_paths:
        print(f"wrote {p}")
    if curve_path is not None:
        print(f"wrote {curve_path}")
    if fragility_path is not None:
        print(f"wrote {fragility_path}")

    if not MPL_AVAILABLE:
        print("matplotlib unavailable: CSV written, plots skipped", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
