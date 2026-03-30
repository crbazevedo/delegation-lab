"""Private module: pure math from the paper.

Every numbered equation lives here. Public modules call into this;
practitioners should never need to import it directly.

Equations are referenced by their number in:
    "Minimal Oversight: A Theory of Principled Autonomy Delegation"
    Carlos R. B. Azevedo, 2026.
"""

from __future__ import annotations

import numpy as np


# ---------------------------------------------------------------------------
# Fisher information (Equation 3, Box 1)
# ---------------------------------------------------------------------------

def fisher_information(sigma: float | np.ndarray) -> float | np.ndarray:
    """Fisher information for Bernoulli outcomes: g(σ) = 1 / [σ(1−σ)].

    Ref: Equation 3.
    """
    sigma = np.asarray(sigma, dtype=float)
    # Regularize to avoid division by zero at boundaries
    eps = 1e-10
    s = np.clip(sigma, eps, 1.0 - eps)
    return 1.0 / (s * (1.0 - s))


def fisher_volume_element(sigma: float | np.ndarray) -> float | np.ndarray:
    """sqrt(g(σ)) = 1 / sqrt(σ(1−σ)).

    Used as the cost weight in the AMO.
    """
    sigma = np.asarray(sigma, dtype=float)
    eps = 1e-10
    s = np.clip(sigma, eps, 1.0 - eps)
    return 1.0 / np.sqrt(s * (1.0 - s))


# ---------------------------------------------------------------------------
# Return Operator (Equations 4, 5, 6)
# ---------------------------------------------------------------------------

def sigma_raw_fixed_point(
    sigma_skill: float,
    eta: float,
    delta: float,
) -> float:
    """Fixed-point raw competence: σ*_raw = η·σ_skill / (η + δ).

    Ref: Equation 5.

    Args:
        sigma_skill: Agent's true competence.
        eta: Observation rate.
        delta: Decay rate.
    """
    return eta * sigma_skill / (eta + delta)


def sigma_corr_fixed_point(
    sigma_raw_star: float,
    catch_rate: float,
) -> float:
    """Fixed-point corrected quality: σ*_corr = σ*_raw + (1 − σ*_raw) × c.

    Ref: Equation 6.

    Args:
        sigma_raw_star: Fixed-point raw competence.
        catch_rate: Corrector catch probability *c*.
    """
    return sigma_raw_star + (1.0 - sigma_raw_star) * catch_rate


def masking_index(sigma_corr: float, sigma_raw: float) -> float:
    """M* = σ_corr / σ_raw. Values > 1 indicate masking.

    Ref: Follows from Equation 6.
    """
    if sigma_raw <= 0:
        return float("inf")
    return sigma_corr / sigma_raw


def return_operator_step(
    sigma: float,
    sigma_skill_eff: float,
    eta: float,
    delta: float,
    dt: float,
) -> float:
    """One Euler step of the Return Operator ODE.

    dσ/dt = η(σ_skill_eff − σ) − δσ

    Ref: Equation 4.
    """
    dsigma = eta * (sigma_skill_eff - sigma) - delta * sigma
    return sigma + dsigma * dt


# ---------------------------------------------------------------------------
# Water-filling / Euler-Lagrange (Equation 8)
# ---------------------------------------------------------------------------

def optimal_authority(
    sigma_raw: np.ndarray,
    lam: float,
    alpha_max: float = 1.0,
) -> np.ndarray:
    """Euler-Lagrange water-filling solution for α*(x).

    α*(x) = min(α_max, (λ/2) · σ_raw · √(σ_raw(1 − σ_raw)))

    Ref: Equation 8.

    Args:
        sigma_raw: Array of raw competence values across scope.
        lam: Lagrange multiplier (water level), determined by delivery constraint.
        alpha_max: Maximum authority ceiling.

    Returns:
        Array of optimal authority allocations.
    """
    sigma = np.asarray(sigma_raw, dtype=float)
    eps = 1e-10
    s = np.clip(sigma, eps, 1.0 - eps)
    alpha_star = (lam / 2.0) * s * np.sqrt(s * (1.0 - s))
    return np.minimum(alpha_star, alpha_max)


def solve_lambda(
    sigma_raw: np.ndarray,
    p_min: float,
    alpha_max: float = 1.0,
    tol: float = 1e-8,
    max_iter: int = 200,
) -> float:
    """Find the Lagrange multiplier λ satisfying the delivery constraint.

    ∫ α*(x) · σ_raw(x) dx ≥ p_min · |S|

    Uses bisection on λ.
    """
    sigma = np.asarray(sigma_raw, dtype=float)
    n = len(sigma)
    target = p_min * n

    # Upper bound search
    lam_lo, lam_hi = 0.0, 1.0
    for _ in range(50):
        alpha = optimal_authority(sigma, lam_hi, alpha_max)
        if np.sum(alpha * sigma) >= target:
            break
        lam_hi *= 2.0

    # Bisection
    for _ in range(max_iter):
        lam_mid = (lam_lo + lam_hi) / 2.0
        alpha = optimal_authority(sigma, lam_mid, alpha_max)
        delivery = np.sum(alpha * sigma)
        if abs(delivery - target) < tol:
            break
        if delivery < target:
            lam_lo = lam_mid
        else:
            lam_hi = lam_mid

    return (lam_lo + lam_hi) / 2.0


# ---------------------------------------------------------------------------
# Effective skill with upstream quality (Equation 7)
# ---------------------------------------------------------------------------

def effective_skill(
    sigma_skill: float,
    parent_sigma_corrs: list[float],
    aggregation: str = "product",
) -> float:
    """Effective skill at a node given upstream corrected qualities.

    σ_skill,eff(v) = σ_skill(v) × AGG(σ_corr(u1), ..., σ_corr(uk))

    Ref: Equation 7.
    """
    if not parent_sigma_corrs:
        return sigma_skill

    parents = np.array(parent_sigma_corrs)
    if aggregation == "product":
        agg = float(np.prod(parents))
    elif aggregation == "min":
        agg = float(np.min(parents))
    elif aggregation == "mean":
        agg = float(np.mean(parents))
    else:
        raise ValueError(f"Unknown aggregation: {aggregation!r}")

    return sigma_skill * agg


# ---------------------------------------------------------------------------
# Delegation capacity (Equations 10, 11, 13)
# ---------------------------------------------------------------------------

def node_capacity(eta: float, delta: float) -> float:
    """Single-node operational capacity: C = η / (η + δ).

    Achieved when σ_skill = 1.

    Ref: Follows from Equation 10 + Equation 5.
    """
    return eta / (eta + delta)


def recursive_chain_quality(
    depth: int,
    sigma_skill: float,
    catch_rate: float,
    eta: float,
    delta: float,
) -> float:
    """Recursive chain quality C_op(D) for a linear chain of identical layers.

    Each layer's effective skill depends on the previous layer's corrected output.

    Ref: Equation 11.
    """
    sigma_corr_prev = 1.0  # input quality at layer 0
    for _ in range(depth):
        sigma_skill_eff = sigma_skill * sigma_corr_prev
        sigma_raw_star = sigma_raw_fixed_point(sigma_skill_eff, eta, delta)
        sigma_corr_prev = sigma_corr_fixed_point(sigma_raw_star, catch_rate)
    return sigma_corr_prev


def channel_capacity_single_letter(
    budget: float,
    epsilon_0: float,
    epsilon_1: float,
) -> float:
    """Single-letter delegation channel capacity C_del(B).

    C_del(B) = (1−B)[1 − H_b(ε₀)] + B[1 − H_b(ε₁)]

    Ref: Equation 13.
    """

    def h_b(p: float) -> float:
        """Binary entropy."""
        if p <= 0 or p >= 1:
            return 0.0
        return -p * np.log2(p) - (1 - p) * np.log2(1 - p)

    return (1 - budget) * (1 - h_b(epsilon_0)) + budget * (1 - h_b(epsilon_1))


# ---------------------------------------------------------------------------
# Process entropy and capacity (Equations 14, 15, 16, 17)
# ---------------------------------------------------------------------------

def effective_autonomy_buffer(
    c_op: float,
    p_min: float,
    lam: float,
    h_w: float,
) -> float:
    """Effective autonomy buffer: B_eff = C_op − p_min − λH(W).

    Ref: Equation 16.
    """
    return c_op - p_min - lam * h_w


def autonomy_time(
    c_op: float,
    p_min: float,
    lam: float,
    h_w: float,
    mu_eff: float,
) -> float:
    """Expected time before intervention: T*_auto = B_eff / μ_eff.

    Ref: Equation 17.
    """
    b_eff = effective_autonomy_buffer(c_op, p_min, lam, h_w)
    if mu_eff <= 0:
        return float("inf") if b_eff > 0 else 0.0
    return max(b_eff / mu_eff, 0.0)


def critical_entropy(c_op: float, p_min: float, lam: float) -> float:
    """Capacity cliff: H_crit = (C_op − p_min) / λ.

    Above H_crit, autonomous operation is impossible.

    Ref: Section 4, Demonstration 7.
    """
    if lam <= 0:
        return float("inf")
    return (c_op - p_min) / lam


def max_pipeline_depth(
    sigma_skill: float,
    catch_rate: float,
    p_min: float,
    eta: float = 10.0,
    delta: float = 2.0,
) -> float:
    """Critical depth D_max beyond which adding layers hurts quality.

    Computed via the product formula: D_max ≈ ln(p_min) / ln(σ*_corr),
    where σ*_corr is the single-layer corrected quality at fixed point.

    Ref: Section 4, Demonstration 4.
    """
    if sigma_skill <= 0 or p_min <= 0:
        return 0.0
    # Single-layer corrected quality
    sigma_raw_star = sigma_raw_fixed_point(sigma_skill, eta, delta)
    sigma_corr_star = sigma_corr_fixed_point(sigma_raw_star, catch_rate)
    if sigma_corr_star >= 1.0:
        return float("inf")
    if sigma_corr_star <= 0.0 or sigma_corr_star <= p_min:
        return 0.0
    return np.log(p_min) / np.log(sigma_corr_star)


# ---------------------------------------------------------------------------
# Corrector capacity threshold
# ---------------------------------------------------------------------------

def corrector_capacity_threshold(
    p_min: float,
    sigma_skill: float,
    catch_rate: float,
) -> float:
    """Minimum K/N for the delegation to be feasible.

    K/N > (p_min − σ*) / [(1 − σ*) × c]

    Ref: Section 1, Euler-Lagrange Solution.
    """
    sigma_star = sigma_skill  # simplified: at fixed point with high eta
    if catch_rate <= 0 or (1 - sigma_star) <= 0:
        return float("inf")
    return (p_min - sigma_star) / ((1 - sigma_star) * catch_rate)


# ---------------------------------------------------------------------------
# SOTA priority score (Heuristic)
# ---------------------------------------------------------------------------

def sota_priority_score(
    delegation_centrality: float,
    masking: float,
    kappa: float,
) -> float:
    """S(v) = DC(v) × M*(v) × κ(v).

    Proxy for ∂T*_auto/∂c(v) when exact sensitivities are unavailable.

    Ref: Section 4, Demonstration 1.

    Args:
        delegation_centrality: DC(v) — fan-out degree weighted by downstream depth.
        masking: M*(v) — masking index at node v.
        kappa: κ(v) = 1 − σ_skill(v) — task complexity.
    """
    return delegation_centrality * masking * kappa
