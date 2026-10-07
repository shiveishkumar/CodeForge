import hashlib
import json
from datetime import date, datetime
from decimal import Decimal


def _normalize_value(value):
    """
    Convert database/Python values into deterministic JSON-compatible values.

    Decimal, date, and datetime values are converted to strings so that
    the same logical audit event always produces the same JSON.
    """

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            key: _normalize_value(value[key])
            for key in sorted(value.keys())
        }

    if isinstance(value, list):
        return [_normalize_value(item) for item in value]

    if isinstance(value, tuple):
        return [_normalize_value(item) for item in value]

    return value


def canonicalize_event(event: dict) -> str:
    """
    Convert an audit event into deterministic canonical JSON.

    Only the seven fields defined by the CodeForge audit-event
    contract are included in the canonical payload.

    Database metadata such as event_id, previous_hash,
    event_hash, and batch_id is not included.
    """

    canonical_fields = {
        "operation",
        "table_name",
        "record_key",
        "old_data",
        "new_data",
        "actor",
        "created_at",
    }

    event_payload = {
        key: event[key]
        for key in canonical_fields
        if key in event
    }

    normalized_event = _normalize_value(event_payload)

    return json.dumps(
        normalized_event,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def calculate_event_hash(
    event: dict,
    previous_hash: str | None,
) -> str:
    """
    Calculate the SHA-256 hash for an audit event.

    Hash formula:
        SHA256(previous_hash + canonical_event_string)

    For the first event, previous_hash is treated as an empty string.
    """

    if previous_hash is None:
        previous_hash = ""

    canonical_event = canonicalize_event(event)

    hash_input = previous_hash + canonical_event

    return hashlib.sha256(
        hash_input.encode("utf-8")
    ).hexdigest()


def verify_event_hash(
    event: dict,
    previous_hash: str | None,
    stored_hash: str,
) -> bool:
    """
    Verify that the stored event hash matches the recalculated hash.

    previous_hash is supplied separately as required by the hash formula,
    so it must not become part of the canonical event payload.
    """

    event_payload = {
        key: value
        for key, value in event.items()
        if key not in {"event_hash", "previous_hash"}
    }

    calculated_hash = calculate_event_hash(
        event_payload,
        previous_hash,
    )

    return calculated_hash == stored_hash

def build_event_record(
    event: dict,
    previous_hash: str | None,
) -> dict:
    """
    Build a complete audit event record.

    The returned record contains the original event fields,
    the previous event hash, and the calculated event hash.
    """

    event_record = dict(event)

    if previous_hash is None:
        previous_hash = ""

    event_record["previous_hash"] = previous_hash
    event_record["event_hash"] = calculate_event_hash(
        event,
        previous_hash,
    )

    return event_record


def verify_hash_chain(events: list[dict]) -> dict:
    """
    Verify the hashes and previous-hash links of an ordered
    sequence of audit events.

    Returns a structured result suitable for the verifier/UI.
    """

    previous_hash = ""

    for event in events:
        event_id = event.get("event_id")

        stored_previous_hash = event.get("previous_hash") or ""

        if stored_previous_hash != previous_hash:
            return {
                "valid": False,
                "type": "HASH_CHAIN",
                "event_id": event_id,
                "message": f"Previous hash mismatch at event {event_id}",
            }

        stored_hash = event.get("event_hash")

        if not stored_hash:
            return {
                "valid": False,
                "type": "EVENT_HASH",
                "event_id": event_id,
                "message": f"Missing event hash at event {event_id}",
            }

        if not verify_event_hash(
            event,
            stored_previous_hash,
            stored_hash,
        ):
            return {
                "valid": False,
                "type": "EVENT_HASH",
                "event_id": event_id,
                "message": f"Event hash mismatch at event {event_id}",
            }

        previous_hash = stored_hash

    return {
        "valid": True,
        "type": "HASH_CHAIN",
        "message": "Hash chain is valid.",
    }

