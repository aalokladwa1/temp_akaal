import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MigrationOverviewDTO, SelectedMigrationHeaderDTO } from '../../models/migration-monitoring.models';

@Component({
  selector: 'app-migration-overview-tab',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- 1. Headline & Sync State Card -->
      <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-3">
        <div class="flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
          <span class="text-xs font-bold text-slate-800 uppercase tracking-wider">Sync State Orientation</span>
        </div>
        <h2 class="text-lg font-bold text-slate-900 tracking-tight leading-snug">
          {{ overview.sync_state_summary }}
        </h2>
        <p class="text-xs font-medium text-slate-600 leading-relaxed max-w-4xl">
          {{ overview.semantic_work_headline }}
        </p>
      </div>

      <!-- 2. Active Conditions Section -->
      <div class="flex flex-col gap-3">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Active Conditions</h3>
          <span class="text-xs text-slate-500 font-medium">{{ overview.active_conditions.length }} conditions observed</span>
        </div>

        @if (overview.active_conditions.length === 0) {
          <div class="p-5 rounded-xl bg-white border border-slate-200 text-center text-xs text-slate-500">
            No active alerts or unusual operational conditions observed.
          </div>
        } @else {
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            @for (cond of overview.active_conditions; track cond.id) {
              <div 
                class="p-4 rounded-xl bg-white border flex flex-col justify-between gap-3 shadow-2xs"
                [ngClass]="{
                  'border-blue-200 bg-blue-50/20': cond.severity === 'INFO',
                  'border-amber-200 bg-amber-50/20': cond.severity === 'WARNING',
                  'border-rose-200 bg-rose-50/20': cond.severity === 'CRITICAL'
                }">
                <div class="flex flex-col gap-1.5">
                  <div class="flex items-center justify-between gap-2">
                    <span class="text-xs font-bold text-slate-900">{{ cond.title }}</span>
                    <span 
                      class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider"
                      [ngClass]="{
                        'bg-blue-100 text-blue-800': cond.severity === 'INFO',
                        'bg-amber-100 text-amber-800': cond.severity === 'WARNING',
                        'bg-rose-100 text-rose-800': cond.severity === 'CRITICAL'
                      }">
                      {{ cond.severity }}
                    </span>
                  </div>
                  <p class="text-xs text-slate-600 leading-relaxed">{{ cond.detail }}</p>
                </div>

                <div class="flex items-center justify-between pt-2 border-t border-slate-100 text-xs text-slate-500">
                  <span>{{ cond.duration_label }}</span>
                  @if (cond.action_label) {
                    <span class="font-medium text-blue-600 hover:text-blue-700 cursor-pointer">{{ cond.action_label }} →</span>
                  }
                </div>
              </div>
            }
          </div>
        }
      </div>

      <!-- 3. Recent Operational Events -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Recent Operational Events</h3>
          <span class="text-xs text-slate-500 font-medium">Last {{ overview.recent_events.length }} events</span>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs text-slate-600">
            <thead>
              <tr class="border-b border-slate-200 text-slate-700 font-semibold bg-slate-50/75">
                <th class="py-2.5 px-3">Timestamp</th>
                <th class="py-2.5 px-3">Category</th>
                <th class="py-2.5 px-3">Summary</th>
                <th class="py-2.5 px-3 text-right">Severity</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              @for (evt of overview.recent_events; track evt.id) {
                <tr class="hover:bg-slate-50/50 transition-colors">
                  <td class="py-2.5 px-3 whitespace-nowrap text-slate-500 font-mono text-[11px]">
                    {{ evt.timestamp | date:'yyyy-MM-dd HH:mm:ss' }}
                  </td>
                  <td class="py-2.5 px-3 whitespace-nowrap font-medium text-slate-700">
                    {{ evt.category }}
                  </td>
                  <td class="py-2.5 px-3 text-slate-800">
                    {{ evt.summary }}
                  </td>
                  <td class="py-2.5 px-3 whitespace-nowrap text-right">
                    <span 
                      class="px-2 py-0.5 rounded text-[10px] font-semibold"
                      [ngClass]="{
                        'bg-blue-50 text-blue-700': evt.severity === 'INFO',
                        'bg-amber-50 text-amber-700': evt.severity === 'WARNING',
                        'bg-rose-50 text-rose-700': evt.severity === 'CRITICAL'
                      }">
                      {{ evt.severity }}
                    </span>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

    </div>
  `
})
export class MigrationOverviewTabComponent {
  @Input({ required: true }) overview!: MigrationOverviewDTO;
  @Input({ required: true }) header!: SelectedMigrationHeaderDTO;
}
