"""
AKAAL Runtime V3 — LOB Stream Pipeline
======================================
High-performance chunked streaming for Oracle CLOB, NCLOB, BLOB, and Large Binary Objects with checkpoint offset tracking.
"""

import logging
from typing import Any, Dict, Generator, Optional

logger = logging.getLogger("akaal.streaming.lob")


class LOBStreamPipe:
    """Chunked streaming pipeline for Oracle LOB/CLOB/BLOB columns."""

    def __init__(self, chunk_size_bytes: int = 65536) -> None:
        self.chunk_size = chunk_size_bytes
        self.total_bytes_streamed = 0
        self.current_offset = 0

    def stream_lob_data(self, lob_content: Any, start_offset: int = 0) -> Generator[Dict[str, Any], None, None]:
        self.current_offset = start_offset

        if isinstance(lob_content, str):
            data_bytes = lob_content.encode("utf-8")
        elif isinstance(lob_content, (bytes, bytearray)):
            data_bytes = bytes(lob_content)
        else:
            data_bytes = str(lob_content).encode("utf-8")

        total_length = len(data_bytes)
        logger.info(f"[LOBPipe] Streaming LOB object ({total_length} bytes) starting at offset {start_offset} in {self.chunk_size}B chunks...")

        while self.current_offset < total_length:
            chunk = data_bytes[self.current_offset : self.current_offset + self.chunk_size]
            chunk_len = len(chunk)
            self.total_bytes_streamed += chunk_len
            self.current_offset += chunk_len

            yield {
                "offset": self.current_offset,
                "total_bytes": total_length,
                "chunk_bytes": chunk_len,
                "is_last_chunk": self.current_offset >= total_length,
                "data": chunk
            }
