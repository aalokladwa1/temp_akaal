import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MigrationReliabilityDTO } from '../../models/migration-monitoring.models';
import { formatSnakeToTitle } from '../../models/monitoring.models';

@Component({
  selector: 'app-migration-reliability-tab',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- 1. Active Recovery & Checkpoint Durability -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        <!-- Active Recovery State -->
        <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Recovery &amp; Self-Healing</h3>
            <span 
              class="px-2 py-0.5 rounded text-[11px] font-semibold"
              [ngClass]="reliability.active_recovery.is_recovering ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700'">
              {{ reliability.active_recovery.is_recovering ? 'Recovery Active' : 'Nominal (No Recovery)' }}
            </span>
          </div>

          <div class="flex flex-col gap-2.5 text-xs">
            <div class="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100">
              <span class="text-slate-500 font-medium">Recovery Status:</span>
              <span class="font-semibold text-slate-800">{{ reliability.active_recovery.recovery_stage }}</span>
            </div>
            <div class="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100">
              <span class="text-slate-500 font-medium">Resume Checkpoint:</span>
              <span class="font-mono font-semibold text-slate-800">{{ reliability.active_recovery.resume_checkpoint_id }}</span>
            </div>
            <div class="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100">
              <span class="text-slate-500 font-medium">Retry Budget:</span>
              <span class="font-mono font-semibold text-slate-800">{{ reliability.active_recovery.current_attempt }} / {{ reliability.active_recovery.max_attempts }} attempts</span>
            </div>
          </div>
        </div>

        <!-- Checkpoints & CAS Leases -->
        <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col justify-between gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Checkpoint &amp; CAS Durability</h3>
            <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700">
              {{ reliability.checkpoints.storage_integrity_state }}
            </span>
          </div>

          <div class="flex flex-col gap-2.5 text-xs">
            <div class="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100">
              <span class="text-slate-500 font-medium">Last Checkpoint:</span>
              <span class="font-mono font-semibold text-slate-800">{{ reliability.checkpoints.last_checkpoint_timestamp | date:'HH:mm:ss' }}</span>
            </div>
            <div class="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100">
              <span class="text-slate-500 font-medium">Committed Offset / SCN:</span>
              <span class="font-mono font-semibold text-slate-800 truncate max-w-[220px]" [title]="reliability.checkpoints.checkpoint_offset_label">
                {{ reliability.checkpoints.checkpoint_offset_label }}
              </span>
            </div>
            <div class="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100">
              <span class="text-slate-500 font-medium">Fencing Lease:</span>
              <span class="font-bold text-emerald-700 flex items-center gap-1">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                Active CAS Protected
              </span>
            </div>
          </div>
        </div>

      </div>

      <!-- 2. Advisory Root Cause Analysis (Strictly Advisory Intelligence) -->
      @if (reliability.rca_candidates.length > 0) {
        <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div class="flex items-center gap-2">
              <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Advisory Root Cause Hypotheses</h3>
              <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-50 text-blue-700">Advisory Only</span>
            </div>
            <span class="text-xs text-slate-500 font-medium">{{ reliability.rca_candidates.length }} hypotheses evaluated</span>
          </div>

          <div class="flex flex-col gap-3">
            @for (rca of reliability.rca_candidates; track rca.rank) {
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
                    <span class="text-[10px] font-medium text-slate-500">{{ formatText(rca.epistemic_status) }}</span>
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

      <!-- 3. Recent Failure Events -->
      <div class="p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <h3 class="text-sm font-bold text-slate-900 tracking-tight font-heading">Recent Failure Events</h3>
          <span class="text-xs text-slate-500 font-medium">{{ reliability.recent_failures.length }} failures recorded</span>
        </div>

        @if (reliability.recent_failures.length === 0) {
          <div class="p-6 rounded-xl bg-slate-50 border border-slate-100 text-center text-xs text-slate-500">
            Zero recent failures recorded. Checkpoint lease and execution pipeline operating nominally.
          </div>
        } @else {
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs text-slate-600">
              <thead>
                <tr class="border-b border-slate-200 text-slate-700 font-semibold bg-slate-50/75">
                  <th class="py-2.5 px-3">Timestamp</th>
                  <th class="py-2.5 px-3">Error Code</th>
                  <th class="py-2.5 px-3">Stage / Component</th>
                  <th class="py-2.5 px-3">Message</th>
                  <th class="py-2.5 px-3 text-right">Recoverable</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                @for (fail of reliability.recent_failures; track fail.id) {
                  <tr class="hover:bg-slate-50/50 transition-colors">
                    <td class="py-2.5 px-3 whitespace-nowrap font-mono text-slate-500">{{ fail.timestamp | date:'HH:mm:ss' }}</td>
                    <td class="py-2.5 px-3 whitespace-nowrap font-mono font-bold text-rose-700">{{ fail.error_code }}</td>
                    <td class="py-2.5 px-3 whitespace-nowrap text-slate-700">{{ fail.stage }} ({{ fail.component }})</td>
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
export class MigrationReliabilityTabComponent {
  @Input({ required: true }) reliability!: MigrationReliabilityDTO;

  public formatText = formatSnakeToTitle;
}
