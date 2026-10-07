import hashlib


def hash_pair(left_hash: str, right_hash: str) -> str:
    """
    Hash two hexadecimal SHA-256 hashes together.

    Parent = SHA256(left_hash + right_hash)
    """

    combined = left_hash + right_hash

    return hashlib.sha256(
        combined.encode("utf-8")
    ).hexdigest()


def build_merkle_root(event_hashes: list[str]) -> str:
    """
    Build a Merkle root from event hashes.

    For an odd number of hashes at any level, the final hash
    is duplicated.

    The DBTHON batch size is 4 events.
    """

    if not event_hashes:
        raise ValueError("event_hashes cannot be empty")

    current_level = list(event_hashes)

    while len(current_level) > 1:
        next_level = []

        for index in range(0, len(current_level), 2):
            left_hash = current_level[index]

            if index + 1 < len(current_level):
                right_hash = current_level[index + 1]
            else:
                right_hash = left_hash

            parent_hash = hash_pair(
                left_hash,
                right_hash,
            )

            next_level.append(parent_hash)

        current_level = next_level

    return current_level[0]

def build_merkle_proof(
    event_hashes: list[str],
    index: int,
) -> list[dict]:
    """
    Build a Merkle inclusion proof for the leaf at index.

    Each proof item contains the sibling hash and the sibling's
    position relative to the current hash.
    """

    if not event_hashes:
        raise ValueError("event_hashes cannot be empty")

    if index < 0 or index >= len(event_hashes):
        raise IndexError("index out of range")

    current_level = list(event_hashes)
    current_index = index
    proof = []

    while len(current_level) > 1:
        # If there is an odd number of hashes, duplicate the last hash.
        if len(current_level) % 2 == 1:
            current_level.append(current_level[-1])

        if current_index % 2 == 0:
            sibling_index = current_index + 1
            sibling_position = "right"
        else:
            sibling_index = current_index - 1
            sibling_position = "left"

        proof.append({
            "position": sibling_position,
            "hash": current_level[sibling_index],
        })

        next_level = []

        for i in range(0, len(current_level), 2):
            next_level.append(
                hash_pair(
                    current_level[i],
                    current_level[i + 1],
                )
            )

        current_index //= 2
        current_level = next_level

    return proof


def verify_merkle_proof(
    leaf_hash: str,
    proof: list[dict],
    expected_root: str,
) -> bool:
    """
    Verify a Merkle inclusion proof against an expected root.
    """

    current_hash = leaf_hash

    for proof_item in proof:
        sibling_hash = proof_item["hash"]
        position = proof_item["position"]

        if position == "left":
            current_hash = hash_pair(
                sibling_hash,
                current_hash,
            )
        elif position == "right":
            current_hash = hash_pair(
                current_hash,
                sibling_hash,
            )
        else:
            return False

    return current_hash == expected_root