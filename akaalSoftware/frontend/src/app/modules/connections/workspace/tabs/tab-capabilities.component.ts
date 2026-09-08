import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ConnectionWorkspaceService } from '../connection-workspace.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-tab-capabilities',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    @if (ws.connection(); as conn) {
      <div class="flex flex-col gap-6 animate-in fade-in duration-150 text-xs select-none">
        
        <!-- Staleness Banner -->
        @if (ws.isVerificationStale()) {
          <div class="p-4 bg-amber-50/80 border border-amber-200 rounded-xl flex items-center justify-between gap-4 text-xs text-amber-900 shadow-2xs">
            <div class="flex items-center gap-2.5">
              <app-lucide-icon name="alert-triangle" [size]="16" class="text-amber-600 shrink-0"></app-lucide-icon>
              <span>
                <strong>Capability Attestation Stale:</strong> Connection configuration has changed since the last test. Proof results may no longer reflect the physical endpoint state.
              </span>
            </div>
            <button
              type="button"
              (click)="ws.testConnection()"
              class="px-3 py-1 rounded text-xs font-semibold bg-amber-600 hover:bg-amber-700 text-white transition-colors cursor-pointer shrink-0">
              Retest Now
            </button>
          </div>
        }

        <!-- Top Header & Action Controls (Text-Only Actions) -->
        <div class="flex items-center justify-between pb-3 border-b border-slate-200 flex-wrap gap-3">
          <div class="flex flex-col gap-0.5">
            <div class="flex items-center gap-2.5">
              <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider font-heading">
                Endpoint Capabilities &amp; Attestation
              </h2>
              <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-50 text-blue-700 border border-blue-200">
                {{ conn.capabilities.proofLevel }}
              </span>
            </div>
            <p class="text-xs text-slate-500 font-normal">
              Factual verification probes, permission introspection, CDC capture fidelity, and discovery capabilities.
            </p>
          </div>

          <!-- Action Probes Bar (Text-Only, No Icons) -->
          <div class="flex items-center gap-2 flex-wrap">
            <button
              type="button"
              (click)="ws.testConnection()"
              [disabled]="ws.isRunningTest()"
              class="h-8 px-3.5 rounded-md text-xs font-semibold bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 transition-colors cursor-pointer shadow-2xs disabled:opacity-50">
              {{ ws.isRunningTest() ? 'Testing Connection...' : 'Test Connection' }}
            </button>

            <button
              type="button"
              (click)="ws.runPermissionProbe()"
              [disabled]="ws.isRunningPermissionProbe()"
              class="h-8 px-3.5 rounded-md text-xs font-semibold bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 transition-colors cursor-pointer shadow-2xs disabled:opacity-50">
              {{ ws.isRunningPermissionProbe() ? 'Checking Permissions...' : 'Run Permission Check' }}
            </button>

            <button
              type="button"
              (click)="ws.runCapabilityProbe()"
              [disabled]="ws.isRunningCapabilityProbe()"
              class="h-8 px-3.5 rounded-md text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white transition-colors cursor-pointer shadow-2xs disabled:opacity-50">
              {{ ws.isRunningCapabilityProbe() ? 'Probing Engine...' : 'Run Capability Check' }}
            </button>
          </div>
        </div>

        <!-- ========================================================================= -->
        <!-- 1. CONNECTIVITY PROBE MULTI-PHASE BREAKDOWN                               -->
        <!-- ========================================================================= -->
        <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div class="flex items-center gap-2">
              <app-lucide-icon name="activity" [size]="16" class="text-blue-600"></app-lucide-icon>
              <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
                1. Point-in-Time Connectivity Probes
              </span>
            </div>
            <span class="text-[11px] text-slate-400">
              Last checked: {{ conn.capabilities.lastCheckedAt ? (conn.capabilities.lastCheckedAt | date:'medium') : 'Never' }}
            </span>
          </div>

          <div class="divide-y divide-slate-100 border border-slate-200 rounded-lg overflow-hidden">
            @for (probe of conn.capabilities.connectivityProbes; track probe.step) {
              <div class="p-3.5 flex items-center justify-between gap-3 hover:bg-slate-50/50 transition-colors flex-wrap">
                <div class="flex items-center gap-3 min-w-[240px]">
                  <span
                    class="w-2.5 h-2.5 rounded-full shrink-0"
                    [class.bg-emerald-500]="probe.status === 'VERIFIED'"
                    [class.bg-rose-500]="probe.status === 'FAILED'"
                    [class.bg-slate-300]="probe.status === 'NOT_CHECKED'">
                  </span>
                  <div class="flex flex-col">
                    <span class="text-xs font-bold text-slate-900">{{ probe.name }}</span>
                    <span class="text-[11px] text-slate-500 font-mono">{{ probe.step }}</span>
                  </div>
                </div>

                <div class="flex items-center gap-4">
                  <span class="text-xs text-slate-600 max-w-md truncate">{{ probe.details }}</span>
                  @if (probe.latencyMs !== undefined) {
                    <span class="text-[11px] font-mono text-slate-400 font-medium whitespace-nowrap">{{ probe.latencyMs }}ms</span>
                  }
                  <span
                    class="px-2 py-0.5 rounded text-[10px] font-mono font-bold whitespace-nowrap"
                    [class.bg-emerald-50]="probe.status === 'VERIFIED'"
                    [class.text-emerald-700]="probe.status === 'VERIFIED'"
                    [class.border-emerald-200]="probe.status === 'VERIFIED'"
                    [class.border]="true"
                    [class.bg-rose-50]="probe.status === 'FAILED'"
                    [class.text-rose-700]="probe.status === 'FAILED'"
                    [class.border-rose-200]="probe.status === 'FAILED'"
                    [class.bg-slate-50]="probe.status === 'NOT_CHECKED'"
                    [class.text-slate-600]="probe.status === 'NOT_CHECKED'"
                    [class.border-slate-200]="probe.status === 'NOT_CHECKED'">
                    {{ probe.status }}
                  </span>
                </div>
              </div>
            }
          </div>
        </div>

        <!-- ========================================================================= -->
        <!-- 2. PERMISSION PROBE PRIVILEGES MATRIX                                     -->
        <!-- ========================================================================= -->
        <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div class="flex items-center gap-2">
              <app-lucide-icon name="shield-check" [size]="16" class="text-blue-600"></app-lucide-icon>
              <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
                2. Introspected Permissions &amp; Privileges
              </span>
            </div>
            <span class="text-[11px] text-slate-500">
              Evaluated against assigned principal: <strong class="font-mono text-slate-800">{{ conn.authConfig.username || 'Current Identity' }}</strong>
            </span>
          </div>

          <div class="divide-y divide-slate-100 border border-slate-200 rounded-lg overflow-hidden">
            @for (perm of conn.capabilities.permissionChecks; track perm.permission) {
              <div class="p-3 flex items-center justify-between gap-3 hover:bg-slate-50/50 transition-colors">
                <div class="flex items-center gap-3">
                  <span class="font-mono font-bold text-xs text-slate-900">{{ perm.permission }}</span>
                  <span class="text-[11px] text-slate-400 font-medium">[{{ perm.scope }}]</span>
                </div>

                <div class="flex items-center gap-3">
                  <span class="text-xs text-slate-600">{{ perm.details }}</span>
                  <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {{ perm.status }}
                  </span>
                </div>
              </div>
            }

            @if (conn.capabilities.permissionChecks.length === 0) {
              <div class="p-4 text-center text-slate-400 text-xs bg-slate-50">
                No active permission checks evaluated. Click "Run Permission Check" above to probe privileges.
              </div>
            }
          </div>
        </div>

        <!-- ========================================================================= -->
        <!-- 3. MIGRATION & SYNCHRONIZATION ENGINE CAPABILITIES                         -->
        <!-- ========================================================================= -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          <!-- Source & Extraction Capability -->
          <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-3.5">
            <div class="flex items-center justify-between pb-2.5 border-b border-slate-100">
              <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Source Engine Extraction</span>
              <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                {{ conn.capabilities.sourceCapability.status }}
              </span>
            </div>
            <div class="flex flex-col gap-2">
              <div class="flex items-center justify-between">
                <span class="text-slate-500">Extraction Throughput:</span>
                <span class="font-semibold text-slate-800">{{ conn.capabilities.sourceCapability.throughputRating }}</span>
              </div>
              <p class="text-xs text-slate-600 leading-relaxed">{{ conn.capabilities.sourceCapability.details }}</p>
            </div>
          </div>

          <!-- Target & Write Capability -->
          <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-3.5">
            <div class="flex items-center justify-between pb-2.5 border-b border-slate-100">
              <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Target Engine Ingestion</span>
              <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                {{ conn.capabilities.targetCapability.status }}
              </span>
            </div>
            <div class="flex flex-col gap-2">
              <div class="flex items-center justify-between">
                <span class="text-slate-500">ACID Transactional Ingestion:</span>
                <span class="font-semibold text-slate-800">{{ conn.capabilities.targetCapability.acidCompliant ? 'Supported' : 'Non-Transactional / Streaming' }}</span>
              </div>
              <p class="text-xs text-slate-600 leading-relaxed">{{ conn.capabilities.targetCapability.details }}</p>
            </div>
          </div>

          <!-- Discovery Engine -->
          <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-3.5">
            <div class="flex items-center justify-between pb-2.5 border-b border-slate-100">
              <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Metadata Discovery Fidelity</span>
              <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                {{ conn.capabilities.discoveryCapability.status }}
              </span>
            </div>
            <div class="flex flex-col gap-2">
              <span class="text-[11px] text-slate-500">Supported Schema Object Classes:</span>
              <div class="flex flex-wrap gap-1.5">
                @for (obj of conn.capabilities.discoveryCapability.supportedObjectTypes; track obj) {
                  <span class="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
                    {{ obj }}
                  </span>
                }
              </div>
            </div>
          </div>

          <!-- CDC Engine (Truthful Representation) -->
          <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-3.5">
            <div class="flex items-center justify-between pb-2.5 border-b border-slate-100">
              <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">CDC &amp; Continuous Replication</span>
              <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-50 text-blue-700 border border-blue-200">
                {{ conn.capabilities.cdcCapability.status }}
              </span>
            </div>
            <div class="flex flex-col gap-1.5">
              <div class="font-bold text-slate-900">{{ conn.capabilities.cdcCapability.label }}</div>
              <p class="text-xs text-slate-600 leading-relaxed">{{ conn.capabilities.cdcCapability.details }}</p>
            </div>
          </div>

        </div>

        <!-- ========================================================================= -->
        <!-- 4. PROVIDER LIMITATIONS                                                   -->
        <!-- ========================================================================= -->
        @if (conn.capabilities.providerLimitations.length > 0) {
          <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-3">
            <div class="flex items-center gap-2 pb-2.5 border-b border-slate-100">
              <app-lucide-icon name="alert-triangle" [size]="15" class="text-amber-600"></app-lucide-icon>
              <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
                Provider Constraints &amp; Architectural Limitations
              </span>
            </div>
            <ul class="list-disc list-inside space-y-1.5 text-xs text-slate-600">
              @for (lim of conn.capabilities.providerLimitations; track lim) {
                <li class="leading-relaxed">{{ lim }}</li>
              }
            </ul>
          </div>
        }

      </div>
    }
  `
})
export class TabCapabilitiesComponent {
  public ws = inject(ConnectionWorkspaceService);
}
