/**
 * AKAAL Monitoring — Part 3 of 4: Platform Reliability Tab Component
 * System resilience over time, checkpoint durability, Raft consensus,
 * component restart churn, failure events, and advisory RCA hypotheses.
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PlatformMonitoringService } from '../../services/platform-monitoring.service';

@Component({
  selector: 'app-platform-reliability-tab',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- 1. Durability, Consensus & Self-Healing Matrix -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        <!-- Storage & Checkpoint Durability -->
        <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Durability &amp; Consensus State</h3>
            <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700">
              {{ pms.reliability().durability.checkpoint_store_integrity }}
            </span>
          </div>

          <div class="flex flex-col gap-2.5 text-xs">
            <div class="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100">
              <span class="text-slate-500 font-medium">Raft Quorum State:</span>
              <span class="font-bold text-emerald-700 flex items-center gap-1.5">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                {{ pms.reliability().durability.raft_consensus_state }}
              </span>
            </div>
            <div class="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100">
              <span class="text-slate-500 font-medium">CAS Lease Fencing:</span>
              <span class="font-bold text-emerald-700 flex items-center gap-1.5">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                {{ pms.reliability().durability.cas_lease_fencing_status }}
              </span>
            </div>
            <div class="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100">
              <span class="text-slate-500 font-medium">Self-Healing Strategy:</span>
              <span class="font-semibold text-slate-800">{{ pms.reliability().recovery_progress.current_strategy }}</span>
            </div>
          </div>
        </div>

        <!-- Recovery & Self-Healing Statistics -->
        <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Recovery &amp; Healing History (24h)</h3>
            <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-50 text-blue-700">
              {{ pms.reliability().recovery_progress.active_recovery_count === 0 ? 'Nominal (Idle)' : 'Recovery Active' }}
            </span>
          </div>

          <div class="grid grid-cols-2 gap-3 text-xs">
            <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Successful Recoveries</span>
              <span class="text-xl font-bold font-mono text-emerald-700">{{ pms.reliability().recovery_progress.successful_recoveries_24h }}</span>
              <span class="text-[11px] text-slate-400">Zero data loss events</span>
            </div>
            <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col gap-1">
              <span class="text-slate-500 font-medium">Failed Recoveries</span>
              <span class="text-xl font-bold font-mono text-slate-900">{{ pms.reliability().recovery_progress.failed_recoveries_24h }}</span>
              <span class="text-[11px] text-emerald-600">All retries resolved</span>
            </div>
          </div>

          <div class="text-[11px] text-slate-500 font-mono">
            Active Recovery Pipelines: <strong class="text-slate-800">{{ pms.reliability().recovery_progress.active_recovery_count }} active</strong>
          </div>
        </div>

      </div>

      <!-- 2. Component Restarts & Churn Analysis -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Component Uptime &amp; Restart Churn</h3>
          <span class="text-xs text-slate-500 font-medium">{{ pms.reliability().component_restarts.length }} tracked components</span>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs text-slate-600">
            <thead>
              <tr class="border-b border-slate-200 text-slate-700 font-semibold bg-slate-50/75">
                <th class="py-2.5 px-3">Component / Subsystem</th>
                <th class="py-2.5 px-3">Uptime Duration</th>
                <th class="py-2.5 px-3">Restarts (24h)</th>
                <th class="py-2.5 px-3 text-right">Churn State</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              @for (cmp of pms.reliability().component_restarts; track cmp.component) {
                <tr class="hover:bg-slate-50/50 transition-colors">
                  <td class="py-2.5 px-3 font-mono font-bold text-slate-900">{{ cmp.component }}</td>
                  <td class="py-2.5 px-3 font-mono text-slate-700">{{ cmp.uptime_duration }}</td>
                  <td class="py-2.5 px-3 font-mono font-semibold" [ngClass]="cmp.restarts_24h > 0 ? 'text-amber-700' : 'text-slate-700'">
                    {{ cmp.restarts_24h }}
                  </td>
                  <td class="py-2.5 px-3 text-right">
                    <span 
                      class="px-2 py-0.5 rounded text-[10px] font-semibold"
                      [ngClass]="cmp.churn_status === 'STABLE' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200/60' : 'bg-amber-50 text-amber-700 border border-amber-200/60'">
                      {{ cmp.churn_status }}
                    </span>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

      <!-- 3. Advisory Root Cause Analysis (Advisory Intelligence) -->
      @if (pms.reliability().advisory_rca.length > 0) {
        <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div class="flex items-center gap-2">
              <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Advisory Root Cause Hypotheses</h3>
              <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-50 text-blue-700">Advisory Only</span>
            </div>
            <span class="text-xs text-slate-500 font-medium">{{ pms.reliability().advisory_rca.length }} hypotheses evaluated</span>
          </div>

          <div class="flex flex-col gap-3">
            @for (rca of pms.reliability().advisory_rca; track rca.rank) {
              <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-2 text-xs">
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <span class="w-5 h-5 rounded bg-blue-600 text-white font-bold flex items-center justify-center text-[10px]">
                      #{{ rca.rank }}
                    </span>
                    <span class="font-bold text-slate-900">{{ rca.candidate_cause }}</span>
                  </div>
                  
                  <div class="flex items-center gap-2">
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">
                      {{ rca.confidence_percent }}% Confidence
                    </span>
                    <span class="text-[10px] font-medium text-slate-500">{{ rca.epistemic_status }}</span>
                  </div>
                </div>

                <p class="text-slate-600 leading-relaxed pt-1 border-t border-slate-200/60">
                  <strong class="text-slate-700">Observed Evidence:</strong> {{ rca.supporting_evidence }}
                </p>
              </div>
            }
          </div>
        </div>
      }

      <!-- 4. Recent Failure Events -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Recent Platform Failure Events</h3>
          <span class="text-xs text-slate-500 font-medium">{{ pms.reliability().failure_events.length }} failures recorded</span>
        </div>

        @if (pms.reliability().failure_events.length === 0) {
          <div class="p-6 rounded-xl bg-slate-50 border border-slate-100 text-center text-xs text-slate-500">
            Zero recent platform failures recorded. Raft consensus, CAS fencing, and checkpoint pipelines operating nominally.
          </div>
        } @else {
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs text-slate-600">
              <thead>
                <tr class="border-b border-slate-200 text-slate-700 font-semibold bg-slate-50/75">
                  <th class="py-2.5 px-3">Timestamp</th>
                  <th class="py-2.5 px-3">Error Code</th>
                  <th class="py-2.5 px-3">Component</th>
                  <th class="py-2.5 px-3">Message</th>
                  <th class="py-2.5 px-3 text-right">Recoverable</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                @for (fail of pms.reliability().failure_events; track fail.id) {
                  <tr class="hover:bg-slate-50/50 transition-colors">
                    <td class="py-2.5 px-3 whitespace-nowrap font-mono text-slate-500">{{ fail.timestamp | date:'HH:mm:ss' }}</td>
                    <td class="py-2.5 px-3 whitespace-nowrap font-mono font-bold text-rose-700">{{ fail.error_code }}</td>
                    <td class="py-2.5 px-3 whitespace-nowrap text-slate-700">{{ fail.component }}</td>
                    <td class="py-2.5 px-3 text-slate-800">{{ fail.message }}</td>
                    <td class="py-2.5 px-3 whitespace-nowrap text-right">
                      <span class="px-2 py-0.5 rounded text-[10px] font-semibold" [ngClass]="fail.is_recoverable ? 'bg-amber-50 text-amber-700' : 'bg-rose-50 text-rose-700'">
                        {{ fail.is_recoverable ? 'Recoverable' : 'Fatal' }}
                      </span>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      </div>

    </div>
  `
})
export class PlatformReliabilityTabComponent {
  public pms = inject(PlatformMonitoringService);
}
