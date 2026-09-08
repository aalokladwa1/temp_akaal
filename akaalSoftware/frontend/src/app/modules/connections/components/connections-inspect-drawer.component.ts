import { Component, inject, Optional } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ConnectionsService } from '../connections.service';
import {
  ConnectionRecord,
  ConnectionFamily,
  ConnectionVerificationState,
  ConnectionRoleApplicability
} from '../connections.models';

@Component({
  selector: 'app-connections-inspect-drawer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div
      *ngIf="cs.isInspectDrawerOpen() && cs.selectedConnection() as conn"
      class="fixed inset-0 z-50 overflow-hidden"
      aria-labelledby="slide-over-title"
      role="dialog"
      aria-modal="true">
      
      <!-- Backdrop -->
      <div
        class="fixed inset-0 bg-slate-900/40 backdrop-blur-[2px] transition-opacity animate-fade-in"
        (click)="close()">
      </div>

      <div class="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <!-- Drawer Panel -->
        <div class="w-screen max-w-xl bg-white border-l border-slate-200 shadow-2xl flex flex-col justify-between overflow-hidden">
          
          <!-- Drawer Header -->
          <div class="px-6 py-5 border-b border-slate-200 bg-slate-50/60 flex items-start justify-between gap-4">
            <div class="flex flex-col gap-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <h2 id="slide-over-title" class="text-lg font-bold text-slate-900 truncate">
                  {{ conn.name }}
                </h2>
                <span [class]="getEnvironmentBadgeClass(conn.environment)">
                  {{ conn.environment }}
                </span>
              </div>
              <div class="flex items-center gap-2 text-xs text-slate-600">
                <span class="font-semibold text-slate-900">{{ conn.providerName }}</span>
                <span>•</span>
                <span [class]="getFamilyBadgeClass(conn.family)">{{ getFamilyLabel(conn.family) }}</span>
                <span>•</span>
                <span class="text-slate-500 font-mono text-[11px]">ID: {{ conn.id }}</span>
              </div>
            </div>

            <!-- Close Action Button (Text-led) -->
            <button
              type="button"
              (click)="close()"
              class="h-8 px-3 text-xs font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-md transition-colors cursor-pointer shadow-2xs focus:outline-hidden focus:ring-2 focus:ring-slate-400 shrink-0">
              Close
            </button>
          </div>

          <!-- Drawer Scrollable Body -->
          <div class="flex-1 overflow-y-auto px-6 py-6 space-y-6 text-sm text-slate-700">
            
            <!-- Description -->
            <div *ngIf="conn.description" class="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-600 leading-relaxed">
              {{ conn.description }}
            </div>

            <!-- Section 1: Verification Truth & Diagnostics -->
            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wider">
                  Verification Diagnostics
                </h3>
                <span [class]="getVerificationBadgeClass(conn.verificationState)">
                  <span [class]="getVerificationDotClass(conn.verificationState)"></span>
                  <span>{{ getVerificationLabel(conn.verificationState) }}</span>
                </span>
              </div>

              <div class="p-4 rounded-xl border bg-slate-50/50 space-y-3"
                [class.border-emerald-200]="conn.verificationState === 'VERIFIED_RECENT' || conn.verificationState === 'VERIFIED_POINT_IN_TIME'"
                [class.border-amber-200]="conn.verificationState === 'VERIFIED_STALE' || conn.verificationState === 'CONFIG_CHANGED_SINCE_TEST'"
                [class.border-rose-200]="conn.verificationState === 'VERIFICATION_FAILED'"
                [class.border-slate-200]="conn.verificationState !== 'VERIFIED_RECENT' && conn.verificationState !== 'VERIFIED_POINT_IN_TIME' && conn.verificationState !== 'VERIFIED_STALE' && conn.verificationState !== 'CONFIG_CHANGED_SINCE_TEST' && conn.verificationState !== 'VERIFICATION_FAILED'">
                
                <div class="flex items-start justify-between gap-2">
                  <div class="text-xs text-slate-600">
                    <div>Last Probe Check: <strong class="font-mono text-slate-900">{{ conn.lastVerifiedAt ? (conn.lastVerifiedAt | date:'medium') : 'Never tested' }}</strong></div>
                  </div>

                  <button
                    type="button"
                    [disabled]="isVerifying(conn.id)"
                    (click)="onVerify(conn)"
                    class="h-7 px-2.5 text-xs font-medium text-blue-700 bg-white border border-blue-200 hover:bg-blue-50 rounded-md transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed shadow-2xs">
                    {{ isVerifying(conn.id) ? 'Testing...' : 'Verify Now' }}
                  </button>
                </div>

                <div *ngIf="conn.lastVerifiedDetails" class="text-xs text-slate-600 bg-white p-2.5 rounded-md border border-slate-200 font-mono text-[11px] whitespace-pre-wrap">
                  {{ conn.lastVerifiedDetails }}
                </div>

                <div *ngIf="conn.verificationFailureReason" class="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 space-y-1">
                  <div class="font-bold">Probe Failure Diagnostic:</div>
                  <div class="font-mono text-[11px]">{{ conn.verificationFailureReason }}</div>
                </div>

                <div *ngIf="conn.configChangedSinceTest" class="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800 space-y-1">
                  <div class="font-bold">Configuration Mutated Since Verification:</div>
                  <p class="text-[11px]">Parameters or authentication bindings were modified after the last probe. Re-verification is recommended before dispatching production workloads.</p>
                </div>
              </div>
            </div>

            <!-- Section 2: Safe Endpoint Architecture -->
            <div class="space-y-3">
              <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wider">
                Safe Endpoint Architecture
              </h3>

              <div class="p-4 bg-white border border-slate-200 rounded-xl space-y-3 shadow-2xs">
                <div>
                  <label class="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1">
                    Safe Target Route / URI
                  </label>
                  <div class="p-2 bg-slate-50 rounded-md border border-slate-200 font-mono text-xs text-slate-900 break-all select-all">
                    {{ conn.endpointDisplay }}
                  </div>
                </div>

                <div class="grid grid-cols-2 gap-3 text-xs pt-1">
                  <div>
                    <span class="block text-[11px] text-slate-500 mb-0.5">Role Applicability</span>
                    <span class="font-medium text-slate-900">{{ getRoleLabel(conn.roleApplicability) }}</span>
                  </div>

                  <div>
                    <span class="block text-[11px] text-slate-500 mb-0.5">Transport Security</span>
                    <span class="font-mono font-medium text-slate-900">{{ conn.tlsMode || 'Not Specified' }}</span>
                  </div>

                  <div>
                    <span class="block text-[11px] text-slate-500 mb-0.5">Authentication Mechanism</span>
                    <span class="font-medium text-slate-900">{{ conn.authMethodDisplay }}</span>
                  </div>

                  <div>
                    <span class="block text-[11px] text-slate-500 mb-0.5">Network Route Info</span>
                    <span class="font-mono text-slate-900">{{ conn.safeRouteInfo || 'Default Gateway' }}</span>
                  </div>
                </div>

                <div *ngIf="conn.fabric" class="pt-2 border-t border-slate-100 text-xs space-y-1">
                  <div class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Fabric Locality & Transit</div>
                  <div class="grid grid-cols-2 gap-2 text-[11px] text-slate-600">
                    <div *ngIf="conn.fabric.site">Site: <strong class="font-mono text-slate-800">{{ conn.fabric.site }}</strong></div>
                    <div *ngIf="conn.fabric.locality">Locality: <strong class="font-mono text-slate-800">{{ conn.fabric.locality }}</strong></div>
                    <div *ngIf="conn.fabric.transitVpc">Transit VPC: <strong class="font-mono text-slate-800">{{ conn.fabric.transitVpc }}</strong></div>
                    <div *ngIf="conn.fabric.datacenterZone">Zone: <strong class="font-mono text-slate-800">{{ conn.fabric.datacenterZone }}</strong></div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Section 3: Workload & Initiative Bindings -->
            <div class="space-y-3">
              <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wider">
                Workload & Initiative Context
              </h3>

              <div class="p-4 bg-white border border-slate-200 rounded-xl space-y-3 shadow-2xs">
                <div *ngIf="!conn.usage.usageAvailable" class="text-xs text-slate-500 italic">
                  Usage telemetry not linked to current workspace authority.
                </div>

                <div *ngIf="conn.usage.usageAvailable">
                  <div class="grid grid-cols-3 gap-2 text-center p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <div>
                      <div class="text-xl font-mono font-bold text-slate-900">{{ conn.usage.referencedProjectCount }}</div>
                      <div class="text-[11px] text-slate-500">Referenced Projects</div>
                    </div>
                    <div>
                      <div class="text-xl font-mono font-bold text-slate-900">{{ conn.usage.activeMigrationCount }}</div>
                      <div class="text-[11px] text-slate-500">Active Migrations</div>
                    </div>
                    <div>
                      <div class="text-xl font-mono font-bold text-slate-900">{{ conn.usage.activeValidationCount }}</div>
                      <div class="text-[11px] text-slate-500">Active Validations</div>
                    </div>
                  </div>

                  <div *ngIf="conn.usage.projectNames && conn.usage.projectNames.length > 0" class="mt-3 space-y-1">
                    <div class="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Linked Projects:</div>
                    <div class="flex flex-wrap gap-1.5">
                      <span
                        *ngFor="let proj of conn.usage.projectNames"
                        class="px-2 py-0.5 bg-slate-100 border border-slate-200 text-xs font-medium text-slate-700 rounded-md">
                        {{ proj }}
                      </span>
                    </div>
                  </div>

                  <div *ngIf="conn.usage.migrationNames && conn.usage.migrationNames.length > 0" class="mt-3 space-y-1">
                    <div class="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Linked Workloads:</div>
                    <div class="flex flex-wrap gap-1.5">
                      <span
                        *ngFor="let mig of conn.usage.migrationNames"
                        class="px-2 py-0.5 bg-blue-50 border border-blue-200 text-xs font-medium text-blue-700 rounded-md">
                        {{ mig }}
                      </span>
                    </div>
                  </div>

                  <div *ngIf="conn.usage.isUnused" class="mt-2 p-2.5 bg-slate-50 border border-slate-200 rounded-md text-xs text-slate-500">
                    This connection is not referenced by any project or active migration. Safe for consolidation or decommissioning.
                  </div>
                </div>
              </div>
            </div>

            <!-- Section 4: Intelligence Advisory -->
            <div *ngIf="conn.advisory" class="space-y-2">
              <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wider">
                System Advisory
              </h3>
              <div class="p-3 bg-indigo-50/70 border border-indigo-200 rounded-xl space-y-1">
                <div class="flex items-center gap-1.5 font-bold text-indigo-900 text-xs">
                  <span>{{ conn.advisory.headline }}</span>
                </div>
                <p *ngIf="conn.advisory.description" class="text-xs text-indigo-800/90 leading-relaxed">
                  {{ conn.advisory.description }}
                </p>
              </div>
            </div>

            <!-- Section 5: Metadata & Audit -->
            <div class="pt-2 border-t border-slate-200 text-xs text-slate-500 space-y-1">
              <div class="flex justify-between">
                <span>Created At:</span>
                <span class="font-mono text-slate-700">{{ conn.createdAt | date:'medium' }}</span>
              </div>
              <div class="flex justify-between">
                <span>Last Updated:</span>
                <span class="font-mono text-slate-700">{{ conn.updatedAt | date:'medium' }}</span>
              </div>
              <div class="flex justify-between">
                <span>Workspace:</span>
                <span class="font-medium text-slate-700">{{ conn.workspaceName || conn.workspaceId }}</span>
              </div>
            </div>

          </div>

          <!-- Drawer Footer Actions (Strictly text-led buttons) -->
          <div class="px-6 py-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between gap-3 flex-wrap">
            <div class="flex items-center gap-2">
              <button
                type="button"
                (click)="close()"
                class="h-9 px-4 text-xs font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-md transition-colors cursor-pointer shadow-2xs focus:outline-hidden focus:ring-2 focus:ring-slate-400">
                Close Drawer
              </button>

              <button
                type="button"
                (click)="openWorkspace(conn)"
                class="h-9 px-4 text-xs font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-md transition-colors cursor-pointer shadow-2xs focus:outline-hidden focus:ring-2 focus:ring-slate-400">
                Open Workspace
              </button>
            </div>

            <button
              type="button"
              [disabled]="isVerifying(conn.id)"
              (click)="onVerify(conn)"
              class="h-9 px-4 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed shadow-2xs focus:outline-hidden focus:ring-2 focus:ring-blue-500">
              {{ isVerifying(conn.id) ? 'Verifying Probe...' : 'Verify Connection' }}
            </button>
          </div>

        </div>
      </div>
    </div>
  `
})
export class ConnectionsInspectDrawerComponent {
  public cs = inject(ConnectionsService);
  public router?: Router;

  constructor(@Optional() router?: Router) {
    if (router) this.router = router;
    else {
      try {
        this.router = inject(Router);
      } catch {}
    }
  }

  close(): void {
    this.cs.closeInspectDrawer();
  }

  openWorkspace(conn: ConnectionRecord): void {
    this.close();
    if (this.router) {
      this.router.navigate(['/connections', conn.id]);
    }
  }

  onVerify(conn: ConnectionRecord): void {
    this.cs.verifyConnection(conn.id);
  }

  isVerifying(connId: string): boolean {
    return this.cs.isVerifyingConnectionId() === connId;
  }

  getEnvironmentBadgeClass(env: string): string {
    switch (env) {
      case 'Production':
        return 'inline-flex items-center px-2 py-0.5 rounded-sm text-[10px] font-medium bg-rose-50 text-rose-700 border border-rose-200 font-mono';
      case 'Staging':
        return 'inline-flex items-center px-2 py-0.5 rounded-sm text-[10px] font-medium bg-amber-50 text-amber-700 border border-amber-200 font-mono';
      case 'Development':
        return 'inline-flex items-center px-2 py-0.5 rounded-sm text-[10px] font-medium bg-blue-50 text-blue-700 border border-blue-200 font-mono';
      default:
        return 'inline-flex items-center px-2 py-0.5 rounded-sm text-[10px] font-medium bg-slate-100 text-slate-600 border border-slate-200 font-mono';
    }
  }

  getFamilyLabel(family: ConnectionFamily): string {
    switch (family) {
      case 'RELATIONAL': return 'Relational';
      case 'WAREHOUSE_LAKE': return 'Warehouse / Lake';
      case 'NOSQL_GRAPH': return 'NoSQL / Graph';
      case 'STREAMING': return 'Streaming';
      case 'OBJECT_STORAGE': return 'Object Storage';
      case 'TIME_SERIES': return 'Time Series';
      case 'APPLICATION': return 'Application';
      case 'MANAGED_CLOUD': return 'Cloud Resolver';
      default: return family;
    }
  }

  getFamilyBadgeClass(family: ConnectionFamily): string {
    switch (family) {
      case 'RELATIONAL':
        return 'inline-flex items-center px-2 py-0.5 rounded-sm text-[11px] font-medium bg-indigo-50 text-indigo-700 border border-indigo-200';
      case 'WAREHOUSE_LAKE':
        return 'inline-flex items-center px-2 py-0.5 rounded-sm text-[11px] font-medium bg-cyan-50 text-cyan-700 border border-cyan-200';
      case 'NOSQL_GRAPH':
        return 'inline-flex items-center px-2 py-0.5 rounded-sm text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200';
      case 'STREAMING':
        return 'inline-flex items-center px-2 py-0.5 rounded-sm text-[11px] font-medium bg-purple-50 text-purple-700 border border-purple-200';
      case 'OBJECT_STORAGE':
        return 'inline-flex items-center px-2 py-0.5 rounded-sm text-[11px] font-medium bg-amber-50 text-amber-700 border border-amber-200';
      case 'TIME_SERIES':
        return 'inline-flex items-center px-2 py-0.5 rounded-sm text-[11px] font-medium bg-teal-50 text-teal-700 border border-teal-200';
      case 'APPLICATION':
        return 'inline-flex items-center px-2 py-0.5 rounded-sm text-[11px] font-medium bg-orange-50 text-orange-700 border border-orange-200';
      case 'MANAGED_CLOUD':
        return 'inline-flex items-center px-2 py-0.5 rounded-sm text-[11px] font-medium bg-sky-50 text-sky-700 border border-sky-200';
      default:
        return 'inline-flex items-center px-2 py-0.5 rounded-sm text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200';
    }
  }

  getRoleLabel(role: ConnectionRoleApplicability): string {
    switch (role) {
      case 'SOURCE_AND_TARGET': return 'Source & Target';
      case 'SOURCE_ONLY': return 'Source Only';
      case 'TARGET_ONLY': return 'Target Only';
      default: return role;
    }
  }

  getVerificationLabel(state: ConnectionVerificationState): string {
    switch (state) {
      case 'VERIFIED_RECENT': return 'Verified (Fresh)';
      case 'VERIFIED_POINT_IN_TIME': return 'Verified (Point-in-Time)';
      case 'VERIFIED_STALE': return 'Verified (Stale)';
      case 'CONFIG_CHANGED_SINCE_TEST': return 'Config Changed';
      case 'PARTIAL_VERIFIED': return 'Partial (L1/L2 Only)';
      case 'TESTING': return 'Testing Probe...';
      case 'NEVER_TESTED': return 'Never Tested';
      case 'VERIFICATION_FAILED': return 'Failed Probe';
      case 'UNAVAILABLE': return 'Bridge Unavailable';
      case 'UNAUTHORIZED': return 'Unauthorized';
      case 'UNKNOWN': return 'Unknown State';
      default: return state;
    }
  }

  getVerificationBadgeClass(state: ConnectionVerificationState): string {
    switch (state) {
      case 'VERIFIED_RECENT':
      case 'VERIFIED_POINT_IN_TIME':
        return 'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200';
      case 'VERIFIED_STALE':
      case 'CONFIG_CHANGED_SINCE_TEST':
        return 'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200';
      case 'PARTIAL_VERIFIED':
        return 'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-sky-50 text-sky-700 border border-sky-200';
      case 'TESTING':
        return 'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200';
      case 'VERIFICATION_FAILED':
        return 'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200';
      case 'UNAVAILABLE':
      case 'UNAUTHORIZED':
      case 'UNKNOWN':
      case 'NEVER_TESTED':
      default:
        return 'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200';
    }
  }

  getVerificationDotClass(state: ConnectionVerificationState): string {
    switch (state) {
      case 'VERIFIED_RECENT':
      case 'VERIFIED_POINT_IN_TIME':
        return 'w-2 h-2 rounded-full bg-emerald-500';
      case 'VERIFIED_STALE':
      case 'CONFIG_CHANGED_SINCE_TEST':
        return 'w-2 h-2 rounded-full bg-amber-500';
      case 'PARTIAL_VERIFIED':
        return 'w-2 h-2 rounded-full bg-sky-500';
      case 'TESTING':
        return 'w-2 h-2 rounded-full bg-blue-500 animate-ping';
      case 'VERIFICATION_FAILED':
        return 'w-2 h-2 rounded-full bg-rose-500';
      case 'NEVER_TESTED':
      default:
        return 'w-2 h-2 rounded-full bg-slate-400';
    }
  }
}
