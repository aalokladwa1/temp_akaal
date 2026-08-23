"""
akaalEngine.cdc.models.position
===============================
Engine-specific typed source position abstractions for PostgreSQL (LSN), Oracle (SCN),
MySQL (GTID/Binlog), MariaDB (GTID domain), SQL Server (LSN), MongoDB (OpLog), and Incremental Polling.
Cross-provider comparisons fail closed with TypeError.
"""

from abc import ABC, abstractmethod
import json
from typing import Any, Dict, Optional, Set

from akaalEngine.cdc.models.errors import CDCPositionError


class CDCSourcePosition(ABC):
    """Abstract base class for engine-specific CDC source positions."""

    def __init__(self, engine: str) -> None:
        self.engine = engine.upper()

    @abstractmethod
    def to_string(self) -> str:
        """Canonical string representation for position comparison & persistence."""
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serializable dictionary representation."""
        pass

    @abstractmethod
    def is_after(self, other: "CDCSourcePosition") -> bool:
        """Returns True if self is strictly after other."""
        pass

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, CDCSourcePosition):
            return False
        return self.engine == other.engine and self.to_string() == other.to_string()

    def __ge__(self, other: Any) -> bool:
        if not isinstance(other, CDCSourcePosition) or self.engine != other.engine:
            raise TypeError(f"Cannot compare positions across different engines: '{self.engine}' vs '{getattr(other, 'engine', None)}'")
        return self.is_after(other) or self.to_string() == other.to_string()

    def __gt__(self, other: Any) -> bool:
        if not isinstance(other, CDCSourcePosition) or self.engine != other.engine:
            raise TypeError(f"Cannot compare positions across different engines: '{self.engine}' vs '{getattr(other, 'engine', None)}'")
        return self.is_after(other)

    def __str__(self) -> str:
        return f"{self.engine}:{self.to_string()}"


class PostgresLSNPosition(CDCSourcePosition):
    """PostgreSQL LSN (Log Sequence Number) Source Position."""

    def __init__(self, lsn: str, flushed_lsn: Optional[str] = None) -> None:
        super().__init__("POSTGRESQL")
        if not lsn or "/" not in lsn:
            raise CDCPositionError(f"Invalid PostgreSQL LSN format: '{lsn}'")
        self.lsn = lsn.upper()
        self.flushed_lsn = (flushed_lsn or lsn).upper()
        self.numeric_val = self._lsn_to_int(self.lsn)

    @staticmethod
    def _lsn_to_int(lsn_str: str) -> int:
        parts = lsn_str.split("/")
        if len(parts) != 2:
            raise CDCPositionError(f"Malformed LSN '{lsn_str}'")
        return (int(parts[0], 16) << 32) + int(parts[1], 16)

    def to_string(self) -> str:
        return self.lsn

    def to_dict(self) -> Dict[str, Any]:
        return {"engine": self.engine, "lsn": self.lsn, "flushed_lsn": self.flushed_lsn, "numeric_val": self.numeric_val}

    def is_after(self, other: CDCSourcePosition) -> bool:
        if not isinstance(other, PostgresLSNPosition) or self.engine != other.engine:
            raise TypeError(f"Cannot compare PostgresLSNPosition with {type(other)}")
        return self.numeric_val > other.numeric_val


class OracleSCNPosition(CDCSourcePosition):
    """Oracle System Change Number (SCN) Source Position."""

    def __init__(self, scn: int, sequence_number: int = 0) -> None:
        super().__init__("ORACLE")
        if scn < 0:
            raise CDCPositionError(f"Invalid Oracle SCN: {scn}")
        self.scn = scn
        self.sequence_number = sequence_number

    def to_string(self) -> str:
        return f"SCN:{self.scn}#SEQ:{self.sequence_number}"

    def to_dict(self) -> Dict[str, Any]:
        return {"engine": self.engine, "scn": self.scn, "sequence_number": self.sequence_number}

    def is_after(self, other: CDCSourcePosition) -> bool:
        if not isinstance(other, OracleSCNPosition) or self.engine != other.engine:
            raise TypeError(f"Cannot compare OracleSCNPosition with {type(other)}")
        if self.scn == other.scn:
            return self.sequence_number > other.sequence_number
        return self.scn > other.scn


class MySQLGTIDPosition(CDCSourcePosition):
    """MySQL Binlog File + Offset and GTID Set Source Position."""

    def __init__(self, binlog_file: str, binlog_pos: int, gtid_set: Optional[str] = None) -> None:
        super().__init__("MYSQL")
        if binlog_pos < 0 or not binlog_file:
            raise CDCPositionError(f"Invalid MySQL binlog file or position: '{binlog_file}':{binlog_pos}")
        self.binlog_file = binlog_file
        self.binlog_pos = binlog_pos
        self.gtid_set = gtid_set

    def parse_gtid_set(self) -> Set[str]:
        """Parses multi-UUID range GTID set string into canonical discrete GTID tokens."""
        if not self.gtid_set:
            return set()
        tokens = set()
        for gtid_expr in self.gtid_set.split(","):
            gtid_expr = gtid_expr.strip()
            if not gtid_expr:
                continue
            if ":" in gtid_expr:
                uuid_val, seq_range = gtid_expr.split(":", 1)
                if "-" in seq_range:
                    start_seq, end_seq = map(int, seq_range.split("-"))
                    for s in range(start_seq, end_seq + 1):
                        tokens.add(f"{uuid_val.upper()}:{s}")
                else:
                    tokens.add(f"{uuid_val.upper()}:{seq_range}")
            else:
                tokens.add(gtid_expr.upper())
        return tokens

    def is_subset_of(self, other: "MySQLGTIDPosition") -> bool:
        """Evaluates whether self GTID set is a strict subset of other GTID set."""
        set_self = self.parse_gtid_set()
        set_other = other.parse_gtid_set()
        return set_self.issubset(set_other)

    def to_string(self) -> str:
        if self.gtid_set:
            return f"{self.gtid_set}@{self.binlog_file}:{self.binlog_pos}"
        return f"{self.binlog_file}:{self.binlog_pos}"

    def to_dict(self) -> Dict[str, Any]:
        return {"engine": self.engine, "binlog_file": self.binlog_file, "binlog_pos": self.binlog_pos, "gtid_set": self.gtid_set}

    def is_after(self, other: CDCSourcePosition) -> bool:
        if not isinstance(other, MySQLGTIDPosition) or self.engine != other.engine:
            raise TypeError(f"Cannot compare MySQLGTIDPosition with {type(other)}")
        if self.gtid_set and other.gtid_set:
            set_self = self.parse_gtid_set()
            set_other = other.parse_gtid_set()
            if set_self != set_other:
                return set_other.issubset(set_self) and len(set_self) > len(set_other)
        if self.binlog_file == other.binlog_file:
            return self.binlog_pos > other.binlog_pos
        return self.binlog_file > other.binlog_file


class MariaDBGTIDPosition(CDCSourcePosition):
    """MariaDB GTID (Domain-Server-Sequence) Source Position."""

    def __init__(self, domain_id: int, server_id: int, sequence_no: int, binlog_file: str = "mariadb-bin.000001", binlog_pos: int = 0) -> None:
        super().__init__("MARIADB")
        self.domain_id = domain_id
        self.server_id = server_id
        self.sequence_no = sequence_no
        self.binlog_file = binlog_file
        self.binlog_pos = binlog_pos

    def to_string(self) -> str:
        return f"{self.domain_id}-{self.server_id}-{self.sequence_no}@{self.binlog_file}:{self.binlog_pos}"

    def to_dict(self) -> Dict[str, Any]:
        return {"engine": self.engine, "domain_id": self.domain_id, "server_id": self.server_id, "sequence_no": self.sequence_no}

    def is_after(self, other: CDCSourcePosition) -> bool:
        if not isinstance(other, MariaDBGTIDPosition) or self.engine != other.engine:
            raise TypeError(f"Cannot compare MariaDBGTIDPosition with {type(other)}")
        return self.sequence_no > other.sequence_no


class MSSQLChangePosition(CDCSourcePosition):
    """SQL Server CDC LSN Position."""

    def __init__(self, lsn_hex: str, seqval_hex: Optional[str] = None) -> None:
        super().__init__("MSSQL")
        self.lsn_hex = lsn_hex.upper()
        self.seqval_hex = (seqval_hex or "00000000").upper()

    def to_string(self) -> str:
        return f"{self.lsn_hex}:{self.seqval_hex}"

    def to_dict(self) -> Dict[str, Any]:
        return {"engine": self.engine, "lsn_hex": self.lsn_hex, "seqval_hex": self.seqval_hex}

    def is_after(self, other: CDCSourcePosition) -> bool:
        if not isinstance(other, MSSQLChangePosition) or self.engine != other.engine:
            raise TypeError(f"Cannot compare MSSQLChangePosition with {type(other)}")
        if self.lsn_hex == other.lsn_hex:
            return self.seqval_hex > other.seqval_hex
        return self.lsn_hex > other.lsn_hex


class MongoDBOpLogPosition(CDCSourcePosition):
    """MongoDB OpLog Timestamp + Increment Position."""

    def __init__(self, timestamp_sec: int, inc: int) -> None:
        super().__init__("MONGODB")
        self.timestamp_sec = timestamp_sec
        self.inc = inc

    def to_string(self) -> str:
        return f"TS:{self.timestamp_sec}:{self.inc}"

    def to_dict(self) -> Dict[str, Any]:
        return {"engine": self.engine, "timestamp_sec": self.timestamp_sec, "inc": self.inc}

    def is_after(self, other: CDCSourcePosition) -> bool:
        if not isinstance(other, MongoDBOpLogPosition) or self.engine != other.engine:
            raise TypeError(f"Cannot compare MongoDBOpLogPosition with {type(other)}")
        if self.timestamp_sec == other.timestamp_sec:
            return self.inc > other.inc
        return self.timestamp_sec > other.timestamp_sec


class PollingWatermarkPosition(CDCSourcePosition):
    """Generic high-watermark position for TIMESTAMP_INCREMENTAL and MONOTONIC_KEY_INCREMENTAL polling."""

    def __init__(self, watermark_val: Any, polling_type: str = "TIMESTAMP") -> None:
        super().__init__(f"POLLING_{polling_type.upper()}")
        self.watermark_val = watermark_val
        self.polling_type = polling_type.upper()

    def to_string(self) -> str:
        return f"WM:{self.watermark_val}"

    def to_dict(self) -> Dict[str, Any]:
        return {"engine": self.engine, "watermark_val": self.watermark_val, "polling_type": self.polling_type}

    def is_after(self, other: CDCSourcePosition) -> bool:
        if not isinstance(other, PollingWatermarkPosition) or self.engine != other.engine:
            raise TypeError(f"Cannot compare PollingWatermarkPosition with {type(other)}")
        return self.watermark_val > other.watermark_val
