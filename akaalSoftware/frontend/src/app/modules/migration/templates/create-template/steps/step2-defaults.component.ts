import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CreateTemplateService } from '../create-template.service';
import { ExecutionPriority, ConnectionPolicy, RequiredAtUseChecklist } from '../create-template.models';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-step2-defaults',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="space-y-6 animate-in fade-in duration-150 text-xs font-sans">
      
      <!-- Top Section Header -->
      <div class="flex flex-col gap-1 border-b border-slate-200 pb-3">
        <h2 class="text-base font-bold text-slate-900 tracking-tight font-heading">Migration Defaults</h2>
        <p class="text-xs text-slate-500 font-normal">
          Establish starting migration defaults and declare the required-at-use inputs that operators must provide during migration creation.
        </p>
      </div>

      <!-- Zero Secrets Callout Banner -->
      <div class="p-3.5 bg-slate-100 border border-slate-200 rounded-lg flex items-start gap-3">
        <app-lucide-icon name="shield-check" [size]="16" class="text-slate-700 shrink-0 mt-0.5"></app-lucide-icon>
        <div class="flex flex-col gap-0.5">
          <span class="font-bold text-slate-900">Zero Plaintext Secrets Law</span>
          <p class="text-[11px] text-slate-600 font-normal m-0 leading-relaxed">
            Templates never store credentials, passwords, or private keys. Connection endpoints and authentication are resolved dynamically at runtime through encrypted connection profiles or logical secret vault references.
          </p>
        </div>
      </div>

      <!-- Migration Naming & Priority Section -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
        
        <!-- Naming Pattern -->
        <div class="flex flex-col gap-1.5">
          <label for="naming-pattern" class="font-semibold text-slate-800 flex items-center gap-1">
            <span>Default Migration Naming Pattern</span>
            <span class="text-rose-500">*</span>
          </label>
          <input
            id="naming-pattern"
            type="text"
            [ngModel]="ts.migrationDefaults().migrationNamePattern"
            (ngModelChange)="ts.updateDefaults({ migrationNamePattern: $event })"
            [placeholder]="'e.g. MIG-{{PROJECT}}-{{ENV}}-{{SEQ}}'"
            class="h-9 px-3 bg-white border border-slate-200 focus:border-blue-600 rounded-md font-mono text-xs font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none transition-colors shadow-2xs" />
          
          <!-- Token Helpers -->
          <div class="flex items-center gap-1.5 flex-wrap pt-0.5">
            <span class="text-[10px] text-slate-400">Tokens:</span>
            <button
              type="button"
              (click)="insertToken('{{PROJECT}}')"
              class="px-1.5 py-0.5 text-[10px] font-mono bg-slate-100 hover:bg-slate-200 text-slate-700 rounded transition-colors cursor-pointer border border-slate-200">
              {{ '{{PROJECT}}' }}
            </button>
            <button
              type="button"
              (click)="insertToken('{{ENV}}')"
              class="px-1.5 py-0.5 text-[10px] font-mono bg-slate-100 hover:bg-slate-200 text-slate-700 rounded transition-colors cursor-pointer border border-slate-200">
              {{ '{{ENV}}' }}
            </button>
            <button
              type="button"
              (click)="insertToken('{{DATE}}')"
              class="px-1.5 py-0.5 text-[10px] font-mono bg-slate-100 hover:bg-slate-200 text-slate-700 rounded transition-colors cursor-pointer border border-slate-200">
              {{ '{{DATE}}' }}
            </button>
            <button
              type="button"
              (click)="insertToken('{{SEQ}}')"
              class="px-1.5 py-0.5 text-[10px] font-mono bg-slate-100 hover:bg-slate-200 text-slate-700 rounded transition-colors cursor-pointer border border-slate-200">
              {{ '{{SEQ}}' }}
            </button>
          </div>
        </div>

        <!-- Default Execution Priority -->
        <div class="flex flex-col gap-1.5">
          <label class="font-semibold text-slate-800">
            Default Execution Priority
          </label>
          <div class="grid grid-cols-4 gap-2">
            @for (p of priorities; track p.value) {
              <button
                type="button"
                (click)="ts.updateDefaults({ executionPriority: p.value })"
                class="h-9 px-2 rounded-md border text-xs font-semibold transition-all cursor-pointer flex items-center justify-center"
                [class]="ts.migrationDefaults().executionPriority === p.value
                  ? 'bg-blue-600 text-white border-blue-600 shadow-2xs'
                  : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'">
                {{ p.label }}
              </button>
            }
          </div>
          <span class="text-[11px] text-slate-400 font-normal">
            Dictates task queue placement and resource thread allocation when provisioning.
          </span>
        </div>

      </div>

      <!-- Logical Connection Preferences -->
      <div class="flex flex-col gap-2.5">
        <label class="font-semibold text-slate-800">
          Logical Connection Resolution Preferences
        </label>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          
          <!-- Source Connection Policy -->
          <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-3 shadow-2xs">
            <div class="flex items-center justify-between">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Source Connection Policy</span>
              <span class="px-2 py-0.5 text-[10px] font-medium bg-slate-100 text-slate-600 rounded-md">Extract Binding</span>
            </div>
            
            <div class="flex flex-col gap-2">
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="src-conn-policy"
                  [checked]="ts.migrationDefaults().sourceConnectionPolicy === 'REQUIRE_AT_CREATION'"
                  (change)="ts.updateDefaults({ sourceConnectionPolicy: 'REQUIRE_AT_CREATION' })"
                  class="text-blue-600 focus:ring-0" />
                <span class="text-xs font-medium text-slate-800">Require operator selection at creation</span>
              </label>

              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="src-conn-policy"
                  [checked]="ts.migrationDefaults().sourceConnectionPolicy === 'PROJECT_POOL'"
                  (change)="ts.updateDefaults({ sourceConnectionPolicy: 'PROJECT_POOL' })"
                  class="text-blue-600 focus:ring-0" />
                <span class="text-xs font-medium text-slate-800">Default to Project's primary source pool</span>
              </label>

              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="src-conn-policy"
                  [checked]="ts.migrationDefaults().sourceConnectionPolicy === 'LOGICAL_TAG'"
                  (change)="ts.updateDefaults({ sourceConnectionPolicy: 'LOGICAL_TAG' })"
                  class="text-blue-600 focus:ring-0" />
                <span class="text-xs font-medium text-slate-800">Match by logical tag</span>
              </label>
            </div>

            @if (ts.migrationDefaults().sourceConnectionPolicy === 'LOGICAL_TAG') {
              <div class="flex flex-col gap-1 pt-1">
                <span class="text-[11px] font-semibold text-slate-600">Source Logical Tag</span>
                <input
                  type="text"
                  [ngModel]="ts.migrationDefaults().sourceConnectionTag"
                  (ngModelChange)="ts.updateDefaults({ sourceConnectionTag: $event })"
                  placeholder="e.g. production-oracle-primary"
                  class="h-8 px-2.5 bg-slate-50 border border-slate-200 rounded-md text-xs font-mono text-slate-900 focus:outline-none focus:border-blue-600" />
              </div>
            }
          </div>

          <!-- Target Connection Policy -->
          <div class="p-4 bg-white border border-slate-200 rounded-lg flex flex-col gap-3 shadow-2xs">
            <div class="flex items-center justify-between">
              <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Target Connection Policy</span>
              <span class="px-2 py-0.5 text-[10px] font-medium bg-slate-100 text-slate-600 rounded-md">Ingest Binding</span>
            </div>
            
            <div class="flex flex-col gap-2">
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="tgt-conn-policy"
                  [checked]="ts.migrationDefaults().targetConnectionPolicy === 'REQUIRE_AT_CREATION'"
                  (change)="ts.updateDefaults({ targetConnectionPolicy: 'REQUIRE_AT_CREATION' })"
                  class="text-blue-600 focus:ring-0" />
                <span class="text-xs font-medium text-slate-800">Require operator selection at creation</span>
              </label>

              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="tgt-conn-policy"
                  [checked]="ts.migrationDefaults().targetConnectionPolicy === 'PROJECT_POOL'"
                  (change)="ts.updateDefaults({ targetConnectionPolicy: 'PROJECT_POOL' })"
                  class="text-blue-600 focus:ring-0" />
                <span class="text-xs font-medium text-slate-800">Default to Project's primary target pool</span>
              </label>

              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="tgt-conn-policy"
                  [checked]="ts.migrationDefaults().targetConnectionPolicy === 'LOGICAL_TAG'"
                  (change)="ts.updateDefaults({ targetConnectionPolicy: 'LOGICAL_TAG' })"
                  class="text-blue-600 focus:ring-0" />
                <span class="text-xs font-medium text-slate-800">Match by logical tag</span>
              </label>
            </div>

            @if (ts.migrationDefaults().targetConnectionPolicy === 'LOGICAL_TAG') {
              <div class="flex flex-col gap-1 pt-1">
                <span class="text-[11px] font-semibold text-slate-600">Target Logical Tag</span>
                <input
                  type="text"
                  [ngModel]="ts.migrationDefaults().targetConnectionTag"
                  (ngModelChange)="ts.updateDefaults({ targetConnectionTag: $event })"
                  placeholder="e.g. analytics-snowflake-dw"
                  class="h-8 px-2.5 bg-slate-50 border border-slate-200 rounded-md text-xs font-mono text-slate-900 focus:outline-none focus:border-blue-600" />
              </div>
            }
          </div>

        </div>
      </div>

      <!-- Required-At-Use Operator Inputs Checklist -->
      <div class="flex flex-col gap-2.5">
        <div class="flex items-center justify-between">
          <label class="font-semibold text-slate-800">
            Required-at-Use Operator Checklist
          </label>
          <span class="text-[11px] text-slate-400">Mandatory values enforced during Migration Wizard application</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          
          <label class="p-3 bg-white border border-slate-200 rounded-lg flex items-start gap-2.5 cursor-pointer hover:bg-slate-50/50 transition-colors shadow-2xs">
            <input
              type="checkbox"
              [checked]="ts.migrationDefaults().requiredAtUse.targetDatabaseRequired"
              (change)="toggleRequiredField('targetDatabaseRequired')"
              class="rounded text-blue-600 focus:ring-0 mt-0.5" />
            <div class="flex flex-col">
              <span class="font-bold text-slate-900">Target Database / Schema</span>
              <span class="text-[11px] text-slate-500 font-normal">Operator must specify target container namespace</span>
            </div>
          </label>

          <label class="p-3 bg-white border border-slate-200 rounded-lg flex items-start gap-2.5 cursor-pointer hover:bg-slate-50/50 transition-colors shadow-2xs">
            <input
              type="checkbox"
              [checked]="ts.migrationDefaults().requiredAtUse.scheduleRequired"
              (change)="toggleRequiredField('scheduleRequired')"
              class="rounded text-blue-600 focus:ring-0 mt-0.5" />
            <div class="flex flex-col">
              <span class="font-bold text-slate-900">Execution Schedule</span>
              <span class="text-[11px] text-slate-500 font-normal">Operator must set recurring cron or kickoff window</span>
            </div>
          </label>

          <label class="p-3 bg-white border border-slate-200 rounded-lg flex items-start gap-2.5 cursor-pointer hover:bg-slate-50/50 transition-colors shadow-2xs">
            <input
              type="checkbox"
              [checked]="ts.migrationDefaults().requiredAtUse.secretBindingsRequired"
              (change)="toggleRequiredField('secretBindingsRequired')"
              class="rounded text-blue-600 focus:ring-0 mt-0.5" />
            <div class="flex flex-col">
              <span class="font-bold text-slate-900">Secret Bindings / Vault Auth</span>
              <span class="text-[11px] text-slate-500 font-normal">Operator must verify vault access authorization</span>
            </div>
          </label>

          <label class="p-3 bg-white border border-slate-200 rounded-lg flex items-start gap-2.5 cursor-pointer hover:bg-slate-50/50 transition-colors shadow-2xs">
            <input
              type="checkbox"
              [checked]="ts.migrationDefaults().requiredAtUse.workspaceSelectionRequired"
              (change)="toggleRequiredField('workspaceSelectionRequired')"
              class="rounded text-blue-600 focus:ring-0 mt-0.5" />
            <div class="flex flex-col">
              <span class="font-bold text-slate-900">Project / Workspace Binding</span>
              <span class="text-[11px] text-slate-500 font-normal">Operator must select target project workspace</span>
            </div>
          </label>

          <label class="p-3 bg-white border border-slate-200 rounded-lg flex items-start gap-2.5 cursor-pointer hover:bg-slate-50/50 transition-colors shadow-2xs">
            <input
              type="checkbox"
              [checked]="ts.migrationDefaults().requiredAtUse.notificationChannelsRequired"
              (change)="toggleRequiredField('notificationChannelsRequired')"
              class="rounded text-blue-600 focus:ring-0 mt-0.5" />
            <div class="flex flex-col">
              <span class="font-bold text-slate-900">Notification Webhooks</span>
              <span class="text-[11px] text-slate-500 font-normal">Operator must bind alert Slack / PagerDuty channel</span>
            </div>
          </label>

        </div>
      </div>

    </div>
  `
})
export class Step2DefaultsComponent {
  public ts = inject(CreateTemplateService);

  public priorities: { label: string; value: ExecutionPriority }[] = [
    { label: 'Low', value: 'LOW' },
    { label: 'Normal', value: 'NORMAL' },
    { label: 'High', value: 'HIGH' },
    { label: 'Critical', value: 'CRITICAL' }
  ];

  public insertToken(token: string): void {
    const current = this.ts.migrationDefaults().migrationNamePattern;
    this.ts.updateDefaults({ migrationNamePattern: current + '-' + token });
  }

  public toggleRequiredField(field: keyof RequiredAtUseChecklist): void {
    const curr = this.ts.migrationDefaults().requiredAtUse;
    this.ts.updateDefaults({
      requiredAtUse: {
        ...curr,
        [field]: !curr[field]
      }
    });
  }
}
