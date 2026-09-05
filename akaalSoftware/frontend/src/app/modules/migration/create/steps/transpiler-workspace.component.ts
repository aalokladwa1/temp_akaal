import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Step5MappingStoreService } from '../../../../core/services/step5-mapping-store.service';
import { MigrationUiService } from '../../../../core/services/migration-ui.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CodeEditorComponent } from '../../../../shared/components/code-editor.component';
import { CodeObjectCategory, TranspilerObjectContract } from './step5-mapping.models';

@Component({
  selector: 'app-transpiler-workspace',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent, CodeEditorComponent],
  host: {
    class: 'flex flex-1 flex-col w-full h-full min-h-0'
  },
  template: `
    <div class="w-full h-full flex flex-col min-h-0 bg-white border border-slate-200 rounded-lg overflow-hidden font-sans text-xs select-none relative flex-1">
      
      <!-- ========================================================================= -->
      <!-- BANNER 1: INAPPLICABLE FOR DATA-ONLY (M7_DATA_ONLY)                       -->
      <!-- ========================================================================= -->
      @if (isDataOnlyMode()) {
        <div class="m-6 p-8 rounded-lg border border-slate-200 bg-slate-50 flex flex-col items-center justify-center text-center gap-3">
          <div class="w-10 h-10 rounded bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center">
            <app-lucide-icon name="info" [size]="20"></app-lucide-icon>
          </div>
          <div class="max-w-md flex flex-col gap-1">
            <h3 class="text-sm font-bold text-slate-900">Code Transpiler Studio Bypassed</h3>
            <p class="text-xs text-slate-600 leading-relaxed font-medium">
              Current migration mode is <strong class="text-slate-800">M7_DATA_ONLY</strong>. In this mode, stored procedures, functions, packages, and views are omitted from migration execution.
            </p>
          </div>
          <div class="mt-2 flex items-center gap-2">
            <button
              type="button"
              (click)="store.setWorkspace('MAPPING')"
              class="h-8 px-4 rounded bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs transition-colors cursor-pointer flex items-center gap-1.5">
              <span>Return to Mapping Studio</span>
              <app-lucide-icon name="arrow-right" [size]="13"></app-lucide-icon>
            </button>
          </div>
        </div>
      } @else if (store.codeObjects().length === 0) {
        <!-- BANNER 2: NO PROCEDURAL OBJECTS IN SCOPE -->
        <div class="m-6 p-8 rounded-lg border border-slate-200 bg-slate-50 flex flex-col items-center justify-center text-center gap-3">
          <div class="w-10 h-10 rounded bg-slate-100 border border-slate-200 text-slate-500 flex items-center justify-center">
            <app-lucide-icon name="code-2" [size]="20"></app-lucide-icon>
          </div>
          <div class="max-w-md flex flex-col gap-1">
            <h3 class="text-sm font-bold text-slate-900">No Procedural Objects in Scope</h3>
            <p class="text-xs text-slate-600 leading-relaxed font-medium">
              The scoped resources selected in Step 4 do not contain stored procedures, functions, packages, or triggers.
            </p>
          </div>
          <button
            type="button"
            (click)="store.setWorkspace('MAPPING')"
            class="mt-2 h-8 px-4 rounded bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 font-semibold text-xs transition-colors cursor-pointer">
            Return to Mapping Studio
          </button>
        </div>
      } @else {

        <!-- ========================================================================= -->
        <!-- STUDIO WORKSPACE: TOP CONTROLS STRIP                                      -->
        <!-- ========================================================================= -->
        <header class="h-11 px-4 border-b border-slate-200 bg-white flex items-center justify-between shrink-0">
          
          <!-- Left: Routine Dialects, Navigator Toggle & Counts -->
          <div class="flex items-center gap-3">
            <button
              type="button"
              (click)="isSidebarCollapsed.set(!isSidebarCollapsed())"
              class="h-7 px-2.5 rounded border border-slate-200 hover:bg-slate-50 text-slate-700 flex items-center gap-1.5 cursor-pointer text-xs font-semibold transition-colors"
              [title]="isSidebarCollapsed() ? 'Show routine navigator' : 'Collapse routine navigator'">
              <app-lucide-icon [name]="isSidebarCollapsed() ? 'panel-left-open' : 'panel-left-close'" [size]="13"></app-lucide-icon>
              <span>{{ isSidebarCollapsed() ? 'Show Navigator' : 'Collapse' }}</span>
            </button>

            <span class="h-4 w-[1px] bg-slate-200"></span>

            <div class="flex items-center gap-1.5 font-bold text-slate-900 text-xs">
              <span>{{ ms.wizardDraft().sourceProvider }} PL/SQL</span>
              <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
              <span class="text-blue-700">{{ ms.wizardDraft().targetProvider }} PL/pgSQL</span>
            </div>

            <span class="h-4 w-[1px] bg-slate-200"></span>

            <div class="flex items-center gap-2 text-[11px] font-medium text-slate-500">
              <span>{{ store.metrics().totalCodeObjects }} routines</span>
              <span>·</span>
              <span class="text-emerald-700">{{ store.metrics().codeConvertedCount }} Converted</span>
              <span>·</span>
              <span class="text-blue-700">{{ store.metrics().codeModifiedCount }} Modified</span>
              <span>·</span>
              <span class="text-amber-700">{{ store.metrics().codeNeedsReviewCount }} Review</span>
            </div>
          </div>

          <!-- Right: View Modes & Focus Editor & Compatibility Modal Trigger -->
          <div class="flex items-center gap-3">
            
            <!-- View Mode Switcher: Source | Side-by-Side | Target -->
            <div class="flex items-center rounded-lg border border-slate-200 bg-slate-100 p-0.5">
              <button
                type="button"
                (click)="viewMode.set('SOURCE')"
                class="h-7 px-2.5 rounded text-xs font-semibold cursor-pointer transition-colors"
                [class.bg-white]="viewMode() === 'SOURCE'"
                [class.text-slate-900]="viewMode() === 'SOURCE'"
                [class.text-slate-600]="viewMode() !== 'SOURCE'">
                Source
              </button>
              <button
                type="button"
                (click)="viewMode.set('SIDE_BY_SIDE')"
                class="h-7 px-2.5 rounded text-xs font-semibold cursor-pointer transition-colors"
                [class.bg-white]="viewMode() === 'SIDE_BY_SIDE'"
                [class.text-slate-900]="viewMode() === 'SIDE_BY_SIDE'"
                [class.text-slate-600]="viewMode() !== 'SIDE_BY_SIDE'">
                Side-by-Side
              </button>
              <button
                type="button"
                (click)="viewMode.set('TARGET')"
                class="h-7 px-2.5 rounded text-xs font-semibold cursor-pointer transition-colors"
                [class.bg-white]="viewMode() === 'TARGET'"
                [class.text-slate-900]="viewMode() === 'TARGET'"
                [class.text-slate-600]="viewMode() !== 'TARGET'">
                Target
              </button>
            </div>

            <!-- Focus Mode Button -->
            <button
              type="button"
              (click)="isFocusMode.set(!isFocusMode())"
              class="h-7 px-2.5 rounded border border-slate-200 bg-white hover:bg-slate-50 font-semibold text-xs flex items-center gap-1.5 cursor-pointer transition-colors"
              [class.bg-blue-50]="isFocusMode()"
              [class.text-blue-700]="isFocusMode()"
              [class.border-blue-300]="isFocusMode()">
              <app-lucide-icon [name]="isFocusMode() ? 'minimize-2' : 'maximize-2'" [size]="12"></app-lucide-icon>
              <span>{{ isFocusMode() ? 'Exit Focus' : 'Focus Editor' }}</span>
            </button>

            <!-- Compatibility Pack Modal Trigger -->
            @if (store.compatibilityHelpers().length > 0) {
              <button
                type="button"
                (click)="showCompatModal = true"
                class="h-7 px-2.5 rounded border border-indigo-200 bg-indigo-50 hover:bg-indigo-100 font-semibold text-xs text-indigo-700 flex items-center gap-1.5 cursor-pointer transition-colors">
                <app-lucide-icon name="layers" [size]="12"></app-lucide-icon>
                <span>Compatibility Pack ({{ store.compatibilityHelpers().length }})</span>
              </button>
            }

          </div>

        </header>

        <!-- ========================================================================= -->
        <!-- STUDIO MAIN BODY: LEFT LIST + EXPANDED CODE WORKBENCH                     -->
        <!-- ========================================================================= -->
        <div class="flex-1 flex min-h-0">
          
          <!-- LEFT PANE: Procedural Object Selector List (Hidden in Focus Mode or when Collapsed) -->
          @if (!isFocusMode() && !isSidebarCollapsed()) {
            <aside class="w-64 bg-white border-r border-slate-200 flex flex-col shrink-0 min-h-0">
              
              <!-- Search & Category Filters -->
              <div class="p-2.5 border-b border-slate-200 bg-slate-50/50 flex flex-col gap-2">
                <div class="relative">
                  <input
                    type="text"
                    [(ngModel)]="searchQuery"
                    placeholder="Search routines &amp; packages..."
                    class="w-full h-7 pl-8 pr-2.5 text-xs bg-white border border-slate-200 rounded-md focus:outline-none focus:border-blue-500 text-slate-800 placeholder:text-slate-400 font-normal" />
                  <app-lucide-icon name="search" [size]="12" class="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"></app-lucide-icon>
                </div>

                <div class="flex items-center gap-1 overflow-x-auto pb-0.5">
                  @for (cat of categoryFilters; track cat.id) {
                    <button
                      type="button"
                      (click)="selectedCategoryFilter.set(cat.id)"
                      class="px-2 py-1 rounded text-[11px] font-medium whitespace-nowrap cursor-pointer transition-colors hover:bg-slate-200"
                      [class.bg-blue-600]="selectedCategoryFilter() === cat.id"
                      [class.text-white]="selectedCategoryFilter() === cat.id"
                      [class.font-semibold]="selectedCategoryFilter() === cat.id"
                      [class.bg-slate-100]="selectedCategoryFilter() !== cat.id"
                      [class.text-slate-600]="selectedCategoryFilter() !== cat.id">
                      {{ cat.label }} ({{ getCategoryCount(cat.id) }})
                    </button>
                  }
                </div>
              </div>

              <!-- List of routines -->
              <div class="flex-1 overflow-y-auto p-1.5 flex flex-col gap-1">
                @for (item of filteredCodeObjects(); track item.id) {
                  <div
                    (click)="store.selectCodeObject(item.id)"
                    class="p-2.5 rounded-md border flex items-center justify-between cursor-pointer transition-colors hover:border-slate-300"
                    [class.border-blue-500]="store.selectedCodeObjectId() === item.id"
                    [class.bg-blue-50]="store.selectedCodeObjectId() === item.id"
                    [class.border-slate-200]="store.selectedCodeObjectId() !== item.id"
                    [class.bg-white]="store.selectedCodeObjectId() !== item.id">
                    
                    <div class="flex flex-col min-w-0 gap-0.5">
                      <div class="flex items-center gap-1.5">
                        <span class="font-bold text-xs text-slate-900 truncate">{{ item.name }}</span>
                      </div>
                      <div class="flex items-center gap-2 text-[10px] text-slate-500 font-medium">
                        <span class="uppercase">{{ item.categoryLabel }}</span>
                        @if (item.diagnostics.length > 0) {
                          <span class="text-amber-700">· {{ item.diagnostics.length }} notices</span>
                        }
                      </div>
                    </div>

                    <div class="flex items-center gap-1 shrink-0">
                      @if (item.status === 'BLOCKED') {
                        <span class="px-1.5 py-0.2 rounded text-[9px] font-bold bg-rose-100 text-rose-800">Blocked</span>
                      } @else if (item.status === 'NEEDS_REVIEW') {
                        <span class="px-1.5 py-0.2 rounded text-[9px] font-bold bg-amber-100 text-amber-900">Review</span>
                      } @else if (item.isModified) {
                        <span class="px-1.5 py-0.2 rounded text-[9px] font-bold bg-blue-100 text-blue-800">Modified</span>
                      } @else {
                        <span class="px-1.5 py-0.2 rounded text-[9px] font-bold bg-emerald-50 text-emerald-700">Converted</span>
                      }
                    </div>

                  </div>
                }
              </div>

            </aside>
          }

          <!-- RIGHT MAIN: FULL MONACO EDITOR WORKBENCH -->
          <section aria-label="Transpiler Studio Workbench" class="flex-1 flex flex-col min-h-0 bg-white min-w-0">
            
            @if (activeCodeObject(); as active) {
              
              <!-- Editor Context & Manual Edit Toolbar -->
              <div class="h-10 px-4 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between shrink-0">
                <div class="flex items-center gap-2 min-w-0">
                  <span class="font-bold text-xs text-slate-900 truncate">{{ active.name }}</span>
                  <span class="text-slate-400">·</span>
                  <span class="text-xs text-slate-600 font-medium">{{ active.categoryLabel }}</span>
                  
                  @if (active.isModified) {
                    <span class="px-1.5 py-0.2 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                      Operator Modified
                    </span>
                  }
                  @if (isTargetDirty()) {
                    <span class="px-1.5 py-0.2 rounded text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
                      Unapplied Draft
                    </span>
                  }
                </div>

                <!-- Action Controls: Edit Manually, Apply, Revert -->
                <div class="flex items-center gap-2 shrink-0">
                  @if (!isEditingManually) {
                    <button
                      type="button"
                      (click)="enableManualEditing()"
                      class="h-7 px-2.5 rounded border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs flex items-center gap-1 cursor-pointer transition-colors">
                      <app-lucide-icon name="edit-3" [size]="12" class="text-blue-600"></app-lucide-icon>
                      <span>Edit Manually</span>
                    </button>
                  } @else {
                    <button
                      type="button"
                      (click)="cancelManualEditing()"
                      class="h-7 px-2.5 rounded border border-slate-200 bg-white text-slate-600 font-semibold text-xs cursor-pointer">
                      Cancel Edit
                    </button>
                  }

                  @if (active.isModified) {
                    <button
                      type="button"
                      (click)="store.revertTranspilerCodeToProposal(active.id)"
                      class="h-7 px-2.5 rounded border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 font-semibold text-xs flex items-center gap-1 cursor-pointer transition-colors">
                      <app-lucide-icon name="rotate-ccw" [size]="11"></app-lucide-icon>
                      <span>Revert to Proposal</span>
                    </button>
                  }

                  <button
                    type="button"
                    [disabled]="!isTargetDirty()"
                    (click)="applyTargetCodeDraft()"
                    class="h-7 px-3 rounded font-semibold text-xs flex items-center gap-1.5 transition-colors"
                    [class.bg-blue-600]="isTargetDirty()"
                    [class.text-white]="isTargetDirty()"
                    [class.cursor-pointer]="isTargetDirty()"
                    [class.bg-slate-100]="!isTargetDirty()"
                    [class.text-slate-400]="!isTargetDirty()"
                    [class.cursor-not-allowed]="!isTargetDirty()">
                    <app-lucide-icon name="check" [size]="12"></app-lucide-icon>
                    <span>Apply Code</span>
                  </button>
                </div>
              </div>

              <!-- DUAL MONACO WORKBENCH CANVAS (Full vertical height utilization) -->
              <div class="flex-1 flex min-h-0 w-full">
                
                <!-- Left: Source Code -->
                @if (viewMode() === 'SOURCE' || viewMode() === 'SIDE_BY_SIDE') {
                  <div class="flex-1 flex flex-col border-r border-slate-200 min-h-0"
                    [ngClass]="viewMode() === 'SIDE_BY_SIDE' ? 'w-1/2' : 'w-full'">
                    <div class="h-7 px-3 bg-slate-100 border-b border-slate-200 flex items-center justify-between text-[11px] font-medium text-slate-600 shrink-0">
                      <span class="font-bold">Source Dialect ({{ active.sourceLanguage }})</span>
                      <span class="text-[10px] text-slate-400 uppercase">Read-Only Reference</span>
                    </div>
                    <div class="flex-1 min-h-0 bg-slate-50 flex flex-col">
                      <app-code-editor
                        class="flex-1 flex flex-col w-full h-full min-h-0"
                        [code]="active.sourceCode"
                        [readOnly]="true"
                        language="sql"
                        [ariaLabel]="'Source code for ' + active.name" />
                    </div>
                  </div>
                }

                <!-- Right: Target Code -->
                @if (viewMode() === 'TARGET' || viewMode() === 'SIDE_BY_SIDE') {
                  <div class="flex-1 flex flex-col min-h-0"
                    [ngClass]="viewMode() === 'SIDE_BY_SIDE' ? 'w-1/2' : 'w-full'">
                    <div class="h-7 px-3 bg-slate-100 border-b border-slate-200 flex items-center justify-between text-[11px] font-medium text-slate-600 shrink-0">
                      <div class="flex items-center gap-1.5">
                        <span class="font-bold">Generated Target ({{ active.targetLanguage }})</span>
                        @if (isEditingManually) {
                          <span class="text-[10px] font-semibold text-blue-700 bg-blue-50 px-1 rounded">
                            Editing
                          </span>
                        }
                      </div>
                      <span class="text-[10px] text-slate-400">
                        {{ isEditingManually ? 'Operator Editable' : 'Generated Read-Only' }}
                      </span>
                    </div>
                    <div class="flex-1 min-h-0 bg-white flex flex-col">
                      <app-code-editor
                        class="flex-1 flex flex-col w-full h-full min-h-0"
                        [code]="currentEditTargetCode"
                        [readOnly]="!isEditingManually"
                        language="sql"
                        (codeChange)="onTargetCodeInput($event)"
                        [ariaLabel]="'Target code editor for ' + active.name" />
                    </div>
                  </div>
                }

              </div>

              <!-- COLLAPSIBLE BOTTOM DIAGNOSTICS STRIP (Zero permanent crush of editor height) -->
              <div class="border-t border-slate-200 bg-slate-50 shrink-0">
                
                <!-- Bottom strip banner -->
                <div
                  id="transpiler-diagnostics-toggle"
                  (click)="isDiagnosticsExpanded = !isDiagnosticsExpanded"
                  class="h-8 px-4 flex items-center justify-between text-xs font-semibold text-slate-700 hover:bg-slate-100 hover:text-blue-700 cursor-pointer transition-colors select-none">
                  <div class="flex items-center gap-2">
                    <app-lucide-icon [name]="isDiagnosticsExpanded ? 'chevron-down' : 'chevron-up'" [size]="13" class="text-slate-500"></app-lucide-icon>
                    <span>Transpiler Diagnostics</span>
                    <span class="px-1.5 py-0.2 rounded text-[10px] font-bold"
                      [class.bg-slate-200]="active.diagnostics.length === 0"
                      [class.text-slate-600]="active.diagnostics.length === 0"
                      [class.bg-amber-100]="active.diagnostics.length > 0"
                      [class.text-amber-800]="active.diagnostics.length > 0">
                      {{ active.diagnostics.length }} notice{{ active.diagnostics.length === 1 ? '' : 's' }}
                    </span>
                  </div>

                  <span class="text-[11px] text-slate-500 font-normal">
                    {{ isDiagnosticsExpanded ? 'Click to collapse drawer' : 'Click to inspect syntax notices' }}
                  </span>
                </div>

                <!-- Expanded Diagnostics Table -->
                @if (isDiagnosticsExpanded) {
                  <div class="p-3 border-t border-slate-200 max-h-44 overflow-y-auto flex flex-col gap-2 bg-white">
                    @for (diag of active.diagnostics; track diag.id) {
                      <div class="p-2.5 rounded-md border flex flex-col gap-1"
                        [class.border-amber-200]="diag.severity === 'WARNING'"
                        [class.bg-amber-50]="diag.severity === 'WARNING'"
                        [class.border-blue-200]="diag.severity === 'INFO'"
                        [class.bg-blue-50]="diag.severity === 'INFO'"
                        [class.border-rose-200]="diag.severity === 'ERROR'"
                        [class.bg-rose-50]="diag.severity === 'ERROR'">
                        
                        <div class="flex items-center justify-between text-[11px]">
                          <div class="flex items-center gap-2">
                            <span class="px-1.5 py-0.2 rounded font-bold text-[10px]"
                              [class.bg-amber-100]="diag.severity === 'WARNING'"
                              [class.text-amber-800]="diag.severity === 'WARNING'"
                              [class.bg-rose-100]="diag.severity === 'ERROR'"
                              [class.text-rose-800]="diag.severity === 'ERROR'"
                              [class.bg-blue-100]="diag.severity === 'INFO'"
                              [class.text-blue-800]="diag.severity === 'INFO'">
                              {{ diag.severity }}
                            </span>
                            @if (diag.line) {
                              <span class="font-mono text-slate-500">Line {{ diag.line }}{{ diag.column ? ':' + diag.column : '' }}</span>
                            }
                            @if (diag.construct) {
                              <span class="font-mono text-slate-700 bg-slate-100 px-1 py-0.2 rounded text-[10px]">{{ diag.construct }}</span>
                            }
                          </div>
                        </div>

                        <p class="text-xs text-slate-800 font-medium leading-relaxed">{{ diag.message }}</p>

                        @if (diag.recommendation) {
                          <p class="text-[11px] text-slate-600 font-normal">
                            <strong>Remediation:</strong> {{ diag.recommendation }}
                          </p>
                        }
                      </div>
                    }

                    @if (active.diagnostics.length === 0) {
                      <div class="py-3 text-center text-slate-400 text-xs">
                        Zero syntax issues or compatibility warnings detected for this routine.
                      </div>
                    }
                  </div>
                }

              </div>

            } @else {
              <div class="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-400">
                <app-lucide-icon name="code-2" [size]="28" class="text-slate-300 mb-2"></app-lucide-icon>
                <span class="font-bold text-xs text-slate-600">No Routine Selected</span>
                <span class="text-[11px] text-slate-400">Select a stored procedure or function from the left navigator</span>
              </div>
            }

          </section>

        </div>

      }

      <!-- ========================================================================= -->
      <!-- COMPATIBILITY PACK MODAL                                                  -->
      <!-- ========================================================================= -->
      @if (showCompatModal) {
        <div class="fixed inset-0 bg-slate-900/40 z-50 flex items-center justify-center p-6">
          <div class="bg-white border border-slate-200 rounded-lg w-full max-w-2xl flex flex-col max-h-[85vh] overflow-hidden">
            
            <div class="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/70 shrink-0">
              <div class="flex items-center gap-2">
                <app-lucide-icon name="layers" [size]="16" class="text-indigo-600"></app-lucide-icon>
                <span class="font-bold text-sm text-slate-900">AKAAL Dialect Compatibility Support Pack</span>
              </div>
              <button
                type="button"
                (click)="showCompatModal = false"
                class="text-slate-400 hover:text-slate-600 cursor-pointer">
                <app-lucide-icon name="x" [size]="16"></app-lucide-icon>
              </button>
            </div>

            <div class="p-4 overflow-y-auto flex flex-col gap-3">
              <p class="text-xs text-slate-600 leading-relaxed font-normal">
                PostgreSQL lacks certain native Oracle PL/SQL built-in functions. AKAAL generates declarative emulation functions to preserve semantics without requiring manual application rewrites.
              </p>

              @for (helper of store.compatibilityHelpers(); track helper.name) {
                <div class="p-3 border border-slate-200 rounded-md flex flex-col gap-1.5 bg-slate-50/40">
                  <div class="flex items-center justify-between">
                    <span class="font-bold text-xs text-indigo-900">{{ helper.name }}</span>
                    <span class="px-1.5 py-0.2 rounded text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
                      {{ helper.category }}
                    </span>
                  </div>
                  <p class="text-xs text-slate-700 font-medium">{{ helper.rationale }}</p>
                  <span class="text-[11px] text-slate-500 font-mono">
                    Referenced in: {{ helper.affectedRoutines.join(', ') }}
                  </span>
                  <div class="mt-1 p-2 bg-slate-900 text-slate-100 rounded text-[11px] font-mono overflow-x-auto select-text">
                    {{ helper.installSql }}
                  </div>
                </div>
              }
            </div>

            <div class="p-3 border-t border-slate-200 bg-slate-50 flex items-center justify-end shrink-0">
              <button
                type="button"
                (click)="showCompatModal = false"
                class="h-8 px-4 rounded bg-slate-800 hover:bg-slate-900 text-white font-semibold text-xs cursor-pointer">
                Close Pack Viewer
              </button>
            </div>

          </div>
        </div>
      }

    </div>
  `
})
export class TranspilerWorkspaceComponent {
  public readonly store = inject(Step5MappingStoreService);
  public readonly ms = inject(MigrationUiService);

  public searchQuery: string = '';
  public selectedCategoryFilter = signal<string>('ALL');
  public viewMode = signal<'SOURCE' | 'SIDE_BY_SIDE' | 'TARGET'>('SIDE_BY_SIDE');
  public isFocusMode = signal<boolean>(false);
  public isSidebarCollapsed = signal<boolean>(false);
  public isDiagnosticsExpanded: boolean = false;
  public showCompatModal: boolean = false;

  public isEditingManually: boolean = false;
  public currentEditTargetCode: string = '';

  public readonly categoryFilters = [
    { id: 'ALL', label: 'All Routines' },
    { id: 'PROCEDURE', label: 'Procedures' },
    { id: 'FUNCTION', label: 'Functions' },
    { id: 'PACKAGE', label: 'Packages' },
    { id: 'VIEW', label: 'Views' },
    { id: 'TRIGGER', label: 'Triggers' }
  ];

  public readonly isDataOnlyMode = computed(() => {
    return this.ms.wizardDraft().mode === 'M7_DATA_ONLY';
  });

  public readonly activeCodeObject = computed<TranspilerObjectContract | null>(() => {
    const id = this.store.selectedCodeObjectId();
    const list = this.store.codeObjects();
    const found = list.find(c => c.id === id) || list[0] || null;
    if (found && !this.isEditingManually) {
      this.currentEditTargetCode = found.currentTargetCode;
    }
    return found;
  });

  public readonly filteredCodeObjects = computed(() => {
    const list = this.store.codeObjects();
    const cat = this.selectedCategoryFilter();
    const q = this.searchQuery.trim().toLowerCase();

    return list.filter(item => {
      if (cat !== 'ALL' && item.category !== cat) return false;
      if (!q) return true;
      return item.name.toLowerCase().includes(q) || item.categoryLabel.toLowerCase().includes(q);
    });
  });

  public getCategoryCount(catId: string): number {
    const list = this.store.codeObjects();
    if (catId === 'ALL') return list.length;
    return list.filter(c => c.category === catId).length;
  }

  public enableManualEditing(): void {
    this.isEditingManually = true;
    const cur = this.activeCodeObject();
    if (cur) {
      this.currentEditTargetCode = cur.currentTargetCode;
    }
  }

  public cancelManualEditing(): void {
    this.isEditingManually = false;
    const cur = this.activeCodeObject();
    if (cur) {
      this.currentEditTargetCode = cur.currentTargetCode;
    }
    this.store.transpilerCodeDraft.set(null);
  }

  public onTargetCodeInput(newCode: string): void {
    this.currentEditTargetCode = newCode;
    this.store.transpilerCodeDraft.set(newCode);
  }

  public isTargetDirty(): boolean {
    const cur = this.activeCodeObject();
    if (!cur) return false;
    return this.currentEditTargetCode !== cur.currentTargetCode;
  }

  public applyTargetCodeDraft(): void {
    const cur = this.activeCodeObject();
    if (!cur) return;
    this.store.updateTargetCode(cur.id, this.currentEditTargetCode);
    this.store.transpilerCodeDraft.set(null);
    this.isEditingManually = false;
  }
}
