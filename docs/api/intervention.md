# intervention

Scheduling and monitoring. Answers: *"When should humans step in?"* and *"What kind of problem is this?"*

*Paper reference: Section 1 (Autonomy time, Prop. 3); Section 4 (Demo 3, diagnostic differential; Algorithm 1, Step 6)*

## compute_autonomy_time

::: minimal_oversight.intervention.compute_autonomy_time
    options:
      show_source: false

$T_\text{auto}^* = B_\text{eff} / \mu_\text{eff}$ — the expected time before quality drops below $p_\text{min}$.

## compute_pipeline_intervention_schedule

::: minimal_oversight.intervention.compute_pipeline_intervention_schedule
    options:
      show_source: false

Returns per-node intervention timing, sorted by urgency (shortest $T_\text{auto}^*$ first).

```python
from minimal_oversight.intervention import compute_pipeline_intervention_schedule

schedule = compute_pipeline_intervention_schedule(pipeline, capacities, p_min=0.80)
for s in schedule:
    print(f"{s.node_name}: review every {s.t_auto:.0f} steps (rank {s.priority_rank})")
```

## diagnose_failure_mode

::: minimal_oversight.intervention.diagnose_failure_mode
    options:
      show_source: false

Classifies the failure mode from $(\Delta\sigma_\text{raw}, \Delta M^*)$:

| $\Delta\sigma_\text{raw}$ | $\Delta M^*$ | Mode | Action |
|---|---|---|---|
| Stable | Stable | `HEALTHY` | None |
| Rising | Falling | `AGENT_IMPROVING` | Reduce corrector budget |
| Falling | Rising | `MASKING_DEGRADATION` | Retrain agent |
| Falling | Falling | `CORRELATED_DRIFT` | Retrain both |
| Stable | Rising | `CORRECTOR_COASTING` | Check agent |

```python
from minimal_oversight.intervention import diagnose_failure_mode

mode = diagnose_failure_mode(delta_sigma_raw=-0.04, delta_m_star=0.05)
print(mode)  # FailureMode.MASKING_DEGRADATION
```

## check_alerts

::: minimal_oversight.intervention.check_alerts
    options:
      show_source: false

Three alert categories: masking ($M^* > \tau$), buffer ($B_\text{eff} < 0.05$), capacity ($K/N < \text{threshold}$). Returns alerts sorted by severity.

## explain_failure_surface

::: minimal_oversight.intervention.explain_failure_surface
    options:
      show_source: false

Human-readable analysis covering five failure modes: infeasible target, masking-driven false confidence, process overload, conditional fragility, upstream bottleneck.

## Data classes

### AlertLevel (Enum)

`INFO`, `WARNING`, `CRITICAL`

### FailureMode (Enum)

`HEALTHY`, `AGENT_IMPROVING`, `MASKING_DEGRADATION`, `CORRELATED_DRIFT`, `CORRECTOR_COASTING`

### InterventionSchedule

| Field | Type | Description |
|-------|------|-------------|
| `node_name` | `str` | Node |
| `t_auto` | `float` | $T_\text{auto}^*$ |
| `intervention_frequency` | `float` | $1/T_\text{auto}^*$ |
| `review_cost` | `float` | Cost weight (uniform in v1) |
| `priority_rank` | `int` | 1 = most urgent |

### MonitoringAlert

| Field | Type | Description |
|-------|------|-------------|
| `level` | `AlertLevel` | Severity |
| `node_name` | `str` | Which node |
| `failure_mode` | `FailureMode` | Classified mode |
| `message` | `str` | What's wrong |
| `recommended_action` | `str` | What to do |
