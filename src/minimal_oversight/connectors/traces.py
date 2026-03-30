"""Trace parsers: convert framework execution traces to normalized format.

Supports:
    - LangSmith trace dicts (from LangGraph runs)
    - ADK trace dicts (from ADK session logs)
    - Generic event logs (JSON-based)

These parsers produce NormalizedTrace objects that can be converted
to WorkflowTrace via the bridge for use with estimation.py.
"""

from __future__ import annotations

from typing import Any

from minimal_oversight.connectors._bridge import traces_from_normalized
from minimal_oversight.models import WorkflowTrace
from minimal_oversight.schema import (
    EventType,
    NormalizedEvent,
    NormalizedOutcome,
    NormalizedTrace,
    OutcomeType,
)


def _parse_langsmith_run(
    run: dict[str, Any],
    trace_id: str,
    events: list[NormalizedEvent],
    outcomes: list[NormalizedOutcome],
    task_id: str = "",
) -> None:
    """Recursively parse a LangSmith run dict."""
    node_id = run.get("name", "unknown")
    run_type = run.get("run_type", "")
    start_time = run.get("start_time", 0.0)
    end_time = run.get("end_time", 0.0)

    if isinstance(start_time, str):
        start_time = 0.0
    if isinstance(end_time, str):
        end_time = 0.0

    status = run.get("status", "")
    error = run.get("error", None)

    # Determine outcome
    if error:
        outcome = OutcomeType.FAILURE
        raw = 0.0
    elif status == "success":
        outcome = OutcomeType.SUCCESS
        raw = 1.0
    else:
        outcome = OutcomeType.UNKNOWN
        raw = 0.5

    events.append(NormalizedEvent(
        event_type=EventType.NODE_ENTER,
        node_id=node_id,
        timestamp=float(start_time),
        task_id=task_id,
    ))

    events.append(NormalizedEvent(
        event_type=EventType.NODE_EXIT,
        node_id=node_id,
        timestamp=float(end_time),
        task_id=task_id,
        outcome=outcome,
    ))

    # For chain/tool runs, add as outcome
    if run_type in ("chain", "llm", "tool"):
        outcomes.append(NormalizedOutcome(
            task_id=task_id or trace_id,
            node_id=node_id,
            raw_outcome=raw,
            corrected_outcome=raw,  # no correction info in basic traces
            was_reviewed=False,
            timestamp=float(end_time),
        ))

    # Recurse into child runs
    for child in run.get("child_runs", []):
        _parse_langsmith_run(child, trace_id, events, outcomes, task_id)


def from_langsmith_traces(
    runs: list[dict[str, Any]],
) -> list[NormalizedTrace]:
    """Parse LangSmith run dicts into normalized traces.

    Args:
        runs: List of LangSmith run dicts (from the LangSmith API or export).
              Each run represents a top-level invocation.

    Returns:
        List of NormalizedTrace objects.
    """
    traces: list[NormalizedTrace] = []

    for i, run in enumerate(runs):
        trace_id = run.get("id", run.get("run_id", f"trace_{i}"))
        task_id = run.get("session_id", trace_id)
        events: list[NormalizedEvent] = []
        outcomes: list[NormalizedOutcome] = []

        _parse_langsmith_run(run, str(trace_id), events, outcomes, str(task_id))

        traces.append(NormalizedTrace(
            trace_id=str(trace_id),
            events=events,
            outcomes=outcomes,
            framework_source="langsmith",
        ))

    return traces


def from_adk_session_logs(
    sessions: list[dict[str, Any]],
) -> list[NormalizedTrace]:
    """Parse ADK session log dicts into normalized traces.

    Args:
        sessions: List of ADK session dicts. Each session has an "events" list
                  with agent actions.

    Returns:
        List of NormalizedTrace objects.
    """
    traces: list[NormalizedTrace] = []

    for i, session in enumerate(sessions):
        session_id = session.get("id", session.get("session_id", f"session_{i}"))
        events: list[NormalizedEvent] = []
        outcomes: list[NormalizedOutcome] = []

        for j, event in enumerate(session.get("events", [])):
            agent_name = event.get("agent", event.get("author", "unknown"))
            event_type_str = event.get("type", event.get("action_type", ""))
            timestamp = event.get("timestamp", float(j))

            if isinstance(timestamp, str):
                timestamp = float(j)

            # Map ADK event types to normalized types
            if "transfer" in event_type_str.lower() or "handoff" in event_type_str.lower():
                evt_type = EventType.HANDOFF
            elif "tool" in event_type_str.lower():
                evt_type = EventType.TOOL_CALL
            elif "error" in event_type_str.lower():
                evt_type = EventType.ERROR
            else:
                evt_type = EventType.NODE_EXIT

            # Determine outcome from event
            is_error = event.get("error", False) or "error" in event_type_str.lower()
            outcome = OutcomeType.FAILURE if is_error else OutcomeType.SUCCESS
            raw = 0.0 if is_error else 1.0

            events.append(NormalizedEvent(
                event_type=evt_type,
                node_id=agent_name,
                timestamp=float(timestamp),
                task_id=str(session_id),
                outcome=outcome,
                payload=event.get("data", {}),
            ))

            outcomes.append(NormalizedOutcome(
                task_id=str(session_id),
                node_id=agent_name,
                raw_outcome=raw,
                corrected_outcome=raw,
                was_reviewed=False,
                timestamp=float(timestamp),
            ))

        traces.append(NormalizedTrace(
            trace_id=str(session_id),
            events=events,
            outcomes=outcomes,
            framework_source="adk",
        ))

    return traces


def from_generic_events(
    events: list[dict[str, Any]],
    task_id_field: str = "task_id",
    node_id_field: str = "node_id",
    outcome_field: str = "outcome",
    timestamp_field: str = "timestamp",
    corrected_field: str | None = None,
    reviewed_field: str | None = None,
) -> list[NormalizedTrace]:
    """Parse generic JSON event logs into normalized traces.

    Flexible parser for custom logging formats. Map your field names
    to the expected fields.

    Args:
        events: List of event dicts.
        task_id_field: Key for the task/item identifier.
        node_id_field: Key for the node/agent identifier.
        outcome_field: Key for the outcome (1/0, success/failure, or float).
        timestamp_field: Key for the timestamp.
        corrected_field: Optional key for post-correction outcome.
        reviewed_field: Optional key for whether the item was reviewed.

    Returns:
        List of NormalizedTrace objects (one per unique task_id).
    """
    # Group events by task
    task_events: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        tid = str(event.get(task_id_field, "unknown"))
        task_events.setdefault(tid, []).append(event)

    traces: list[NormalizedTrace] = []

    for task_id, task_evts in task_events.items():
        norm_events: list[NormalizedEvent] = []
        norm_outcomes: list[NormalizedOutcome] = []

        for evt in task_evts:
            node_id = str(evt.get(node_id_field, "unknown"))
            timestamp = float(evt.get(timestamp_field, 0.0))

            # Parse outcome
            raw_val = evt.get(outcome_field, None)
            if isinstance(raw_val, (int, float)):
                raw = float(raw_val)
            elif isinstance(raw_val, str):
                raw = 1.0 if raw_val.lower() in ("success", "true", "1", "pass") else 0.0
            elif isinstance(raw_val, bool):
                raw = 1.0 if raw_val else 0.0
            else:
                raw = 0.5

            corrected = raw
            if corrected_field and corrected_field in evt:
                corr_val = evt[corrected_field]
                if isinstance(corr_val, (int, float)):
                    corrected = float(corr_val)
                elif isinstance(corr_val, bool):
                    corrected = 1.0 if corr_val else 0.0

            reviewed = False
            if reviewed_field and reviewed_field in evt:
                reviewed = bool(evt[reviewed_field])

            norm_events.append(NormalizedEvent(
                event_type=EventType.NODE_EXIT,
                node_id=node_id,
                timestamp=timestamp,
                task_id=task_id,
                outcome=OutcomeType.SUCCESS if raw >= 0.5 else OutcomeType.FAILURE,
                pre_correction=corrected_field is not None,
                post_correction=corrected_field is not None,
            ))

            norm_outcomes.append(NormalizedOutcome(
                task_id=task_id,
                node_id=node_id,
                raw_outcome=raw,
                corrected_outcome=corrected,
                was_reviewed=reviewed,
                timestamp=timestamp,
            ))

        traces.append(NormalizedTrace(
            trace_id=task_id,
            events=norm_events,
            outcomes=norm_outcomes,
            framework_source="generic",
        ))

    return traces


def to_workflow_traces(normalized_traces: list[NormalizedTrace]) -> list[WorkflowTrace]:
    """Convert normalized traces to WorkflowTrace objects for estimation.

    Convenience function that wraps the bridge.
    """
    return traces_from_normalized(normalized_traces)
