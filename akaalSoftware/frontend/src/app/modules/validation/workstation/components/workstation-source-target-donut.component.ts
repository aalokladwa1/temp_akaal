import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationWorkstationService } from '../validation-workstation.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { DonutViewModel, DonutSemanticMode } from '../validation-workstation.models';

@Component({
  selector: 'app-workstation-source-target-donut',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-6">
      
      <!-- Panel Header -->
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <div class="flex items-center gap-2">
          <app-lucide-icon name="arrow-left-right" [size]="16" class="text-blue-600" />
          <h2 class="text-sm font-bold text-slate-900 tracking-tight font-heading">
            Source &harr; Target Topology &amp; Comparison Progress
          </h2>
        </div>

        <!-- Mode Semantic Clarification Badge -->
        <div class="flex items-center gap-2">
          <span class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Semantic Mode:</span>
          <span [ngClass]="getSemanticModeBadgeClasses()"
                class="px-2.5 py-0.5 rounded text-[11px] font-bold border">
            {{ getSemanticModeLabel() }}
          </span>
        </div>
      </div>

      <!-- 3-Column Hero Layout: Source Card | SVG Donut | Target Card -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
        
        <!-- Left: Source Endpoint Card (Cols 4) -->
        <div class="lg:col-span-4 p-5 rounded-xl bg-slate-50/70 border border-slate-200/80 flex flex-col gap-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="w-8 h-8 rounded-lg bg-blue-100/70 border border-blue-200 flex items-center justify-center">
                <app-lucide-icon name="database" [size]="16" class="text-blue-700" />
              </div>
              <div class="flex flex-col">
                <span class="text-[10px] font-bold text-blue-700 uppercase tracking-wider">Source Endpoint</span>
                <span class="text-sm font-bold text-slate-900">{{ donut().sourceLabel }}</span>
              </div>
            </div>
            <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-white text-slate-600 border border-slate-200">
              Origin
            </span>
          </div>

          <div class="flex flex-col gap-2 pt-2 border-t border-slate-200/60 text-xs">
            <div class="flex items-center justify-between">
              <span class="text-slate-500 font-medium">Connection:</span>
              <span class="font-mono text-slate-800 text-[11px] truncate max-w-[200px]" [title]="donut().sourceHost">
                {{ donut().sourceHost }}
              </span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-slate-500 font-medium">In-Scope Objects:</span>
              @if (donut().sourceObjectCount !== null) {
                <span class="font-mono font-bold text-slate-900">{{ donut().sourceObjectCount }} tables / views</span>
              } @else {
                <span class="font-mono text-slate-400 text-xs">Pending engine link</span>
              }
            </div>
          </div>
        </div>

        <!-- Center: Pure SVG Donut Visualization (Cols 4) -->
        <div class="lg:col-span-4 flex flex-col items-center justify-center py-2"
             role="region"
             [attr.aria-label]="getAriaLabel()">
          <div class="relative w-48 h-48 flex items-center justify-center">
            
            <!-- SVG Donut Chart (viewBox 0 0 160 160) -->
            <svg class="w-full h-full -rotate-90 transform" viewBox="0 0 160 160" aria-hidden="true">
              
              <!-- Background Neutral Track -->
              <circle
                cx="80"
                cy="80"
                r="62"
                fill="transparent"
                stroke="#e2e8f0"
                stroke-width="12" />

              <!-- Active Progress Arc -->
              @if (donut().centerPercentage !== null) {
                <circle
                  cx="80"
                  cy="80"
                  r="62"
                  fill="transparent"
                  [attr.stroke]="getProgressStrokeColor()"
                  stroke-width="12"
                  stroke-linecap="round"
                  [attr.stroke-dasharray]="circumference"
                  [attr.stroke-dashoffset]="dashOffset()"
                  class="transition-all duration-700 ease-out" />
              }
            </svg>

            <!-- Center Content (Accessible and Visual) -->
            <div class="absolute inset-0 flex flex-col items-center justify-center text-center px-4 pointer-events-none">
              
              <!-- Completed State: Display Canonical SYNC or ASYNC if specified -->
              @if (isCompletedState()) {
                @if (donut().canonicalComparisonMode === 'SYNC') {
                  <span class="text-3xl font-black font-mono tracking-wider text-slate-900">
                    SYNC
                  </span>
                  <span class="text-xs font-bold text-slate-700 mt-0.5">
                    Canonical Sync Mode
                  </span>
                  <span class="text-[10px] font-medium text-slate-500 mt-0.5">
                    {{ donut().centerSubtext || 'Comparison Complete' }}
                  </span>
                } @else if (donut().canonicalComparisonMode === 'ASYNC') {
                  <span class="text-3xl font-black font-mono tracking-wider text-slate-900">
                    ASYNC
                  </span>
                  <span class="text-xs font-bold text-slate-700 mt-0.5">
                    Canonical Async Mode
                  </span>
                  <span class="text-[10px] font-medium text-slate-500 mt-0.5">
                    {{ donut().centerSubtext || 'Comparison Complete' }}
                  </span>
                } @else {
                  <!-- Completed but mode unspecified: do not guess SYNC/ASYNC -->
                  <span class="text-3xl font-black font-mono tracking-tight text-slate-900">
                    100%
                  </span>
                  <span class="text-xs font-bold text-slate-700 mt-0.5">
                    Comparison Complete
                  </span>
                  <span class="text-[10px] font-medium text-slate-400 mt-0.5">
                    Mode Unspecified
                  </span>
                }
              } @else if (donut().centerPercentage !== null) {
                <!-- Running / Partial Execution State -->
                <span class="text-3xl font-black font-mono tracking-tight text-slate-900">
                  {{ donut().centerPercentage }}%
                </span>
                <span class="text-xs font-bold text-slate-700 mt-0.5">
                  {{ donut().centerLabel }}
                </span>
                <span class="text-[10px] font-medium text-slate-500 mt-0.5">
                  {{ donut().centerSubtext }}
                </span>
              } @else {
                <!-- Not Connected / Standby Default State -->
                <span class="text-2xl font-bold font-mono text-slate-400">
                  &mdash;
                </span>
                <span class="text-xs font-bold text-slate-600 mt-1">
                  {{ donut().centerLabel }}
                </span>
                <span class="text-[10px] font-medium text-slate-400 mt-0.5">
                  {{ donut().centerSubtext }}
                </span>
              }

            </div>
          </div>

          <!-- Explanatory Caption -->
          <div class="text-center mt-2">
            @if (donut().mode === 'NOT_CONNECTED') {
              <p class="text-[11px] text-slate-500 max-w-[280px]">
                Truthful state: Comparison metric is not calculated until validation daemon connects.
              </p>
            } @else if (isCompletedState()) {
              <p class="text-[11px] text-slate-600 max-w-[280px]">
                @if (donut().canonicalComparisonMode === 'SYNC') {
                  Synchronous verification: Canonical CDC / synchronous replication pipeline boundary.
                } @else if (donut().canonicalComparisonMode === 'ASYNC') {
                  Asynchronous verification: Point-in-time snapshot / decoupled downstream pipeline.
                } @else {
                  Comparison complete across evaluated scope. Relationship mode unspecified.
                }
              </p>
            } @else if (donut().mode === 'INDEPENDENT_VALIDATION') {
              <p class="text-[11px] text-slate-600 max-w-[280px]">
                Independent validation coverage: Metric represents percentage of scope evaluated.
              </p>
            } @else {
              <p class="text-[11px] text-slate-600 max-w-[280px]">
                Migration sync parity: Metric derived from canonical CDC pipeline replication stream.
              </p>
            }
          </div>
        </div>

        <!-- Right: Target Endpoint Card (Cols 4) -->
        <div class="lg:col-span-4 p-5 rounded-xl bg-slate-50/70 border border-slate-200/80 flex flex-col gap-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="w-8 h-8 rounded-lg bg-emerald-100/70 border border-emerald-200 flex items-center justify-center">
                <app-lucide-icon name="database" [size]="16" class="text-emerald-700" />
              </div>
              <div class="flex flex-col">
                <span class="text-[10px] font-bold text-emerald-700 uppercase tracking-wider">Target Endpoint</span>
                <span class="text-sm font-bold text-slate-900">{{ donut().targetLabel }}</span>
              </div>
            </div>
            <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-white text-slate-600 border border-slate-200">
              Destination
            </span>
          </div>

          <div class="flex flex-col gap-2 pt-2 border-t border-slate-200/60 text-xs">
            <div class="flex items-center justify-between">
              <span class="text-slate-500 font-medium">Connection:</span>
              <span class="font-mono text-slate-800 text-[11px] truncate max-w-[200px]" [title]="donut().targetHost">
                {{ donut().targetHost }}
              </span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-slate-500 font-medium">In-Scope Objects:</span>
              @if (donut().targetObjectCount !== null) {
                <span class="font-mono font-bold text-slate-900">{{ donut().targetObjectCount }} tables / views</span>
              } @else {
                <span class="font-mono text-slate-400 text-xs">Pending engine link</span>
              }
            </div>
          </div>
        </div>

      </div>
    </section>
  `
})
export class WorkstationSourceTargetDonutComponent {
  readonly store = inject(ValidationWorkstationService);

  readonly donut = computed(() => this.store.state().donut);

  readonly radius = 62;
  readonly circumference = 2 * Math.PI * this.radius; // ~389.56

  readonly dashOffset = computed(() => {
    const pct = this.donut().centerPercentage;
    if (pct === null || pct === undefined) {
      return this.circumference;
    }
    const clamped = Math.max(0, Math.min(100, pct));
    return this.circumference * (1 - clamped / 100);
  });

  isCompletedState(): boolean {
    return this.store.executionState() === 'COMPLETED';
  }

  getProgressStrokeColor(): string {
    const verdict = this.store.verdict();
    if (verdict === 'FAILED') return '#e11d48'; // rose-600
    if (verdict === 'PASSED') return '#10b981'; // emerald-500
    return '#2563eb'; // blue-600 default running
  }

  getSemanticModeLabel(): string {
    if (this.isCompletedState()) {
      const mode = this.donut().canonicalComparisonMode;
      if (mode === 'SYNC') return 'Canonical SYNC Relationship';
      if (mode === 'ASYNC') return 'Canonical ASYNC Relationship';
      return 'Relationship Mode Unspecified';
    }

    switch (this.donut().mode) {
      case 'NOT_CONNECTED': return 'Standby (Not Connected)';
      case 'INDEPENDENT_VALIDATION': return 'Independent Validation Coverage';
      case 'MIGRATION_SYNC': return 'Migration Sync Parity';
    }
  }

  getSemanticModeBadgeClasses(): string {
    if (this.isCompletedState()) {
      const mode = this.donut().canonicalComparisonMode;
      if (mode === 'SYNC') return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      if (mode === 'ASYNC') return 'bg-blue-50 text-blue-700 border-blue-200';
      return 'bg-slate-100 text-slate-600 border-slate-200';
    }

    switch (this.donut().mode) {
      case 'NOT_CONNECTED': return 'bg-slate-100 text-slate-600 border-slate-200';
      case 'INDEPENDENT_VALIDATION': return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'MIGRATION_SYNC': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    }
  }

  getAriaLabel(): string {
    const d = this.donut();
    const state = this.store.executionState();
    const verdict = this.store.verdict();
    let text = `Source endpoint: ${d.sourceLabel} to Target endpoint: ${d.targetLabel}. `;
    if (state === 'NOT_CONNECTED') {
      text += 'Comparison state unavailable. Engine link pending.';
    } else if (state === 'COMPLETED') {
      text += `Comparison complete. Mode: ${d.canonicalComparisonMode || 'Unspecified'}. Verdict: ${verdict}.`;
    } else {
      text += `Evaluation in progress: ${d.centerPercentage || 0}% scope evaluated.`;
    }
    return text;
  }
}
