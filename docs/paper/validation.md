# Paper Validation

All 8 experiments from Section 3 of the paper are reproduced in [`notebooks/06_paper_validation.ipynb`](https://github.com/crbazevedo/delegation-lab/blob/main/notebooks/06_paper_validation.ipynb).

## Summary of results

| # | Experiment | Tests | Result |
|---|-----------|-------|--------|
| 1 | Masking problem | Single vs dual σ governance | M* = 1.83 (Eq. 6, c=0.70)[^1]; single-σ over-authorizes by 36% |
| 2 | Communication strategy | L0-L4 routing strategies | Routing dominates (~53%); L4 outperforms L0 by +6.1% |
| 3 | Bottleneck mechanisms | B1-B4 in isolation and combination | B1 (capacity) ≫ B3 > B2 > B4; B1+B3 super-additive |
| 4 | Linked chains | Depth 1-5 masking accumulation | M*_total super-multiplicative: 38.7 vs 17.2 at D=5 |
| 5 | Multi-task DAGs | SDLC fan-out + diamond fragility | 3× cascade; 1.4× conditional fragility |
| 6 | Delegation capacity | Recursive chain quality (28 conditions) | Theory-observation gap < 0.002 |
| 7 | Process entropy | H(W) sweep with 3 K/N levels | Linear degradation, λ ≈ 0.02/bit |
| 8 | Autonomy time | Drift rate sweep | T*_auto ∝ 1/μ, log-log slope = −0.99 |

[^1]: The theoretical M* = 1.83 uses the closed-form correction (Eq. 6) with raw c. The paper's Experiment 1 simulation observes M* ≈ 1.4 because the simulator applies c × K/N as the effective catch rate. Both are correct at different levels of the model.

## Running the validation

```bash
cd notebooks/
jupyter notebook 06_paper_validation.ipynb
```

The notebook uses only `_formulae.py` (closed-form equations) and inline simulation code. No external data or API keys required.

## Standard parameters

Unless otherwise stated, all experiments use:

- η = 10 (observation rate)
- δ = 2 (decay rate)
- σ_skill = 0.55 (agent skill)
- c = 0.65-0.70 (corrector catch rate)
- K/N = 0.50 (review coverage)
- Δt = 0.1 (ODE step size)
- n = 20 seeds per condition
