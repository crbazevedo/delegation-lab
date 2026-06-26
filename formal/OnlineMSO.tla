------------------------------ MODULE OnlineMSO ------------------------------
(***************************************************************************)
(* Formal specification of the online MSO review controller's control     *)
(* loop (the reference implementation is minimal_oversight/online_control.py).*)
(*                                                                         *)
(* This abstracts the per-node review budget as an integer count in 0..K   *)
(* (K = b_max/delta increments) and abstracts delivered quality by the     *)
(* monotone proxy `Total` (= total review committed): corrected quality is  *)
(* non-decreasing in every budget[v] (INV-MONOTONE on `corrected`), so      *)
(* "delivered quality below target" refines to "Total < Target", and the    *)
(* argmax-marginal node choice refines the nondeterministic "any node".     *)
(*                                                                         *)
(* TWO control actions, matching the two controllers in online_control.py:  *)
(*   AddReview     (online_step, the monotone ratchet) raises Total when it  *)
(*                 is below target.                                          *)
(*   ReleaseReview (online_step_release) lowers Total when it is slack       *)
(*                 BEYOND a deadband (Total > Target + Deadband). The ratchet *)
(*                 is the special case Deadband -> infinity (never release).  *)
(*                                                                         *)
(* WHY Init is arbitrary.  Under competence drift the bottleneck moves, so   *)
(* by the time the controller runs the committed budget can be anything --   *)
(* including budget that is now pure slack (Total >> Target). We therefore    *)
(* let Init range over ALL budgets and verify the controller drives Total     *)
(* into the band [Target, Target + Deadband] and holds the target there.      *)
(*                                                                         *)
(* The monotone ratchet satisfied MonotoneProgress (Total never decreases).  *)
(* The release controller GIVES THAT UP by design; its replacements are       *)
(*   FeasibilityPreserved (INV-FEASIBLE) -- a control step never drops Total   *)
(*       below Target once it is at/above Target; and                          *)
(*   Terminates (INV-NO-CYCLE / INV-TERMINATE) -- the deadband (>= one grid     *)
(*       step) separates the add region (Total < Target) from the release       *)
(*       region (Total > Target + Deadband), so Total is a Lyapunov function     *)
(*       that settles into the band and stops: no add-then-release cycle.        *)
(*                                                                         *)
(* HOW TO CHECK (requires the TLA+ tools / Java -- not run in the authoring  *)
(* environment):  tlc OnlineMSO.tla -config OnlineMSO.cfg                    *)
(* The algebraic invariants (corrected/min/product/mean monotonicity, budget *)
(* -cap safety, non-harmful add step, release-preserves-feasibility, and the  *)
(* deadband no-cycle fact) are separately machine-checked with Z3 in          *)
(* scripts/verify_online_control.py (P1-P9), which IS run.                    *)
(***************************************************************************)
EXTENDS Naturals, FiniteSets

CONSTANTS Nodes,     \* finite set of workflow nodes
          K,         \* max review increments per node (= b_max / delta)
          Target,    \* review needed to hold delivered quality at p_min
          Deadband   \* slack (in increments) a sink must exceed before release

ASSUME /\ Nodes # {} /\ K \in Nat /\ K >= 1
       /\ Target \in Nat /\ Target <= Cardinality(Nodes) * K
       /\ Deadband \in Nat /\ Deadband >= 1   \* >= one grid step (Z3 P9 / INV-NO-CYCLE)

VARIABLE budget      \* Nodes -> 0..K
vars == budget
Cap == Cardinality(Nodes) * K

\* Total committed review = sum of the per-node budgets (the monotone quality proxy).
RECURSIVE SumOver(_, _)
SumOver(b, S) == IF S = {} THEN 0
                 ELSE LET n == CHOOSE x \in S : TRUE IN b[n] + SumOver(b, S \ {n})
Total == SumOver(budget, Nodes)

TypeOK == budget \in [Nodes -> 0..K]

\* Arbitrary initial commit: the post-drift snapshot the controller inherits.
Init == budget \in [Nodes -> 0..K]

HasHeadroom == \E n \in Nodes : budget[n] < K
HasBudget   == \E n \in Nodes : budget[n] > 0

\* ADD one review increment (the ratchet / online_step add path; argmax-marginal in
\* the implementation, nondeterministic here, which over-approximates the policy).
AddReview(n) == /\ budget[n] < K
                /\ budget' = [budget EXCEPT ![n] = @ + 1]
\* RELEASE one increment from a node with budget (online_step_release), guarded so
\* it fires only when Total is slack beyond the deadband.
ReleaseReview(n) == /\ budget[n] > 0
                    /\ budget' = [budget EXCEPT ![n] = @ - 1]

AddStep == /\ Total < Target
           /\ \E n \in Nodes : AddReview(n)
RelStep == /\ Total > Target + Deadband
           /\ \E n \in Nodes : ReleaseReview(n)
CtrlStep == AddStep \/ RelStep

CanAdd     == Total < Target /\ HasHeadroom
CanRelease == Total > Target + Deadband /\ HasBudget
AtRest     == ~CanAdd /\ ~CanRelease           \* settled in the deadband band

Done == AtRest /\ UNCHANGED vars
Next == CtrlStep \/ Done

Spec == Init /\ [][Next]_vars /\ WF_vars(CtrlStep)

(***************************************************************************)
(* Properties.                                                            *)
(***************************************************************************)
\* INV-BUDGET: every per-node budget stays within its cap.
BudgetSafety == \A n \in Nodes : budget[n] \in 0..K
\* Total never exceeds the structural cap.
Bounded == Total <= Cap
\* INV-FEASIBLE (replaces the ratchet's MonotoneProgress): a control step never
\* drops Total below Target once it is at/above Target -- adds only fire below
\* Target, and a release fires only with Total > Target + Deadband, leaving
\* Total' = Total - 1 >= Target (Deadband >= 1). Drift (Init) may start slack;
\* the CONTROLLER never breaks the target on its own.
FeasibilityPreserved == [][ (Total >= Target) => (Total' >= Target) ]_vars
\* INV-NO-CYCLE / INV-TERMINATE: the deadband separates the add and release regions,
\* so Total settles into the band [Target, Target + Deadband] and the controller
\* stops -- it cannot add-then-release the same increment forever.
InBand == Total >= Target /\ Total <= Target + Deadband
Terminates == <>[] AtRest
=============================================================================
