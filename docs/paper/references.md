# Equation-to-Code Reference

Every numbered equation from the paper maps to a function in `_formulae.py`. This page is the bridge: if you're reading the paper, find the code; if you're reading the code, find the theorem.

## Core equations

| Eq. | Paper name | Formula | Code |
|-----|-----------|---------|------|
| (1) | Authorization function | $\alpha(x,t) = G(\sigma_\text{raw}(x,t))$ | Governance functional (conceptual) |
| (2) | **Minimum Sufficient Oversight Principle** | $\min_\alpha \int \alpha^2 \sqrt{\det g}\, dx\, dt$ s.t. delivery | `solve_mso()` + `optimal_authority()` |
| (3) | Fisher information | $g(\sigma) = 1/[\sigma(1-\sigma)]$ | `fisher_information()` |
| (4) | Return Operator | $\partial\sigma/\partial t = \eta(\sigma_\text{skill,eff} - \sigma) - \delta(\sigma-\sigma_0)$ | `return_operator_step()` |
| (5) | Fixed point | $\sigma_\text{raw}^* = (\eta\sigma_\text{skill}+\delta\sigma_0)/(\eta + \delta)$ | `sigma_raw_fixed_point()` |
| (6) | Corrected fixed point | $\sigma_\text{corr}^* = \sigma_\text{raw}^* + (1-\sigma_\text{raw}^*)\times c$ | `sigma_corr_fixed_point()` |
| (7) | Effective skill | $\sigma_\text{skill,eff}(v) = \sigma_\text{skill}(v) \times \text{AGG}(\ldots)$ | `effective_skill()` |
| (8) | **Water-filling solution** | $\alpha^*(x) = \min(\alpha_\text{max}, \frac{\lambda}{2}\sigma\sqrt{\sigma(1-\sigma)})$ | `optimal_authority()` |
| (10) | Delegation capacity | $C_\text{op} = \sup_{p(\text{task})} q^*(\text{output})$ | `node_capacity()` / `compute_pipeline_capacity()` |
| (11) | Recursive chain quality | $\sigma_\text{corr}^*(i) = R(\sigma_\text{skill} \times \sigma_\text{corr}^*(i-1))$ | `recursive_chain_quality()` |
| (13) | Revealed-action stationary capacity | $C_\text{del}(B) = (1-B)[1-H_b(\varepsilon_0)] + B[1-H_b(\varepsilon_1)]$ | `channel_capacity_single_letter()` |
| (9) | GSPN dynamics | $\partial\sigma_\text{raw}/\partial t = \lambda_\text{obs}[\sigma_\text{skill,eff} - \sigma_\text{raw}] - \lambda_\text{forget}(\sigma_\text{raw}-\sigma_0)$ | Not implemented (mean-field approx. only) |
| (12) | Formal capacity | $C_\text{del}(B) = \sup_\pi \liminf \frac{1}{n} I(X^n; Y^n)$ | Theoretical; see Eq. 13 for computable form |
| (14) | Process entropy | $H(W) = H(\text{routing}) + H(\text{tools}) + H(\text{timing})$ | `estimation.estimate_process_entropy()` |
| (15) | Complexity-quality law | $\sigma_\text{raw}^* \geq C_\text{op} - \lambda H(W)$ | `effective_autonomy_buffer()` |
| (16) | **Autonomy buffer** | $B_\text{eff} = C_\text{op} - p_\text{min} - \lambda H(W)$ | `effective_autonomy_buffer()` |
| (17) | **Autonomy time** | $T_\text{auto}^* = B_\text{eff} / \mu_\text{eff}$ | `autonomy_time()` |

## Derived quantities

| Quantity | Definition | Code |
|----------|-----------|------|
| Masking index $M^*$ | $\sigma_\text{corr}^* / \sigma_\text{raw}^*$ | `masking_index()` |
| Critical depth $D_\text{max}$ | $\max\{D: C_\text{op}(D) \geq p_\text{min}\}$ | `max_pipeline_depth()` |
| Critical entropy $H_\text{crit}$ | $(C_\text{op} - p_\text{min}) / \lambda$ | `critical_entropy()` |
| Capacity threshold $K/N$ | $\max(0,(p_\text{min}-\sigma_\text{raw}^*)/[(1-\sigma_\text{raw}^*)c])$ | `corrector_capacity_threshold()` |
| SOTA priority score $S(v)$ | $\text{DC}(v) \times M^*(v) \times \kappa(v)$ | `sota_priority_score()` |

## Higher-level functions

| Paper concept | Section | Code |
|--------------|---------|------|
| Feasibility check | Alg. 1, Step 1 | `capacity.check_feasibility()` |
| Scope selection | Alg. 1, Step 2 | `allocation.select_scope()` |
| Oversight allocation | Alg. 1, Step 3 | `allocation.solve_mso()` |
| State measurement | Alg. 1, Step 4 | `estimation.estimate_node()` |
| Buffer computation | Alg. 1, Step 5 | `capacity.compute_buffer()` |
| Intervention scheduling | Alg. 1, Step 6 | `intervention.compute_pipeline_intervention_schedule()` |
| Diagnostic differential | Demo 3 | `intervention.diagnose_failure_mode()` |
| Failure surface | Box 3 | `intervention.explain_failure_surface()` |
| Motif detection | Table 2 | `topology.detect_motifs()` |
| Delegation centrality | Section 4 | `topology.delegation_centrality()` |
| Conditional fragility | Demo 4 | `topology.conditional_fragility()` |

## Theoretical status

The paper distinguishes three levels of rigor:

| Level | Quantities | Status in code |
|-------|-----------|----------------|
| **Theorem** (proved in the stated model) | $\alpha^*$, $\sigma_\text{raw}^*$, $\sigma_\text{corr}^*$, $M^*$, revealed-action $C_\text{del}(B)$, $K/N$ threshold, $T_\text{cal}$ | Exact in `_formulae.py` under stated assumptions |
| **Proposition** (approximation) | $\lambda$ (governance gap), $T_\text{auto}^*$ | Approximate; $T_\text{auto}^*$ is a drift-dominated first-passage scaling |
| **Empirical law** (observed) | $\lambda \approx 0.02$/bit, $T_\text{auto}^* \propto 1/\mu$ scaling | Confirmed in Experiments 7 and 8 |

The SOTA priority score $S(v)$ is a practical heuristic, not a theorem. The principled quantity is $\partial T_\text{auto}^* / \partial c(v)$, which requires the Jacobian of the coupled system.
