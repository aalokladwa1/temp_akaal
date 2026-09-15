/**
 * AKAAL Monitoring — Part 4 of 4: Alert Evaluation Tab Component
 * Rule evaluation state, observed telemetry values, thresholds, and execution cadence.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AlertsMonitoringService } from '../../services/alerts-monitoring.service';
import { CustomSelectComponent, SelectOption } from '../../../../shared/components/custom-select.component';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-alerts-evaluation-tab',
  standalone: true,
  imports: [CommonModule, CustomSelectComponent, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- 1. Evaluation Engine KPI Stat Strip -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
        
        <!-- Total Active Rules -->
        <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-1">
          <span class="text-xs font-medium text-slate-500">Evaluated Rules</span>
          <div class="flex items-baseline gap-1.5">
            <span class="text-2xl font-bold text-slate-900 font-mono tracking-tight">
              {{ ams.evaluationRules().length }}
            </span>
            <span class="text-xs text-slate-400">rules active</span>
          </div>
          <span class="text-[11px] text-slate-500 font-medium flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
            Continuous 15s evaluation loop
          </span>
        </div>

        <!-- Rules Firing -->
        <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-1">
          <span class="text-xs font-medium text-slate-500">Rules Firing</span>
          <div class="flex items-baseline gap-1.5">
            <span class="text-2xl font-bold text-rose-600 font-mono tracking-tight">
              {{ firingRulesCount }}
            </span>
            <span class="text-xs text-slate-400">breaching threshold</span>
          </div>
          <span class="text-[11px] text-rose-600 font-medium flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
            Dispatched to active alerts
          </span>
        </div>

        <!-- Rules In Nominal State -->
        <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-1">
          <span class="text-xs font-medium text-slate-500">Normal / Clear</span>
          <div class="flex items-baseline gap-1.5">
            <span class="text-2xl font-bold text-emerald-600 font-mono tracking-tight">
              {{ normalRulesCount }}
            </span>
            <span class="text-xs text-slate-400">within bounds</span>
          </div>
          <span class="text-[11px] text-emerald-600 font-medium flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            No anomalies detected
          </span>
        </div>

        <!-- Evaluator Precision -->
        <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-1">
          <span class="text-xs font-medium text-slate-500">Evaluator Cadence</span>
          <div class="flex items-baseline gap-1.5">
            <span class="text-2xl font-bold text-slate-900 font-mono tracking-tight">
              15.0
            </span>
            <span class="text-xs text-slate-400">sec avg interval</span>
          </div>
          <span class="text-[11px] text-emerald-600 font-medium flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            Zero evaluation lag
          </span>
        </div>

      </div>

      <!-- 2. Search & Filter Bar -->
      <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        
        <!-- Search input -->
        <div class="relative flex-1">
          <app-lucide-icon name="search" [size]="15" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"></app-lucide-icon>
          <input
            type="text"
            [value]="ams.ruleSearchQuery()"
            (input)="onSearchInput($event)"
            placeholder="Search evaluation rules by name, signal key, or rule ID..."
            class="w-full pl-9 pr-4 py-2 text-xs font-medium bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-600 focus:border-blue-600 transition-all"
          />
        </div>

        <!-- State Filter Dropdown -->
        <div class="w-full sm:w-56">
          <app-custom-select
            [options]="stateOptions"
            [value]="ams.ruleStateFilter()"
            (valueChange)="ams.ruleStateFilter.set($event)"
            placeholder="Filter State">
          </app-custom-select>
        </div>

      </div>

      <!-- 3. Evaluation Rules Table -->
      <div class="rounded-2xl bg-white border border-slate-200 shadow-2xs overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th class="py-3.5 px-4">Rule Name & ID</th>
                <th class="py-3.5 px-4">Signal Expression</th>
                <th class="py-3.5 px-4">Observed Telemetry</th>
                <th class="py-3.5 px-4">Threshold Boundary</th>
                <th class="py-3.5 px-4">Evaluation Result</th>
                <th class="py-3.5 px-4">Cadence</th>
                <th class="py-3.5 px-4">Last Evaluated</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs">
              @for (rule of ams.filteredRules(); track rule.rule_id) {
                <tr class="hover:bg-slate-50/60 transition-colors">
                  
                  <!-- Rule Name & ID -->
                  <td class="py-3.5 px-4">
                    <div class="flex flex-col gap-0.5">
                      <span class="font-bold text-slate-900">{{ rule.name }}</span>
                      <div class="flex items-center gap-1.5">
                        <span class="font-mono text-[10px] text-slate-400">{{ rule.rule_id }}</span>
                        <span class="px-1.5 py-0.2 rounded text-[9px] font-semibold bg-slate-100 text-slate-600">
                          {{ ams.formatText(rule.target_scope) }}
                        </span>
                      </div>
                    </div>
                  </td>

                  <!-- Signal Expression -->
                  <td class="py-3.5 px-4">
                    <span class="font-mono text-xs text-slate-700 font-medium bg-slate-50 px-2 py-1 rounded border border-slate-200/60">
                      {{ rule.signal }}
                    </span>
                  </td>

                  <!-- Observed Telemetry -->
                  <td class="py-3.5 px-4">
                    <span 
                      class="font-mono font-bold text-xs"
                      [ngClass]="{
                        'text-rose-600': rule.result_state === 'FIRING',
                        'text-emerald-600': rule.result_state === 'NORMAL',
                        'text-slate-600': rule.result_state === 'SUPPRESSED'
                      }">
                      {{ rule.observed_value }}
                    </span>
                  </td>

                  <!-- Threshold Boundary -->
                  <td class="py-3.5 px-4">
                    <div class="flex items-center gap-1.5">
                      <span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-700">
                        {{ rule.comparator }}
                      </span>
                      <span class="font-mono text-xs text-slate-700">{{ rule.threshold_value }}</span>
                    </div>
                  </td>

                  <!-- Evaluation Result -->
                  <td class="py-3.5 px-4">
                    <span 
                      class="px-2 py-0.5 rounded text-[11px] font-bold inline-flex items-center gap-1.5"
                      [ngClass]="{
                        'bg-rose-100 text-rose-800': rule.result_state === 'FIRING',
                        'bg-emerald-100 text-emerald-800': rule.result_state === 'NORMAL',
                        'bg-slate-100 text-slate-700': rule.result_state === 'SUPPRESSED',
                        'bg-amber-100 text-amber-800': rule.result_state === 'UNKNOWN'
                      }">
                      <span 
                        class="w-1.5 h-1.5 rounded-full shrink-0"
                        [ngClass]="{
                          'bg-rose-600': rule.result_state === 'FIRING',
                          'bg-emerald-600': rule.result_state === 'NORMAL',
                          'bg-slate-500': rule.result_state === 'SUPPRESSED',
                          'bg-amber-500': rule.result_state === 'UNKNOWN'
                        }">
                      </span>
                      <span>{{ rule.result_state }}</span>
                    </span>
                  </td>

                  <!-- Cadence -->
                  <td class="py-3.5 px-4">
                    <span class="font-mono text-xs text-slate-600">{{ rule.evaluation_cadence_sec }}s</span>
                  </td>

                  <!-- Last Evaluated -->
                  <td class="py-3.5 px-4 text-slate-500 font-mono text-[11px]">
                    {{ rule.last_evaluated_at | date:'HH:mm:ss' }}
                  </td>

                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

      <!-- 4. Operational Notice -->
      <div class="p-4 rounded-2xl bg-blue-50/50 border border-blue-200/60 flex items-start gap-3">
        <app-lucide-icon name="info" [size]="16" class="text-blue-600 shrink-0 mt-0.5"></app-lucide-icon>
        <div class="flex flex-col gap-0.5 text-xs text-blue-900">
          <span class="font-bold">Evaluation Engine Scope</span>
          <p class="text-blue-700 leading-relaxed">
            Rule conditions are evaluated synchronously against incoming telemetry queues every 15 seconds. Rule definitions, threshold adjustments, and alert suppression windows are managed under Administration Settings.
          </p>
        </div>
      </div>

    </div>
  `
})
export class AlertsEvaluationTabComponent {
  public ams = inject(AlertsMonitoringService);

  public stateOptions: SelectOption[] = [
    { label: 'All Rule States', value: 'ALL' },
    { label: 'Firing Only', value: 'FIRING' },
    { label: 'Normal Only', value: 'NORMAL' },
    { label: 'Suppressed Only', value: 'SUPPRESSED' }
  ];

  public get firingRulesCount(): number {
    return this.ams.evaluationRules().filter(r => r.result_state === 'FIRING').length;
  }

  public get normalRulesCount(): number {
    return this.ams.evaluationRules().filter(r => r.result_state === 'NORMAL').length;
  }

  public onSearchInput(event: Event): void {
    const target = event.target as HTMLInputElement;
    this.ams.ruleSearchQuery.set(target.value);
  }
}
