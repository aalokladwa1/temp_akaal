import { Component, Input, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DiscrepancyItem } from '../validation-discrepancies.models';
import { ValidationWorkstationService } from '../../validation-workstation.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-discrepancies-context-card',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
      
      <!-- Card 1: Comparison & Transformation Context -->
      <div class="bg-white border border-slate-200/80 rounded-xl p-5 lg:p-6 shadow-2xs flex flex-col justify-between gap-4">
        <div class="flex flex-col gap-3.5">
          <div class="flex items-center justify-between border-b border-slate-100 pb-3">
            <div class="flex items-center gap-2">
              <div class="w-6 h-6 rounded-md bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 shrink-0">
                <app-lucide-icon name="git-merge" [size]="13"></app-lucide-icon>
              </div>
              <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
                Comparison &amp; Mapping Context
              </h4>
            </div>
            <span class="text-[10.5px] font-semibold text-slate-600 bg-slate-50 border border-slate-200 px-2.5 py-0.5 rounded">
              {{ item.transformationContext?.ruleName || 'Canonical Pass-Through' }}
            </span>
          </div>

          <div class="grid grid-cols-2 gap-3.5 text-xs">
            <div>
              <span class="text-[10.5px] font-bold text-slate-500 block uppercase tracking-wider">Source Attribute</span>
              <span class="font-mono font-medium text-slate-900 mt-0.5 block">{{ item.transformationContext?.sourceAttributeMapped || item.affectedAttributes.join(', ') }}</span>
            </div>

            <div>
              <span class="text-[10.5px] font-bold text-slate-500 block uppercase tracking-wider">Target Attribute</span>
              <span class="font-mono font-medium text-slate-900 mt-0.5 block">{{ item.transformationContext?.targetAttributeMapped || item.affectedAttributes.join(', ') }}</span>
            </div>

            @if (item.transformationContext?.transformationType) {
              <div class="col-span-2">
                <span class="text-[10.5px] font-bold text-slate-500 block uppercase tracking-wider">Transformation Policy</span>
                <span class="font-mono text-blue-700 font-semibold mt-0.5 block">{{ item.transformationContext?.transformationType }}</span>
              </div>
            }

            @if (item.transformationContext?.filterPredicate) {
              <div class="col-span-2">
                <span class="text-[10.5px] font-bold text-slate-500 block uppercase tracking-wider">Migration Scope Filter</span>
                <span class="font-mono text-slate-700 bg-slate-50 border border-slate-200 px-2.5 py-1 rounded-lg block text-[11px] mt-1">
                  {{ item.transformationContext?.filterPredicate }}
                </span>
              </div>
            }

            @if (item.transformationContext?.dedupPolicy) {
              <div class="col-span-2">
                <span class="text-[10.5px] font-bold text-slate-500 block uppercase tracking-wider">Deduplication Policy</span>
                <span class="font-mono text-slate-700 bg-slate-50 border border-slate-200 px-2.5 py-1 rounded-lg block text-[11px] mt-1">
                  {{ item.transformationContext?.dedupPolicy }}
                </span>
              </div>
            }
          </div>
        </div>
      </div>

      <!-- Card 2: P7B Baseline & Governance Handoff -->
      <div class="bg-white border border-slate-200/80 rounded-xl p-5 lg:p-6 shadow-2xs flex flex-col justify-between gap-4">
        <div class="flex flex-col gap-3.5">
          <div class="flex items-center justify-between border-b border-slate-100 pb-3">
            <div class="flex items-center gap-2">
              <div class="w-6 h-6 rounded-md bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 shrink-0">
                <app-lucide-icon name="shield-check" [size]="13"></app-lucide-icon>
              </div>
              <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
                P7B Baseline &amp; Governance
              </h4>
            </div>
            
            @if (item.baselineContext) {
              <span
                [class.bg-emerald-50]="item.baselineContext.baselineStatus === 'VALID'"
                [class.text-emerald-800]="item.baselineContext.baselineStatus === 'VALID'"
                [class.border-emerald-200]="item.baselineContext.baselineStatus === 'VALID'"
                [class.bg-amber-50]="item.baselineContext.baselineStatus === 'STALE'"
                [class.text-amber-800]="item.baselineContext.baselineStatus === 'STALE'"
                [class.border-amber-200]="item.baselineContext.baselineStatus === 'STALE'"
                class="px-2.5 py-0.5 rounded text-[10.5px] font-bold uppercase tracking-wider border">
                {{ item.baselineContext.baselineStatus === 'VALID' ? 'Baseline Valid' : 'Baseline Drift' }}
              </span>
            }
          </div>

          <div class="flex flex-col gap-2.5 text-xs">
            <div class="flex items-center justify-between">
              <span class="text-slate-500 font-medium">Baseline Reference ID:</span>
              <span class="font-mono font-bold text-slate-900">{{ item.baselineContext?.baselineId || 'BSL-9981-FROZEN' }}</span>
            </div>

            <div class="flex items-center justify-between">
              <span class="text-slate-500 font-medium">Snapshot Timestamp:</span>
              <span class="font-mono text-slate-700">{{ item.baselineContext?.snapshotTimestamp || '2026-09-07T08:00:00Z' }}</span>
            </div>

            <p class="text-[11px] text-slate-500 leading-relaxed pt-1">
              Validation is strictly read-only and non-mutating. Any repair action requires a P7B Governed Repair Plan with dual-operator approval before target reconciliation.
            </p>
          </div>
        </div>

        <!-- Governed Repair Handoff Button -->
        <div class="pt-3 border-t border-slate-100 flex items-center justify-between">
          <span class="text-[11px] text-slate-500 font-medium">
            Governed Action:
          </span>
          <button
            type="button"
            (click)="navigateToRepair()"
            class="px-3.5 py-1.5 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 hover:bg-blue-100 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer shadow-2xs">
            <span>Review in Governed Repair Workspace</span>
            <app-lucide-icon name="arrow-right" [size]="13"></app-lucide-icon>
          </button>
        </div>

      </div>

    </div>
  `
})
export class DiscrepanciesContextCardComponent {
  @Input({ required: true }) item!: DiscrepancyItem;

  private readonly workstationService = inject(ValidationWorkstationService);

  navigateToRepair(): void {
    this.workstationService.setActiveTab('repair');
  }
}
