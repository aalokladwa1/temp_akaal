import asyncio
import time
import logging
import hashlib
from typing import Any, Dict, List, Optional
from akaal.adapters.base_adapter import BaseAdapter
from akaal.adapters.adapter_registry import get_adapter_class

logger = logging.getLogger("akaal.connection_pool")

class ConnectionPool:
    """Database-agnostic Connection Pool.
    Interacts ONLY via BaseAdapter public methods:
    - create_connection()
    - close_connection(conn)
    - validate_connection(conn)
    Never touches private members or implementation details.
    """
    def __init__(self, config: Any):
        self.config = config
        self.enabled = getattr(config, "enable_connection_pooling", False)
        self.max_size = getattr(config, "maximum_pool_size", getattr(config, "pool_size", 4))
        self.min_size = getattr(config, "minimum_pool_size", 1)
        self.idle_timeout = getattr(config, "connection_idle_timeout", 60.0)
        self.acq_timeout = getattr(config, "acquisition_timeout", 5.0)
        self.validation_interval = getattr(config, "validation_interval", 30.0)
        self.validate_on_checkout = getattr(config, "connection_validation_on_checkout", True)

        self._idle_connections = []  # list of (conn, timestamp_idle, timestamp_validated)
        self._active_connections = set()  # set of active connection handles checked out
        self._all_connections = set()  # set of all active connection handles managed
        self._lock = asyncio.Lock()

        # Phase 7K — extract metrics registry from config dynamically
        self._metrics = getattr(config, "_metrics", None)

        # Runtime metrics
        self._total_acquisitions = 0
        self._physical_connections_created = 0
        self._peak_active_connections = 0

    async def initialize(self) -> None:
        """Prefill the pool up to minimum_pool_size."""
        if not self.enabled:
            return
        async with self._lock:
            for _ in range(self.min_size):
                try:
                    conn = await self._create_physical_connection()
                    self._idle_connections.append((conn, time.time(), time.time()))
                    self._all_connections.add(conn)
                except Exception as e:
                    logger.error("[ConnectionPool] Failed to initialize connection: %s", e)

    async def _create_physical_connection(self) -> Any:
        adapter_cls = get_adapter_class(self.config.system_type)
        # Create unpooled temp adapter to run connection establishment logic
        temp_adapter = adapter_cls(self.config)
        conn = await temp_adapter.create_connection()
        self._physical_connections_created += 1
        try:
            if self._metrics is not None:
                self._metrics.counter("pool_connection_create_count").increment()
        except Exception:
            pass
        return conn

    async def _close_physical_connection(self, conn: Any) -> None:
        adapter_cls = get_adapter_class(self.config.system_type)
        temp_adapter = adapter_cls(self.config)
        await temp_adapter.close_connection(conn)
        try:
            if self._metrics is not None:
                self._metrics.counter("pool_connection_close_count").increment()
        except Exception:
            pass

    async def _validate_physical_connection(self, conn: Any) -> bool:
        adapter_cls = get_adapter_class(self.config.system_type)
        temp_adapter = adapter_cls(self.config)
        return await temp_adapter.validate_connection(conn)

    async def acquire(self) -> Any:
        start_time = time.time()
        while True:
            async with self._lock:
                now = time.time()
                
                # 1. Prune expired idle connections (respecting minimum size)
                active_idle = []
                for conn, idle_since, val_since in self._idle_connections:
                    if now - idle_since > self.idle_timeout and len(self._all_connections) > self.min_size:
                        await self._close_physical_connection(conn)
                        self._all_connections.discard(conn)
                    else:
                        active_idle.append((conn, idle_since, val_since))
                self._idle_connections = active_idle

                # 2. Try to pop an idle connection
                while self._idle_connections:
                    conn, idle_since, val_since = self._idle_connections.pop(0)
                    
                    need_validation = self.validate_on_checkout or (now - val_since > self.validation_interval)
                    is_valid = True
                    if need_validation:
                        is_valid = await self._validate_physical_connection(conn)
                        
                    if is_valid:
                        self._active_connections.add(conn)
                        self._total_acquisitions += 1
                        self._peak_active_connections = max(self._peak_active_connections, len(self._active_connections))
                        try:
                            if self._metrics is not None:
                                self._metrics.counter("pool_acquire_count").increment()
                        except Exception:
                            pass
                        logger.debug("Connection acquired", extra={"event": "connection_acquired"})
                        return conn
                    else:
                        await self._close_physical_connection(conn)
                        self._all_connections.discard(conn)

                # 3. Create a new connection if max limit not reached
                if len(self._all_connections) < self.max_size:
                    try:
                        conn = await self._create_physical_connection()
                        self._all_connections.add(conn)
                        self._active_connections.add(conn)
                        self._total_acquisitions += 1
                        self._peak_active_connections = max(self._peak_active_connections, len(self._active_connections))
                        try:
                            if self._metrics is not None:
                                self._metrics.counter("pool_acquire_count").increment()
                        except Exception:
                            pass
                        logger.debug("Connection acquired", extra={"event": "connection_acquired"})
                        return conn
                    except Exception as e:
                        logger.error("[ConnectionPool] Failed to create physical connection: %s", e)
                        raise

            if time.time() - start_time > self.acq_timeout:
                raise asyncio.TimeoutError("Connection acquisition timeout exceeded")
            await asyncio.sleep(0.02)

    def get_pool_statistics(self) -> Dict[str, Any]:
        """Return a read-only dictionary of runtime statistics for the pool."""
        reused = max(0, self._total_acquisitions - self._physical_connections_created)
        rate = (reused / self._total_acquisitions) * 100.0 if self._total_acquisitions > 0 else 0.0
        return {
            "total_acquisitions": self._total_acquisitions,
            "physical_connections_created": self._physical_connections_created,
            "reused_connections": reused,
            "reuse_rate": rate,
            "peak_active_connections": self._peak_active_connections,
        }

    async def release(self, conn: Any) -> None:
        async with self._lock:
            if conn in self._active_connections:
                self._active_connections.remove(conn)
                try:
                    if self._metrics is not None:
                        self._metrics.counter("pool_release_count").increment()
                except Exception:
                    pass
                is_valid = await self._validate_physical_connection(conn)
                if is_valid:
                    self._idle_connections.append((conn, time.time(), time.time()))
                else:
                    await self._close_physical_connection(conn)
                    self._all_connections.discard(conn)
                logger.debug("Connection released", extra={"event": "connection_released"})

    async def shutdown(self) -> None:
        async with self._lock:
            for conn in list(self._all_connections):
                try:
                    await self._close_physical_connection(conn)
                except Exception as e:
                    logger.warning("[ConnectionPool] Error closing connection on shutdown: %s", e)
            self._idle_connections.clear()
            self._active_connections.clear()
            self._all_connections.clear()


_POOLS: Dict[str, ConnectionPool] = {}
_POOLS_LOCK = asyncio.Lock()

def _get_pool_key(config: Any) -> str:
    sys_type = config.system_type.value
    host = getattr(config, "host", "")
    db = getattr(config, "database_name", "")
    port = getattr(config, "port", "")
    user = getattr(config, "username", "")
    
    key_str = f"{sys_type}:{host}:{port}:{db}:{user}"
    return hashlib.sha256(key_str.encode("utf-8")).hexdigest()

async def get_connection_pool(config: Any) -> ConnectionPool:
    global _POOLS
    key = _get_pool_key(config)
    async with _POOLS_LOCK:
        if key not in _POOLS:
            pool = ConnectionPool(config)
            await pool.initialize()
            _POOLS[key] = pool
        return _POOLS[key]

async def shutdown_all_pools() -> None:
    global _POOLS
    async with _POOLS_LOCK:
        for pool in _POOLS.values():
            await pool.shutdown()
        _POOLS.clear()


class PooledAdapter(BaseAdapter):
    """Transparent adapter wrapper implementing BaseAdapter.
    Lazily acquires connection on connect() and releases on close().
    """
    def __init__(self, adapter: BaseAdapter):
        super().__init__(adapter.config)
        self._adapter = adapter
        self.config = adapter.config
        self.is_connected = False
        self._pool = None
        self._conn_handle = None

    def __getattr__(self, name: str) -> Any:
        return getattr(self._adapter, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ("_adapter", "config", "is_connected", "_pool", "_conn_handle", "mock_mode", "_discovery_provider") or "_adapter" not in self.__dict__:
            super().__setattr__(name, value)
        else:
            setattr(self._adapter, name, value)

    async def connect(self) -> None:
        if not self._pool:
            self._pool = await get_connection_pool(self.config)
        self._conn_handle = await self._pool.acquire()
        self._adapter.set_connection(self._conn_handle)
        self._adapter.is_connected = True
        self.is_connected = True

    async def close(self) -> None:
        if self._pool and self._conn_handle:
            await self._pool.release(self._conn_handle)
            self._adapter.set_connection(None)
            self._conn_handle = None
        self._adapter.is_connected = False
        self.is_connected = False

    def get_connection(self) -> Any:
        return self._adapter.get_connection()

    def set_connection(self, conn: Any) -> None:
        self._adapter.set_connection(conn)

    async def check_permissions(self) -> bool:
        return await self._adapter.check_permissions()

    async def discover_tables(self) -> List[str]:
        return await self._adapter.discover_tables()

    async def discover_columns(self, table_name: str) -> List[Dict[str, Any]]:
        return await self._adapter.discover_columns(table_name)

    async def discover_foreign_keys(self) -> List[Dict[str, Any]]:
        return await self._adapter.discover_foreign_keys()

    async def discover_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        return await self._adapter.discover_indexes(table_name)

    async def discover_constraints(self, table_name: str) -> List[Dict[str, Any]]:
        return await self._adapter.discover_constraints(table_name)

    async def discover_triggers(self, table_name: str) -> List[Dict[str, Any]]:
        return await self._adapter.discover_triggers(table_name)

    async def discover_views(self) -> List[Dict[str, Any]]:
        return await self._adapter.discover_views()

    async def read_batch(
        self,
        table_name: str,
        offset: int,
        limit: int,
        last_processed_primary_key: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        return await self._adapter.read_batch(table_name, offset, limit, last_processed_primary_key)

    async def write_batch(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        return await self._adapter.write_batch(table_name, rows)

    async def get_row_count(self, table_name: str) -> int:
        return await self._adapter.get_row_count(table_name)

    async def compute_checksum(self, table_name: str) -> str:
        return await self._adapter.compute_checksum(table_name)
