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
    else:
        raise ValueError(f"Unsupported or missing engine for CDC position: '{engine}'")

