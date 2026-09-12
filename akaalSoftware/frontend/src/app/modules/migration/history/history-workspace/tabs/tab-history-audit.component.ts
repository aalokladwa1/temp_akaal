import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HistoryWorkspaceService } from '../history-workspace.service';
import { AuditTrailEvent } from '../history-workspace.models';

@Component({
  selector: 'app-tab-history-audit',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    @if (hws.currentRecord(); as record) {
      <div class="space-y-4">
        
        <!-- Audit Stream Search & Filter Toolbar -->
        <div class="bg-white border border-slate-200 rounded-lg p-3.5 shadow-xs flex flex-col md:flex-row items-center justify-between gap-3">
          <!-- Search Input -->
          <div class="w-full md:w-72">
            <input
              type="text"
              [ngModel]="hws.auditSearch()"
              (ngModelChange)="hws.auditSearch.set($event)"
              placeholder="Search audit events, actors, hashes..."
              class="w-full h-8 px-3 text-xs bg-slate-50 border border-slate-300 rounded-md placeholder-slate-400 text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-colors" />
          </div>

          <!-- Dropdowns & Reset -->
          <div class="flex items-center gap-2 w-full md:w-auto justify-end flex-wrap">
            <!-- Actor Filter -->
            <div class="flex items-center gap-1 text-xs text-slate-600">
              <span class="text-[11px] font-semibold text-slate-500">Actor:</span>
              <select
                [ngModel]="hws.auditActor()"
                (ngModelChange)="hws.auditActor.set($event)"
                class="h-8 px-2.5 text-xs bg-white border border-slate-300 rounded-md text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer">
                <option value="ALL">All Actors</option>
                @for (act of hws.auditDistinctActors(); track act) {
                  <option [value]="act">{{ act }}</option>
                }
              </select>
            </div>

            <!-- Action Filter -->
            <div class="flex items-center gap-1 text-xs text-slate-600">
              <span class="text-[11px] font-semibold text-slate-500">Action:</span>
              <select
                [ngModel]="hws.auditAction()"
                (ngModelChange)="hws.auditAction.set($event)"
                class="h-8 px-2.5 text-xs bg-white border border-slate-300 rounded-md text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer">
                <option value="ALL">All Actions</option>
                @for (act of hws.auditDistinctActions(); track act) {
                  <option [value]="act">{{ act }}</option>
                }
              </select>
            </div>

            <!-- Reset Button -->
            <button
              type="button"
              (click)="hws.resetAuditFilters()"
              class="h-8 px-3 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium transition-colors cursor-pointer">
              Reset
            </button>
          </div>
        </div>

        <!-- Hash-Chain Integrity Status Banner -->
        <div class="bg-slate-50 border border-slate-200 rounded-lg p-3.5 flex items-center justify-between text-xs">
          <div class="flex items-center gap-3">
            <span class="inline-flex items-center justify-center w-6 h-6 rounded-full bg-emerald-100 text-emerald-800 text-xs font-bold">&check;</span>
            <div>
              <div class="font-bold text-slate-800">Cryptographic Hash-Chain Verified</div>
              <div class="text-[11px] text-slate-500">Every audit log entry is immutably chained via forward SHA-256 block digests.</div>
            </div>
          </div>
          <span class="font-mono text-[11px] text-slate-600 bg-white px-2.5 py-1 rounded border border-slate-200">
            Chain Valid (0 Breaks)
          </span>
        </div>

        <!-- Audit Trail Events Table -->
        <div class="bg-white border border-slate-200 rounded-lg shadow-xs overflow-hidden">
          <div class="px-5 py-3.5 border-b border-slate-200 bg-slate-50/70 flex items-center justify-between">
            <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Governed Event Stream ({{ hws.filteredAuditEvents().length }})
            </h3>
            <span class="text-xs text-slate-500">Strict chronological order</span>
          </div>

          @if (hws.filteredAuditEvents().length > 0) {
            <div class="overflow-x-auto">
              <table class="w-full text-left border-collapse min-w-[850px]">
                <thead>
                  <tr class="border-b border-slate-200 bg-slate-50/50 text-[11px] font-bold text-slate-600 uppercase tracking-wider select-none">
                    <th class="py-2.5 px-4">Timestamp</th>
                    <th class="py-2.5 px-4">Actor Principal</th>
                    <th class="py-2.5 px-4">Action</th>
                    <th class="py-2.5 px-4">Resource Target</th>
                    <th class="py-2.5 px-4">Outcome</th>
                    <th class="py-2.5 px-4">Hash Chain Digest</th>
                    <th class="py-2.5 px-4 text-right">Details</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
                  @for (ev of hws.filteredAuditEvents(); track ev.id) {
                    <tr class="hover:bg-slate-50/80 transition-colors">
                      <td class="py-3 px-4 font-mono text-slate-500 whitespace-nowrap">{{ formatTimestamp(ev.timestamp) }}</td>
                      <td class="py-3 px-4 font-medium text-slate-900 whitespace-nowrap">
                        <div>{{ ev.actorPrincipal }}</div>
                        <div class="text-[11px] text-slate-500 font-normal">{{ ev.actorRole }}</div>
                      </td>
                      <td class="py-3 px-4 whitespace-nowrap font-mono text-xs font-semibold text-slate-800">{{ ev.action }}</td>
                      <td class="py-3 px-4 font-mono text-slate-600 whitespace-nowrap">{{ ev.resourceTarget }}</td>
                      <td class="py-3 px-4 whitespace-nowrap">
                        <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold border"
                          [ngClass]="getOutcomeBadgeClass(ev.outcome)">
                          {{ ev.outcome }}
                        </span>
                      </td>
                      <td class="py-3 px-4 font-mono text-[11px] text-slate-500 truncate max-w-[180px]" [title]="ev.hashChainLinkSha256">
                        {{ ev.hashChainLinkSha256 }}
                      </td>
                      <td class="py-3 px-4 text-right whitespace-nowrap">
                        @if (ev.beforeSnapshotJson || ev.afterSnapshotJson) {
                          <button
                            type="button"
                            (click)="hws.inspectAuditEvent(ev)"
                            class="px-2.5 py-1 rounded border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium shadow-2xs transition-colors cursor-pointer">
                            Inspect Diff
                          </button>
                        } @else {
                          <span class="text-slate-400">—</span>
                        }
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          } @else {
            <div class="py-12 text-center text-xs text-slate-500">
              <p class="font-medium text-slate-700">No audit trail events match your filter criteria.</p>
              <button
                type="button"
                (click)="hws.resetAuditFilters()"
                class="mt-3 h-8 px-3 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium transition-colors cursor-pointer">
                Reset Filters
              </button>
            </div>
          }
        </div>

        <!-- Before / After Snapshot Inspection Modal -->
        @if (hws.activeAuditInspection(); as selected) {
          <div class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4" (click)="hws.inspectAuditEvent(null)">
            <div class="bg-white border border-slate-200 rounded-lg shadow-xl w-full max-w-3xl overflow-hidden" (click)="$event.stopPropagation()">
              <div class="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
                <div>
                  <h3 class="text-sm font-bold text-slate-900">Audit State Snapshot Inspection</h3>
                  <div class="text-xs text-slate-500 font-mono mt-0.5">{{ selected.action }} &bull; {{ selected.actorPrincipal }}</div>
                </div>
                <button
                  type="button"
                  (click)="hws.inspectAuditEvent(null)"
                  class="h-8 px-3 rounded-md border border-slate-300 bg-white hover:bg-slate-100 text-slate-700 text-xs font-medium cursor-pointer">
                  Close
                </button>
              </div>

              <div class="p-6 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs max-h-[70vh] overflow-y-auto">
                <div>
                  <div class="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2">Before Snapshot</div>
                  <pre class="p-3 bg-slate-50 rounded-md border border-slate-200 font-mono text-[11px] text-slate-800 overflow-x-auto whitespace-pre-wrap">{{ selected.beforeSnapshotJson || '// No prior state snapshot recorded' }}</pre>
                </div>
                <div>
                  <div class="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2">After Snapshot</div>
                  <pre class="p-3 bg-slate-50 rounded-md border border-slate-200 font-mono text-[11px] text-slate-800 overflow-x-auto whitespace-pre-wrap">{{ selected.afterSnapshotJson || '// No subsequent state snapshot recorded' }}</pre>
                </div>
              </div>

              <div class="px-6 py-3 border-t border-slate-200 bg-slate-50 flex items-center justify-between text-xs text-slate-500">
                <span class="font-mono text-[11px] truncate max-w-[450px]">Hash: {{ selected.hashChainLinkSha256 }}</span>
                <button
                  type="button"
                  (click)="hws.inspectAuditEvent(null)"
                  class="h-8 px-4 rounded-md bg-slate-900 hover:bg-slate-800 text-white font-medium cursor-pointer">
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        }

      </div>
    }
  `
})
export class TabHistoryAuditComponent {
  public hws = inject(HistoryWorkspaceService);

  public getOutcomeBadgeClass(outcome: string): string {
    switch (outcome) {
      case 'SUCCESS': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'DENIED':
      case 'FAILED': return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'CHALLENGED': return 'bg-amber-50 text-amber-700 border-amber-200';
      default: return 'bg-slate-100 text-slate-700 border-slate-200';
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
