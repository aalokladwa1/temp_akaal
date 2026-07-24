"""MerkleService: 256-bit SHA256 Cryptographic Merkle Tree Engine."""

import hashlib
from typing import Any, Dict, List, Optional, Tuple
from akaal.validation.core.interfaces import IService


class MerkleNode:
    """Node in a Merkle Tree."""

    def __init__(self, hash_val: str, left: Optional["MerkleNode"] = None, right: Optional["MerkleNode"] = None, data: Any = None):
        self.hash = hash_val
        self.left = left
        self.right = right
        self.data = data


class MerkleService(IService):
    """Infrastructure service for building and comparing SHA256 Merkle trees across tables."""

    @property
    def service_name(self) -> str:
        return "MerkleService"

    def compute_sha256(self, value: Any) -> str:
        """Compute SHA256 string for data chunk."""
        serialized = str(value).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    def build_tree(self, leaf_data: List[Any]) -> Tuple[Optional[MerkleNode], str]:
        """Build Merkle Tree from list of records or row hashes. Return (root_node, root_hash)."""
        if not leaf_data:
            empty_hash = hashlib.sha256(b"").hexdigest()
            return MerkleNode(empty_hash), empty_hash

        # Step 1: Create leaf nodes
        nodes = [MerkleNode(self.compute_sha256(item), data=item) for item in leaf_data]

        # Step 2: Build tree upwards
        while len(nodes) > 1:
            if len(nodes) % 2 != 0:
                nodes.append(nodes[-1])  # Duplicate last element if odd number

            next_level = []
            for i in range(0, len(nodes), 2):
                combined_hash = hashlib.sha256((nodes[i].hash + nodes[i + 1].hash).encode("utf-8")).hexdigest()
                parent = MerkleNode(combined_hash, left=nodes[i], right=nodes[i + 1])
                next_level.append(parent)

            nodes = next_level

        root_node = nodes[0]
        return root_node, root_node.hash

    def compare_trees(self, source_root: Optional[MerkleNode], target_root: Optional[MerkleNode]) -> Tuple[bool, List[Any]]:
        """Compare two Merkle Trees and return (is_identical, mismatched_data_list)."""
        if not source_root or not target_root:
            return source_root == target_root, []

        if source_root.hash == target_root.hash:
            return True, []

        mismatches = []
        stack = [(source_root, target_root)]

        while stack:
            src, tgt = stack.pop()
            if not src or not tgt:
                continue

            if src.hash != tgt.hash:
                if src.left is None and src.right is None:
                    # Leaf node mismatch
                    mismatches.append({"source": src.data, "target": tgt.data})
                else:
                    if src.left and tgt.left:
                        stack.append((src.left, tgt.left))
                    if src.right and tgt.right:
                        stack.append((src.right, tgt.right))

        return False, mismatches
