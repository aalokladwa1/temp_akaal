import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Step6ConfigurationStoreService } from '../../../../core/services/step6-configuration-store.service';
import { ConfigurationStandardComponent } from './configuration-standard.component';
import { ConfigurationAdvancedComponent } from './configuration-advanced.component';
import { ConfigurationActionsModalComponent } from './configuration-actions-modal.component';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-step6-configuration',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideIconComponent,
    ConfigurationStandardComponent,
    ConfigurationAdvancedComponent,
    ConfigurationActionsModalComponent
  ],
  template: `
    <div class="w-full flex flex-col gap-4 font-sans select-none animate-in fade-in duration-150 text-xs">
      
      <!-- ========================================================================= -->
      <!-- 0. PAGE INTRODUCTION & DEPTH SELECTOR                                     -->
      <!-- ========================================================================= -->
      <div class="flex flex-col gap-2.5 border-b border-slate-200/60 pb-3">
        
        <!-- Top Row: Title + Depth Selector Segmented Control -->
        <div class="flex items-center justify-between flex-wrap gap-3">
          <div class="flex flex-col gap-0.5">
            <h1 class="text-base font-bold text-slate-900 tracking-tight">Enterprise Configuration</h1>
            <p class="text-xs text-slate-500 font-normal">Configure how AKAAL should execute this migration.</p>
          </div>

          <!-- Configuration Depth Selector (GDS Segmented Control) -->
          <div class="flex items-center gap-2">
            <div class="p-0.5 bg-slate-100 border border-slate-200 rounded-lg flex items-center gap-0.5 select-none">
              <button
                type="button"
                (click)="store.setDepth('STANDARD')"
                class="px-3 py-1.5 rounded-md text-xs font-semibold cursor-pointer transition-colors flex items-center gap-1.5"
                [class.bg-white]="store.draft().depth === 'STANDARD'"
                [class.text-slate-900]="store.draft().depth === 'STANDARD'"
                [class.border]="store.draft().depth === 'STANDARD'"
                [class.border-slate-200]="store.draft().depth === 'STANDARD'"
                [class.text-slate-600]="store.draft().depth !== 'STANDARD'"
                [class.hover:text-slate-900]="store.draft().depth !== 'STANDARD'">
                <span>Standard</span>
                @if (store.isCustomized() && store.draft().depth === 'STANDARD') {
                  <span class="px-1.5 py-0.2 rounded text-[9px] font-bold bg-blue-100 text-blue-700">Customized</span>
                }
              </button>

              <button
                type="button"
                (click)="store.setDepth('ADVANCED')"
                class="px-3 py-1.5 rounded-md text-xs font-semibold cursor-pointer transition-colors flex items-center gap-1.5"
                [class.bg-white]="store.draft().depth === 'ADVANCED'"
                [class.text-slate-900]="store.draft().depth === 'ADVANCED'"
                [class.border]="store.draft().depth === 'ADVANCED'"
                [class.border-slate-200]="store.draft().depth === 'ADVANCED'"
                [class.text-slate-600]="store.draft().depth !== 'ADVANCED'"
                [class.hover:text-slate-900]="store.draft().depth !== 'ADVANCED'">
                <span>Advanced</span>
                @if (store.totalOverridesCount() > 0) {
                  <span class="px-1.5 py-0.2 rounded text-[9px] font-bold font-mono bg-blue-100 text-blue-700">
                    {{ store.totalOverridesCount() }}
                  </span>
                }
              </button>
            </div>
          </div>
        </div>

        <!-- Inherited Context Row (Zero Giant Cards, Low-Profile GDS Context Bar) -->
        <div class="flex items-center gap-2 text-[11px] text-slate-600 flex-wrap">
          <div class="flex items-center gap-1.5 font-semibold text-slate-800">
            <span>{{ store.sourceProvider() }}</span>
            <app-lucide-icon name="arrow-right" [size]="11" class="text-slate-400"></app-lucide-icon>
            <span>{{ store.targetProvider() }}</span>
          </div>

          <span class="text-slate-300 font-light">&middot;</span>
          <span class="font-medium text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.2 rounded">
            {{ store.modeDisplayTitle() }}
          </span>

          <span class="text-slate-300 font-light">&middot;</span>
          <div class="flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full" [class.bg-rose-500]="store.environment() === 'Production'" [class.bg-emerald-500]="store.environment() !== 'Production'"></span>
            <span class="font-medium text-slate-700">{{ store.environment() }}</span>
          </div>

          <span class="text-slate-300 font-light">&middot;</span>
          <span class="text-slate-500">{{ store.scopedObjectsCount() }} scoped objects</span>

          @if (store.isCustomized()) {
            <span class="text-slate-300 font-light">&middot;</span>
            <span class="text-blue-700 font-medium">
              {{ store.totalOverridesCount() }} advanced override{{ store.totalOverridesCount() > 1 ? 's' : '' }} active
            </span>
          }
        </div>

      </div>

      <!-- ========================================================================= -->
      <!-- 1. WORKSPACE VIEW SWITCHER                                                -->
      <!-- ========================================================================= -->
      @if (store.draft().depth === 'STANDARD') {
        <app-configuration-standard />
      } @else {
        <app-configuration-advanced />
      }

      <!-- ========================================================================= -->
      <!-- OVERLAYS & MODALS                                                         -->
      <!-- ========================================================================= -->

      <!-- 1. SWITCH FROM ADVANCED TO STANDARD OVERRIDE PROTECTION MODAL -->
      @if (store.showSwitchToStandardModal()) {
        <div
          role="dialog"
          aria-modal="true"
          class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 animate-in fade-in duration-100"
          (click)="store.cancelSwitchToStandard()">
          
          <div
            class="w-full max-w-md bg-white rounded-xl border border-slate-200 p-6 flex flex-col gap-4 animate-in zoom-in-95 duration-100"
            (click)="$event.stopPropagation()">
            
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-lg bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center shrink-0">
                <app-lucide-icon name="sliders-horizontal" [size]="18"></app-lucide-icon>
              </div>
              <div class="flex flex-col">
                <h3 class="text-sm font-bold text-slate-900">Switch to Standard configuration?</h3>
                <span class="text-xs text-slate-500 font-medium">{{ store.totalOverridesCount() }} advanced overrides are active</span>
              </div>
            </div>

            <p class="text-xs text-slate-600 leading-relaxed font-normal">
              You have customized parameters in Advanced mode. You can return to the Standard view while keeping your custom settings, or reset back to the standard profile preset.
            </p>

            <div class="flex flex-col gap-2 pt-2 border-t border-slate-200">
              <button
                type="button"
                (click)="store.keepOverridesAndSwitchToStandard()"
                class="w-full h-8 px-3 text-xs font-semibold rounded-md bg-blue-600 hover:bg-blue-700 text-white transition-colors cursor-pointer">
                Keep Overrides (Standard &middot; Customized)
              </button>

              <div class="flex items-center gap-2">
                <button
                  type="button"
                  (click)="store.cancelSwitchToStandard()"
                  class="flex-1 h-8 px-3 text-xs font-medium text-slate-700 border border-slate-200 rounded-md bg-white hover:bg-slate-50 transition-colors cursor-pointer">
                  Cancel
                </button>

                <button
                  type="button"
                  (click)="store.resetOverridesAndSwitchToStandard()"
                  class="flex-1 h-8 px-3 text-xs font-semibold text-rose-700 hover:bg-rose-50 border border-rose-200 rounded-md transition-colors cursor-pointer">
                  Reset to Standard
                </button>
              </div>
            </div>

          </div>
        </div>
      }

      <!-- 2. MATERIAL CHANGE PLAN INVALIDATION WARNING MODAL -->
      @if (store.pendingMaterialField(); as pending) {
        <div
          role="dialog"
          aria-modal="true"
          class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 animate-in fade-in duration-100"
          (click)="store.cancelMaterialChange()">
          
          <div
            class="w-full max-w-md bg-white rounded-xl border border-slate-200 p-6 flex flex-col gap-4 animate-in zoom-in-95 duration-100"
            (click)="$event.stopPropagation()">
            
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-lg bg-amber-50 border border-amber-200 text-amber-600 flex items-center justify-center shrink-0">
                <app-lucide-icon name="alert-triangle" [size]="18"></app-lucide-icon>
              </div>
              <div class="flex flex-col">
                <h3 class="text-sm font-bold text-slate-900">Change affects the execution plan</h3>
                <span class="text-xs text-slate-500 font-medium">Setting: {{ pending.field.label }}</span>
              </div>
            </div>

            <p class="text-xs text-slate-600 leading-relaxed font-normal">
              {{ pending.field.materialChangeWarning || 'Changing this setting requires the execution plan to be regenerated. Downstream readiness based on the previous plan may become stale.' }}
            </p>

            <div class="p-2.5 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between text-xs font-mono">
              <span class="text-slate-500">Current: <strong class="text-slate-800">{{ pending.field.effectiveValue }}{{ pending.field.unit ? ' ' + pending.field.unit : '' }}</strong></span>
              <span class="text-slate-400">&rarr;</span>
              <span class="text-blue-700 font-bold">New: {{ pending.pendingValue }}{{ pending.field.unit ? ' ' + pending.field.unit : '' }}</span>
            </div>

            <div class="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-200">
              <button
                type="button"
                (click)="store.cancelMaterialChange()"
                class="h-8 px-3 text-xs font-medium text-slate-700 border border-slate-200 rounded-md bg-white hover:bg-slate-50 transition-colors cursor-pointer">
                Cancel
              </button>

              <button
                type="button"
                (click)="store.confirmMaterialChange()"
                class="h-8 px-3.5 text-xs font-semibold rounded-md bg-blue-600 hover:bg-blue-700 text-white transition-colors cursor-pointer">
                Apply Change
              </button>
            </div>

          </div>
        </div>
      }

      <!-- 3. CUSTOM SQL ACTIONS MODAL -->
      @if (store.showCustomActionsModal()) {
        <app-configuration-actions-modal />
      }

    </div>
  `
})
export class Step6ConfigurationComponent {
  public store = inject(Step6ConfigurationStoreService);
}
