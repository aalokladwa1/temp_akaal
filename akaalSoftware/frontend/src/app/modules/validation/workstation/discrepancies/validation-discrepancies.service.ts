/**
 * validation-discrepancies.service.ts
 * =====================================
 * Reactive state store for the Discrepancies & Reconciliation workspace.
 * Manages local investigation UI state (selection, filtering, pagination) while preserving canonical truth.
 */

import { Injectable, signal, computed } from '@angular/core';
import {
  DiscrepanciesWorkspaceModel,
  DiscrepancyItem,
  DiscrepancyCategory,
  DiscrepancyProofTier,
  ReconciliationState,
  DiscrepancyViewStatus
} from './validation-discrepancies.models';
import {
  FIXTURE_DISCREPANCIES_DEFAULT_NOT_CONNECTED,
  DISCREPANCIES_FIXTURES
} from './validation-discrepancies.fixtures';

@Injectable({
  providedIn: 'root'
})
export class ValidationDiscrepanciesService {
  // Main workspace state signal (defaults strictly to truthful NOT_CONNECTED)
  private _state = signal<DiscrepanciesWorkspaceModel>(FIXTURE_DISCREPANCIES_DEFAULT_NOT_CONNECTED);
  readonly state = this._state.asReadonly();

  // Selected discrepancy signal
  readonly selectedDiscrepancyId = computed(() => this._state().selectedDiscrepancyId);

  // Active filters
  readonly selectedObjectFilter = computed(() => this._state().selectedObjectFilter);
  readonly selectedPartitionFilter = computed(() => this._state().selectedPartitionFilter);
  readonly selectedCategoryFilter = computed(() => this._state().selectedCategoryFilter);
  readonly selectedProofTierFilter = computed(() => this._state().selectedProofTierFilter);
  readonly selectedReconciliationFilter = computed(() => this._state().selectedReconciliationFilter);
  readonly searchQuery = computed(() => this._state().searchQuery);
  readonly showDifferencesOnly = computed(() => this._state().showDifferencesOnly);

  // Status & summaries
  readonly viewStatus = computed(() => this._state().viewStatus);
  readonly summary = computed(() => this._state().summary);
  readonly navigator = computed(() => this._state().navigator);
  readonly isHistorical = computed(() => !!this._state().isHistorical);
  readonly errorMessage = computed(() => this._state().errorMessage);

  // Filtered items (applies search & active filter criteria)
  readonly filteredItems = computed(() => {
    const s = this._state();
    let result = s.items;

    if (s.selectedObjectFilter) {
      result = result.filter(item => item.objectName === s.selectedObjectFilter);
    }

    if (s.selectedPartitionFilter) {
      result = result.filter(item => item.partitionId === s.selectedPartitionFilter);
    }

    if (s.selectedCategoryFilter !== 'ALL') {
      result = result.filter(item => item.category === s.selectedCategoryFilter);
    }

    if (s.selectedProofTierFilter !== 'ALL') {
      result = result.filter(item => item.proofTier === s.selectedProofTierFilter);
    }

    if (s.selectedReconciliationFilter !== 'ALL') {
      result = result.filter(item => item.reconciliationState === s.selectedReconciliationFilter);
    }

    if (s.searchQuery.trim()) {
      const q = s.searchQuery.trim().toLowerCase();
      result = result.filter(item =>
        item.objectName.toLowerCase().includes(q) ||
        item.recordKey.toLowerCase().includes(q) ||
        item.differenceSummary.toLowerCase().includes(q) ||
        item.affectedAttributes.some(attr => attr.toLowerCase().includes(q)) ||
        item.attributes.some(attr => attr.attributeName.toLowerCase().includes(q))
      );
    }

    return result;
  });

  // Selected discrepancy object computed from current items
  readonly selectedDiscrepancy = computed<DiscrepancyItem | null>(() => {
    const s = this._state();
    if (!s.selectedDiscrepancyId) {
      return s.items.length > 0 ? s.items[0] : null;
    }
    return s.items.find(item => item.id === s.selectedDiscrepancyId) || (s.items.length > 0 ? s.items[0] : null);
  });

  // Active filter count for badge/reset display
  readonly activeFiltersCount = computed(() => {
    let count = 0;
    const s = this._state();
    if (s.selectedObjectFilter) count++;
    if (s.selectedPartitionFilter) count++;
    if (s.selectedCategoryFilter !== 'ALL') count++;
    if (s.selectedProofTierFilter !== 'ALL') count++;
    if (s.selectedReconciliationFilter !== 'ALL') count++;
    if (s.searchQuery.trim()) count++;
    return count;
  });

  // Available unique objects for filter dropdown
  readonly availableObjects = computed(() => {
    const s = this._state();
    const set = new Set<string>();
    s.items.forEach(i => set.add(i.objectName));
    return Array.from(set);
  });

  /**
   * Select a discrepancy by ID for detailed inspection.
   */
  selectDiscrepancy(id: string): void {
    this._state.update(curr => ({ ...curr, selectedDiscrepancyId: id }));
  }

  /**
   * Set object filter from scope navigator or dropdown.
   */
  setObjectFilter(objectName: string | null): void {
    this._state.update(curr => {
      // If filtering by object, reset partition filter if it doesn't belong
      return {
        ...curr,
        selectedObjectFilter: objectName,
        selectedPartitionFilter: null
      };
    });
  }

  /**
   * Set partition filter from scope navigator.
   */
  setPartitionFilter(partitionId: string | null, objectName?: string): void {
    this._state.update(curr => ({
      ...curr,
      selectedPartitionFilter: partitionId,
      selectedObjectFilter: objectName !== undefined ? objectName : curr.selectedObjectFilter
    }));
  }

  /**
   * Set category filter.
   */
  setCategoryFilter(category: DiscrepancyCategory | 'ALL'): void {
    this._state.update(curr => ({ ...curr, selectedCategoryFilter: category }));
  }

  /**
   * Set proof tier filter.
   */
  setProofTierFilter(tier: DiscrepancyProofTier | 'ALL'): void {
    this._state.update(curr => ({ ...curr, selectedProofTierFilter: tier }));
  }

  /**
   * Set reconciliation state filter.
   */
  setReconciliationFilter(recState: ReconciliationState | 'ALL'): void {
    this._state.update(curr => ({ ...curr, selectedReconciliationFilter: recState }));
  }

  /**
   * Set search query.
   */
  setSearchQuery(query: string): void {
    this._state.update(curr => ({ ...curr, searchQuery: query }));
  }

  /**
   * Toggle differences only vs show all attributes.
   */
  toggleShowDifferencesOnly(): void {
    this._state.update(curr => ({ ...curr, showDifferencesOnly: !curr.showDifferencesOnly }));
  }

  /**
   * Clear all active filters.
   */
  resetFilters(): void {
    this._state.update(curr => ({
      ...curr,
      selectedObjectFilter: null,
      selectedPartitionFilter: null,
      selectedCategoryFilter: 'ALL',
      selectedProofTierFilter: 'ALL',
      selectedReconciliationFilter: 'ALL',
      searchQuery: ''
    }));
  }

  /**
   * Change pagination page.
   */
  setPage(page: number): void {
    this._state.update(curr => ({
      ...curr,
      pagination: { ...curr.pagination, currentPage: page }
    }));
  }

  /**
   * Set view status directly (e.g. LOADING, ERROR, UNAVAILABLE).
   */
  setViewStatus(status: DiscrepancyViewStatus, errorMsg?: string): void {
    this._state.update(curr => ({
      ...curr,
      viewStatus: status,
      errorMessage: errorMsg
    }));
  }

  /**
   * Test fixture loader for visual testing and demonstration.
   */
  setFixture(fixtureKey: string): void {
    const fixture = DISCREPANCIES_FIXTURES[fixtureKey];
    if (fixture) {
      this._state.set(JSON.parse(JSON.stringify(fixture)));
    }
  }

  /**
   * Reset strictly to truthful production default.
   */
  resetToProductionDefault(): void {
    this._state.set(FIXTURE_DISCREPANCIES_DEFAULT_NOT_CONNECTED);
  }
}
