import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ValidationUiService } from '../../../core/services/validation-ui.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-new-validation-wizard',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-8 w-full max-w-[1680px] mx-auto pb-16 font-sans select-none animate-in fade-in duration-150">
      
      <!-- Top Header -->
      <div class="flex items-center justify-between gap-4 pb-6 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-2">
            <a routerLink="/migration/validation" class="text-xs font-semibold text-blue-600 hover:underline">Validation Operations</a>
            <span class="text-slate-300">/</span>
            <span class="text-xs font-semibold text-slate-700">New Validation Wizard</span>
          </div>
          <h1 class="text-2xl font-bold font-heading text-slate-900 tracking-tight">New Validation (M8)</h1>
          <p class="text-sm text-slate-600 font-medium">Independent cross-database comparison, post-migration verification, and reconciliation.</p>
        </div>

        <span class="px-3 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-bold flex items-center gap-1.5">
          <app-lucide-icon name="shield-check" [size]="14"></app-lucide-icon>
          <span>READ-ONLY NON-MUTATING VERIFICATION</span>
        </span>
      </div>

      <!-- 6-Step Indicator -->
      <div class="p-3 rounded-2xl bg-white border border-slate-200 shadow-xs flex items-center justify-between overflow-x-auto gap-2">
        @for (st of steps; track st.step) {
          <button
            type="button"
            (click)="vs.newValidationDraft().currentStep = st.step"
            class="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all shrink-0 cursor-pointer"
            [class.bg-blue-600]="vs.newValidationDraft().currentStep === st.step"
            [class.text-white]="vs.newValidationDraft().currentStep === st.step"
            [class.shadow-2xs]="vs.newValidationDraft().currentStep === st.step"
            [class.text-slate-700]="vs.newValidationDraft().currentStep !== st.step">
            <span 
              class="w-5 h-5 rounded-full flex items-center justify-center text-[10px]"
              [class.bg-blue-800]="vs.newValidationDraft().currentStep === st.step"
              [class.text-white]="vs.newValidationDraft().currentStep === st.step"
              [class.bg-slate-200]="vs.newValidationDraft().currentStep !== st.step"
              [class.text-slate-700]="vs.newValidationDraft().currentStep !== st.step">
              {{ st.step }}
            </span>
            <span>{{ st.label }}</span>
          </button>
        }
      </div>

      <!-- Step Content Container -->
      <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-6">
        @switch (vs.newValidationDraft().currentStep) {
          @case (1) {
            <div class="flex flex-col gap-4 text-xs">
              <h3 class="text-sm font-bold text-slate-900">Step 1 • Validation Definition &amp; Scope</h3>
              <div class="flex flex-col gap-1.5">
                <label class="font-bold text-slate-800">Validation Name</label>
                <input type="text" [(ngModel)]="vs.newValidationDraft().name" class="px-3.5 py-2.5 rounded-xl bg-slate-50 border border-slate-200 text-xs font-semibold" />
              </div>
            </div>
          }
          @case (2) {
            <div class="flex flex-col gap-4 text-xs">
              <h3 class="text-sm font-bold text-slate-900">Step 2 • Reference (Source) Database</h3>
              <p class="text-slate-600">Reference system against which comparison is verified.</p>
            </div>
          }
          @case (3) {
            <div class="flex flex-col gap-4 text-xs">
              <h3 class="text-sm font-bold text-slate-900">Step 3 • Target (Comparison) Database</h3>
              <p class="text-slate-600">Target system evaluated for state and row parity.</p>
            </div>
          }
          @case (4) {
            <div class="flex flex-col gap-4 text-xs">
              <h3 class="text-sm font-bold text-slate-900">Step 4 • Scope &amp; Object Correspondence</h3>
              <p class="text-slate-600">42 tables mapped with 1:1 key correspondence.</p>
            </div>
          }
          @case (5) {
            <div class="flex flex-col gap-4 text-xs">
              <h3 class="text-sm font-bold text-slate-900">Step 5 • Validation Configuration Profile</h3>
              <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div class="p-4 rounded-xl border-2 border-blue-600 bg-blue-50/20 flex flex-col gap-1">
                  <span class="font-bold text-slate-900">Deep Profile</span>
                  <span class="text-[11px] text-slate-500">Row-level hash + Merkle tree check</span>
                </div>
                <div class="p-4 rounded-xl border border-slate-200 flex flex-col gap-1">
                  <span class="font-bold text-slate-900">Standard</span>
                  <span class="text-[11px] text-slate-500">Counts &amp; partition checksums</span>
                </div>
              </div>
            </div>
          }
          @case (6) {
            <div class="flex flex-col gap-4 text-xs">
              <h3 class="text-sm font-bold text-slate-900">Step 6 • Review &amp; Launch</h3>
              <p class="text-slate-600">Ready to execute read-only verification against target.</p>
            </div>
          }
        }
      </div>

      <!-- Navigation Footer -->
      <div class="p-4 bg-white border border-slate-200 rounded-2xl shadow-xs flex items-center justify-between">
        <button
          type="button"
          (click)="prevStep()"
          [disabled]="vs.newValidationDraft().currentStep === 1"
          class="px-4 py-2 rounded-xl bg-slate-100 text-slate-700 text-xs font-bold disabled:opacity-40">
          Previous
        </button>

        @if (vs.newValidationDraft().currentStep < 6) {
          <button
            type="button"
            (click)="nextStep()"
            class="px-5 py-2 rounded-xl bg-blue-600 text-white text-xs font-bold shadow-xs">
            Next Step
          </button>
        } @else {
          <button
            type="button"
            (click)="launchValidation()"
            class="px-6 py-2 rounded-xl bg-blue-600 text-white text-xs font-bold shadow-xs">
            Launch Validation
          </button>
        }
      </div>

    </div>
  `
})
export class NewValidationWizardComponent {
  public vs = inject(ValidationUiService);
  private router = inject(Router);

  public steps = [
    { step: 1, label: 'Definition' },
    { step: 2, label: 'Source' },
    { step: 3, label: 'Target' },
    { step: 4, label: 'Scope' },
    { step: 5, label: 'Config' },
    { step: 6, label: 'Review' }
  ];

  public nextStep(): void {
    if (this.vs.newValidationDraft().currentStep < 6) {
      this.vs.newValidationDraft().currentStep++;
    }
  }

  public prevStep(): void {
    if (this.vs.newValidationDraft().currentStep > 1) {
      this.vs.newValidationDraft().currentStep--;
    }
  }

  public launchValidation(): void {
    this.router.navigate(['/migration/validation', 'val-002']);
  }
}
