#!/usr/bin/env python3
"""Is the noise floor FUNDAMENTAL, or can a filter average it away? Prove-or-break.

The bounded-memory deadband pays holding overhead Omega(sigma*T). The obvious
objection: filter the noise -- average a window W and the noise falls as
sigma/sqrt(W). The answer is that DRIFT caps the window: averaging W steps lags a
moving target. The two trade off and leave an IRREDUCIBLE tracking error.

Clean rigorous instance -- random-walk drift + Gaussian noise:
    r(t+1) = r(t) + N(0, nu^2)          (drift, increment std nu)
    obs(t) = r(t) + N(0, sigma^2)       (observation noise std sigma)
For this linear-Gaussian model the KALMAN FILTER is the MMSE-optimal causal
estimator (the conditional mean minimises MSE; for linear-Gaussian it is Kalman).
So NO causal estimator beats its steady-state error -- it is a genuine lower bound.

Steady-state posterior variance P solves the scalar Riccati equation
    P = (P + nu^2) sigma^2 / (P + nu^2 + sigma^2)   ==>  P^2 + nu^2 P - nu^2 sigma^2 = 0
    P* = ( -nu^2 + sqrt(nu^4 + 4 nu^2 sigma^2) ) / 2 ,   and for nu << sigma,  P* -> nu*sigma.
So the irreducible RMS tracking error is sqrt(P*) ~ (nu*sigma)^{1/2} > 0 for nu>0.

Propagation to the controller. To stay feasible (b >= true r) w.p. >= 1-delta with a
causal estimate of error std eps, the held margin must be >= z_delta*eps, which is
pure holding overhead vs the clairvoyant optimum. Hence:

  Thm 3' (fundamental noise floor).  Every causal controller maintaining feasibility
  w.p. >= 1-delta incurs holding regret >= z_delta * sqrt(P*) * T = Omega(sqrt(nu*sigma)*T),
  and a Kalman-filter + margin controller MATCHES it. The unfiltered deadband pays
  z_delta*sigma*T -- larger by sqrt(sigma/nu); filtering closes the gap to the floor
  but cannot remove it. (Worst-case Lipschitz drift of slope nu gives the stronger
  rate sigma^{2/3} nu^{1/3}; the random walk is the clean provable case.)

This script BREAKS the theorem if it can: it pits Kalman against a zoo of causal
estimators (moving averages, EWMA, raw) and checks (a) nothing beats Kalman,
(b) Kalman's error equals sqrt(P*), (c) the regret floor scales as sqrt(nu*sigma).

Run:  python3 scripts/online_tracking.py
"""

from __future__ import annotations

import math

import numpy as np

Z_DELTA = 2.054          # one-sided Phi^{-1}(0.98): feasibility target 1-delta = 0.98
T = 60_000               # steps per trial (long, for steady-state statistics)
SEED = 11


# ----------------------------- the instance -------------------------------- #
def simulate(nu, sigma, T=T, seed=SEED):
    """Random-walk drift r(t) and its noisy observation obs(t)."""
    rng = np.random.default_rng(seed)
    steps = rng.normal(0.0, nu, T)
    r = np.cumsum(steps)                      # pure random walk (translation-free)
    obs = r + rng.normal(0.0, sigma, T)
    return r, obs


def kalman_steadystate_P(nu, sigma):
    """Closed-form steady-state posterior variance P* of the scalar KF."""
    Q, R = nu * nu, sigma * sigma
    return (-Q + math.sqrt(Q * Q + 4 * Q * R)) / 2.0


# ---------------------------- causal estimators ---------------------------- #
def est_kalman(obs, nu, sigma):
    Q, R = nu * nu, sigma * sigma
    xhat, P = obs[0], R
    out = np.empty_like(obs)
    for t in range(len(obs)):
        P_pred = P + Q                        # predict
        K = P_pred / (P_pred + R)             # gain
        xhat = xhat + K * (obs[t] - xhat)     # update on obs(t)
        P = (1 - K) * P_pred
        out[t] = xhat
    return out


def est_movavg(obs, W):
    """Causal moving average of the last W observations."""
    c = np.cumsum(np.insert(obs, 0, 0.0))
    out = np.empty_like(obs)
    for t in range(len(obs)):
        lo = max(0, t - W + 1)
        out[t] = (c[t + 1] - c[lo]) / (t + 1 - lo)
    return out


def est_ewma(obs, alpha):
    out = np.empty_like(obs)
    x = obs[0]
    for t in range(len(obs)):
        x = alpha * obs[t] + (1 - alpha) * x
        out[t] = x
    return out


def rmse(est, r, burn=2000):
    e = est[burn:] - r[burn:]
    return float(np.sqrt(np.mean(e * e)))


# --------------------------------- tests ----------------------------------- #
def test_nothing_beats_kalman():
    print("(1) Causal-estimator zoo vs Kalman (nu=0.02, sigma=0.20): RMSE, lower is "
          "better")
    nu, sigma = 0.02, 0.20
    r, obs = simulate(nu, sigma)
    Pstar = kalman_steadystate_P(nu, sigma)
    cands = {"kalman": est_kalman(obs, nu, sigma),
             "raw (W=1)": obs,
             "movavg W=5": est_movavg(obs, 5),
             "movavg W=sqrt(s/nu)~?": est_movavg(obs, max(1, round(sigma / nu))),
             "movavg W=50": est_movavg(obs, 50),
             "movavg W=200": est_movavg(obs, 200),
             "ewma a=0.1": est_ewma(obs, 0.1),
             "ewma a=0.3": est_ewma(obs, 0.3)}
    results = {k: rmse(v, r) for k, v in cands.items()}
    kal = results["kalman"]
    for k in sorted(results, key=results.get):
        tag = "  <- MMSE-optimal" if k == "kalman" else ""
        worse = f"  (+{100*(results[k]/kal - 1):.0f}% vs Kalman)" if k != "kalman" else ""
        print(f"    {k:24s} RMSE={results[k]:.4f}{worse}{tag}")
    print(f"    theory sqrt(P*) = {math.sqrt(Pstar):.4f}   "
          f"Kalman empirical = {kal:.4f}")
    assert abs(kal - math.sqrt(Pstar)) < 0.02 * math.sqrt(Pstar) + 1e-3, (kal, Pstar)
    assert kal <= min(results.values()) + 1e-9, "something beat Kalman -- theorem BROKEN"
    print("    -> nothing beats Kalman; its error == sqrt(P*).  Floor is real.\n")


def test_floor_scales_sqrt_nu_sigma():
    print("(2) Does the holding-regret floor scale as sqrt(nu*sigma)?  "
          "(regret = z*RMSE_kalman)")
    print(f"    {'nu':>6s} {'sigma':>7s} {'sqrt(nu*sigma)':>15s} {'kalman RMSE':>12s} "
          f"{'regret/T':>9s} {'regret/(z*sqrt(nu*sig))':>24s}")
    ratios = []
    for nu, sigma in [(0.01, 0.10), (0.01, 0.40), (0.04, 0.10), (0.04, 0.40),
                      (0.02, 0.20), (0.005, 0.20), (0.02, 0.05)]:
        r, obs = simulate(nu, sigma)
        kr = rmse(est_kalman(obs, nu, sigma), r)
        regret = Z_DELTA * kr                       # per-step holding overhead floor
        ref = math.sqrt(nu * sigma)
        ratio = regret / (Z_DELTA * ref)
        ratios.append(ratio)
        print(f"    {nu:6.3f} {sigma:7.2f} {ref:15.4f} {kr:12.4f} {regret:9.4f} "
              f"{ratio:24.3f}")
    spread = max(ratios) / min(ratios)
    print(f"    -> ratio is ~constant (spread {spread:.2f}x) => regret floor = "
          f"Theta(sqrt(nu*sigma)).")
    assert spread < 1.3, f"sqrt(nu*sigma) law violated (spread {spread:.2f})"
    print()


def test_filter_beats_deadband_but_not_to_zero():
    print("(3) Filtering helps but cannot reach zero (vs the unfiltered deadband):")
    print(f"    {'nu':>6s} {'sigma':>7s} {'deadband margin z*sigma':>24s} "
          f"{'kalman margin z*sqrt(P*)':>26s} {'gain':>6s}")
    for nu, sigma in [(0.02, 0.20), (0.005, 0.20), (0.001, 0.20)]:
        r, obs = simulate(nu, sigma)
        kr = rmse(est_kalman(obs, nu, sigma), r)
        m_dead = Z_DELTA * sigma
        m_kal = Z_DELTA * kr
        print(f"    {nu:6.3f} {sigma:7.2f} {m_dead:24.3f} {m_kal:26.3f} "
              f"{m_dead/m_kal:5.1f}x")
    print("    -> as drift nu -> 0 the filter wins more (sqrt(sigma/nu)); but for "
          "any nu>0 the floor z*sqrt(nu*sigma) > 0.\n")


def test_feasibility_calibrated():
    print("(4) Sanity: margin = z*RMSE delivers the target feasibility (~98%):")
    nu, sigma = 0.02, 0.20
    r, obs = simulate(nu, sigma)
    for name, est in (("kalman", est_kalman(obs, nu, sigma)), ("raw", obs)):
        e = est - r
        kr = math.sqrt(np.mean((e[2000:]) ** 2))
        b = est + Z_DELTA * kr
        feas = np.mean(b[2000:] >= r[2000:])
        print(f"    {name:8s} feasible = {feas*100:.1f}%  (target 98%)")
    print()


def main() -> int:
    print("=" * 76)
    print("Fundamental noise floor: tracking lower bound (Kalman-optimal) "
          "-- prove or break")
    print("=" * 76 + "\n")
    test_nothing_beats_kalman()
    test_floor_scales_sqrt_nu_sigma()
    test_filter_beats_deadband_but_not_to_zero()
    test_feasibility_calibrated()
    print("VERDICT: the noise floor is fundamental -- Omega(sqrt(nu*sigma)) per step, "
          "Kalman-matched,\n         filter-proof for any drift nu > 0.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
