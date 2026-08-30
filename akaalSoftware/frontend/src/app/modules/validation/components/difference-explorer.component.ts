import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ValidationUiService } from '../../../core/services/validation-ui.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-difference-explorer',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 font-sans select-none text-xs">
      
      <!-- Sub-Tabs Switcher -->
      <div class="flex items-center gap-2 border-b border-slate-200 pb-px flex-wrap">
        <button
          type="button"
          (click)="vs.activeDifferenceTab.set('funnel')"
          class="px-4 py-2 rounded-t-xl font-bold border-b-2 transition-all cursor-pointer flex items-center gap-1.5"
          [class.border-blue-600]="vs.activeDifferenceTab() === 'funnel'"
          [class.text-blue-700]="vs.activeDifferenceTab() === 'funnel'"
          [class.bg-white]="vs.activeDifferenceTab() === 'funnel'"
          [class.border-transparent]="vs.activeDifferenceTab() !== 'funnel'"
          [class.text-slate-600]="vs.activeDifferenceTab() !== 'funnel'">
          <app-lucide-icon name="filter" [size]="13"></app-lucide-icon>
          <span>1. Difference Funnel</span>
        </button>

        <button
          type="button"
          (click)="vs.activeDifferenceTab.set('schema')"
          class="px-4 py-2 rounded-t-xl font-bold border-b-2 transition-all cursor-pointer flex items-center gap-1.5"
          [class.border-blue-600]="vs.activeDifferenceTab() === 'schema'"
          [class.text-blue-700]="vs.activeDifferenceTab() === 'schema'"
          [class.bg-white]="vs.activeDifferenceTab() === 'schema'"
          [class.border-transparent]="vs.activeDifferenceTab() !== 'schema'"
          [class.text-slate-600]="vs.activeDifferenceTab() !== 'schema'">
          <app-lucide-icon name="table-properties" [size]="13"></app-lucide-icon>
          <span>2. Schema Diff</span>
        </button>

        <button
          type="button"
          (click)="vs.activeDifferenceTab.set('heatmap')"
          class="px-4 py-2 rounded-t-xl font-bold border-b-2 transition-all cursor-pointer flex items-center gap-1.5"
          [class.border-blue-600]="vs.activeDifferenceTab() === 'heatmap'"
          [class.text-blue-700]="vs.activeDifferenceTab() === 'heatmap'"
          [class.bg-white]="vs.activeDifferenceTab() === 'heatmap'"
          [class.border-transparent]="vs.activeDifferenceTab() !== 'heatmap'"
          [class.text-slate-600]="vs.activeDifferenceTab() !== 'heatmap'">
          <app-lucide-icon name="grid-2x2" [size]="13"></app-lucide-icon>
          <span>3. Partition Heatmap</span>
        </button>

        <button
          type="button"
          (click)="vs.activeDifferenceTab.set('merkle')"
          class="px-4 py-2 rounded-t-xl font-bold border-b-2 transition-all cursor-pointer flex items-center gap-1.5"
          [class.border-blue-600]="vs.activeDifferenceTab() === 'merkle'"
          [class.text-blue-700]="vs.activeDifferenceTab() === 'merkle'"
          [class.bg-white]="vs.activeDifferenceTab() === 'merkle'"
          [class.border-transparent]="vs.activeDifferenceTab() !== 'merkle'"
          [class.text-slate-600]="vs.activeDifferenceTab() !== 'merkle'">
          <app-lucide-icon name="git-branch" [size]="13"></app-lucide-icon>
          <span>4. Merkle Tree</span>
        </button>

        <button
          type="button"
          (click)="vs.activeDifferenceTab.set('rows')"
          class="px-4 py-2 rounded-t-xl font-bold border-b-2 transition-all cursor-pointer flex items-center gap-1.5"
          [class.border-blue-600]="vs.activeDifferenceTab() === 'rows'"
          [class.text-blue-700]="vs.activeDifferenceTab() === 'rows'"
          [class.bg-white]="vs.activeDifferenceTab() === 'rows'"
          [class.border-transparent]="vs.activeDifferenceTab() !== 'rows'"
          [class.text-slate-600]="vs.activeDifferenceTab() !== 'rows'">
          <app-lucide-icon name="file-diff" [size]="13"></app-lucide-icon>
          <span>5. Disputed Rows</span>
        </button>
      </div>

      <!-- Tab 1: Funnel -->
      @if (vs.activeDifferenceTab() === 'funnel') {
        <div class="grid grid-cols-1 sm:grid-cols-5 gap-3">
          @for (lvl of vs.differenceFunnel(); track lvl.label) {
            <div class="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-3">
              <span class="text-[10px] font-bold text-slate-500 uppercase">{{ lvl.label }}</span>
              <div class="flex flex-col">
                <span class="text-base font-bold font-mono text-slate-900">{{ lvl.matchedCount | number }} / {{ lvl.totalCount | number }} {{ lvl.unit }}</span>
                <span class="text-[11px] font-bold" [class.text-emerald-700]="lvl.mismatchedCount === 0" [class.text-rose-700]="lvl.mismatchedCount > 0">
                  {{ lvl.mismatchedCount > 0 ? (lvl.mismatchedCount + ' Divergent') : '100% Synced' }}
                </span>
              </div>
            </div>
          }
        </div>
      }

      <!-- Tab 2: Schema Diff -->
      @if (vs.activeDifferenceTab() === 'schema') {
        <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-3">
          <span class="font-bold text-slate-900">Schema Type Correspondence</span>
          <div class="flex flex-col gap-2">
            @for (item of vs.schemaDiff(); track item.objectName) {
              <div class="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
                <div class="flex flex-col">
                  <span class="font-mono font-bold text-slate-900">{{ item.objectName }}</span>
                  <span class="text-[11px] text-slate-500">{{ item.sourceType }} &rarr; {{ item.targetType }}</span>
                </div>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">{{ item.status }}</span>
              </div>
            }
          </div>
        </div>
      }

      <!-- Tab 3: Partition Heatmap -->
      @if (vs.activeDifferenceTab() === 'heatmap') {
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
          @for (cell of vs.partitionHeatmap(); track cell.partitionId) {
            <div
              class="p-3.5 rounded-xl border flex flex-col justify-between gap-2"
              [class.bg-emerald-50]="cell.status === 'IDENTICAL'"
              [class.border-emerald-200]="cell.status === 'IDENTICAL'"
              [class.bg-amber-50]="cell.status !== 'IDENTICAL'"
              [class.border-amber-300]="cell.status !== 'IDENTICAL'">
              <div class="flex items-center justify-between">
                <span class="font-bold font-mono text-slate-900">{{ cell.partitionId }}</span>
                <span class="text-[10px] font-bold" [class.text-emerald-700]="cell.status === 'IDENTICAL'" [class.text-amber-800]="cell.status !== 'IDENTICAL'">
                  {{ cell.divergentRows }} Mismatches
                </span>
              </div>
              <div class="text-[10px] font-mono text-slate-500">
                <span>Range: {{ cell.keyRange }}</span>
              </div>
            </div>
          }
        </div>
      }

      <!-- Tab 4: Merkle Tree -->
      @if (vs.activeDifferenceTab() === 'merkle') {
        <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-3">
          <span class="font-bold text-slate-900">Hierarchical XXHash64 Merkle Tree</span>
          <div class="p-3.5 rounded-xl bg-slate-900 text-slate-200 font-mono text-xs max-h-60 overflow-y-auto">
            <p>ROOT: {{ vs.merkleTree().range }} &bull; Source Hash: <span class="text-blue-400">{{ vs.merkleTree().sourceHash }}</span> | Target: <span class="text-rose-400">{{ vs.merkleTree().targetHash }}</span> (MISMATCH)</p>
            <p class="pl-4 pt-1">&boxur;&bull; Left Branch (1..10000000): Mismatch localized to leaf-p3 (5000001..7500000)</p>
            <p class="pl-4">&boxur;&bull; Right Branch (10000001..18600000): Identical (100% matched)</p>
          </div>
        </div>
      }

      <!-- Tab 5: Disputed Rows -->
      @if (vs.activeDifferenceTab() === 'rows') {
        <div class="flex flex-col gap-3">
          @for (row of vs.disputedRows(); track row.primaryKey) {
            <div class="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-2 font-mono">
              <div class="flex items-center justify-between">
                <span class="font-bold text-slate-900">PK: {{ row.primaryKey }} &bull; {{ row.tableName }}</span>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">{{ row.differenceType }}</span>
              </div>
              <div class="grid grid-cols-2 gap-3 pt-2">
                <div class="p-2.5 rounded bg-slate-50 border border-slate-200">
                  <span class="font-bold text-slate-600 block text-[10px] pb-1">Source Record:</span>
                  <pre class="text-[11px] text-slate-800">{{ row.sourceFields | json }}</pre>
                </div>
                <div class="p-2.5 rounded bg-slate-50 border border-slate-200">
                  <span class="font-bold text-blue-700 block text-[10px] pb-1">Target Record:</span>
                  <pre class="text-[11px] text-slate-800">{{ row.targetFields | json }}</pre>
                </div>
              </div>
            </div>
          }
        </div>
      }

    </div>
  `
})
export class DifferenceExplorerComponent {
  public vs = inject(ValidationUiService);
}
