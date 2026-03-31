# ADK Integration

Import Google ADK agent hierarchies — from `Agent` objects or YAML/JSON configs.

## From Agent objects

```python
from google.adk import Agent
from minimal_oversight import analyze_pipeline

root = Agent(
    name="support",
    model="gemini-2.0-flash",
    description="Routes customer queries",
    sub_agents=[
        Agent(name="billing", model="gemini-2.0-flash", description="Billing questions"),
        Agent(name="tech", model="gemini-2.0-flash", description="Technical support"),
    ],
)

# Auto-detected
report = analyze_pipeline(root, p_min=0.80)
```

## From config dicts

```python
from minimal_oversight import analyze_pipeline

config = {
    "name": "support",
    "model": "gemini-2.0-flash",
    "sub_agents": [
        {"name": "billing", "description": "Billing questions"},
        {"name": "tech", "description": "Technical support"},
    ],
}

# Also auto-detected (requires "sub_agents" key)
report = analyze_pipeline(config, p_min=0.80)
```

## Hierarchical IDs

ADK agents form trees. To prevent name collisions (e.g., two sub-agents named "helper" under different parents), the connector generates hierarchical IDs:

```
support                        → "support"
support/billing                → "support/billing"
support/tech                   → "support/tech"
support/tech/diagnostics       → "support/tech/diagnostics"
```

Use these IDs for parameter overrides:

```python
from minimal_oversight.connectors.adk import from_adk_config

pipeline = from_adk_config(config, parameter_overrides={
    "support/billing": {"sigma_skill": 0.70},
})
```

## Role inference

The connector infers roles from agent names and descriptions:

| Keyword pattern | Inferred role | Default σ_skill |
|----------------|---------------|-----------------|
| "generate", "write", "draft" | Generator | 0.55 |
| "review", "check", "validate" | Reviewer | 0.60 |
| "route", "triage", "classify" | Router | 0.70 |
| "merge", "gate", "aggregate" | Gate | 0.55 |
| "search", "api", "tool" | Tool | 0.80 |
| "human", "escalate" | Human | 0.85 |

The root agent defaults to Router if it has sub-agents, Generator if it doesn't.

## Calibrating from session logs

```python
from minimal_oversight.connectors.traces import from_adk_session_logs, to_workflow_traces

sessions = [...]  # ADK session dicts with "id" and "events"
traces = to_workflow_traces(from_adk_session_logs(sessions))
report = analyze_pipeline(pipeline, p_min=0.80, traces=traces)
```

!!! note "ID matching"
    ADK session logs use flat agent names (`"billing"`), but the pipeline uses hierarchical IDs (`"support/billing"`). For trace calibration, either use a flat pipeline or map trace IDs to hierarchical IDs.
