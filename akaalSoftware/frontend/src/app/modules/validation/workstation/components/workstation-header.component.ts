import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ValidationWorkstationService } from '../validation-workstation.service';
import { ValidationDiscrepanciesService } from '../discrepancies/validation-discrepancies.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';
import { ValidationExecutionState, ValidationVerdict } from '../validation-workstation.models';

@Component({
  selector: 'app-workstation-header',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent, CustomSelectComponent],
  template: `
    <header class="bg-white border-b border-slate-200 px-6 lg:px-8 py-4 sticky top-0 z-30 shadow-2xs">
      <div class="max-w-[1680px] mx-auto flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        
        <!-- Identity Zone -->
        <div class="flex flex-col gap-2">
          
          <!-- Breadcrumbs & Identity Badges (Rectangular, rounded-md, NO pill capsules) -->
          <div class="flex items-center flex-wrap gap-2 text-xs">
            <span class="text-slate-400 font-medium">AKAAL Enterprise</span>
            <span class="text-slate-300">/</span>
            <a routerLink="/migration/validation" class="text-slate-500 hover:text-blue-600 font-medium transition-colors">
              Validation Missions
            </a>
            <span class="text-slate-300">/</span>
            
            <!-- Canonical Mission ID copy trigger -->
            <button
              type="button"
              (click)="store.copyValidationId()"
              class="inline-flex items-center gap-1.5 font-mono text-xs font-semibold px-2.5 py-1 rounded-md bg-slate-50 hover:bg-blue-50 text-slate-700 hover:text-blue-700 hover:border-blue-300 transition-colors border border-slate-200 cursor-pointer"
              [title]="'Click to copy mission ID: ' + store.validationId()">
              <span>{{ store.validationId() }}</span>
              <app-lucide-icon
                [name]="store.copiedId() ? 'check' : 'copy'"
                [size]="12"
                [class]="store.copiedId() ? 'text-emerald-600' : 'text-slate-400'"></app-lucide-icon>
            </button>

            <!-- Environment Tag -->
            <span class="inline-flex items-center px-2.5 py-1 rounded-md text-[11px] font-semibold bg-slate-50 text-slate-700 border border-slate-200">
              {{ store.state().environment }}
            </span>

            <!-- Production / Fixture Badge -->
            @if (store.isProductionDefault()) {
              <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-600 border border-slate-200" title="Truthful production state: No synthetic execution data">
                <span class="w-1.5 h-1.5 rounded-sm bg-slate-400"></span>
                <span>Production Mode</span>
              </span>
            } @else {
              <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200" title="Visual verification fixture active">
                <span class="w-1.5 h-1.5 rounded-sm bg-amber-500"></span>
                <span>Visual Test Fixture</span>
              </span>
            }
          </div>

          <!-- Mission Heading & Status Badges -->
          <div class="flex items-center flex-wrap gap-3.5 pt-0.5">
            <h1 class="text-xl font-bold text-slate-900 tracking-tight font-heading">
              {{ store.validationName() }}
            </h1>

            <!-- Execution State Badge -->
            <div [ngClass]="getExecutionStateBadgeClasses(store.executionState())"
                 class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold uppercase tracking-wider border">
              <app-lucide-icon [name]="getExecutionStateIcon(store.executionState())" [size]="12"></app-lucide-icon>
              <span>{{ formatExecutionState(store.executionState()) }}</span>
            </div>

            <!-- Validation Verdict Badge -->
            <div [ngClass]="getVerdictBadgeClasses(store.verdict())"
                 class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold uppercase tracking-wider border">
              <app-lucide-icon [name]="getVerdictIcon(store.verdict())" [size]="12"></app-lucide-icon>
              <span>Verdict: {{ formatVerdict(store.verdict()) }}</span>
            </div>

            <!-- Endpoint Route Summary Card -->
            <div class="inline-flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-700">
              <div class="flex items-center gap-1.5 font-medium">
                <app-lucide-icon name="database" [size]="13" class="text-blue-600"></app-lucide-icon>
                <span class="font-bold text-slate-900">{{ store.state().source.provider }}</span>
                <span class="text-slate-400 font-mono text-[11px]">({{ store.state().source.label }})</span>
              </div>
              <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400"></app-lucide-icon>
              <div class="flex items-center gap-1.5 font-medium">
                <app-lucide-icon name="database" [size]="13" class="text-emerald-600"></app-lucide-icon>
                <span class="font-bold text-slate-900">{{ store.state().target.provider }}</span>
                <span class="text-slate-400 font-mono text-[11px]">({{ store.state().target.label }})</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Action Bar Zone -->
        <div class="flex items-center gap-3 shrink-0 flex-wrap">
          
          <!-- Test Fixture Switcher (Using Global Canonical CustomSelectComponent) -->
          <div class="w-64">
            <app-custom-select
              [options]="fixtureOptions"
              [value]="currentFixtureValue"
              [size]="'sm'"
              [searchable]="true"
              searchPlaceholder="Search scenario fixtures..."
              (valueChange)="onFixtureSelected($event)">
            </app-custom-select>
          </div>

          <!-- Technical Inspection Drawer Button -->
          <button
            type="button"
            (click)="store.toggleDrawer()"
            class="h-7 px-3 text-xs font-semibold rounded bg-white border border-slate-200 hover:border-blue-300 hover:bg-blue-50 text-slate-700 hover:text-blue-700 transition-all flex items-center gap-1.5 cursor-pointer shadow-2xs">
            <app-lucide-icon name="panel-left-close" [size]="13" class="text-slate-500"></app-lucide-icon>
            <span>Technical Details</span>
          </button>
        </div>
      </div>
    </header>
  `
})
export class WorkstationHeaderComponent {
  readonly store = inject(ValidationWorkstationService);
  readonly discrepanciesStore = inject(ValidationDiscrepanciesService);

  currentFixtureValue: string = 'NOT_CONNECTED';

  readonly fixtureOptions: CustomSelectOption[] = [
    { label: 'Default (Not Connected)', value: 'NOT_CONNECTED', group: 'Truthful Production State', icon: 'shield' },
    { label: 'Running (Clean Parity)', value: 'RUNNING_CLEAN', group: 'Overview Fixtures', icon: 'play-circle' },
    { label: 'Running (Divergence Flagged)', value: 'RUNNING_DIFFS', group: 'Overview Fixtures', icon: 'alert-triangle' },
    { label: 'Completed + Passed (SYNC)', value: 'COMPLETED_PASSED_SYNC', group: 'Overview Fixtures', icon: 'check-circle-2' },
    { label: 'Completed + Failed (SYNC)', value: 'COMPLETED_FAILED_SYNC', group: 'Overview Fixtures', icon: 'x-circle' },
    { label: 'Completed + Passed (ASYNC)', value: 'COMPLETED_PASSED_ASYNC', group: 'Overview Fixtures', icon: 'check-circle-2' },
    { label: 'Completed + Failed (ASYNC)', value: 'COMPLETED_FAILED_ASYNC', group: 'Overview Fixtures', icon: 'x-circle' },
    { label: 'Completed (Mode Unspecified)', value: 'COMPLETED_UNKNOWN_MODE', group: 'Overview Fixtures', icon: 'check-circle-2' },
    { label: 'Verdict Withheld', value: 'WITHHELD', group: 'Overview Fixtures', icon: 'help-circle' },
    { label: 'Interrupted', value: 'INTERRUPTED', group: 'Overview Fixtures', icon: 'pause-circle' },
    { label: 'Recovering from Checkpoint', value: 'RECOVERING', group: 'Overview Fixtures', icon: 'refresh-cw' },
    { label: 'Blocked (Missing Map)', value: 'BLOCKED', group: 'Overview Fixtures', icon: 'alert-octagon' },
    { label: 'Baseline Stale', value: 'BASELINE_INVALID', group: 'Overview Fixtures', icon: 'alert-triangle' },
    { label: 'Audit-Only (Mutation Prohibited)', value: 'AUDIT_ONLY_REPAIR_FORBIDDEN', group: 'Overview Fixtures', icon: 'lock' },
    { label: 'Large Enterprise (2.45B)', value: 'LARGE_ENTERPRISE', group: 'Overview Fixtures', icon: 'database' },
    
    // Discrepancy Scenarios
    { label: 'Discrepancies: 19 Findings (Normal)', value: 'DISC_NORMAL_19_FINDINGS', group: 'Discrepancies Scenarios', icon: 'list-tree' },
    { label: 'Discrepancies: Value Difference Focus', value: 'DISC_VALUE_DIFF', group: 'Discrepancies Scenarios', icon: 'file-diff' },
    { label: 'Discrepancies: Missing Target Focus', value: 'DISC_MISSING_TARGET', group: 'Discrepancies Scenarios', icon: 'minus-square' },
    { label: 'Discrepancies: Extra Target Focus', value: 'DISC_EXTRA_TARGET', group: 'Discrepancies Scenarios', icon: 'plus-square' },
    { label: 'Discrepancies: Cardinality Delta Focus', value: 'DISC_CARDINALITY_DIFF', group: 'Discrepancies Scenarios', icon: 'binary' },
    { label: 'Discrepancies: Partition Fingerprint Focus', value: 'DISC_FINGERPRINT_DIFF', group: 'Discrepancies Scenarios', icon: 'git-branch' },
    { label: 'Discrepancies: Transformed Context Focus', value: 'DISC_TRANSFORMED_EXPLAINED', group: 'Discrepancies Scenarios', icon: 'git-merge' },
    { label: 'Discrepancies: NULL vs Empty Focus', value: 'DISC_NULL_EMPTY_ABSENT', group: 'Discrepancies Scenarios', icon: 'code' },
    { label: 'Discrepancies: Long Values & LOB Focus', value: 'DISC_LONG_VALUES_LOB', group: 'Discrepancies Scenarios', icon: 'file-text' },
    { label: 'Discrepancies: Schema DDL Diff Focus', value: 'DISC_STRUCTURAL_DIFF', group: 'Discrepancies Scenarios', icon: 'table-properties' },
    { label: 'Discrepancies: Baseline Drift Focus', value: 'DISC_BASELINE_DRIFT', group: 'Discrepancies Scenarios', icon: 'shield-alert' },
    { label: 'Discrepancies: 40M Findings Aggregate', value: 'DISC_LARGE_40M_AGGREGATE', group: 'Discrepancies Scenarios', icon: 'server' },
    { label: 'Discrepancies: Zero Findings (Passed)', value: 'DISC_EMPTY_PASSED', group: 'Discrepancies Scenarios', icon: 'check-circle-2' },
    { label: 'Discrepancies: Not Evaluated', value: 'DISC_NOT_EVALUATED', group: 'Discrepancies Scenarios', icon: 'clock' },
    { label: 'Discrepancies: Loading Skeleton', value: 'DISC_LOADING', group: 'Discrepancies Scenarios', icon: 'loader' },
    { label: 'Discrepancies: Error State', value: 'DISC_ERROR', group: 'Discrepancies Scenarios', icon: 'alert-octagon' },
    { label: 'Discrepancies: Historical Read-Only', value: 'DISC_HISTORICAL', group: 'Discrepancies Scenarios', icon: 'history' }
  ];

  formatExecutionState(state: ValidationExecutionState): string {
    switch (state) {
      case 'NOT_CONNECTED': return 'Not Connected';
      case 'QUEUED': return 'Queued';
      case 'RUNNING': return 'Running';
      case 'PAUSED': return 'Paused';
      case 'INTERRUPTED': return 'Interrupted';
      case 'RECOVERING': return 'Recovering';
      case 'BLOCKED': return 'Blocked';
      case 'COMPLETED': return 'Completed';
    }
  }

  getExecutionStateIcon(state: ValidationExecutionState): string {
    switch (state) {
      case 'NOT_CONNECTED': return 'shield';
      case 'QUEUED': return 'clock';
      case 'RUNNING': return 'play-circle';
      case 'PAUSED': return 'pause-circle';
      case 'INTERRUPTED': return 'alert-triangle';
      case 'RECOVERING': return 'refresh-cw';
      case 'BLOCKED': return 'alert-octagon';
      case 'COMPLETED': return 'check-circle-2';
    }
  }

  getExecutionStateBadgeClasses(state: ValidationExecutionState): string {
    switch (state) {
      case 'NOT_CONNECTED': return 'bg-slate-100 text-slate-700 border-slate-300';
      case 'QUEUED': return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'RUNNING': return 'bg-blue-50 text-blue-700 border-blue-200 animate-pulse';
      case 'PAUSED': return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'INTERRUPTED': return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'RECOVERING': return 'bg-purple-50 text-purple-700 border-purple-200';
      case 'BLOCKED': return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'COMPLETED': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    }
  }

  getExecutionStateDotClasses(state: ValidationExecutionState): string {
    switch (state) {
      case 'NOT_CONNECTED': return 'bg-slate-400';
      case 'QUEUED': return 'bg-blue-500';
      case 'RUNNING': return 'bg-blue-600';
      case 'PAUSED': return 'bg-amber-500';
      case 'INTERRUPTED': return 'bg-amber-500';
      case 'RECOVERING': return 'bg-purple-500';
      case 'BLOCKED': return 'bg-rose-500';
      case 'COMPLETED': return 'bg-emerald-500';
    }
  }

  formatVerdict(verdict: ValidationVerdict): string {
    switch (verdict) {
      case 'NOT_EVALUATED': return 'Not Evaluated';
      case 'PASSED': return 'Passed';
      case 'FAILED': return 'Failed';
      case 'WITHHELD': return 'Withheld';
    }
  }

  getVerdictBadgeClasses(verdict: ValidationVerdict): string {
    switch (verdict) {
      case 'NOT_EVALUATED': return 'bg-slate-50 text-slate-600 border-slate-200';
      case 'PASSED': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'FAILED': return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'WITHHELD': return 'bg-amber-50 text-amber-700 border-amber-200';
    }
  }

  getVerdictIcon(verdict: ValidationVerdict): string {
    switch (verdict) {
      case 'NOT_EVALUATED': return 'help-circle';
      case 'PASSED': return 'shield-check';
      case 'FAILED': return 'shield-alert';
      case 'WITHHELD': return 'alert-triangle';
    }
  }

  onFixtureSelected(val: string): void {
    this.currentFixtureValue = val;
    if (val.startsWith('DISC_')) {
      const discKey = val.replace('DISC_', '');
      this.store.setFixture('RUNNING_DIFFS');
      this.discrepanciesStore.setFixture(discKey);
      this.store.setActiveTab('discrepancies');
    } else if (val === 'NOT_CONNECTED') {
      this.store.resetToProductionDefault();
      this.discrepanciesStore.resetToProductionDefault();
    } else {
      this.store.setFixture(val);
    }
  }
}
