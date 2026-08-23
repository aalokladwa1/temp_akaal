"""
akaalEngine.discovery.core.fingerprint
=====================================
Deterministic SHA-256 structural metadata fingerprint calculator.
Computes canonical hashes across all material physical discovery domains.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Optional

from akaalEngine.discovery.models.snapshot import DiscoveryFingerprint


class DiscoveryFingerprintCalculator:
    """
    Computes deterministic structural metadata fingerprints for point-in-time drift verification.
    Guarantees consistent key-sorted canonical JSON serialization, full physical domain coverage,
    and exclusion of non-semantic timestamps or ephemeral sample data.
    """

    @classmethod
    def compute(
        cls,
        namespaces_dict: Mapping[str, Any],
        objects_dict: Mapping[str, Any],
        structures_dict: Mapping[str, Any],
        identity_dict: Optional[Mapping[str, Any]] = None,
        permissions_dict: Optional[Mapping[str, Any]] = None,
        programmables_dict: Optional[Mapping[str, Any]] = None,
        partitioning_dict: Optional[Mapping[str, Any]] = None,
        statistics_dict: Optional[Mapping[str, Any]] = None,
        volume_dict: Optional[Mapping[str, Any]] = None,
        topology_dict: Optional[Mapping[str, Any]] = None,
        cdc_dict: Optional[Mapping[str, Any]] = None,
        environment_dict: Optional[Mapping[str, Any]] = None,
    ) -> DiscoveryFingerprint:
        component_hashes: dict[str, str] = {}

        # 1. Identity Domain
        if identity_dict:
            id_json = json.dumps(identity_dict, sort_keys=True)
            component_hashes["identity"] = hashlib.sha256(id_json.encode("utf-8")).hexdigest()

        # 2. Permissions Domain
        if permissions_dict:
            perm_json = json.dumps(permissions_dict, sort_keys=True)
            component_hashes["permissions"] = hashlib.sha256(perm_json.encode("utf-8")).hexdigest()

        # 3. Namespaces Domain
        ns_json = json.dumps(namespaces_dict or {}, sort_keys=True)
        component_hashes["namespaces"] = hashlib.sha256(ns_json.encode("utf-8")).hexdigest()

        # 4. Objects Domain (Tables & Views)
        obj_json = json.dumps(objects_dict or {}, sort_keys=True)
        component_hashes["objects"] = hashlib.sha256(obj_json.encode("utf-8")).hexdigest()

        # 5. Structures Domain (Columns, PKs, FKs, Unique, Check, Indexes)
        struct_json = json.dumps(structures_dict or {}, sort_keys=True)
        component_hashes["structures"] = hashlib.sha256(struct_json.encode("utf-8")).hexdigest()

        # 6. Programmables Domain (Routines, Triggers, Sequences, UDTs)
        if programmables_dict:
            prog_json = json.dumps(programmables_dict, sort_keys=True)
            component_hashes["programmables"] = hashlib.sha256(prog_json.encode("utf-8")).hexdigest()

        # 7. Partitioning Domain
        if partitioning_dict:
            part_json = json.dumps(partitioning_dict, sort_keys=True)
            component_hashes["partitioning"] = hashlib.sha256(part_json.encode("utf-8")).hexdigest()

        # 8. Statistics Domain
        if statistics_dict:
            stats_json = json.dumps(statistics_dict, sort_keys=True)
            component_hashes["statistics"] = hashlib.sha256(stats_json.encode("utf-8")).hexdigest()

        # 9. Volume Domain
        if volume_dict:
            vol_json = json.dumps(volume_dict, sort_keys=True)
            component_hashes["volume"] = hashlib.sha256(vol_json.encode("utf-8")).hexdigest()

        # 10. Topology Domain
        if topology_dict:
            topo_json = json.dumps(topology_dict, sort_keys=True)
            component_hashes["topology"] = hashlib.sha256(topo_json.encode("utf-8")).hexdigest()

        # 11. CDC Prerequisites Domain
        if cdc_dict:
            cdc_json = json.dumps(cdc_dict, sort_keys=True)
            component_hashes["cdc"] = hashlib.sha256(cdc_json.encode("utf-8")).hexdigest()

        # 12. Environment Domain (Version, Edition, Charset, Collation)
        if environment_dict:
            env_json = json.dumps(environment_dict, sort_keys=True)
            component_hashes["environment"] = hashlib.sha256(env_json.encode("utf-8")).hexdigest()

        # Top-level Composite Canonical Hash
        overall_json = json.dumps(component_hashes, sort_keys=True)
        overall_hash = hashlib.sha256(overall_json.encode("utf-8")).hexdigest()

        return DiscoveryFingerprint(
            sha256_hash=overall_hash,
            component_hashes=component_hashes,
        )
