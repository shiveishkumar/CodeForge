from audit import verify_hash_chain
from merkle import build_merkle_root
from checkpoint import calculate_chained_root


def _failure(
    failure_type: str,
    message: str,
    event_id=None,
    batch_id=None,
) -> dict:
    """
    Build a standard tampering-detected result.
    """

    result = {
        "valid": False,
        "status": "TAMPERING_DETECTED",
        "type": failure_type,
        "message": message,
    }

    if event_id is not None:
        result["event_id"] = event_id

    if batch_id is not None:
        result["batch_id"] = batch_id

    return result


def verify_cryptographic_integrity(
    events: list[dict],
    batches: list[dict],
    checkpoint: dict | None,
) -> dict:
    """
    Verify the complete cryptographic audit structure.

    Verification order:
    1. Event hashes and hash chain
    2. Merkle roots
    3. Root chaining
    4. External checkpoint
    """

    # ---------------------------------------------------------
    # 1. Verify event hashes and previous-hash chain
    # ---------------------------------------------------------

    sorted_events = sorted(
        events,
        key=lambda event: event.get("event_id", 0),
    )

    chain_result = verify_hash_chain(sorted_events)

    if not chain_result.get("valid", False):
        return _failure(
            chain_result.get("type", "HASH_CHAIN"),
            chain_result.get("message", "Hash-chain verification failed."),
            event_id=chain_result.get("event_id"),
        )

    # ---------------------------------------------------------
    # 2. Group events by batch_id
    # ---------------------------------------------------------

    events_by_batch = {}

    for event in sorted_events:
        batch_id = event.get("batch_id")

        if batch_id is None:
            return _failure(
                "MERKLE_ROOT",
                f"Missing batch_id for event {event.get('event_id')}",
                event_id=event.get("event_id"),
            )

        events_by_batch.setdefault(batch_id, []).append(event)

    sorted_batches = sorted(
        batches,
        key=lambda batch: batch.get("batch_id", 0),
    )

    # ---------------------------------------------------------
    # 3. Verify every Merkle root
    # ---------------------------------------------------------

    for batch in sorted_batches:
        batch_id = batch.get("batch_id")

        batch_events = events_by_batch.get(batch_id, [])

        if not batch_events:
            return _failure(
                "MERKLE_ROOT",
                f"No events found for batch {batch_id}",
                batch_id=batch_id,
            )

        stored_leaf_count = batch.get("leaf_count")

        if stored_leaf_count != len(batch_events):
            return _failure(
                "MERKLE_ROOT",
                f"Leaf count mismatch for batch {batch_id}",
                batch_id=batch_id,
            )

        event_hashes = [
            event["event_hash"]
            for event in batch_events
        ]

        calculated_root = build_merkle_root(event_hashes)

        stored_root = batch.get("merkle_root")

        if calculated_root != stored_root:
            return _failure(
                "MERKLE_ROOT",
                f"Merkle root mismatch for batch {batch_id}",
                batch_id=batch_id,
            )

    # ---------------------------------------------------------
    # 4. Verify chained roots
    # ---------------------------------------------------------

    previous_root_hash = ""

    for batch in sorted_batches:
        batch_id = batch.get("batch_id")
        merkle_root = batch.get("merkle_root")

        stored_previous_root = (
            batch.get("previous_root_hash") or ""
        )

        if stored_previous_root != previous_root_hash:
            return _failure(
                "ROOT_CHAIN",
                f"Previous root mismatch for batch {batch_id}",
                batch_id=batch_id,
            )

        calculated_chained_root = calculate_chained_root(
            previous_root_hash,
            merkle_root,
        )

        stored_chained_root = batch.get(
            "chained_root_hash"
        )

        if calculated_chained_root != stored_chained_root:
            return _failure(
                "ROOT_CHAIN",
                f"Chained root mismatch for batch {batch_id}",
                batch_id=batch_id,
            )

        previous_root_hash = calculated_chained_root

    # ---------------------------------------------------------
    # 5. Verify external checkpoint
    # ---------------------------------------------------------

    if sorted_batches:
        if checkpoint is None:
            return _failure(
                "CHECKPOINT",
                "Checkpoint is missing.",
            )

        latest_batch_id = sorted_batches[-1].get("batch_id")

        checkpoint_batch_id = checkpoint.get("batch_id")

        checkpoint_root = checkpoint.get(
            "chained_root_hash"
        )

        if checkpoint_batch_id != latest_batch_id:
            return _failure(
                "CHECKPOINT",
                "Checkpoint batch_id does not match the latest batch.",
                batch_id=latest_batch_id,
            )

        if checkpoint_root != previous_root_hash:
            return _failure(
                "CHECKPOINT",
                "Checkpoint chained root does not match the latest chained root.",
                batch_id=latest_batch_id,
            )

    # ---------------------------------------------------------
    # 6. Everything passed
    # ---------------------------------------------------------

    return {
        "valid": True,
        "status": "VERIFIED",
        "message": "All cryptographic audit checks passed.",
    }