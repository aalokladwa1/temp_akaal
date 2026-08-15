"""
AKAAL Canonical CDC Partition Router (P3.6).
============================================================
Determines stable, identity-bound, generation-aware partition routing.
Uses SHA-256 deterministic hashing — NEVER process-randomized hash().
"""

import hashlib
import logging
from typing import List, Dict, Any, Optional
from akaal.cdc.domain.events import CDCEventIdentity, CDCEvent, CDCTransaction
from akaal.cdc.sharding.domain import CDCRoutedTransaction, CDCPartitionKey

logger = logging.getLogger(__name__)


class CDCPartitionRouter:
    """Canonical Partition Router for CDC transactions and events."""

    def __init__(
        self,
        partition_count: int = 4,
        routing_generation: int = 1,
        shard_key_rules: Optional[Dict[str, str]] = None,
    ) -> None:
        if partition_count <= 0:
            raise ValueError("partition_count must be greater than 0")
        self.partition_count = partition_count
        self.routing_generation = routing_generation
        self.shard_key_rules = shard_key_rules or {}

    @classmethod
    def get_deterministic_hash_slot(
        cls,
        cdc_session_id: str,
        table_name: str,
        entity_key: str,
        partition_count: int,
        routing_generation: int,
    ) -> int:
        """
        Computes deterministic partition slot (0 <= slot < partition_count).
        Strictly uses SHA-256 HMAC digest to ensure cross-process stability.
        """
        payload = f"{cdc_session_id}:{table_name}:{entity_key}:{routing_generation}".encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        slot = int(digest[:16], 16) % partition_count
        return slot

    def extract_entity_key(self, event: CDCEvent) -> str:
        """Extracts entity key from CDCEvent based on payload primary keys or rules."""
        table_name = event.source_table
        custom_key_field = self.shard_key_rules.get(table_name) or self.shard_key_rules.get("*")

        image = event.after_image or event.before_image or {}

        if custom_key_field and custom_key_field in image:
            return str(image[custom_key_field])

        # Priority 1: standard primary key names
        for pk_col in ["id", "uuid", "pk", f"{table_name}_id", "_id"]:
            if pk_col in image:
                return str(image[pk_col])

        # Priority 2: first key in dictionary
        if image:
            first_val = next(iter(image.values()))
            return str(first_val)

        # Fallback: table name default
        return f"table-{table_name}"

    def route_event(
        self,
        event: CDCEvent,
        partition_count: Optional[int] = None,
        routing_generation: Optional[int] = None,
    ) -> CDCPartitionKey:
        """Routes an individual CDC event to a CDCPartitionKey."""
        part_count = partition_count or self.partition_count
        gen = routing_generation if routing_generation is not None else self.routing_generation
        entity_key = self.extract_entity_key(event)
        part_id = self.get_deterministic_hash_slot(
            cdc_session_id=event.identity.cdc_session_id,
            table_name=event.source_table,
            entity_key=entity_key,
            partition_count=part_count,
            routing_generation=gen,
        )
        return CDCPartitionKey(
            identity=event.identity,
            table_name=event.source_table,
            entity_key=entity_key,
            partition_id=part_id,
            routing_generation=gen,
        )

    def route_transaction(
        self,
        transaction: CDCTransaction,
        partition_count: Optional[int] = None,
        routing_generation: Optional[int] = None,
    ) -> CDCRoutedTransaction:
        """
        Routes an atomic CDCTransaction.
        Gathers target partitions for all events within the transaction.
        If multiple distinct partitions are touched, marks transaction as multi-partition.
        """
        part_count = partition_count or self.partition_count
        gen = routing_generation if routing_generation is not None else self.routing_generation

        target_partitions: List[int] = []
        for event in transaction.events:
            pkey = self.route_event(event, partition_count=part_count, routing_generation=gen)
            if pkey.partition_id not in target_partitions:
                target_partitions.append(pkey.partition_id)

        if not target_partitions:
            target_partitions = [0]

        is_multi = len(target_partitions) > 1

        return CDCRoutedTransaction(
            transaction=transaction,
            partition_ids=target_partitions,
            routing_generation=gen,
            is_multi_partition=is_multi,
        )
