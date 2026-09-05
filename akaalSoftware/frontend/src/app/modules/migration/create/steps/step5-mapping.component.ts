import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Step5MappingStoreService } from '../../../../core/services/step5-mapping-store.service';
import { MigrationUiService } from '../../../../core/services/migration-ui.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { MappingOverviewComponent } from './mapping-overview.component';
import { MappingStructureComponent } from './mapping-structure.component';
import { MappingFieldsComponent } from './mapping-fields.component';
import { MappingControlsComponent } from './mapping-controls.component';
import { TranspilerWorkspaceComponent } from './transpiler-workspace.component';

@Component({
  selector: 'app-step5-mapping',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideIconComponent,
    MappingOverviewComponent,
    MappingStructureComponent,
    MappingFieldsComponent,
    MappingControlsComponent,
    TranspilerWorkspaceComponent
  ],
  host: {
    class: 'flex flex-1 flex-col w-full h-full min-h-0'
  },
  template: `
    <div class="w-full h-full flex flex-col gap-3 min-h-0 font-sans text-xs select-none relative">
      
      <!-- ========================================================================= -->
      <!-- ROW 1: TOP CONTEXT LINE & MASTER WORKSPACE SWITCHER                       -->
      <!-- ========================================================================= -->
      <header class="h-11 px-4 bg-white border border-slate-200 rounded-lg flex items-center justify-between shrink-0">
        
        <!-- Left: Context Line (Source -> Target, Mode, Scoped Counts) -->
        <div class="flex items-center gap-2.5 min-w-0">
          <div class="flex items-center gap-1.5 font-bold text-slate-900 text-xs">
            <span class="truncate">{{ ms.wizardDraft().sourceProvider }}</span>
            <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
            <span class="truncate">{{ ms.wizardDraft().targetProvider }}</span>
          </div>

          <span class="h-3.5 w-[1px] bg-slate-300 shrink-0"></span>

          <!-- Migration Mode Tag -->
          <span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-50 border border-slate-200 text-slate-700 shrink-0 font-semibold uppercase">
            {{ ms.wizardDraft().mode }}
          </span>

          <span class="h-3.5 w-[1px] bg-slate-300 shrink-0"></span>

          <!-- Object Count Summary -->
          <span class="text-xs text-slate-500 font-medium shrink-0">
            {{ store.objects().length }} scoped object{{ store.objects().length === 1 ? '' : 's' }}
          </span>

          <!-- Controls Active Chip -->
          @if (hasActiveDataControls()) {
            <span class="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-blue-50 border border-blue-200 text-blue-700 font-semibold shrink-0">
              <app-lucide-icon name="shield" [size]="10"></app-lucide-icon>
              <span>Data Controls Active</span>
            </span>
          }
        </div>

        <!-- Right: Master Workspace Segmented Control: [ Mapping Studio ] vs [ Transpiler Studio ] -->
        <div class="flex items-center gap-2 shrink-0">
          <div class="flex items-center rounded-lg border border-slate-200 bg-slate-100 p-0.5">
            <button
              type="button"
              (click)="store.setWorkspace('MAPPING')"
              class="h-7 px-3 rounded-md text-xs font-semibold transition-colors cursor-pointer flex items-center gap-1.5 hover:bg-blue-50 hover:text-blue-700"
              [class.bg-white]="store.activeWorkspace() === 'MAPPING'"
              [class.text-blue-700]="store.activeWorkspace() === 'MAPPING'"
              [class.border]="store.activeWorkspace() === 'MAPPING'"
              [class.border-slate-200]="store.activeWorkspace() === 'MAPPING'"
              [class.text-slate-600]="store.activeWorkspace() !== 'MAPPING'">
              <app-lucide-icon name="layers" [size]="12"></app-lucide-icon>
              <span>Mapping Studio</span>
            </button>

            <button
              type="button"
              (click)="store.setWorkspace('TRANSPILER')"
              [disabled]="!store.isTranspilerApplicable()"
              class="h-7 px-3 rounded-md text-xs font-semibold transition-colors cursor-pointer flex items-center gap-1.5 disabled:opacity-40 disabled:pointer-events-none hover:bg-blue-50 hover:text-blue-700"
              [class.bg-white]="store.activeWorkspace() === 'TRANSPILER'"
              [class.text-blue-700]="store.activeWorkspace() === 'TRANSPILER'"
              [class.border]="store.activeWorkspace() === 'TRANSPILER'"
              [class.border-slate-200]="store.activeWorkspace() === 'TRANSPILER'"
              [class.text-slate-600]="store.activeWorkspace() !== 'TRANSPILER'"
              [title]="store.transpilerDisabledReason() || 'Open Procedural Transpilation Studio'">
              <app-lucide-icon name="code-2" [size]="12"></app-lucide-icon>
              <span>Transpiler Studio</span>
              @if (store.isTranspilerApplicable() && store.codeObjects().length > 0) {
                <span class="text-[10px] px-1.5 py-0.2 rounded font-bold"
                  [class.bg-blue-100]="store.activeWorkspace() === 'TRANSPILER'"
                  [class.text-blue-800]="store.activeWorkspace() === 'TRANSPILER'"
                  [class.bg-slate-200]="store.activeWorkspace() !== 'TRANSPILER'"
                  [class.text-slate-600]="store.activeWorkspace() !== 'TRANSPILER'">
                  {{ store.codeObjects().length }}
                </span>
              }
            </button>
          </div>
        </div>

      </header>

      <!-- ========================================================================= -->
      <!-- ROW 2: MAPPING STUDIO SECONDARY TAB STRIP (ONLY WHEN MAPPING IS ACTIVE)    -->
      <!-- ========================================================================= -->
      @if (store.activeWorkspace() === 'MAPPING') {
        <nav aria-label="Mapping Studio Views" class="h-9 px-1 flex items-center justify-between shrink-0">
          <div class="flex items-center rounded-lg border border-slate-200 bg-slate-100 p-0.5">
            
            <!-- 1. Overview -->
            <button
              type="button"
              (click)="store.setSubWorkspace('OVERVIEW')"
              class="h-7 px-3 rounded-md text-xs font-semibold transition-colors cursor-pointer flex items-center gap-1.5 hover:bg-blue-50 hover:text-blue-700"
              [class.bg-white]="store.activeSubWorkspace() === 'OVERVIEW'"
              [class.text-blue-700]="store.activeSubWorkspace() === 'OVERVIEW'"
              [class.border]="store.activeSubWorkspace() === 'OVERVIEW'"
              [class.border-slate-200]="store.activeSubWorkspace() === 'OVERVIEW'"
              [class.text-slate-600]="store.activeSubWorkspace() !== 'OVERVIEW'">
              <app-lucide-icon name="layout-dashboard" [size]="12"></app-lucide-icon>
              <span>Overview</span>
              @if (store.metrics().needsReviewCount > 0 || store.metrics().blockedCount > 0) {
                <span class="text-[10px] px-1.5 py-0.2 rounded font-bold"
                  [class.bg-amber-100]="store.activeSubWorkspace() === 'OVERVIEW'"
                  [class.text-amber-800]="store.activeSubWorkspace() === 'OVERVIEW'"
                  [class.bg-amber-50]="store.activeSubWorkspace() !== 'OVERVIEW'"
                  [class.text-amber-700]="store.activeSubWorkspace() !== 'OVERVIEW'">
                  {{ store.metrics().needsReviewCount + store.metrics().blockedCount }}
                </span>
              }
            </button>

            <!-- 2. Structure -->
            <button
              type="button"
              (click)="store.setSubWorkspace('STRUCTURE')"
              class="h-7 px-3 rounded-md text-xs font-semibold transition-colors cursor-pointer flex items-center gap-1.5 hover:bg-blue-50 hover:text-blue-700"
              [class.bg-white]="store.activeSubWorkspace() === 'STRUCTURE'"
              [class.text-blue-700]="store.activeSubWorkspace() === 'STRUCTURE'"
              [class.border]="store.activeSubWorkspace() === 'STRUCTURE'"
              [class.border-slate-200]="store.activeSubWorkspace() === 'STRUCTURE'"
              [class.text-slate-600]="store.activeSubWorkspace() !== 'STRUCTURE'">
              <app-lucide-icon name="network" [size]="12"></app-lucide-icon>
              <span>Structure</span>
            </button>

            <!-- 3. Fields -->
            <button
              type="button"
              (click)="store.setSubWorkspace('FIELDS')"
              class="h-7 px-3 rounded-md text-xs font-semibold transition-colors cursor-pointer flex items-center gap-1.5 hover:bg-blue-50 hover:text-blue-700"
              [class.bg-white]="store.activeSubWorkspace() === 'FIELDS'"
              [class.text-blue-700]="store.activeSubWorkspace() === 'FIELDS'"
              [class.border]="store.activeSubWorkspace() === 'FIELDS'"
              [class.border-slate-200]="store.activeSubWorkspace() === 'FIELDS'"
              [class.text-slate-600]="store.activeSubWorkspace() !== 'FIELDS'">
              <app-lucide-icon name="table" [size]="12"></app-lucide-icon>
              <span>Fields</span>
              <span class="text-[10px] px-1.5 py-0.2 rounded font-bold"
                [class.bg-blue-100]="store.activeSubWorkspace() === 'FIELDS'"
                [class.text-blue-800]="store.activeSubWorkspace() === 'FIELDS'"
                [class.bg-slate-200]="store.activeSubWorkspace() !== 'FIELDS'"
                [class.text-slate-600]="store.activeSubWorkspace() !== 'FIELDS'">
                {{ store.objects().length }}
              </span>
            </button>

            <!-- 4. Data Controls -->
            <button
              type="button"
              (click)="store.setSubWorkspace('CONTROLS')"
              class="h-7 px-3 rounded-md text-xs font-semibold transition-colors cursor-pointer flex items-center gap-1.5 hover:bg-blue-50 hover:text-blue-700"
              [class.bg-white]="store.activeSubWorkspace() === 'CONTROLS'"
              [class.text-blue-700]="store.activeSubWorkspace() === 'CONTROLS'"
              [class.border]="store.activeSubWorkspace() === 'CONTROLS'"
              [class.border-slate-200]="store.activeSubWorkspace() === 'CONTROLS'"
              [class.text-slate-600]="store.activeSubWorkspace() !== 'CONTROLS'">
              <app-lucide-icon name="shield" [size]="12"></app-lucide-icon>
              <span>Data Controls</span>
            </button>

          </div>
        </nav>
      }

      <!-- ========================================================================= -->
      <!-- WORKSPACE CONTENT CANVAS                                                  -->
      <!-- ========================================================================= -->
      <div class="flex-1 min-h-0 flex flex-col">
        
        <!-- Workspace 1: Mapping Studio -->
        @if (store.activeWorkspace() === 'MAPPING') {
          @if (store.activeSubWorkspace() === 'OVERVIEW') {
            <app-mapping-overview class="w-full h-full flex flex-col min-h-0" />
          } @else if (store.activeSubWorkspace() === 'STRUCTURE') {
            <app-mapping-structure class="w-full h-full flex min-h-0" />
          } @else if (store.activeSubWorkspace() === 'FIELDS') {
            <app-mapping-fields class="w-full h-full flex min-h-0" />
          } @else if (store.activeSubWorkspace() === 'CONTROLS') {
            <app-mapping-controls class="w-full h-full flex flex-col min-h-0" />
          }
        }

        <!-- Workspace 2: Transpiler Studio -->
        @if (store.activeWorkspace() === 'TRANSPILER') {
          <app-transpiler-workspace class="w-full h-full flex flex-col min-h-0" />
        }

      </div>

      <!-- ========================================================================= -->
      <!-- MODAL 1: UNSAVED CHANGE PROTECTION DIALOG                                 -->
      <!-- ========================================================================= -->
      @if (store.pendingNavigation(); as pending) {
        <div class="fixed inset-0 bg-slate-900/40 z-50 flex items-center justify-center p-6 animate-in fade-in duration-100">
          <div class="bg-white border border-slate-200 rounded-lg w-full max-w-md flex flex-col p-5 gap-3">
            
            <div class="flex items-center gap-2.5">
              <div class="w-8 h-8 rounded-full bg-amber-50 border border-amber-200 flex items-center justify-center shrink-0">
                <app-lucide-icon name="alert-circle" [size]="16" class="text-amber-600"></app-lucide-icon>
              </div>
              <h3 class="font-bold text-sm text-slate-900">{{ pending.title }}</h3>
            </div>

            <p class="text-xs text-slate-600 leading-relaxed font-normal">
              {{ pending.description }}
            </p>

            <div class="flex items-center justify-end gap-2 pt-2 border-t border-slate-100 mt-1">
              <button
                type="button"
                (click)="store.cancelPendingNavigation()"
                class="h-8 px-3 rounded border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs cursor-pointer transition-colors">
                Stay / Cancel
              </button>
              <button
                type="button"
                (click)="store.discardPendingNavigation()"
                class="h-8 px-3 rounded border border-rose-200 bg-rose-50 hover:bg-rose-100 text-rose-700 font-semibold text-xs cursor-pointer transition-colors">
                Discard Changes
              </button>
              <button
                type="button"
                (click)="store.applyAndProceedPendingNavigation()"
                class="h-8 px-3.5 rounded bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs cursor-pointer transition-colors">
                Apply Changes
              </button>
            </div>

          </div>
        </div>
      }

      <!-- ========================================================================= -->
      <!-- MODAL 2: STRUCTURAL DEPENDENCY IMPACT MODAL                               -->
      <!-- ========================================================================= -->
      @if (store.showImpactModal() && store.impactModalObject(); as obj) {
        <div class="fixed inset-0 bg-slate-900/40 z-50 flex items-center justify-center p-6 animate-in fade-in duration-100">
          <div class="bg-white border border-slate-200 rounded-lg w-full max-w-xl flex flex-col max-h-[85vh] overflow-hidden">
            
            <div class="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/70 shrink-0">
              <div class="flex items-center gap-2">
                <app-lucide-icon name="network" [size]="16" class="text-indigo-600"></app-lucide-icon>
                <span class="font-bold text-sm text-slate-900">Structural Dependency Impact: {{ obj.sourceName }}</span>
              </div>
              <button
                type="button"
                (click)="store.closeImpactModal()"
                class="text-slate-400 hover:text-slate-600 cursor-pointer">
                <app-lucide-icon name="x" [size]="16"></app-lucide-icon>
              </button>
            </div>

            <div class="p-4 overflow-y-auto flex flex-col gap-3">
              <div class="p-3 bg-indigo-50/50 border border-indigo-200 rounded-md">
                <span class="font-bold text-xs text-indigo-900">
                  This resource has {{ obj.structuralImpact.dependentObjectsCount }} downstream dependencies.
                </span>
                <p class="text-xs text-indigo-800 leading-relaxed font-normal pt-1">
                  Excluding or re-routing this object affects related foreign keys, views, triggers, and routines. Note that formal waiver approval occurs in Step 8: Govern.
                </p>
              </div>

              <!-- Dependencies List -->
              <div class="flex flex-col gap-2">
                <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Affected Objects</span>
                @for (dep of obj.structuralImpact.dependentObjects; track dep.name) {
                  <div class="p-2.5 rounded border border-slate-200 bg-white flex items-center justify-between">
                    <div class="flex flex-col">
                      <div class="flex items-center gap-2">
                        <span class="font-bold text-xs text-slate-900">{{ dep.name }}</span>
                        <span class="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-slate-100 text-slate-600">
                          {{ dep.type }}
                        </span>
                      </div>
                      <span class="text-[11px] text-slate-500 font-medium">{{ dep.impactDescription }}</span>
                    </div>
                  </div>
                }
              </div>
            </div>

            <div class="p-3 border-t border-slate-200 bg-slate-50 flex items-center justify-end shrink-0">
              <button
                type="button"
                (click)="store.closeImpactModal()"
                class="h-8 px-4 rounded bg-slate-800 hover:bg-slate-900 text-white font-semibold text-xs cursor-pointer">
                Done Inspecting
              </button>
            </div>

          </div>
        </div>
      }

    </div>
  `
})
export class Step5MappingComponent implements OnInit {
  public readonly store = inject(Step5MappingStoreService);
  public readonly ms = inject(MigrationUiService);

  ngOnInit(): void {
    this.store.initializeFromDraft();
  }

  public hasActiveDataControls(): boolean {
    const m = this.store.metrics();
    return (
      m.totalPrivacyCount > 0 ||
      m.totalCleansingCount > 0 ||
      m.totalFilterCount > 0 ||
      m.totalDedupCount > 0 ||
      m.totalQualityCount > 0
    );
  }
}
