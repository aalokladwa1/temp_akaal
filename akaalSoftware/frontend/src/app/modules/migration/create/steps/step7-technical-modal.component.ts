import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { Step7PlanStoreService } from '../../../../core/services/step7-plan-store.service';

@Component({
  selector: 'app-step7-technical-modal',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <!-- BACKDROP -->
    <div
      (click)="store.closeTechnicalModal()"
      class="fixed inset-0 bg-slate-900/50 z-50 flex items-center justify-center p-4 select-none font-sans">
      
      <!-- MODAL CARD -->
      <div
        (click)="$event.stopPropagation()"
        class="w-full max-w-3xl bg-white rounded-xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh] shadow-none">
        
        <!-- HEADER -->
        <header class="p-4 border-b border-slate-200 flex items-center justify-between gap-3 bg-slate-50/80">
          <div class="flex items-center gap-2.5 min-w-0">
            <div class="w-8 h-8 rounded-lg bg-slate-100 border border-slate-200 text-slate-700 flex items-center justify-center shrink-0">
              <app-lucide-icon name="file-code" [size]="16"></app-lucide-icon>
            </div>
            <div class="flex flex-col min-w-0">
              <h3 class="text-sm font-bold text-slate-900 m-0">Technical Plan Specification & Fingerprint</h3>
              <span class="text-[11px] text-slate-500">Authoritative deterministic execution descriptor and HMAC-SHA256 signature.</span>
            </div>
          </div>

          <button
            type="button"
            (click)="store.closeTechnicalModal()"
            class="w-7 h-7 rounded-lg border border-slate-200 bg-white hover:bg-slate-100 text-slate-500 hover:text-slate-800 flex items-center justify-center cursor-pointer transition-colors"
            title="Close Modal">
            <app-lucide-icon name="x" [size]="14"></app-lucide-icon>
          </button>
        </header>

        <!-- BODY -->
        <div class="p-5 overflow-y-auto flex flex-col gap-4 text-xs">
          
          <!-- METADATA STRIP -->
          <div class="grid grid-cols-4 gap-2.5 bg-slate-50 border border-slate-200 rounded-lg p-3">
            <div class="flex flex-col">
              <span class="text-[10.5px] font-semibold text-slate-500 uppercase">Plan ID</span>
              <span class="font-mono font-bold text-slate-900 text-xs truncate">{{ tech().planId }}</span>
            </div>
            <div class="flex flex-col">
              <span class="text-[10.5px] font-semibold text-slate-500 uppercase">Schema Version</span>
              <span class="font-mono font-bold text-slate-900 text-xs">v{{ tech().version }}</span>
            </div>
            <div class="flex flex-col">
              <span class="text-[10.5px] font-semibold text-slate-500 uppercase">Compiler</span>
              <span class="font-mono font-bold text-slate-900 text-xs truncate">{{ tech().compilerScheme }}</span>
            </div>
            <div class="flex flex-col">
              <span class="text-[10.5px] font-semibold text-slate-500 uppercase">Generated</span>
              <span class="font-mono text-slate-700 text-xs truncate">{{ tech().generatedTimestamp }}</span>
            </div>
          </div>

          <!-- CRYPTOGRAPHIC FINGERPRINT -->
          <div class="bg-slate-50 border border-slate-200 rounded-lg p-3.5 flex flex-col gap-2">
            <div class="flex items-center justify-between gap-2">
              <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                <app-lucide-icon name="fingerprint" [size]="13" class="text-slate-500"></app-lucide-icon>
                <span>Plan SHA-256 Fingerprint (Canonical Binding)</span>
              </span>

              <button
                type="button"
                (click)="copyFingerprint()"
                class="h-6 px-2.5 rounded bg-white border border-slate-300 hover:border-blue-500 text-slate-700 hover:text-blue-700 text-[10.5px] font-semibold flex items-center gap-1 cursor-pointer transition-colors">
                <app-lucide-icon [name]="copiedFingerprint ? 'check' : 'copy'" [size]="11"></app-lucide-icon>
                <span>{{ copiedFingerprint ? 'Copied!' : 'Copy Hash' }}</span>
              </button>
            </div>

            <div class="p-2 bg-white border border-slate-200 rounded font-mono text-xs text-slate-800 break-all select-all">
              {{ tech().canonicalFingerprint }}
            </div>
          </div>

          <!-- REDACTED JSON DEFINITION -->
          <div class="flex flex-col gap-2">
            <div class="flex items-center justify-between gap-2">
              <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                <app-lucide-icon name="code-2" [size]="13" class="text-slate-500"></app-lucide-icon>
                <span>Compiled Plan Definition (Redacted JSON)</span>
              </span>

              <button
                type="button"
                (click)="copyJson()"
                class="h-6 px-2.5 rounded bg-white border border-slate-300 hover:border-blue-500 text-slate-700 hover:text-blue-700 text-[10.5px] font-semibold flex items-center gap-1 cursor-pointer transition-colors">
                <app-lucide-icon [name]="copiedJson ? 'check' : 'copy'" [size]="11"></app-lucide-icon>
                <span>{{ copiedJson ? 'Copied!' : 'Copy JSON' }}</span>
              </button>
            </div>

            <pre class="p-3.5 bg-slate-50 text-slate-800 rounded-lg text-[11px] font-mono overflow-x-auto max-h-64 border border-slate-200 select-all leading-relaxed whitespace-pre"><code>{{ tech().redactedJsonDefinition }}</code></pre>
          </div>

        </div>

        <!-- FOOTER -->
        <footer class="p-4 border-t border-slate-200 flex items-center justify-end bg-slate-50/50 shrink-0">
          <button
            type="button"
            (click)="store.closeTechnicalModal()"
            class="h-8 px-4 rounded-lg bg-slate-800 hover:bg-slate-900 text-white text-xs font-bold cursor-pointer transition-colors">
            Close
          </button>
        </footer>

      </div>
    </div>
  `
})
export class Step7TechnicalModalComponent {
  public store = inject(Step7PlanStoreService);
  public tech = computed(() => this.store.technicalDetails());

  public copiedFingerprint = false;
  public copiedJson = false;

  public copyFingerprint(): void {
    navigator.clipboard.writeText(this.tech().canonicalFingerprint);
    this.copiedFingerprint = true;
    setTimeout(() => this.copiedFingerprint = false, 2000);
  }

  public copyJson(): void {
    navigator.clipboard.writeText(this.tech().redactedJsonDefinition);
    this.copiedJson = true;
    setTimeout(() => this.copiedJson = false, 2000);
  }
}
