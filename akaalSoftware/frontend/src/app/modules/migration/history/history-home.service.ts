import { Injectable, signal, computed, inject, Optional } from '@angular/core';
import {
  MigrationHistoryItem,
  HistoryFilterState,
  HistoryAvailabilityState,
  HistoryMode,
  HistoryOutcome,
  ValidationReconciliationState,
  HistorySortOption,
  HistoryDateRangeOption,
  HISTORY_MODE_DESCRIPTORS
} from './history-home.models';
import { INITIAL_MIGRATION_HISTORY_FIXTURES } from './history-home.fixtures';
import { CustomSelectOption } from '../../../shared/components/custom-select.component';
import { MigrationIpc } from '../../../core/services/ipc/migration.ipc';
import { IpcService } from '../../../core/services/ipc.service';
import { ContextService } from '../../../core/services/context.service';

@Injectable({
  providedIn: 'root'
})
export class HistoryHomeService {
  private migrationIpc?: MigrationIpc;
  private ipc?: IpcService;

  public historyItems = signal<MigrationHistoryItem[]>(INITIAL_MIGRATION_HISTORY_FIXTURES);

  public filters = signal<HistoryFilterState>({
    searchQuery: '',
    project: 'ALL',
    mode: 'ALL',
    outcome: 'ALL',
    validationState: 'ALL',
    evidence: 'ALL',
    continuity: 'ALL',
    dateRange: 'ALL',
    startDate: '',
    endDate: '',
    sortBy: 'completed_desc'
  });

  public availabilityState = signal<HistoryAvailabilityState>('READY');
  public errorMessage = signal<string>('');

  private unsubs: Array<() => void> = [];

  public cs?: ContextService;

  constructor(
    @Optional() migrationIpc?: MigrationIpc,
    @Optional() ipc?: IpcService,
    @Optional() contextService?: ContextService
  ) {
    if (ipc) {
      this.ipc = ipc;
    } else {
      try { this.ipc = inject(IpcService, { optional: true }) || undefined; } catch { this.ipc = undefined; }
    }
    if (migrationIpc) {
      this.migrationIpc = migrationIpc;
    } else {
      try { this.migrationIpc = inject(MigrationIpc, { optional: true }) || (this.ipc ? new MigrationIpc(this.ipc) : undefined); } catch { this.migrationIpc = undefined; }
    }
    try {
      this.cs = contextService || inject(ContextService, { optional: true }) || undefined;
    } catch {
      this.cs = contextService;
    }

    this.setupSubscriptions();
    if (this.cs) {
      this.cs.onContextChange(() => {
        this.loadState();
      });
    }
    this.loadState();
  }

  /**
   * Computed active filter indicator
   */
  public isFiltered = computed<boolean>(() => {
    const f = this.filters();
    return (
      !!f.searchQuery.trim() ||
      f.project !== 'ALL' ||
      f.mode !== 'ALL' ||
      f.outcome !== 'ALL' ||
      f.validationState !== 'ALL' ||
      f.evidence !== 'ALL' ||
      f.continuity !== 'ALL' ||
      f.dateRange !== 'ALL'
    );
  });

  /**
   * Active filter count badge
   */
  public activeFilterCount = computed<number>(() => {
    let count = 0;
    const f = this.filters();
    if (f.searchQuery.trim()) count++;
    if (f.project !== 'ALL') count++;
    if (f.mode !== 'ALL') count++;
    if (f.outcome !== 'ALL') count++;
    if (f.validationState !== 'ALL') count++;
    if (f.evidence !== 'ALL') count++;
    if (f.continuity !== 'ALL') count++;
    if (f.dateRange !== 'ALL') count++;
    return count;
  });

  /**
   * Filtered and sorted historical ledger items
   */
  public filteredHistoryItems = computed<MigrationHistoryItem[]>(() => {
    const all = this.historyItems();
    const f = this.filters();
    const q = f.searchQuery.trim().toLowerCase();

    let list = all.filter(item => {
      // 1. Text search across migration name, ID, execution ID, project, source/target providers, operator
      if (q) {
        const modeDesc = HISTORY_MODE_DESCRIPTORS[item.mode];
        const matchName = item.migrationName.toLowerCase().includes(q);
        const matchMigId = item.migrationId.toLowerCase().includes(q);
        const matchExecId = item.executionId.toLowerCase().includes(q);
        const matchProj = item.projectName.toLowerCase().includes(q);
        const matchSource = item.sourceProvider.toLowerCase().includes(q);
        const matchTarget = item.targetProvider.toLowerCase().includes(q);
        const matchOperator = item.operator.toLowerCase().includes(q);
        const matchMode = modeDesc ? (modeDesc.label.toLowerCase().includes(q) || modeDesc.shortCode.toLowerCase().includes(q)) : false;

        if (
          !matchName &&
          !matchMigId &&
          !matchExecId &&
          !matchProj &&
          !matchSource &&
          !matchTarget &&
          !matchOperator &&
          !matchMode
        ) {
          return false;
        }
      }

      // 2. Project filter
      if (f.project !== 'ALL' && item.projectId !== f.project) {
        return false;
      }

      // 3. Mode filter (M1 through M8 all 8 modes supported!)
      if (f.mode !== 'ALL' && item.mode !== f.mode) {
        return false;
      }

      // 4. Outcome filter
      if (f.outcome !== 'ALL' && item.outcome !== f.outcome) {
        return false;
      }

      // 5. Validation State filter
      if (f.validationState !== 'ALL' && item.validationState !== f.validationState) {
        return false;
      }

      // 6. Evidence Filter
      if (f.evidence !== 'ALL') {
        if (f.evidence === 'SEALED' && item.evidenceAvailability !== 'SEALED') return false;
        if (f.evidence === 'AVAILABLE' && item.evidenceAvailability !== 'AVAILABLE' && item.evidenceAvailability !== 'SEALED') return false;
        if (f.evidence === 'SHA256_VERIFIED' && item.evidenceIntegrity !== 'SHA256_VERIFIED') return false;
        if (f.evidence === 'UNVERIFIED' && item.evidenceIntegrity !== 'UNVERIFIED') return false;
        if (f.evidence === 'ALERT' && item.evidenceIntegrity !== 'HASH_MISMATCH' && item.evidenceAvailability !== 'CORRUPTED') return false;
      }

      // 7. Continuity / Cutover Filter
      if (f.continuity !== 'ALL') {
        if (f.continuity === 'CUTOVER_COMPLETED' && item.continuity.cutoverStatus !== 'COMPLETED') return false;
        if (f.continuity === 'ROLLED_BACK' && item.continuity.cutoverStatus !== 'ROLLED_BACK') return false;
        if (f.continuity === 'IN_PROGRESS' && item.continuity.cutoverStatus !== 'IN_PROGRESS') return false;
      }

      // 8. Date Range Filter
      if (f.dateRange !== 'ALL') {
        const itemDateStr = item.startedAt || item.completedAt;
        if (itemDateStr) {
          const itemTime = new Date(itemDateStr).getTime();
          const now = Date.now();
          if (f.dateRange === 'TODAY') {
            const todayStart = new Date();
            todayStart.setHours(0, 0, 0, 0);
            if (itemTime < todayStart.getTime()) return false;
          } else if (f.dateRange === 'LAST_7_DAYS') {
            if (itemTime < now - 7 * 24 * 60 * 60 * 1000) return false;
          } else if (f.dateRange === 'LAST_30_DAYS') {
            if (itemTime < now - 30 * 24 * 60 * 60 * 1000) return false;
          } else if (f.dateRange === 'CUSTOM') {
            if (f.startDate) {
              const startT = new Date(f.startDate).getTime();
              if (itemTime < startT) return false;
            }
            if (f.endDate) {
              const endT = new Date(f.endDate);
              endT.setHours(23, 59, 59, 999);
              if (itemTime > endT.getTime()) return false;
            }
          }
        }
      }

      return true;
    });

    // 8. Sorting
    list = [...list].sort((a, b) => {
      switch (f.sortBy) {
        case 'completed_desc': {
          const aTime = a.completedAt ? new Date(a.completedAt).getTime() : new Date(a.startedAt).getTime();
          const bTime = b.completedAt ? new Date(b.completedAt).getTime() : new Date(b.startedAt).getTime();
          return bTime - aTime;
        }
        case 'completed_asc': {
          const aTime = a.completedAt ? new Date(a.completedAt).getTime() : new Date(a.startedAt).getTime();
          const bTime = b.completedAt ? new Date(b.completedAt).getTime() : new Date(b.startedAt).getTime();
          return aTime - bTime;
        }
        case 'name_asc':
          return a.migrationName.localeCompare(b.migrationName);
        case 'name_desc':
          return b.migrationName.localeCompare(a.migrationName);
        case 'duration_desc':
          return b.rowsProcessed - a.rowsProcessed; // Fallback or row sorting
        case 'discrepancies_desc':
          return b.validationDiscrepancyCount - a.validationDiscrepancyCount;
        case 'rows_desc':
          return b.rowsProcessed - a.rowsProcessed;
        default:
          return 0;
      }
    });

    return list;
  });

  /**
   * Mode options for GDS select dropdown (M1 through M8)
   */
  public modeOptions: CustomSelectOption[] = [
    { label: 'All Modes (M1–M8)', value: 'ALL' },
    { label: HISTORY_MODE_DESCRIPTORS.M1_BULK.label, value: 'M1_BULK' },
    { label: HISTORY_MODE_DESCRIPTORS.M2_BULK_CDC.label, value: 'M2_BULK_CDC' },
    { label: HISTORY_MODE_DESCRIPTORS.M3_CDC.label, value: 'M3_CDC' },
    { label: HISTORY_MODE_DESCRIPTORS.M4_INCREMENTAL.label, value: 'M4_INCREMENTAL' },
    { label: HISTORY_MODE_DESCRIPTORS.M5_STATE_SYNC.label, value: 'M5_STATE_SYNC' },
    { label: HISTORY_MODE_DESCRIPTORS.M6_SCHEMA_ONLY.label, value: 'M6_SCHEMA_ONLY' },
    { label: HISTORY_MODE_DESCRIPTORS.M7_DATA_ONLY.label, value: 'M7_DATA_ONLY' },
    { label: HISTORY_MODE_DESCRIPTORS.M8_VALIDATION_ONLY.label, value: 'M8_VALIDATION_ONLY' },
  ];

  /**
   * Project options derived from historical records
   */
  public projectOptions = computed<CustomSelectOption[]>(() => {
    const list = this.historyItems();
    const map = new Map<string, string>();
    for (const item of list) {
      if (!map.has(item.projectId)) {
        map.set(item.projectId, item.projectName);
      }
    }

    const opts: CustomSelectOption[] = [{ label: 'All Projects', value: 'ALL' }];
    for (const [projId, projName] of map.entries()) {
      opts.push({ label: projName, value: projId });
    }
    return opts;
  });

  /**
   * Outcome options for GDS select dropdown
   */
  public outcomeOptions: CustomSelectOption[] = [
    { label: 'All Outcomes', value: 'ALL' },
    { label: 'Succeeded', value: 'SUCCEEDED' },
    { label: 'Failed', value: 'FAILED' },
    { label: 'Stopped', value: 'STOPPED' },
    { label: 'Running', value: 'RUNNING' },
    { label: 'Cancelled', value: 'CANCELLED' },
    { label: 'Aborted', value: 'ABORTED' }
  ];

  /**
   * Validation State options for GDS select dropdown
   */
  public validationOptions: CustomSelectOption[] = [
    { label: 'All Validation States', value: 'ALL' },
    { label: 'Passed (0 Discrepancies)', value: 'PASSED' },
    { label: 'Discrepancies Detected', value: 'MISMATCHES_DETECTED' },
    { label: 'Reconciled', value: 'RECONCILED' },
    { label: 'Validation Failed', value: 'FAILED' },
    { label: 'Skipped', value: 'SKIPPED' },
    { label: 'Not Configured', value: 'NOT_CONFIGURED' }
  ];

  /**
   * Evidence options for GDS select dropdown
   */
  public evidenceOptions: CustomSelectOption[] = [
    { label: 'All Evidence States', value: 'ALL' },
    { label: 'Sealed (SHA-256 Verified)', value: 'SEALED' },
    { label: 'Available (Sealed / Open)', value: 'AVAILABLE' },
    { label: 'Unverified / Raw', value: 'UNVERIFIED' },
    { label: 'Integrity Alert / Mismatch', value: 'ALERT' }
  ];

  /**
   * Continuity options for GDS select dropdown
   */
  public continuityOptions: CustomSelectOption[] = [
    { label: 'All Continuity States', value: 'ALL' },
    { label: 'Cutover Completed', value: 'CUTOVER_COMPLETED' },
    { label: 'Cutover Rolled Back', value: 'ROLLED_BACK' },
    { label: 'Cutover In Progress', value: 'IN_PROGRESS' }
  ];

  /**
   * Sort options for GDS select dropdown
   */
  public sortOptions: CustomSelectOption[] = [
    { label: 'Date Completed (Newest)', value: 'completed_desc' },
    { label: 'Date Completed (Oldest)', value: 'completed_asc' },
    { label: 'Migration Name (A to Z)', value: 'name_asc' },
    { label: 'Migration Name (Z to A)', value: 'name_desc' },
    { label: 'Total Rows (Highest)', value: 'rows_desc' },
    { label: 'Discrepancies (Highest)', value: 'discrepancies_desc' }
  ];

  /**
   * Date Range options for GDS select dropdown
   */
  public dateRangeOptions: CustomSelectOption[] = [
    { label: 'All Dates', value: 'ALL' },
    { label: 'Today', value: 'TODAY' },
    { label: 'Last 7 Days', value: 'LAST_7_DAYS' },
    { label: 'Last 30 Days', value: 'LAST_30_DAYS' },
    { label: 'Custom Range', value: 'CUSTOM' }
  ];

  public setSearchQuery(q: string): void {
    this.filters.update(curr => ({ ...curr, searchQuery: q }));
  }

  public setProjectFilter(project: string | 'ALL'): void {
    this.filters.update(curr => ({ ...curr, project }));
  }

  public setModeFilter(mode: HistoryMode | 'ALL'): void {
    this.filters.update(curr => ({ ...curr, mode }));
  }

  public setOutcomeFilter(outcome: HistoryOutcome | 'ALL'): void {
    this.filters.update(curr => ({ ...curr, outcome }));
  }

  public setValidationFilter(validationState: ValidationReconciliationState | 'ALL'): void {
    this.filters.update(curr => ({ ...curr, validationState }));
  }

  public setEvidenceFilter(evidence: string | 'ALL'): void {
    this.filters.update(curr => ({ ...curr, evidence }));
  }

  public setContinuityFilter(continuity: string | 'ALL'): void {
    this.filters.update(curr => ({ ...curr, continuity }));
  }

  public setDateRangeFilter(dateRange: HistoryDateRangeOption, startDate?: string, endDate?: string): void {
    this.filters.update(curr => ({
      ...curr,
      dateRange,
      startDate: startDate !== undefined ? startDate : curr.startDate,
      endDate: endDate !== undefined ? endDate : curr.endDate
    }));
  }

  public setCustomDateRange(startDate: string, endDate: string): void {
    this.filters.update(curr => ({
      ...curr,
      dateRange: 'CUSTOM',
      startDate,
      endDate
    }));
  }

  public setSort(sortBy: HistorySortOption): void {
    this.filters.update(curr => ({ ...curr, sortBy }));
  }

  public clearFilters(): void {
    this.filters.set({
      searchQuery: '',
      project: 'ALL',
      mode: 'ALL',
      outcome: 'ALL',
      validationState: 'ALL',
      evidence: 'ALL',
      continuity: 'ALL',
      dateRange: 'ALL',
      startDate: '',
      endDate: '',
      sortBy: 'completed_desc'
    });
  }

  private setupSubscriptions(): void {
    if (!this.ipc) return;

    const unsubTelemetry = this.ipc.subscribe('akaal:telemetry', (event: any) => {
      if (!event) return;
      const migId = event.migration_id || event.migrationId || event.subject_id;
      if (migId) {
        this.historyItems.update(list =>
          list.map(item => {
            if (item.migrationId === migId || item.id === migId) {
              const nextOutcome = event.state === 'COMPLETED' ? 'SUCCEEDED' : event.state === 'FAILED' ? 'FAILED' : item.outcome;
              const nextThroughput = typeof event.throughput_rows_per_sec === 'number' ? `${Math.round(event.throughput_rows_per_sec / 1000)}k rows/s` : item.throughputFormatted;
              return {
                ...item,
                outcome: nextOutcome as HistoryOutcome,
                throughputFormatted: nextThroughput,
                completedAt: event.state === 'COMPLETED' ? (event.timestamp || new Date().toISOString()) : item.completedAt
              };
            }
            return item;
          })
        );
      }
    });
    this.unsubs.push(unsubTelemetry);

    const unsubStatus = this.ipc.subscribe('akaal:migration:status', (event: any) => {
      if (!event) return;
      const migId = event.migration_id || event.migrationId;
      if (migId) {
        this.historyItems.update(list =>
          list.map(item => {
            if (item.migrationId === migId || item.id === migId) {
              return {
                ...item,
                outcome: (event.state === 'COMPLETED' ? 'SUCCEEDED' : event.state === 'FAILED' ? 'FAILED' : item.outcome) as HistoryOutcome,
                completedAt: event.state === 'COMPLETED' ? new Date().toISOString() : item.completedAt
              };
            }
            return item;
          })
        );
      }
    });
    this.unsubs.push(unsubStatus);

    const unsubConn = this.ipc.subscribe('akaal:engine:connected', () => {
      this.loadState();
    });
    this.unsubs.push(unsubConn);
  }

  public async loadState(): Promise<void> {
    if (!this.migrationIpc) {
      this.availabilityState.set('READY');
      return;
    }

    this.availabilityState.set('LOADING');
    this.errorMessage.set('');

    try {
      const [migRes, auditRes] = await Promise.all([
        this.migrationIpc.listMigrations().catch(() => null),
        this.migrationIpc.getAuditTrail().catch(() => null)
      ]);

      if (migRes && migRes.status === 'SUCCESS' && Array.isArray(migRes.data?.migrations)) {
        const canonicalMigs = migRes.data.migrations;
        if (canonicalMigs.length === 0) {
          this.historyItems.set([]);
          this.availabilityState.set('EMPTY');
          return;
        }

        const formatDuration = (startStr?: string, endStr?: string | null): string => {
          if (!startStr) return '—';
          const start = new Date(startStr).getTime();
          const end = endStr ? new Date(endStr).getTime() : Date.now();
          const diffSec = Math.max(0, Math.floor((end - start) / 1000));
          if (diffSec < 60) return `${diffSec}s`;
          const mins = Math.floor(diffSec / 60);
          const secs = diffSec % 60;
          if (mins < 60) return `${mins}m ${secs}s`;
          const hrs = Math.floor(mins / 60);
          const remMins = mins % 60;
          return `${hrs}h ${remMins}m`;
        };

        const mapped: MigrationHistoryItem[] = canonicalMigs.map((m: any, idx: number) => {
          const cfg = m.configuration || {};
          const srcProv = m.source_provider || cfg.source_provider || cfg.source?.provider || 'Source DB';
          const tgtProv = m.target_provider || cfg.target_provider || cfg.target?.provider || 'Target DB';
          const isCutover = ['M2_BULK_CDC', 'M3_CDC', 'M4_INCREMENTAL', 'M5_STATE_SYNC'].includes(m.mode);
          const startTimestamp = m.started_at || m.created_at || new Date().toISOString();
          const endTimestamp = m.state === 'COMPLETED' ? (m.updated_at || new Date().toISOString()) : (['FAILED', 'STOPPED', 'CANCELLED', 'ABORTED'].includes(m.state) ? (m.updated_at || null) : null);
          const rowCount = m.rows_processed || m.objects_completed || m.total_rows || 0;

          return {
            id: m.id || m.migration_id || `hist-${idx + 1}`,
            migrationId: m.migration_id || m.id,
            migrationName: m.name || `${srcProv} to ${tgtProv}`,
            executionId: m.execution_id || m.active_attempt_id || `exec-${m.migration_id || m.id}-01`,
            projectId: m.project_id || 'proj-core',
            projectName: m.project_name || 'Enterprise Modernization',
            initiativeName: m.initiative_name,
            sourceProvider: srcProv,
            sourceProviderCode: srcProv.toLowerCase().split(' ')[0],
            targetProvider: tgtProv,
            targetProviderCode: tgtProv.toLowerCase().split(' ')[0],
            mode: (m.mode || 'M1_BULK') as HistoryMode,
            outcome: (m.state === 'COMPLETED' ? 'SUCCEEDED' : m.state === 'FAILED' ? 'FAILED' : m.state === 'RUNNING' ? 'RUNNING' : m.state === 'PAUSED' ? 'PAUSED' : m.state === 'CANCELLED' ? 'CANCELLED' : m.state === 'ABORTED' ? 'ABORTED' : 'SUCCEEDED') as HistoryOutcome,
            errorMessage: m.error_message || null,
            validationState: (m.difference_count && m.difference_count > 0 ? 'MISMATCHES_DETECTED' : m.validation_state || (m.state === 'COMPLETED' ? 'PASSED' : 'NOT_CONFIGURED')) as ValidationReconciliationState,
            validationDiscrepancyCount: m.difference_count || 0,
            evidenceAvailability: (m.evidence_availability || (m.state === 'COMPLETED' ? 'SEALED' : 'NOT_GENERATED')) as any,
            evidenceIntegrity: (m.evidence_integrity || (m.state === 'COMPLETED' ? 'SHA256_VERIFIED' : 'UNVERIFIED')) as any,
            evidenceDigest: m.evidence_digest || m.plan_fingerprint || null,
            evidenceSizeBytes: m.evidence_size_bytes || null,
            continuity: {
              cutoverStatus: isCutover ? (m.state === 'COMPLETED' ? 'COMPLETED' : m.state === 'RUNNING' ? 'IN_PROGRESS' : 'SCHEDULED') : 'NOT_APPLICABLE',
              recoveryStatus: isCutover ? (m.state === 'FAILED' ? 'RESTORED' : 'NONE') : 'NOT_APPLICABLE',
              cdcLagSeconds: typeof m.cdc_lag_ms === 'number' ? m.cdc_lag_ms / 1000 : (typeof m.cdc_lag_seconds === 'number' ? m.cdc_lag_seconds : null),
              cutoverDowntimeSeconds: m.cutover_downtime_seconds ?? null,
              cutoverCompletedAt: isCutover && m.state === 'COMPLETED' ? m.updated_at : null,
              rollbackTriggeredAt: m.rollback_triggered_at || null,
              rollbackReason: m.rollback_reason || null
            },
            operator: m.operator || m.actor_id || m.creator_actor_id || 'System Operator',
            startedAt: startTimestamp,
            completedAt: endTimestamp,
            durationString: m.duration_string || formatDuration(startTimestamp, endTimestamp),
            rowsProcessed: rowCount,
            throughputFormatted: m.throughput_rows_per_sec ? `${Math.round(m.throughput_rows_per_sec).toLocaleString()} rows/s` : (rowCount > 0 ? `${rowCount.toLocaleString()} rows` : '—')
          };
        });

        this.historyItems.set(mapped);
        this.availabilityState.set('READY');
      } else {
        this.availabilityState.set('UNAVAILABLE');
        this.historyItems.set([]);
      }
    } catch (err: any) {
      this.availabilityState.set('ERROR');
      this.errorMessage.set(err?.message || 'Failed to load migration history');
      this.historyItems.set([]);
    }
  }

  public reload(): void {
    this.errorMessage.set('');
    if (this.historyItems().length === 0) {
      this.historyItems.set(INITIAL_MIGRATION_HISTORY_FIXTURES);
    }
    this.availabilityState.set('READY');
    if (this.ipc && this.ipc.connectionState() === 'connected') {
      this.loadState();
    }
  }

  public loadFixturesForTesting(): void {
    this.availabilityState.set('READY');
    this.historyItems.set(INITIAL_MIGRATION_HISTORY_FIXTURES);
    this.errorMessage.set('');
  }

  public setAvailabilityState(state: HistoryAvailabilityState, errorMsg?: string): void {
    this.availabilityState.set(state);
    if (errorMsg) {
      this.errorMessage.set(errorMsg);
    }
  }
}
