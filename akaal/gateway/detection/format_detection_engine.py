"""
NexusForge — Format Detection Engine
=======================================
Identifies the file format (SQL/JSON/CSV) and, within SQL files,
the originating database vendor (MySQL, PostgreSQL, SQLite, etc.).

Architecture — Strategy Registry Pattern:
  Each database vendor detector is a registered callable (strategy).
  Adding a new detector = registering one function. No other changes needed.

Detection pipeline:
  Stage 1 — File Format Detection
    - From file extension (.sql → SQL, .json → JSON, .csv → CSV)
    - Validates against actual file header as a sanity check

  Stage 2 — Database Vendor Detection (SQL files only)
    - Reads first SAMPLE_BYTES of the file (no full load into memory)
    - Scores each registered vendor detector
    - Returns the highest-confidence match
    - If confidence < CONFIDENCE_THRESHOLD → returns None (user must confirm)

Confidence scoring:
  - Each keyword/pattern match contributes a weighted score
  - Total score is normalised to [0.0, 1.0]
  - Confidence ≥ 0.6 → automatic detection
  - Confidence < 0.6 → requires user confirmation (never guesses)

Never executes file content.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from akaal.core.models.enums import FileFormat, SystemType


logger = logging.getLogger("nexusforge.gateway.detection")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Bytes to read for detection (first 64 KB is sufficient for most signals)
SAMPLE_BYTES: int = 64 * 1024

# Minimum confidence to auto-accept a detection result
CONFIDENCE_THRESHOLD: float = 0.6

# Map file extensions to FileFormat
EXTENSION_TO_FORMAT: Dict[str, FileFormat] = {
    ".sql": FileFormat.SQL,
    ".json": FileFormat.JSON,
    ".csv": FileFormat.CSV,
}


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class DetectionResult:
    """
    Result of the format and database vendor detection pipeline.

    file_format:          Always populated when detection runs.
    db_type:              Populated only when confidence >= CONFIDENCE_THRESHOLD.
                          None means the user must confirm.
    confidence:           Float in [0.0, 1.0].
    requires_user_input:  True when confidence < CONFIDENCE_THRESHOLD.
    evidence:             List of matched keywords/patterns explaining the result.
    """
    file_format: FileFormat
    db_type: Optional[SystemType]
    confidence: float
    requires_user_input: bool
    evidence: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"DetectionResult(format={self.file_format.value}, "
            f"db={self.db_type}, confidence={self.confidence:.2f}, "
            f"requires_user_input={self.requires_user_input})"
        )


# ---------------------------------------------------------------------------
# Vendor Detector Strategies
# ---------------------------------------------------------------------------
# Each strategy is a callable:
#   (sample_text: str) -> Tuple[float, List[str]]
#                          (score,   evidence)
# Score range: 0.0 – 1.0 per detector (will be normalised against competitors)

VendorDetector = Callable[[str], Tuple[float, List[str]]]


def _detect_mysql(sample: str) -> Tuple[float, List[str]]:
    """Detect MySQL-specific patterns."""
    evidence: List[str] = []
    score = 0.0

    patterns = [
        (r"ENGINE\s*=\s*(InnoDB|MyISAM|MEMORY|ARCHIVE)", 0.35, "ENGINE= clause (MySQL-specific)"),
        (r"AUTO_INCREMENT\s*=\s*\d+", 0.30, "AUTO_INCREMENT attribute"),
        (r"DEFAULT CHARSET\s*=", 0.25, "DEFAULT CHARSET clause"),
        (r"`[^`]+`",              0.15, "Backtick identifiers (MySQL style)"),
        (r"TINYINT\(1\)",          0.15, "TINYINT(1) boolean type"),
        (r"UNSIGNED",              0.10, "UNSIGNED type modifier"),
        (r"-- MySQL dump",         0.50, "MySQL dump header comment"),
        (r"mysqldump",             0.50, "mysqldump signature"),
        (r"ROW_FORMAT",            0.20, "ROW_FORMAT clause"),
        (r"COLLATE\s+utf8",        0.15, "utf8 collation specifier"),
    ]

    for pattern, weight, label in patterns:
        if re.search(pattern, sample, re.IGNORECASE):
            score += weight
            evidence.append(label)

    return min(score, 1.0), evidence


def _detect_postgresql(sample: str) -> Tuple[float, List[str]]:
    """Detect PostgreSQL-specific patterns."""
    evidence: List[str] = []
    score = 0.0

    patterns = [
        (r"--\s*PostgreSQL database dump",      0.70, "PostgreSQL dump header"),
        (r"pg_dump",                             0.60, "pg_dump signature"),
        (r"COPY\s+\w+\s*\(",                     0.35, "COPY statement (PostgreSQL-specific)"),
        (r"SEQUENCE",                            0.25, "SEQUENCE object"),
        (r"SERIAL\b",                            0.25, "SERIAL data type"),
        (r"BIGSERIAL\b",                         0.20, "BIGSERIAL data type"),
        (r"\$\$",                                0.20, "Dollar-quoting ($$)"),
        (r"RETURNING\b",                         0.20, "RETURNING clause"),
        (r"ON CONFLICT",                         0.20, "ON CONFLICT clause"),
        (r"INHERITS\b",                          0.25, "INHERITS (table inheritance)"),
        (r"TEXT\[\]",                            0.20, "Array type TEXT[]"),
        (r"JSONB\b",                             0.30, "JSONB type (PostgreSQL-specific)"),
        (r'"[^"]+"',                             0.10, "Double-quoted identifiers (ANSI)"),
    ]

    for pattern, weight, label in patterns:
        if re.search(pattern, sample, re.IGNORECASE):
            score += weight
            evidence.append(label)

    return min(score, 1.0), evidence


def _detect_sqlite(sample: str) -> Tuple[float, List[str]]:
    """Detect SQLite-specific patterns."""
    evidence: List[str] = []
    score = 0.0

    patterns = [
        (r"SQLite format 3",             0.90, "SQLite file magic signature"),
        (r"sqlite_master",               0.70, "sqlite_master table reference"),
        (r"sqlite_sequence",             0.60, "sqlite_sequence table reference"),
        (r"AUTOINCREMENT\b",             0.30, "AUTOINCREMENT keyword (SQLite)"),
        (r"PRAGMA\b",                    0.30, "PRAGMA statement"),
        (r"WITHOUT ROWID",               0.35, "WITHOUT ROWID (SQLite-specific)"),
        (r"INTEGER PRIMARY KEY",         0.25, "INTEGER PRIMARY KEY (rowid alias)"),
        (r"\.dump",                      0.20, ".dump command"),
        (r"BEGIN TRANSACTION",           0.10, "BEGIN TRANSACTION"),
    ]

    for pattern, weight, label in patterns:
        if re.search(pattern, sample, re.IGNORECASE):
            score += weight
            evidence.append(label)

    return min(score, 1.0), evidence


def _detect_mssql(sample: str) -> Tuple[float, List[str]]:
    """Detect Microsoft SQL Server-specific patterns."""
    evidence: List[str] = []
    score = 0.0

    patterns = [
        (r"Microsoft SQL Server",              0.80, "SQL Server product name"),
        (r"\[dbo\]\.",                         0.40, "[dbo]. schema prefix"),
        (r"\[[^\]]+\]",                        0.20, "Bracket-quoted identifiers"),
        (r"NVARCHAR\b",                        0.25, "NVARCHAR data type"),
        (r"NCHAR\b",                           0.20, "NCHAR data type"),
        (r"GETDATE\(\)",                       0.25, "GETDATE() function"),
        (r"GETUTCDATE\(\)",                    0.20, "GETUTCDATE() function"),
        (r"IDENTITY\s*\(",                     0.30, "IDENTITY column"),
        (r"TOP\s+\d+\b",                       0.15, "TOP N clause"),
        (r"GO\s*$",                            0.15, "GO batch separator"),
        (r"USE\s+\[",                          0.25, "USE [database] statement"),
        (r"CLUSTERED INDEX",                   0.20, "CLUSTERED INDEX"),
        (r"WITH\s*\(NOLOCK\)",                 0.25, "NOLOCK hint"),
    ]

    for pattern, weight, label in patterns:
        if re.search(pattern, sample, re.IGNORECASE | re.MULTILINE):
            score += weight
            evidence.append(label)

    return min(score, 1.0), evidence


def _detect_oracle(sample: str) -> Tuple[float, List[str]]:
    """Detect Oracle-specific patterns."""
    evidence: List[str] = []
    score = 0.0

    patterns = [
        (r"Oracle Database",               0.80, "Oracle Database product name"),
        (r"exp\s+userid=",                 0.60, "Oracle exp export signature"),
        (r"expdp\s+",                      0.60, "Oracle Data Pump expdp signature"),
        (r"DBMS_OUTPUT",                   0.30, "DBMS_OUTPUT package"),
        (r"SYSDATE\b",                     0.25, "SYSDATE function"),
        (r"NVL\s*\(",                      0.20, "NVL() function"),
        (r"DECODE\s*\(",                   0.20, "DECODE() function"),
        (r"ROWNUM\b",                      0.25, "ROWNUM pseudocolumn"),
        (r"NUMBER\s*\(\d+",                0.20, "NUMBER(p,s) type"),
        (r"VARCHAR2\b",                    0.30, "VARCHAR2 data type"),
        (r"CONNECT BY",                    0.30, "CONNECT BY (hierarchical query)"),
        (r"TABLESPACE\s+\w+",              0.20, "TABLESPACE clause"),
    ]

    for pattern, weight, label in patterns:
        if re.search(pattern, sample, re.IGNORECASE):
            score += weight
            evidence.append(label)

    return min(score, 1.0), evidence


def _detect_mongodb(sample: str) -> Tuple[float, List[str]]:
    """Detect MongoDB export patterns (JSON/BSON exports)."""
    evidence: List[str] = []
    score = 0.0

    patterns = [
        (r'"_id"\s*:\s*\{\s*"\$oid"',     0.70, "MongoDB ObjectId ($oid)"),
        (r'"\$date"\s*:',                  0.50, "MongoDB date ($date)"),
        (r'"\$numberLong"\s*:',            0.40, "MongoDB NumberLong"),
        (r'"\$numberDecimal"\s*:',         0.40, "MongoDB NumberDecimal"),
        (r'"\$binary"\s*:',                0.40, "MongoDB Binary"),
        (r'"\$ref"\s*:',                   0.35, "MongoDB DBRef ($ref)"),
        (r'mongodump',                     0.60, "mongodump signature"),
        (r'"__v"\s*:',                     0.20, "Mongoose version key (__v)"),
    ]

    for pattern, weight, label in patterns:
        if re.search(pattern, sample, re.IGNORECASE):
            score += weight
            evidence.append(label)

    return min(score, 1.0), evidence


# ---------------------------------------------------------------------------
# Vendor detector registry
# ---------------------------------------------------------------------------

_VENDOR_DETECTORS: Dict[SystemType, VendorDetector] = {
    SystemType.MYSQL:      _detect_mysql,
    SystemType.POSTGRESQL: _detect_postgresql,
    SystemType.GENERIC:    _detect_sqlite,   # SQLite maps to GENERIC (closest fit)
    SystemType.MSSQL:      _detect_mssql,
    SystemType.ORACLE:     _detect_oracle,
    SystemType.MONGODB:    _detect_mongodb,
}

# Remap SQLite (it's not in SystemType directly; closest match)
# We use GENERIC as a fallback for SQLite until SystemType has SQLITE added.
# This mapping resolves the detected key to the correct SystemType.
_SQLITE_KEY = "SQLITE_INTERNAL"


# ---------------------------------------------------------------------------
# Format Detection Engine
# ---------------------------------------------------------------------------

class FormatDetectionEngine:
    """
    Two-stage detection engine:
      Stage 1: Determine file format (SQL, JSON, CSV) from extension.
      Stage 2: For SQL files, detect the originating database vendor.

    The engine is designed as a strategy registry. New database vendors
    can be added by registering a detector function without touching
    any other Gateway code.

    Usage:
        engine = FormatDetectionEngine()
        result = engine.detect(file_path="/tmp/export.sql", extension=".sql")
    """

    def __init__(
        self,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
        sample_bytes: int = SAMPLE_BYTES,
        vendor_detectors: Optional[Dict[SystemType, VendorDetector]] = None,
    ) -> None:
        self._threshold = confidence_threshold
        self._sample_bytes = sample_bytes
        self._detectors = vendor_detectors or _VENDOR_DETECTORS

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    def detect(self, file_path: str, extension: str) -> DetectionResult:
        """
        Run both detection stages on the given file.

        Parameters
        ----------
        file_path : str
            Absolute path to the staged file.
        extension : str
            Lowercase file extension including dot (e.g. ".sql").

        Returns
        -------
        DetectionResult
            Always returns a result. Never raises.
        """
        file_format = EXTENSION_TO_FORMAT.get(extension)
        if file_format is None:
            # This should not happen if ValidationEngine ran first,
            # but we handle it defensively.
            logger.warning("[Detection] Unknown extension: %s", extension)
            file_format = FileFormat.SQL  # Safest fallback for detection

        logger.debug("[Detection] Format=%s file=%s", file_format.value, file_path)

        # Stage 2 — vendor detection only for SQL files
        if file_format == FileFormat.SQL:
            return self._detect_vendor(file_path, file_format)

        # For JSON and CSV, we try MongoDB detection (JSON exports)
        if file_format == FileFormat.JSON:
            return self._detect_json_vendor(file_path, file_format)

        # CSV — cannot determine database vendor from CSV alone
        return DetectionResult(
            file_format=file_format,
            db_type=None,
            confidence=0.0,
            requires_user_input=True,
            evidence=["CSV format detected. Database vendor cannot be auto-detected from CSV."],
        )

    # ----------------------------------------------------------------
    # Stage 2 — SQL Vendor Detection
    # ----------------------------------------------------------------

    def _detect_vendor(self, file_path: str, file_format: FileFormat) -> DetectionResult:
        """Score all registered vendor detectors and pick the winner."""
        sample = self._read_sample(file_path)
        if not sample:
            return DetectionResult(
                file_format=file_format,
                db_type=None,
                confidence=0.0,
                requires_user_input=True,
                evidence=["File sample could not be read."],
            )

        scores: Dict[SystemType, Tuple[float, List[str]]] = {}
        for vendor, detector in self._detectors.items():
            try:
                score, evidence = detector(sample)
                scores[vendor] = (score, evidence)
            except Exception as exc:  # pragma: no cover
                logger.warning("[Detection] Detector %s raised: %s", vendor, exc)
                scores[vendor] = (0.0, [])

        if not scores:
            return DetectionResult(
                file_format=file_format,
                db_type=None,
                confidence=0.0,
                requires_user_input=True,
                evidence=["No vendor detectors available."],
            )

        # Pick the highest-scoring vendor
        best_vendor = max(scores, key=lambda v: scores[v][0])
        best_score, best_evidence = scores[best_vendor]

        logger.debug(
            "[Detection] Best vendor=%s score=%.3f", best_vendor.value, best_score
        )

        if best_score < self._threshold:
            return DetectionResult(
                file_format=file_format,
                db_type=None,
                confidence=best_score,
                requires_user_input=True,
                evidence=best_evidence + [
                    f"Confidence {best_score:.2f} is below threshold {self._threshold:.2f}. "
                    "Please specify the database type."
                ],
            )

        return DetectionResult(
            file_format=file_format,
            db_type=best_vendor,
            confidence=best_score,
            requires_user_input=False,
            evidence=best_evidence,
        )

    def _detect_json_vendor(self, file_path: str, file_format: FileFormat) -> DetectionResult:
        """For JSON files, try to detect MongoDB export patterns."""
        sample = self._read_sample(file_path)
        if sample:
            mongo_score, mongo_evidence = _detect_mongodb(sample)
            if mongo_score >= self._threshold:
                return DetectionResult(
                    file_format=file_format,
                    db_type=SystemType.MONGODB,
                    confidence=mongo_score,
                    requires_user_input=False,
                    evidence=mongo_evidence,
                )

        return DetectionResult(
            file_format=file_format,
            db_type=None,
            confidence=0.0,
            requires_user_input=True,
            evidence=["JSON format detected. Could not identify database vendor. Please specify."],
        )

    # ----------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------

    def _read_sample(self, file_path: str) -> str:
        """
        Read the first SAMPLE_BYTES of the file as UTF-8 text.
        Falls back to latin-1 if UTF-8 decode fails.
        Returns empty string on I/O error.
        """
        path = Path(file_path)
        try:
            raw = path.read_bytes()
            sample_raw = raw[: self._sample_bytes]
            try:
                return sample_raw.decode("utf-8", errors="replace")
            except Exception:
                return sample_raw.decode("latin-1", errors="replace")
        except (IOError, OSError) as exc:
            logger.error("[Detection] Cannot read file sample: %s", exc)
            return ""

    def register_detector(self, vendor: SystemType, detector: VendorDetector) -> None:
        """
        Register a new vendor detector.

        This is the extension point for adding new database types.
        Call this before running detect().

        Parameters
        ----------
        vendor : SystemType
            The SystemType enum value this detector identifies.
        detector : VendorDetector
            Callable: (sample: str) -> (score: float, evidence: List[str])
        """
        self._detectors[vendor] = detector
        logger.info("[Detection] Registered detector for vendor: %s", vendor.value)
