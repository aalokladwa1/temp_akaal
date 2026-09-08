import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CreateConnectionService } from '../create-connection.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-step4-capabilities',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="max-w-5xl mx-auto w-full space-y-6 select-none animate-in fade-in duration-150 text-xs font-sans">
      
      <!-- Top Section Header -->
      <div class="flex flex-col gap-1 border-b border-slate-200 pb-3">
        <div class="flex items-center justify-between flex-wrap gap-2">
          <div class="flex flex-col gap-0.5">
            <h2 class="text-base font-bold text-slate-900 tracking-tight">Capabilities &amp; Point-in-Time Verification</h2>
            <p class="text-xs text-slate-500 font-normal">
              Execute live point-in-time connectivity, privilege introspection, and engine capability probes.
            </p>
          </div>

          <!-- Primary Test Trigger (Text-Led Action Button, No Icon) -->
          <button
            type="button"
            (click)="cs.runTestConnection()"
            [disabled]="cs.draft().isTesting"
            class="h-8 px-4 rounded-md bg-blue-600 hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 text-white text-xs font-semibold transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-2xs">
            {{ cs.draft().isTesting ? 'Testing Probe...' : 'Test Connection' }}
          </button>
        </div>
      </div>

      <!-- Staleness Advisory Banner (When upstream fields were changed after a test) -->
      @if (cs.draft().isStaleVerification) {
        <div class="p-3.5 bg-amber-50 border border-amber-300 rounded-xl flex items-center justify-between gap-3 text-xs animate-in fade-in duration-100">
          <div class="flex items-center gap-2">
            <app-lucide-icon name="alert-triangle" [size]="16" class="text-amber-600 shrink-0"></app-lucide-icon>
            <span class="font-semibold text-amber-900">
              Configuration Changed Since Last Verification: Prior probe facts are stale. Re-run Test Connection to confirm.
            </span>
          </div>
          <button
            type="button"
            (click)="cs.runTestConnection()"
            class="px-2.5 py-1 text-xs font-semibold text-amber-900 bg-white border border-amber-300 hover:bg-amber-50 rounded-md cursor-pointer">
            Re-test Now
          </button>
        </div>
      }

      <!-- Untested Hero Banner (When not yet tested) -->
      @if (cs.draft().verificationFacts.overallStatus === 'UNTESTED' && !cs.draft().isTesting) {
        <div class="p-8 bg-white border border-dashed border-slate-300 rounded-2xl flex flex-col items-center justify-center text-center gap-4">
          <div class="w-12 h-12 rounded-2xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
            <app-lucide-icon name="activity" [size]="24"></app-lucide-icon>
          </div>
          <div class="flex flex-col gap-1 max-w-md">
            <span class="text-sm font-bold text-slate-900">Point-in-Time Probe Ready</span>
            <p class="text-xs text-slate-500 font-normal leading-relaxed">
              Verify DNS resolution, socket reachability, TLS handshake, authentication attestation, and CDC prerequisites before creating the connection resource.
            </p>
          </div>
          <button
            type="button"
            (click)="cs.runTestConnection()"
            class="h-9 px-5 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition-colors cursor-pointer shadow-xs">
            Test Connection
          </button>
        </div>
      }

      <!-- Active Testing Skeleton Pulse -->
      @if (cs.draft().isTesting) {
        <div class="p-8 bg-white border border-slate-200 rounded-2xl flex flex-col items-center justify-center gap-3 animate-pulse">
          <div class="w-8 h-8 rounded-full border-2 border-blue-600 border-t-transparent animate-spin"></div>
          <span class="text-xs font-semibold text-slate-700">Dispatching point-in-time connectivity probe...</span>
          <span class="text-[11px] text-slate-400">Testing TCP socket, TLS ciphers, and authentication handshake</span>
        </div>
      }

      <!-- Tested Results View -->
      @if (cs.draft().verificationFacts.overallStatus === 'PASSED' && !cs.draft().isTesting) {
        
        <!-- ========================================================================= -->
        <!-- SECTION 1: CONNECTIVITY FACTS CARD                                        -->
        <!-- ========================================================================= -->
        <div class="p-5 bg-white border border-slate-200 rounded-xl space-y-4 shadow-2xs">
          <div class="pb-2 border-b border-slate-100 flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-900">1. Connectivity Facts</span>
              <span class="px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 font-mono">
                ALL PASSED
              </span>
            </div>
            <span class="text-[11px] text-slate-400 font-mono">
              Tested: {{ cs.draft().verificationFacts.testedAt | date:'mediumTime' }}
            </span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            @for (fact of cs.draft().verificationFacts.connectivity; track fact.key) {
              <div class="p-3 bg-slate-50/75 border border-slate-200 rounded-lg flex items-center justify-between gap-3 text-xs">
                <div class="flex items-center gap-2.5 min-w-0">
                  <div class="w-2 h-2 rounded-full bg-emerald-500 shrink-0"></div>
                  <div class="flex flex-col min-w-0">
                    <span class="font-semibold text-slate-800 truncate">{{ fact.label }}</span>
                    <span class="text-[11px] text-slate-500 truncate">{{ fact.value }}</span>
                  </div>
                </div>

                @if (fact.latencyMs !== undefined) {
                  <span class="text-[10px] font-mono text-slate-400 bg-white px-1.5 py-0.5 rounded border border-slate-200 shrink-0">
                    {{ fact.latencyMs }}ms
                  </span>
                }
              </div>
            }
          </div>
        </div>

        <!-- ========================================================================= -->
        <!-- SECTION 2: PERMISSION PROBE CARD                                          -->
        <!-- ========================================================================= -->
        <div class="p-5 bg-white border border-slate-200 rounded-xl space-y-4 shadow-2xs">
          <div class="pb-2 border-b border-slate-100 flex items-center justify-between flex-wrap gap-2">
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-900">2. Permission Probe</span>
              <span class="text-[11px] text-slate-400 font-normal">Introspect catalog privileges</span>
            </div>

            <button
              type="button"
              (click)="cs.runPermissionProbe()"
              [disabled]="cs.draft().isTestingPermissions"
              class="h-7 px-3 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors cursor-pointer">
              {{ cs.draft().isTestingPermissions ? 'Checking Privileges...' : (cs.draft().verificationFacts.permissions.length > 0 ? 'Re-run Permission Check' : 'Run Permission Check') }}
            </button>
          </div>

          @if (cs.draft().verificationFacts.permissions.length === 0 && !cs.draft().isTestingPermissions) {
            <div class="py-4 text-center text-slate-400 text-xs bg-slate-50/50 rounded-lg border border-dashed border-slate-200">
              Permission probe has not yet been executed for this endpoint. Click "Run Permission Check" to introspect.
            </div>
          }

          @if (cs.draft().verificationFacts.permissions.length > 0) {
            <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2.5">
              @for (perm of cs.draft().verificationFacts.permissions; track perm.privilege) {
                <div class="p-2.5 bg-slate-50 border border-slate-200 rounded-lg flex flex-col justify-between gap-1 text-xs">
                  <span class="font-bold text-slate-900 text-[11px] truncate">{{ perm.privilege }}</span>
                  <div class="flex items-center justify-between text-[10px]">
                    <span class="text-slate-400 font-mono">{{ perm.scope || 'ALL' }}</span>
                    <span class="px-1.5 py-0.2 rounded font-bold"
                      [class]="perm.status === 'VERIFIED'
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : 'bg-slate-100 text-slate-500 border border-slate-200'">
                      {{ perm.status }}
                    </span>
                  </div>
                </div>
              }
            </div>
          }
        </div>

        <!-- ========================================================================= -->
        <!-- SECTION 3: CAPABILITY PROBE CARD                                          -->
        <!-- ========================================================================= -->
        <div class="p-5 bg-white border border-slate-200 rounded-xl space-y-4 shadow-2xs">
          <div class="pb-2 border-b border-slate-100 flex items-center justify-between flex-wrap gap-2">
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-900">3. Engine Capabilities &amp; Prerequisites</span>
              <span class="text-[11px] text-slate-400 font-normal">CDC, Snapshot, &amp; Ingestion Fastpaths</span>
            </div>

            <button
              type="button"
              (click)="cs.runCapabilityProbe()"
              [disabled]="cs.draft().isTestingCapabilities"
              class="h-7 px-3 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors cursor-pointer">
              {{ cs.draft().isTestingCapabilities ? 'Checking Capabilities...' : (cs.draft().verificationFacts.capabilities.length > 0 ? 'Re-run Capability Check' : 'Run Capability Check') }}
            </button>
          </div>

          @if (cs.draft().verificationFacts.capabilities.length === 0 && !cs.draft().isTestingCapabilities) {
            <div class="py-4 text-center text-slate-400 text-xs bg-slate-50/50 rounded-lg border border-dashed border-slate-200">
              Capability probe has not yet been executed. Click "Run Capability Check" to evaluate engine features.
            </div>
          }

          @if (cs.draft().verificationFacts.capabilities.length > 0) {
            <div class="space-y-2">
              @for (cap of cs.draft().verificationFacts.capabilities; track cap.capability) {
                <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between gap-3 text-xs">
                  <div class="flex items-center gap-2.5 min-w-0">
                    <span class="px-1.5 py-0.5 text-[9px] font-bold font-mono bg-blue-50 text-blue-700 border border-blue-200 rounded shrink-0">
                      {{ cap.category }}
                    </span>
                    <div class="flex flex-col min-w-0">
                      <span class="font-semibold text-slate-900 truncate">{{ cap.capability }}</span>
                      <span class="text-[11px] text-slate-500 truncate">{{ cap.detail }}</span>
                    </div>
                  </div>

                  <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 shrink-0">
                    {{ cap.status }}
                  </span>
                </div>
              }
            </div>
          }
        </div>

        <!-- ========================================================================= -->
        <!-- SECTION 4: ELIGIBILITY, CDC TRUTH & VALIDATION #11                        -->
        <!-- ========================================================================= -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          
          <!-- Card A: Source / Target Eligibility & Discovery -->
          <div class="p-5 bg-white border border-slate-200 rounded-xl space-y-3 shadow-2xs">
            <span class="text-xs font-bold text-slate-900">4. Role Eligibility &amp; Discovery</span>
            
            <div class="space-y-2 text-xs">
              <div class="flex items-center justify-between p-2.5 bg-slate-50 border border-slate-200 rounded-lg">
                <span class="font-medium text-slate-700">Source Workload Eligibility</span>
                <span class="font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded text-[10px]">
                  {{ cs.draft().verificationFacts.sourceEligibility }}
                </span>
              </div>

              <div class="flex items-center justify-between p-2.5 bg-slate-50 border border-slate-200 rounded-lg">
                <span class="font-medium text-slate-700">Target Workload Eligibility</span>
                <span class="font-bold px-2 py-0.5 rounded text-[10px]"
                  [class]="cs.draft().verificationFacts.targetEligibility === 'AVAILABLE'
                    ? 'text-emerald-700 bg-emerald-50 border border-emerald-200'
                    : 'text-amber-700 bg-amber-50 border border-amber-200'">
                  {{ cs.draft().verificationFacts.targetEligibility }}
                </span>
              </div>

              <div class="flex items-center justify-between p-2.5 bg-slate-50 border border-slate-200 rounded-lg">
                <span class="font-medium text-slate-700">Catalog Schema Discovery</span>
                <span class="font-bold text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded text-[10px]">
                  {{ cs.draft().verificationFacts.discoveryCapability }}
                </span>
              </div>
            </div>
          </div>

          <!-- Card B: CDC Capability & Validation #11 -->
          <div class="p-5 bg-white border border-slate-200 rounded-xl space-y-3 shadow-2xs">
            <span class="text-xs font-bold text-slate-900">5. Continuous CDC &amp; Validation #11</span>
            
            <div class="space-y-2 text-xs">
              <div class="p-2.5 bg-slate-50 border border-slate-200 rounded-lg flex flex-col gap-0.5">
                <div class="flex items-center justify-between">
                  <span class="font-semibold text-slate-800">CDC Classification:</span>
                  <span class="font-mono text-[10px] font-bold text-slate-700">
                    {{ cs.draft().verificationFacts.cdcCapability.label }}
                  </span>
                </div>
                <span class="text-[11px] text-slate-500">
                  {{ cs.draft().verificationFacts.cdcCapability.description }}
                </span>
              </div>

              <div class="p-2.5 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between">
                <div class="flex flex-col">
                  <span class="font-semibold text-slate-800">Validation #11 Capability</span>
                  <span class="text-[11px] text-slate-500">Non-mutating row checksum &amp; reconciliation</span>
                </div>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  SUPPORTED
                </span>
              </div>
            </div>
          </div>

        </div>

      }

    </div>
  `
})
export class Step4CapabilitiesComponent {
  public cs = inject(CreateConnectionService);
}
