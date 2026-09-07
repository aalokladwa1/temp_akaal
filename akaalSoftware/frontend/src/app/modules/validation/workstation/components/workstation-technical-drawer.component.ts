import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationWorkstationService } from '../validation-workstation.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-workstation-technical-drawer',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    @if (store.drawerOpen()) {
      <!-- Backdrop -->
      <div
        (click)="store.toggleDrawer(false)"
        class="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-40 transition-opacity animate-in fade-in duration-200">
      </div>

      <!-- Slide-Over Drawer Container -->
      <aside class="fixed inset-y-0 right-0 w-full max-w-md bg-white border-l border-slate-200 shadow-xl z-50 flex flex-col justify-between animate-in slide-in-from-right duration-250 select-none">
        
        <!-- Drawer Header -->
        <div class="px-6 py-5 border-b border-slate-200 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <app-lucide-icon name="panel-left-close" [size]="18" class="text-blue-600" />
            <div class="flex flex-col">
              <h2 class="text-sm font-bold text-slate-900 font-heading">Technical Architecture</h2>
              <span class="text-[11px] text-slate-500">Engine placement, boundaries &amp; provenance</span>
            </div>
          </div>

          <button
            type="button"
            (click)="store.toggleDrawer(false)"
            class="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors cursor-pointer"
            title="Close drawer">
            <app-lucide-icon name="x-circle" [size]="18" />
          </button>
        </div>

        <!-- Drawer Content Scroll Area -->
        <div class="flex-1 overflow-y-auto p-6 flex flex-col gap-6 text-xs">
          
          <!-- Section 1: Canonical Identities -->
          <div class="flex flex-col gap-2.5">
            <h3 class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              Canonical Identity &amp; Bindings
            </h3>
            
            <div class="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-2 font-mono text-[11px]">
              <div class="flex items-center justify-between">
                <span class="text-slate-500 font-sans font-medium">Mission ID:</span>
                <span class="font-bold text-slate-900">{{ store.state().technicalDrawer.canonicalValidationId }}</span>
              </div>
              @if (store.state().technicalDrawer.draftId) {
                <div class="flex items-center justify-between">
                  <span class="text-slate-500 font-sans font-medium">Origin Draft:</span>
                  <span class="text-slate-700">{{ store.state().technicalDrawer.draftId }}</span>
                </div>
              }
              <div class="flex items-center justify-between">
                <span class="text-slate-500 font-sans font-medium">Environment:</span>
                <span class="text-slate-700">{{ store.state().environment }}</span>
              </div>
            </div>
          </div>

          <!-- Section 2: Engine Runtime & Placement -->
          <div class="flex flex-col gap-2.5">
            <h3 class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              Engine Runtime &amp; Resources
            </h3>
            
            <div class="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-2 text-xs">
              <div class="flex items-center justify-between">
                <span class="text-slate-500 font-medium">Placement:</span>
                <span class="font-semibold text-slate-800">{{ store.state().technicalDrawer.enginePlacement }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-slate-500 font-medium">Engine Daemon Version:</span>
                <span class="font-mono text-slate-800">{{ store.state().technicalDrawer.engineVersion }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-slate-500 font-medium">Memory Allocation:</span>
                <span class="font-mono text-slate-800">{{ store.state().technicalDrawer.maxMemoryLimit }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-slate-500 font-medium">Active Worker Pool:</span>
                <span class="font-mono text-slate-800">
                  {{ store.state().technicalDrawer.workerCount !== null ? store.state().technicalDrawer.workerCount + ' threads' : 'Unallocated' }}
                </span>
              </div>
            </div>
          </div>

          <!-- Section 3: Verified Capabilities -->
          <div class="flex flex-col gap-2.5">
            <h3 class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              Supported Engine Capabilities
            </h3>
            
            <div class="flex flex-col gap-1.5">
              @for (cap of store.state().technicalDrawer.capabilities; track cap) {
                <div class="px-3 py-2 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 flex items-center gap-2">
                  <app-lucide-icon name="check-circle" [size]="13" class="text-emerald-600 shrink-0" />
                  <span class="font-medium text-[11px]">{{ cap }}</span>
                </div>
              }
            </div>
          </div>

          <!-- Section 4: Cryptographic Evidence Provenance -->
          <div class="flex flex-col gap-2.5">
            <h3 class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              Evidence Provenance &amp; Sealing
            </h3>
            
            <div class="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-2 font-mono text-[11px]">
              <div class="flex flex-col gap-0.5">
                <span class="text-slate-500 font-sans font-medium">Evidence SHA-256:</span>
                @if (store.state().technicalDrawer.evidenceHash) {
                  <span class="text-slate-900 break-all bg-white p-1.5 rounded border border-slate-200">
                    {{ store.state().technicalDrawer.evidenceHash }}
                  </span>
                } @else {
                  <span class="text-slate-400 font-sans">Evidence bundle unsealed</span>
                }
              </div>

              @if (store.state().technicalDrawer.signingKeyId) {
                <div class="flex items-center justify-between pt-1">
                  <span class="text-slate-500 font-sans font-medium">Signing Key:</span>
                  <span class="text-slate-800">{{ store.state().technicalDrawer.signingKeyId }}</span>
                </div>
              }

              @if (store.state().technicalDrawer.evidenceUri) {
                <div class="flex flex-col gap-0.5 pt-1">
                  <span class="text-slate-500 font-sans font-medium">Storage URI:</span>
                  <span class="text-slate-700 break-all text-[10px]">{{ store.state().technicalDrawer.evidenceUri }}</span>
                </div>
              }
            </div>
          </div>

        </div>

        <!-- Drawer Footer -->
        <div class="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
          <span class="text-[11px] text-slate-500">M8 Immutable Verification Spec</span>
          <button
            type="button"
            (click)="store.toggleDrawer(false)"
            class="px-3.5 py-1.5 rounded-lg bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 text-xs font-semibold cursor-pointer transition-colors">
            Dismiss
          </button>
        </div>

      </aside>
    }
  `
})
export class WorkstationTechnicalDrawerComponent {
  readonly store = inject(ValidationWorkstationService);
}
