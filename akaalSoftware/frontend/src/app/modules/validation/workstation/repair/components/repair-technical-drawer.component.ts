import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationRepairService } from '../validation-repair.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-repair-technical-drawer',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    @if (store.isTechnicalDrawerOpen()) {
      <div class="fixed inset-0 z-50 overflow-hidden">
        
        <!-- Backdrop -->
        <div
          (click)="store.toggleTechnicalDrawer(false)"
          class="absolute inset-0 bg-slate-900/40 backdrop-blur-2xs transition-opacity animate-in fade-in duration-200">
        </div>

        <div class="fixed inset-y-0 right-0 max-w-full flex pl-10">
          <div class="w-screen max-w-xl bg-white border-l border-slate-200 shadow-2xl flex flex-col justify-between animate-in slide-in-from-right duration-200">
            
            <!-- Drawer Header -->
            <div class="p-6 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
              <div class="flex items-center gap-3">
                <div class="w-9 h-9 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 shadow-2xs">
                  <app-lucide-icon name="code-2" [size]="18"></app-lucide-icon>
                </div>
                <div>
                  <h3 class="text-xs font-bold uppercase tracking-wider text-slate-900 font-heading">
                    Technical Details &amp; Provenance
                  </h3>
                  <p class="text-[11.5px] text-slate-500">Governed repair execution metadata &amp; cryptographic proofs</p>
                </div>
              </div>

              <button
                type="button"
                (click)="store.toggleTechnicalDrawer(false)"
                class="p-2 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer">
                <app-lucide-icon name="x" [size]="16"></app-lucide-icon>
              </button>
            </div>

            <!-- Drawer Body -->
            <div class="p-6 flex-1 overflow-y-auto flex flex-col gap-6 text-xs text-slate-700">
              
              <!-- Proposal Plan Identity -->
              <div class="flex flex-col gap-2.5">
                <div class="flex items-center gap-2 text-slate-700 font-bold uppercase tracking-wider text-xs font-heading">
                  <app-lucide-icon name="file-text" [size]="14" class="text-slate-500"></app-lucide-icon>
                  <span>Proposal Plan Identity</span>
                </div>
                <div class="p-4.5 rounded-xl bg-slate-50/80 border border-slate-200 flex flex-col gap-2.5 font-mono text-xs shadow-2xs">
                  <div class="flex items-center justify-between">
                    <span class="text-slate-500 font-sans font-medium">Proposal ID:</span>
                    <span class="font-bold text-slate-900 bg-white px-2.5 py-0.5 rounded border border-slate-200 shadow-2xs">{{ store.technicalDetails()?.proposalId || 'N/A' }}</span>
                  </div>
                  <div class="flex items-center justify-between">
                    <span class="text-slate-500 font-sans font-medium">Plan Version:</span>
                    <span class="font-bold text-slate-800">{{ store.technicalDetails()?.proposalVersion || 'v1.0.0' }}</span>
                  </div>
                  <div class="flex flex-col gap-1 pt-2 border-t border-slate-200/80">
                    <span class="text-slate-500 font-sans font-medium">Plan Fingerprint (HMAC-SHA256):</span>
                    <span class="text-[11px] break-all text-slate-800 bg-white p-2 rounded-lg border border-slate-200 shadow-2xs leading-relaxed">{{ store.technicalDetails()?.proposalFingerprint || 'N/A' }}</span>
                  </div>
                </div>
              </div>

              <!-- Execution & Checkpoint State -->
              <div class="flex flex-col gap-2.5">
                <div class="flex items-center gap-2 text-slate-700 font-bold uppercase tracking-wider text-xs font-heading">
                  <app-lucide-icon name="activity" [size]="14" class="text-slate-500"></app-lucide-icon>
                  <span>Runtime Fencing &amp; Checkpoint</span>
                </div>
                <div class="p-4.5 rounded-xl bg-slate-50/80 border border-slate-200 flex flex-col gap-2.5 font-mono text-xs shadow-2xs">
                  <div class="flex items-center justify-between">
                    <span class="text-slate-500 font-sans font-medium">Execution ID:</span>
                    <span class="font-bold text-slate-900 bg-white px-2.5 py-0.5 rounded border border-slate-200 shadow-2xs">{{ store.technicalDetails()?.executionId || 'Not Dispatched' }}</span>
                  </div>
                  <div class="flex items-center justify-between">
                    <span class="text-slate-500 font-sans font-medium">Provider Op ID:</span>
                    <span class="font-bold text-slate-800">{{ store.technicalDetails()?.providerOperationId || 'N/A' }}</span>
                  </div>
                  <div class="flex items-center justify-between">
                    <span class="text-slate-500 font-sans font-medium">Checkpoint Sequence:</span>
                    <span class="font-bold text-slate-800">{{ store.technicalDetails()?.checkpointSequence || 'N/A' }}</span>
                  </div>
                </div>
              </div>

              <!-- P7B Placement & Evidence -->
              <div class="flex flex-col gap-2.5">
                <div class="flex items-center gap-2 text-slate-700 font-bold uppercase tracking-wider text-xs font-heading">
                  <app-lucide-icon name="vault" [size]="14" class="text-slate-500"></app-lucide-icon>
                  <span>P7B Fabric &amp; Evidence Vault</span>
                </div>
                <div class="p-4.5 rounded-xl bg-slate-50/80 border border-slate-200 flex flex-col gap-2.5 font-mono text-xs shadow-2xs">
                  <div class="flex flex-col gap-1">
                    <span class="text-slate-500 font-sans font-medium">Placement Digest:</span>
                    <span class="text-[11px] break-all text-slate-800 bg-white p-2 rounded-lg border border-slate-200 shadow-2xs leading-relaxed">{{ store.technicalDetails()?.p7bPlacementDigest || 'N/A' }}</span>
                  </div>
                  <div class="flex items-center justify-between pt-2 border-t border-slate-200/80">
                    <span class="text-slate-500 font-sans font-medium">Evidence Reference:</span>
                    <span class="text-emerald-700 font-bold bg-emerald-50 px-2.5 py-0.5 rounded border border-emerald-200 shadow-2xs">{{ store.technicalDetails()?.evidenceRef || 'Pending Execution' }}</span>
                  </div>
                </div>
              </div>

              <!-- Canonical DML -->
              @if (store.technicalDetails()?.canonicalDmlStatement; as dml) {
                <div class="flex flex-col gap-2.5">
                  <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2 text-slate-700 font-bold uppercase tracking-wider text-xs font-heading">
                      <app-lucide-icon name="terminal" [size]="14" class="text-blue-600"></app-lucide-icon>
                      <span>Canonical DML Statement</span>
                    </div>
                    <button
                      type="button"
                      (click)="copyDml(dml)"
                      class="px-2.5 py-1 rounded-md text-xs font-semibold bg-white hover:bg-slate-100 border border-slate-200 text-slate-700 flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs">
                      <app-lucide-icon [name]="copied ? 'check' : 'copy'" [size]="12"></app-lucide-icon>
                      <span>{{ copied ? 'Copied' : 'Copy' }}</span>
                    </button>
                  </div>
                  <div class="p-4.5 rounded-xl bg-slate-50/90 border border-slate-200 text-slate-800 font-mono text-xs leading-relaxed overflow-x-auto whitespace-pre-wrap select-text shadow-2xs">
                    {{ dml }}
                  </div>
                </div>
              }

            </div>

            <!-- Drawer Footer -->
            <div class="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-end">
              <button
                type="button"
                (click)="store.toggleTechnicalDrawer(false)"
                class="h-8.5 px-4 rounded-lg bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 text-xs font-semibold cursor-pointer transition-colors shadow-2xs">
                Close Details
              </button>
            </div>

          </div>
        </div>

      </div>
    }
  `
})
export class RepairTechnicalDrawerComponent {
  readonly store = inject(ValidationRepairService);
  copied = false;

  copyDml(dml: string): void {
    if (navigator?.clipboard && dml) {
      navigator.clipboard.writeText(dml);
      this.copied = true;
      setTimeout(() => { this.copied = false; }, 2000);
    }
  }
}
