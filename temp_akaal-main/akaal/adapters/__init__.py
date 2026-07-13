"""Akaal Adapters — 17 database/storage systems supported."""
from akaal.adapters.adapter_registry import create_adapter, get_adapter_class
from akaal.adapters.base_adapter import BaseAdapter

__all__ = ["BaseAdapter", "create_adapter", "get_adapter_class"]
