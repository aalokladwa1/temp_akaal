"""
NexusForge — Secure File Storage
===================================
Manages isolated, temporary staging of uploaded files.

Security guarantees:
  1. Every file is copied to an isolated staging directory.
     The original source path is never modified.
  2. Path traversal is prevented by resolving the full path
     and verifying it remains inside the staging root.
  3. Staged files are cleaned up after processing completes
     (success or failure).
  4. A malware_scan_hook callable slot is provided. It is
     a no-op by default. A real AV integration can be plugged in
     without changing the Gateway architecture.
  5. File contents are NEVER executed (no eval, exec, subprocess).

Design:
  Each staging session gets its own subdirectory:
    <staging_root>/<session_id>/<sanitized_filename>

  This isolates concurrent uploads from each other.
"""

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("nexusforge.gateway.storage")


# ---------------------------------------------------------------------------
# Malware scan hook type alias
# ---------------------------------------------------------------------------

# Signature: (file_path: str) -> None
# Raise an exception if the file is deemed unsafe.
MalwareScanHook = Callable[[str], None]


def _noop_malware_scan(file_path: str) -> None:
    """
    Default no-op malware scan hook.

    Replace this with a real AV/sandboxed scan integration.
    The hook must raise an exception if the file is unsafe.
    Returning normally means the file is safe to proceed.
    """
    logger.debug("[Storage] Malware scan hook invoked (no-op) for: %s", file_path)


# ---------------------------------------------------------------------------
# SecureFileStorage
# ---------------------------------------------------------------------------

class StorageError(Exception):
    """Raised when a file storage operation fails."""


class PathTraversalError(StorageError):
    """Raised when a path traversal attempt is detected."""


class SecureFileStorage:
    """
    Manages isolated temporary staging for uploaded files.

    Lifecycle:
        staged_path = storage.stage(session_id, source_path, filename)
        # ... process file at staged_path ...
        storage.release(session_id)   # always call in finally block

    Thread-safety:
        Each session gets its own subdirectory so concurrent uploads
        do not interfere with each other.
    """

    def __init__(
        self,
        staging_root: Optional[str] = None,
        malware_scan_hook: MalwareScanHook = _noop_malware_scan,
    ) -> None:
        """
        Parameters
        ----------
        staging_root : str, optional
            Root directory for all staged files.
            Defaults to a temporary directory created by tempfile.mkdtemp().
            The directory is created if it does not exist.
        malware_scan_hook : callable, optional
            Called on every staged file before it is handed to the parser.
            Must raise an exception if the file is unsafe.
        """
        if staging_root:
            self._staging_root = Path(staging_root).resolve()
            self._staging_root.mkdir(parents=True, exist_ok=True)
            self._owns_staging_root = False
        else:
            self._staging_root = Path(tempfile.mkdtemp(prefix="nexusforge_gateway_"))
            self._owns_staging_root = True

        self._malware_scan = malware_scan_hook

        logger.info("[Storage] Staging root: %s", self._staging_root)

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    def stage(self, session_id: str, source_path: str, sanitized_filename: str) -> str:
        """
        Copy the source file into an isolated staging directory.

        Parameters
        ----------
        session_id : str
            Unique session identifier — used as the staging subdirectory name.
        source_path : str
            Absolute path to the file to stage.
        sanitized_filename : str
            The sanitized filename to use inside the staging directory.
            Must already be sanitized by the caller.

        Returns
        -------
        str
            Absolute path to the staged file copy.

        Raises
        ------
        StorageError
            If the source file does not exist or cannot be read.
        PathTraversalError
            If the computed destination escapes the staging root.
        StorageError
            If the copy operation fails.
        """
        source = Path(source_path).resolve()

        # Guard: source must exist and be a file
        if not source.exists():
            raise StorageError(f"Source file does not exist: {source_path!r}")
        if not source.is_file():
            raise StorageError(f"Source path is not a file: {source_path!r}")

        # Build destination
        session_dir = self._staging_root / session_id
        destination = (session_dir / sanitized_filename).resolve()

        # Guard: path traversal prevention
        self._assert_within_staging_root(destination)

        # Create session directory
        try:
            session_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StorageError(f"Failed to create staging directory: {exc}") from exc

        # Copy file (preserves metadata)
        try:
            shutil.copy2(str(source), str(destination))
        except (IOError, OSError, shutil.Error) as exc:
            raise StorageError(f"Failed to copy file to staging: {exc}") from exc

        staged_path = str(destination)
        logger.debug("[Storage] Staged: %s → %s", source_path, staged_path)

        # Run malware scan on the staged copy
        try:
            self._malware_scan(staged_path)
        except Exception as exc:
            # Scan failed — remove the staged file and propagate
            self._safe_remove_file(staged_path)
            raise StorageError(f"Malware scan rejected file: {exc}") from exc

        return staged_path

    def release(self, session_id: str) -> None:
        """
        Remove all staged files for a session.

        Safe to call even if the session directory does not exist.
        Always call this in a finally block to ensure cleanup.

        Parameters
        ----------
        session_id : str
            The session whose staged files should be deleted.
        """
        session_dir = self._staging_root / session_id
        if session_dir.exists():
            try:
                shutil.rmtree(str(session_dir), ignore_errors=True)
                logger.debug("[Storage] Released staging dir for session: %s", session_id)
            except Exception as exc:  # pragma: no cover
                logger.warning("[Storage] Failed to release staging dir: %s", exc)

    def cleanup(self) -> None:
        """
        Remove the entire staging root.
        Only call on full shutdown if the storage owns its staging root.
        """
        if self._owns_staging_root and self._staging_root.exists():
            try:
                shutil.rmtree(str(self._staging_root), ignore_errors=True)
                logger.info("[Storage] Staging root cleaned up: %s", self._staging_root)
            except Exception as exc:  # pragma: no cover
                logger.warning("[Storage] Failed to clean up staging root: %s", exc)

    # ----------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------

    def _assert_within_staging_root(self, path: Path) -> None:
        """
        Verify that a resolved path is inside the staging root.
        Raises PathTraversalError if it is not.
        """
        try:
            path.relative_to(self._staging_root)
        except ValueError:
            raise PathTraversalError(
                f"Path traversal detected! Resolved path '{path}' "
                f"escapes staging root '{self._staging_root}'."
            )

    @staticmethod
    def _safe_remove_file(path: str) -> None:
        """Delete a single file, ignoring errors."""
        try:
            os.remove(path)
        except OSError:
            pass

    @property
    def staging_root(self) -> str:
        """Return the absolute path to the staging root."""
        return str(self._staging_root)
