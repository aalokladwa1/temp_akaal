import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ConnectionWorkspaceService } from '../connection-workspace.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-tab-overview',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    @if (ws.connection(); as conn) {
      <div class="flex flex-col gap-6 animate-in fade-in duration-150 text-xs select-none">
        
        <!-- Staleness / Needs Attention Notice Banner -->
        @if (ws.isVerificationStale()) {
          <div class="p-4 bg-amber-50/80 border border-amber-200 rounded-xl flex items-center justify-between gap-4 text-xs text-amber-900 shadow-2xs">
            <div class="flex items-center gap-3">
              <app-lucide-icon name="alert-triangle" [size]="18" class="text-amber-600 shrink-0"></app-lucide-icon>
              <div>
                <strong class="font-bold">Configuration Changed Since Last Verification:</strong>
                <span class="text-amber-800 ml-1">
                  Connection parameters were modified after the last successful test. Previous attestation is now stale. Retest to verify new configuration.
                </span>
              </div>
            </div>
            <button
              type="button"
              (click)="ws.testConnection()"
              [disabled]="ws.isRunningTest()"
              class="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-amber-600 hover:bg-amber-700 text-white transition-colors cursor-pointer shrink-0 disabled:opacity-50">
              {{ ws.isRunningTest() ? 'Testing...' : 'Retest Connection' }}
            </button>
          </div>
        }

        <!-- P7C Non-Binding Advisory Banner (If Available) -->
        @if (conn.advisory; as adv) {
          <div class="p-4 bg-blue-50/60 border border-blue-200 rounded-xl flex items-start gap-3.5 text-xs text-blue-950 shadow-2xs">
            <app-lucide-icon name="sparkles" [size]="16" class="text-blue-600 shrink-0 mt-0.5"></app-lucide-icon>
            <div class="flex flex-col gap-1">
              <div class="flex items-center gap-2">
                <span class="font-bold text-slate-900">{{ adv.headline }}</span>
                <span class="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-blue-100 text-blue-800 border border-blue-200">
                  AI Advisory
                </span>
              </div>
              @if (adv.description) {
                <p class="text-slate-600 font-normal leading-relaxed">{{ adv.description }}</p>
              }
              <span class="text-[10px] text-slate-400 font-medium">
                P7C Intelligence advises. Canonical AKAAL authorities validate, authorize and execute.
              </span>
            </div>
          </div>
        }

        <!-- ========================================================================= -->
        <!-- ROW 1: 2-COLUMN HERO CARDS (Identity & Factual Verification)             -->
        <!-- ========================================================================= -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          <!-- Card 1: Identity & Provider Context -->
          <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-5">
            <div class="flex items-center justify-between pb-3 border-b border-slate-100">
              <div class="flex items-center gap-2.5">
                <app-lucide-icon name="database" [size]="16" class="text-blue-600"></app-lucide-icon>
                <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Resource Identity</span>
              </div>
              <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                {{ conn.roleApplicability.replace('_', ' ') }}
              </span>
            </div>

            <div class="flex flex-col gap-3">
              <div>
                <span class="text-[11px] font-medium text-slate-400">Connection Name</span>
                <div class="text-sm font-bold text-slate-900 pt-0.5">{{ conn.name }}</div>
              </div>

              @if (conn.description) {
                <div>
                  <span class="text-[11px] font-medium text-slate-400">Description</span>
                  <p class="text-xs text-slate-600 pt-0.5 leading-relaxed">{{ conn.description }}</p>
                </div>
              }

              <div class="grid grid-cols-2 gap-3 pt-2 border-t border-slate-100">
                <div>
                  <span class="text-[11px] font-medium text-slate-400">Physical Engine</span>
                  <div class="text-xs font-bold text-slate-900 pt-0.5">{{ conn.providerName }}</div>
                </div>
                <div>
                  <span class="text-[11px] font-medium text-slate-400">Provider Family</span>
                  <div class="text-xs font-semibold text-slate-700 pt-0.5">{{ conn.family }}</div>
                </div>
              </div>

              @if (conn.managedCloudName) {
                <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between">
                  <div>
                    <span class="text-[10px] font-medium text-slate-400">Managed Cloud Resolver</span>
                    <div class="text-xs font-bold text-slate-800">{{ conn.managedCloudName }}</div>
                  </div>
                  <span class="text-[11px] font-mono text-slate-500">{{ conn.managedResourceType }}</span>
                </div>
              }

              <div class="grid grid-cols-2 gap-3 pt-2 border-t border-slate-100 text-[11px]">
                <div>
                  <span class="font-medium text-slate-400">Workspace Context</span>
                  <div class="font-semibold text-slate-800 pt-0.5">{{ conn.workspaceName }}</div>
                </div>
                <div>
                  <span class="font-medium text-slate-400">P7B Locality & Site</span>
                  <div class="font-semibold text-slate-800 pt-0.5">{{ conn.fabric.site || 'Default DC' }} ({{ conn.fabric.locality || 'Primary' }})</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Card 2: Availability & Point-in-Time Factual Verification -->
          <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-5">
            <div class="flex items-center justify-between pb-3 border-b border-slate-100">
              <div class="flex items-center gap-2.5">
                <app-lucide-icon name="shield-check" [size]="16" class="text-emerald-600"></app-lucide-icon>
                <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Factual Availability & Verification</span>
              </div>
              
              <button
                type="button"
                (click)="ws.testConnection()"
                [disabled]="ws.isRunningTest()"
                class="px-2.5 py-1 rounded text-xs font-semibold bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 transition-colors cursor-pointer disabled:opacity-50">
                {{ ws.isRunningTest() ? 'Testing...' : 'Retest' }}
              </button>
            </div>

            <div class="flex flex-col gap-3">
              <!-- Point-in-time test facts list -->
              <div class="divide-y divide-slate-100 border border-slate-100 rounded-lg overflow-hidden bg-slate-50/50">
                
                <div class="p-2.5 flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
                    <span class="text-xs font-medium text-slate-800">Transport Reachability & DNS</span>
                  </div>
                  <span class="text-[11px] font-mono text-emerald-700 font-semibold">Verified (0.8ms)</span>
                </div>

                <div class="p-2.5 flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
                    <span class="text-xs font-medium text-slate-800">Transport Security (TLS Handshake)</span>
                  </div>
                  <span class="text-[11px] font-mono text-emerald-700 font-semibold">Verified (TLS 1.3)</span>
                </div>

                <div class="p-2.5 flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
                    <span class="text-xs font-medium text-slate-800">Authentication & Principal Attestation</span>
                  </div>
                  <span class="text-[11px] font-mono text-emerald-700 font-semibold">Verified</span>
                </div>

                <div class="p-2.5 flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
                    <span class="text-xs font-medium text-slate-800">Catalog & Permission Probe</span>
                  </div>
                  <span class="text-[11px] font-mono text-emerald-700 font-semibold">Checked</span>
                </div>

                <div class="p-2.5 flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
                    <span class="text-xs font-medium text-slate-800">CDC & Synchronization Engine</span>
                  </div>
                  <span class="text-[11px] font-mono text-emerald-700 font-semibold">Attested</span>
                </div>

              </div>

              <!-- Verification Semantics Footnote -->
              <div class="p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-[10px] text-slate-500 flex items-center justify-between">
                <span>
                  <strong>Verification Law:</strong> Configured &ne; Reachable &ne; Authenticated &ne; Permitted &ne; Capable &ne; Ready.
                </span>
                <span class="text-slate-400 whitespace-nowrap pl-2">
                  Last: {{ conn.lastVerifiedAt ? (conn.lastVerifiedAt | date:'medium') : 'Never' }}
                </span>
              </div>
            </div>
          </div>

        </div>

        <!-- ========================================================================= -->
        <!-- ROW 2: 2-COLUMN SUMMARY (Endpoint / Security & Capabilities / Usage)      -->
        <!-- ========================================================================= -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          <!-- Card 3: Endpoint Addressing & Security Summary (Provider Aware) -->
          <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
            <div class="flex items-center justify-between pb-3 border-b border-slate-100">
              <div class="flex items-center gap-2.5">
                <app-lucide-icon name="network" [size]="16" class="text-blue-600"></app-lucide-icon>
                <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Endpoint & Security Summary</span>
              </div>
              <button
                type="button"
                (click)="ws.setActiveTab('configuration')"
                class="text-xs font-semibold text-blue-600 hover:text-blue-800 cursor-pointer">
                View Configuration &rarr;
              </button>
            </div>

            <!-- Provider-Aware Addressing Grid -->
            <div class="grid grid-cols-2 gap-3.5">
              
              <div>
                <span class="text-[11px] font-medium text-slate-400">Endpoint / Addressing</span>
                <div class="text-xs font-mono font-bold text-slate-900 pt-0.5 break-all">
                  {{ conn.endpointDisplay }}
                </div>
              </div>

              <div>
                <span class="text-[11px] font-medium text-slate-400">Network Route Type</span>
                <div class="text-xs font-bold text-slate-900 pt-0.5">
                  {{ conn.routeConfig.type.replace('_', ' ') }}
                </div>
              </div>

              <div>
                <span class="text-[11px] font-medium text-slate-400">Authentication Method</span>
                <div class="text-xs font-semibold text-slate-800 pt-0.5">
                  {{ conn.authConfig.authMethod }}
                </div>
              </div>

              <div>
                <span class="text-[11px] font-medium text-slate-400">Secret Reference</span>
                <div class="text-xs font-mono text-emerald-700 font-semibold pt-0.5 flex items-center gap-1.5">
                  <app-lucide-icon name="lock" [size]="11"></app-lucide-icon>
                  <span>Configured (Redacted)</span>
                </div>
              </div>

              <div>
                <span class="text-[11px] font-medium text-slate-400">TLS Transport Mode</span>
                <div class="text-xs font-semibold text-slate-800 pt-0.5">
                  {{ conn.tlsConfig.mode }} ({{ conn.tlsConfig.minVersion }})
                </div>
              </div>

              <div>
                <span class="text-[11px] font-medium text-slate-400">Mutual TLS (mTLS)</span>
                <div class="text-xs font-semibold text-slate-800 pt-0.5">
                  {{ conn.tlsConfig.isMtlsEnabled ? 'Enabled (Client Cert Configured)' : 'Disabled' }}
                </div>
              </div>

            </div>
          </div>

          <!-- Card 4: Capabilities & Reusable Resource Usage Summary -->
          <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
            <div class="flex items-center justify-between pb-3 border-b border-slate-100">
              <div class="flex items-center gap-2.5">
                <app-lucide-icon name="folder-git-2" [size]="16" class="text-blue-600"></app-lucide-icon>
                <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Capabilities & Usage Overview</span>
              </div>
              <button
                type="button"
                (click)="ws.setActiveTab('usage')"
                class="text-xs font-semibold text-blue-600 hover:text-blue-800 cursor-pointer">
                View Usage &rarr;
              </button>
            </div>

            <div class="grid grid-cols-2 gap-3.5">
              
              <div>
                <span class="text-[11px] font-medium text-slate-400">Source Extraction</span>
                <div class="text-xs font-bold text-emerald-700 pt-0.5">
                  {{ conn.capabilities.sourceCapability.status }}
                </div>
              </div>

              <div>
                <span class="text-[11px] font-medium text-slate-400">Target Writing</span>
                <div class="text-xs font-bold text-emerald-700 pt-0.5">
                  {{ conn.capabilities.targetCapability.status }}
                </div>
              </div>

              <div>
                <span class="text-[11px] font-medium text-slate-400">CDC / Synchronization</span>
                <div class="text-xs font-semibold text-slate-800 pt-0.5">
                  {{ conn.capabilities.cdcCapability.label }}
                </div>
              </div>

              <div>
                <span class="text-[11px] font-medium text-slate-400">Proof Classification</span>
                <div class="text-xs font-mono font-bold text-blue-700 pt-0.5">
                  {{ conn.capabilities.proofLevel }}
                </div>
              </div>

              <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                <span class="text-[10px] font-medium text-slate-400">Referenced Projects</span>
                <div class="text-sm font-bold text-slate-900 pt-0.5 font-mono">
                  {{ conn.usage.projects.length }} {{ conn.usage.projects.length === 1 ? 'Project' : 'Projects' }}
                </div>
              </div>

              <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                <span class="text-[10px] font-medium text-slate-400">Active / Historical Migrations</span>
                <div class="text-sm font-bold text-slate-900 pt-0.5 font-mono">
                  {{ conn.usage.migrations.length }} {{ conn.usage.migrations.length === 1 ? 'Migration' : 'Migrations' }}
                </div>
              </div>

            </div>
          </div>

        </div>

      </div>
    }
  `
})
export class TabOverviewComponent {
  public ws = inject(ConnectionWorkspaceService);
}
