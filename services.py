from datetime import datetime
from verifier import verify_cryptographic_integrity
from checkpoint import load_checkpoint
from audit import build_event_record, verify_hash_chain
from merkle import build_merkle_root
from checkpoint import (
    calculate_chained_root,
    save_checkpoint
)

from database import (
    get_last_event_hash,
    insert_audit_event,
    get_unbatched_audit_events,
    insert_merkle_batch,
    get_last_chained_root,
    get_all_audit_events,
    get_all_merkle_batches,
    get_latest_audited_states,
    get_current_business_record
)


MERKLE_BATCH_SIZE = 4


def create_audit_event(
    operation,
    table_name,
    record_key,
    old_data,
    new_data,
    actor="demo_user"
):
    event = {
        "operation": operation,
        "table_name": table_name,
        "record_key": str(record_key),
        "old_data": old_data,
        "new_data": new_data,
        "actor": actor,
        "created_at": datetime.now().isoformat(timespec="seconds")
    }

    previous_hash = get_last_event_hash()

    event_record = build_event_record(
        event,
        previous_hash
    )

    event_id = insert_audit_event(event_record)

    create_merkle_batch_if_ready()

    return event_id


def create_merkle_batch_if_ready():
    events = get_unbatched_audit_events()

    if len(events) < MERKLE_BATCH_SIZE:
        return None

    event_hashes = [
        event[9]
        for event in events
    ]

    merkle_root = build_merkle_root(event_hashes)

    previous_root_hash = get_last_chained_root()

    chained_root_hash = calculate_chained_root(
        previous_root_hash,
        merkle_root
    )

    start_event_id = events[0][0]
    end_event_id = events[-1][0]

    batch_id = insert_merkle_batch(
        start_event_id=start_event_id,
        end_event_id=end_event_id,
        leaf_count=len(events),
        merkle_root=merkle_root,
        previous_root_hash=previous_root_hash,
        chained_root_hash=chained_root_hash
    )

    save_checkpoint(
        batch_id,
        chained_root_hash
    )

    return batch_id

def verify_system_integrity():
    all_events = get_all_audit_events()
    batches = get_all_merkle_batches()
    checkpoint = load_checkpoint()

    # 1. Verify the hash chain for ALL events,
    # including events waiting for the next Merkle batch.
    chain_result = verify_hash_chain(all_events)

    if not chain_result["valid"]:
        return {
            "valid": False,
            "status": "TAMPERING_DETECTED",
            **chain_result
        }

    # 2. Full Merkle/checkpoint verification only applies
    # to events that already belong to completed batches.
    batched_events = [
        event
        for event in all_events
        if event["batch_id"] is not None
    ]

    if batches:
        crypto_result = verify_cryptographic_integrity(
            batched_events,
            batches,
            checkpoint
        )

        if not crypto_result["valid"]:
            return crypto_result

    # 3. Verify current business data against the latest
    # legitimate audit state, including unbatched events.
    audited_states = get_latest_audited_states()

    for state in audited_states:
        table_name = state["table_name"]
        record_key = state["record_key"]
        expected_data = state["new_data"]
        operation = state["operation"]

        current_data = get_current_business_record(
            table_name,
            record_key
        )

        if operation == "DELETE":
            if current_data is not None:
                return {
                    "valid": False,
                    "status": "TAMPERING_DETECTED",
                    "type": "BUSINESS_STATE",
                    "message": (
                        f"Deleted record unexpectedly exists: "
                        f"{table_name} #{record_key}"
                    )
                }

            continue

        if current_data is None:
            return {
                "valid": False,
                "status": "TAMPERING_DETECTED",
                "type": "BUSINESS_STATE",
                "message": (
                    f"Record missing from {table_name}: "
                    f"#{record_key}"
                )
            }

        for field, expected_value in expected_data.items():
            current_value = current_data.get(field)

            if str(current_value) != str(expected_value):
                return {
                    "valid": False,
                    "status": "TAMPERING_DETECTED",
                    "type": "BUSINESS_STATE",
                    "table_name": table_name,
                    "record_key": record_key,
                    "field": field,
                    "expected": expected_value,
                    "current": current_value,
                    "message": (
                        f"Unauthorized change detected in "
                        f"{table_name} #{record_key}, field '{field}'. "
                        f"Expected {expected_value}, found {current_value}."
                    )
                }

    return {
        "valid": True,
        "status": "VERIFIED",
        "message": "All cryptographic audit checks passed."
    }

def get_integrity_breakdown():
    result = verify_system_integrity()

    events = get_all_audit_events()
    batches = get_all_merkle_batches()

    checks = {
        "hash_chain": {
            "name": "Hash Chain",
            "description": f"{len(events)} audit events linked correctly",
            "status": "passed"
        },

        "merkle": {
            "name": "Merkle Integrity",
            "description": f"{len(batches)} completed batches verified",
            "status": "passed"
        },

        "checkpoint": {
            "name": "External Checkpoint",
            "description": "Latest trusted root matches",
            "status": "passed"
        },

        "business_state": {
            "name": "Database State",
            "description": "Current records match authenticated history",
            "status": "passed"
        }
    }

    if result["valid"]:
        return {
            "valid": True,
            "checks": checks,
            "failure_message": None
        }

    failure_type = result.get("type")

    # Hash/event failure
    if failure_type in ("EVENT_HASH", "HASH_CHAIN"):

        checks["hash_chain"]["status"] = "failed"
        checks["hash_chain"]["description"] = result.get(
            "message",
            "Hash-chain verification failed"
        )

        checks["merkle"]["status"] = "not_checked"
        checks["checkpoint"]["status"] = "not_checked"
        checks["business_state"]["status"] = "not_checked"

    # Merkle or root-chain failure
    elif failure_type in ("MERKLE_ROOT", "ROOT_CHAIN"):

        checks["merkle"]["status"] = "failed"
        checks["merkle"]["description"] = result.get(
            "message",
            "Merkle verification failed"
        )

        checks["checkpoint"]["status"] = "not_checked"
        checks["business_state"]["status"] = "not_checked"

    # Checkpoint failure
    elif failure_type == "CHECKPOINT":

        checks["checkpoint"]["status"] = "failed"
        checks["checkpoint"]["description"] = result.get(
            "message",
            "Checkpoint verification failed"
        )

        checks["business_state"]["status"] = "not_checked"

    # Live database mismatch
    elif failure_type == "BUSINESS_STATE":

        checks["business_state"]["status"] = "failed"
        checks["business_state"]["description"] = result.get(
            "message",
            "Business-state mismatch detected"
        )

    return {
        "valid": False,
        "checks": checks,
        "failure_message": result.get("message")
    }