import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, ActivatedRoute } from '@angular/router';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ValidationUiService } from '../../../core/services/validation-ui.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { StatusBadgeComponent } from '../../migration/components/status-badge.component';

@Component({
  selector: 'app-validation-mission-control',
  standalone: true,
  imports: [CommonModule, RouterLink, TableModule, TagModule, LucideIconComponent, StatusBadgeComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto pb-20 font-sans select-none animate-in fade-in duration-150">
      
      <!-- Top Workspace Header (38) -->
      <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-5">
        <div class="flex items-center justify-between gap-4 flex-wrap pb-3 border-b border-slate-100">
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-2">
              <a routerLink="/migration/validation" class="text-xs font-semibold text-blue-600 hover:underline">Validation Operations</a>
              <span class="text-slate-300">/</span>
              <span class="text-xs font-semibold text-slate-700">Workspace</span>
            </div>
            <div class="flex items-center gap-3">
              <h1 class="text-xl font-bold font-heading text-slate-900">{{ vs.activeValidation()?.name }}</h1>
              <app-status-badge [verdict]="vs.activeValidation()?.verdict"></app-status-badge>
            </div>
          </div>

          <button
            type="button"
            (click)="activeTab.set('repair')"
            class="h-9 px-4 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold shadow-xs transition-colors cursor-pointer flex items-center gap-1.5">
            <app-lucide-icon name="wrench" [size]="14"></app-lucide-icon>
            <span>Governed Repair Plan</span>
          </button>
        </div>

        <!-- 7 Tab Horizontal Stepper/Switcher (38) -->
        <div class="flex items-center gap-2 overflow-x-auto pb-1">
          @for (tab of tabs; track tab.id) {
            <button
              type="button"
              (click)="activeTab.set(tab.id)"
              class="px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer whitespace-nowrap"
              [class.bg-blue-600]="activeTab() === tab.id"
              [class.text-white]="activeTab() === tab.id"
              [class.bg-slate-100]="activeTab() !== tab.id"
              [class.text-slate-700]="activeTab() !== tab.id">
              {{ tab.label }}
            </button>
          }
        </div>
      </div>

      <!-- Tab Content Area -->
      @switch (activeTab()) {
        
        <!-- Tab 1: Overview -->
        @case ('overview') {
          <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
              <span class="text-[10px] font-bold text-slate-500 uppercase">Rows Evaluated</span>
              <span class="text-2xl font-bold text-slate-900 font-mono">18,600,000</span>
            </div>
            <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
              <span class="text-[10px] font-bold text-rose-700 uppercase">Disputed Rows</span>
              <span class="text-2xl font-bold text-rose-700 font-mono">18</span>
            </div>
            <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
              <span class="text-[10px] font-bold text-slate-500 uppercase">Missing In Target</span>
              <span class="text-2xl font-bold text-slate-900 font-mono">14</span>
            </div>
            <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1">
              <span class="text-[10px] font-bold text-slate-500 uppercase">Duration</span>
              <span class="text-2xl font-bold text-slate-900 font-mono">2m 08s</span>
            </div>
          </div>
        }

        <!-- Tab 3: Differences Explorer (Funnel, Schema, Heatmap, Merkle, Disputed Rows) -->
        @case ('differences') {
          <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-5">
            <h2 class="text-base font-bold text-slate-900">Five-Level Difference Localization Funnel</h2>

            <!-- 5-Level Funnel Visualization (41) -->
            <div class="grid grid-cols-1 sm:grid-cols-5 gap-3">
              @for (lvl of vs.differenceFunnel(); track lvl.label) {
                <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col justify-between gap-2">
                  <span class="text-[10px] font-bold text-slate-500 uppercase">{{ lvl.label }}</span>
                  <div class="flex flex-col">
                    <span class="text-base font-bold font-mono text-slate-900">{{ lvl.totalCount | number }} {{ lvl.unit }}</span>
                    <span class="text-[11px] font-bold" [class.text-emerald-700]="lvl.mismatchedCount === 0" [class.text-rose-700]="lvl.mismatchedCount > 0">
                      {{ lvl.mismatchedCount > 0 ? (lvl.mismatchedCount + ' divergent') : '100% Match' }}
                    </span>
                  </div>
                </div>
              }
            </div>

            <!-- Disputed Rows Side-by-Side Diff Table (45) -->
            <div class="flex flex-col gap-3 pt-3 border-t border-slate-100">
              <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider">Side-by-Side Disputed Row Diffs</h3>
              
              <div class="flex flex-col gap-3">
                @for (row of vs.disputedRows(); track row.primaryKey) {
                  <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-2 font-mono text-xs">
                    <div class="flex items-center justify-between">
                      <span class="font-bold text-slate-900">PK: {{ row.primaryKey }} &bull; {{ row.tableName }}</span>
                      <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">{{ row.differenceType }}</span>
                    </div>

                    <div class="grid grid-cols-2 gap-3 pt-2">
                      <div class="p-2.5 rounded bg-white border border-slate-200">
                        <span class="font-bold text-slate-700 text-[10px] block pb-1">Source (Oracle):</span>
                        <pre class="text-[11px] text-slate-900">{{ row.sourceFields | json }}</pre>
                      </div>
                      <div class="p-2.5 rounded bg-white border border-slate-200">
                        <span class="font-bold text-blue-700 text-[10px] block pb-1">Target (PostgreSQL):</span>
                        <pre class="text-[11px] text-slate-900">{{ row.targetFields | json }}</pre>
                      </div>
                    </div>
                  </div>
                }
              </div>
            </div>

          </div>
        }

        <!-- Tab 5: Governed Repair (47) -->
        @case ('repair') {
          <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-5">
            <div class="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <h2 class="text-base font-bold text-slate-900">Governed Target Mutation Repair Plan</h2>
                <p class="text-xs text-slate-500 font-medium">Authoritative target mutation boundary with mandatory revalidation requirement.</p>
              </div>
              <span class="px-2.5 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200">
                APPROVAL PENDING
              </span>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-medium">
              <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-1">
                <span class="text-slate-500">Proposed Inserts:</span>
                <span class="font-bold text-slate-900 text-lg">14 Rows</span>
              </div>
              <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-1">
                <span class="text-slate-500">Proposed Updates:</span>
                <span class="font-bold text-slate-900 text-lg">4 Rows</span>
              </div>
              <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-1">
                <span class="text-slate-500">Proposed Deletes:</span>
                <span class="font-bold text-slate-900 text-lg">0 Rows</span>
              </div>
            </div>

            <div class="p-4 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-800 flex items-center justify-between">
              <span>Mandatory Revalidation Required: Execution of repair will trigger an automatic verification pass to re-evaluate parity.</span>
              <button type="button" class="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs cursor-pointer shadow-xs">
                Authorize Repair Plan
              </button>
            </div>
          </div>
        }

        @default {
          <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-2">
            <h3 class="text-sm font-bold text-slate-900">Workspace Tab View</h3>
            <p class="text-xs text-slate-500">Detailed verification telemetry and comparison matrices.</p>
          </div>
        }

      }

    </div>
  `
})
export class ValidationMissionControlComponent {
  public vs = inject(ValidationUiService);
  public activeTab = signal<string>('differences');

  public tabs = [
    { id: 'overview', label: '1. Overview' },
    { id: 'comparison', label: '2. Comparison Matrix' },
    { id: 'differences', label: '3. Differences Explorer' },
    { id: 'reconciliation', label: '4. Reconciliation' },
    { id: 'repair', label: '5. Governed Repair' },
    { id: 'evidence', label: '6. Evidence Manifest' },
    { id: 'history', label: '7. History & Lineage' }
  ];
}
