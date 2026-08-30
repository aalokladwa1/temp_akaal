import { Injectable, signal, computed } from '@angular/core';
import { MigrationDevFixturesAdapter } from '../fixtures/migration-dev-fixtures.adapter';
import {
  HistoryLedgerItem,
  MultiRunComparisonMetric
} from '../models/migration-view.models';

@Injectable({
  providedIn: 'root'
})
export class HistoryUiService {
  private fixtures: MigrationDevFixturesAdapter;

  public ledgerItems = signal<HistoryLedgerItem[]>([]);
  public filterSearch = signal<string>('');
  public filterLifecycle = signal<string>('ALL');
  public filterValidation = signal<string>('ALL');
  public filterEvidence = signal<string>('ALL');

  public selectedExecutionIds = signal<string[]>(['exec-20260828-001', 'exec-20260827-003']);
  public isComparisonModalOpen = signal<boolean>(false);

  public filteredLedgerItems = computed<HistoryLedgerItem[]>(() => {
    let list = this.ledgerItems();
    const q = this.filterSearch().trim().toLowerCase();
    const lc = this.filterLifecycle();
    const val = this.filterValidation();
    const ev = this.filterEvidence();

    if (q) {
      list = list.filter(i =>
        i.migrationName.toLowerCase().includes(q) ||
        i.executionId.toLowerCase().includes(q) ||
        i.operator.toLowerCase().includes(q)
      );
    }

    if (lc !== 'ALL') {
      list = list.filter(i => i.lifecycleState === lc);
    }

    if (val !== 'ALL') {
      list = list.filter(i => i.validationVerdict === val);
    }

    if (ev !== 'ALL') {
      list = list.filter(i => i.evidenceState === ev);
    }

    return list;
  });

  public comparisonMetrics = computed<MultiRunComparisonMetric[]>(() => {
    return this.fixtures.getMultiRunComparison();
  });

  constructor(fixtures?: MigrationDevFixturesAdapter) {
    this.fixtures = fixtures || new MigrationDevFixturesAdapter();
    this.ledgerItems.set(this.fixtures.getHistoryLedger());
  }

  public toggleExecutionSelection(id: string): void {
    const curr = this.selectedExecutionIds();
    if (curr.includes(id)) {
      this.selectedExecutionIds.set(curr.filter(x => x !== id));
    } else if (curr.length < 5) {
      this.selectedExecutionIds.set([...curr, id]);
    }
  }
}
