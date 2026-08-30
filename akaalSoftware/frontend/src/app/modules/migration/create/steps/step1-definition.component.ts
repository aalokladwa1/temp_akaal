import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MigrationUiService } from '../../../../core/services/migration-ui.service';
import { MigrationDevFixturesAdapter } from '../../../../core/fixtures/migration-dev-fixtures.adapter';
import { MigrationModeDefinition } from '../../../../core/models/migration-view.models';

@Component({
  selector: 'app-step1-definition',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="flex flex-col gap-4 font-sans select-none animate-in fade-in duration-150 text-xs">
      
      <!-- =============================================================== -->
      <!-- CARD 1: MIGRATION DETAILS                                       -->
      <!-- =============================================================== -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200/90 shadow-2xs flex flex-col gap-4">
        
        <div class="flex items-center justify-between pb-2.5 border-b border-slate-100">
          <span class="text-xs font-bold text-slate-900 uppercase tracking-wider">1. MIGRATION DETAILS</span>
          <span class="text-[11px] text-slate-500 font-medium">Pipeline Identity &amp; Environment</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-3.5">
          
          <!-- Migration Name (col-span 1 or 2) -->
          <div class="flex flex-col gap-1 md:col-span-1">
            <label class="font-bold text-slate-800 text-xs">
              Migration Name <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [ngModel]="ms.wizardDraft().name"
              (ngModelChange)="ms.updateDraft({ name: $event })"
              placeholder="e.g. Core Banking Migration"
              class="h-9 px-3 rounded-xl bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all" />
          </div>

          <!-- Project -->
          <div class="flex flex-col gap-1 md:col-span-1">
            <label class="font-bold text-slate-800 text-xs">Project</label>
            <select
              [ngModel]="ms.wizardDraft().projectId || ''"
              (ngModelChange)="ms.updateDraft({ projectId: $event || undefined })"
              class="h-9 px-3 rounded-xl bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 cursor-pointer">
              <option value="">Independent (No Project)</option>
              <option value="proj-01">Core Banking Modernization</option>
              <option value="proj-02">Analytics Warehouse Consolidation</option>
              <option value="proj-03">Legacy Decommissioning</option>
            </select>
          </div>

          <!-- Environment -->
          <div class="flex flex-col gap-1 md:col-span-1">
            <label class="font-bold text-slate-800 text-xs">
              Environment <span class="text-rose-500">*</span>
            </label>
            <select
              [ngModel]="ms.wizardDraft().environment"
              (ngModelChange)="ms.updateDraft({ environment: $event })"
              class="h-9 px-3 rounded-xl bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 cursor-pointer">
              @for (env of environments; track env.id) {
                <option [value]="env.id">{{ env.label }}</option>
              }
            </select>
          </div>

          <!-- Description (Full Width) -->
          <div class="flex flex-col gap-1 md:col-span-3">
            <label class="font-bold text-slate-800 text-xs">Description</label>
            <input
              type="text"
              [ngModel]="ms.wizardDraft().description"
              (ngModelChange)="ms.updateDraft({ description: $event })"
              placeholder="Transactional core migration from on-prem Oracle RAC to PostgreSQL..."
              class="h-9 px-3 rounded-xl bg-slate-50 border border-slate-200 text-xs font-medium text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all" />
          </div>

        </div>

      </div>

      <!-- =============================================================== -->
      <!-- CARD 2: EXECUTION MODE (CLEAN COMPACT 2-COLUMN GRID)            -->
      <!-- =============================================================== -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200/90 shadow-2xs flex flex-col gap-3">
        
        <div class="flex items-center justify-between pb-2 border-b border-slate-100">
          <span class="text-xs font-bold text-slate-900 uppercase tracking-wider">2. EXECUTION MODE</span>
          <span class="text-[11px] text-slate-500 font-medium">Select 1 of 7 Canonical Strategies</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-2.5">
          @for (m of modes; track m.id; let last = $last) {
            <div
              (click)="ms.updateWizardMode(m.id)"
              class="p-3 rounded-xl border-2 cursor-pointer transition-all flex items-center justify-between gap-3"
              [class.md:col-span-2]="last"
              [class.border-blue-600]="ms.wizardDraft().mode === m.id"
              [class.bg-blue-50]="ms.wizardDraft().mode === m.id"
              [class.shadow-2xs]="ms.wizardDraft().mode === m.id"
              [class.border-slate-200]="ms.wizardDraft().mode !== m.id"
              [class.bg-white]="ms.wizardDraft().mode !== m.id"
              [class.hover:border-slate-300]="ms.wizardDraft().mode !== m.id"
              [class.hover:bg-slate-50]="ms.wizardDraft().mode !== m.id">
              
              <div class="flex items-center gap-3 min-w-0">
                <!-- Radio Dot -->
                <div
                  class="w-4 h-4 rounded-full border-2 flex items-center justify-center shrink-0"
                  [class.border-blue-600]="ms.wizardDraft().mode === m.id"
                  [class.bg-blue-600]="ms.wizardDraft().mode === m.id"
                  [class.border-slate-300]="ms.wizardDraft().mode !== m.id">
                  @if (ms.wizardDraft().mode === m.id) {
                    <div class="w-1.5 h-1.5 rounded-full bg-white"></div>
                  }
                </div>

                <!-- Title & Summary -->
                <div class="flex flex-col min-w-0">
                  <span class="font-bold text-slate-900 text-xs truncate">{{ m.title }}</span>
                  <span class="text-slate-600 text-[11px] font-normal truncate">{{ m.shortDesc }}</span>
                </div>
              </div>

              <span class="px-2 py-0.5 rounded text-[10px] font-bold shrink-0"
                [class.bg-blue-100]="ms.wizardDraft().mode === m.id"
                [class.text-blue-800]="ms.wizardDraft().mode === m.id"
                [class.bg-slate-100]="ms.wizardDraft().mode !== m.id"
                [class.text-slate-600]="ms.wizardDraft().mode !== m.id">
                {{ m.badge }}
              </span>

            </div>
          }
        </div>

      </div>

    </div>
  `
})
export class Step1DefinitionComponent {
  public ms = inject(MigrationUiService);
  private fixtures = new MigrationDevFixturesAdapter();

  public modes: MigrationModeDefinition[] = this.fixtures.getExecutionModes();

  public environments = [
    { id: 'Production', label: 'Production' },
    { id: 'Staging', label: 'Staging' },
    { id: 'Development', label: 'Development' }
  ];
}
