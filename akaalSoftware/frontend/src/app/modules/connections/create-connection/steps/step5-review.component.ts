import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CreateConnectionService } from '../create-connection.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-step5-review',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="max-w-5xl mx-auto w-full space-y-6 select-none animate-in fade-in duration-150 text-xs font-sans">
      
      <!-- Top Section Header -->
      <div class="flex flex-col gap-1 border-b border-slate-200 pb-3">
        <h2 class="text-base font-bold text-slate-900 tracking-tight">Review &amp; Create Connection</h2>
        <p class="text-xs text-slate-500 font-normal">
          Confirm configuration parameters, security baseline, and point-in-time verification facts before provisioning.
        </p>
      </div>

      <!-- Overview Cards Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        <!-- ========================================================================= -->
        <!-- CARD 1: IDENTITY & PROVIDER SUMMARY                                       -->
        <!-- ========================================================================= -->
        <div class="p-5 bg-white border border-slate-200 rounded-xl space-y-3.5 shadow-2xs">
          <div class="flex items-center justify-between pb-2 border-b border-slate-100">
            <span class="text-xs font-bold text-slate-900">Resource Identity &amp; Provider</span>
            <button
              type="button"
              (click)="cs.goToStep(1)"
              class="text-[11px] font-semibold text-blue-600 hover:underline cursor-pointer">
              Edit
            </button>
          </div>

          <div class="space-y-2 text-xs">
            <div class="flex items-center justify-between">
              <span class="text-slate-500">Connection Name:</span>
              <strong class="font-bold text-slate-900">{{ cs.draft().name }}</strong>
            </div>

            <div class="flex items-center justify-between">
              <span class="text-slate-500">Provider Platform:</span>
              <span class="font-semibold text-slate-800">{{ cs.selectedProvider()?.name }} ({{ cs.selectedProvider()?.categoryLabel }})</span>
            </div>

            <div class="flex items-center justify-between">
              <span class="text-slate-500">Environment:</span>
              <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
                {{ cs.draft().environment }}
              </span>
            </div>

            @if (cs.draft().description) {
              <div class="flex flex-col gap-0.5 pt-1 border-t border-slate-100">
                <span class="text-slate-500">Description:</span>
                <span class="text-slate-700 italic text-[11px]">{{ cs.draft().description }}</span>
              </div>
            }
          </div>
        </div>

        <!-- ========================================================================= -->
        <!-- CARD 2: ENDPOINT & ADDRESSING SUMMARY                                     -->
        <!-- ========================================================================= -->
        <div class="p-5 bg-white border border-slate-200 rounded-xl space-y-3.5 shadow-2xs">
          <div class="flex items-center justify-between pb-2 border-b border-slate-100">
            <span class="text-xs font-bold text-slate-900">Endpoint &amp; Addressing</span>
            <button
              type="button"
              (click)="cs.goToStep(2)"
              class="text-[11px] font-semibold text-blue-600 hover:underline cursor-pointer">
              Edit
            </button>
          </div>

          <div class="space-y-2 text-xs">
            <div class="flex items-center justify-between">
              <span class="text-slate-500">Endpoint String:</span>
              <span class="font-mono font-bold text-slate-900 truncate max-w-[240px]">{{ endpointSummary() }}</span>
            </div>

            @if (cs.selectedProvider()?.id === 'oracle') {
              <div class="flex items-center justify-between">
                <span class="text-slate-500">Addressing Mode:</span>
                <span class="font-medium text-slate-800">{{ cs.draft().oracleAddressingMode }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-slate-500">Driver Mode:</span>
                <span class="font-medium text-slate-800">{{ cs.draft().oracleDriverMode }}</span>
              </div>
            }

            @if (cs.selectedProvider()?.id === 'bigquery') {
              <div class="flex items-center justify-between">
                <span class="text-slate-500">Location:</span>
                <span class="font-medium text-slate-800">{{ cs.draft().bigqueryLocation }}</span>
              </div>
            }

            <div class="flex items-center justify-between">
              <span class="text-slate-500">Role Applicability:</span>
              <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                {{ cs.selectedProvider()?.roleApplicability === 'SOURCE_AND_TARGET' ? 'Source + Target' : (cs.selectedProvider()?.roleApplicability === 'SOURCE_ONLY' ? 'Source Only' : 'Target Only') }}
              </span>
            </div>
          </div>
        </div>

        <!-- ========================================================================= -->
        <!-- CARD 3: AUTHENTICATION & SECRETS (NO SECRETS EXPOSED)                     -->
        <!-- ========================================================================= -->
        <div class="p-5 bg-white border border-slate-200 rounded-xl space-y-3.5 shadow-2xs">
          <div class="flex items-center justify-between pb-2 border-b border-slate-100">
            <span class="text-xs font-bold text-slate-900">Authentication &amp; Custody</span>
            <button
              type="button"
              (click)="cs.goToStep(3)"
              class="text-[11px] font-semibold text-blue-600 hover:underline cursor-pointer">
              Edit
            </button>
          </div>

          <div class="space-y-2 text-xs">
            <div class="flex items-center justify-between">
              <span class="text-slate-500">Auth Protocol:</span>
              <span class="font-bold text-slate-800">{{ formatAuth(cs.draft().authMethod) }}</span>
            </div>

            @if (cs.draft().authUsername) {
              <div class="flex items-center justify-between">
                <span class="text-slate-500">Principal / Username:</span>
                <span class="font-mono text-slate-800">{{ cs.draft().authUsername }}</span>
              </div>
            }

            @if (cs.draft().authRoleArn) {
              <div class="flex items-center justify-between">
                <span class="text-slate-500">IAM Role ARN:</span>
                <span class="font-mono text-slate-800 truncate max-w-[200px]">{{ cs.draft().authRoleArn }}</span>
              </div>
            }

            <div class="flex items-center justify-between pt-1 border-t border-slate-100">
              <span class="text-slate-500">Secret Reference:</span>
              <span class="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded">
                <app-lucide-icon name="check" [size]="12"></app-lucide-icon>
                <span>Configured (Opaque Reference)</span>
              </span>
            </div>
          </div>
        </div>

        <!-- ========================================================================= -->
        <!-- CARD 4: TRANSPORT SECURITY & NETWORK ROUTING                              -->
        <!-- ========================================================================= -->
        <div class="p-5 bg-white border border-slate-200 rounded-xl space-y-3.5 shadow-2xs">
          <div class="flex items-center justify-between pb-2 border-b border-slate-100">
            <span class="text-xs font-bold text-slate-900">Security &amp; Network Routing</span>
            <button
              type="button"
              (click)="cs.goToStep(3)"
              class="text-[11px] font-semibold text-blue-600 hover:underline cursor-pointer">
              Edit
            </button>
          </div>

          <div class="space-y-2 text-xs">
            <div class="flex items-center justify-between">
              <span class="text-slate-500">TLS Encryption:</span>
              <span class="font-bold text-slate-800">{{ cs.draft().tlsMode }} ({{ cs.draft().minTlsVersion }})</span>
            </div>

            <div class="flex items-center justify-between">
              <span class="text-slate-500">Network Route:</span>
              <span class="font-medium text-slate-800">{{ formatRoute(cs.draft().networkRoute) }}</span>
            </div>

            @if (cs.draft().networkRoute === 'SSH_BASTION') {
              <div class="flex items-center justify-between">
                <span class="text-slate-500">Bastion Host:</span>
                <span class="font-mono text-slate-800">{{ cs.draft().sshBastionHost }}:{{ cs.draft().sshBastionPort }}</span>
              </div>
            }

            <div class="flex items-center justify-between">
              <span class="text-slate-500">Fabric Locality:</span>
              <span class="text-slate-700 font-mono">{{ cs.draft().fabricSite }} &middot; {{ cs.draft().fabricLocality }}</span>
            </div>
          </div>
        </div>

      </div>

      <!-- ========================================================================= -->
      <!-- CARD 5: VERIFICATION PROBE FACTS & CDC STATUS                             -->
      <!-- ========================================================================= -->
      <div class="p-5 bg-white border border-slate-200 rounded-xl space-y-3.5 shadow-2xs">
        <div class="flex items-center justify-between pb-2 border-b border-slate-100">
          <span class="text-xs font-bold text-slate-900">Point-in-Time Verification Truth</span>
          <button
            type="button"
            (click)="cs.goToStep(4)"
            class="text-[11px] font-semibold text-blue-600 hover:underline cursor-pointer">
            Re-test
          </button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          
          <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between">
            <span class="text-slate-600">Connection Probe:</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-bold"
              [class]="cs.draft().verificationFacts.overallStatus === 'PASSED'
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                : 'bg-slate-100 text-slate-600 border border-slate-200'">
              {{ cs.draft().verificationFacts.overallStatus === 'PASSED' ? 'VERIFIED (POINT-IN-TIME)' : 'UNTESTED' }}
            </span>
          </div>

          <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between">
            <span class="text-slate-600">CDC Capability:</span>
            <span class="font-mono text-[10px] font-bold text-slate-800">
              {{ cs.draft().verificationFacts.cdcCapability.label }}
            </span>
          </div>

          <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between">
            <span class="text-slate-600">Validation #11:</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
              SUPPORTED
            </span>
          </div>

        </div>
      </div>

    </div>
  `
})
export class Step5ReviewComponent {
  public cs = inject(CreateConnectionService);

  public formatRoute(route: string): string {
    return route ? route.replace(/_/g, ' ') : 'Direct';
  }

  public formatAuth(auth: string): string {
    return auth ? auth.replace(/_/g, ' ') : 'Password';
  }

  public endpointSummary = computed<string>(() => {
    const d = this.cs.draft();
    const p = this.cs.selectedProvider();
    if (!p) return 'N/A';

    if (p.id === 'oracle') {
      return d.oracleAddressingMode === 'HOST_SERVICE'
        ? `${d.oracleHost || 'oracle-db'}:${d.oraclePort || 1521}/${d.oracleServiceName || 'PDB1'}`
        : `${d.oracleTnsName || d.oracleSid || 'ORCL'}`;
    }
    if (p.id === 'bigquery') return `gcp://${d.bigqueryProjectId || 'project'}/${d.bigqueryDataset || 'all_datasets'}`;
    if (p.id === 'spanner') return `spanner://${d.spannerProjectId || 'project'}/${d.spannerInstanceId || 'instance'}/${d.spannerDatabaseId || 'db'}`;
    if (p.id === 'salesforce') return d.salesforceInstanceUrl || 'company.my.salesforce.com';
    if (p.id === 'servicenow') return d.servicenowInstanceUrl || 'company.service-now.com';
    if (p.id === 'sap_application') {
      return d.sapConnectionMode === 'RFC_BAPI'
        ? `sap-rfc://${d.sapAppServerHost || d.sapMessageServerHost || 'sap-host'}:${d.sapSystemNumber || '00'}`
        : (d.sapOdataServiceUrl || 'sap-odata');
    }
    if (p.id === 'sqlite') return (d.parameters['database_path'] as string) || '/var/data/app.db';
    if (p.id === 's3' || p.id === 'gcs' || p.id === 'minio') return `s3://${d.parameters['bucket'] || 'enterprise-data-lake'}`;
    if (p.id === 'kafka') return d.parameters['bootstrap_servers'] || 'kafka-broker:9092';

    return `${d.parameters['host'] || 'db.prod.corp.internal'}:${d.parameters['port'] || p.defaultPort || '5432'}/${d.parameters['database'] || 'finance_prod'}`;
  });
}
