#!/usr/bin/env python3
"""Pool-squat separation lemma -- the AAMAS friction-version DECISION GATE.

Question (prove-or-break): in a costed-report ski-rental review gate with a
strategically-misreporting worker, does COMMITTING to the gate policy strictly
beat the MYOPIC (no-commitment) gate by a margin G0 > 0 -- OR does it collapse
to G0 == 0 the way the bare coverage Stackelberg game did (T-STACK, where the
leader's review cost kappa*||b||_1 was attacker-INDEPENDENT, hence timing-
invariant, hence minimax => commitment worthless)?

We do NOT trust closed-form algebra alone. MYO and COMMITTED are each computed
by EXPLICIT equilibrium enumeration over the discretized strategy space, then
compared against the hand-derived closed form. If the brute force disagrees with
the closed form, the theory is wrong and the run says so.

Cost model is the SOURCE ski-rental kernel (scripts/online_skirental.py):
    hold-through cost  = tau            (rent: slot funded tau steps)
    release cost       = 2*lambda       (buy: release + re-acquire at need)
    efficient per-type = min(tau, 2*lambda)

Players (Stackelberg):
    Nature draws type theta in {L,H}, P=1/2 each; tau_L < 2*lambda < tau_H.
      (worker observes theta; supervisor observes realized tau only EX POST)
    Worker: squatting bias beta>0 (private benefit from HOLD); limited
      liability T_max (max penalty it can be charged); may misreport.
    Supervisor: a gate mapping report -> {HOLD, RELEASE}; channel costs c_msg.

MYO  = best NO-COMMITMENT outcome (cheap talk; worker best-responds, supervisor
       best-responds to posterior). COMMITTED = best Stackelberg commitment to a
       (report -> action, contradicted-report -> penalty<=T_max) mechanism with
       EX-POST verification of tau. G0 = MYO - COMMITTED.
"""
from __future__ import annotations

import itertools
import math


def sys_cost(action: str, tau: float, lam: float) -> float:
    """System (supervisor) cost of a gate action given the realized slack tau."""
    return tau if action == "HOLD" else 2.0 * lam      # HOLD=rent tau ; RELEASE=buy 2lambda


def first_best(tau_L, tau_H, lam, p=0.5):
    return p * min(tau_L, 2 * lam) + (1 - p) * min(tau_H, 2 * lam)


# --------------------------------------------------------------------------- #
#  MYOPIC GATE: best no-commitment (cheap-talk) outcome, by PBE enumeration.   #
# --------------------------------------------------------------------------- #
def myopic_value(tau_L, tau_H, lam, beta, p=0.5):
    """Enumerate every (worker report strategy, supervisor action map) profile,
    keep those that are a mutual best response (a PBE of the cheap-talk game),
    and return the supervisor's expected cost in the WORKER-PREFERRED such
    equilibrium (the realistic no-commitment outcome). Also return whether any
    SEPARATING equilibrium exists (it must not, when beta>0)."""
    types = [("L", tau_L), ("H", tau_H)]
    msgs = [0, 1]
    actions = ["HOLD", "RELEASE"]

    def worker_util(action, beta):
        return beta if action == "HOLD" else 0.0       # squatting: HOLD worth beta

    best_cost, separating_exists = None, False
    # supervisor policy: msg -> action  (4 maps); worker policy: type -> msg (4 maps)
    for sup in itertools.product(actions, repeat=len(msgs)):      # sup[m]
        sup_map = {m: sup[i] for i, m in enumerate(msgs)}
        for wk in itertools.product(msgs, repeat=len(types)):     # wk[type-index]
            wk_map = {types[i][0]: wk[i] for i in range(len(types))}
            # (a) worker best-responds: for each type, its chosen msg maximizes util
            worker_ok = True
            for ti, (tn, tv) in enumerate(types):
                chosen = wk_map[tn]
                u_chosen = worker_util(sup_map[chosen], beta)
                for m in msgs:
                    if worker_util(sup_map[m], beta) > u_chosen + 1e-12:
                        worker_ok = False
                        break
                if not worker_ok:
                    break
            if not worker_ok:
                continue
            # (b) supervisor best-responds to the posterior induced by each msg.
            sup_ok = True
            for m in msgs:
                senders = [(tn, tv) for (tn, tv) in types if wk_map[tn] == m]
                if not senders:
                    continue  # off-path msg; any action sustainable, skip the check
                # posterior given msg m (uniform over senders, equal prior)
                e_hold = sum(tv for _, tv in senders) / len(senders)
                e_rel = 2 * lam
                best_action = "HOLD" if e_hold <= e_rel else "RELEASE"
                # supervisor's prescribed action must itself be a best response
                pres = sup_map[m]
                cost_pres = e_hold if pres == "HOLD" else e_rel
                cost_best = min(e_hold, e_rel)
                if cost_pres > cost_best + 1e-12:
                    sup_ok = False
                    break
            if not sup_ok:
                continue
            # this profile is a PBE; compute supervisor expected cost
            ecost = sum(p * sys_cost(sup_map[wk_map[tn]], tv, lam) for tn, tv in types)
            # separating == the two types send different msgs
            if wk_map["L"] != wk_map["H"]:
                separating_exists = True
            if best_cost is None or ecost > best_cost:   # worker-preferred = highest sup cost
                best_cost = ecost
    return best_cost, separating_exists


# --------------------------------------------------------------------------- #
#  COMMITTED GATE: Stackelberg commitment with ex-post-verified penalty.       #
# --------------------------------------------------------------------------- #
def committed_value(tau_L, tau_H, lam, beta, T_max, c_msg, p=0.5, grid=400):
    """Supervisor commits to: report theta_hat -> action a(theta_hat), and a
    penalty pen in [0, T_max] charged when the EX-POST tau contradicts the
    report (reported 'soon/L' but tau came late, or vice-versa). Worker then
    best-responds. Minimize E[system action cost] + c_msg over the committed
    rule. (On-path truth-telling => no penalty is actually paid.)"""
    types = [("L", tau_L), ("H", tau_H)]
    # The only useful separating rule maps L->HOLD, H->RELEASE (the efficient one);
    # also allow the two pooling rules (always-HOLD, always-RELEASE) at zero channel.
    best = math.inf
    # candidate committed action rules: dict type-report -> action
    rules = [
        {"L": "HOLD", "H": "RELEASE"},   # efficient separation (needs IC)
        {"L": "HOLD", "H": "HOLD"},      # pool hold
        {"L": "RELEASE", "H": "RELEASE"},# pool release
    ]
    for rule in rules:
        separating = rule["L"] != rule["H"]
        for k in range(grid + 1):
            pen = T_max * k / grid
            # worker BR: each true type picks the report maximizing
            #   beta*1[action=HOLD] - pen*1[report contradicted by ex-post tau]
            # 'contradicted' = reported the OTHER type's label (deterministic here).
            reported = {}
            for tn, tv in types:
                best_u, best_r = -math.inf, None
                for rep in ("L", "H"):
                    a = rule[rep]
                    contradicted = (rep != tn)          # ex-post tau reveals true tn
                    u = (beta if a == "HOLD" else 0.0) - (pen if contradicted else 0.0)
                    if u > best_u + 1e-12:
                        best_u, best_r = u, rep
                reported[tn] = best_r
            # resulting action per true type and expected system cost
            ecost = sum(p * sys_cost(rule[reported[tn]], tv, lam) for tn, tv in types)
            # channel paid only if the rule actually conditions on the report
            channel = c_msg if separating else 0.0
            total = ecost + channel
            if total < best - 1e-15:
                best = total
    return best


def g0_closed_form(tau_L, tau_H, lam, beta, T_max, c_msg, p=0.5):
    """Closed-form prediction, matching the brute-force equilibrium solver.

    Worker-preferred (adversarial) selection: without commitment the worker pools
    on the supervisor-worst message, so the myopic gate is stuck on the best
    PRIOR-ONLY action MYO = min(E[tau], 2*lambda) -- regardless of beta (at beta=0
    the indifferent worker still pools under the adversarial tie-break). With
    commitment + ex-post verification, truthful separation is IC iff T_max >= beta,
    yielding first-best; and the committed gate DECLINES the channel whenever it is
    not worth it, so commitment WEAKLY DOMINATES: G0 = max(0, VoI - c_msg)."""
    myo = min(p * tau_L + (1 - p) * tau_H, 2 * lam)
    fb = first_best(tau_L, tau_H, lam, p)
    straddle = (tau_L < 2 * lam < tau_H)
    # Separation needs a STRICT penalty pen>beta to deter the squatting lie under
    # the adversarial tie-break; feasible iff T_max>beta (knife-edge T_max==beta
    # fails -- the indifferent worker lies). This is the limited-liability frontier.
    if T_max > beta and straddle:
        committed = min(myo, fb + c_msg)     # decline channel if VoI <= c_msg
    else:
        committed = myo                       # cannot separate / nothing to gain
    return myo - committed, (myo, committed)


# --------------------------------------------------------------------------- #
def check(tau_L, tau_H, lam, beta, T_max, c_msg, p=0.5, verbose=False):
    myo, sep = myopic_value(tau_L, tau_H, lam, beta, p)
    com = committed_value(tau_L, tau_H, lam, beta, T_max, c_msg, p)
    g0 = myo - com
    g0_cf, (myo_cf, com_cf) = g0_closed_form(tau_L, tau_H, lam, beta, T_max, c_msg, p)
    ok = abs(g0 - g0_cf) < 1e-6 and abs(myo - myo_cf) < 1e-6 and abs(com - com_cf) < 1e-6
    if verbose:
        print(f"  lam={lam} tauL={tau_L} tauH={tau_H} beta={beta} Tmax={T_max} "
              f"c_msg={c_msg}")
        print(f"     MYO  brute={myo:.4f} cf={myo_cf:.4f}   sep_exists={sep}")
        print(f"     COMM brute={com:.4f} cf={com_cf:.4f}")
        print(f"     G0   brute={g0:.4f} cf={g0_cf:.4f}   {'OK' if ok else 'MISMATCH!!'}")
    return ok, g0, sep


def main():
    print("=" * 72)
    print("POOL-SQUAT SEPARATION LEMMA -- prove-or-break decision gate")
    print("=" * 72)

    print("\n[1] Brute-force equilibrium == closed form, over a random-ish grid:")
    allok = True
    grid = []
    for lam in (5, 10):
        for tau_L in (1, 3, 6):
            for tau_H in (15, 30, 60):
                for beta in (0.0, 2.0):
                    for T_max in (0.0, 1.0, 5.0):
                        for c_msg in (0.0, 0.5, 3.0, 100.0):
                            if not (tau_L < 2 * lam < tau_H):
                                continue
                            ok, g0, sep = check(tau_L, tau_H, lam, beta, T_max, c_msg)
                            allok = allok and ok
                            grid.append((lam, tau_L, tau_H, beta, T_max, c_msg, g0, sep))
    print(f"    checked {len(grid)} instances; brute==closed-form: "
          f"{'ALL PASS' if allok else 'FAILURES PRESENT'}")

    print("\n[2] Worked instances (the witnesses):")
    print("  (a) STRATEGIC + deterrable + cheap channel  -> expect G0>0:")
    check(3, 30, 10, beta=2.0, T_max=5.0, c_msg=0.5, verbose=True)
    print("  (b) channel FREE (c_msg=0)  -> G0 -> VoI>0  (NOT 0; value is info-borne):")
    check(3, 30, 10, beta=2.0, T_max=5.0, c_msg=0.0, verbose=True)
    print("  (c) beta=0  -> gap PERSISTS (=VoI-c_msg): info+commitment-borne, NOT a")
    print("      beta artifact; beta only PRICES separation via T_max>=beta (strict")
    print("      positivity at beta=0 uses the worker-preferred tie-break):")
    check(3, 30, 10, beta=0.0, T_max=5.0, c_msg=0.5, verbose=True)
    print("  (d) liability too small (T_max<beta)  -> COLLAPSE G0==0 (the genuine")
    print("      T-STACK-like failure: limited liability cannot deter squatting):")
    check(3, 30, 10, beta=2.0, T_max=1.0, c_msg=0.5, verbose=True)
    print("  (e) channel too expensive (c_msg>VoI)  -> expect G0<=0:")
    check(3, 30, 10, beta=2.0, T_max=5.0, c_msg=100.0, verbose=True)
    print("  (f) types DON'T straddle 2lambda (both < 2lam)  -> VoI=0 -> G0<=0:")
    check(3, 9, 10, beta=2.0, T_max=5.0, c_msg=0.0, verbose=True)

    print("\n[3] VERDICT:")
    g0_main = check(3, 30, 10, beta=2.0, T_max=5.0, c_msg=0.0)[1]
    voi = 0.5 * min(2 * 10 - 3, 30 - 2 * 10)
    print(f"    On the strategic, deterrable, straddling region the gate SEPARATES:")
    print(f"    G0 = VoI - c_msg, VoI = 1/2 min(2lam-tauL, tauH-2lam) > 0.")
    print(f"    e.g. lam=10,tauL=3,tauH=30: VoI={voi}, G0(c_msg=0)={g0_main:.3f}.")
    print(f"    => G0 > 0 is REAL (prove); but G0 -> VoI (NOT 0) as c_msg->0:")
    print(f"       value is INFORMATION-borne (private stopping time) + commitment-")
    print(f"       to-ex-post-verification, NOT channel-borne. Distinct from T-STACK")
    print(f"       (there the leader cost was attacker-INDEPENDENT => no VoI => G==0).")
    print(f"    Collapse witnesses (G0==0): T_max<beta (limited liability cannot")
    print(f"    deter -- the genuine T-STACK-like failure), or no straddle (VoI=0),")
    print(f"    or c_msg>=VoI (channel too dear). The gap PERSISTS at beta=0.")
    print(f"    CAVEAT: novelty of the lemma itself is low -- this is the known")
    print(f"    inspection/deterrence kernel on the stopping axis; AAMAS-core")
    print(f"    novelty rests ENTIRELY on the unproven h<N paging lift (Step 3).")
    return 0 if allok else 1


if __name__ == "__main__":
    raise SystemExit(main())
