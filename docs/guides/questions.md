# The questions the cockpit answers

The paper frames oversight as an **allocation problem**: once work is delegated,
governance is no longer "how accurate is the model?" but "where should oversight
go?" This page maps each question the framework poses to the exact place you can
*read the answer off* the [cockpit](https://crbazevedo.github.io/delegation-lab/app/widgets/cockpit.html) —
through a metric, a lever, a prescription, or a lesson.

Every value is computed by the same equations as the `minimal-oversight` package
(pinned by a parity test), so the cockpit is the paper made interactive, not a
mock-up.

## Where should autonomy expand?

**Read it:** the **Prescriptions** panel surfaces *"Autonomy can expand at X —
review is barely lifting it (M\*≈1)"* whenever a reviewed node has slack and the
pipeline has a positive **Autonomy buffer (B_eff)**. That is the water-filling
rule running in reverse: reclaim oversight where its marginal value is near zero.
**Lever:** lower a node's catch rate (c) and watch B_eff stay positive.

## Where should review remain?

**Read it:** **Risk ranking** orders nodes by `S = DC · M* · κ`, and the
Prescriptions panel says *"Keep review at X"* for high-**masking (M\*)**, central
nodes. High masking means corrected quality is propping up weak raw competence —
exactly where removing review would bite.

## Where should intervention happen earlier (upstream)?

**Read it:** **Delegation centrality (DC)** in the risk ranking measures how much
downstream work depends on a node. The **diamond** motif triggers the
prescription *"Intervene upstream — correct the shared source, not the merge."*
**Lesson:** *Reviewer placement* shows a reviewer on one branch leaving the other
raw; moving it above the fan-out fixes both.

## Where is the workflow too uncertain / complex / drift-sensitive to delegate?

**Read it:** the **feasibility banner**. If **Capacity ceiling (C_op)** falls
below the **Quality target (p_min)** the pipeline is INFEASIBLE — no local policy
rescues it. Raise **Process complexity (H(W))** and watch the buffer collapse
toward the capacity cliff (H_crit).

## Which regions consume oversight without improving outcomes?

**Read it:** **masking (M\*)** near 1.0 on a *reviewed* node — review is running
but barely changing the output. The "Autonomy can expand" prescription points
straight at it.

## Which task motifs are structurally fragile under delegation?

**Read it:** the **Motifs** panel tags `chain`, `fan_out`, `merge`, and
`diamond`. **Lessons:** *Merge gate type* (all-required vs vote) and *Chain depth
& masking* show how each motif degrades and how to redesign it.

## Where does process entropy increase as autonomy expands?

**Read it:** the **Process complexity (H(W))** slider feeds the **Autonomy buffer
(B_eff = C_op − p_min − λ·H(W))**. More routing/branching ⇒ higher H(W) ⇒ smaller
buffer ⇒ closer to the cliff.

## Where does early intervention prevent downstream correction load?

**Read it:** high **delegation centrality (DC)** marks nodes whose errors
compound downstream. Fixing them upstream (vs. correcting every consequence) is
the cheaper allocation — the SOTA priority score `S` ranks exactly these.

## Where should autonomy be *blocked* until feasibility improves?

**Read it:** the **INFEASIBLE** banner names the bottleneck and the prescription
says *"Block autonomy / redesign … before expanding autonomy."* Feasibility is a
gate, not a goal.

## Is "corrected" performance evidence of autonomous competence?

**No — and the cockpit makes the trap visible.** A node can show high corrected
quality (σ_corr) while its **raw competence (σ_raw)** is poor; the gap is the
**masking index (M\* = σ_corr / σ_raw)**. **Lesson:** *Reviewer ≠ corrector*
shows that a reviewer which only *detects* (catch rate c) without a corrector
that *repairs* (fix rate f) leaves quality stuck — corrected ≠ autonomous.

---

### The framework's prescriptions, and where they live

| Prescription (from the paper) | In the cockpit |
|---|---|
| Allocate oversight where marginal value is highest | Risk ranking (S = DC·M*·κ) + "Keep review" prescriptions |
| Intervene upstream when downstream correction compounds | Delegation centrality + diamond motif + "Intervene upstream" |
| Identify motifs that degrade under delegation | Motifs panel + Merge-gate / Chain-depth lessons |
| Check feasibility before expanding autonomy | Feasibility banner (C_op vs p_min), H_crit cliff |
| Treat corrected performance as insufficient evidence | Masking index + Reviewer ≠ corrector lesson |
| Minimize governance burden (the MSO principle) | "Autonomy can expand here" prescription |

Start from a template, slide the **Quality target** and **Process complexity**,
seed nodes from public benchmarks (the ⊕ button — see
[How the priors are built](../methodology/priors.md)), then refine every number
with your own traces. The cockpit is a calculator for the autonomy ↔ uncertainty
↔ process-structure ↔ intervention ↔ capacity tradeoff — not a verdict.
