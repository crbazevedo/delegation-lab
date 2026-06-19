# The theory, and where it lives in the cockpit

Every number and lever in the [cockpit](https://crbazevedo.github.io/delegation-lab/app/widgets/cockpit.html)
is one of the paper's equations made interactive — the same code path as the
`minimal-oversight` package, pinned by a parity test. This page is the map: each
element of the theory → exactly where you see and use it.

## The quantities

| Theory (symbol · ref) | What it means | Where it is in the cockpit |
|---|---|---|
| **Raw competence** (σ_raw · Eq 5) | P(a node is right on its own, pre-review) | Node card; "agent skill (σ_skill)" slider; seeded from the (model × task) priors |
| **Corrected quality** (σ_corr · Eq 6) | quality after review + correction | Drives capacity propagation; `σ_corr = σ_raw + (1−σ_raw)·c·f` |
| **Catch / fix** (c, f) | reviewer *detects* · corrector *repairs* | "Reviewer catch rate (c)" and "Corrector fix rate (f)" sliders; the *Reviewer ≠ corrector* lesson |
| **Masking index** (M\* = σ_corr/σ_raw) | how much review is hiding weak raw skill | "Worst masking" card; per-node M\* badge; risk ranking |
| **Effective skill** (Eq 7) | a node's skill × its parents' corrected quality | How depth compounds — the "chain of depth N" motif |
| **Fisher information** (g(σ)=1/[σ(1−σ)] · Eq 3) | informativeness / cost weight | Weights the water-filling allocation (below) |
| **Water-filling authority** (α\*(x) · Eq 8) | optimal oversight spread across the workflow | **Recipe: "Where to invest oversight"** |
| **Capacity ceiling** (C_op · Eq 10–11) | best corrected quality the pipeline sustains | "Capacity ceiling (C_op)" card; the FEASIBLE / INFEASIBLE verdict |
| **Process entropy** (H(W) · Eq 14) | routing / tool / timing complexity, in bits | "Process complexity" slider |
| **Autonomy buffer** (B_eff = C_op − p_min − λH(W) · Eq 16) | headroom before the autonomy cliff | "Autonomy buffer (B_eff)" card; **Recipe: "Maximize autonomy buffer"** |
| **Capacity cliff** (H_crit = (C_op−p_min)/λ) | process-entropy ceiling; beyond it autonomy is impossible | Theory readout; **Recipe: "Max safe process load"** |
| **Autonomy time** (T\*_auto = B_eff/μ_eff · Eq 17) | how long autonomy lasts before drift forces intervention | "Autonomy runway" readout; **Recipe: "Run N× longer"** |
| **Drift** (μ_eff) | rate competence degrades | Node "drift rate"; aggregated into μ_eff |
| **Corrector capacity** (K/N) | minimum fraction of outputs that must be reviewed | **Recipe: "Min review to hit target"** |
| **Delegation centrality** (DC) | how much downstream work depends on a node | Risk ranking (DC); intervene-upstream prescriptions |
| **SOTA priority** (S = DC·M\*·κ) | where oversight has the highest marginal value | Risk ranking (S); "keep review here" prescriptions |
| **Task motifs** (chain / fan-out / merge / diamond) | structurally fragile patterns | "Motifs" panel; the merge-gate / diamond lessons |
| **Cost & allocation** (cost index, optimizer) | $/run, open-source vs proprietary | Node cost; budget; ⚡ Optimize ([how priors are built](priors.md)) |

## The recipe library — theory you can *apply*

The **Theory toolkit** panel turns the equations into one-click moves. Each is a
heuristic grounded in a specific result; each shows its working.

- **⏱ Run N× longer** — *autonomy time, Eq 17.* Autonomy ends when **drift**, not
  raw quality, pulls the buffer to zero: `T*_auto = B_eff / μ_eff`. The recipe
  scales every node's drift by `1/N` (the real-world levers: stabler models,
  lower temperature, response caching, pinned versions) so the workflow runs
  ≈ N× longer between interventions. *Tune this workflow so it can run 2× as
  long* is exactly this button with N = 2.
- **▲ Max safe process load** — *capacity cliff, Demonstration 7.* Sets H(W) to
  80% of `H_crit`: the most routing, tool variety and branching the workflow can
  absorb before *no* governance policy keeps it autonomous.
- **K/N Min review to hit target** — *corrector capacity threshold.* For the
  bottleneck, `K/N ≥ (p_min − σ_raw) / [(1−σ_raw)·c·f]` — the minimum share of
  outputs you must review. If it exceeds 100%, reviewing alone can't get there;
  strengthen the reviewer/corrector or change the model.
- **α\* Where to invest oversight** — *water-filling, Eq 8.* Fisher-weighted
  authority pools where it has the highest marginal value (mid-competence nodes,
  not the strongest or the weakest). The recipe ranks the nodes to invest in
  first.
- **Maximize autonomy buffer** — *autonomy buffer, Eq 16.* Decomposes B_eff into
  its three levers (raise C_op, lower H(W), relax p_min) and quantifies the
  drift-time each buys.

## Why this matters

The point of the paper is to make oversight **computable** — an explicit
trade-off between autonomy, uncertainty, process structure, intervention and
capacity. The cockpit is that trade-off you can touch: change a model, a target,
a drift rate or the process complexity, and every governed quantity updates live.
The recipes are starting heuristics — calibrate them against your own traces, the
same way you would the [priors](priors.md).
