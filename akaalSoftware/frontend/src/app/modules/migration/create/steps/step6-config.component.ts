import { Component, inject, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MigrationUiService } from '../../../../core/services/migration-ui.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ConfigDomainGroup, ConfigFieldDescriptor, BasicPerformancePreset } from '../../../../core/models/migration-view.models';

@Component({
  selector: 'app-step6-config',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 animate-in fade-in duration-150 text-xs select-none">
      
      <!-- Header -->
      <div class="flex items-center justify-between pb-2 border-b border-slate-200">
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center font-bold">
            <app-lucide-icon name="sliders" [size]="16"></app-lucide-icon>
          </div>
          <div>
            <h2 class="text-base font-bold text-slate-900">Step 6 &bull; ENTERPRISE CONFIGURATION CENTER</h2>
            <p class="text-xs text-slate-500 font-medium">Mode-adaptive configuration workbench. Fine-tune workers, memory budgets, checkpoints, and CDC.</p>
          </div>
        </div>

        <!-- Mode Toggle: Basic vs Advanced -->
        <div class="flex items-center gap-2 p-1 rounded-xl bg-slate-100/80 border border-slate-200">
          <button
            type="button"
            (click)="isAdvanced.set(false)"
            class="h-7 px-3 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5"
            [class.bg-white]="!isAdvanced()"
            [class.text-blue-700]="!isAdvanced()"
            [class.shadow-2xs]="!isAdvanced()"
            [class.text-slate-600]="isAdvanced()">
            <span>Basic Mode</span>
          </button>

          <button
            type="button"
            (click)="isAdvanced.set(true)"
            class="h-7 px-3 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5"
            [class.bg-white]="isAdvanced()"
            [class.text-blue-700]="isAdvanced()"
            [class.shadow-2xs]="isAdvanced()"
            [class.text-slate-600]="!isAdvanced()">
            <span>Advanced Workbench</span>
          </button>
        </div>
      </div>

      <!-- =============================================================== -->
      <!-- BASIC CONFIGURATION MODE                                        -->
      <!-- =============================================================== -->
      @if (!isAdvanced()) {
        <div class="grid grid-cols-1 md:grid-cols-2 gap-5 p-5 rounded-xl bg-white border border-slate-200/90 shadow-2xs">
          
          <div class="flex flex-col gap-1 pb-2 border-b border-slate-100 md:col-span-2">
            <span class="font-bold text-slate-900 uppercase tracking-wider text-[11px]">High-Level Performance &amp; Durability Presets</span>
            <span class="text-[11px] text-slate-500 font-medium">Automatically computes balanced worker threads, ring buffers, and commit batch sizes.</span>
          </div>

          <!-- Performance Preset -->
          <div class="flex flex-col gap-2 md:col-span-2">
            <label class="font-bold text-slate-800 text-xs">Performance &amp; IOPS Preset</label>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
              @for (preset of presets; track preset.id) {
                <div
                  (click)="selectPreset(preset.id)"
                  class="p-3.5 rounded-xl border-2 cursor-pointer transition-all flex flex-col justify-between gap-2"
                  [class.border-blue-600]="basicView().performancePreset === preset.id"
                  [class.bg-blue-50]="basicView().performancePreset === preset.id"
                  [class.border-slate-200]="basicView().performancePreset !== preset.id"
                  [class.bg-white]="basicView().performancePreset !== preset.id">
                  
                  <div class="flex items-center justify-between">
                    <span class="font-bold text-slate-900 text-xs">{{ preset.label }}</span>
                    <span class="px-1.5 py-0.5 rounded text-[10px] font-bold"
                      [class.bg-blue-100]="basicView().performancePreset === preset.id"
                      [class.text-blue-800]="basicView().performancePreset === preset.id"
                      [class.bg-slate-100]="basicView().performancePreset !== preset.id"
                      [class.text-slate-600]="basicView().performancePreset !== preset.id">
                      {{ preset.workers }} Workers
                    </span>
                  </div>

                  <p class="text-[11px] text-slate-600 leading-relaxed font-normal">{{ preset.desc }}</p>
                </div>
              }
            </div>
          </div>

          <!-- Durability & Buffer Headroom -->
          <div class="flex flex-col gap-1.5">
            <label class="font-bold text-slate-800 text-xs">Durability &amp; Spill Headroom</label>
            <select
              [ngModel]="basicView().durabilityLevel"
              (ngModelChange)="updateBasicField('durabilityLevel', $event)"
              class="h-9 px-3 rounded-lg bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-900">
              <option value="STANDARD">Standard WAL Journaling (10 GB Spill Quota)</option>
              <option value="MAXIMUM">Maximum Durability &bull; Synchronous Commit (50 GB Spool)</option>
            </select>
          </div>

          <!-- Validation Depth -->
          <div class="flex flex-col gap-1.5">
            <label class="font-bold text-slate-800 text-xs">Continuous Validation Depth</label>
            <select
              [ngModel]="basicView().validationDepth"
              (ngModelChange)="updateBasicField('validationDepth', $event)"
              class="h-9 px-3 rounded-lg bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-900">
              <option value="STANDARD">Standard Checksum Sampling (10% sample)</option>
              <option value="QUICK">Quick Count &amp; Aggregate Check</option>
              <option value="DEEP">Deep Merkle Tree Row-By-Row Verification (100% full scan)</option>
            </select>
          </div>

          <!-- Cutover Readiness Target (Adaptive: only shown if continuous sync) -->
          @if (isContinuousSyncMode()) {
            <div class="flex flex-col gap-1.5 md:col-span-2 p-3.5 rounded-lg bg-blue-50/50 border border-blue-200">
              <label class="font-bold text-blue-950 text-xs">CDC Cutover Replication Lag Objective (Target: &lt; 500ms)</label>
              <span class="text-[11px] text-slate-600">Threshold that triggers cutover eligibility and enables maker-checker sign-off gate.</span>
              <div class="flex items-center gap-3 pt-1">
                <input
                  type="number"
                  [ngModel]="basicView().cdcLagObjectiveMs || 500"
                  (ngModelChange)="updateBasicField('cdcLagObjectiveMs', $event)"
                  class="h-8 px-3 w-32 rounded-md bg-white border border-slate-200 text-xs font-semibold font-mono text-slate-900" />
                <span class="text-xs text-slate-500 font-medium">milliseconds of acceptable target lag</span>
              </div>
            </div>
          }

        </div>
      }

      <!-- =============================================================== -->
      <!-- ADVANCED CONFIGURATION WORKBENCH (3-PANE WORKBENCH)             -->
      <!-- =============================================================== -->
      @if (isAdvanced()) {
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          
          <!-- LEFT (25%): Domain Navigation -->
          <div class="lg:col-span-3 flex flex-col gap-2 p-4 rounded-xl bg-white border border-slate-200/90 shadow-2xs">
            <div class="pb-2 border-b border-slate-100 flex items-center justify-between">
              <span class="font-bold text-slate-900 uppercase tracking-wider text-[11px]">Configuration Domains</span>
              <span class="text-[10px] font-bold text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded font-mono">{{ activeDomains().length }} Active</span>
            </div>

            <div class="flex flex-col gap-1 max-h-[500px] overflow-y-auto pr-1">
              @for (domain of activeDomains(); track domain.id) {
                <button
                  type="button"
                  (click)="selectedDomainId = domain.id"
                  class="p-2.5 rounded-lg border text-left flex flex-col gap-0.5 transition-all cursor-pointer"
                  [class.border-blue-600]="selectedDomainId === domain.id"
                  [class.bg-blue-50]="selectedDomainId === domain.id"
                  [class.border-slate-200]="selectedDomainId !== domain.id"
                  [class.bg-white]="selectedDomainId !== domain.id">
                  <div class="flex items-center justify-between">
                    <span class="font-bold text-xs" [class.text-blue-900]="selectedDomainId === domain.id" [class.text-slate-900]="selectedDomainId !== domain.id">
                      {{ domain.id }}. {{ domain.name }}
                    </span>
                  </div>
                  <span class="text-[10.5px] text-slate-500 truncate">{{ domain.fields.length }} parameters</span>
                </button>
              }
            </div>
          </div>

          <!-- CENTER (50%): Selected Domain Configuration Editor -->
          <div class="lg:col-span-6 flex flex-col gap-4 p-5 rounded-xl bg-white border border-slate-200/90 shadow-2xs">
            
            <div class="flex items-center justify-between pb-3 border-b border-slate-100">
              <div class="flex flex-col">
                <span class="font-bold text-slate-900 text-xs">Domain {{ selectedDomain()?.id }}: {{ selectedDomain()?.name }}</span>
                <span class="text-[11px] text-slate-500 font-medium">{{ selectedDomain()?.description }}</span>
              </div>
            </div>

            <div class="flex flex-col gap-4">
              @for (field of selectedDomain()?.fields; track field.id) {
                <div class="flex flex-col gap-1.5 p-3 rounded-lg bg-slate-50 border border-slate-200/80">
                  <div class="flex items-center justify-between">
                    <label class="font-bold text-slate-800 text-xs">{{ field.label }}</label>
                    <span class="text-[10px] font-mono font-semibold text-slate-500">Scope: {{ field.scope }}</span>
                  </div>

                  <p class="text-[11px] text-slate-600 font-normal leading-relaxed">{{ field.description }}</p>

                  <!-- Type-Safe Inputs -->
                  @switch (field.type) {
                    @case ('number') {
                      <input
                        type="number"
                        [ngModel]="getFieldEffectiveValue(field)"
                        (ngModelChange)="setFieldOverride(field.id, $event)"
                        class="h-8 px-3 rounded-md bg-white border border-slate-200 text-xs font-semibold font-mono text-slate-900 w-48 focus:outline-none focus:ring-1 focus:ring-blue-500" />
                    }
                    @case ('select') {
                      <select
                        [ngModel]="getFieldEffectiveValue(field)"
                        (ngModelChange)="setFieldOverride(field.id, $event)"
                        class="h-8 px-3 rounded-md bg-white border border-slate-200 text-xs font-semibold text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500">
                        @for (opt of field.options; track opt.value) {
                          <option [value]="opt.value">{{ opt.label }}</option>
                        }
                      </select>
                    }
                    @case ('boolean') {
                      <label class="flex items-center gap-2 cursor-pointer pt-1">
                        <input
                          type="checkbox"
                          [ngModel]="getFieldEffectiveValue(field)"
                          (ngModelChange)="setFieldOverride(field.id, $event)"
                          class="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 cursor-pointer" />
                        <span class="font-semibold text-slate-800 text-xs">Enable setting</span>
                      </label>
                    }
                    @case ('string') {
                      <input
                        type="text"
                        [ngModel]="getFieldEffectiveValue(field)"
                        (ngModelChange)="setFieldOverride(field.id, $event)"
                        class="h-8 px-3 rounded-md bg-white border border-slate-200 text-xs font-semibold font-mono text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500" />
                    }
                  }

                  @if (field.recommendation) {
                    <div class="text-[10.5px] text-blue-700 font-medium flex items-center gap-1 pt-1">
                      <app-lucide-icon name="info" [size]="11"></app-lucide-icon>
                      <span>Recommendation: {{ field.recommendation }}</span>
                    </div>
                  }
                </div>
              }
            </div>

          </div>

          <!-- RIGHT (25%): Effective Value, Provenance & Warnings -->
          <div class="lg:col-span-3 flex flex-col gap-3 p-4 rounded-xl bg-white border border-slate-200/90 shadow-2xs">
            <div class="pb-2 border-b border-slate-100 flex items-center justify-between">
              <span class="font-bold text-slate-900 uppercase tracking-wider text-[11px]">Provenance &amp; Impact</span>
              <span class="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">Resolved</span>
            </div>

            <div class="flex flex-col gap-2.5 text-[11.5px]">
              <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-1">
                <span class="text-slate-500 text-[10.5px] font-bold uppercase">Configuration Scope</span>
                <span class="font-bold text-slate-900 font-mono">Scope: MIGRATION</span>
                <span class="text-slate-500 text-[10.5px]">Inherits workspace defaults with user overrides.</span>
              </div>

              <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-1">
                <span class="text-slate-500 text-[10.5px] font-bold uppercase">Hot Reloadability</span>
                <span class="font-bold text-emerald-700 font-mono">Zero-Downtime Hot Reload</span>
                <span class="text-slate-500 text-[10.5px]">Engine applies updates without worker restart.</span>
              </div>

              <div class="p-2.5 rounded-lg bg-blue-50/70 border border-blue-200 flex flex-col gap-1">
                <span class="text-blue-900 text-[10.5px] font-bold uppercase">Mode Adaptation</span>
                <span class="font-semibold text-blue-950">
                  Mode: {{ ms.wizardDraft().mode }}
                </span>
                <span class="text-blue-800 text-[10.5px]">Irrelevant parameters suppressed from compilation catalog.</span>
              </div>
            </div>
          </div>

        </div>
      }

    </div>
  `
})
export class Step6ConfigComponent {
  public ms = inject(MigrationUiService);

  public isAdvanced = signal<boolean>(false);
  public selectedDomainId = 'A';

  public presets: { id: BasicPerformancePreset; label: string; workers: number; desc: string }[] = [
    { id: 'CONSERVATIVE', label: 'Conservative', workers: 4, desc: 'Low IOPS footprint for shared production servers without disrupting OLTP transactions.' },
    { id: 'BALANCED', label: 'Balanced (Standard)', workers: 8, desc: 'Recommended baseline balancing high data transfer speed with database connection limits.' },
    { id: 'HIGH_THROUGHPUT', label: 'High Throughput', workers: 16, desc: 'Aggressive parallel streaming utilizing maximum available core and memory budgets.' }
  ];

  public basicView = computed(() => this.ms.wizardDraft().basicView);

  public activeDomains = computed<ConfigDomainGroup[]>(() => {
    return this.ms.wizardConfigDomains();
  });

  public selectedDomain = computed<ConfigDomainGroup | undefined>(() => {
    const list = this.activeDomains();
    return list.find(d => d.id === this.selectedDomainId) || list[0];
  });

  public selectPreset(preset: BasicPerformancePreset): void {
    const workers = preset === 'CONSERVATIVE' ? 4 : (preset === 'BALANCED' ? 8 : 16);
    this.ms.updateDraft({
      basicView: {
        ...this.ms.wizardDraft().basicView,
        performancePreset: preset,
        derivedMaxWorkers: workers,
        derivedBatchMb: workers * 2
      }
    });
  }

  public updateBasicField(field: string, value: any): void {
    this.ms.updateDraft({
      basicView: {
        ...this.ms.wizardDraft().basicView,
        [field]: value
      }
    });
  }

  public getFieldEffectiveValue(field: ConfigFieldDescriptor): any {
    const overrides = this.ms.wizardDraft().configOverrides;
    if (overrides[field.id] !== undefined) {
      return overrides[field.id];
    }
    return field.effectiveValue;
  }

  public setFieldOverride(fieldId: string, value: any): void {
    const updated = { ...this.ms.wizardDraft().configOverrides, [fieldId]: value };
    this.ms.updateDraft({ configOverrides: updated });
  }

  public isContinuousSyncMode(): boolean {
    const m = this.ms.wizardDraft().mode;
    return m === 'M2_BULK_CDC' || m === 'M3_CDC' || m === 'M5_STATE_SYNC';
  }
}
