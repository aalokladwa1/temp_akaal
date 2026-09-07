import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationResultsService } from '../validation-results.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-results-technical-drawer',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    @if (store.isTechnicalDrawerOpen()) {
      <!-- Backdrop -->
      <div
        (click)="store.toggleTechnicalDrawer(false)"
        class="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-50 transition-opacity animate-in fade-in duration-200">
      </div>

      <!-- Slide-over Drawer Panel -->
      <aside
        class="fixed top-0 right-0 bottom-0 w-full max-w-xl bg-white z-50 shadow-2xl border-l border-slate-200 flex flex-col animate-in slide-in-from-right duration-200 text-slate-800">
        
        <!-- Drawer Header -->
        <div class="px-6 py-5 border-b border-slate-200 flex items-center justify-between bg-slate-50/80 shrink-0">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
              <app-lucide-icon name="layers" [size]="16" />
            </div>
            <div>
              <h3 class="text-sm font-bold text-slate-900 font-heading">
                Technical Provenance &amp; Engine Details
              </h3>
              <p class="text-[11px] text-slate-500">
                P7B execution metadata, content digest, and cluster placement
              </p>
            </div>
          </div>

          <button
            type="button"
            (click)="store.toggleTechnicalDrawer(false)"
            class="w-8 h-8 rounded-lg hover:bg-slate-200/80 flex items-center justify-center text-slate-500 hover:text-slate-900 transition-colors cursor-pointer">
            <app-lucide-icon name="x" [size]="16" />
          </button>
        </div>

        <!-- Drawer Scrollable Body -->
        <div class="flex-1 overflow-y-auto p-6 space-y-6">
          
          <!-- Section 1: Canonical Mission Identity -->
          <div class="flex flex-col gap-2">
            <span class="text-xs font-bold text-slate-900 font-heading uppercase tracking-wider text-[11px]">
              Mission Identity &amp; Execution Plan
            </span>
            <div class="p-4 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col gap-2.5 text-xs">
              
              <div class="flex items-center justify-between">
                <span class="text-slate-500 font-sans">Validation ID:</span>
                <span class="font-mono text-[11px] font-bold text-slate-900 break-all select-all">
                  {{ store.technicalDetails().canonicalValidationId }}
                </span>
              </div>

              @if (store.technicalDetails().planId) {
                <div class="flex items-center justify-between border-t border-slate-200/60 pt-2">
                  <span class="text-slate-500 font-sans">Execution Plan:</span>
                  <span class="font-mono text-[11px] text-slate-800">
                    {{ store.technicalDetails().planId }}
                  </span>
                </div>
              }

              @if (store.technicalDetails().planFingerprint) {
                <div class="flex items-center justify-between border-t border-slate-200/60 pt-2">
                  <span class="text-slate-500 font-sans">Plan Fingerprint:</span>
                  <span class="font-mono text-[11px] text-slate-800">
                    {{ store.technicalDetails().planFingerprint }}
                  </span>
                </div>
              }

            </div>
          </div>

          <!-- Section 2: Engine & Compute Placement -->
          <div class="flex flex-col gap-2">
            <span class="text-xs font-bold text-slate-900 font-heading uppercase tracking-wider text-[11px]">
              Engine &amp; Placement Fabric
            </span>
            <div class="p-4 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col gap-2.5 text-xs">
              
              <div class="flex items-center justify-between">
                <span class="text-slate-500 font-sans">Engine Version:</span>
                <span class="font-mono text-[11px] text-slate-800 font-semibold">
                  {{ store.technicalDetails().engineVersion || 'v2.4.0-standalone' }}
                </span>
              </div>

              <div class="flex items-center justify-between border-t border-slate-200/60 pt-2">
                <span class="text-slate-500 font-sans">Placement Fabric:</span>
                <span class="font-sans text-slate-800 font-medium truncate max-w-[280px]">
                  {{ store.technicalDetails().enginePlacement || 'Fabric Standby' }}
                </span>
              </div>

              @if (store.technicalDetails().workerCount !== undefined && store.technicalDetails().workerCount !== null) {
                <div class="flex items-center justify-between border-t border-slate-200/60 pt-2">
                  <span class="text-slate-500 font-sans">Dedicated Workers:</span>
                  <span class="font-mono text-slate-900 font-bold">
                    {{ store.technicalDetails().workerCount }} workers
                  </span>
                </div>
              }

            </div>
          </div>

          <!-- Section 3: P7B Fabric Provenance (Directive #15) -->
          @if (store.technicalDetails().p7bFabric; as p7b) {
            <div class="flex flex-col gap-2">
              <span class="text-xs font-bold text-slate-900 font-heading uppercase tracking-wider text-[11px]">
                P7B Execution Provenance
              </span>
              <div class="p-4 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col gap-2.5 text-xs">
                
                @if (p7b.site) {
                  <div class="flex items-center justify-between">
                    <span class="text-slate-500 font-sans">Site / DC:</span>
                    <span class="font-mono text-slate-800 font-semibold">{{ p7b.site }}</span>
                  </div>
                }

                @if (p7b.region) {
                  <div class="flex items-center justify-between border-t border-slate-200/60 pt-2">
                    <span class="text-slate-500 font-sans">Cloud / Region:</span>
                    <span class="font-mono text-slate-800">{{ p7b.region }}</span>
                  </div>
                }

                @if (p7b.placementNode) {
                  <div class="flex items-center justify-between border-t border-slate-200/60 pt-2">
                    <span class="text-slate-500 font-sans">Placement Node:</span>
                    <span class="font-mono text-slate-800">{{ p7b.placementNode }}</span>
                  </div>
                }

                @if (p7b.failoverReady !== undefined) {
                  <div class="flex items-center justify-between border-t border-slate-200/60 pt-2">
                    <span class="text-slate-500 font-sans">Failover Ready:</span>
                    <span class="font-semibold text-emerald-700 font-mono text-[11px]">
                      {{ p7b.failoverReady ? 'YES' : 'NO' }}
                    </span>
                  </div>
                }

              </div>
            </div>
          }

          <!-- Section 4: Content Integrity & Storage Reference -->
          <div class="flex flex-col gap-2">
            <span class="text-xs font-bold text-slate-900 font-heading uppercase tracking-wider text-[11px]">
              Content Integrity &amp; Checkpoint
            </span>
            <div class="p-4 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col gap-3 text-xs">
              
              @if (store.technicalDetails().contentDigest) {
                <div class="flex flex-col gap-1.5">
                  <span class="text-slate-500 font-sans">Content Digest (SHA-256):</span>
                  <div class="p-2.5 bg-white border border-slate-200 rounded-lg font-mono text-[11px] text-slate-800 break-all select-all leading-relaxed">
                    {{ store.technicalDetails().contentDigest }}
                  </div>
                </div>
              }

              @if (store.technicalDetails().checkpointReference) {
                <div class="flex items-center justify-between border-t border-slate-200/60 pt-2">
                  <span class="text-slate-500 font-sans">Checkpoint Ref:</span>
                  <span class="font-mono text-[11px] text-slate-800">
                    {{ store.technicalDetails().checkpointReference }}
                  </span>
                </div>
              }

              @if (store.technicalDetails().storageLocation) {
                <div class="flex flex-col gap-1 border-t border-slate-200/60 pt-2">
                  <span class="text-slate-500 font-sans">Storage Reference:</span>
                  <span class="font-mono text-[11px] text-slate-700 break-all">
                    {{ store.technicalDetails().storageLocation }}
                  </span>
                </div>
              }

            </div>
          </div>

        </div>

        <!-- Drawer Footer -->
        <div class="p-4 border-t border-slate-200 bg-slate-50/80 flex items-center justify-end shrink-0">
          <button
            type="button"
            (click)="store.toggleTechnicalDrawer(false)"
            class="h-9 px-4 rounded-lg bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 text-xs font-semibold cursor-pointer transition-colors shadow-2xs">
            Close
          </button>
        </div>

      </aside>
    }
  `
})
export class ResultsTechnicalDrawerComponent {
  readonly store = inject(ValidationResultsService);
}
