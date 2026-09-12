import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CreateTemplateService } from '../create-template.service';
import {
  OverridabilityLevel,
  MappingOverrideLevel,
  ScopeOverrideLevel,
  AuditLogLevel,
  SecretVaultProvider
} from '../create-template.models';
import { CustomSelectComponent, CustomSelectOption } from '../../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-step5-governance-reuse',
  standalone: true,
  imports: [CommonModule, FormsModule, CustomSelectComponent],
  template: `
    <div class="space-y-6 animate-in fade-in duration-150 text-xs font-sans">
      
      <!-- Top Section Header -->
      <div class="flex flex-col gap-1 border-b border-slate-200 pb-3">
        <h2 class="text-base font-bold text-slate-900 tracking-tight font-heading">Governance & Reuse Rules</h2>
        <p class="text-xs text-slate-500 font-normal">
          Declare runtime parameter overridability constraints, engine prerequisite capabilities, enterprise approval policies, and secret vault resolution rules.
        </p>
      </div>

      <!-- SECTION 1: PARAMETER OVERRIDABILITY CONSTRAINTS (Using GDS Custom Select) -->
      <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-3.5 shadow-2xs">
        <div class="flex items-center justify-between border-b border-slate-100 pb-2">
          <div class="flex flex-col">
            <span class="font-bold text-slate-900">Operator Overridability Enforcement</span>
            <span class="text-[11px] text-slate-500 font-normal">Control whether engineers can mutate template presets when creating a migration.</span>
          </div>
          <span class="text-[10px] text-slate-400">Security & Stability Guardrails</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          
          <!-- Performance Overridability -->
          <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg flex flex-col gap-2">
            <span class="font-bold text-slate-800">Performance & Concurrency</span>
            <app-custom-select
              [options]="performanceOverridabilityOptions"
              [ngModel]="ts.governance().overridability.performanceSettings"
              (ngModelChange)="updateOverridability({ performanceSettings: $event })">
            </app-custom-select>
            <span class="text-[10px] text-slate-400">Limits runtime thread and batch size adjustment</span>
          </div>

          <!-- Mapping Overridability -->
          <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg flex flex-col gap-2">
            <span class="font-bold text-slate-800">Mapping & Transformations</span>
            <app-custom-select
              [options]="mappingOverridabilityOptions"
              [ngModel]="ts.governance().overridability.mappingRules"
              (ngModelChange)="updateOverridability({ mappingRules: $event })">
            </app-custom-select>
            <span class="text-[10px] text-slate-400">Controls column mapping and masking changes</span>
          </div>

          <!-- Scope Overridability -->
          <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg flex flex-col gap-2">
            <span class="font-bold text-slate-800">Object Scope Boundary</span>
            <app-custom-select
              [options]="scopeOverridabilityOptions"
              [ngModel]="ts.governance().overridability.scopeObjects"
              (ngModelChange)="updateOverridability({ scopeObjects: $event })">
            </app-custom-select>
            <span class="text-[10px] text-slate-400">Prevents unauthorized table inclusions</span>
          </div>

        </div>
      </div>

      <!-- SECTION 2: REQUIRED-AT-USE VALUES LEDGER -->
      <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-3 shadow-2xs">
        <div class="flex items-center justify-between border-b border-slate-100 pb-2">
          <div class="flex flex-col">
            <span class="font-bold text-slate-900">Required-at-Use Values Ledger</span>
            <span class="text-[11px] text-slate-500 font-normal">Active contract checklist of runtime values mandated by this template.</span>
          </div>
          <span class="px-2 py-0.5 text-[10px] font-mono bg-blue-50 text-blue-700 border border-blue-200 rounded-md">
            Enforced at Migration Provisioning
          </span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
          <div class="p-2.5 bg-slate-50 border border-slate-200 rounded-md flex items-center gap-2">
            <span
              class="w-4 h-4 rounded flex items-center justify-center text-[10px] font-bold"
              [class]="ts.migrationDefaults().requiredAtUse.targetDatabaseRequired ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-500'">
              {{ ts.migrationDefaults().requiredAtUse.targetDatabaseRequired ? '✓' : '—' }}
            </span>
            <span class="font-medium text-slate-800">Target Database / Schema</span>
          </div>

          <div class="p-2.5 bg-slate-50 border border-slate-200 rounded-md flex items-center gap-2">
            <span
              class="w-4 h-4 rounded flex items-center justify-center text-[10px] font-bold"
              [class]="ts.migrationDefaults().requiredAtUse.scheduleRequired ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-500'">
              {{ ts.migrationDefaults().requiredAtUse.scheduleRequired ? '✓' : '—' }}
            </span>
            <span class="font-medium text-slate-800">Execution Schedule</span>
          </div>

          <div class="p-2.5 bg-slate-50 border border-slate-200 rounded-md flex items-center gap-2">
            <span
              class="w-4 h-4 rounded flex items-center justify-center text-[10px] font-bold"
              [class]="ts.migrationDefaults().requiredAtUse.secretBindingsRequired ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-500'">
              {{ ts.migrationDefaults().requiredAtUse.secretBindingsRequired ? '✓' : '—' }}
            </span>
            <span class="font-medium text-slate-800">Secret Bindings / Vault Auth</span>
          </div>

          <div class="p-2.5 bg-slate-50 border border-slate-200 rounded-md flex items-center gap-2">
            <span
              class="w-4 h-4 rounded flex items-center justify-center text-[10px] font-bold"
              [class]="ts.migrationDefaults().requiredAtUse.workspaceSelectionRequired ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-500'">
              {{ ts.migrationDefaults().requiredAtUse.workspaceSelectionRequired ? '✓' : '—' }}
            </span>
            <span class="font-medium text-slate-800">Project / Workspace Binding</span>
          </div>

          <div class="p-2.5 bg-slate-50 border border-slate-200 rounded-md flex items-center gap-2">
            <span
              class="w-4 h-4 rounded flex items-center justify-center text-[10px] font-bold"
              [class]="ts.migrationDefaults().requiredAtUse.notificationChannelsRequired ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-500'">
              {{ ts.migrationDefaults().requiredAtUse.notificationChannelsRequired ? '✓' : '—' }}
            </span>
            <span class="font-medium text-slate-800">Notification Webhooks</span>
          </div>
        </div>
      </div>

      <!-- SECTION 3: CAPABILITY PREREQUISITES & VERIFICATION -->
      <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-3 shadow-2xs">
        <div class="flex items-center justify-between border-b border-slate-100 pb-2">
          <div class="flex flex-col">
            <span class="font-bold text-slate-900">Database Capability & Privilege Prerequisites</span>
            <span class="text-[11px] text-slate-500 font-normal">Privileges checked by Connection Verifier before allowing migration execution.</span>
          </div>
          <span class="text-[10px] text-slate-400">Pre-Flight Assurances</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          
          <!-- Source Privileges -->
          <div class="flex flex-col gap-2">
            <span class="text-[11px] font-bold text-slate-700 uppercase">Source Privileges</span>
            <div class="flex flex-wrap gap-1.5 min-h-12 p-2 bg-slate-50 border border-slate-200 rounded-md">
              @for (priv of ts.governance().requiredCapabilities.sourcePrivileges; track priv) {
                <span class="px-2 py-0.5 text-[10px] font-mono font-bold bg-white text-slate-800 border border-slate-200 rounded flex items-center gap-1">
                  <span>{{ priv }}</span>
                  <button
                    type="button"
                    (click)="removeSourcePrivilege(priv)"
                    class="text-slate-400 hover:text-rose-600 cursor-pointer">
                    &times;
                  </button>
                </span>
              }
            </div>
            <div class="flex items-center gap-1.5">
              <input
                type="text"
                [(ngModel)]="newSourcePrivilege"
                placeholder="e.g. SELECT, REPLICATION"
                class="h-8 px-2.5 flex-1 bg-white border border-slate-200 rounded-md text-xs font-mono text-slate-900 focus:outline-none focus:border-blue-600 shadow-2xs" />
              <button
                type="button"
                (click)="addSourcePrivilege()"
                [disabled]="!newSourcePrivilege.trim()"
                class="h-8 px-3.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-xs font-semibold cursor-pointer disabled:opacity-40 disabled:pointer-events-none shadow-2xs transition-colors">
                Add
              </button>
            </div>
          </div>

          <!-- Target Privileges -->
          <div class="flex flex-col gap-2">
            <span class="text-[11px] font-bold text-slate-700 uppercase">Target Privileges</span>
            <div class="flex flex-wrap gap-1.5 min-h-12 p-2 bg-slate-50 border border-slate-200 rounded-md">
              @for (priv of ts.governance().requiredCapabilities.targetPrivileges; track priv) {
                <span class="px-2 py-0.5 text-[10px] font-mono font-bold bg-white text-slate-800 border border-slate-200 rounded-md flex items-center gap-1">
                  <span>{{ priv }}</span>
                  <button
                    type="button"
                    (click)="removeTargetPrivilege(priv)"
                    class="text-slate-400 hover:text-rose-600 cursor-pointer">
                    &times;
                  </button>
                </span>
              }
            </div>
            <div class="flex items-center gap-1.5">
              <input
                type="text"
                [(ngModel)]="newTargetPrivilege"
                placeholder="e.g. CREATE TABLE, INSERT"
                class="h-8 px-2.5 flex-1 bg-white border border-slate-200 rounded-md text-xs font-mono text-slate-900 focus:outline-none focus:border-blue-600 shadow-2xs" />
              <button
                type="button"
                (click)="addTargetPrivilege()"
                [disabled]="!newTargetPrivilege.trim()"
                class="h-8 px-3.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-xs font-semibold cursor-pointer disabled:opacity-40 disabled:pointer-events-none shadow-2xs transition-colors">
                Add
              </button>
            </div>
          </div>

          <!-- Network Requirements -->
          <div class="flex flex-col gap-2">
            <span class="text-[11px] font-bold text-slate-700 uppercase">Network Requirements</span>
            <div class="flex flex-wrap gap-1.5 min-h-12 p-2 bg-slate-50 border border-slate-200 rounded-md">
              @for (net of ts.governance().requiredCapabilities.networkRequirements; track net) {
                <span class="px-2 py-0.5 text-[10px] font-mono font-bold bg-white text-slate-800 border border-slate-200 rounded-md flex items-center gap-1">
                  <span>{{ net }}</span>
                  <button
                    type="button"
                    (click)="removeNetworkReq(net)"
                    class="text-slate-400 hover:text-rose-600 cursor-pointer">
                    &times;
                  </button>
                </span>
              }
            </div>
            <div class="flex items-center gap-1.5">
              <input
                type="text"
                [(ngModel)]="newNetworkReq"
                placeholder="e.g. TLS 1.3, VPC Peering"
                class="h-8 px-2.5 flex-1 bg-white border border-slate-200 rounded-md text-xs font-mono text-slate-900 focus:outline-none focus:border-blue-600 shadow-2xs" />
              <button
                type="button"
                (click)="addNetworkReq()"
                [disabled]="!newNetworkReq.trim()"
                class="h-8 px-3.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-xs font-semibold cursor-pointer disabled:opacity-40 disabled:pointer-events-none shadow-2xs transition-colors">
                Add
              </button>
            </div>
          </div>

        </div>
      </div>

      <!-- SECTION 4: APPROVAL POLICY & SECRET VAULT RULES (Using GDS Custom Select) -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        <!-- Governance & Approval Window -->
        <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-3 shadow-2xs">
          <div class="flex items-center justify-between border-b border-slate-100 pb-2">
            <span class="font-bold text-slate-900">Governance & Launch Policies</span>
            <span class="text-[10px] text-slate-400">Operational Compliance</span>
          </div>

          <div class="flex flex-col gap-3">
            <label class="flex items-start gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                [checked]="ts.governance().approvalAndPolicy.requirePeerReview"
                (change)="togglePeerReview()"
                class="rounded text-blue-600 focus:ring-0 mt-0.5" />
              <div class="flex flex-col">
                <span class="font-bold text-slate-800">Mandatory Dual-Operator Peer Review</span>
                <span class="text-[11px] text-slate-500 font-normal">Require secondary approval from a Lead Data Engineer before kickoff</span>
              </div>
            </label>

            <label class="flex items-start gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                [checked]="ts.governance().approvalAndPolicy.enforceChangeFreezeWindow"
                (change)="toggleChangeFreeze()"
                class="rounded text-blue-600 focus:ring-0 mt-0.5" />
              <div class="flex flex-col">
                <span class="font-bold text-slate-800">Enforce Production Change Freeze Windows</span>
                <span class="text-[11px] text-slate-500 font-normal">Block launches during quarterly corporate change freeze periods</span>
              </div>
            </label>

            <div class="flex flex-col gap-1 pt-1 border-t border-slate-100">
              <span class="text-[11px] font-semibold text-slate-700">Audit Logging Verbosity:</span>
              <app-custom-select
                [options]="auditLogOptions"
                [ngModel]="ts.governance().approvalAndPolicy.auditLogLevel"
                (ngModelChange)="updateAuditLog($event)">
              </app-custom-select>
            </div>
          </div>
        </div>

        <!-- Logical Secret Reference Policy (Using GDS Custom Select) -->
        <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-3 shadow-2xs">
          <div class="flex items-center justify-between border-b border-slate-100 pb-2">
            <span class="font-bold text-slate-900">Logical Secret Vault Resolution</span>
            <span class="text-[10px] text-slate-400">Zero Raw Creds</span>
          </div>

          <div class="flex flex-col gap-2.5">
            <div class="flex flex-col gap-1">
              <span class="text-[11px] font-semibold text-slate-700">Enterprise Vault Provider</span>
              <app-custom-select
                [options]="vaultProviderOptions"
                [ngModel]="ts.governance().secretReferenceRules.vaultProvider"
                (ngModelChange)="updateVault({ vaultProvider: $event })">
              </app-custom-select>
            </div>

            <div class="flex flex-col gap-1">
              <label for="vault-prefix" class="text-[11px] font-semibold text-slate-700 flex items-center gap-1">
                <span>Vault Key Path Prefix</span>
                <span class="text-rose-500">*</span>
              </label>
              <input
                id="vault-prefix"
                type="text"
                [ngModel]="ts.governance().secretReferenceRules.keyPathPrefix"
                (ngModelChange)="updateVault({ keyPathPrefix: $event })"
                placeholder="e.g. secret/data/akaal/migration/"
                class="h-9 px-2.5 bg-white border border-slate-200 focus:border-blue-600 rounded-md text-xs font-mono text-slate-900 focus:outline-none" />
            </div>

            <div class="p-2 bg-slate-50 border border-slate-200 rounded text-[11px] text-slate-500 leading-relaxed">
              {{ ts.governance().secretReferenceRules.guidanceNote }}
            </div>
          </div>
        </div>

      </div>

    </div>
  `
})
export class Step5GovernanceReuseComponent {
  public ts = inject(CreateTemplateService);

  public performanceOverridabilityOptions: CustomSelectOption[] = [
    { label: 'Full Override Allowed', value: 'FULL_OVERRIDE', desc: 'Operators can freely tune threads & batching' },
    { label: 'Restricted (±20% Bounded)', value: 'RESTRICTED', desc: 'Bounds changes within safe threshold' },
    { label: 'Locked (Template Enforced)', value: 'LOCKED', desc: 'Strict non-overridable parameter limits' }
  ];

  public mappingOverridabilityOptions: CustomSelectOption[] = [
    { label: 'Allowed at Creation', value: 'ALLOWED', desc: 'Operators can customize schema & column rules' },
    { label: 'Requires Lead Approval', value: 'REQUIRES_APPROVAL', desc: 'Triggers review barrier on mapping changes' },
    { label: 'Strictly Locked', value: 'LOCKED', desc: 'Mappings cannot be modified at runtime' }
  ];

  public scopeOverridabilityOptions: CustomSelectOption[] = [
    { label: 'Unrestricted Table Additions', value: 'UNRESTRICTED', desc: 'Operators can include any tables' },
    { label: 'Subset Only (Cannot Add)', value: 'SUBSET_ONLY', desc: 'Can only deselect tables from preset' },
    { label: 'Locked Object Boundary', value: 'LOCKED', desc: 'Strict object scope adherence' }
  ];

  public auditLogOptions: CustomSelectOption[] = [
    { label: 'Standard', value: 'STANDARD', desc: 'Lifecycle events & error summaries' },
    { label: 'Verbose', value: 'VERBOSE', desc: 'Detailed worker thread operations' },
    { label: 'Compliance Audit Trail', value: 'COMPLIANCE', desc: 'Cryptographic non-repudiation audit trail' }
  ];

  public vaultProviderOptions: CustomSelectOption[] = [
    { label: 'HashiCorp Vault KV v2', value: 'HASHICORP_VAULT', desc: 'HashiCorp Enterprise Vault' },
    { label: 'AWS Secrets Manager', value: 'AWS_SECRETS_MANAGER', desc: 'AWS IAM Role bound secrets' },
    { label: 'Azure Key Vault', value: 'AZURE_KEY_VAULT', desc: 'Azure Managed Identity Key Vault' },
    { label: 'Encrypted Environment Vault', value: 'ENVIRONMENT_VAULT', desc: 'Local AES-256 encrypted vault' }
  ];

  public newSourcePrivilege = '';
  public newTargetPrivilege = '';
  public newNetworkReq = '';

  public updateOverridability(partial: Partial<ReturnType<typeof this.ts.governance>['overridability']>): void {
    const curr = this.ts.governance();
    this.ts.updateGovernance({
      overridability: { ...curr.overridability, ...partial }
    });
  }

  public togglePeerReview(): void {
    const curr = this.ts.governance().approvalAndPolicy;
    this.ts.updateGovernance({
      approvalAndPolicy: {
        ...curr,
        requirePeerReview: !curr.requirePeerReview
      }
    });
  }

  public toggleChangeFreeze(): void {
    const curr = this.ts.governance().approvalAndPolicy;
    this.ts.updateGovernance({
      approvalAndPolicy: {
        ...curr,
        enforceChangeFreezeWindow: !curr.enforceChangeFreezeWindow
      }
    });
  }

  public updateAuditLog(auditLogLevel: AuditLogLevel): void {
    const curr = this.ts.governance().approvalAndPolicy;
    this.ts.updateGovernance({
      approvalAndPolicy: {
        ...curr,
        auditLogLevel
      }
    });
  }

  public updateVault(partial: Partial<ReturnType<typeof this.ts.governance>['secretReferenceRules']>): void {
    const curr = this.ts.governance();
    this.ts.updateGovernance({
      secretReferenceRules: { ...curr.secretReferenceRules, ...partial }
    });
  }

  public addSourcePrivilege(): void {
    if (!this.newSourcePrivilege.trim()) return;
    const curr = this.ts.governance().requiredCapabilities.sourcePrivileges;
    if (!curr.includes(this.newSourcePrivilege.trim().toUpperCase())) {
      this.ts.updateGovernance({
        requiredCapabilities: {
          ...this.ts.governance().requiredCapabilities,
          sourcePrivileges: [...curr, this.newSourcePrivilege.trim().toUpperCase()]
        }
      });
    }
    this.newSourcePrivilege = '';
  }

  public removeSourcePrivilege(priv: string): void {
    const curr = this.ts.governance().requiredCapabilities.sourcePrivileges;
    this.ts.updateGovernance({
      requiredCapabilities: {
        ...this.ts.governance().requiredCapabilities,
        sourcePrivileges: curr.filter(p => p !== priv)
      }
    });
  }

  public addTargetPrivilege(): void {
    if (!this.newTargetPrivilege.trim()) return;
    const curr = this.ts.governance().requiredCapabilities.targetPrivileges;
    if (!curr.includes(this.newTargetPrivilege.trim().toUpperCase())) {
      this.ts.updateGovernance({
        requiredCapabilities: {
          ...this.ts.governance().requiredCapabilities,
          targetPrivileges: [...curr, this.newTargetPrivilege.trim().toUpperCase()]
        }
      });
    }
    this.newTargetPrivilege = '';
  }

  public removeTargetPrivilege(priv: string): void {
    const curr = this.ts.governance().requiredCapabilities.targetPrivileges;
    this.ts.updateGovernance({
      requiredCapabilities: {
        ...this.ts.governance().requiredCapabilities,
        targetPrivileges: curr.filter(p => p !== priv)
      }
    });
  }

  public addNetworkReq(): void {
    if (!this.newNetworkReq.trim()) return;
    const curr = this.ts.governance().requiredCapabilities.networkRequirements;
    if (!curr.includes(this.newNetworkReq.trim())) {
      this.ts.updateGovernance({
        requiredCapabilities: {
          ...this.ts.governance().requiredCapabilities,
          networkRequirements: [...curr, this.newNetworkReq.trim()]
        }
      });
    }
    this.newNetworkReq = '';
  }

  public removeNetworkReq(req: string): void {
    const curr = this.ts.governance().requiredCapabilities.networkRequirements;
    this.ts.updateGovernance({
      requiredCapabilities: {
        ...this.ts.governance().requiredCapabilities,
        networkRequirements: curr.filter(r => r !== req)
      }
    });
  }
}
