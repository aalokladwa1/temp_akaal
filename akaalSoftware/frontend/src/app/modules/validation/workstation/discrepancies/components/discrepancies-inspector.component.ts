import { Component, Input, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DiscrepancyItem, DiscrepancyCategory, DiscrepancyProofTier, ReconciliationState } from '../validation-discrepancies.models';
import { ValidationDiscrepanciesService } from '../validation-discrepancies.service';
import { DiscrepanciesAttributeDiffComponent } from './discrepancies-attribute-diff.component';
import { DiscrepanciesContextCardComponent } from './discrepancies-context-card.component';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-discrepancies-inspector',
  standalone: true,
  imports: [
    CommonModule,
    LucideIconComponent,
    DiscrepanciesAttributeDiffComponent,
    DiscrepanciesContextCardComponent
  ],
  template: `
    <section class="bg-white border border-slate-200/80 rounded-xl p-6 lg:p-7 shadow-2xs flex flex-col gap-6">
      
      <!-- Top Inspector Header -->
      <div class="flex items-center justify-between flex-wrap gap-4 pb-5 border-b border-slate-100">
        
        <!-- Left: Selected Item Identity -->
        <div class="flex items-center gap-3.5 flex-wrap">
          <div class="w-10 h-10 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 shrink-0">
            <app-lucide-icon name="microscope" [size]="20"></app-lucide-icon>
          </div>

          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-xs font-mono font-bold text-slate-900 bg-slate-100 px-2.5 py-0.5 rounded border border-slate-200">
                {{ item.objectName }}
              </span>
              <span class="text-slate-400 font-mono text-xs">/</span>
              <button
                type="button"
                (click)="copyText(item.recordKey, 'rec_' + item.recordKey)"
                [title]="copiedKey() === 'rec_' + item.recordKey ? 'Copied record key' : 'Copy record key'"
                class="inline-flex items-center gap-1.5 font-mono font-bold text-blue-700 hover:text-blue-800 hover:bg-blue-50 px-1.5 py-0.5 rounded cursor-pointer transition-colors text-xs">
                <span>{{ item.recordKey }}</span>
                <app-lucide-icon
                  [name]="copiedKey() === 'rec_' + item.recordKey ? 'check' : 'copy'"
                  [size]="11"
                  [class]="copiedKey() === 'rec_' + item.recordKey ? 'text-emerald-600' : 'text-blue-400'"></app-lucide-icon>
              </button>
            </div>
            <button
              type="button"
              (click)="copyText(item.id, 'id_' + item.id)"
              [title]="copiedKey() === 'id_' + item.id ? 'Copied discrepancy ID' : 'Copy discrepancy ID'"
              class="inline-flex items-center gap-1.5 text-[11px] text-slate-500 hover:text-slate-800 hover:bg-slate-100 px-1.5 py-0.5 rounded font-mono cursor-pointer transition-colors w-fit">
              <span>Canonical Discrepancy ID: {{ item.id }}</span>
              <app-lucide-icon
                [name]="copiedKey() === 'id_' + item.id ? 'check' : 'copy'"
                [size]="11"
                [class]="copiedKey() === 'id_' + item.id ? 'text-emerald-600' : 'text-slate-400'"></app-lucide-icon>
            </button>
          </div>
        </div>

        <!-- Right: Badges -->
        <div class="flex items-center gap-2.5 flex-wrap">
          
          <!-- Proof Tier Badge -->
          <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold bg-slate-50 border border-slate-200 text-slate-700">
            <app-lucide-icon name="layers" [size]="13"></app-lucide-icon>
            <span>{{ formatProofTier(item.proofTier) }}</span>
          </span>

          <!-- Category Badge -->
          <span [ngClass]="getCategoryBadgeClasses(item.category)"
                class="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-bold uppercase tracking-wider border">
            <app-lucide-icon [name]="getCategoryIcon(item.category)" [size]="13"></app-lucide-icon>
            <span>{{ formatCategory(item.category) }}</span>
          </span>

          <!-- Reconciliation State Badge -->
          <span [ngClass]="getReconciliationBadgeClasses(item.reconciliationState)"
                class="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold border">
            <app-lucide-icon [name]="getReconciliationIcon(item.reconciliationState)" [size]="13"></app-lucide-icon>
            <span>{{ formatReconciliation(item.reconciliationState) }}</span>
          </span>

        </div>

      </div>

      <!-- Endpoint Routing & Topology Bar -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        <!-- Source Endpoint Card -->
        <div class="p-4 rounded-xl bg-blue-50/50 border border-blue-100 flex items-center justify-between gap-3">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-white border border-blue-200 flex items-center justify-center text-blue-600 shadow-2xs">
              <app-lucide-icon name="database" [size]="16"></app-lucide-icon>
            </div>
            <div class="flex flex-col">
              <div class="flex items-center gap-1.5">
                <span class="text-[10px] font-bold text-blue-600 uppercase tracking-wider">Source Endpoint</span>
                <span class="text-[10px] text-slate-400 font-mono">({{ item.sourceEndpoint.label }})</span>
              </div>
              <span class="text-xs font-bold text-slate-900">{{ item.sourceEndpoint.provider }}</span>
            </div>
          </div>
          <button
            type="button"
            (click)="copyText(item.sourceEndpoint.location, 'src_loc_' + item.id)"
            [title]="copiedKey() === 'src_loc_' + item.id ? 'Copied source location' : 'Copy source location'"
            class="inline-flex items-center gap-1.5 text-[11px] font-mono text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-50 px-2.5 py-1 rounded border border-blue-200 cursor-pointer transition-colors shadow-2xs">
            <span>{{ item.sourceEndpoint.location }}</span>
            <app-lucide-icon
              [name]="copiedKey() === 'src_loc_' + item.id ? 'check' : 'copy'"
              [size]="11"
              [class]="copiedKey() === 'src_loc_' + item.id ? 'text-emerald-600' : 'text-slate-400'"></app-lucide-icon>
          </button>
        </div>

        <!-- Target Endpoint Card -->
        <div class="p-4 rounded-xl bg-emerald-50/50 border border-emerald-100 flex items-center justify-between gap-3">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-white border border-emerald-200 flex items-center justify-center text-emerald-600 shadow-2xs">
              <app-lucide-icon name="database" [size]="16"></app-lucide-icon>
            </div>
            <div class="flex flex-col">
              <div class="flex items-center gap-1.5">
                <span class="text-[10px] font-bold text-emerald-600 uppercase tracking-wider">Target Endpoint</span>
                <span class="text-[10px] text-slate-400 font-mono">({{ item.targetEndpoint.label }})</span>
              </div>
              <span class="text-xs font-bold text-slate-900">{{ item.targetEndpoint.provider }}</span>
            </div>
          </div>
          <button
            type="button"
            (click)="copyText(item.targetEndpoint.location, 'tgt_loc_' + item.id)"
            [title]="copiedKey() === 'tgt_loc_' + item.id ? 'Copied target location' : 'Copy target location'"
            class="inline-flex items-center gap-1.5 text-[11px] font-mono text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-50 px-2.5 py-1 rounded border border-emerald-200 cursor-pointer transition-colors shadow-2xs">
            <span>{{ item.targetEndpoint.location }}</span>
            <app-lucide-icon
              [name]="copiedKey() === 'tgt_loc_' + item.id ? 'check' : 'copy'"
              [size]="11"
              [class]="copiedKey() === 'tgt_loc_' + item.id ? 'text-emerald-600' : 'text-slate-400'"></app-lucide-icon>
          </button>
        </div>

      </div>

      <!-- Difference Summary Alert Box -->
      <div class="p-4 rounded-xl bg-rose-50/70 border border-rose-200/80 flex items-start gap-3 text-xs text-rose-900">
        <app-lucide-icon name="info" [size]="16" class="text-rose-600 shrink-0 mt-0.5"></app-lucide-icon>
        <div class="flex flex-col gap-1 flex-1">
          <span class="font-bold text-rose-950">Divergence Finding Summary:</span>
          <p class="leading-relaxed text-rose-900 font-normal">{{ item.differenceSummary }}</p>
        </div>
      </div>

      <!-- Cardinality Summary View (For Tier 2 findings) -->
      @if (item.cardinalitySummary) {
        <div class="p-5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-4">
          <div class="flex items-center justify-between border-b border-slate-200 pb-3">
            <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Cardinality Count Evaluation</span>
            <span class="text-[11px] font-mono text-slate-500">Localization: {{ item.cardinalitySummary.localizationStatus }}</span>
          </div>

          <div class="grid grid-cols-3 gap-4 text-center">
            <div class="p-4 bg-white rounded-lg border border-slate-200">
              <span class="text-[10.5px] font-bold text-slate-500 block uppercase tracking-wider">Source Observed</span>
              <span class="text-lg font-bold font-mono text-slate-900 mt-1 block">{{ item.cardinalitySummary.sourceCount | number }}</span>
            </div>

            <div class="p-4 bg-white rounded-lg border border-slate-200">
              <span class="text-[10.5px] font-bold text-slate-500 block uppercase tracking-wider">Target Observed</span>
              <span class="text-lg font-bold font-mono text-slate-900 mt-1 block">{{ item.cardinalitySummary.targetCount | number }}</span>
            </div>

            <div class="p-4 bg-rose-50 rounded-lg border border-rose-200">
              <span class="text-[10.5px] font-bold text-rose-700 block uppercase tracking-wider">Difference Delta</span>
              <span class="text-lg font-bold font-mono text-rose-700 mt-1 block">{{ item.cardinalitySummary.delta }} rows</span>
            </div>
          </div>
        </div>
      }

      <!-- Fingerprint Summary View (For Tier 3 findings) -->
      @if (item.fingerprintSummary) {
        <div class="p-5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-4">
          <div class="flex items-center justify-between border-b border-slate-200 pb-3">
            <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Partition Merkle Hash Tree Comparison</span>
            <span class="text-[11px] font-mono text-slate-500">Localization: {{ item.fingerprintSummary.localizationStatus }}</span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div class="p-3.5 bg-white rounded-lg border border-slate-200 flex flex-col gap-1.5">
              <span class="text-[10.5px] font-bold text-blue-600 uppercase tracking-wider">Source Partition Hash</span>
              <span class="font-mono text-[11px] text-slate-800 break-all leading-relaxed">{{ item.fingerprintSummary.sourceHash }}</span>
            </div>

            <div class="p-3.5 bg-white rounded-lg border border-slate-200 flex flex-col gap-1.5">
              <span class="text-[10.5px] font-bold text-emerald-600 uppercase tracking-wider">Target Partition Hash</span>
              <span class="font-mono text-[11px] text-slate-800 break-all leading-relaxed">{{ item.fingerprintSummary.targetHash }}</span>
            </div>
          </div>

          @if (item.fingerprintSummary.hostileXorNote) {
            <p class="text-[11px] text-amber-900 bg-amber-50 border border-amber-200 p-3 rounded-lg leading-relaxed">
              {{ item.fingerprintSummary.hostileXorNote }}
            </p>
          }
        </div>
      }

      <!-- Structural Schema Diff View (For Tier 1 findings) -->
      @if (item.structuralSummary) {
        <div class="p-5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-4">
          <div class="flex items-center justify-between border-b border-slate-200 pb-3">
            <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Structural Schema Discrepancy</span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div class="p-3.5 bg-white rounded-lg border border-slate-200 flex flex-col gap-1.5">
              <span class="text-[10.5px] font-bold text-blue-600 uppercase tracking-wider">Source Definition</span>
              <span class="font-mono text-[11px] text-slate-800 leading-relaxed">{{ item.structuralSummary.sourceSchemaDetails }}</span>
            </div>

            <div class="p-3.5 bg-white rounded-lg border border-slate-200 flex flex-col gap-1.5">
              <span class="text-[10.5px] font-bold text-rose-600 uppercase tracking-wider">Target Definition</span>
              <span class="font-mono text-[11px] text-slate-800 leading-relaxed">{{ item.structuralSummary.targetSchemaDetails }}</span>
            </div>
          </div>
        </div>
      }

      <!-- Attribute-Level Comparison Table -->
      @if (item.attributes.length > 0) {
        <div class="flex flex-col gap-3">
          <div class="flex items-center justify-between flex-wrap gap-2">
            <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
              Attribute Logical Value Comparison ({{ item.attributes.length }} Attributes Compared)
            </h4>
            <span class="text-[11px] text-slate-500 font-mono">
              {{ store.showDifferencesOnly() ? 'Filtering: Differences Only' : 'Showing: All Compared Attributes' }}
            </span>
          </div>

          <app-discrepancies-attribute-diff
            [attributes]="item.attributes"
            [showDifferencesOnly]="store.showDifferencesOnly()" />
        </div>
      }

      <!-- Comparison Context & P7B Governance Cards -->
      <app-discrepancies-context-card [item]="item" />

    </section>
  `
})
export class DiscrepanciesInspectorComponent {
  @Input({ required: true }) item!: DiscrepancyItem;

  readonly store = inject(ValidationDiscrepanciesService);

  getCategoryBadgeClasses(cat: DiscrepancyCategory): string {
    switch (cat) {
      case 'VALUE_DIFFERENCE': return 'bg-rose-50 border-rose-200 text-rose-700';
      case 'MISSING_ON_TARGET': return 'bg-amber-50 border-amber-200 text-amber-700';
      case 'EXTRA_ON_TARGET': return 'bg-purple-50 border-purple-200 text-purple-700';
      case 'STRUCTURAL_DIFFERENCE': return 'bg-orange-50 border-orange-200 text-orange-700';
      case 'CARDINALITY_DIFFERENCE': return 'bg-blue-50 border-blue-200 text-blue-700';
      case 'PARTITION_FINGERPRINT': return 'bg-indigo-50 border-indigo-200 text-indigo-700';
      case 'UNRESOLVED_CORRESPONDENCE': return 'bg-yellow-50 border-yellow-200 text-yellow-800';
      case 'INCONCLUSIVE': return 'bg-slate-50 border-slate-200 text-slate-700';
    }
  }

  getCategoryIcon(cat: DiscrepancyCategory): string {
    switch (cat) {
      case 'VALUE_DIFFERENCE': return 'file-diff';
      case 'MISSING_ON_TARGET': return 'minus-square';
      case 'EXTRA_ON_TARGET': return 'plus-square';
      case 'STRUCTURAL_DIFFERENCE': return 'table-properties';
      case 'CARDINALITY_DIFFERENCE': return 'binary';
      case 'PARTITION_FINGERPRINT': return 'git-branch';
      case 'UNRESOLVED_CORRESPONDENCE': return 'help-circle';
      case 'INCONCLUSIVE': return 'alert-circle';
    }
  }

  formatCategory(cat: DiscrepancyCategory): string {
    switch (cat) {
      case 'VALUE_DIFFERENCE': return 'Value Difference';
      case 'MISSING_ON_TARGET': return 'Missing on Target';
      case 'EXTRA_ON_TARGET': return 'Extra on Target';
      case 'STRUCTURAL_DIFFERENCE': return 'Schema Difference';
      case 'CARDINALITY_DIFFERENCE': return 'Cardinality Difference';
      case 'PARTITION_FINGERPRINT': return 'Fingerprint Difference';
      case 'UNRESOLVED_CORRESPONDENCE': return 'Unresolved Mapping';
      case 'INCONCLUSIVE': return 'Inconclusive';
    }
  }

  formatProofTier(tier: DiscrepancyProofTier): string {
    switch (tier) {
      case 'TIER_1_STRUCTURAL': return 'Tier 1 — Structural';
      case 'TIER_2_CARDINALITY': return 'Tier 2 — Cardinality';
      case 'TIER_3_PARTITION': return 'Tier 3 — Partition';
      case 'TIER_4_ATTRIBUTE': return 'Tier 4 — Attribute';
    }
  }

  getReconciliationBadgeClasses(state: ReconciliationState): string {
    switch (state) {
      case 'UNRESOLVED': return 'bg-rose-50 border-rose-200 text-rose-700';
      case 'CONFIRMED_DISCREPANCY': return 'bg-red-50 border-red-200 text-red-800';
      case 'EXPECTED_DIFFERENCE': return 'bg-blue-50 border-blue-200 text-blue-700';
      case 'EXPLAINED_BY_TRANSFORMATION': return 'bg-emerald-50 border-emerald-200 text-emerald-800';
      case 'EXCLUDED_BY_SCOPE': return 'bg-slate-100 border-slate-200 text-slate-700';
      case 'INCONCLUSIVE': return 'bg-amber-50 border-amber-200 text-amber-800';
    }
  }

  copiedKey = signal<string | null>(null);

  copyText(val: string, key: string): void {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(val);
      this.copiedKey.set(key);
      setTimeout(() => {
        if (this.copiedKey() === key) {
          this.copiedKey.set(null);
        }
      }, 2000);
    }
  }

  getReconciliationIcon(state: ReconciliationState): string {
    switch (state) {
      case 'UNRESOLVED': return 'clock';
      case 'CONFIRMED_DISCREPANCY': return 'alert-triangle';
      case 'EXPECTED_DIFFERENCE': return 'check';
      case 'EXPLAINED_BY_TRANSFORMATION': return 'git-merge';
      case 'EXCLUDED_BY_SCOPE': return 'filter-x';
      case 'INCONCLUSIVE': return 'help-circle';
    }
  }

  formatReconciliation(state: ReconciliationState): string {
    switch (state) {
      case 'UNRESOLVED': return 'Unresolved';
      case 'CONFIRMED_DISCREPANCY': return 'Confirmed Discrepancy';
      case 'EXPECTED_DIFFERENCE': return 'Expected Difference';
      case 'EXPLAINED_BY_TRANSFORMATION': return 'Explained by Transformation';
      case 'EXCLUDED_BY_SCOPE': return 'Excluded by Scope';
      case 'INCONCLUSIVE': return 'Inconclusive';
    }
  }
}
