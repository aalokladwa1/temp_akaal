import { Injectable, signal, computed } from '@angular/core';
import {
  MigrationHistoryItem,
  HistoryFilterState,
  HistoryAvailabilityState,
  HistoryMode,
  HistoryOutcome,
  ValidationReconciliationState,
  HistorySortOption,
  HISTORY_MODE_DESCRIPTORS
} from './history-home.models';
import { INITIAL_MIGRATION_HISTORY_FIXTURES } from './history-home.fixtures';
import { CustomSelectOption } from '../../../shared/components/custom-select.component';

@Injectable({
  providedIn: 'root'
})
export class HistoryHomeService {
  public historyItems = signal<MigrationHistoryItem[]>(INITIAL_MIGRATION_HISTORY_FIXTURES);

  public filters = signal<HistoryFilterState>({
    searchQuery: '',
    project: 'ALL',
    mode: 'ALL',
    outcome: 'ALL',
    validationState: 'ALL',
    evidence: 'ALL',
    continuity: 'ALL',
    sortBy: 'completed_desc'
  });

  public availabilityState = signal<HistoryAvailabilityState>('READY');
  public errorMessage = signal<string>('');

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
      f.continuity !== 'ALL'
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
      sortBy: 'completed_desc'
    });
  }

  public reload(): void {
    this.availabilityState.set('READY');
    this.errorMessage.set('');
    this.historyItems.set(INITIAL_MIGRATION_HISTORY_FIXTURES);
  }

  public setAvailabilityState(state: HistoryAvailabilityState, errorMsg?: string): void {
    this.availabilityState.set(state);
    if (errorMsg) {
      this.errorMessage.set(errorMsg);
    }
  }
}
