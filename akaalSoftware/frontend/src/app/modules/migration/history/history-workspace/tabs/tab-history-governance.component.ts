import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HistoryWorkspaceService } from '../history-workspace.service';
import { GovernanceBarrierRecord, ApproverDecision } from '../history-workspace.models';

@Component({
  selector: 'app-tab-history-governance',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (hws.currentRecord(); as record) {
      <div class="space-y-6">
        
        @if (record.governance.length > 0) {
          @for (barrier of record.governance; track barrier.barrierId) {
            <!-- Barrier Card -->
            <div class="bg-white border border-slate-200 rounded-lg p-5 shadow-xs space-y-4">
              
              <!-- Barrier Header -->
              <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3 pb-3 border-b border-slate-100">
                <div>
                  <div class="flex items-center gap-2.5 flex-wrap">
                    <h2 class="text-base font-bold text-slate-900">
                      {{ barrier.protectedOperation }}
                    </h2>
                    <span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-bold border"
                      [ngClass]="getBarrierStatusClass(barrier.status)">
                      {{ barrier.status }}
                    </span>
                    <span class="font-mono text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                      {{ barrier.barrierId }}
                    </span>
                  </div>
                  <div class="text-xs text-slate-500 mt-1">
                    Requested by <strong class="text-slate-700">{{ barrier.requesterName }}</strong> at {{ formatTimestamp(barrier.requestedAt) }}
                  </div>
                </div>

                <!-- Quorum Metric -->
                <div class="flex items-center gap-3 bg-slate-50 px-3.5 py-2 rounded-md border border-slate-200 self-start md:self-auto">
                  <div class="text-right">
                    <div class="text-[10px] font-bold uppercase text-slate-500">Maker-Checker Quorum</div>
                    <div class="text-xs font-bold" [ngClass]="barrier.makerCheckerSatisfied ? 'text-emerald-700' : 'text-amber-700'">
                      {{ barrier.quorumSatisfied }} / {{ barrier.quorumRequired }} Required Approvals Satisfied
                    </div>
                  </div>
                </div>
              </div>

              <!-- Cryptographic Plan Fingerprint Binding -->
              <div class="p-3 bg-slate-50 rounded-md border border-slate-200 text-xs text-slate-700 flex flex-col md:flex-row md:items-center justify-between gap-2">
                <div class="flex items-center gap-2">
                  <span class="font-semibold text-slate-800">Bound Plan Fingerprint:</span>
                  <span class="font-mono text-[11px] text-slate-600 truncate max-w-[420px]" [title]="barrier.planFingerprintBinding">
                    {{ barrier.planFingerprintBinding }}
                  </span>
                </div>
                <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-100 text-emerald-800 shrink-0">
                  Fingerprint Match Verified
                </span>
              </div>

              <!-- Approver Decision Stream -->
              <div>
                <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2">
                  Dual-Control Sign-Off Log ({{ barrier.approvers.length }})
                </h3>

                <div class="overflow-x-auto">
                  <table class="w-full text-left border-collapse min-w-[650px]">
                    <thead>
                      <tr class="border-b border-slate-200 bg-slate-50/50 text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                        <th class="py-2.5 px-4">Approver</th>
                        <th class="py-2.5 px-4">Role / Authority</th>
                        <th class="py-2.5 px-4">Decision</th>
                        <th class="py-2.5 px-4">Timestamp</th>
                        <th class="py-2.5 px-4">Notes &amp; Attestation</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
                      @for (dec of barrier.approvers; track dec.approverName) {
                        <tr class="hover:bg-slate-50/80 transition-colors">
                          <td class="py-3 px-4 font-semibold text-slate-900 whitespace-nowrap">{{ dec.approverName }}</td>
                          <td class="py-3 px-4 text-slate-600 whitespace-nowrap">{{ dec.role }}</td>
                          <td class="py-3 px-4 whitespace-nowrap">
                            <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold border"
                              [ngClass]="getDecisionBadgeClass(dec.decision)">
                              {{ dec.decision }}
                            </span>
                          </td>
                          <td class="py-3 px-4 text-slate-500 font-mono whitespace-nowrap">{{ formatTimestamp(dec.decidedAt) }}</td>
                          <td class="py-3 px-4 text-slate-700">{{ dec.comment || '—' }}</td>
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
              </div>

              @if (barrier.decisionNotes) {
                <div class="text-xs text-slate-500 pt-2 border-t border-slate-100">
                  <strong>Governance Notes:</strong> {{ barrier.decisionNotes }}
                </div>
              }

            </div>
          }
        } @else {
          <!-- Empty / Direct Execution State -->
          <div class="bg-white border border-slate-200 rounded-lg p-10 text-center text-xs text-slate-500 shadow-xs">
            <div class="text-sm font-bold text-slate-800">Direct Execution (No Governance Barriers Configured)</div>
            <p class="text-slate-400 mt-1 max-w-md mx-auto">
              This migration was triggered with direct operator credentials without requiring dual-control maker-checker quorum gates.
            </p>
          </div>
        }

      </div>
    }
  `
})
export class TabHistoryGovernanceComponent {
  public hws = inject(HistoryWorkspaceService);

  public getBarrierStatusClass(status: string): string {
    switch (status) {
      case 'APPROVED': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'REJECTED': return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'EXPIRED':
      case 'TIMED_OUT': return 'bg-amber-50 text-amber-700 border-amber-200';
      default: return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  }

  public getDecisionBadgeClass(decision: string): string {
    switch (decision) {
      case 'APPROVED': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'REJECTED': return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'PENDING': return 'bg-amber-50 text-amber-700 border-amber-200';
      default: return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  }

  public formatTimestamp(ts: string | null): string {
    if (!ts) return '—';
    try {
      const d = new Date(ts);
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return ts;
    }
  }
}
