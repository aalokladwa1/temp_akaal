import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RecoveryReliabilityReportPayload } from '../../../models/report-payloads.models';

@Component({
  selector: 'app-recovery-reliability-report-body',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col gap-6 select-none">
      
      <!-- Recovery Summary Key-Values -->
      <div class="p-5 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
        <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-heading">
          FAULT RECOVERY &amp; RECONSTRUCTION SUMMARY
        </span>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Fault Events</span>
            <span class="text-base font-bold font-mono text-slate-900">{{ payload.recovery_summary.total_failures_encountered }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Automatic Restarts</span>
            <span class="text-base font-bold font-mono text-emerald-700">{{ payload.recovery_summary.automatic_restarts }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Manual Interventions</span>
            <span class="text-base font-bold font-mono text-slate-700">{{ payload.recovery_summary.manual_interventions }}</span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-slate-500 font-medium">Last Known Checkpoint</span>
            <span class="text-base font-bold font-mono text-slate-900 text-[11px] truncate">{{ payload.recovery_summary.last_known_checkpoint }}</span>
          </div>
        </div>
      </div>

      <!-- Failure Events Table -->
      @if (payload.failure_events && payload.failure_events.length > 0) {
        <div class="flex flex-col gap-3">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            FAILURE EVENTS &amp; RESOLUTION TIMELINE
          </span>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Event ID</th>
                  <th class="py-3 px-4">Component</th>
                  <th class="py-3 px-4">Failure Type</th>
                  <th class="py-3 px-4">Recovery Action</th>
                  <th class="py-3 px-4 text-right">Status</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (ev of payload.failure_events; track ev.event_id) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-mono text-slate-800 text-[11px]">
                      {{ ev.event_id }}
                    </td>
                    <td class="py-3.5 px-4 font-semibold text-slate-900">
                      {{ ev.component }}
                    </td>
                    <td class="py-3.5 px-4 text-slate-600">
                      {{ ev.failure_type }}
                    </td>
                    <td class="py-3.5 px-4 text-slate-700">
                      {{ ev.recovery_action }}
                    </td>
                    <td class="py-3.5 px-4 text-right">
                      <span 
                        class="px-2 py-0.5 rounded text-[10px] font-bold"
                        [ngClass]="ev.resolution_status === 'RESOLVED' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'">
                        {{ ev.resolution_status }}
                      </span>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      }

      <!-- Checkpoint History Table -->
      @if (payload.checkpoint_history && payload.checkpoint_history.length > 0) {
        <div class="flex flex-col gap-3">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            DURABLE CHECKPOINT SNAPSHOTS
          </span>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Checkpoint ID</th>
                  <th class="py-3 px-4">Timestamp</th>
                  <th class="py-3 px-4">State Size</th>
                  <th class="py-3 px-4 text-right">Durable Reference</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (cp of payload.checkpoint_history; track cp.checkpoint_id) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-mono font-semibold text-slate-900 text-[11px]">
                      {{ cp.checkpoint_id }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-slate-500 text-[11px]">
                      {{ cp.timestamp | date:'yyyy-MM-dd HH:mm:ss' }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-slate-700">
                      {{ (cp.reconstructed_state_byte_size / 1024) | number:'1.0-0' }} KB
                    </td>
                    <td class="py-3.5 px-4 text-right font-mono text-slate-600 text-[11px]">
                      {{ cp.durable_reference }}
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      }

      <!-- Lease & Fencing Evidence (If applicable) -->
      @if (payload.lease_and_fencing_evidence && payload.lease_and_fencing_evidence.length > 0) {
        <div class="flex flex-col gap-3">
          <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-heading">
            WORKER LEASE &amp; FENCING OBSERVATIONS
          </span>

          <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th class="py-3 px-4">Worker Node</th>
                  <th class="py-3 px-4">Lease Acquired</th>
                  <th class="py-3 px-4">Fenced Timestamp</th>
                  <th class="py-3 px-4 text-right">Reason</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (lease of payload.lease_and_fencing_evidence; track lease.worker_node_id) {
                  <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="py-3.5 px-4 font-mono font-semibold text-slate-900 text-[11px]">
                      {{ lease.worker_node_id }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-slate-500 text-[11px]">
                      {{ lease.lease_acquired_at | date:'yyyy-MM-dd HH:mm' }}
                    </td>
                    <td class="py-3.5 px-4 font-mono text-slate-500 text-[11px]">
                      {{ lease.lease_fenced_at ? (lease.lease_fenced_at | date:'yyyy-MM-dd HH:mm') : 'Active' }}
                    </td>
                    <td class="py-3.5 px-4 text-right text-slate-600 text-[11px]">
                      {{ lease.fencing_reason || '—' }}
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      }

    </div>
  `
})
export class RecoveryReliabilityReportBodyComponent {
  @Input({ required: true }) public payload!: RecoveryReliabilityReportPayload;
}
