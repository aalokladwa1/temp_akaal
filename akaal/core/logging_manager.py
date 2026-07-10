"""
Akaal — Centralized Logging Manager
====================================
Coordinates logging formatting (JSON/Text), root handlers configuration,
and context propagation via contextvars.
"""

import contextlib
import contextvars
import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, Generator, Optional

# ContextVar holding the current migration context dict
_migration_context: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    "migration_context", default={}
)

def get_current_context() -> Dict[str, Any]:
    """Retrieve the active migration context dictionary."""
    return _migration_context.get()

def set_migration_context(**kwargs: Any) -> contextvars.Token[Dict[str, Any]]:
    """
    Update the active migration context with new fields.
    Returns a Token that can be used to reset the context to its previous state.
    """
    ctx = _migration_context.get().copy()
    ctx.update({k: v for k, v in kwargs.items() if v is not None})
    return _migration_context.set(ctx)

def reset_migration_context(token: contextvars.Token[Dict[str, Any]]) -> None:
    """Reset the migration context using a previously returned Token."""
    _migration_context.reset(token)

@contextlib.contextmanager
def migration_context(**kwargs: Any) -> Generator[None, None, None]:
    """
    Context manager to temporarily scope migration context variables.
    Works seamlessly across asyncio tasks and threads.
    """
    token = set_migration_context(**kwargs)
    try:
        yield
    finally:
        reset_migration_context(token)

# Reserved LogRecord attributes that should not be dynamically merged as dynamic "extra" fields
RESERVED_FIELDS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "asctime"
}

class StructuredFormatter(logging.Formatter):
    """
    Formatter supporting:
    - log_format="json": Outputting sorted, JSON-serialized log records.
    - log_format="text": Outputting standard human-readable text.
    """
    def __init__(self, log_format: str = "text") -> None:
        super().__init__()
        self.log_format = log_format

    def format(self, record: logging.LogRecord) -> str:
        # Base exception formatting
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)

        if self.log_format == "json":
            # Formulate structured JSON dictionary
            log_data: Dict[str, Any] = {
                "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat().replace("+00:00", "Z"),
                "log_level": record.levelname,
                "component": record.name,
                "message": record.getMessage(),
            }

            # 1. Merge active context values from contextvars
            current_ctx = get_current_context()
            for k, v in current_ctx.items():
                if v is not None:
                    log_data[k] = v

            # 2. Dynamically merge any non-reserved attributes passed via extra={...}
            for k, v in record.__dict__.items():
                if k not in RESERVED_FIELDS and v is not None:
                    log_data[k] = v

            # 3. Append exception details if present
            if record.exc_text:
                log_data["exception"] = record.exc_text

            return json.dumps(log_data, sort_keys=True)
        else:
            # Fallback to plain human-readable formatting
            # Format: [timestamp] [level] [logger_name] message
            asctime = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
            log_line = f"[{asctime}] [{record.levelname}] [{record.name}] {record.getMessage()}"
            if record.exc_text:
                log_line += "\n" + record.exc_text
            return log_line

# Keep track of active handlers we configured on the root logger so we can clear/rotate them cleanly
_active_handlers = []

def configure_logging(
    log_format: str = "text",
    log_level: str = "INFO",
    log_to_console: bool = True,
    log_to_file: bool = True,
    log_directory: str = "logs",
    log_file_name: str = "akaal.log",
    log_rotation_size_mb: int = 10,
    log_backup_count: int = 5,
    project_name: Optional[str] = None
) -> None:
    """
    Configure root logger handlers and levels based on setup configs.
    Cleans up any previously registered handlers to avoid duplicate output.
    """
    global _active_handlers

    root_logger = logging.getLogger()
    
    # Safely clear only handlers that were previously added by us
    for h in list(root_logger.handlers):
        if h in _active_handlers:
            root_logger.removeHandler(h)
            h.close()
    _active_handlers.clear()

    # Determine numeric log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Adjust levels for specific parent namespaces so that they obey root config
    for ns in ["akaal", "nexusforge"]:
        logging.getLogger(ns).setLevel(numeric_level)

    # Instantiate formatter
    formatter = StructuredFormatter(log_format=log_format)

    # Pre-populate project name if provided
    if project_name:
        set_migration_context(project_name=project_name)

    # Console Handler
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(numeric_level)
        root_logger.addHandler(console_handler)
        _active_handlers.append(console_handler)

    # File Handler
    if log_to_file:
        os.makedirs(log_directory, exist_ok=True)
        file_path = os.path.join(log_directory, log_file_name)
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=log_rotation_size_mb * 1024 * 1024,
            backupCount=log_backup_count,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(numeric_level)
        root_logger.addHandler(file_handler)
        _active_handlers.append(file_handler)
