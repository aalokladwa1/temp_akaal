"""
Bounded Segmented Disk Spooler for Authority #5 — Durability (DUR-009).
"""

import datetime
import hashlib
import os
import struct
import tempfile
import uuid
import zlib
from dataclasses import dataclass
from typing import Dict, Any, Iterator, Optional
from akaalEngine.durability.models.errors import SpillCorruptError, PartialSegmentError, StorageQuotaExceededError
from akaalEngine.durability.integrity.quota import StorageQuotaMonitor


@dataclass(frozen=True)
class SpilledSegmentRef:
    """Immutable reference handle for a spilled binary segment file."""
    segment_id: str
    stream_id: str
    file_path: str
    payload_length: int
    crc32: int
    sha256: str
    created_at: str


class BoundedDiskSpooler:
    """
    Bounded-memory disk spooler writing binary payloads using a framed segment format:
    Header: Magic ("AKSP" 4B) | Version (2B) | Segment UUID Bytes (16B) | Payload Length (8B) | CRC32 (4B) | SHA-256 (32B)
    Body: Payload bytes
    """

    MAGIC_HEADER: bytes = b"AKSP"
    VERSION: int = 1
    HEADER_SIZE: int = 4 + 2 + 16 + 8 + 4 + 32  # 66 bytes

    def __init__(self, spool_dir: str, quota_monitor: Optional[StorageQuotaMonitor] = None) -> None:
        self.spool_dir = spool_dir
        self.quota_monitor = quota_monitor
        os.makedirs(self.spool_dir, exist_ok=True)
        self.cleanup_orphaned_tmp_files()

    def cleanup_orphaned_tmp_files(self) -> int:
        """Cleans up orphaned .tmp files left by interrupted process writes."""
        cleaned = 0
        if not os.path.exists(self.spool_dir):
            return 0
        for f in os.listdir(self.spool_dir):
            if f.endswith(".tmp"):
                fp = os.path.join(self.spool_dir, f)
                try:
                    os.remove(fp)
                    cleaned += 1
                except OSError:
                    pass
        return cleaned

    def spill_data(self, stream_id: str, payload: bytes) -> SpilledSegmentRef:
        """Spills binary payload to disk using atomic temp file rename and framing."""
        payload_len = len(payload)
        if self.quota_monitor:
            self.quota_monitor.validate_allocation(payload_len + self.HEADER_SIZE)

        segment_uuid = uuid.uuid4()
        segment_id = str(segment_uuid)
        crc32_val = zlib.crc32(payload) & 0xFFFFFFFF
        sha256_hex = hashlib.sha256(payload).hexdigest()
        sha256_bytes = bytes.fromhex(sha256_hex)

        header = struct.pack(
            ">4sH16sQI32s",
            self.MAGIC_HEADER,
            self.VERSION,
            segment_uuid.bytes,
            payload_len,
            crc32_val,
            sha256_bytes,
        )

        final_path = os.path.join(self.spool_dir, f"{segment_id}.spill")
        tmp_fd, tmp_path = tempfile.mkstemp(prefix="akaal_spool_", suffix=".tmp", dir=self.spool_dir)

        try:
            with os.fdopen(tmp_fd, "wb") as f:
                f.write(header)
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())

            os.replace(tmp_path, final_path)

            # Flush parent directory on POSIX to guarantee directory entry persistence
            if os.name == "posix":
                try:
                    dir_fd = os.open(self.spool_dir, os.O_RDONLY)
                    try:
                        os.fsync(dir_fd)
                    finally:
                        os.close(dir_fd)
                except OSError:
                    pass
        except Exception as e:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            raise e

        # Set restricted permissions on POSIX
        if os.name == "posix":
            try:
                os.chmod(final_path, 0o600)
            except OSError:
                pass

        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return SpilledSegmentRef(
            segment_id=segment_id,
            stream_id=stream_id,
            file_path=final_path,
            payload_length=payload_len,
            crc32=crc32_val,
            sha256=sha256_hex,
            created_at=created_at,
        )

    def stream_spilled_data(self, ref: SpilledSegmentRef, chunk_size: int = 65536) -> Iterator[bytes]:
        """
        Streams binary payload in bounded memory chunks while computing running CRC32 & SHA-256 checksums.
        Defect #6: Validates exact header version, segment UUID, expected total file size, and rejects appended trailing garbage.
        """
        if not os.path.exists(ref.file_path):
            raise SpillCorruptError(f"Spill segment file '{ref.file_path}' does not exist.")

        actual_file_size = os.path.getsize(ref.file_path)
        expected_file_size = self.HEADER_SIZE + ref.payload_length
        if actual_file_size != expected_file_size:
            raise SpillCorruptError(
                f"Spill file size mismatch or appended trailing garbage: expected {expected_file_size} bytes, got {actual_file_size} bytes."
            )

        with open(ref.file_path, "rb") as f:
            header_bytes = f.read(self.HEADER_SIZE)
            if len(header_bytes) < self.HEADER_SIZE:
                raise PartialSegmentError("Spill segment header truncated.")

            magic, version, seg_bytes, payload_len, crc32_val, sha256_bytes = struct.unpack(">4sH16sQI32s", header_bytes)
            if magic != self.MAGIC_HEADER:
                raise SpillCorruptError(f"Invalid magic header in spill segment '{ref.segment_id}'.")

            if version != self.VERSION:
                raise SpillCorruptError(f"Unsupported spill version {version} in segment '{ref.segment_id}'.")

            seg_uuid_str = str(uuid.UUID(bytes=seg_bytes))
            if seg_uuid_str != ref.segment_id:
                raise SpillCorruptError(f"Spill segment UUID mismatch: header specifies {seg_uuid_str}, ref specifies {ref.segment_id}.")

            if payload_len != ref.payload_length:
                raise PartialSegmentError(f"Spill payload length mismatch: header specifies {payload_len}, ref specifies {ref.payload_length}.")

            if crc32_val != ref.crc32 or sha256_bytes.hex() != ref.sha256:
                raise SpillCorruptError(f"Spill reference digest mismatch for segment '{ref.segment_id}'.")

            bytes_read = 0
            running_crc = 0
            sha256_hash = hashlib.sha256()

            while bytes_read < payload_len:
                to_read = min(chunk_size, payload_len - bytes_read)
                chunk = f.read(to_read)
                if not chunk:
                    raise PartialSegmentError(f"Spill payload truncated after {bytes_read} bytes.")
                bytes_read += len(chunk)
                running_crc = zlib.crc32(chunk, running_crc) & 0xFFFFFFFF
                sha256_hash.update(chunk)
                yield chunk

            if running_crc != crc32_val:
                raise SpillCorruptError(f"Payload CRC32 mismatch in spill segment '{ref.segment_id}'.")

            if sha256_hash.hexdigest() != sha256_bytes.hex():
                raise SpillCorruptError(f"Payload SHA-256 mismatch in spill segment '{ref.segment_id}'.")

    def read_spilled_data(self, ref: SpilledSegmentRef) -> bytes:
        """Reads complete binary payload from disk segment after stream verification."""
        chunks = list(self.stream_spilled_data(ref))
        return b"".join(chunks)

    def delete_spilled_segment(self, ref: SpilledSegmentRef) -> bool:
        """Deletes a spilled segment file."""
        if os.path.exists(ref.file_path):
            try:
                os.remove(ref.file_path)
                return True
            except OSError:
                return False
        return False
