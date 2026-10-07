import hashlib
import json
from datetime import datetime


def calculate_chained_root(
    previous_root_hash: str | None,
    merkle_root: str,
) -> str:
    """
    Calculate the chained root for a Merkle batch.

    Formula:
        SHA256(previous_root_hash + merkle_root)

    For the first batch, previous_root_hash is treated
    as an empty string.
    """

    if previous_root_hash is None:
        previous_root_hash = ""

    hash_input = previous_root_hash + merkle_root

    return hashlib.sha256(
        hash_input.encode("utf-8")
    ).hexdigest()


def save_checkpoint(
    batch_id: int,
    chained_root_hash: str,
    path: str = "checkpoint.json",
) -> None:
    """
    Save the latest trusted chained root to checkpoint.json.
    """

    checkpoint = {
        "batch_id": batch_id,
        "chained_root_hash": chained_root_hash,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }

    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            checkpoint,
            file,
            indent=2,
        )


def load_checkpoint(
    path: str = "checkpoint.json",
) -> dict | None:
    """
    Load the checkpoint from checkpoint.json.

    Returns None if the checkpoint file does not exist.
    """

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    except FileNotFoundError:
        return None