import os
import unittest

from audit import (
    canonicalize_event,
    calculate_event_hash,
    build_event_record,
    verify_hash_chain,
)

from merkle import (
    build_merkle_root,
    build_merkle_proof,
    verify_merkle_proof,
)

from checkpoint import (
    calculate_chained_root,
    save_checkpoint,
    load_checkpoint,
)

from verifier import verify_cryptographic_integrity


class TestCodeForgeCrypto(unittest.TestCase):

    def create_events(self):
        event1 = {
            "event_id": 1,
            "operation": "UPDATE",
            "table_name": "accounts",
            "record_key": "1",
            "old_data": {"balance": "50000.00"},
            "new_data": {"balance": "45000.00"},
            "actor": "demo_user",
            "created_at": "2026-10-07T14:30:00",
            "batch_id": 1,
        }

        event2 = {
            "event_id": 2,
            "operation": "UPDATE",
            "table_name": "accounts",
            "record_key": "2",
            "old_data": {"balance": "35000.00"},
            "new_data": {"balance": "34000.00"},
            "actor": "demo_user",
            "created_at": "2026-10-07T14:31:00",
            "batch_id": 1,
        }

        event3 = {
            "event_id": 3,
            "operation": "UPDATE",
            "table_name": "accounts",
            "record_key": "3",
            "old_data": {"balance": "25000.00"},
            "new_data": {"balance": "24000.00"},
            "actor": "demo_user",
            "created_at": "2026-10-07T14:32:00",
            "batch_id": 1,
        }

        event4 = {
            "event_id": 4,
            "operation": "UPDATE",
            "table_name": "accounts",
            "record_key": "4",
            "old_data": {"balance": "40000.00"},
            "new_data": {"balance": "39000.00"},
            "actor": "demo_user",
            "created_at": "2026-10-07T14:33:00",
            "batch_id": 1,
        }

        record1 = build_event_record(event1, None)
        record2 = build_event_record(event2, record1["event_hash"])
        record3 = build_event_record(event3, record2["event_hash"])
        record4 = build_event_record(event4, record3["event_hash"])

        return [record1, record2, record3, record4]

    def create_batch(self, events):
        event_hashes = [
            event["event_hash"]
            for event in events
        ]

        merkle_root = build_merkle_root(event_hashes)

        chained_root = calculate_chained_root(
            None,
            merkle_root,
        )

        batch = {
            "batch_id": 1,
            "start_event_id": 1,
            "end_event_id": 4,
            "leaf_count": 4,
            "merkle_root": merkle_root,
            "previous_root_hash": "",
            "chained_root_hash": chained_root,
            "created_at": "2026-10-07T14:34:00",
        }

        checkpoint = {
            "batch_id": 1,
            "chained_root_hash": chained_root,
        }

        return batch, checkpoint

    def test_canonicalization_is_deterministic(self):
        event1 = {
            "operation": "UPDATE",
            "table_name": "accounts",
            "record_key": "1",
            "old_data": {"balance": "50000.00"},
            "new_data": {"balance": "45000.00"},
            "actor": "demo_user",
            "created_at": "2026-10-07T14:30:00",
        }

        event2 = {
            "created_at": "2026-10-07T14:30:00",
            "actor": "demo_user",
            "new_data": {"balance": "45000.00"},
            "old_data": {"balance": "50000.00"},
            "record_key": "1",
            "table_name": "accounts",
            "operation": "UPDATE",
        }

        self.assertEqual(
            canonicalize_event(event1),
            canonicalize_event(event2),
        )

        self.assertEqual(
            calculate_event_hash(event1, None),
            calculate_event_hash(event2, None),
        )

    def test_metadata_does_not_change_event_hash(self):
        event = {
            "operation": "UPDATE",
            "table_name": "accounts",
            "record_key": "1",
            "old_data": {"balance": "50000.00"},
            "new_data": {"balance": "45000.00"},
            "actor": "demo_user",
            "created_at": "2026-10-07T14:30:00",
        }

        event_with_metadata = {
            **event,
            "event_id": 999,
            "previous_hash": "abc",
            "event_hash": "def",
            "batch_id": 99,
        }

        self.assertEqual(
            calculate_event_hash(event, None),
            calculate_event_hash(event_with_metadata, None),
        )

    def test_changed_event_changes_hash(self):
        event = {
            "operation": "UPDATE",
            "table_name": "accounts",
            "record_key": "1",
            "old_data": {"balance": "50000.00"},
            "new_data": {"balance": "45000.00"},
            "actor": "demo_user",
            "created_at": "2026-10-07T14:30:00",
        }

        changed_event = {
            **event,
            "new_data": {"balance": "45001.00"},
        }

        self.assertNotEqual(
            calculate_event_hash(event, None),
            calculate_event_hash(changed_event, None),
        )

    def test_hash_chain_verifies(self):
        events = self.create_events()

        result = verify_hash_chain(events)

        self.assertTrue(result["valid"])

    def test_hash_chain_detects_tampering(self):
        events = self.create_events()

        events[1]["new_data"]["balance"] = "99999.00"

        result = verify_hash_chain(events)

        self.assertFalse(result["valid"])
        self.assertEqual(result["type"], "EVENT_HASH")
        self.assertEqual(result["event_id"], 2)

    def test_merkle_root_changes_when_leaf_changes(self):
        events = self.create_events()

        original_hashes = [
            event["event_hash"]
            for event in events
        ]

        original_root = build_merkle_root(original_hashes)

        modified_hashes = list(original_hashes)
        modified_hashes[2] = (
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        )

        modified_root = build_merkle_root(modified_hashes)

        self.assertNotEqual(
            original_root,
            modified_root,
        )

    def test_merkle_proof(self):
        events = self.create_events()

        event_hashes = [
            event["event_hash"]
            for event in events
        ]

        root = build_merkle_root(event_hashes)

        proof = build_merkle_proof(
            event_hashes,
            2,
        )

        self.assertTrue(
            verify_merkle_proof(
                event_hashes[2],
                proof,
                root,
            )
        )

    def test_merkle_proof_rejects_wrong_leaf(self):
        events = self.create_events()

        event_hashes = [
            event["event_hash"]
            for event in events
        ]

        root = build_merkle_root(event_hashes)

        proof = build_merkle_proof(
            event_hashes,
            2,
        )

        wrong_leaf = (
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        )

        self.assertFalse(
            verify_merkle_proof(
                wrong_leaf,
                proof,
                root,
            )
        )

    def test_root_chaining(self):
        root1 = build_merkle_root(
            [
                "1111111111111111111111111111111111111111111111111111111111111111",
                "2222222222222222222222222222222222222222222222222222222222222222",
                "3333333333333333333333333333333333333333333333333333333333333333",
                "4444444444444444444444444444444444444444444444444444444444444444",
            ]
        )

        chained_root = calculate_chained_root(
            None,
            root1,
        )

        self.assertEqual(
            len(chained_root),
            64,
        )

    def test_checkpoint_save_and_load(self):
        checkpoint_path = "test_checkpoint.json"

        try:
            save_checkpoint(
                batch_id=1,
                chained_root_hash="a" * 64,
                path=checkpoint_path,
            )

            checkpoint = load_checkpoint(
                checkpoint_path
            )

            self.assertEqual(
                checkpoint["batch_id"],
                1,
            )

            self.assertEqual(
                checkpoint["chained_root_hash"],
                "a" * 64,
            )

        finally:
            if os.path.exists(checkpoint_path):
                os.remove(checkpoint_path)

    def test_complete_verifier_returns_verified(self):
        events = self.create_events()

        batch, checkpoint = self.create_batch(events)

        result = verify_cryptographic_integrity(
            events,
            [batch],
            checkpoint,
        )

        self.assertTrue(result["valid"])
        self.assertEqual(
            result["status"],
            "VERIFIED",
        )

    def test_complete_verifier_detects_event_tampering(self):
        events = self.create_events()

        batch, checkpoint = self.create_batch(events)

        events[1]["new_data"]["balance"] = "99999.00"

        result = verify_cryptographic_integrity(
            events,
            [batch],
            checkpoint,
        )

        self.assertFalse(result["valid"])
        self.assertEqual(
            result["status"],
            "TAMPERING_DETECTED",
        )
        self.assertEqual(
            result["type"],
            "EVENT_HASH",
        )
        self.assertEqual(
            result["event_id"],
            2,
        )

    def test_hash_chain_detects_deleted_event(self):
        events = self.create_events()

        # Delete Event 2 from the sequence.
        del events[1]

        result = verify_hash_chain(events)

        self.assertFalse(result["valid"])
        self.assertEqual(result["type"], "HASH_CHAIN")
        self.assertEqual(result["event_id"], 3)

    def test_complete_verifier_detects_changed_batch_root(self):
        events = self.create_events()

        batch, checkpoint = self.create_batch(events)

        # Tamper with the stored Merkle root.
        batch["merkle_root"] = "a" * 64

        result = verify_cryptographic_integrity(
            events,
            [batch],
            checkpoint,
        )

        self.assertFalse(result["valid"])
        self.assertEqual(
            result["status"],
            "TAMPERING_DETECTED",
        )
        self.assertEqual(
            result["type"],
            "MERKLE_ROOT",
        )
        self.assertEqual(
            result["batch_id"],
            1,
        )

    def test_complete_verifier_detects_changed_checkpoint(self):
        events = self.create_events()

        batch, checkpoint = self.create_batch(events)

        # Tamper with the external checkpoint hash.
        checkpoint["chained_root_hash"] = "b" * 64

        result = verify_cryptographic_integrity(
            events,
            [batch],
            checkpoint,
        )

        self.assertFalse(result["valid"])
        self.assertEqual(
            result["status"],
            "TAMPERING_DETECTED",
        )
        self.assertEqual(
            result["type"],
            "CHECKPOINT",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)