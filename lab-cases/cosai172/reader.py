"""Finite offline fixture reader, not a CoSAI wire schema or deployment verifier."""

from __future__ import annotations

from typing import Any

# Fixture keys map the thirteen §7.1 rows; they are not proposed OCSF names.
REQUIRED = frozenset({
    "principal_and_delegation_chain", "actor_id", "subject_id",
    "policy_version", "assurance_boundary_statement", "tool_catalog_version",
    "action_identifier", "request_digest", "enforcement_decision_and_reason",
    "runtime_identity_or_attestation_reference", "outcome",
    "integrity_protected_sequence", "accounting_decision",
})


def string_values(value: Any) -> list[str]:
    """Find values, not JSON key names, that the fixture authority can consume."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [item for child in value.values() for item in string_values(child)]
    if isinstance(value, list):
        return [item for child in value for item in string_values(child)]
    return []


def can_replay(record: dict[str, Any], fixture_grant: str) -> bool:
    """The sole synthetic enforcement point accepts only its exact local grant."""
    return fixture_grant in string_values(record)


def read_record(
    record: Any, observation: Any, fixture_grant: str,
) -> dict[str, Any]:
    """Check one record, then the separately held observation for this fixture."""
    if not isinstance(record, dict) or set(record) != REQUIRED:
        return {"result": "processing_failure", "reason": "record_fields"}
    if any(not isinstance(v, (dict, str)) or not v for v in record.values()):
        return {"result": "processing_failure", "reason": "empty_or_invalid_field"}
    if can_replay(record, fixture_grant):
        return {"result": "refused", "reason": "replayable_fixture_authority"}
    runtime = record["runtime_identity_or_attestation_reference"]
    if (
        not isinstance(runtime, dict)
        or set(runtime) != {"state", "value", "reason"}
        or not all(isinstance(v, str) and v for v in runtime.values())
        or runtime["state"] not in {"absent", "not_established"}
    ):
        return {"result": "processing_failure", "reason": "runtime_observation_shape"}
    if runtime["state"] == "absent" and runtime["value"] != "not-available":
        return {"result": "processing_failure", "reason": "runtime_absence_value"}
    if runtime["state"] == "not_established" and runtime["value"] != "fixture:unknown":
        return {"result": "processing_failure", "reason": "runtime_unknown_value"}
    if (
        not isinstance(observation, dict)
        or set(observation) != {"action_identifier", "availability"}
        or not isinstance(observation["availability"], str)
        or observation["action_identifier"] != record["action_identifier"]
        or observation["availability"] not in {"unavailable", "not_established"}
    ):
        return {"result": "processing_failure", "reason": "fixture_observation_context"}
    # This context is a stipulated fixture premise, not proof of real provenance.
    state = "absent" if observation["availability"] == "unavailable" else "not_established"
    if runtime["state"] != state:
        return {"result": "refused", "reason": "unsupported_runtime_observation"}
    return {"result": "record_read", "runtime_observation": state}
