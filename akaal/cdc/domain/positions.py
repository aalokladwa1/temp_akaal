"""
AKAAL CDC Engine Source Position Domain Models.
===============================================
Polymorphic, engine-specific source position abstractions for PostgreSQL (LSN), MySQL (GTID/Binlog),
Oracle (SCN), SQL Server (LSN), and MongoDB (OpLog) with strict serialization, parsing, and monotonicity checks.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import json


class CDCSourcePosition(ABC):
    """Abstract base class for all engine-specific CDC source positions."""

    def __init__(self, engine: str) -> None:
        self.engine = engine.upper()

    @abstractmethod
    def to_string(self) -> str:
        """String representation of position for logging & API DTOs."""
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serializable dictionary representation."""
        pass

    @abstractmethod
    def is_after(self, other: "CDCSourcePosition") -> bool:
        """Monotonic comparison: returns True if self is strictly after other."""
        pass

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, CDCSourcePosition):
            if hasattr(self, "numeric_val") and hasattr(other, "numeric_val"):
                return self.numeric_val < getattr(other, "numeric_val")
            return not self.is_after(other) and self.to_string() != other.to_string()
        return NotImplemented

    def __le__(self, other: Any) -> bool:
        if isinstance(other, CDCSourcePosition):
            return self < other or self.to_string() == other.to_string()
        return NotImplemented

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, CDCSourcePosition):
            return self.is_after(other)
        return NotImplemented

    def __ge__(self, other: Any) -> bool:
        if isinstance(other, CDCSourcePosition):
            return self.is_after(other) or self.to_string() == other.to_string()
        return NotImplemented

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, CDCSourcePosition):
            return self.engine == other.engine and self.to_string() == other.to_string()
        return False

    def __str__(self) -> str:
        return f"{self.engine}:{self.to_string()}"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} engine={self.engine} pos={self.to_string()}>"


class PostgresLSNPosition(CDCSourcePosition):
    """PostgreSQL LSN (Log Sequence Number) Source Position."""

    def __init__(self, lsn: str, flushed_lsn: Optional[str] = None) -> None:
        super().__init__("POSTGRESQL")
        if not lsn or "/" not in lsn:
            raise ValueError(f"Invalid PostgreSQL LSN format: '{lsn}'")
        self.lsn = lsn.upper()
        self.flushed_lsn = (flushed_lsn or lsn).upper()
        self.numeric_val = self._lsn_to_int(self.lsn)

    @staticmethod
    def _lsn_to_int(lsn_str: str) -> int:
        parts = lsn_str.split("/")
        if len(parts) != 2:
            raise ValueError(f"Malformed LSN '{lsn_str}'")
        return (int(parts[0], 16) << 32) + int(parts[1], 16)

    def to_string(self) -> str:
        return self.lsn

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine": self.engine,
            "lsn": self.lsn,
            "flushed_lsn": self.flushed_lsn,
            "numeric_val": self.numeric_val,
        }

    def is_after(self, other: CDCSourcePosition) -> bool:
        if not isinstance(other, PostgresLSNPosition) or self.engine != other.engine:
            raise TypeError(f"Cannot compare PostgresLSNPosition with {type(other)} (engine={getattr(other, 'engine', None)})")
        return self.numeric_val > other.numeric_val


class MySQLGTIDPosition(CDCSourcePosition):
    """MySQL Binlog File + Offset and/or GTID Set Source Position."""

    def __init__(self, binlog_file: str, binlog_pos: int, gtid_set: Optional[str] = None) -> None:
        super().__init__("MYSQL")
        if binlog_pos < 0 or not binlog_file:
            raise ValueError(f"Invalid MySQL binlog file or position: '{binlog_file}':{binlog_pos}")
        self.binlog_file = binlog_file
        self.binlog_pos = binlog_pos
        self.gtid_set = gtid_set

    def to_string(self) -> str:
        if self.gtid_set:
            return f"{self.gtid_set}@{self.binlog_file}:{self.binlog_pos}"
        return f"{self.binlog_file}:{self.binlog_pos}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine": self.engine,
            "binlog_file": self.binlog_file,
            "binlog_pos": self.binlog_pos,
            "gtid_set": self.gtid_set,
        }

    def is_after(self, other: CDCSourcePosition) -> bool:
        if not isinstance(other, MySQLGTIDPosition) or self.engine != other.engine:
            raise TypeError(f"Cannot compare MySQLGTIDPosition with {type(other)} (engine={getattr(other, 'engine', None)})")
        if self.binlog_file == other.binlog_file:
            return self.binlog_pos > other.binlog_pos
        return self.binlog_file > other.binlog_file


class OracleSCNPosition(CDCSourcePosition):
    """Oracle System Change Number (SCN) Source Position."""

    def __init__(self, scn: int, sequence_number: int = 0, redo_thread: int = 1) -> None:
        super().__init__("ORACLE")
        if scn < 0:
            raise ValueError(f"Invalid Oracle SCN: {scn}")
        self.scn = scn
        self.sequence_number = sequence_number
        self.redo_thread = redo_thread

    def to_string(self) -> str:
        return f"SCN:{self.scn}#SEQ:{self.sequence_number}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine": self.engine,
            "scn": self.scn,
            "sequence_number": self.sequence_number,
            "redo_thread": self.redo_thread,
        }

    def is_after(self, other: CDCSourcePosition) -> bool:
        if not isinstance(other, OracleSCNPosition) or self.engine != other.engine:
            raise TypeError(f"Cannot compare OracleSCNPosition with {type(other)} (engine={getattr(other, 'engine', None)})")
        if self.scn == other.scn:
            return self.sequence_number > other.sequence_number
        return self.scn > other.scn


class MSSQLChangePosition(CDCSourcePosition):
    """SQL Server CDC LSN / Change Position."""

    def __init__(self, lsn_hex: str, seqval_hex: Optional[str] = None) -> None:
        super().__init__("MSSQL")
        if not lsn_hex:
            raise ValueError("SQL Server LSN cannot be empty")
        self.lsn_hex = lsn_hex.upper()
        self.seqval_hex = (seqval_hex or "00000000").upper()

    def to_string(self) -> str:
        return f"{self.lsn_hex}:{self.seqval_hex}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine": self.engine,
            "lsn_hex": self.lsn_hex,
            "seqval_hex": self.seqval_hex,
        }

    def is_after(self, other: CDCSourcePosition) -> bool:
        if not isinstance(other, MSSQLChangePosition) or self.engine != other.engine:
            raise TypeError(f"Cannot compare MSSQLChangePosition with {type(other)} (engine={getattr(other, 'engine', None)})")
        if self.lsn_hex == other.lsn_hex:
            return self.seqval_hex > other.seqval_hex
        return self.lsn_hex > other.lsn_hex


class MongoDBOpLogPosition(CDCSourcePosition):
    """MongoDB OpLog Timestamp + Increment Position."""

    def __init__(self, timestamp_sec: int, inc: int) -> None:
        super().__init__("MONGODB")
        if timestamp_sec < 0 or inc < 0:
            raise ValueError("MongoDB OpLog timestamp and inc must be non-negative")
        self.timestamp_sec = timestamp_sec
        self.inc = inc

    def to_string(self) -> str:
        return f"TS:{self.timestamp_sec}:{self.inc}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine": self.engine,
            "timestamp_sec": self.timestamp_sec,
            "inc": self.inc,
        }

    def is_after(self, other: CDCSourcePosition) -> bool:
        if not isinstance(other, MongoDBOpLogPosition) or self.engine != other.engine:
            raise TypeError(f"Cannot compare MongoDBOpLogPosition with {type(other)} (engine={getattr(other, 'engine', None)})")
        if self.timestamp_sec == other.timestamp_sec:
            return self.inc > other.inc
        return self.timestamp_sec > other.timestamp_sec


class MariaDBGTIDPosition(CDCSourcePosition):
    """MariaDB GTID (Domain-Server-Sequence) and Binlog Source Position."""

    def __init__(self, domain_id: int, server_id: int, sequence_no: int, binlog_file: Optional[str] = None, binlog_pos: int = 0) -> None:
        super().__init__("MARIADB")
        if domain_id < 0 or server_id < 0 or sequence_no < 0:
            raise ValueError("MariaDB GTID domain_id, server_id, and sequence_no must be non-negative")
        self.domain_id = domain_id
        self.server_id = server_id
        self.sequence_no = sequence_no
        self.binlog_file = binlog_file or "mariadb-bin.000001"
        self.binlog_pos = binlog_pos

    def to_string(self) -> str:
        return f"{self.domain_id}-{self.server_id}-{self.sequence_no}@{self.binlog_file}:{self.binlog_pos}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine": self.engine,
            "domain_id": self.domain_id,
            "server_id": self.server_id,
            "sequence_no": self.sequence_no,
            "binlog_file": self.binlog_file,
            "binlog_pos": self.binlog_pos,
        }

    def is_after(self, other: CDCSourcePosition) -> bool:
        if not isinstance(other, MariaDBGTIDPosition) or self.engine != other.engine:
            raise TypeError(f"Cannot compare MariaDBGTIDPosition with {type(other)} (engine={getattr(other, 'engine', None)})")
        if self.domain_id == other.domain_id and self.server_id == other.server_id:
            return self.sequence_no > other.sequence_no
        if self.sequence_no == other.sequence_no:
            return self.binlog_pos > other.binlog_pos
        return self.sequence_no > other.sequence_no


class DeltaTableVersionPosition(CDCSourcePosition):
    """Databricks / Delta Lake table version & commit source position."""

    def __init__(
        self,
        table_version: int,
        table_name: str = "",
        timestamp_ms: Optional[int] = None,
        commit_id: Optional[str] = None,
    ) -> None:
        super().__init__("DATABRICKS")
        if table_version < 0:
            raise ValueError("Delta table version must be non-negative")
        self.table_version = table_version
        self.table_name = table_name
        self.timestamp_ms = timestamp_ms
        self.commit_id = commit_id

    def to_string(self) -> str:
        tbl_pfx = f"{self.table_name}@" if self.table_name else ""
        return f"{tbl_pfx}v{self.table_version}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine": self.engine,
            "table_version": self.table_version,
            "table_name": self.table_name,
            "timestamp_ms": self.timestamp_ms,
            "commit_id": self.commit_id,
        }

    def is_after(self, other: CDCSourcePosition) -> bool:
        if not isinstance(other, DeltaTableVersionPosition) or self.engine != other.engine:
            raise TypeError(f"Cannot compare DeltaTableVersionPosition with {type(other)} (engine={getattr(other, 'engine', None)})")
        if self.table_name and other.table_name and self.table_name != other.table_name:
            raise TypeError(f"Cannot compare Delta positions across disparate tables: '{self.table_name}' vs '{other.table_name}'")
        return self.table_version > other.table_version


class WarehouseQueryPosition(CDCSourcePosition):
    """Cloud Data Warehouse extraction query job / chunk / offset position."""

    def __init__(
        self,
        engine: str,
        query_id: str,
        chunk_index: int = 0,
        row_offset: int = 0,
    ) -> None:
        super().__init__(engine.upper())
        if chunk_index < 0 or row_offset < 0:
            raise ValueError("WarehouseQueryPosition chunk_index and row_offset must be non-negative")
        self.query_id = str(query_id).strip()
        self.chunk_index = chunk_index
        self.row_offset = row_offset

    def to_string(self) -> str:
        return f"{self.query_id}:chunk{self.chunk_index}:offset{self.row_offset}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine": self.engine,
            "query_id": self.query_id,
            "chunk_index": self.chunk_index,
            "row_offset": self.row_offset,
        }

    def is_after(self, other: CDCSourcePosition) -> bool:
        if not isinstance(other, WarehouseQueryPosition) or self.engine != other.engine:
            raise TypeError(f"Cannot compare WarehouseQueryPosition with {type(other)} (engine={getattr(other, 'engine', None)})")
        if self.query_id != other.query_id:
            raise TypeError(f"Cannot compare positions across different query IDs: '{self.query_id}' vs '{other.query_id}'")
        if self.chunk_index == other.chunk_index:
            return self.row_offset > other.row_offset
        return self.chunk_index > other.chunk_index


def parse_source_position(data: Dict[str, Any]) -> CDCSourcePosition:
    """Parses a dictionary into the appropriate engine-specific CDCSourcePosition instance."""
    if not isinstance(data, dict):
        raise ValueError("Position data must be a dictionary.")
    engine = data.get("engine", "").upper()
    if engine in ("POSTGRESQL", "POSTGRES"):
        return PostgresLSNPosition(lsn=data["lsn"], flushed_lsn=data.get("flushed_lsn"))
    elif engine == "MYSQL":
        return MySQLGTIDPosition(
            binlog_file=data["binlog_file"],
            binlog_pos=data["binlog_pos"],
            gtid_set=data.get("gtid_set"),
        )
    elif engine == "MARIADB":
        return MariaDBGTIDPosition(
            domain_id=data.get("domain_id", 0),
            server_id=data.get("server_id", 1),
            sequence_no=data.get("sequence_no", data.get("binlog_pos", 0)),
            binlog_file=data.get("binlog_file"),
            binlog_pos=data.get("binlog_pos", 0),
        )
    elif engine == "ORACLE":
        return OracleSCNPosition(
            scn=data["scn"],
            sequence_number=data.get("sequence_number", 0),
            redo_thread=data.get("redo_thread", 1),
        )
    elif engine == "MSSQL":
        return MSSQLChangePosition(lsn_hex=data["lsn_hex"], seqval_hex=data.get("seqval_hex"))
    elif engine == "MONGODB":
        return MongoDBOpLogPosition(timestamp_sec=data["timestamp_sec"], inc=data["inc"])
    elif engine in ("DATABRICKS", "DELTA", "DELTA_LAKE"):
        return DeltaTableVersionPosition(
            table_version=data.get("table_version", data.get("version", 0)),
            table_name=data.get("table_name", ""),
            timestamp_ms=data.get("timestamp_ms"),
            commit_id=data.get("commit_id"),
        )
    elif engine in ("SNOWFLAKE", "BIGQUERY", "REDSHIFT", "WAREHOUSE"):
        return WarehouseQueryPosition(
            engine=engine,
            query_id=data.get("query_id", "q-default"),
            chunk_index=data.get("chunk_index", 0),
            row_offset=data.get("row_offset", 0),
        )
    else:
        raise ValueError(f"Unsupported or missing engine for CDC position: '{engine}'")

