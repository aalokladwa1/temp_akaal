import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MigrationUiService } from '../../../../core/services/migration-ui.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ReadinessCheckItem } from '../../../../core/models/migration-view.models';

@Component({
  selector: 'app-step8-governance',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 animate-in fade-in duration-150 text-xs select-none">
      
      <!-- Header -->
      <div class="flex items-center justify-between pb-2 border-b border-slate-200">
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center font-bold">
            <app-lucide-icon name="shield-check" [size]="16"></app-lucide-icon>
          </div>
          <div>
            <h2 class="text-base font-bold text-slate-900">Step 8 &bull; PREFLIGHT GOVERNANCE &amp; MULTI-CUSTODY</h2>
            <p class="text-xs text-slate-500 font-medium">Automated readiness evaluation and multi-custody quorum sign-off before pipeline initialization.</p>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <span class="text-slate-500 font-medium">Preflight Verdict:</span>
          <span class="px-2.5 py-1 rounded-md font-bold text-xs"
            [class.bg-emerald-100]="readinessVerdict() === 'READY'"
            [class.text-emerald-800]="readinessVerdict() === 'READY'"
            [class.bg-amber-100]="readinessVerdict() === 'BLOCKED'"
            [class.text-amber-800]="readinessVerdict() === 'BLOCKED'">
            {{ readinessVerdict() === 'READY' ? 'READY FOR INITIALIZATION' : 'ATTENTION REQUIRED (BLOCKED)' }}
          </span>
        </div>
      </div>

      <!-- TOP: AUTOMATED PREFLIGHT READINESS SUMMARY -->
      <div class="flex flex-col gap-4 p-5 rounded-xl bg-white border border-slate-200/90 shadow-2xs">
        <div class="flex items-center justify-between pb-2.5 border-b border-slate-100">
          <div class="flex items-center gap-2">
            <app-lucide-icon name="activity" [size]="15" class="text-blue-600"></app-lucide-icon>
            <span class="font-bold text-slate-900 uppercase tracking-wider text-[11px]">1. Automated Preflight Readiness Checks (7 Domains)</span>
          </div>
          <span class="text-[11px] text-slate-500 font-medium">Evaluated against source, target, scope, and effective configuration</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          @for (check of readinessChecks; track check.id) {
            <div class="p-3 rounded-xl border flex items-start justify-between gap-3"
              [class.bg-slate-50]="check.status === 'PASSED'"
              [class.border-slate-200]="check.status === 'PASSED'"
              [class.bg-amber-50]="check.status === 'WARNING' || check.status === 'REQUIRES_ACTION'"
              [class.border-amber-200]="check.status === 'WARNING' || check.status === 'REQUIRES_ACTION'">
              
              <div class="flex items-start gap-2.5">
                <div class="w-6 h-6 rounded-md flex items-center justify-center font-bold text-[11px] shrink-0 mt-0.5"
                  [class.bg-emerald-100]="check.status === 'PASSED'"
                  [class.text-emerald-800]="check.status === 'PASSED'"
                  [class.bg-amber-100]="check.status !== 'PASSED'"
                  [class.text-amber-800]="check.status !== 'PASSED'">
                  <app-lucide-icon [name]="check.status === 'PASSED' ? 'check' : 'alert-triangle'" [size]="13"></app-lucide-icon>
                </div>

                <div class="flex flex-col gap-0.5">
                  <span class="font-bold text-slate-900 text-xs">{{ check.title }}</span>
                  <span class="text-[11px] text-slate-600 leading-relaxed font-normal">{{ check.detail }}</span>
                  @if (check.remediation) {
                    <span class="text-[10.5px] text-amber-800 font-semibold pt-0.5">Action: {{ check.remediation }}</span>
                  }
                </div>
              </div>

              <span class="px-2 py-0.5 rounded text-[10.5px] font-bold shrink-0"
                [class.bg-emerald-50]="check.status === 'PASSED'"
                [class.text-emerald-700]="check.status === 'PASSED'"
                [class.border]="check.status === 'PASSED'"
                [class.border-emerald-200]="check.status === 'PASSED'"
                [class.bg-amber-100]="check.status !== 'PASSED'"
                [class.text-amber-900]="check.status !== 'PASSED'">
                {{ check.status === 'PASSED' ? 'PASSED' : 'ACTION REQUIRED' }}
              </span>
            </div>
          }
        </div>
      </div>

      <!-- BOTTOM: MULTI-CUSTODY SIGN-OFF & QUORUM -->
      <div class="flex flex-col gap-4 p-5 rounded-xl bg-white border border-slate-200/90 shadow-2xs">
        
        <div class="flex items-center justify-between pb-2.5 border-b border-slate-100">
          <div class="flex items-center gap-2">
            <app-lucide-icon name="lock" [size]="15" class="text-amber-600"></app-lucide-icon>
            <span class="font-bold text-slate-900 uppercase tracking-wider text-[11px]">2. Multi-Custody Governance &amp; Four-Eyes Quorum</span>
          </div>
          <span class="text-[11px] text-slate-500 font-medium">Segregation of Duties (SoD) Enforced</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          
          <!-- Requester / Maker Card -->
          <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-2">
            <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Pipeline Author / Requester</span>
            <div class="flex items-center gap-2">
              <div class="w-7 h-7 rounded-full bg-blue-600 text-white font-bold flex items-center justify-center text-xs">
                AL
              </div>
              <div class="flex flex-col">
                <span class="font-bold text-slate-900 text-xs">{{ ms.wizardDraft().owner }}</span>
                <span class="text-[11px] text-slate-500">Lead Migration Engineer</span>
              </div>
            </div>
            <span class="text-[10.5px] text-slate-500 pt-1 border-t border-slate-200">
              Maker &bull; Cannot self-authorize production cutover barrier.
            </span>
          </div>

          <!-- Assigned Custody Approvers -->
          <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-2 md:col-span-2">
            <div class="flex items-center justify-between">
              <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Required Quorum Approvers (2 of 3 Required)</span>
              <span class="text-[10.5px] text-amber-700 font-bold bg-amber-50 px-2 py-0.5 rounded border border-amber-200">Pending Execution Authorization</span>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1">
              <div class="p-2 rounded-lg bg-white border border-slate-200 flex items-center justify-between">
                <div class="flex flex-col">
                  <span class="font-bold text-slate-900 text-xs">M. Vance</span>
                  <span class="text-[10.5px] text-slate-500">SecOps Lead (L4)</span>
                </div>
                <span class="w-2 h-2 rounded-full bg-amber-400" title="Awaiting Sign-Off"></span>
              </div>

              <div class="p-2 rounded-lg bg-white border border-slate-200 flex items-center justify-between">
                <div class="flex flex-col">
                  <span class="font-bold text-slate-900 text-xs">Sarah Chen</span>
                  <span class="text-[10.5px] text-slate-500">Principal DBA</span>
                </div>
                <span class="w-2 h-2 rounded-full bg-amber-400" title="Awaiting Sign-Off"></span>
              </div>

              <div class="p-2 rounded-lg bg-white border border-slate-200 flex items-center justify-between">
                <div class="flex flex-col">
                  <span class="font-bold text-slate-900 text-xs">Platform Gate</span>
                  <span class="text-[10.5px] text-slate-500">Automated Policy</span>
                </div>
                <span class="w-2 h-2 rounded-full bg-emerald-500" title="Preflight Validated"></span>
              </div>
            </div>
          </div>

        </div>

      </div>

    </div>
  `
})
export class Step8GovernanceComponent {
  public ms = inject(MigrationUiService);

  public readinessChecks: ReadinessCheckItem[] = [
    {
      id: 'chk-net',
      category: 'NETWORK',
      title: 'Network Transit & TLS Encryption',
      status: 'PASSED',
      detail: 'TLS 1.3 mutual handshake verified on port 1521 and 5432.'
    },
    {
      id: 'chk-src-prereqs',
      category: 'PREREQUISITES',
      title: 'Source Engine Supplemental Logging',
      status: 'PASSED',
      detail: 'Oracle ARCHIVELOG and SUPPLEMENTAL_LOG_DATA_MIN confirmed active on ORCLPDB.'
    },
    {
      id: 'chk-tgt-grants',
      category: 'CONNECTION',
      title: 'Target Write & DDL Authority',
      status: 'PASSED',
      detail: 'Role akaal_app has CREATE TABLE, INSERT, and REPLICATION grants on target.'
    },
    {
      id: 'chk-scope',
      category: 'SCHEMA',
      title: 'Scope & Table Mapping Completeness',
      status: 'PASSED',
      detail: '4 of 4 tables mapped with 100% column type coercions resolved.'
    },
    {
      id: 'chk-resource',
      category: 'STORAGE',
      title: 'Worker Memory & Spill Disk Quota',
      status: 'PASSED',
      detail: 'Worker pool allocated 16 threads &bull; 10 GB spill disk budget available.'
    },
    {
      id: 'chk-pii',
      category: 'GOVERNANCE',
      title: 'PII Masking & Privacy Policy',
      status: 'PASSED',
      detail: '1 format-preserving redaction rule configured for SSN_NO column.'
    },
    {
      id: 'chk-quorum',
      category: 'GOVERNANCE',
      title: 'Four-Eyes Maker-Checker Custody',
      status: 'PASSED',
      detail: 'Mandatory cutover barrier in place requiring 2 of 3 independent sign-offs.'
    }
  ];

  public readinessVerdict = signal<'READY' | 'BLOCKED'>('READY');
}
