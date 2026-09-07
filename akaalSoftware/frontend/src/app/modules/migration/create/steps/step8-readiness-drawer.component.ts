import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { Step8GovernanceStoreService } from '../../../../core/services/step8-governance-store.service';
import { ReadinessCheckPresentation } from './step8-governance.models';

@Component({
  selector: 'app-step8-readiness-drawer',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <!-- Overlay Backdrop (zero blur) -->
    <div
      class="fixed inset-0 z-40 bg-slate-900/40 animate-in fade-in duration-100"
      (click)="store.closeReadinessDrawer()">
    </div>

    <!-- Slide-over Drawer Surface (Right-aligned, w-[520px], flat border) -->
    <aside
      role="dialog"
      aria-modal="true"
      aria-label="Technical Readiness Check Inspector"
      class="fixed right-0 top-0 bottom-0 z-50 w-[520px] bg-white border-l border-slate-200 flex flex-col justify-between font-sans text-xs select-none animate-in slide-in-from-right duration-150"
      (click)="$event.stopPropagation()">
      
      <!-- Drawer Header -->
      <header class="p-4 border-b border-slate-200 flex items-start justify-between gap-3 bg-slate-50 shrink-0">
        <div class="flex flex-col gap-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="font-bold text-slate-900 text-sm truncate">{{ check()?.name }}</span>
            <span class="px-1.5 py-0.5 rounded text-[10px] font-bold border shrink-0"
              [class.bg-emerald-50]="check()?.status === 'READY'"
              [class.text-emerald-700]="check()?.status === 'READY'"
              [class.border-emerald-200]="check()?.status === 'READY'"
              [class.bg-amber-50]="check()?.status === 'WARNING'"
              [class.text-amber-800]="check()?.status === 'WARNING'"
              [class.border-amber-200]="check()?.status === 'WARNING'"
              [class.bg-rose-50]="check()?.status === 'BLOCKED'"
              [class.text-rose-700]="check()?.status === 'BLOCKED'"
              [class.border-rose-200]="check()?.status === 'BLOCKED'">
              {{ check()?.status === 'READY' ? 'Check Passed' : (check()?.status === 'WARNING' ? 'Warning' : 'Blocked') }}
            </span>
          </div>
          <span class="text-[11px] text-slate-500 font-mono">Category: {{ formatCategory(check()?.category) }}</span>
        </div>

        <button
          type="button"
          (click)="store.closeReadinessDrawer()"
          class="w-7 h-7 rounded border border-slate-200 bg-white hover:bg-slate-100 text-slate-500 hover:text-slate-900 flex items-center justify-center cursor-pointer transition-colors shrink-0"
          title="Close drawer">
          <app-lucide-icon name="x" [size]="14"></app-lucide-icon>
        </button>
      </header>

      <!-- Drawer Scrollable Body -->
      <div class="p-5 flex-1 overflow-y-auto flex flex-col gap-4">
        
        <!-- 1. Observation & Technical Impact -->
        <div class="bg-white border border-slate-200 rounded-lg p-3 flex flex-col gap-2">
          <span class="text-[11px] font-bold uppercase tracking-wider text-slate-500">Diagnostic Observation</span>
          <p class="text-xs text-slate-900 m-0 leading-relaxed font-medium">{{ check()?.observation }}</p>
          
          <div class="pt-2 border-t border-slate-100 flex flex-col gap-1 text-[11.5px]">
            <span class="text-slate-500 font-medium">Technical Impact:</span>
            <p class="text-slate-700 m-0 leading-normal">{{ check()?.impact }}</p>
          </div>
        </div>

        <!-- 2. Affected Resources -->
        <div class="flex flex-col gap-1.5">
          <span class="text-[11px] font-bold uppercase tracking-wider text-slate-500">Affected Resources</span>
          <div class="bg-slate-50 border border-slate-200 rounded-lg p-3 flex flex-col gap-1 text-[11px]">
            @for (res of check()?.affectedResources || []; track res) {
              <div class="flex items-center gap-2 text-slate-700">
                <app-lucide-icon name="database" [size]="13" class="text-slate-400 shrink-0"></app-lucide-icon>
                <span class="font-mono font-medium">{{ res }}</span>
              </div>
            }
          </div>
        </div>

        <!-- 3. Remediation Guidance & Upstream Routing -->
        @if (check()?.remediationGuidance) {
          <div class="bg-blue-50 border border-blue-200 rounded-lg p-3.5 flex flex-col gap-2">
            <div class="flex items-center gap-2 text-blue-900 font-bold text-xs">
              <app-lucide-icon name="info" [size]="14" class="text-blue-600 shrink-0"></app-lucide-icon>
              <span>Remediation Guidance</span>
            </div>
            <p class="text-xs text-blue-800 m-0 leading-relaxed">{{ check()?.remediationGuidance }}</p>

            @if (check()?.upstreamStepOwner) {
              <div class="pt-2 border-t border-blue-200/60 flex items-center justify-between">
                <span class="text-[11px] text-blue-700 font-medium">Upstream Configuration Owner:</span>
                <button
                  type="button"
                  (click)="handleUpstreamRouting()"
                  class="h-7 px-2.5 rounded bg-white border border-blue-300 hover:bg-blue-100 text-blue-800 text-[11px] font-bold flex items-center gap-1 cursor-pointer transition-colors">
                  <span>{{ check()?.upstreamStepLabel || 'Review in Step ' + check()?.upstreamStepOwner }}</span>
                  <app-lucide-icon name="arrow-right" [size]="11"></app-lucide-icon>
                </button>
              </div>
            }
          </div>
        }

        <!-- 4. Secondary Progressive Disclosure: Diagnostic Logs -->
        @if (check()?.diagnosticDetails) {
          <div class="flex flex-col gap-1.5">
            <button
              type="button"
              (click)="toggleDiagnostics()"
              class="text-[11px] font-bold text-slate-600 hover:text-slate-900 flex items-center justify-between py-1 cursor-pointer select-none">
              <span class="uppercase tracking-wider">Technical Diagnostic Output</span>
              <div class="flex items-center gap-1 text-slate-400">
                <span>{{ showDiagnostics() ? 'Hide' : 'Show Details' }}</span>
                <app-lucide-icon [name]="showDiagnostics() ? 'chevron-up' : 'chevron-down'" [size]="13"></app-lucide-icon>
              </div>
            </button>

            @if (showDiagnostics()) {
              <div class="bg-slate-100 border border-slate-200 rounded-lg p-3 font-mono text-[11px] text-slate-800 flex flex-col gap-1.5 overflow-x-auto leading-relaxed animate-in fade-in duration-100">
                <div class="flex items-center justify-between text-slate-500 text-[10px] border-b border-slate-200 pb-1">
                  <span>PROBE_CODE: {{ check()?.diagnosticDetails?.probeResultCode }}</span>
                  <span>DURATION: {{ check()?.diagnosticDetails?.executionDurationMs }}ms</span>
                </div>
                <pre class="m-0 whitespace-pre-wrap font-mono">{{ check()?.diagnosticDetails?.sanitizedDiagnosticText }}</pre>
              </div>
            }
          </div>
        }

      </div>

      <!-- Drawer Footer Actions -->
      <footer class="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between gap-3 shrink-0">
        <button
          type="button"
          (click)="store.closeReadinessDrawer()"
          class="h-8 px-3 text-xs font-medium text-slate-700 border border-slate-200 rounded-md bg-white hover:bg-slate-100 transition-colors cursor-pointer">
          Close
        </button>

        <button
          type="button"
          (click)="handleRetry()"
          [disabled]="store.isRetryingCheck()"
          class="h-8 px-3.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-1.5">
          <app-lucide-icon [name]="store.isRetryingCheck() ? 'loader-2' : 'refresh-cw'" [size]="13" [class.animate-spin]="store.isRetryingCheck()"></app-lucide-icon>
          <span>{{ store.isRetryingCheck() ? 'Re-evaluating...' : 'Re-evaluate Check' }}</span>
        </button>
      </footer>

    </aside>
  `
})
export class Step8ReadinessDrawerComponent {
  public store = inject(Step8GovernanceStoreService);
  public showDiagnostics = signal<boolean>(false);

  public check(): ReadinessCheckPresentation | null {
    return this.store.selectedReadinessCheck();
  }

  public toggleDiagnostics(): void {
    this.showDiagnostics.update(v => !v);
  }

  public formatCategory(category?: string): string {
    switch (category) {
      case 'CONNECTIONS_ACCESS': return 'Connections & Access';
      case 'SCHEMA_COMPATIBILITY': return 'Schema & Compatibility';
      case 'CHANGE_CAPTURE': return 'Change Capture';
      case 'CAPACITY_RESOURCES': return 'Capacity & Resources';
      case 'EXECUTION_REQUIREMENTS': return 'Execution Requirements';
      case 'VALIDATION_REQUIREMENTS': return 'Validation Requirements';
      default: return category || 'Technical Check';
    }
  }

  public handleUpstreamRouting(): void {
    const c = this.check();
    if (c?.upstreamStepOwner) {
      this.store.closeReadinessDrawer();
      this.store.routeToUpstreamStep(c.upstreamStepOwner);
    }
  }

  public handleRetry(): void {
    const c = this.check();
    if (c) {
      this.store.retryCheck(c.id);
    }
  }
}
