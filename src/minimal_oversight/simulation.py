"""Simulation: synthetic engine for what-if analysis and notebooks.

Subordinate module. Useful for:
    - Reproducing paper experiments
    - What-if analysis on parameter changes
    - Stress-testing topologies
    - Generating synthetic traces for demos

Not the center of the package.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from minimal_oversight import _formulae as F
from minimal_oversight.models import PipelineGraph, WorkflowTrace


@dataclass
class SimulationConfig:
    """Configuration for a delegation simulation."""

    n_steps: int = 200
    n_scope: int = 100
    dt: float = 0.1
    eta: float = 10.0
    delta: float = 2.0
    seed: int | None = None


@dataclass
class SimulationResult:
    """Result of a simulation run."""

    sigma_raw_history: np.ndarray  # shape: (n_steps, n_nodes)
    sigma_corr_history: np.ndarray
    masking_history: np.ndarray
    node_names: list[str]
    config: SimulationConfig


def simulate_single_node(
    sigma_skill: float = 0.55,
    catch_rate: float = 0.65,
    review_capacity: float = 0.50,
    n_steps: int = 200,
    n_scope: int = 100,
    eta: float = 10.0,
    delta: float = 2.0,
    drift_rate: float = 0.0,
    dt: float = 0.1,
    seed: int | None = None,
) -> dict[str, np.ndarray]:
    """Simulate a single delegation node with mean-field ODE dynamics.

    Returns dict with keys: sigma_raw, sigma_corr, masking_index, steps.
    """
    rng = np.random.default_rng(seed)

    sigma_raw = np.zeros(n_steps)
    sigma_corr = np.zeros(n_steps)
    sigma_raw[0] = 0.5  # initial estimate

    current_skill = sigma_skill

    for t in range(1, n_steps):
        # Drift
        current_skill = max(0.01, current_skill - drift_rate * dt)

        # Return Operator ODE step
        sigma_raw[t] = F.return_operator_step(
            sigma_raw[t - 1], current_skill, eta, delta, dt
        )

        # Add Bernoulli noise (finite-sample effect)
        noise = rng.normal(0, 0.01 / np.sqrt(n_scope))
        sigma_raw[t] = np.clip(sigma_raw[t] + noise, 0.01, 0.99)

        # Corrector
        sigma_corr[t] = (
            sigma_raw[t] + (1 - sigma_raw[t]) * catch_rate * review_capacity
        )

    masking = np.where(sigma_raw > 0, sigma_corr / sigma_raw, 1.0)

    return {
        "sigma_raw": sigma_raw,
        "sigma_corr": sigma_corr,
        "masking_index": masking,
        "steps": np.arange(n_steps),
    }


def simulate_pipeline(
    pipeline: PipelineGraph,
    config: SimulationConfig | None = None,
) -> SimulationResult:
    """Simulate the full pipeline in topological order.

    Each node's effective skill depends on upstream corrected quality.
    """
    if config is None:
        config = SimulationConfig()

    rng = np.random.default_rng(config.seed)
    order = pipeline.topological_order()
    n_nodes = len(order)

    sigma_raw_h = np.zeros((config.n_steps, n_nodes))
    sigma_corr_h = np.zeros((config.n_steps, n_nodes))

    # Initialize
    for j in range(n_nodes):
        sigma_raw_h[0, j] = 0.5

    node_idx = {name: i for i, name in enumerate(order)}

    for t in range(1, config.n_steps):
        for j, name in enumerate(order):
            node = pipeline.get_node(name)
            sigma_skill = node.sigma_skill if node.sigma_skill is not None else 0.55
            catch_rate = node.catch_rate if node.catch_rate is not None else 0.65
            review_cap = node.review_capacity if node.review_capacity is not None else 0.50

            # Effective skill from parents
            parents = pipeline.parents(name)
            if parents:
                parent_corrs = [sigma_corr_h[t - 1, node_idx[p]] for p in parents]
                agg = node.aggregation.value
                skill_eff = F.effective_skill(sigma_skill, parent_corrs, agg)
            else:
                skill_eff = sigma_skill

            # Drift
            drift = node.drift_rate if node.drift_rate is not None else 0.0
            skill_eff = max(0.01, skill_eff - drift * config.dt)

            # ODE step
            sigma_raw_h[t, j] = F.return_operator_step(
                sigma_raw_h[t - 1, j], skill_eff, config.eta, config.delta, config.dt
            )

            # Noise
            noise = rng.normal(0, 0.01 / np.sqrt(config.n_scope))
            sigma_raw_h[t, j] = np.clip(sigma_raw_h[t, j] + noise, 0.01, 0.99)

            # Corrector
            sigma_corr_h[t, j] = (
                sigma_raw_h[t, j]
                + (1 - sigma_raw_h[t, j]) * catch_rate * review_cap
            )

    masking_h = np.where(sigma_raw_h > 0, sigma_corr_h / sigma_raw_h, 1.0)

    return SimulationResult(
        sigma_raw_history=sigma_raw_h,
        sigma_corr_history=sigma_corr_h,
        masking_history=masking_h,
        node_names=order,
        config=config,
    )


def generate_synthetic_traces(
    pipeline: PipelineGraph,
    n_items: int = 500,
    seed: int | None = None,
) -> list[WorkflowTrace]:
    """Generate synthetic WorkflowTrace objects for testing and demos."""
    rng = np.random.default_rng(seed)
    order = pipeline.topological_order()
    traces: list[WorkflowTrace] = []

    for i in range(n_items):
        outcomes: dict[str, float] = {}
        corrected: dict[str, float] = {}
        reviewed: dict[str, bool] = {}

        for name in order:
            node = pipeline.get_node(name)
            sigma_skill = node.sigma_skill if node.sigma_skill is not None else 0.55
            catch_rate = node.catch_rate if node.catch_rate is not None else 0.65
            review_cap = node.review_capacity if node.review_capacity is not None else 0.50

            # Effective skill
            parents = pipeline.parents(name)
            if parents:
                parent_corrs = [corrected.get(p, 0.8) for p in parents]
                agg = node.aggregation.value
                skill_eff = F.effective_skill(sigma_skill, parent_corrs, agg)
            else:
                skill_eff = sigma_skill

            # Raw outcome
            raw = float(rng.random() < skill_eff)
            outcomes[name] = raw

            # Review decision
            is_reviewed = rng.random() < review_cap
            reviewed[name] = bool(is_reviewed)

            # Correction
            if raw == 0.0 and is_reviewed and rng.random() < catch_rate:
                corrected[name] = 1.0
            else:
                corrected[name] = raw

        traces.append(WorkflowTrace(
            task_id=f"item_{i:04d}",
            node_outcomes=outcomes,
            node_corrected=corrected,
            routing_path=order,
            timestamps={name: float(j) for j, name in enumerate(order)},
            was_reviewed=reviewed,
        ))

    return traces
