import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationRepairService } from '../validation-repair.service';
import { RepairOperationFamily } from '../validation-repair.models';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-repair-proposal-card',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200/80 rounded-xl p-6 shadow-2xs flex flex-col gap-5">
      
      <!-- Section Header -->
      <div class="flex items-center justify-between flex-wrap gap-3 pb-4 border-b border-slate-100">
        <div class="flex items-center gap-2.5">
          <div class="w-7 h-7 rounded-md bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 shrink-0">
            <app-lucide-icon name="file-code" [size]="14"></app-lucide-icon>
          </div>
          <div>
            <h2 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
              2. Repair Proposal &amp; Compensating Strategy
            </h2>
            <p class="text-[11px] text-slate-500 mt-0.5">
              Compiled compensating target mutation strategy satisfying canonical transformation policy
            </p>
          </div>
        </div>

        @if (store.proposal(); as prop) {
          <div class="flex items-center gap-2">
            <span [ngClass]="getOperationFamilyBadgeClass(prop.operationFamily)"
                  class="px-2.5 py-1 rounded-md text-[10.5px] font-bold uppercase tracking-wider border flex items-center gap-1.5">
              <app-lucide-icon [name]="getOperationFamilyIcon(prop.operationFamily)" [size]="12"></app-lucide-icon>
              <span>{{ formatOperationFamily(prop.operationFamily) }}</span>
            </span>
          </div>
        }
      </div>

      <!-- Proposal Body -->
      @if (store.proposal(); as prop) {
        <div class="flex flex-col gap-4">
          
          <!-- Summary Callout -->
          <div class="p-5 sm:p-6 rounded-xl bg-slate-50/80 border border-slate-200/90 flex flex-col gap-3 shadow-2xs">
            <div class="flex items-center justify-between flex-wrap gap-3 text-xs">
              <div class="flex items-center gap-2">
                <app-lucide-icon name="table" [size]="13" class="text-slate-400"></app-lucide-icon>
                <span class="text-slate-500 font-medium">Target Object:</span>
                <span class="font-mono font-bold text-slate-900 bg-white px-2.5 py-1 rounded-md border border-slate-200 shadow-2xs">{{ prop.targetObject }}</span>
              </div>
              <div class="flex items-center gap-2">
                <app-lucide-icon name="key" [size]="13" class="text-slate-400"></app-lucide-icon>
                <span class="text-slate-500 font-medium">Record Key:</span>
                <span class="font-mono font-bold text-slate-900 bg-white px-2.5 py-1 rounded-md border border-slate-200 shadow-2xs">
                  {{ prop.recordKey }}
                </span>
              </div>
              <div class="flex items-center gap-2 text-slate-500 font-mono text-[11.5px]">
                <app-lucide-icon name="clock" [size]="12" class="text-slate-400"></app-lucide-icon>
                <span>Version {{ prop.proposalVersion }}</span>
                <span>&bull;</span>
                <span>Compiled {{ prop.createdAt }}</span>
              </div>
            </div>

            <p class="text-xs text-slate-900 font-semibold leading-relaxed mt-1">
              {{ prop.summaryNote }}
            </p>

            <p class="text-xs text-slate-600 leading-relaxed">
              {{ prop.detailedRationale }}
            </p>
          </div>

          <!-- Proposal Fingerprint & Integrity Card -->
          <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-xl bg-slate-50/80 border border-slate-200 text-xs shadow-2xs">
            <div class="flex items-center gap-3 flex-wrap min-w-0">
              <div class="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600 shrink-0">
                <app-lucide-icon name="fingerprint" [size]="16"></app-lucide-icon>
              </div>
              <span class="font-bold text-slate-800 font-heading">Proposal Plan Fingerprint:</span>
              <span class="font-mono text-slate-700 bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-2xs break-all leading-normal text-[11.5px]" [title]="prop.proposalFingerprint">
                {{ prop.proposalFingerprint }}
              </span>
            </div>

            <button
              type="button"
              (click)="copyFingerprint(prop.proposalFingerprint)"
              class="px-3.5 py-2 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-semibold flex items-center gap-2 cursor-pointer shrink-0 transition-colors shadow-2xs">
              <app-lucide-icon [name]="copiedFingerprint ? 'check' : 'copy'" [size]="13"></app-lucide-icon>
              <span>{{ copiedFingerprint ? 'Copied' : 'Copy Digest' }}</span>
            </button>
          </div>

          <!-- Canonical DML Preview (Light Enterprise Theme) -->
          @if (prop.canonicalDmlPreview) {
            <div class="flex flex-col gap-3 p-5 sm:p-6 rounded-xl bg-slate-50/90 border border-slate-200 text-xs shadow-2xs">
              <div class="flex items-center justify-between text-xs text-slate-500 pb-3 border-b border-slate-200/80 flex-wrap gap-2">
                <div class="flex items-center gap-2 font-sans font-bold uppercase tracking-wider text-slate-700 font-heading">
                  <app-lucide-icon name="code-2" [size]="15" class="text-blue-600"></app-lucide-icon>
                  <span>Canonical DML Statement Preview</span>
                </div>
                <div class="flex items-center gap-3">
                  <span class="text-slate-400 font-sans hidden sm:inline text-[11.5px]">Read-only preview compiled by backend planner</span>
                  <button
                    type="button"
                    (click)="copyDml(prop.canonicalDmlPreview)"
                    class="px-3 py-1.5 rounded-lg bg-white hover:bg-slate-100 border border-slate-200 text-slate-700 text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs">
                    <app-lucide-icon [name]="copiedDml ? 'check' : 'copy'" [size]="12"></app-lucide-icon>
                    <span>{{ copiedDml ? 'Copied' : 'Copy DML' }}</span>
                  </button>
                </div>
              </div>
              <pre class="overflow-x-auto text-[12px] font-mono leading-relaxed text-slate-800 whitespace-pre-wrap py-2 select-text bg-white p-4 sm:p-5 rounded-lg border border-slate-200/80 shadow-2xs">{{ prop.canonicalDmlPreview }}</pre>
            </div>
          }

        </div>
      } @else {
        <!-- No Proposal Available State -->
        <div class="p-10 rounded-xl bg-slate-50 border border-slate-200 text-center flex flex-col items-center justify-center gap-3">
          <div class="w-12 h-12 rounded-xl bg-slate-200/80 flex items-center justify-center text-slate-500">
            <app-lucide-icon name="file-x" [size]="22"></app-lucide-icon>
          </div>
          <span class="text-xs font-bold text-slate-800">No Canonical Repair Proposal Established</span>
          <p class="text-xs text-slate-500 max-w-md leading-relaxed">
            Controlled repair planning has not compiled a compensating strategy for the current selection.
          </p>
        </div>
      }

    </section>
  `
})
export class RepairProposalCardComponent {
  readonly store = inject(ValidationRepairService);
  copiedFingerprint = false;
  copiedDml = false;

  copyFingerprint(fp: string): void {
    if (navigator?.clipboard) {
      navigator.clipboard.writeText(fp);
      this.copiedFingerprint = true;
      setTimeout(() => { this.copiedFingerprint = false; }, 2000);
    }
  }

  copyDml(dml: string): void {
    if (navigator?.clipboard && dml) {
      navigator.clipboard.writeText(dml);
      this.copiedDml = true;
      setTimeout(() => { this.copiedDml = false; }, 2000);
    }
  }

  formatOperationFamily(fam: RepairOperationFamily): string {
    switch (fam) {
      case 'UPDATE_DIFFERING_ATTRIBUTES': return 'Update Differing Attributes';
      case 'INSERT_MISSING_TARGET': return 'Insert Missing Record';
      case 'DELETE_EXTRA_TARGET': return 'Delete Extra Record (Destructive)';
      case 'STRUCTURAL_UNSUPPORTED': return 'Structural Remediation Unavailable';
      case 'NO_SAFE_AUTOMATIC_PROPOSAL': return 'No Safe Automatic Proposal';
      case 'MANUAL_REMEDIATION': return 'Manual Remediation Required';
      default: return fam;
    }
  }

  getOperationFamilyBadgeClass(fam: RepairOperationFamily): string {
    switch (fam) {
      case 'UPDATE_DIFFERING_ATTRIBUTES': return 'bg-blue-50 border-blue-200 text-blue-800';
      case 'INSERT_MISSING_TARGET': return 'bg-emerald-50 border-emerald-200 text-emerald-800';
      case 'DELETE_EXTRA_TARGET': return 'bg-red-50 border-red-200 text-red-800';
      case 'STRUCTURAL_UNSUPPORTED': return 'bg-amber-50 border-amber-200 text-amber-800';
      default: return 'bg-slate-100 border-slate-200 text-slate-700';
    }
  }

  getOperationFamilyIcon(fam: RepairOperationFamily): string {
    switch (fam) {
      case 'UPDATE_DIFFERING_ATTRIBUTES': return 'file-diff';
      case 'INSERT_MISSING_TARGET': return 'plus-circle';
      case 'DELETE_EXTRA_TARGET': return 'trash-2';
      case 'STRUCTURAL_UNSUPPORTED': return 'alert-triangle';
      default: return 'file-code';
    }
  }
}
