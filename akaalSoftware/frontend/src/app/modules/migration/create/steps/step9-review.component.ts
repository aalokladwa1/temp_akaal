import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MigrationUiService } from '../../../../core/services/migration-ui.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-step9-review',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 animate-in fade-in duration-150 text-xs select-none">
      
      <!-- Header -->
      <div class="flex items-center justify-between pb-2 border-b border-slate-200">
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center font-bold">
            <app-lucide-icon name="file-check-2" [size]="16"></app-lucide-icon>
          </div>
          <div>
            <h2 class="text-base font-bold text-slate-900">Step 9 &bull; FINAL LAUNCH CONTRACT</h2>
            <p class="text-xs text-slate-500 font-medium">Final executive review of operator intent and initialization contract before compilation.</p>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <span class="text-slate-500 font-medium">Contract Status:</span>
          <span class="px-2.5 py-1 rounded-md bg-blue-50 text-blue-700 font-bold border border-blue-200 font-mono">
            Awaiting Initialization
          </span>
        </div>
      </div>

      <!-- 1. Executive Migration Contract Grid -->
      <div class="p-5 rounded-xl bg-white border border-slate-200/90 shadow-2xs flex flex-col gap-4">
        <div class="pb-2.5 border-b border-slate-100 flex items-center justify-between">
          <span class="font-bold text-slate-900 uppercase tracking-wider text-[11px]">EXECUTIVE MIGRATION CONTRACT</span>
          <span class="text-[11px] font-mono text-blue-700 bg-blue-50 px-2 py-0.5 rounded font-bold">DRAFT INTENT</span>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-[11.5px]">
          <div class="flex flex-col gap-0.5 p-3 rounded-lg bg-slate-50 border border-slate-200">
            <span class="text-slate-500 text-[10px] font-bold uppercase">Migration Name</span>
            <span class="font-bold text-slate-900 font-mono truncate">{{ ms.wizardDraft().name || 'Unnamed Pipeline' }}</span>
          </div>

          <div class="flex flex-col gap-0.5 p-3 rounded-lg bg-slate-50 border border-slate-200">
            <span class="text-slate-500 text-[10px] font-bold uppercase">Project Container</span>
            <span class="font-bold text-slate-900 truncate">{{ ms.wizardDraft().projectId ? 'Assigned to Project' : 'Independent Migration' }}</span>
          </div>

          <div class="flex flex-col gap-0.5 p-3 rounded-lg bg-slate-50 border border-slate-200">
            <span class="text-slate-500 text-[10px] font-bold uppercase">Execution Mode</span>
            <span class="font-bold text-blue-700 font-mono">{{ ms.wizardDraft().mode }}</span>
          </div>

          <div class="flex flex-col gap-0.5 p-3 rounded-lg bg-slate-50 border border-slate-200">
            <span class="text-slate-500 text-[10px] font-bold uppercase">Target Environment</span>
            <span class="font-bold text-slate-900">{{ ms.wizardDraft().environment }}</span>
          </div>

          <div class="flex flex-col gap-0.5 p-3 rounded-lg bg-slate-50 border border-slate-200">
            <span class="text-slate-500 text-[10px] font-bold uppercase">Source Engine &amp; Host</span>
            <span class="font-bold text-slate-900 font-mono truncate">{{ ms.wizardDraft().sourceProvider }} ({{ ms.wizardDraft().sourceHost || 'Pending' }})</span>
          </div>

          <div class="flex flex-col gap-0.5 p-3 rounded-lg bg-slate-50 border border-slate-200">
            <span class="text-slate-500 text-[10px] font-bold uppercase">Target Engine &amp; Host</span>
            <span class="font-bold text-slate-900 font-mono truncate">{{ ms.wizardDraft().targetProvider }} ({{ ms.wizardDraft().targetHost || 'Pending' }})</span>
          </div>

          <div class="flex flex-col gap-0.5 p-3 rounded-lg bg-slate-50 border border-slate-200">
            <span class="text-slate-500 text-[10px] font-bold uppercase">Scope Selection</span>
            <span class="font-bold text-slate-900">{{ ms.wizardDraft().selectedTopologyNodes.length }} Hierarchy Nodes</span>
          </div>

          <div class="flex flex-col gap-0.5 p-3 rounded-lg bg-slate-50 border border-slate-200">
            <span class="text-slate-500 text-[10px] font-bold uppercase">Approval Barriers</span>
            <span class="font-bold text-amber-800">{{ ms.wizardDraft().customBarriersCount }} Governance Barriers</span>
          </div>
        </div>
      </div>

      <!-- 2. CANONICAL FINGERPRINTS (Zero Fake Authority) -->
      <div class="p-5 rounded-xl bg-white border border-slate-200/90 shadow-2xs flex flex-col gap-3">
        <div class="pb-2.5 border-b border-slate-100 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <app-lucide-icon name="fingerprint" [size]="15" class="text-slate-700"></app-lucide-icon>
            <span class="font-bold text-slate-900 uppercase tracking-wider text-[11px]">CANONICAL FINGERPRINTS</span>
          </div>
          <span class="text-[10.5px] text-slate-500 font-medium">Authoritative values generated by backend compiler</span>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 font-mono text-[11px]">
          <div class="p-3 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-1">
            <span class="text-slate-500 text-[10px] font-bold uppercase font-sans">Plan Fingerprint</span>
            <span class="text-slate-600 font-semibold italic">Pending canonical compilation</span>
          </div>

          <div class="p-3 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-1">
            <span class="text-slate-500 text-[10px] font-bold uppercase font-sans">Configuration Fingerprint</span>
            <span class="text-slate-600 font-semibold italic">Pending configuration resolution</span>
          </div>

          <div class="p-3 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-1">
            <span class="text-slate-500 text-[10px] font-bold uppercase font-sans">Approval Fingerprint</span>
            <span class="text-slate-600 font-semibold italic">Pending approval resolution</span>
          </div>

          <div class="p-3 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-1">
            <span class="text-slate-500 text-[10px] font-bold uppercase font-sans">Initialization Fingerprint</span>
            <span class="text-slate-600 font-semibold italic">Created at initialization</span>
          </div>
        </div>
      </div>

      <!-- 3. LAUNCH SCHEDULING CHOICES -->
      <div class="p-5 rounded-xl bg-white border border-slate-200/90 shadow-2xs flex flex-col gap-4">
        <div class="pb-2.5 border-b border-slate-100 flex items-center justify-between">
          <span class="font-bold text-slate-900 uppercase tracking-wider text-[11px]">INITIALIZATION DISPATCH SCHEDULE</span>
          <span class="text-[11px] text-slate-500 font-medium">Select execution trigger window</span>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <!-- Choice 1: Run Now -->
          <div
            (click)="ms.updateDraft({ scheduleChoice: 'RUN_NOW' })"
            class="p-4 rounded-xl border-2 cursor-pointer transition-all flex flex-col gap-2"
            [class.border-blue-600]="ms.wizardDraft().scheduleChoice === 'RUN_NOW'"
            [class.bg-blue-50]="ms.wizardDraft().scheduleChoice === 'RUN_NOW'"
            [class.border-slate-200]="ms.wizardDraft().scheduleChoice !== 'RUN_NOW'"
            [class.bg-white]="ms.wizardDraft().scheduleChoice !== 'RUN_NOW'">
            
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <div class="w-4 h-4 rounded-full border-2 flex items-center justify-center shrink-0"
                  [class.border-blue-600]="ms.wizardDraft().scheduleChoice === 'RUN_NOW'"
                  [class.bg-blue-600]="ms.wizardDraft().scheduleChoice === 'RUN_NOW'"
                  [class.border-slate-300]="ms.wizardDraft().scheduleChoice !== 'RUN_NOW'">
                  @if (ms.wizardDraft().scheduleChoice === 'RUN_NOW') {
                    <div class="w-1.5 h-1.5 rounded-full bg-white"></div>
                  }
                </div>
                <span class="font-bold text-slate-900 text-xs">Run Now (Immediate Initialization)</span>
              </div>
              <span class="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px] font-bold">Direct</span>
            </div>

            <p class="text-[11px] text-slate-600 leading-relaxed font-normal pl-6">
              Compiles canonical execution DAG, allocates worker threads, and begins pipeline execution immediately upon sign-off.
            </p>
          </div>

          <!-- Choice 2: Scheduled Maintenance Window -->
          <div
            (click)="ms.updateDraft({ scheduleChoice: 'SCHEDULE' })"
            class="p-4 rounded-xl border-2 cursor-pointer transition-all flex flex-col gap-2"
            [class.border-blue-600]="ms.wizardDraft().scheduleChoice === 'SCHEDULE'"
            [class.bg-blue-50]="ms.wizardDraft().scheduleChoice === 'SCHEDULE'"
            [class.border-slate-200]="ms.wizardDraft().scheduleChoice !== 'SCHEDULE'"
            [class.bg-white]="ms.wizardDraft().scheduleChoice !== 'SCHEDULE'">
            
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <div class="w-4 h-4 rounded-full border-2 flex items-center justify-center shrink-0"
                  [class.border-blue-600]="ms.wizardDraft().scheduleChoice === 'SCHEDULE'"
                  [class.bg-blue-600]="ms.wizardDraft().scheduleChoice === 'SCHEDULE'"
                  [class.border-slate-300]="ms.wizardDraft().scheduleChoice !== 'SCHEDULE'">
                  @if (ms.wizardDraft().scheduleChoice === 'SCHEDULE') {
                    <div class="w-1.5 h-1.5 rounded-full bg-white"></div>
                  }
                </div>
                <span class="font-bold text-slate-900 text-xs">Schedule Maintenance Window</span>
              </div>
              <span class="px-2 py-0.5 rounded bg-blue-100 text-blue-800 text-[10px] font-bold">Planned</span>
            </div>

            <p class="text-[11px] text-slate-600 leading-relaxed font-normal pl-6">
              Defer execution start time to a scheduled change-window. Pipeline remains in INITIALIZED state until timer fires.
            </p>
          </div>
        </div>

        <!-- Conditional Schedule Date/Time Inputs -->
        @if (ms.wizardDraft().scheduleChoice === 'SCHEDULE') {
          <div class="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex items-center gap-4 flex-wrap">
            <div class="flex flex-col gap-1">
              <label class="font-bold text-slate-800 text-[11px]">Execution Date &amp; Time (UTC)</label>
              <input
                type="datetime-local"
                [ngModel]="ms.wizardDraft().scheduledTime"
                (ngModelChange)="ms.updateDraft({ scheduledTime: $event })"
                class="h-8 px-3 rounded-md bg-white border border-slate-200 text-xs font-semibold font-mono text-slate-900" />
            </div>
            <div class="flex flex-col gap-1">
              <label class="font-bold text-slate-800 text-[11px]">Timezone Reference</label>
              <span class="h-8 px-3 rounded-md bg-slate-100 border border-slate-200 text-xs font-semibold text-slate-700 flex items-center">
                UTC (Coordinated Universal Time)
              </span>
            </div>
          </div>
        }

      </div>

    </div>
  `
})
export class Step9ReviewComponent {
  public ms = inject(MigrationUiService);
}
