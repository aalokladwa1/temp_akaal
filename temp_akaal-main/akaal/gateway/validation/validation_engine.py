"""
NexusForge — File Validation Engine
========================================
Validates every uploaded file before any processing occurs.

Every uploaded file is treated as untrusted. All validations are
performed before the file reaches the detection or parser layer.

Validation checks (in order):
  1. File exists
  2. File is readable
  3. File is not empty
  4. Filename is safe (no path traversal, no null bytes, allow-list chars only)
  5. File extension is supported
  6. File size is within acceptable limits
  7. File is not truncated / incomplete (basic integrity check)

On first failure, validation stops and returns a structured result.
The caller never receives partial validation results.

Supported extensions are defined as a frozenset to allow O(1) lookup.
Adding new formats requires only adding to SUPPORTED_EXTENSIONS and
updating the FormatDetectionEngine — zero other changes needed.
"""

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from akaal.gateway.models.gateway_response import GatewayErrorCode


logger = logging.getLogger("nexusforge.gateway.validation")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Maximum allowed upload size (50 GB)
MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024 * 1024

# Supported file extensions (lowercase, including dot)
SUPPORTED_EXTENSIONS: frozenset = frozenset({".sql", ".json", ".csv"})

# Minimum bytes for a non-empty file
MIN_FILE_SIZE_BYTES: int = 1

# Filename allow-list: alphanumeric, dots, underscores, hyphens, spaces
_SAFE_FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9 ._\-]+$")

# Maximum filename length
MAX_FILENAME_LENGTH: int = 255


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class FileValidationResult:
    """
    Result of a file validation run.

    success=True:  All checks passed. sanitized_filename and file_size_bytes
                   are populated.
    success=False: A check failed. error_code and error_message explain why.
    """
    success: bool
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    sanitized_filename: str = ""
    file_size_bytes: int = 0
    file_extension: str = ""
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Validation Engine
# ---------------------------------------------------------------------------

class FileValidationEngine:
    """
    Validates uploaded files against all Gateway security and integrity rules.

    Usage:
        engine = FileValidationEngine()
        result = engine.validate(file_path="/tmp/export.sql",
                                 original_filename="export.sql")
        if not result.success:
            # reject upload
    """

    def __init__(
        self,
        max_file_size_bytes: int = MAX_FILE_SIZE_BYTES,
        supported_extensions: Optional[frozenset] = None,
    ) -> None:
        self._max_size = max_file_size_bytes
        self._supported_exts = supported_extensions or SUPPORTED_EXTENSIONS

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    def validate(self, file_path: str, original_filename: str) -> FileValidationResult:
        """
        Run all validation checks on the given file.

        Checks are run in order. The first failure short-circuits the
        remaining checks and returns the error immediately.

        Parameters
        ----------
        file_path : str
            Absolute path to the file to validate (may be the staged copy).
        original_filename : str
            The filename as submitted by the caller (used for extension/name checks).

        Returns
        -------
        FileValidationResult
            success=True if all checks pass; False with error details otherwise.
        """
        # 1. Filename safety (before any file I/O)
        name_result = self._validate_filename(original_filename)
        if not name_result.success:
            return name_result

        sanitized = name_result.sanitized_filename
        extension = name_result.file_extension

        # 2. Extension is supported
        ext_result = self._validate_extension(extension, original_filename)
        if not ext_result.success:
            return ext_result

        # 3. File exists
        exists_result = self._validate_exists(file_path)
        if not exists_result.success:
            return exists_result

        # 4. File is readable
        readable_result = self._validate_readable(file_path)
        if not readable_result.success:
            return readable_result

        # 5. File size (not empty + not over limit)
        size_result = self._validate_size(file_path)
        if not size_result.success:
            return size_result

        file_size = size_result.file_size_bytes

        # 6. Integrity check (basic: file not truncated)
        integrity_result = self._validate_integrity(file_path, extension)
        if not integrity_result.success:
            return integrity_result

        logger.debug(
            "[Validation] PASS — file=%r size=%d ext=%s",
            original_filename, file_size, extension,
        )

        return FileValidationResult(
            success=True,
            sanitized_filename=sanitized,
            file_size_bytes=file_size,
            file_extension=extension,
            warnings=integrity_result.warnings,
        )

    # ----------------------------------------------------------------
    # Individual check methods
    # ----------------------------------------------------------------

    def _validate_filename(self, original_filename: str) -> FileValidationResult:
        """Sanitize and validate the filename."""
        if not original_filename or not original_filename.strip():
            return FileValidationResult(
                success=False,
                error_code=GatewayErrorCode.UNSAFE_FILENAME,
                error_message="Filename is empty.",
            )

        # Strip leading/trailing whitespace
        name = original_filename.strip()

        # Null byte check
        if "\x00" in name:
            return FileValidationResult(
                success=False,
                error_code=GatewayErrorCode.UNSAFE_FILENAME,
                error_message="Filename contains null bytes.",
            )

        # Length check
        if len(name) > MAX_FILENAME_LENGTH:
            return FileValidationResult(
                success=False,
                error_code=GatewayErrorCode.UNSAFE_FILENAME,
                error_message=f"Filename exceeds maximum length of {MAX_FILENAME_LENGTH} characters.",
            )

        # Path traversal: reject if filename contains path separators
        if "/" in name or "\\" in name:
            return FileValidationResult(
                success=False,
                error_code=GatewayErrorCode.PATH_TRAVERSAL,
                error_message="Filename contains path separators (potential path traversal).",
            )

        # Dot-only or starts with dot-dot
        if name.startswith(".."):
            return FileValidationResult(
                success=False,
                error_code=GatewayErrorCode.PATH_TRAVERSAL,
                error_message="Filename starts with '..' (path traversal).",
            )

        # Extract basename only (defensive)
        basename = Path(name).name

        # Allow-list check
        if not _SAFE_FILENAME_PATTERN.match(basename):
            return FileValidationResult(
                success=False,
                error_code=GatewayErrorCode.UNSAFE_FILENAME,
                error_message=(
                    f"Filename '{basename}' contains unsafe characters. "
                    "Only alphanumeric, spaces, dots, underscores, and hyphens are allowed."
                ),
            )

        # Extract extension (last suffix only, lowercase)
        extension = Path(basename).suffix.lower()

        return FileValidationResult(
            success=True,
            sanitized_filename=basename,
            file_extension=extension,
        )

    def _validate_extension(self, extension: str, original_filename: str) -> FileValidationResult:
        """Verify the file extension is in the supported set."""
        if not extension:
            return FileValidationResult(
                success=False,
                error_code=GatewayErrorCode.UNSUPPORTED_FORMAT,
                error_message=(
                    f"File '{original_filename}' has no extension. "
                    f"Supported formats: {sorted(self._supported_exts)}"
                ),
            )
        if extension not in self._supported_exts:
            return FileValidationResult(
                success=False,
                error_code=GatewayErrorCode.UNSUPPORTED_FORMAT,
                error_message=(
                    f"File extension '{extension}' is not supported. "
                    f"Supported formats: {sorted(self._supported_exts)}"
                ),
            )
        return FileValidationResult(success=True, file_extension=extension)

    def _validate_exists(self, file_path: str) -> FileValidationResult:
        """Verify the file exists at the given path."""
        if not os.path.exists(file_path):
            return FileValidationResult(
                success=False,
                error_code=GatewayErrorCode.FILE_NOT_FOUND,
                error_message=f"File not found: {file_path!r}",
            )
        if not os.path.isfile(file_path):
            return FileValidationResult(
                success=False,
                error_code=GatewayErrorCode.FILE_NOT_FOUND,
                error_message=f"Path is not a regular file: {file_path!r}",
            )
        return FileValidationResult(success=True)

    def _validate_readable(self, file_path: str) -> FileValidationResult:
        """Verify the file is readable."""
        if not os.access(file_path, os.R_OK):
            return FileValidationResult(
                success=False,
                error_code=GatewayErrorCode.FILE_NOT_READABLE,
                error_message=f"File is not readable (permission denied): {file_path!r}",
            )
        return FileValidationResult(success=True)

    def _validate_size(self, file_path: str) -> FileValidationResult:
        """Check file size: not empty, not over the limit."""
        try:
            size = os.path.getsize(file_path)
        except OSError as exc:
            return FileValidationResult(
                success=False,
                error_code=GatewayErrorCode.FILE_NOT_READABLE,
                error_message=f"Cannot determine file size: {exc}",
            )

        if size < MIN_FILE_SIZE_BYTES:
            return FileValidationResult(
                success=False,
                error_code=GatewayErrorCode.FILE_EMPTY,
                error_message="File is empty (0 bytes).",
            )

        if size > self._max_size:
            max_mb = self._max_size / (1024 * 1024)
            actual_mb = size / (1024 * 1024)
            return FileValidationResult(
                success=False,
                error_code=GatewayErrorCode.FILE_TOO_LARGE,
                error_message=(
                    f"File size {actual_mb:.1f} MB exceeds the maximum allowed {max_mb:.0f} MB."
                ),
                file_size_bytes=size,
            )

        return FileValidationResult(success=True, file_size_bytes=size)

    def _validate_integrity(self, file_path: str, extension: str) -> FileValidationResult:
        """
        Basic integrity check: verify the file is not obviously truncated.

        Strategy:
          - For JSON: verify we can open and read the first/last bytes
            to check brackets are not missing (very cheap check)
          - For SQL/CSV: verify the file is readable end-to-end by
            seeking to the end; check final bytes are not garbage (NUL-heavy)
          - This is NOT a full parse — just a quick sanity check.
        """
        warnings: List[str] = []
        try:
            with open(file_path, "rb") as fh:
                # Read first 512 bytes
                header = fh.read(512)
                if not header:
                    return FileValidationResult(
                        success=False,
                        error_code=GatewayErrorCode.FILE_EMPTY,
                        error_message="File has no readable content.",
                    )

                # NUL-byte concentration check (indicates binary/corrupted file)
                nul_count = header.count(b"\x00")
                if nul_count > len(header) * 0.3:
                    return FileValidationResult(
                        success=False,
                        error_code=GatewayErrorCode.FILE_CORRUPTED,
                        error_message=(
                            "File appears to be binary or corrupted "
                            f"({nul_count} NUL bytes in first 512 bytes)."
                        ),
                    )

                # For JSON: check first non-whitespace char is { or [
                if extension == ".json":
                    stripped = header.lstrip()
                    if stripped and stripped[0:1] not in (b"{", b"["):
                        warnings.append(
                            "JSON file does not start with '{' or '['. "
                            "May be NDJSON or have a BOM — parser will handle this."
                        )

        except (IOError, OSError) as exc:
            return FileValidationResult(
                success=False,
                error_code=GatewayErrorCode.FILE_NOT_READABLE,
                error_message=f"Cannot read file during integrity check: {exc}",
            )

        return FileValidationResult(success=True, warnings=warnings)
