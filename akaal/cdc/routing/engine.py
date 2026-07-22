"""
CDC Routing Engine & Route Rules Policy.
"""

from typing import List, Dict, Optional, Callable
try:
    from pydantic import BaseModel, Field
except ImportError:
    class BaseModel:
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)
        def dict(self):
            return self.__dict__
        def model_dump(self):
            return self.__dict__
    def Field(default=None, default_factory=None, **kwargs):
        return default
from akaal.cdc.contracts.event import CDCEvent


class RoutePolicy(BaseModel):
    route_id: str
    table_pattern: str = "*"
    tenant_filter: Optional[str] = None
    target_destination: str
    filter_func: Optional[Callable[[CDCEvent], bool]] = None


class CDCRoutingEngine:
    """Enterprise CDC Routing Engine directing events based on rules."""

    def __init__(self) -> None:
        self.routes: List[RoutePolicy] = []

    def add_route(self, route: RoutePolicy) -> None:
        self.routes.append(route)

    def route_event(self, event: CDCEvent) -> List[str]:
        """
        Determine target destinations for a CDC event based on registered policies.
        Preserves per-table ordering.
        """
        destinations = []
        full_table_name = f"{event.source_schema}.{event.source_table}"

        for r in self.routes:
            # Check table pattern match
            if fnmatch.fnmatch(full_table_name, r.table_pattern) or fnmatch.fnmatch(event.source_table, r.table_pattern):
                # Check tenant filter
                if r.tenant_filter and event.tenant_id != r.tenant_filter:
                    continue
                destinations.append(r.target_destination)

        return destinations if destinations else ["default_destination"]
