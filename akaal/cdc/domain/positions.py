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
        if not isinstance(other, PostgresLSNPosition):
            raise TypeError(f"Cannot compare PostgresLSNPosition with {type(other)}")
        return self.numeric_val > other.numeric_val


class MySQLGTIDPosition(CDCSourcePosition):
    """MySQL Binlog File + Offset and/or GTID Set Source Position."""

    def __init__(self, binlog_file: str, binlog_pos: int, gtid_set: Optional[str] = None) -> None:
        super().__init__("MYSQL")
        if binlog_pos < 0:
            raise ValueError(f"Invalid MySQL binlog position: {binlog_pos}")
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
        if not isinstance(other, MySQLGTIDPosition):
            raise TypeError(f"Cannot compare MySQLGTIDPosition with {type(other)}")
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
        if not isinstance(other, OracleSCNPosition):
            raise TypeError(f"Cannot compare OracleSCNPosition with {type(other)}")
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
        if not isinstance(other, MSSQLChangePosition):
            raise TypeError(f"Cannot compare MSSQLChangePosition with {type(other)}")
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
        if not isinstance(other, MongoDBOpLogPosition):
            raise TypeError(f"Cannot compare MongoDBOpLogPosition with {type(other)}")
        if self.timestamp_sec == other.timestamp_sec:
            return self.inc > other.inc
        return self.timestamp_sec > other.timestamp_sec


def parse_source_position(data: Dict[str, Any]) -> CDCSourcePosition:
    """Parses a dictionary into the appropriate engine-specific CDCSourcePosition instance."""
    engine = data.get("engine", "").upper()
    if engine in ("POSTGRESQL", "POSTGRES"):
        return PostgresLSNPosition(lsn=data["lsn"], flushed_lsn=data.get("flushed_lsn"))
    elif engine == "MYSQL":
        return MySQLGTIDPosition(
            binlog_file=data["binlog_file"],
            binlog_pos=data["binlog_pos"],
            gtid_set=data.get("gtid_set"),
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
