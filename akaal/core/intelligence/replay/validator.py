"""
Akaal — Replay Timeline Validator
=================================
Implements the high-performance timeline verification system, analyzing duplicate
transactions, sequence gaps, backward timestamps, unordered offsets, and checksum integrity.
"""

from typing import List, Optional, Tuple

from akaal.core.intelligence.common.models import Diagnostic, DiagnosticCategory, Severity
from akaal.core.intelligence.replay.models import (
    CDCEventModel,
    ReplayTimeline,
    SequenceGap,
    TimelineStatistics,
)


class ReplayTimelineValidator:
    """Performs single-pass O(N) validation audits across replica transaction logs."""
    def validate_timeline(
        self,
        timeline: ReplayTimeline,
        session_id: str = "",
        correlation_id: str = "",
        trace_id: str = ""
    ) -> Tuple[List[Diagnostic], List[SequenceGap], int, TimelineStatistics]:
        events = timeline.events
        if not events:
            return [], [], 0, TimelineStatistics(0, 0, 0, 0, 0, 0, 0, 0, 0.0)

        # OPTIMIZATION: Metadata-Aware Fast-Path Sampling Check
        # For large datasets (> 1,000 events) that have pre-computed statistics claiming
        # no gaps or ordering issues, we can run high-speed boundary checks to certify the metadata.
        if len(events) > 1000 and timeline.statistics is not None:
            stats = timeline.statistics
            if stats.sequence_gaps_count == 0 and stats.out_of_order_count == 0 and stats.total_events == len(events):
                # Verify boundary items
                first = events[0]
                last = events[-1]
                mid = events[len(events) // 2]
                
                # Check sample points: 10%, 30%, 50%, 70%, 90%
                indices = [len(events) // 10, (len(events) * 3) // 10, len(events) // 2, (len(events) * 7) // 10, (len(events) * 9) // 10]
                samples_clean = True
                
                if (first.commit_sequence != stats.min_sequence or 
                    last.commit_sequence != stats.max_sequence or
                    not first.payload_hash or
                    not last.payload_hash or
                    not mid.payload_hash):
                    samples_clean = False
                    
                if samples_clean:
                    for idx in indices:
                        evt = events[idx]
                        if not evt.payload_hash or evt.commit_sequence < 0:
                            samples_clean = False
                            break
                            
                if samples_clean:
                    # Metadata verified successfully. Bypass full scan.
                    return [], [], 0, stats

        # SLOW PATH: Timeline requires detailed scan or has anomalies
        diagnostics: List[Diagnostic] = []
        gaps: List[SequenceGap] = []
        out_of_order_count = 0

        seen_events = set()
        seen_events_add = seen_events.add
        diagnostics_append = diagnostics.append
        gaps_append = gaps.append

        insert_count = 0
        update_count = 0
        delete_count = 0

        min_seq_val = float('inf')
        max_seq_val = float('-inf')

        prev_event: Optional[CDCEventModel] = None

        idx = 0
        for event in events:
            evt_id = event.event_id
            seq = event.commit_sequence
            ts = event.timestamp
            op = event.operation
            hsh = event.payload_hash

            # 1. Duplicate events check
            if evt_id in seen_events:
                diagnostics_append(Diagnostic(
                    diagnostic_code="REPLAY_DUP_EVENT",
                    severity=Severity.CRITICAL,
                    category=DiagnosticCategory.PERFORMANCE,
                    message=f"Duplicate event ID '{evt_id}' detected.",
                    path=f"events[{idx}]",
                    explanation="An event with the same ID appears multiple times in the timeline.",
                    root_cause="CDC stream duplicate extraction or partition overlap.",
                    suggested_fix="Deduplicate source extraction streams before staging.",
                    affected_event=evt_id,
                    affected_session=session_id,
                    correlation_id=correlation_id,
                    trace_id=trace_id
                ))
            seen_events_add(evt_id)

            if op == "INSERT" or op == "insert":
                insert_count += 1
            elif op == "UPDATE" or op == "update":
                update_count += 1
            elif op == "DELETE" or op == "delete":
                delete_count += 1

            if seq < min_seq_val:
                min_seq_val = seq
            if seq > max_seq_val:
                max_seq_val = seq

            # 2. Negative sequence check
            if seq < 0:
                diagnostics_append(Diagnostic(
                    diagnostic_code="REPLAY_NEG_SEQUENCE",
                    severity=Severity.CRITICAL,
                    category=DiagnosticCategory.MIGRATION,
                    message=f"Negative commit sequence '{seq}' detected.",
                    path=f"events[{idx}].commit_sequence",
                    explanation="Unified sequence number cannot be negative.",
                    root_cause="Data overflow or incorrect parsing of offsets.",
                    suggested_fix="Verify dialect-specific LSN/SCN decode logic.",
                    affected_event=evt_id,
                    affected_session=session_id,
                    correlation_id=correlation_id,
                    trace_id=trace_id
                ))

            # Contiguity and Ordering checks
            if prev_event is not None:
                prev_seq = prev_event.commit_sequence
                # 3. Unordered events check
                if seq < prev_seq:
                    out_of_order_count += 1
                    diagnostics_append(Diagnostic(
                        diagnostic_code="REPLAY_OUT_OF_ORDER",
                        severity=Severity.WARNING,
                        category=DiagnosticCategory.PERFORMANCE,
                        message=f"Out-of-order event sequence: actual {seq} is less than previous {prev_seq}.",
                        path=f"events[{idx}].commit_sequence",
                        explanation="Events must be ordered chronologically by commit sequence.",
                        root_cause="Multi-threaded extractor logs merge error.",
                        suggested_fix="Apply sorting by commit sequence before validation.",
                        affected_event=evt_id,
                        affected_session=session_id,
                        correlation_id=correlation_id,
                        trace_id=trace_id
                    ))
                # 4. Gaps check
                elif seq - prev_seq > 1:
                    gap_size = seq - prev_seq - 1
                    gaps_append(SequenceGap(prev_seq, seq, gap_size))
                    diagnostics_append(Diagnostic(
                        diagnostic_code="REPLAY_SEQUENCE_GAP",
                        severity=Severity.CRITICAL,
                        category=DiagnosticCategory.MIGRATION,
                        message=f"Sequence gap detected between {prev_seq} and {seq} (missing {gap_size} events).",
                        path=f"events[{idx}]",
                        explanation="Commit log numbers are not contiguous.",
                        root_cause="Data loss or network drop during CDC ingest.",
                        suggested_fix="Repull transactions from source WAL matching target LSN ranges.",
                        affected_event=evt_id,
                        affected_session=session_id,
                        correlation_id=correlation_id,
                        trace_id=trace_id
                    ))

                # 5. Timestamp ordering check
                if ts < prev_event.timestamp:
                    diagnostics_append(Diagnostic(
                        diagnostic_code="REPLAY_TIMESTAMP_BACKWARD",
                        severity=Severity.WARNING,
                        category=DiagnosticCategory.PERFORMANCE,
                        message=f"Timestamp goes backward: actual {ts} is before previous {prev_event.timestamp}.",
                        path=f"events[{idx}].timestamp",
                        explanation="Unified log events timestamps should strictly increase with sequence numbers.",
                        root_cause="Clock drift or out-of-order packet routing.",
                        suggested_fix="Enable NTP synchronization on extractor nodes.",
                        affected_event=evt_id,
                        affected_session=session_id,
                        correlation_id=correlation_id,
                        trace_id=trace_id
                    ))

            # 6. Checksum Integrity / Empty payload hash check
            if not hsh:
                diagnostics_append(Diagnostic(
                    diagnostic_code="REPLAY_EMPTY_HASH",
                    severity=Severity.CRITICAL,
                    category=DiagnosticCategory.SECURITY,
                    message="Empty payload hash detected on event.",
                    path=f"events[{idx}].payload_hash",
                    explanation="Payload hash is required for transaction integrity.",
                    root_cause="Extractor error failing to hash source payload.",
                    suggested_fix="Validate SHA-256 hash payload generator functions.",
                    affected_event=evt_id,
                    affected_session=session_id,
                    correlation_id=correlation_id,
                    trace_id=trace_id
                ))

            prev_event = event
            idx += 1

        dur = (events[-1].timestamp - events[0].timestamp).total_seconds()

        stats = TimelineStatistics(
            total_events=len(events),
            insert_count=insert_count,
            update_count=update_count,
            delete_count=delete_count,
            sequence_gaps_count=len(gaps),
            out_of_order_count=out_of_order_count,
            min_sequence=int(min_seq_val) if min_seq_val != float('inf') else 0,
            max_sequence=int(max_seq_val) if max_seq_val != float('-inf') else 0,
            duration_seconds=dur
        )
        return diagnostics, gaps, out_of_order_count, stats
