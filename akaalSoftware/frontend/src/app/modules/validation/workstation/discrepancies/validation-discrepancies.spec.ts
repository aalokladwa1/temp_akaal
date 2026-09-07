import { describe, it, expect, beforeEach } from 'vitest';
import { ValidationDiscrepanciesService } from './validation-discrepancies.service';
import {
  FIXTURE_DISCREPANCIES_DEFAULT_NOT_CONNECTED,
  FIXTURE_DISCREPANCIES_NORMAL,
  FIXTURE_DISCREPANCIES_40M_AGGREGATE,
  FIXTURE_DISCREPANCIES_EMPTY_PASSED,
  FIXTURE_DISCREPANCIES_NOT_EVALUATED,
  FIXTURE_DISCREPANCIES_LOADING,
  FIXTURE_DISCREPANCIES_ERROR,
  DISC_01_CUSTOMER_VALUE_DIFF,
  DISC_05_FINGERPRINT_DIFF,
  DISC_07_NULL_VS_EMPTY_STRING
} from './validation-discrepancies.fixtures';

describe('ValidationDiscrepanciesService & Domain Models', () => {
  let service: ValidationDiscrepanciesService;

  beforeEach(() => {
    service = new ValidationDiscrepanciesService();
  });

  it('should initialize with truthful default production state (NOT_CONNECTED, UNAVAILABLE)', () => {
    expect(service.viewStatus()).toBe('UNAVAILABLE');
    expect(service.summary().totalDiscrepancies).toBeNull();
    expect(service.summary().totalDiscrepanciesFormatted).toBe('—');
    expect(service.filteredItems().length).toBe(0);
    expect(service.navigator().length).toBe(0);
  });

  it('should load normal 19 findings fixture with accurate summary metrics', () => {
    service.setFixture('NORMAL_19_FINDINGS');

    expect(service.viewStatus()).toBe('READY');
    expect(service.summary().totalDiscrepancies).toBe(19);
    expect(service.summary().totalDiscrepanciesFormatted).toBe('19');
    expect(service.summary().affectedObjectsCount).toBe(4);
    expect(service.summary().unresolvedCount).toBe(18);
    expect(service.summary().explainedCount).toBe(1);
    expect(service.filteredItems().length).toBe(9);
    expect(service.selectedDiscrepancy()?.id).toBe('DISC-2026-0089-001');
  });

  it('should select a discrepancy by ID and update selectedDiscrepancy signal', () => {
    service.setFixture('NORMAL_19_FINDINGS');
    service.selectDiscrepancy('DISC-2026-0089-003');

    expect(service.selectedDiscrepancyId()).toBe('DISC-2026-0089-003');
    expect(service.selectedDiscrepancy()?.recordKey).toBe('order_id=ORD-99182');
    expect(service.selectedDiscrepancy()?.category).toBe('EXTRA_ON_TARGET');
  });

  it('should filter items by search query across object, key, attribute, and summary', () => {
    service.setFixture('NORMAL_19_FINDINGS');

    // Search by table name
    service.setSearchQuery('orders');
    expect(service.filteredItems().length).toBe(1);
    expect(service.filteredItems()[0].objectName).toBe('public.orders');

    // Search by attribute name
    service.setSearchQuery('balance');
    expect(service.filteredItems().length).toBe(2);

    // Search by key
    service.setSearchQuery('84109');
    expect(service.filteredItems().length).toBe(1);
    expect(service.filteredItems()[0].recordKey).toBe('customer_id=84109');

    // Clear search
    service.setSearchQuery('');
    expect(service.filteredItems().length).toBe(9);
  });

  it('should filter items by Discrepancy Category', () => {
    service.setFixture('NORMAL_19_FINDINGS');

    service.setCategoryFilter('MISSING_ON_TARGET');
    expect(service.filteredItems().length).toBe(1);
    expect(service.filteredItems()[0].category).toBe('MISSING_ON_TARGET');

    service.setCategoryFilter('CARDINALITY_DIFFERENCE');
    expect(service.filteredItems().length).toBe(1);
    expect(service.filteredItems()[0].category).toBe('CARDINALITY_DIFFERENCE');

    service.setCategoryFilter('ALL');
    expect(service.filteredItems().length).toBe(9);
  });

  it('should filter items by Proof Tier', () => {
    service.setFixture('NORMAL_19_FINDINGS');

    service.setProofTierFilter('TIER_1_STRUCTURAL');
    expect(service.filteredItems().length).toBe(1);
    expect(service.filteredItems()[0].id).toBe('DISC-2026-0089-009');

    service.setProofTierFilter('TIER_2_CARDINALITY');
    expect(service.filteredItems().length).toBe(1);
    expect(service.filteredItems()[0].id).toBe('DISC-2026-0089-004');

    service.setProofTierFilter('ALL');
    expect(service.filteredItems().length).toBe(9);
  });

  it('should filter items by Reconciliation State', () => {
    service.setFixture('NORMAL_19_FINDINGS');

    service.setReconciliationFilter('EXPLAINED_BY_TRANSFORMATION');
    expect(service.filteredItems().length).toBe(1);
    expect(service.filteredItems()[0].id).toBe('DISC-2026-0089-006');

    service.setReconciliationFilter('ALL');
    expect(service.filteredItems().length).toBe(9);
  });

  it('should handle Scope Navigator hierarchy and drill path', () => {
    service.setFixture('NORMAL_19_FINDINGS');

    // Filter by object
    service.setObjectFilter('public.customers');
    expect(service.selectedObjectFilter()).toBe('public.customers');
    expect(service.filteredItems().length).toBe(4);

    // Filter by partition
    service.setPartitionFilter('p_2026_q2', 'public.customers');
    expect(service.selectedPartitionFilter()).toBe('p_2026_q2');

    // Reset to root
    service.setObjectFilter(null);
    expect(service.selectedObjectFilter()).toBeNull();
    expect(service.selectedPartitionFilter()).toBeNull();
    expect(service.filteredItems().length).toBe(9);
  });

  it('should track active filter count and reset all filters cleanly', () => {
    service.setFixture('NORMAL_19_FINDINGS');

    service.setObjectFilter('public.customers');
    service.setCategoryFilter('VALUE_DIFFERENCE');
    service.setSearchQuery('balance');

    expect(service.activeFiltersCount()).toBe(3);

    service.resetFilters();

    expect(service.activeFiltersCount()).toBe(0);
    expect(service.selectedObjectFilter()).toBeNull();
    expect(service.selectedCategoryFilter()).toBe('ALL');
    expect(service.searchQuery()).toBe('');
    expect(service.filteredItems().length).toBe(9);
  });

  it('should handle 40M findings aggregate with bounded page without memory explosion', () => {
    service.setFixture('LARGE_40M_AGGREGATE');

    expect(service.summary().totalDiscrepancies).toBe(40000000);
    expect(service.summary().totalDiscrepanciesFormatted).toBe('40,000,000');
    expect(service.summary().isLargeAggregate).toBe(true);
    expect(service.summary().boundedPageSize).toBe(25);
    expect(service.filteredItems().length).toBe(3); // Bounded current page in memory
    expect(service.state().pagination.currentPage).toBe(1);

    service.setPage(2);
    expect(service.state().pagination.currentPage).toBe(2);
  });

  it('should preserve sensitive-data fail-closed policy (PROTECTED values masked, no raw leaks)', () => {
    service.setFixture('VALUE_DIFF');

    const item = service.selectedDiscrepancy();
    expect(item).not.toBeNull();

    const taxAttr = item!.attributes.find(a => a.attributeName === 'tax_identifier');
    expect(taxAttr).toBeDefined();
    expect(taxAttr!.sourceValueKind).toBe('PROTECTED');
    expect(taxAttr!.targetValueKind).toBe('PROTECTED');
    expect(taxAttr!.isSensitive).toBe(true);
  });

  it('should strictly distinguish NULL, EMPTY_STRING, WHITESPACE, and ABSENT values', () => {
    service.setFixture('NULL_EMPTY_ABSENT');

    const item = service.selectedDiscrepancy();
    expect(item).not.toBeNull();

    const middleName = item!.attributes.find(a => a.attributeName === 'middle_name');
    expect(middleName!.sourceValueKind).toBe('NULL');
    expect(middleName!.targetValueKind).toBe('EMPTY_STRING');

    const secEmail = item!.attributes.find(a => a.attributeName === 'secondary_email');
    expect(secEmail!.sourceValueKind).toBe('WHITESPACE');
    expect(secEmail!.targetValueKind).toBe('NULL');
  });

  it('should handle Tier 3 Partition Fingerprint difference with truthful unlocalized status and XOR disclaimer', () => {
    service.setFixture('FINGERPRINT_DIFF');

    const item = service.selectedDiscrepancy();
    expect(item).not.toBeNull();
    expect(item!.category).toBe('PARTITION_FINGERPRINT');
    expect(item!.fingerprintSummary?.localizationStatus).toBe('UNAVAILABLE');
    expect(item!.fingerprintSummary?.hostileXorNote).toContain('Hostile XOR Defect Guard');
  });

  it('should handle empty state (0 discrepancies) truthfully', () => {
    service.setFixture('EMPTY_PASSED');

    expect(service.viewStatus()).toBe('EMPTY');
    expect(service.summary().totalDiscrepancies).toBe(0);
    expect(service.summary().totalDiscrepanciesFormatted).toBe('0');
  });

  it('should handle NOT_EVALUATED state truthfully', () => {
    service.setFixture('NOT_EVALUATED');

    expect(service.viewStatus()).toBe('NOT_EVALUATED');
    expect(service.summary().totalDiscrepancies).toBeNull();
  });

  it('should handle LOADING state truthfully', () => {
    service.setFixture('LOADING');

    expect(service.viewStatus()).toBe('LOADING');
  });

  it('should handle ERROR state with error message', () => {
    service.setFixture('ERROR');

    expect(service.viewStatus()).toBe('ERROR');
    expect(service.errorMessage()).toContain('Connection refused');
  });

  it('should handle Historical read-only mission fixture', () => {
    service.setFixture('HISTORICAL');

    expect(service.isHistorical()).toBe(true);
  });
});
