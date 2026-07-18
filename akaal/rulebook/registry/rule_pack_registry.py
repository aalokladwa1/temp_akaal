"""
Akaal — Rule Pack Registry
==========================
Registry for loading, unloading, and managing RuleProvider plugins.
"""

import threading
from typing import Dict, List, Optional, Type
from akaal.rulebook.providers.base_provider import BaseRuleProvider
from akaal.rulebook.providers.generic_provider import GenericRuleProvider
from akaal.rulebook.providers.postgres_provider import PostgresRuleProvider
from akaal.rulebook.providers.mysql_provider import MySQLRuleProvider
from akaal.rulebook.providers.oracle_provider import OracleRuleProvider
from akaal.rulebook.providers.sqlserver_provider import SQLServerRuleProvider
from akaal.rulebook.providers.mongodb_provider import MongoDBRuleProvider


class RulePackRegistry:
    """Registry for RuleProvider plugins."""

    def __init__(self, auto_register_defaults: bool = True) -> None:
        self._lock = threading.RLock()
        self._providers: Dict[str, BaseRuleProvider] = {}
        if auto_register_defaults:
            self._bootstrap_defaults()

    def _bootstrap_defaults(self) -> None:
        self.load(GenericRuleProvider())
        self.load(PostgresRuleProvider())
        self.load(MySQLRuleProvider())
        self.load(OracleRuleProvider())
        self.load(SQLServerRuleProvider())
        self.load(MongoDBRuleProvider())

    def load(self, provider: BaseRuleProvider) -> None:
        with self._lock:
            self._providers[provider.provider_id] = provider

    def unload(self, provider_id: str) -> None:
        with self._lock:
            self._providers.pop(provider_id, None)

    def get_provider(self, provider_id: str) -> Optional[BaseRuleProvider]:
        with self._lock:
            return self._providers.get(provider_id)

    def list_packs(self) -> List[Dict[str, str]]:
        with self._lock:
            return [p.metadata() for p in self._providers.values()]

    def checksum(self, provider_id: str) -> str:
        with self._lock:
            p = self._providers.get(provider_id)
            return p.checksum() if p else ""

    def manifest(self) -> Dict[str, str]:
        with self._lock:
            return {p_id: p.version() for p_id, p in self._providers.items()}
