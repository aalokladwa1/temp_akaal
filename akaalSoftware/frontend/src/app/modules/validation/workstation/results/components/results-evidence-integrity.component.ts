import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationResultsService } from '../validation-results.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-results-evidence-integrity',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200 rounded-xl p-6 sm:p-7 shadow-2xs">
      
      <!-- Section Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 mb-5 border-b border-slate-100">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-700">
            <app-lucide-icon name="file-text" [size]="16" />
          </div>
          <div>
            <h2 class="text-sm font-bold text-slate-900 font-heading">
              Evidence &amp; Integrity Record
            </h2>
            <p class="text-xs text-slate-500">
              Content integrity provenance (Evidence #12 Authority)
            </p>
          </div>
        </div>

        <div class="text-xs text-slate-500 font-sans">
          Immutable Content Digest
        </div>
      </div>

      <!-- Evidence Content -->
      @if (store.evidence().evidenceAvailable) {
        
        <div class="flex flex-col gap-5">
          
          <!-- Content Integrity Digest Box (Strictly labeled as Content Integrity Digest) -->
          <div class="p-5 rounded-xl bg-slate-50/80 border border-slate-200/90 flex flex-col gap-3 shadow-2xs">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div class="flex items-center gap-2">
                <app-lucide-icon name="hash" [size]="14" class="text-slate-500" />
                <span class="text-xs font-bold text-slate-800 font-heading">
                  Content Integrity Digest
                </span>
                <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-slate-200 text-slate-700">
                  {{ store.evidence().digestAlgorithm || 'SHA-256' }}
                </span>
              </div>

              <!-- One-click Copy Button -->
              <button
                type="button"
                (click)="store.copyDigest()"
                class="h-8 px-3 rounded-lg bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs self-start sm:self-auto">
                <app-lucide-icon [name]="store.copiedDigest() ? 'check' : 'copy'" [size]="13" [class.text-emerald-600]="store.copiedDigest()" />
                <span>{{ store.copiedDigest() ? 'Copied Digest' : 'Copy Digest' }}</span>
              </button>
            </div>

            <!-- Monospaced Digest Display -->
            <div class="p-3 bg-white border border-slate-200 rounded-lg font-mono text-xs text-slate-800 break-all select-all leading-relaxed">
              {{ store.evidence().contentDigest }}
            </div>

            <!-- Mandatory Disclaimer (Directive #7) -->
            <div class="flex items-start gap-2 text-[11px] text-slate-500 leading-normal pt-1">
              <app-lucide-icon name="info" [size]="13" class="text-slate-400 shrink-0 mt-0.5" />
              <span>
                Content integrity digest is computed directly from execution artifacts for immutable verification. SHA-256 digest represents cryptographic content hash and does not constitute a digital signature or compliance certification.
              </span>
            </div>
          </div>

          <!-- Provenance Metadata Grid -->
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
            
            <!-- Bundle ID -->
            <div class="p-4 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col gap-1">
              <span class="text-xs text-slate-500 font-sans">Evidence Bundle ID</span>
              <span class="text-xs font-mono font-bold text-slate-900 truncate">
                {{ store.evidence().evidenceBundleId || '—' }}
              </span>
            </div>

            <!-- Generated Timestamp -->
            <div class="p-4 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col gap-1">
              <span class="text-xs text-slate-500 font-sans">Generated Timestamp</span>
              <span class="text-xs font-sans text-slate-800">
                {{ (store.evidence().generatedAt | date:'medium') || '—' }}
              </span>
            </div>

            <!-- Bundle Size -->
            <div class="p-4 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col gap-1">
              <span class="text-xs text-slate-500 font-sans">Bundle Payload Size</span>
              <span class="text-xs font-mono font-semibold text-slate-800">
                {{ store.evidence().bundleSizeFormatted || '—' }}
              </span>
            </div>

          </div>

        </div>

      } @else {
        
        <!-- Evidence Unavailable State -->
        <div class="p-5 rounded-xl bg-slate-50/60 border border-slate-200/80 text-center flex flex-col items-center justify-center gap-2 text-slate-500 py-8">
          <app-lucide-icon name="file-text" [size]="24" class="text-slate-400" />
          <span class="text-xs font-medium text-slate-700">Evidence is not currently available</span>
          <p class="text-[11px] text-slate-500 max-w-md">
            {{ store.evidence().integrityNote || 'Evidence bundles and content integrity digests are recorded upon mission execution completion.' }}
          </p>
        </div>

      }

    </section>
  `
})
export class ResultsEvidenceIntegrityComponent {
  readonly store = inject(ValidationResultsService);
}
