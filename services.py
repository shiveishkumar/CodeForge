
from datetime import datetime

from verifier import verify_cryptographic_integrity
from checkpoint import load_checkpoint

from audit import (
    build_event_record,
    verify_hash_chain
)

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
    get_current_business_record,
    get_records_missing_audit_baseline,
    get_all_current_business_records
)


MERKLE_BATCH_SIZE = 4


# =========================================================
# CREATE AUDIT EVENT
# =========================================================

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
        "created_at": datetime.now().isoformat(
            timespec="seconds"
        )
    }

    previous_hash = get_last_event_hash()

    event_record = build_event_record(
        event,
        previous_hash
    )

    event_id = insert_audit_event(event_record)

    create_merkle_batch_if_ready()

    return event_id


# =========================================================
# CREATE MERKLE BATCH
# =========================================================

def create_merkle_batch_if_ready(force=False):
    """
    Create a Merkle batch.

    Normal operation requires MERKLE_BATCH_SIZE events.
    When force=True, a partial batch can also be finalized.
    """

    events = get_unbatched_audit_events()

    if not events:
        return None

    # Preserve normal batching unless explicitly forced.
    if len(events) < MERKLE_BATCH_SIZE and not force:
        return None

    # database.py returns tuples:
    # event_id is index 0; event_hash is index 9.
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


# =========================================================
# FINALIZE PENDING MERKLE BATCHES
# =========================================================

def finalize_pending_merkle_batches():
    """
    Finalize remaining pending audit events.

    Complete batches are processed normally.
    The final incomplete batch is also finalized.
    """

    finalized_batch_ids = []

    while True:
        batch_id = create_merkle_batch_if_ready(
            force=True
        )

        if batch_id is None:
            break

        finalized_batch_ids.append(batch_id)

    return finalized_batch_ids


# =========================================================
# INITIALIZE TRUSTED BASELINE
# =========================================================

def initialize_trusted_baseline():
    """
    Create authenticated baseline events for existing
    business records that do not yet have audit history.

    Existing audited records are skipped.
    """

    missing_records = get_records_missing_audit_baseline()

    created_count = 0

    for record in missing_records:
        create_audit_event(
            operation="BASELINE",
            table_name=record["table_name"],
            record_key=record["record_key"],
            old_data=None,
            new_data=record["new_data"],
            actor="system_baseline"
        )

        created_count += 1

    return {
        "created": created_count,
        "status": "BASELINE_COMPLETE"
    }


# =========================================================
# VERIFY COMPLETE SYSTEM
# =========================================================

def verify_system_integrity():

    all_events = get_all_audit_events()
    batches = get_all_merkle_batches()
    checkpoint = load_checkpoint()

    # =====================================================
    # 1. VERIFY HASH CHAIN
    # =====================================================

    chain_result = verify_hash_chain(all_events)

    if not chain_result["valid"]:
        return {
            "valid": False,
            "status": "TAMPERING_DETECTED",
            **chain_result
        }

    # =====================================================
    # 2. VERIFY MERKLE BATCHES + CHECKPOINT
    # =====================================================

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

    # =====================================================
    # 3. VERIFY CURRENT BUSINESS STATE
    # =====================================================

    audited_states = get_latest_audited_states()

    # Fetch all current business records in two queries
    # rather than querying every account/product separately.
    current_records = get_all_current_business_records()

    violations = []

    for state in audited_states:

        table_name = state["table_name"]
        record_key = state["record_key"]
        expected_data = state["new_data"]
        operation = state["operation"]

        current_data = current_records.get(
            (
                table_name,
                str(record_key)
            )
        )

        # =================================================
        # DELETED RECORD SHOULD NOT EXIST
        # =================================================

        if operation == "DELETE":

            if current_data is not None:
                violations.append({
                    "type": "BUSINESS_STATE",
                    "table_name": table_name,
                    "record_key": str(record_key),
                    "field": None,
                    "expected": None,
                    "current": current_data,
                    "trusted_data": expected_data,
                    "restore_supported": False,
                    "message": (
                        f"Deleted record unexpectedly exists: "
                        f"{table_name} #{record_key}"
                    )
                })

            continue

        # =================================================
        # RECORD SHOULD EXIST
        # =================================================

        if current_data is None:
            violations.append({
                "type": "BUSINESS_STATE",
                "table_name": table_name,
                "record_key": str(record_key),
                "field": None,
                "expected": expected_data,
                "current": None,
                "trusted_data": expected_data,
                "restore_supported": False,
                "message": (
                    f"Record missing from "
                    f"{table_name}: "
                    f"#{record_key}"
                )
            })

            continue

        # =================================================
        # COMPARE AUTHENTICATED FIELDS
        # =================================================

        for field, expected_value in expected_data.items():

            current_value = current_data.get(field)

            if str(current_value) != str(expected_value):
                violations.append({
                    "type": "BUSINESS_STATE",
                    "table_name": table_name,
                    "record_key": str(record_key),
                    "field": field,
                    "expected": expected_value,
                    "current": current_value,
                    "trusted_data": expected_data,
                    "restore_supported": True,
                    "message": (
                        f"Unauthorized change detected in "
                        f"{table_name} #{record_key}, "
                        f"field '{field}'. "
                        f"Expected {expected_value}, "
                        f"found {current_value}."
                    )
                })

    # =====================================================
    # RETURN ALL BUSINESS VIOLATIONS
    # =====================================================

    if violations:

        recoverable_violations = [
            violation
            for violation in violations
            if violation.get("restore_supported")
        ]

        # Preserve compatibility with the existing
        # Restore Trusted State route.
        first_recoverable = None

        if recoverable_violations:
            first_recoverable = recoverable_violations[0]

        result = {
            "valid": False,
            "status": "TAMPERING_DETECTED",
            "type": "BUSINESS_STATE",
            "violation_count": len(violations),
            "violations": violations,
            "recoverable_violations": recoverable_violations,
            "restore_supported": len(recoverable_violations) > 0,
            "message": (
                f"{len(violations)} unauthorized "
                f"business-state change"
                f"{'s' if len(violations) != 1 else ''} "
                f"detected."
            )
        }

        # =================================================
        # BACKWARD COMPATIBILITY
        # =================================================

        if first_recoverable:

            result["table_name"] = (
                first_recoverable["table_name"]
            )

            result["record_key"] = (
                first_recoverable["record_key"]
            )

            result["field"] = (
                first_recoverable["field"]
            )

            result["expected"] = (
                first_recoverable["expected"]
            )

            result["current"] = (
                first_recoverable["current"]
            )

            result["trusted_data"] = (
                first_recoverable["trusted_data"]
            )

        return result

    # =====================================================
    # EVERYTHING PASSED
    # =====================================================

    return {
        "valid": True,
        "status": "VERIFIED",
        "message": "All cryptographic audit checks passed.",
        "restore_supported": False,
        "violation_count": 0,
        "violations": [],
        "recoverable_violations": []
    }


# =========================================================
# DASHBOARD INTEGRITY BREAKDOWN
# =========================================================

def get_integrity_breakdown():

    result = verify_system_integrity()

    events = get_all_audit_events()
    batches = get_all_merkle_batches()

    checks = {
        "hash_chain": {
            "name": "Hash Chain",
            "description": (
                f"{len(events)} audit events linked correctly"
            ),
            "status": "passed"
        },

        "merkle": {
            "name": "Merkle Integrity",
            "description": (
                f"{len(batches)} completed batches verified"
            ),
            "status": "passed"
        },

        "checkpoint": {
            "name": "External Checkpoint",
            "description": "Latest trusted root matches",
            "status": "passed"
        },

        "business_state": {
            "name": "Database State",
            "description": (
                "Current records match authenticated history"
            ),
            "status": "passed"
        }
    }

    # =====================================================
    # EVERYTHING PASSED
    # =====================================================

    if result["valid"]:
        return {
            "valid": True,
            "checks": checks,
            "failure_message": None,
            "failure_type": None,
            "restore_supported": False,
            "violation_count": 0,
            "violations": [],
            "recoverable_violations": []
        }

    failure_type = result.get("type")

    # =====================================================
    # HASH / EVENT FAILURE
    # =====================================================

    if failure_type in ("EVENT_HASH", "HASH_CHAIN"):

        checks["hash_chain"]["status"] = "failed"

        checks["hash_chain"]["description"] = result.get(
            "message",
            "Hash-chain verification failed"
        )

        checks["merkle"]["status"] = "not_checked"
        checks["checkpoint"]["status"] = "not_checked"
        checks["business_state"]["status"] = "not_checked"

    # =====================================================
    # MERKLE / ROOT CHAIN FAILURE
    # =====================================================

    elif failure_type in ("MERKLE_ROOT", "ROOT_CHAIN"):

        checks["merkle"]["status"] = "failed"

        checks["merkle"]["description"] = result.get(
            "message",
            "Merkle verification failed"
        )

        checks["checkpoint"]["status"] = "not_checked"
        checks["business_state"]["status"] = "not_checked"

    # =====================================================
    # CHECKPOINT FAILURE
    # =====================================================

    elif failure_type == "CHECKPOINT":

        checks["checkpoint"]["status"] = "failed"

        checks["checkpoint"]["description"] = result.get(
            "message",
            "Checkpoint verification failed"
        )

        checks["business_state"]["status"] = "not_checked"

    # =====================================================
    # BUSINESS STATE FAILURE
    # =====================================================

    elif failure_type == "BUSINESS_STATE":

        checks["business_state"]["status"] = "failed"

        violation_count = result.get("violation_count", 1)

        if violation_count == 1:

            violations = result.get("violations", [])

            if violations:
                checks["business_state"]["description"] = (
                    violations[0]["message"]
                )
            else:
                checks["business_state"]["description"] = (
                    result.get(
                        "message",
                        "Business-state mismatch detected"
                    )
                )

        else:
            checks["business_state"]["description"] = (
                f"{violation_count} unauthorized "
                f"business-state changes detected"
            )

    # =====================================================
    # RETURN DASHBOARD DATA
    # =====================================================

    return {
        "valid": False,
        "checks": checks,
        "failure_message": result.get("message"),
        "failure_type": failure_type,
        "restore_supported": result.get(
            "restore_supported",
            False
        ),
        "violation_count": result.get("violation_count", 0),
        "violations": result.get("violations", []),
        "recoverable_violations": result.get(
            "recoverable_violations",
            []
        ),

        # Preserve compatibility with the existing dashboard
        # and Restore Trusted State route.
        "table_name": result.get("table_name"),
        "record_key": result.get("record_key"),
        "field": result.get("field"),
        "expected": result.get("expected"),
        "current": result.get("current"),
        "trusted_data": result.get("trusted_data")
    }
