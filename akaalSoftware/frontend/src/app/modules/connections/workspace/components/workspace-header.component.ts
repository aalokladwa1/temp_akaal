import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ConnectionWorkspaceService } from '../connection-workspace.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';
import { ConnectionVerificationState } from '../../connections.models';

@Component({
  selector: 'app-workspace-header',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent, CustomSelectComponent],
  template: `
    <header class="bg-white border-b border-slate-200 px-6 lg:px-8 py-4 sticky top-0 z-30 shadow-2xs select-none">
      <div class="max-w-[1680px] mx-auto flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        
        <!-- Identity Zone -->
        @if (ws.connection(); as conn) {
          <div class="flex flex-col gap-2 min-w-0">
            
            <!-- Breadcrumbs & Context Badges -->
            <div class="flex items-center flex-wrap gap-2 text-xs">
              <span class="text-slate-400 font-medium">AKAAL Enterprise</span>
              <span class="text-slate-300">/</span>
              <a routerLink="/connections" class="text-slate-500 hover:text-blue-600 font-medium transition-colors">
                Connections
              </a>
              <span class="text-slate-300">/</span>
              
              <!-- Canonical Connection ID copy trigger -->
              <button
                type="button"
                (click)="ws.copyConnectionId()"
                class="inline-flex items-center gap-1.5 font-mono text-xs font-semibold px-2.5 py-1 rounded-md bg-slate-50 hover:bg-blue-50 text-slate-700 hover:text-blue-700 hover:border-blue-300 transition-colors border border-slate-200 cursor-pointer"
                [title]="'Click to copy connection ID: ' + conn.id">
                <span>{{ conn.id }}</span>
                <app-lucide-icon
                  [name]="ws.copiedId() ? 'check' : 'copy'"
                  [size]="12"
                  [class]="ws.copiedId() ? 'text-emerald-600' : 'text-slate-400'"></app-lucide-icon>
              </button>

              <!-- Environment Tag -->
              <span class="inline-flex items-center px-2.5 py-1 rounded-md text-[11px] font-semibold bg-slate-50 text-slate-700 border border-slate-200">
                {{ conn.environment }}
              </span>

              <!-- Managed Cloud Origin Tag (if applicable) -->
              @if (conn.managedCloudName) {
                <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                  <app-lucide-icon name="cloud" [size]="12"></app-lucide-icon>
                  <span>{{ conn.managedCloudName }}</span>
                </span>
              }

              <!-- Verification Staleness Alert Badge -->
              @if (ws.isVerificationStale()) {
                <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-bold bg-amber-50 text-amber-800 border border-amber-300">
                  <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
                  <span>Verification Stale</span>
                </span>
              }
            </div>

            <!-- Main Heading Row: Icon + Name + Verification Badge + Lifecycle Badge -->
            <div class="flex items-center flex-wrap gap-3.5 pt-0.5">
              
              <div class="w-8 h-8 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-700 shrink-0">
                <app-lucide-icon [name]="getProviderIcon(conn.providerId)" [size]="17"></app-lucide-icon>
              </div>

              <h1 class="text-xl font-bold text-slate-900 tracking-tight font-heading truncate">
                {{ conn.name }}
              </h1>

              <!-- Provider Family Badge -->
              <span class="px-2.5 py-0.5 rounded-md text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200 shrink-0">
                {{ conn.providerName }}
              </span>

              <!-- Factual Verification Badge -->
              <div [class]="getVerificationBadgeClass(conn.verificationState)"
                   class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold border select-none shrink-0">
                <span [class]="getVerificationDotClass(conn.verificationState)"></span>
                <span>{{ getVerificationLabel(conn.verificationState) }}</span>
              </div>

              <!-- Lifecycle State Badge -->
              <span
                class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold border select-none shrink-0"
                [class.bg-emerald-50]="conn.lifecycleState === 'ACTIVE'"
                [class.text-emerald-700]="conn.lifecycleState === 'ACTIVE'"
                [class.border-emerald-200]="conn.lifecycleState === 'ACTIVE'"
                [class.bg-amber-50]="conn.lifecycleState === 'DISABLED'"
                [class.text-amber-700]="conn.lifecycleState === 'DISABLED'"
                [class.border-amber-200]="conn.lifecycleState === 'DISABLED'"
                [class.bg-slate-100]="conn.lifecycleState === 'ARCHIVED'"
                [class.text-slate-700]="conn.lifecycleState === 'ARCHIVED'"
                [class.border-slate-200]="conn.lifecycleState === 'ARCHIVED'">
                <span>{{ conn.lifecycleState }}</span>
              </span>

            </div>

            <!-- Contextual Endpoint Line -->
            <div class="text-xs text-slate-500 flex items-center flex-wrap gap-2 pt-0.5">
              <span class="font-mono text-slate-700 font-medium">{{ conn.endpointDisplay }}</span>
              <span class="text-slate-300">&bull;</span>
              <span>{{ conn.safeRouteInfo }}</span>
              <span class="text-slate-300">&bull;</span>
              <span>{{ conn.authMethodDisplay }}</span>
            </div>

          </div>
        }

        <!-- Action Bar Zone (Text-Led, No Icons in Action Buttons) -->
        <div class="flex items-center gap-2.5 shrink-0 flex-wrap">
          
          <!-- Scenario Fixture Switcher (For Visual Acceptance) -->
          <div class="w-60">
            <app-custom-select
              [options]="scenarioOptions"
              [value]="currentScenarioValue"
              [size]="'sm'"
              (valueChange)="onScenarioSelected($event)">
            </app-custom-select>
          </div>

          <!-- Test Connection Action (Text-Only) -->
          <button
            type="button"
            (click)="ws.testConnection()"
            [disabled]="ws.isRunningTest()"
            class="h-8 px-3.5 text-xs font-semibold rounded-md bg-white border border-slate-300 hover:bg-slate-50 hover:border-slate-400 active:bg-slate-100 text-slate-700 transition-all cursor-pointer shadow-2xs disabled:opacity-50">
            {{ ws.isRunningTest() ? 'Testing Connection...' : 'Test Connection' }}
          </button>

          <!-- Edit Configuration Action (Text-Only) -->
          <button
            type="button"
            (click)="onEditClick()"
            class="h-8 px-3.5 text-xs font-semibold rounded-md bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white transition-all cursor-pointer shadow-2xs">
            Edit Configuration
          </button>

        </div>

      </div>
    </header>
  `
})
export class WorkspaceHeaderComponent {
  public ws = inject(ConnectionWorkspaceService);

  public currentScenarioValue: string = 'conn-ora-rac-01';

  public scenarioOptions: CustomSelectOption[] = [
    { label: 'Oracle RAC (Core Banking)', value: 'conn-ora-rac-01', group: 'Heterogeneous Providers', icon: 'database' },
    { label: 'AWS Aurora PG 16 (Managed)', value: 'conn-pg-aurora-01', group: 'Heterogeneous Providers', icon: 'cloud' },
    { label: 'Kafka Cluster (Streaming)', value: 'conn-kafka-prod-01', group: 'Heterogeneous Providers', icon: 'radio' },
    { label: 'Amazon S3 (Archival Bucket)', value: 'conn-s3-lake-01', group: 'Heterogeneous Providers', icon: 'hard-drive' },
    { label: 'Unused Sandbox (Permits Delete)', value: 'conn-unused-test-01', group: 'Lifecycle & Edge Cases', icon: 'trash-2' },
    { label: 'Failed Probe (Sybase Standby)', value: 'conn-failed-test-01', group: 'Lifecycle & Edge Cases', icon: 'alert-triangle' }
  ];

  public onScenarioSelected(val: string): void {
    this.currentScenarioValue = val;
    this.ws.loadConnection(val, this.ws.activeTab());
  }

  public onEditClick(): void {
    this.ws.setActiveTab('configuration');
    this.ws.startEditingConfig();
  }

  public getProviderIcon(providerId: string): string {
    switch (providerId) {
      case 'oracle':
      case 'postgresql':
      case 'mysql':
      case 'mariadb':
      case 'mssql':
      case 'sqlite':
        return 'database';
      case 'snowflake':
      case 'bigquery':
      case 'redshift':
      case 'databricks':
        return 'layers';
      case 'kafka':
      case 'pulsar':
      case 'kinesis':
        return 'radio';
      case 's3':
      case 'gcs':
      case 'azure_blob':
        return 'hard-drive';
      case 'salesforce':
      case 'servicenow':
      case 'sap_app':
        return 'briefcase';
      default:
        return 'database';
    }
  }

  public getVerificationLabel(state: ConnectionVerificationState): string {
    switch (state) {
      case 'VERIFIED_RECENT': return 'Verified (Fresh)';
      case 'VERIFIED_POINT_IN_TIME': return 'Verified (Point-in-Time)';
      case 'VERIFIED_STALE': return 'Verified (Stale)';
      case 'CONFIG_CHANGED_SINCE_TEST': return 'Needs Verification';
      case 'PARTIAL_VERIFIED': return 'Partial (L1/L2 Only)';
      case 'TESTING': return 'Testing Probe...';
      case 'NEVER_TESTED': return 'Never Tested';
      case 'VERIFICATION_FAILED': return 'Failed Probe';
      case 'UNAVAILABLE': return 'Bridge Unavailable';
      default: return 'Unknown State';
    }
  }

  public getVerificationBadgeClass(state: ConnectionVerificationState): string {
    switch (state) {
      case 'VERIFIED_RECENT':
      case 'VERIFIED_POINT_IN_TIME':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'VERIFIED_STALE':
      case 'CONFIG_CHANGED_SINCE_TEST':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'PARTIAL_VERIFIED':
        return 'bg-sky-50 text-sky-700 border-sky-200';
      case 'TESTING':
        return 'bg-blue-50 text-blue-700 border-blue-200 animate-pulse';
      case 'VERIFICATION_FAILED':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      default:
        return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  }

  public getVerificationDotClass(state: ConnectionVerificationState): string {
    switch (state) {
      case 'VERIFIED_RECENT':
      case 'VERIFIED_POINT_IN_TIME':
        return 'w-1.5 h-1.5 rounded-full bg-emerald-500';
      case 'VERIFIED_STALE':
      case 'CONFIG_CHANGED_SINCE_TEST':
        return 'w-1.5 h-1.5 rounded-full bg-amber-500';
      case 'PARTIAL_VERIFIED':
        return 'w-1.5 h-1.5 rounded-full bg-sky-500';
      case 'TESTING':
        return 'w-1.5 h-1.5 rounded-full bg-blue-500 animate-ping';
      case 'VERIFICATION_FAILED':
        return 'w-1.5 h-1.5 rounded-full bg-rose-500';
      default:
        return 'w-1.5 h-1.5 rounded-full bg-slate-400';
    }
  }
}
