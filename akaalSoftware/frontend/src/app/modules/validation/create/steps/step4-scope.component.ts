import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ValidationUiService } from '../../../../core/services/validation-ui.service';
import { PhysicalProviderId } from '../../../../core/models/migration-view.models';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';
import {
  Step4Pathway,
  ComparisonUnit,
  ScopeDisposition,
  CorrespondenceProvenance,
  PhysicalObservationStatus,
  ColumnCorrespondenceItem,
  MigrationExecutionSummary,
  OperatorDecisionItem,
  NamespaceScopeItem,
  DiscoveredComparisonUnit,
  DiscoveredHierarchyNode,
  FlattenedScopeNode
} from './step4-scope.models';

@Component({
  selector: 'app-step4-scope',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="max-w-7xl mx-auto w-full space-y-6 select-none font-sans text-xs">
      
      <!-- ========================================================================= -->
      <!-- 0. HEADER & RESTRAINED CONTEXT AREA                                       -->
      <!-- ========================================================================= -->
      <div class="flex flex-col gap-3.5 border-b border-slate-200 pb-4">
        <div class="flex items-start justify-between flex-wrap gap-4">
          <div class="flex flex-col gap-1.5">
            <h1 class="text-xl font-bold text-slate-900 tracking-tight">Scope &amp; Correspondence</h1>
            <p class="text-sm text-slate-500 font-normal leading-relaxed">
              Define what existing Source truth this validation mission should prove against the Target.
            </p>
          </div>

          <!-- Restrained Endpoint Context Bar -->
          <div class="flex items-center gap-3 px-3.5 py-2 bg-white border border-slate-200 rounded-lg shadow-2xs text-xs">
            <div class="flex items-center gap-2 text-slate-700">
              <app-lucide-icon [name]="getProviderIcon(sourceProvider())" [size]="14" class="text-blue-600"></app-lucide-icon>
              <span class="font-bold text-slate-900">{{ sourceProvider() }}</span>
              <span class="text-slate-400">&middot;</span>
              <span class="font-mono text-slate-600 truncate max-w-[150px]">{{ sourceEndpointLabel() }}</span>
            </div>

            <app-lucide-icon name="arrow-right" [size]="13" class="text-slate-400 shrink-0 mx-0.5"></app-lucide-icon>

            <div class="flex items-center gap-2 text-slate-700">
              <app-lucide-icon [name]="getProviderIcon(targetProvider())" [size]="14" class="text-emerald-600"></app-lucide-icon>
              <span class="font-bold text-slate-900">{{ targetProvider() }}</span>
              <span class="text-slate-400">&middot;</span>
              <span class="font-mono text-slate-600 truncate max-w-[150px]">{{ targetEndpointLabel() }}</span>
            </div>

            @if (vs.newValidationDraft().validationContext === 'EXISTING_PROJECT') {
              <span class="ml-1.5 px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 text-[10px] font-bold">
                Project Linked
              </span>
            }
          </div>
        </div>

        <!-- Factual Summary Strip (Zero KPI cards, restrained enterprise layout) -->
        <div class="h-11 px-4 bg-slate-50/80 border border-slate-200 rounded-lg flex items-center justify-between flex-wrap gap-4 text-xs">
          <div class="flex items-center gap-4 text-slate-600">
            <span class="flex items-center gap-1.5">
              <strong class="font-bold text-slate-900 font-mono text-xs">{{ includedUnitsCount() }}</strong>
              <span>comparison units</span>
            </span>
            <span class="text-slate-300">&middot;</span>
            <span class="flex items-center gap-1.5">
              <strong class="font-bold text-emerald-700 font-mono text-xs">{{ discoveredTargetsCount() }}</strong>
              <span>discovered in target</span>
            </span>
            @if (notDiscoveredTargetsCount() > 0) {
              <span class="text-slate-300">&middot;</span>
              <span class="flex items-center gap-1.5">
                <strong class="font-bold text-amber-700 font-mono text-xs">{{ notDiscoveredTargetsCount() }}</strong>
                <span>not currently discovered</span>
              </span>
            }
            <span class="text-slate-300">&middot;</span>
            <span class="flex items-center gap-1.5">
              @if (decisionsRequiredCount() > 0) {
                <strong class="font-bold text-amber-700 font-mono text-xs">{{ decisionsRequiredCount() }}</strong>
                <span class="text-amber-800 font-semibold">decisions required</span>
              } @else {
                <strong class="font-bold text-emerald-700 font-mono text-xs">0</strong>
                <span class="text-slate-600">decisions required</span>
              }
            </span>
            @if (totalVolumeFormatted()) {
              <span class="text-slate-300">&middot;</span>
              <span class="flex items-center gap-1.5 text-slate-500 text-xs">
                <span>Volume estimate:</span>
                <strong class="font-bold text-slate-800 font-mono">{{ totalVolumeFormatted() }}</strong>
              </span>
            }
          </div>

          <!-- Actions: Refresh Observation -->
          <div class="flex items-center gap-2">
            <button
              type="button"
              (click)="refreshObservation()"
              [disabled]="isRefreshing()"
              class="h-7 px-3 text-xs font-medium text-slate-700 hover:text-slate-900 bg-white border border-slate-200 hover:bg-slate-100 rounded-md flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs disabled:opacity-50"
              title="Re-evaluate target catalog discovery observation">
              <app-lucide-icon name="refresh-cw" [size]="12" [class.animate-spin]="isRefreshing()"></app-lucide-icon>
              <span>Refresh Observation</span>
            </button>
          </div>
        </div>
      </div>

      <!-- ========================================================================= -->
      <!-- PATHWAY A: INHERITED MIGRATION SCOPE (Linked AKAAL Migration Project)      -->
      <!-- ========================================================================= -->
      @if (vs.newValidationDraft().validationContext === 'EXISTING_PROJECT') {
        <div class="space-y-5">
          
          <!-- Card 1: Authoritative Migration Scope & Execution Context -->
          <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-2xs space-y-4">
            <div class="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-3">
              <div class="flex items-center gap-2.5">
                <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center shrink-0">
                  <app-lucide-icon name="layers" [size]="16"></app-lucide-icon>
                </div>
                <div>
                  <div class="flex items-center gap-2">
                    <h2 class="text-sm font-bold text-slate-900">Authoritative Migration Scope</h2>
                    <span class="px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 text-[10px] font-bold">
                      Migration Plan
                    </span>
                  </div>
                  <p class="text-xs text-slate-500 font-normal">
                    Scope is inherited directly from the linked migration plan without redundant manual re-entry.
                  </p>
                </div>
              </div>

              <!-- Scope Action Buttons -->
              <div class="flex items-center gap-2">
                <button
                  type="button"
                  (click)="openCustomizeModal()"
                  class="h-8 px-3 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-md flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs"
                  title="Include or exclude specific schemas and tables">
                  <app-lucide-icon name="sliders-horizontal" [size]="13" class="text-slate-500"></app-lucide-icon>
                  <span>Customize Scope</span>
                </button>
                <button
                  type="button"
                  (click)="openInspectDrawer()"
                  class="h-8 px-3 text-xs font-semibold text-blue-700 bg-blue-50/80 border border-blue-200 hover:bg-blue-100/70 rounded-md flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs"
                  title="Inspect complete comparison unit manifest and column mappings">
                  <app-lucide-icon name="eye" [size]="13" class="text-blue-600"></app-lucide-icon>
                  <span>Inspect Scope</span>
                </button>
              </div>
            </div>

            <!-- Factual Breakdown Grid -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
              <!-- Scope Definition -->
              <div class="p-3.5 bg-slate-50/70 border border-slate-200 rounded-lg space-y-1">
                <div class="text-[11px] font-bold uppercase tracking-wider text-slate-500">Inherited Scope</div>
                <div class="text-sm font-bold text-slate-900 font-mono">{{ includedUnitsCount() }} Comparison Units</div>
                <div class="text-xs text-slate-500">Spanning {{ uniqueSchemas().join(', ') }} schemas</div>
              </div>

              <!-- Migration Execution Context -->
              <div class="p-3.5 bg-slate-50/70 border border-slate-200 rounded-lg space-y-1">
                <div class="text-[11px] font-bold uppercase tracking-wider text-slate-500">Execution Status</div>
                <div class="flex items-center gap-2 text-xs font-mono">
                  <span class="text-emerald-700 font-bold">{{ executionSummary().completedUnits }} completed</span>
                  <span class="text-slate-300">&middot;</span>
                  <span class="text-red-700 font-bold">{{ executionSummary().failedUnits }} failed</span>
                  <span class="text-slate-300">&middot;</span>
                  <span class="text-slate-600 font-bold">{{ executionSummary().inProgressUnits }} pending</span>
                </div>
                <div class="text-xs text-slate-500">Source: Execution Graph Phase 2</div>
              </div>

              <!-- Correspondence Provenance -->
              <div class="p-3.5 bg-slate-50/70 border border-slate-200 rounded-lg space-y-1">
                <div class="text-[11px] font-bold uppercase tracking-wider text-slate-500">Correspondence Provenance</div>
                <div class="text-sm font-bold text-slate-900">Canonical Migration Plan</div>
                <div class="text-xs text-slate-500">All {{ units().length }} units have authoritative expected targets</div>
              </div>
            </div>
          </div>

          <!-- Card 2: Target Correspondence & Physical Observation Status -->
          <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-2xs space-y-4">
            <div class="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-3">
              <div class="flex items-center gap-2.5">
                <div class="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center shrink-0">
                  <app-lucide-icon name="shield-check" [size]="16"></app-lucide-icon>
                </div>
                <div>
                  <h2 class="text-sm font-bold text-slate-900">Target Counterparts &amp; Physical Observation</h2>
                  <p class="text-xs text-slate-500 font-normal">
                    Physical observation status confirms what discovered objects exist in the Target catalog today.
                  </p>
                </div>
              </div>

              <span class="px-2.5 py-1 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-bold">
                {{ discoveredTargetsCount() }} of {{ includedUnitsCount() }} Discovered
              </span>
            </div>

            <!-- Law 6 Notice: Missing Expected Target is NOT a configuration blocker -->
            @if (notDiscoveredTargetsCount() > 0) {
              <div class="p-4 bg-amber-50/70 border border-amber-200 rounded-lg flex items-start gap-3 text-xs">
                <app-lucide-icon name="alert-circle" [size]="16" class="text-amber-600 shrink-0 mt-0.5"></app-lucide-icon>
                <div class="space-y-1">
                  <div class="font-bold text-amber-900">
                    {{ notDiscoveredTargetsCount() }} expected target counterpart is not currently discovered in the Target catalog
                  </div>
                  <p class="text-amber-800 leading-relaxed font-normal">
                    <strong class="font-semibold">Observation Law:</strong> A known expected target that is physically absent from the target catalog remains in validation scope.
                    Validation exists specifically to prove whether required data arrived; missing target objects will be tested and reported at execution runtime.
                    This does not block proceeding to Step 5.
                  </p>
                </div>
              </div>
            }

            <!-- Decisions Status -->
            <div class="p-3.5 bg-slate-50/70 border border-slate-200 rounded-lg flex items-center justify-between flex-wrap gap-3">
              <div class="flex items-center gap-2 text-xs">
                <app-lucide-icon name="check-circle" [size]="15" class="text-emerald-600"></app-lucide-icon>
                <span class="font-medium text-slate-700">
                  All <strong class="text-slate-900 font-mono">{{ includedUnitsCount() }}</strong> comparison units have authoritative target correspondence defined by the migration plan.
                </span>
              </div>
              <span class="text-xs font-bold text-emerald-700">0 Operator Decisions Required</span>
            </div>
          </div>

        </div>
      }

      <!-- ========================================================================= -->
      <!-- PATHWAY B & C: INDEPENDENT VALIDATION (Choice, Import, Define)             -->
      <!-- ========================================================================= -->
      @if (vs.newValidationDraft().validationContext === 'INDEPENDENT') {
        
        <!-- ======================================================================= -->
        <!-- STATE 1: CHOICE OPENING (2 Clean Interactive Cards)                     -->
        <!-- ======================================================================= -->
        @if (currentPathway() === 'CHOICE') {
          <div class="space-y-6">
            <div class="text-center max-w-xl mx-auto space-y-1.5 py-3">
              <h2 class="text-base font-bold text-slate-900 tracking-tight">Select Scope &amp; Correspondence Pathway</h2>
              <p class="text-xs text-slate-500 leading-relaxed">
                Choose how comparison units and expected Target counterparts are established for this mission.
              </p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-5 max-w-4xl mx-auto">
              <!-- Card 1: Import Migration Metadata -->
              <div
                (click)="setPathway('IMPORT')"
                class="group bg-white hover:bg-slate-50/60 border border-slate-200 hover:border-blue-400 rounded-xl p-6 shadow-2xs hover:shadow-xs transition-all cursor-pointer flex flex-col justify-between gap-5 text-left">
                <div class="space-y-3">
                  <div class="flex items-center justify-between">
                    <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center group-hover:scale-105 transition-transform">
                      <app-lucide-icon name="file-spreadsheet" [size]="20"></app-lucide-icon>
                    </div>
                    <span class="px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200 text-[10px] font-bold">
                      External Manifest
                    </span>
                  </div>
                  <div class="space-y-1">
                    <h3 class="text-sm font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
                      Import Migration Metadata
                    </h3>
                    <p class="text-xs text-slate-500 leading-relaxed font-normal">
                      Load mapping specifications or manifests from external migration tools (AWS DMS, Oracle GoldenGate, custom plans, CSV/JSON).
                    </p>
                  </div>
                </div>

                <div class="pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-blue-600 font-semibold">
                  <span>Import external manifest</span>
                  <app-lucide-icon name="arrow-right" [size]="14" class="group-hover:translate-x-0.5 transition-transform"></app-lucide-icon>
                </div>
              </div>

              <!-- Card 2: Define Correspondence -->
              <div
                (click)="setPathway('DEFINE')"
                class="group bg-white hover:bg-slate-50/60 border border-slate-200 hover:border-emerald-400 rounded-xl p-6 shadow-2xs hover:shadow-xs transition-all cursor-pointer flex flex-col justify-between gap-5 text-left">
                <div class="space-y-3">
                  <div class="flex items-center justify-between">
                    <div class="w-10 h-10 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center group-hover:scale-105 transition-transform">
                      <app-lucide-icon name="sliders-horizontal" [size]="20"></app-lucide-icon>
                    </div>
                    <span class="px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200 text-[10px] font-bold">
                      Catalog Discovery
                    </span>
                  </div>
                  <div class="space-y-1">
                    <h3 class="text-sm font-bold text-slate-900 group-hover:text-emerald-600 transition-colors">
                      Define Correspondence Rules
                    </h3>
                    <p class="text-xs text-slate-500 leading-relaxed font-normal">
                      Declare comparison scope across discovered catalogs and evaluate correspondence rules (exact match, prefix mapping, custom rules).
                    </p>
                  </div>
                </div>

                <div class="pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-emerald-600 font-semibold">
                  <span>Define rules &amp; scope</span>
                  <app-lucide-icon name="arrow-right" [size]="14" class="group-hover:translate-x-0.5 transition-transform"></app-lucide-icon>
                </div>
              </div>
            </div>
          </div>
        }

        <!-- ======================================================================= -->
        <!-- STATE 2: EXTERNAL METADATA IMPORT (Truthful Unavailable State)          -->
        <!-- ======================================================================= -->
        @if (currentPathway() === 'IMPORT') {
          <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs max-w-2xl mx-auto space-y-5 text-center">
            <div class="w-12 h-12 rounded-xl bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center mx-auto">
              <app-lucide-icon name="file-spreadsheet" [size]="24"></app-lucide-icon>
            </div>

            <div class="space-y-2">
              <h2 class="text-base font-bold text-slate-900">External Metadata Import Pending Integration</h2>
              <p class="text-xs text-slate-600 leading-relaxed max-w-lg mx-auto font-normal">
                Direct external migration manifest ingestion (AWS DMS task logs, GoldenGate PRM parameters, CSV correspondence files) is pending backend engine integration in this release.
              </p>
            </div>

            <div class="p-4 bg-slate-50 border border-slate-200 rounded-lg text-left text-xs text-slate-600 space-y-1.5">
              <div class="font-bold text-slate-800">Supported in this build:</div>
              <ul class="list-disc pl-5 space-y-1 text-slate-600">
                <li>Automated rule-based discovery against connected Source and Target endpoints</li>
                <li>Provider-aware identifier equivalence and explicit operator target selection</li>
                <li>Full comparison unit inspection, scope customization, and secondary column mapping</li>
              </ul>
            </div>

            <div class="flex items-center justify-center gap-3 pt-2">
              <button
                type="button"
                (click)="setPathway('CHOICE')"
                class="h-8 px-4 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white border border-slate-200 hover:bg-slate-50 rounded-md cursor-pointer transition-colors">
                Back to Options
              </button>
              <button
                type="button"
                (click)="setPathway('DEFINE')"
                class="h-8 px-4 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs">
                <span>Define Correspondence Instead</span>
                <app-lucide-icon name="arrow-right" [size]="13"></app-lucide-icon>
              </button>
            </div>
          </div>
        }

        <!-- ======================================================================= -->
        <!-- STATE 3: DEFINE CORRESPONDENCE (Scope-Level Rule Evaluator & Workbench) -->
        <!-- ======================================================================= -->
        @if (currentPathway() === 'DEFINE') {
          <div class="space-y-5">
            
            <!-- Correspondence Rules & Scope Selectors Card -->
            <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-2xs space-y-4">
              <div class="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-3">
                <div class="flex items-center gap-2.5">
                  <div class="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center shrink-0">
                    <app-lucide-icon name="sliders-horizontal" [size]="16"></app-lucide-icon>
                  </div>
                  <div>
                    <h2 class="text-sm font-bold text-slate-900">Define Scope &amp; Correspondence Rule</h2>
                    <p class="text-xs text-slate-500 font-normal">
                      Select discovered catalog namespaces and apply a canonical correspondence rule to establish Target counterparts.
                    </p>
                  </div>
                </div>

                <div class="flex items-center gap-2">
                  <button
                    type="button"
                    (click)="openCustomizeModal()"
                    class="h-8 px-3 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-md flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs">
                    <app-lucide-icon name="sliders-horizontal" [size]="13" class="text-slate-500"></app-lucide-icon>
                    <span>Customize Scope</span>
                  </button>
                  <button
                    type="button"
                    (click)="openInspectDrawer()"
                    class="h-8 px-3 text-xs font-semibold text-blue-700 bg-blue-50/80 border border-blue-200 hover:bg-blue-100/70 rounded-md flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs">
                    <app-lucide-icon name="eye" [size]="13" class="text-blue-600"></app-lucide-icon>
                    <span>Inspect Scope</span>
                  </button>
                </div>
              </div>

              <!-- Selectors Grid -->
              <div class="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
                <!-- Source Scope Selector -->
                <div class="space-y-1.5">
                  <label class="text-[11px] font-bold uppercase tracking-wider text-slate-600">Source Namespace</label>
                  <app-custom-select
                    [options]="sourceNamespaceOptions"
                    [value]="selectedSourceNamespace()"
                    (valueChange)="onSourceNamespaceChange($event)"
                    placeholder="Select Source Namespace...">
                  </app-custom-select>
                </div>

                <!-- Target Scope Selector -->
                <div class="space-y-1.5">
                  <label class="text-[11px] font-bold uppercase tracking-wider text-slate-600">Target Namespace</label>
                  <app-custom-select
                    [options]="targetNamespaceOptions"
                    [value]="selectedTargetNamespace()"
                    (valueChange)="onTargetNamespaceChange($event)"
                    placeholder="Select Target Namespace...">
                  </app-custom-select>
                </div>

                <!-- Correspondence Rule Selector -->
                <div class="space-y-1.5">
                  <label class="text-[11px] font-bold uppercase tracking-wider text-slate-600">Correspondence Rule</label>
                  <app-custom-select
                    [options]="correspondenceRuleOptions"
                    [value]="selectedCorrespondenceRule()"
                    (valueChange)="onCorrespondenceRuleChange($event)"
                    placeholder="Select Correspondence Rule...">
                  </app-custom-select>
                </div>
              </div>

              <!-- Rule Evaluation Note -->
              <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-600 leading-relaxed font-normal flex items-start gap-2">
                <app-lucide-icon name="info" [size]="14" class="text-blue-600 shrink-0 mt-0.5"></app-lucide-icon>
                <span>
                  <strong class="font-semibold text-slate-800">Rule Boundary:</strong>
                  Correspondence rules evaluate canonical catalog metadata. Objects without unambiguous matches are surfaced in Decisions Required below for explicit operator intent.
                </span>
              </div>
            </div>

            <!-- Decisions Required Workbench (Exception-Driven) -->
            @if (decisionsRequiredCount() > 0) {
              <div class="bg-white border border-amber-200 rounded-xl p-5 shadow-2xs space-y-4">
                <div class="flex items-center justify-between pb-3 border-b border-amber-100 flex-wrap gap-3">
                  <div class="flex items-center gap-2.5">
                    <div class="w-8 h-8 rounded-lg bg-amber-50 border border-amber-200 text-amber-600 flex items-center justify-center shrink-0">
                      <app-lucide-icon name="alert-circle" [size]="16"></app-lucide-icon>
                    </div>
                    <div>
                      <h2 class="text-sm font-bold text-slate-900">
                        Decisions Required ({{ decisionsRequiredCount() }} unmapped comparison unit)
                      </h2>
                      <p class="text-xs text-slate-500 font-normal">
                        Angular does not guess ambiguous correspondence. Choose the intended target counterpart or exclude from validation scope.
                      </p>
                    </div>
                  </div>

                  <span class="px-2.5 py-1 rounded bg-amber-50 text-amber-800 border border-amber-200 text-xs font-bold">
                    Action Required
                  </span>
                </div>

                <!-- Decision Items List -->
                <div class="space-y-3">
                  @for (d of decisionsList(); track d.unitId) {
                    <div class="p-4 bg-amber-50/40 border border-amber-200/80 rounded-lg flex items-center justify-between flex-wrap gap-4 text-xs">
                      <div class="space-y-1">
                        <div class="flex items-center gap-2">
                          <span class="font-mono font-bold text-slate-900 text-xs">{{ d.sourceNamespace }}.{{ d.sourceName }}</span>
                          <span class="px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200 text-[10px] font-mono">
                            {{ d.sourceKeyFact }}
                          </span>
                          <span class="text-slate-500 font-mono">{{ d.sourceVolumeFact }}</span>
                        </div>
                        <div class="text-slate-600 font-normal">
                          Issue: <span class="text-amber-900 font-medium">{{ d.issue }}</span>
                        </div>
                      </div>

                      <div class="flex items-center gap-2.5">
                        <!-- Select Target Counterpart using CustomSelect -->
                        <div class="w-64">
                          <app-custom-select
                            size="sm"
                            [options]="getDecisionCandidateOptions(d)"
                            [value]="d.selectedTarget || ''"
                            (valueChange)="onSelectDecisionTargetCustom(d.unitId, $event)"
                            placeholder="Select target counterpart...">
                          </app-custom-select>
                        </div>

                        <!-- Exclude from Scope -->
                        <button
                          type="button"
                          (click)="excludeDecisionUnit(d.unitId)"
                          class="h-7 px-3 text-xs font-medium text-slate-600 hover:text-slate-900 bg-white border border-slate-200 hover:bg-slate-50 rounded cursor-pointer transition-colors shadow-2xs"
                          title="Exclude this table from validation scope">
                          Exclude from Scope
                        </button>
                      </div>
                    </div>
                  }
                </div>

                <!-- Any previously resolved operator decisions while some are still pending -->
                @if (operatorDecisions().length > 0) {
                  <div class="pt-3 border-t border-amber-200/60 space-y-2">
                    <div class="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                      Resolved Decisions ({{ operatorDecisions().length }})
                    </div>
                    @for (u of operatorDecisions(); track u.id) {
                      <div class="p-3 bg-white border border-slate-200 rounded-lg flex items-center justify-between flex-wrap gap-3 text-xs">
                        <div class="flex items-center gap-2.5">
                          <app-lucide-icon name="check" [size]="14" class="text-emerald-600 shrink-0"></app-lucide-icon>
                          <div class="flex items-center gap-2 font-mono">
                            <span class="font-bold text-slate-900">{{ u.sourceNamespace }}.{{ u.sourceName }}</span>
                            <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400"></app-lucide-icon>
                            @if (u.disposition === 'EXCLUDED') {
                              <span class="text-slate-500 italic font-sans">Excluded from Scope</span>
                            } @else {
                              <span class="font-bold text-blue-700">{{ u.expectedTargetNamespace || 'public' }}.{{ u.expectedTargetName }}</span>
                            }
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200 font-sans">
                              {{ u.provenanceBasis || 'Operator Selected' }}
                            </span>
                          </div>
                        </div>

                        <button
                          type="button"
                          (click)="reopenDecision(u.id)"
                          class="h-7 px-3 text-xs font-semibold text-slate-700 hover:text-blue-700 bg-white border border-slate-200 hover:border-blue-300 hover:bg-blue-50/50 rounded-md flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs"
                          title="Change target counterpart or exclusion for this unit">
                          <app-lucide-icon name="rotate-ccw" [size]="12" class="text-slate-500"></app-lucide-icon>
                          <span>Change Decision</span>
                        </button>
                      </div>
                    }
                  </div>
                }
              </div>
            } @else {
              <!-- All Mapped Confirmation Surface (with Operator Decisions & Change Decision buttons) -->
              <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-2xs space-y-4">
                <div class="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-3">
                  <div class="flex items-center gap-2.5 text-xs text-slate-700">
                    <app-lucide-icon name="check-circle" [size]="16" class="text-emerald-600 shrink-0"></app-lucide-icon>
                    <div>
                      <h2 class="text-sm font-bold text-slate-900">All Target Correspondences Established</h2>
                      <p class="text-xs text-slate-500 font-normal">
                        All <strong class="text-slate-900 font-mono">{{ includedUnitsCount() }}</strong> comparison units have confirmed target counterparts. No operator decisions required.
                      </p>
                    </div>
                  </div>
                  <span class="px-2.5 py-1 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-bold">
                    Ready to Validate
                  </span>
                </div>

                @if (operatorDecisions().length > 0) {
                  <div class="space-y-2 pt-1">
                    <div class="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                      Operator Decisions ({{ operatorDecisions().length }})
                    </div>
                    @for (u of operatorDecisions(); track u.id) {
                      <div class="p-3 bg-slate-50/80 border border-slate-200 rounded-lg flex items-center justify-between flex-wrap gap-3 text-xs">
                        <div class="flex items-center gap-2.5">
                          <app-lucide-icon name="check" [size]="14" class="text-emerald-600 shrink-0"></app-lucide-icon>
                          <div class="flex items-center gap-2 font-mono">
                            <span class="font-bold text-slate-900">{{ u.sourceNamespace }}.{{ u.sourceName }}</span>
                            <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400"></app-lucide-icon>
                            @if (u.disposition === 'EXCLUDED') {
                              <span class="text-slate-500 italic font-sans">Excluded from Scope</span>
                            } @else {
                              <span class="font-bold text-blue-700">{{ u.expectedTargetNamespace || 'public' }}.{{ u.expectedTargetName }}</span>
                            }
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200 font-sans">
                              {{ u.provenanceBasis || 'Operator Selected' }}
                            </span>
                          </div>
                        </div>

                        <button
                          type="button"
                          (click)="reopenDecision(u.id)"
                          class="h-7 px-3 text-xs font-semibold text-slate-700 hover:text-blue-700 bg-white border border-slate-200 hover:border-blue-300 hover:bg-blue-50/50 rounded-md flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs"
                          title="Change target counterpart or exclusion for this unit">
                          <app-lucide-icon name="rotate-ccw" [size]="12" class="text-slate-500"></app-lucide-icon>
                          <span>Change Decision</span>
                        </button>
                      </div>
                    }
                  </div>
                }
              </div>
            }

          </div>
        }

      }

      <!-- ========================================================================= -->
      <!-- OVERLAYS: 1. CUSTOMIZE SCOPE MODAL                                        -->
      <!-- ========================================================================= -->
      @if (isCustomizeModalOpen()) {
        <div
          role="dialog"
          aria-modal="true"
          class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 !m-0 animate-in fade-in duration-100"
          (click)="closeCustomizeModal()">
          <div
            class="w-full max-w-2xl rounded-xl bg-white border border-slate-200 shadow-xl overflow-hidden flex flex-col max-h-[85vh]"
            (click)="$event.stopPropagation()">
            
            <!-- Modal Header -->
            <div class="px-6 py-4 border-b border-slate-200 flex items-center justify-between shrink-0">
              <div class="space-y-0.5">
                <h3 class="text-sm font-bold text-slate-900">Customize Comparison Scope</h3>
                <p class="text-xs text-slate-500 font-normal">
                  Include or exclude specific schemas and comparison units from this validation mission.
                </p>
              </div>
              <button
                type="button"
                (click)="closeCustomizeModal()"
                class="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100 cursor-pointer transition-colors">
                <app-lucide-icon name="x" [size]="16"></app-lucide-icon>
              </button>
            </div>

            <!-- Modal Search & Filter Strip -->
            <div class="px-6 py-3 border-b border-slate-100 bg-slate-50/70 flex items-center justify-between gap-4 flex-wrap shrink-0">
              <div class="relative flex-1 min-w-[200px]">
                <input
                  type="text"
                  [(ngModel)]="customizeSearchQuery"
                  placeholder="Filter comparison units..."
                  class="w-full h-8 pl-8 pr-3 text-xs bg-white border border-slate-200 focus:border-blue-600 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none" />
                <app-lucide-icon name="search" [size]="13" class="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400"></app-lucide-icon>
              </div>

              <div class="flex items-center gap-2">
                <button
                  type="button"
                  (click)="selectAllCustomUnits()"
                  class="text-xs text-blue-600 hover:text-blue-800 font-medium cursor-pointer">
                  Select All
                </button>
                <span class="text-slate-300">&middot;</span>
                <button
                  type="button"
                  (click)="deselectAllCustomUnits()"
                  class="text-xs text-slate-600 hover:text-slate-900 font-medium cursor-pointer">
                  Deselect All
                </button>
              </div>
            </div>

            <!-- Modal Units List -->
            <div class="flex-1 overflow-y-auto px-6 py-3 divide-y divide-slate-100">
              @for (u of filteredCustomizeUnits(); track u.id) {
                <div class="py-2.5 flex items-center justify-between gap-3 text-xs">
                  <label class="flex items-center gap-3 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      [checked]="u.disposition === 'INCLUDED'"
                      (change)="toggleUnitDisposition(u.id)"
                      class="rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer" />
                    <div>
                      <div class="font-mono font-bold text-slate-900">{{ u.sourceNamespace }}.{{ u.sourceName }}</div>
                      <div class="text-[11px] text-slate-500 font-normal">
                        Expected Target: <span class="font-mono text-slate-700">{{ u.expectedTargetNamespace || 'public' }}.{{ u.expectedTargetName || '—' }}</span>
                      </div>
                    </div>
                  </label>

                  <div class="flex items-center gap-3 text-right">
                    <div class="text-[11px] text-slate-500 font-mono">{{ u.sourceVolumeFact }}</div>
                    @if (u.disposition === 'INCLUDED') {
                      <span class="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-bold">
                        INCLUDED
                      </span>
                    } @else {
                      <span class="px-2 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200 text-[10px] font-medium">
                        EXCLUDED
                      </span>
                    }
                  </div>
                </div>
              }
            </div>

            <!-- Modal Footer -->
            <div class="px-6 py-3.5 border-t border-slate-200 bg-slate-50 flex items-center justify-between shrink-0">
              <div class="text-xs text-slate-600">
                Included: <strong class="font-mono text-slate-900">{{ includedUnitsCount() }}</strong> of <span class="font-mono">{{ units().length }}</span> comparison units
              </div>
              <div class="flex items-center gap-2.5">
                <button
                  type="button"
                  (click)="closeCustomizeModal()"
                  class="h-8 px-4 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-md cursor-pointer transition-colors shadow-2xs">
                  Done
                </button>
              </div>
            </div>

          </div>
        </div>
      }

      <!-- ========================================================================= -->
      <!-- OVERLAYS: 2. INSPECT SCOPE DRAWER (Slide-over Right Panel)               -->
      <!-- ========================================================================= -->
      @if (isInspectDrawerOpen()) {
        <div
          role="dialog"
          aria-modal="true"
          class="fixed inset-0 z-50 flex justify-end bg-slate-900/40 backdrop-blur-xs !m-0"
          (click)="closeInspectDrawer()">
          <div
            class="w-full max-w-3xl bg-white border-l border-slate-200 shadow-2xl h-full flex flex-col"
            (click)="$event.stopPropagation()">
            
            @if (activeColumnDrawerPair(); as activePair) {
              <!-- ================================================================= -->
              <!-- VIEW B: COLUMN CORRESPONDENCE DETAIL VIEW (Premium Enterprise)    -->
              <!-- ================================================================= -->
              <!-- Top Navigation Header -->
              <div class="px-6 py-4 border-b border-slate-200 flex items-center justify-between shrink-0 bg-slate-50">
                <button
                  type="button"
                  (click)="closeColumnDrawer()"
                  class="flex items-center gap-2 text-xs font-semibold text-blue-600 hover:text-blue-800 cursor-pointer transition-colors">
                  <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
                  <span>Back to Scope Manifest</span>
                </button>
                <button
                  type="button"
                  (click)="closeInspectDrawer(); closeColumnDrawer()"
                  class="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100 cursor-pointer transition-colors">
                  <app-lucide-icon name="x" [size]="16"></app-lucide-icon>
                </button>
              </div>

              <!-- Title & Operational Factual Badges -->
              <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between flex-wrap gap-3 shrink-0">
                <div class="space-y-0.5">
                  <div class="flex items-center gap-2">
                    <span class="font-mono font-bold text-slate-900 text-sm">
                      {{ activePair.sourceNamespace }}.{{ activePair.sourceName }}
                    </span>
                    <app-lucide-icon name="arrow-right" [size]="13" class="text-slate-400"></app-lucide-icon>
                    <span class="font-mono font-bold text-blue-700 text-sm">
                      {{ activePair.expectedTargetNamespace || 'public' }}.{{ activePair.expectedTargetName || '—' }}
                    </span>
                  </div>
                  <p class="text-xs text-slate-500 font-normal">
                    Read-only structural column correspondence proof. Verifies operand types ahead of strategy selection.
                  </p>
                </div>
                <div class="flex items-center gap-2">
                  <span class="px-2.5 py-1 rounded bg-blue-50 text-blue-700 border border-blue-200 text-xs font-bold">
                    {{ (activePair.columns || defaultColumnsForPair(activePair)).length }} Columns
                  </span>
                  <span class="px-2.5 py-1 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold flex items-center gap-1">
                    <app-lucide-icon name="key" [size]="11"></app-lucide-icon>
                    <span>1 PK</span>
                  </span>
                  <span class="px-2.5 py-1 rounded bg-slate-100 text-slate-700 border border-slate-200 text-xs font-mono">
                    Read-Only
                  </span>
                </div>
              </div>

              <!-- Column Filter Search Bar -->
              <div class="px-6 py-2.5 border-b border-slate-100 bg-slate-50/70 flex items-center justify-between gap-3 shrink-0">
                <div class="relative flex-1">
                  <input
                    type="text"
                    [ngModel]="columnSearchQuery()"
                    (ngModelChange)="columnSearchQuery.set($event)"
                    placeholder="Search columns or data types (e.g. ID, name, varchar)..."
                    class="w-full h-8 pl-8 pr-3 text-xs bg-white border border-slate-200 focus:border-blue-600 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none" />
                  <app-lucide-icon name="search" [size]="13" class="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400"></app-lucide-icon>
                </div>
              </div>

              <!-- Column Detail Table Container -->
              <div class="flex-1 overflow-y-auto p-6">
                <div class="border border-slate-200 rounded-xl overflow-hidden shadow-2xs bg-white">
                  <table class="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr class="border-b border-slate-200 bg-slate-50/90 text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                        <th class="py-2.5 px-4">
                          <div class="flex items-center gap-1.5">
                            <app-lucide-icon [name]="getProviderIcon(sourceProvider())" [size]="13" class="text-blue-600"></app-lucide-icon>
                            <span>Source Column ({{ sourceProvider() }})</span>
                          </div>
                        </th>
                        <th class="py-2.5 px-2 text-center w-10"></th>
                        <th class="py-2.5 px-4">
                          <div class="flex items-center gap-1.5">
                            <app-lucide-icon [name]="getProviderIcon(targetProvider())" [size]="13" class="text-emerald-600"></app-lucide-icon>
                            <span>Target Column ({{ targetProvider() }})</span>
                          </div>
                        </th>
                        <th class="py-2.5 px-4 text-center">Mapping</th>
                        <th class="py-2.5 px-4 text-right">Key Attribute</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100 font-mono">
                      @for (col of filteredColumns(); track col.sourceColumn) {
                        <tr class="hover:bg-slate-50/70 transition-colors">
                          <td class="py-3 px-4">
                            <div class="font-bold text-slate-900 text-xs">{{ col.sourceColumn }}</div>
                            <div class="text-[10px] text-slate-500 font-sans mt-0.5">
                              <span class="px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200 font-mono">{{ col.sourceType }}</span>
                            </div>
                          </td>
                          <td class="py-3 px-2 text-center">
                            <div class="w-5 h-5 rounded-md bg-blue-50 text-blue-600 flex items-center justify-center mx-auto">
                              <app-lucide-icon name="arrow-right" [size]="11"></app-lucide-icon>
                            </div>
                          </td>
                          <td class="py-3 px-4">
                            <div class="font-bold text-slate-900 text-xs">{{ col.targetColumn }}</div>
                            <div class="text-[10px] text-slate-500 font-sans mt-0.5">
                              <span class="px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200 font-mono">{{ col.targetType }}</span>
                            </div>
                          </td>
                          <td class="py-3 px-4 text-center font-sans">
                            <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                              Equivalent
                            </span>
                          </td>
                          <td class="py-3 px-4 text-right font-sans">
                            @if (col.isPrimaryKey) {
                              <span class="px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 text-[10px] font-bold inline-flex items-center gap-1">
                                <app-lucide-icon name="key" [size]="10"></app-lucide-icon>
                                <span>PK</span>
                              </span>
                            } @else {
                              <span class="text-slate-400 text-xs font-mono">&mdash;</span>
                            }
                          </td>
                        </tr>
                      }
                      @if (filteredColumns().length === 0) {
                        <tr>
                          <td colspan="5" class="py-8 text-center text-slate-400 text-xs font-sans">
                            No columns match "{{ columnSearchQuery() }}"
                          </td>
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
              </div>

              <!-- Footer -->
              <div class="px-6 py-3.5 border-t border-slate-200 bg-slate-50 flex items-center justify-between shrink-0">
                <div class="text-xs text-slate-500 font-normal">
                  Validation proves column alignment at execution runtime. Zero schema mutation.
                </div>
                <button
                  type="button"
                  (click)="closeColumnDrawer()"
                  class="h-8 px-4 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-md cursor-pointer transition-colors shadow-2xs">
                  Back to Scope Manifest
                </button>
              </div>

            } @else {
              <!-- ================================================================= -->
              <!-- VIEW A: SCOPE MANIFEST TABLE VIEW                                 -->
              <!-- ================================================================= -->
              <!-- Drawer Header -->
              <div class="px-6 py-4 border-b border-slate-200 flex items-center justify-between shrink-0">
                <div class="space-y-0.5">
                  <h3 class="text-sm font-bold text-slate-900">Scope Manifest &amp; Correspondence Inspection</h3>
                  <p class="text-xs text-slate-500 font-normal">
                    Inspect comparison units, counterpart mappings, provenance, and physical observations.
                  </p>
                </div>
                <button
                  type="button"
                  (click)="closeInspectDrawer()"
                  class="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100 cursor-pointer transition-colors">
                  <app-lucide-icon name="x" [size]="16"></app-lucide-icon>
                </button>
              </div>

              <!-- Drawer Filter Bar -->
              <div class="px-6 py-3 border-b border-slate-100 bg-slate-50 flex items-center justify-between gap-4 flex-wrap shrink-0">
                <div class="relative flex-1 min-w-[200px]">
                  <input
                    type="text"
                    [(ngModel)]="inspectSearchQuery"
                    placeholder="Filter manifest by table name..."
                    class="w-full h-8 pl-8 pr-3 text-xs bg-white border border-slate-200 focus:border-blue-600 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none" />
                  <app-lucide-icon name="search" [size]="13" class="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400"></app-lucide-icon>
                </div>

                <!-- Filter Tabs -->
                <div class="flex items-center gap-1.5">
                  <button
                    type="button"
                    (click)="inspectStatusFilter = 'ALL'"
                    class="px-2.5 py-1 rounded text-[11px] font-medium transition-colors cursor-pointer border"
                    [class]="inspectStatusFilter === 'ALL' ? 'bg-white text-slate-900 border-slate-300 font-bold shadow-2xs' : 'text-slate-600 border-transparent hover:bg-slate-200/60'">
                    All ({{ units().length }})
                  </button>
                  <button
                    type="button"
                    (click)="inspectStatusFilter = 'DISCOVERED'"
                    class="px-2.5 py-1 rounded text-[11px] font-medium transition-colors cursor-pointer border"
                    [class]="inspectStatusFilter === 'DISCOVERED' ? 'bg-white text-slate-900 border-slate-300 font-bold shadow-2xs' : 'text-slate-600 border-transparent hover:bg-slate-200/60'">
                    Discovered ({{ discoveredTargetsCount() }})
                  </button>
                  @if (notDiscoveredTargetsCount() > 0) {
                    <button
                      type="button"
                      (click)="inspectStatusFilter = 'NOT_DISCOVERED'"
                      class="px-2.5 py-1 rounded text-[11px] font-medium transition-colors cursor-pointer border"
                      [class]="inspectStatusFilter === 'NOT_DISCOVERED' ? 'bg-white text-slate-900 border-slate-300 font-bold shadow-2xs' : 'text-slate-600 border-transparent hover:bg-slate-200/60'">
                      Not Discovered ({{ notDiscoveredTargetsCount() }})
                    </button>
                  }
                </div>
              </div>

              <!-- Drawer Table Content -->
              <div class="flex-1 overflow-y-auto">
                <table class="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr class="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                      <th class="py-2.5 px-4">Source Unit</th>
                      <th class="py-2.5 px-4">Expected Target</th>
                      <th class="py-2.5 px-4">Provenance</th>
                      <th class="py-2.5 px-4">Observation</th>
                      <th class="py-2.5 px-4 text-right">Details</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-slate-100 font-sans">
                    @for (u of filteredInspectUnits(); track u.id) {
                      <tr class="hover:bg-slate-50/70 transition-colors">
                        <!-- Source Unit -->
                        <td class="py-3 px-4">
                          <div class="font-mono font-bold text-slate-900">{{ u.sourceNamespace }}.{{ u.sourceName }}</div>
                          <div class="text-[11px] text-slate-500 font-mono">{{ u.sourceKeyFact }}</div>
                        </td>

                        <!-- Expected Target -->
                        <td class="py-3 px-4">
                          @if (u.expectedTargetName) {
                            <div class="font-mono font-bold text-slate-900">{{ u.expectedTargetNamespace || 'public' }}.{{ u.expectedTargetName }}</div>
                            <div class="text-[11px] text-slate-500 font-mono">{{ u.expectedTargetKeyFact || 'PK matched' }}</div>
                          } @else {
                            <span class="text-slate-400 italic">Unassigned</span>
                          }
                        </td>

                        <!-- Provenance -->
                        <td class="py-3 px-4">
                          <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
                            {{ u.provenanceBasis }}
                          </span>
                        </td>

                        <!-- Observation Status -->
                        <td class="py-3 px-4">
                          @if (u.observationStatus === 'DISCOVERED') {
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1 w-fit">
                              <app-lucide-icon name="check" [size]="10"></app-lucide-icon>
                              <span>Discovered</span>
                            </span>
                          } @else if (u.observationStatus === 'NOT_DISCOVERED') {
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200 flex items-center gap-1 w-fit" title="Physically absent from target catalog; will be tested at runtime">
                              <app-lucide-icon name="alert-circle" [size]="10"></app-lucide-icon>
                              <span>Not Discovered</span>
                            </span>
                          } @else {
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-600 border border-slate-200">
                              Unavailable
                            </span>
                          }
                        </td>

                        <!-- Details & Change Decision Actions -->
                        <td class="py-3 px-4 text-right">
                          <div class="flex items-center justify-end gap-1.5">
                            @if (u.provenance === 'OPERATOR_DEFINED' || u.provenanceBasis === 'Operator Selected') {
                              <button
                                type="button"
                                (click)="reopenDecision(u.id); closeInspectDrawer()"
                                class="h-7 px-2 text-[11px] font-semibold text-slate-700 hover:text-blue-700 bg-white hover:bg-blue-50 border border-slate-200 hover:border-blue-300 rounded cursor-pointer transition-colors flex items-center gap-1"
                                title="Change target counterpart decision">
                                <app-lucide-icon name="rotate-ccw" [size]="11"></app-lucide-icon>
                                <span>Change</span>
                              </button>
                            }
                            <button
                              type="button"
                              (click)="openColumnDrawer(u)"
                              class="h-7 px-2.5 text-xs font-semibold text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded cursor-pointer transition-colors"
                              title="View secondary column correspondences">
                              Columns
                            </button>
                          </div>
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>

              <!-- Drawer Footer -->
              <div class="px-6 py-3.5 border-t border-slate-200 bg-slate-50/70 flex items-center justify-between shrink-0">
                <div class="text-xs text-slate-600 font-mono">
                  Showing {{ filteredInspectUnits().length }} of {{ units().length }} units
                </div>
                <button
                  type="button"
                  (click)="closeInspectDrawer()"
                  class="h-8 px-4 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-md cursor-pointer transition-colors shadow-2xs">
                  Close Manifest
                </button>
              </div>
            }

          </div>
        </div>
      }

      <!-- ========================================================================= -->
      <!-- OVERLAYS: 3. STANDALONE COLUMN CORRESPONDENCE DRAWER                      -->
      <!-- ========================================================================= -->
      @if (activeColumnDrawerPair() && !isInspectDrawerOpen()) {
        <div
          role="dialog"
          aria-modal="true"
          class="fixed inset-0 z-50 flex justify-end bg-slate-900/40 backdrop-blur-xs !m-0"
          (click)="closeColumnDrawer()">
          <div
            class="w-full max-w-3xl bg-white border-l border-slate-200 shadow-2xl h-full flex flex-col"
            (click)="$event.stopPropagation()">
            
            <!-- Column Drawer Header -->
            <div class="px-6 py-4 border-b border-slate-200 flex items-center justify-between shrink-0 bg-slate-50">
              <div class="space-y-0.5">
                <div class="flex items-center gap-2">
                  <span class="font-mono font-bold text-slate-900 text-sm">
                    {{ activeColumnDrawerPair()?.sourceNamespace }}.{{ activeColumnDrawerPair()?.sourceName }}
                  </span>
                  <app-lucide-icon name="arrow-right" [size]="13" class="text-slate-400"></app-lucide-icon>
                  <span class="font-mono font-bold text-blue-700 text-sm">
                    {{ activeColumnDrawerPair()?.expectedTargetNamespace || 'public' }}.{{ activeColumnDrawerPair()?.expectedTargetName || '—' }}
                  </span>
                </div>
                <p class="text-xs text-slate-500 font-normal">
                  Read-only structural column correspondence proof. Verifies operand types ahead of strategy selection.
                </p>
              </div>
              <button
                type="button"
                (click)="closeColumnDrawer()"
                class="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100 cursor-pointer transition-colors">
                <app-lucide-icon name="x" [size]="16"></app-lucide-icon>
              </button>
            </div>

            <!-- Operational Factual Badges & Filter -->
            <div class="px-6 py-3 border-b border-slate-100 flex items-center justify-between flex-wrap gap-3 shrink-0">
              <div class="relative flex-1 min-w-[200px]">
                <input
                  type="text"
                  [ngModel]="columnSearchQuery()"
                  (ngModelChange)="columnSearchQuery.set($event)"
                  placeholder="Search columns or data types..."
                  class="w-full h-8 pl-8 pr-3 text-xs bg-white border border-slate-200 focus:border-blue-600 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none" />
                <app-lucide-icon name="search" [size]="13" class="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400"></app-lucide-icon>
              </div>
              <div class="flex items-center gap-2">
                <span class="px-2.5 py-1 rounded bg-blue-50 text-blue-700 border border-blue-200 text-xs font-bold">
                  {{ (activeColumnDrawerPair()?.columns || defaultColumnsForPair(activeColumnDrawerPair()!)).length }} Columns
                </span>
                <span class="px-2.5 py-1 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold flex items-center gap-1">
                  <app-lucide-icon name="key" [size]="11"></app-lucide-icon>
                  <span>1 PK</span>
                </span>
              </div>
            </div>

            <!-- Column List Table Container -->
            <div class="flex-1 overflow-y-auto p-6">
              <div class="border border-slate-200 rounded-xl overflow-hidden shadow-2xs bg-white">
                <table class="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr class="border-b border-slate-200 bg-slate-50/90 text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                      <th class="py-2.5 px-4">
                        <div class="flex items-center gap-1.5">
                          <app-lucide-icon [name]="getProviderIcon(sourceProvider())" [size]="13" class="text-blue-600"></app-lucide-icon>
                          <span>Source Column ({{ sourceProvider() }})</span>
                        </div>
                      </th>
                      <th class="py-2.5 px-2 text-center w-10"></th>
                      <th class="py-2.5 px-4">
                        <div class="flex items-center gap-1.5">
                          <app-lucide-icon [name]="getProviderIcon(targetProvider())" [size]="13" class="text-emerald-600"></app-lucide-icon>
                          <span>Target Column ({{ targetProvider() }})</span>
                        </div>
                      </th>
                      <th class="py-2.5 px-4 text-center">Mapping</th>
                      <th class="py-2.5 px-4 text-right">Key Attribute</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-slate-100 font-mono">
                    @for (col of filteredColumns(); track col.sourceColumn) {
                      <tr class="hover:bg-slate-50/70 transition-colors">
                        <td class="py-3 px-4">
                          <div class="font-bold text-slate-900 text-xs">{{ col.sourceColumn }}</div>
                          <div class="text-[10px] text-slate-500 font-sans mt-0.5">
                            <span class="px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200 font-mono">{{ col.sourceType }}</span>
                          </div>
                        </td>
                        <td class="py-3 px-2 text-center">
                          <div class="w-5 h-5 rounded-md bg-blue-50 text-blue-600 flex items-center justify-center mx-auto">
                            <app-lucide-icon name="arrow-right" [size]="11"></app-lucide-icon>
                          </div>
                        </td>
                        <td class="py-3 px-4">
                          <div class="font-bold text-slate-900 text-xs">{{ col.targetColumn }}</div>
                          <div class="text-[10px] text-slate-500 font-sans mt-0.5">
                            <span class="px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200 font-mono">{{ col.targetType }}</span>
                          </div>
                        </td>
                        <td class="py-3 px-4 text-center font-sans">
                          <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            Equivalent
                          </span>
                        </td>
                        <td class="py-3 px-4 text-right font-sans">
                          @if (col.isPrimaryKey) {
                            <span class="px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 text-[10px] font-bold inline-flex items-center gap-1">
                              <app-lucide-icon name="key" [size]="10"></app-lucide-icon>
                              <span>PK</span>
                            </span>
                          } @else {
                            <span class="text-slate-400 text-xs font-mono">&mdash;</span>
                          }
                        </td>
                      </tr>
                    }
                    @if (filteredColumns().length === 0) {
                      <tr>
                        <td colspan="5" class="py-8 text-center text-slate-400 text-xs font-sans">
                          No columns match "{{ columnSearchQuery() }}"
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Footer -->
            <div class="px-6 py-3.5 border-t border-slate-200 bg-slate-50 flex items-center justify-between shrink-0">
              <div class="text-xs text-slate-500 font-normal">
                Validation proves column alignment at execution runtime. Zero schema mutation.
              </div>
              <button
                type="button"
                (click)="closeColumnDrawer()"
                class="h-8 px-4 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-md cursor-pointer transition-colors shadow-2xs">
                Close
              </button>
            </div>

          </div>
        </div>
      }

    </div>
  `
})
export class Step4ScopeComponent implements OnInit {
  public vs: ValidationUiService;

  // Pathway signals
  public currentPathway = computed<Step4Pathway>(() => {
    const draft = this.vs.newValidationDraft();
    if (draft.validationContext === 'EXISTING_PROJECT') {
      return 'INHERIT';
    }
    return draft.step4Pathway || 'CHOICE';
  });

  // Comparison Units signal
  public units = computed<ComparisonUnit[]>(() => {
    const draft = this.vs.newValidationDraft();
    if (draft.comparisonUnits && draft.comparisonUnits.length > 0) {
      return draft.comparisonUnits;
    }
    if (draft.scopedPairs && draft.scopedPairs.length > 0) {
      return draft.scopedPairs;
    }
    return [];
  });

  // State signals
  public isRefreshing = signal<boolean>(false);
  public isCustomizeModalOpen = signal<boolean>(false);
  public isInspectDrawerOpen = signal<boolean>(false);
  public activeColumnDrawerPair = signal<ComparisonUnit | null>(null);

  // Search & Filters for Overlays
  public customizeSearchQuery: string = '';
  public inspectSearchQuery: string = '';
  public inspectStatusFilter = 'ALL';

  // Rule & Scope selections for Pathway C
  public selectedSourceNamespace = signal<string>('ALL');
  public selectedTargetNamespace = signal<string>('public');
  public selectedCorrespondenceRule = signal<string>('EXACT_IDENTIFIER_MATCH');

  // Custom select options matching steps 1-3
  public sourceNamespaceOptions: CustomSelectOption[] = [
    { label: 'All Discovered Schemas (FINANCE, HR)', value: 'ALL', badge: '13 tables', icon: 'database' },
    { label: 'FINANCE', value: 'FINANCE', badge: '9 tables', desc: 'Core ledger, accounts and transactions', icon: 'table' },
    { label: 'HR', value: 'HR', badge: '4 tables', desc: 'Employee, department and salary records', icon: 'table' }
  ];

  public targetNamespaceOptions: CustomSelectOption[] = [
    { label: 'public', value: 'public', badge: 'default', desc: 'Target PostgreSQL default schema', icon: 'database' },
    { label: 'finance_target', value: 'finance_target', badge: 'isolated', desc: 'Dedicated validation target schema', icon: 'database' }
  ];

  public correspondenceRuleOptions: CustomSelectOption[] = [
    { label: 'Exact Identifier Match (Case-Insensitive)', value: 'EXACT_IDENTIFIER_MATCH', desc: 'Deterministic 1:1 identifier match across source and target', icon: 'check-check' },
    { label: 'Provider-Aware Equivalence (Oracle -> PG)', value: 'PROVIDER_AWARE_EQUIVALENCE', desc: 'Transforms Oracle uppercase identifiers to PostgreSQL lowercase', icon: 'shuffle' },
    { label: 'Target Schema Prefix Match', value: 'TARGET_SCHEMA_PREFIX', desc: 'Preserves source schema identifier as prefix on target namespace', icon: 'hash' }
  ];

  // Column search & filtered list
  public columnSearchQuery = signal<string>('');

  public filteredColumns = computed<ColumnCorrespondenceItem[]>(() => {
    const pair = this.activeColumnDrawerPair();
    if (!pair) return [];
    const allCols = pair.columns && pair.columns.length > 0 ? pair.columns : this.defaultColumnsForPair(pair);
    const q = this.columnSearchQuery().trim().toLowerCase();
    if (!q) return allCols;
    return allCols.filter(c =>
      c.sourceColumn.toLowerCase().includes(q) ||
      c.targetColumn.toLowerCase().includes(q) ||
      c.sourceType.toLowerCase().includes(q) ||
      c.targetType.toLowerCase().includes(q)
    );
  });

  // Operator resolved decisions tracker
  public operatorDecisions = computed<ComparisonUnit[]>(() => {
    return this.units().filter(u =>
      u.provenance === 'OPERATOR_DEFINED' ||
      u.provenanceBasis === 'Operator Selected' ||
      u.provenanceBasis === 'Operator Excluded' ||
      (u.previousDecisionReason && !u.isDecisionRequired)
    );
  });

  // Computed metrics
  public includedUnitsCount = computed<number>(() => {
    return this.units().filter(u => u.disposition !== 'EXCLUDED').length;
  });

  public discoveredTargetsCount = computed<number>(() => {
    return this.units().filter(u => u.disposition !== 'EXCLUDED' && u.observationStatus === 'DISCOVERED').length;
  });

  public notDiscoveredTargetsCount = computed<number>(() => {
    return this.units().filter(u => u.disposition !== 'EXCLUDED' && u.observationStatus === 'NOT_DISCOVERED').length;
  });

  public decisionsRequiredCount = computed<number>(() => {
    return this.units().filter(u => u.disposition !== 'EXCLUDED' && u.isDecisionRequired).length;
  });

  public uniqueSchemas = computed<string[]>(() => {
    const schemas = new Set<string>();
    this.units().forEach(u => {
      if (u.sourceNamespace) schemas.add(u.sourceNamespace);
    });
    return Array.from(schemas);
  });

  public executionSummary = computed<MigrationExecutionSummary>(() => {
    return {
      totalUnits: 303,
      completedUnits: 300,
      failedUnits: 2,
      inProgressUnits: 1,
      schemas: ['FINANCE', 'HR']
    };
  });

  public totalVolumeFormatted = computed<string>(() => {
    if (this.includedUnitsCount() === 0) return '';
    return '36.8M rows (estimate)';
  });

  // Filtered lists
  public filteredCustomizeUnits = computed<ComparisonUnit[]>(() => {
    const q = this.customizeSearchQuery.trim().toLowerCase();
    return this.units().filter(u => {
      if (!q) return true;
      return u.sourceName.toLowerCase().includes(q) || u.sourceNamespace.toLowerCase().includes(q);
    });
  });

  public filteredInspectUnits = computed<ComparisonUnit[]>(() => {
    const q = this.inspectSearchQuery.trim().toLowerCase();
    const filter = this.inspectStatusFilter;
    return this.units().filter(u => {
      if (filter === 'DISCOVERED' && u.observationStatus !== 'DISCOVERED') return false;
      if (filter === 'NOT_DISCOVERED' && u.observationStatus !== 'NOT_DISCOVERED') return false;
      if (!q) return true;
      return (
        u.sourceName.toLowerCase().includes(q) ||
        (u.expectedTargetName && u.expectedTargetName.toLowerCase().includes(q)) ||
        u.sourceNamespace.toLowerCase().includes(q)
      );
    });
  });

  public decisionsList = computed<OperatorDecisionItem[]>(() => {
    return this.units()
      .filter(u => u.disposition !== 'EXCLUDED' && u.isDecisionRequired)
      .map(u => ({
        unitId: u.id,
        sourceName: u.sourceName,
        sourceNamespace: u.sourceNamespace,
        sourceKeyFact: u.sourceKeyFact,
        sourceVolumeFact: u.sourceVolumeFact,
        issue: u.decisionReason || 'No exact counterpart found in target schema',
        selectedTarget: u.expectedTargetName || '',
        suggestedCandidates: [
          { id: 'cand-1', name: u.sourceName.toLowerCase(), namespace: 'public' },
          { id: 'cand-2', name: `${u.sourceName.toLowerCase()}_v2`, namespace: 'public' }
        ]
      }));
  });

  // Endpoints Context
  public sourceProvider = computed<PhysicalProviderId>(() => {
    return this.vs.newValidationDraft().sourceProvider || 'Oracle';
  });

  public targetProvider = computed<PhysicalProviderId>(() => {
    return this.vs.newValidationDraft().targetProvider || 'PostgreSQL';
  });

  public sourceEndpointLabel = computed<string>(() => {
    const draft = this.vs.newValidationDraft();
    if (draft.sourceHost) {
      return `${draft.sourceHost}:${draft.sourcePort || 1521} / ${draft.sourceDatabase || 'FINANCE'}`;
    }
    return 'prod-oracle-db.corp:1521 / FINANCE';
  });

  public targetEndpointLabel = computed<string>(() => {
    const draft = this.vs.newValidationDraft();
    if (draft.targetHost) {
      return `${draft.targetHost}:${draft.targetPort || 5432} / ${draft.targetDatabase || 'public'}`;
    }
    return 'aws-aurora-pg.corp:5432 / public';
  });

  constructor(vs?: ValidationUiService) {
    this.vs = vs || inject(ValidationUiService);
  }

  public ngOnInit(): void {
    const draft = this.vs.newValidationDraft();
    if (draft.validationContext === 'EXISTING_PROJECT') {
      this.initInheritedMigrationScope();
    } else if (draft.comparisonUnits && draft.comparisonUnits.length > 0) {
      // Already has units
    } else {
      // Independent default
      this.vs.updateDraft({ step4Pathway: draft.step4Pathway || 'CHOICE' });
    }
  }

  // ===========================================================================
  // PATHWAY NAVIGATION
  // ===========================================================================
  public setPathway(pathway: Step4Pathway): void {
    this.vs.updateDraft({ step4Pathway: pathway });
    if (pathway === 'DEFINE') {
      this.initCatalogDiscoveryScope();
    }
  }

  // ===========================================================================
  // INITIALIZERS
  // ===========================================================================
  public initInheritedMigrationScope(): void {
    const inherited: ComparisonUnit[] = [
      {
        id: 'unit-01',
        sourceId: 'src-01',
        sourceName: 'ACCOUNTS',
        sourceNamespace: 'FINANCE',
        sourceType: 'Table',
        sourceKeyFact: 'PK: ACC_ID',
        sourceVolumeFact: '1.2M rows',
        sourceEstimatedRows: 1200000,
        expectedTargetId: 'tgt-01',
        expectedTargetName: 'accounts',
        expectedTargetNamespace: 'public',
        expectedTargetType: 'Table',
        expectedTargetKeyFact: 'PK: acc_id',
        disposition: 'INCLUDED',
        provenance: 'MIGRATION_PLAN',
        provenanceBasis: 'Migration Plan: Graph Phase 2',
        observationStatus: 'DISCOVERED',
        isDecisionRequired: false,
        targetStatus: 'INHERITED_CONFIRMED',
        targetName: 'accounts',
        columns: [
          { sourceColumn: 'ACC_ID', sourceType: 'NUMBER(10)', targetColumn: 'acc_id', targetType: 'bigint', isPrimaryKey: true },
          { sourceColumn: 'ACC_NUMBER', sourceType: 'VARCHAR2(32)', targetColumn: 'acc_number', targetType: 'varchar(32)' },
          { sourceColumn: 'BALANCE', sourceType: 'NUMBER(18,2)', targetColumn: 'balance', targetType: 'numeric(18,2)' },
          { sourceColumn: 'STATUS', sourceType: 'VARCHAR2(16)', targetColumn: 'status', targetType: 'varchar(16)' },
          { sourceColumn: 'CREATED_AT', sourceType: 'TIMESTAMP', targetColumn: 'created_at', targetType: 'timestamptz' }
        ]
      },
      {
        id: 'unit-02',
        sourceId: 'src-02',
        sourceName: 'TRANSACTIONS',
        sourceNamespace: 'FINANCE',
        sourceType: 'Table',
        sourceKeyFact: 'PK: TX_ID',
        sourceVolumeFact: '18.6M rows',
        sourceEstimatedRows: 18600000,
        expectedTargetId: 'tgt-02',
        expectedTargetName: 'transactions',
        expectedTargetNamespace: 'public',
        expectedTargetType: 'Table',
        expectedTargetKeyFact: 'PK: tx_id',
        disposition: 'INCLUDED',
        provenance: 'MIGRATION_PLAN',
        provenanceBasis: 'Migration Plan: Graph Phase 2',
        observationStatus: 'DISCOVERED',
        isDecisionRequired: false,
        targetStatus: 'INHERITED_CONFIRMED',
        targetName: 'transactions',
        columns: [
          { sourceColumn: 'TX_ID', sourceType: 'NUMBER(12)', targetColumn: 'tx_id', targetType: 'bigint', isPrimaryKey: true },
          { sourceColumn: 'ACC_ID', sourceType: 'NUMBER(10)', targetColumn: 'acc_id', targetType: 'bigint' },
          { sourceColumn: 'AMOUNT', sourceType: 'NUMBER(18,2)', targetColumn: 'amount', targetType: 'numeric(18,2)' },
          { sourceColumn: 'TX_DATE', sourceType: 'TIMESTAMP', targetColumn: 'tx_date', targetType: 'timestamptz' }
        ]
      },
      {
        id: 'unit-03',
        sourceId: 'src-03',
        sourceName: 'CUSTOMERS',
        sourceNamespace: 'FINANCE',
        sourceType: 'Table',
        sourceKeyFact: 'PK: CUST_ID',
        sourceVolumeFact: '450,000 rows',
        sourceEstimatedRows: 450000,
        expectedTargetId: 'tgt-03',
        expectedTargetName: 'customers',
        expectedTargetNamespace: 'public',
        expectedTargetType: 'Table',
        expectedTargetKeyFact: 'PK: cust_id',
        disposition: 'INCLUDED',
        provenance: 'MIGRATION_PLAN',
        provenanceBasis: 'Migration Plan: Graph Phase 2',
        observationStatus: 'DISCOVERED',
        isDecisionRequired: false,
        targetStatus: 'INHERITED_CONFIRMED',
        targetName: 'customers'
      },
      {
        id: 'unit-04',
        sourceId: 'src-04',
        sourceName: 'LEDGER_ENTRIES',
        sourceNamespace: 'FINANCE',
        sourceType: 'Table',
        sourceKeyFact: 'PK: ENTRY_ID',
        sourceVolumeFact: '9.4M rows',
        sourceEstimatedRows: 9400000,
        expectedTargetId: 'tgt-04',
        expectedTargetName: 'ledger_entries',
        expectedTargetNamespace: 'public',
        expectedTargetType: 'Table',
        expectedTargetKeyFact: 'PK: entry_id',
        disposition: 'INCLUDED',
        provenance: 'MIGRATION_PLAN',
        provenanceBasis: 'Migration Plan: Graph Phase 2',
        observationStatus: 'DISCOVERED',
        isDecisionRequired: false,
        targetStatus: 'INHERITED_CONFIRMED',
        targetName: 'ledger_entries'
      },
      {
        id: 'unit-05',
        sourceId: 'src-05',
        sourceName: 'AUDIT_LOG_2025',
        sourceNamespace: 'FINANCE',
        sourceType: 'Table',
        sourceKeyFact: 'PK: LOG_ID',
        sourceVolumeFact: '2.1M rows',
        sourceEstimatedRows: 2100000,
        expectedTargetId: 'tgt-05',
        expectedTargetName: 'audit_log_2025',
        expectedTargetNamespace: 'public',
        expectedTargetType: 'Table',
        expectedTargetKeyFact: 'PK: log_id',
        disposition: 'INCLUDED',
        provenance: 'MIGRATION_PLAN',
        provenanceBasis: 'Migration Plan: Graph Phase 2',
        observationStatus: 'NOT_DISCOVERED', // Law 6 demonstration: Missing physically, stays in scope
        observationNote: 'Not discovered in target catalog; retained for runtime verification',
        isDecisionRequired: false,
        targetStatus: 'INHERITED_CONFIRMED',
        targetName: 'audit_log_2025'
      },
      {
        id: 'unit-06',
        sourceId: 'src-06',
        sourceName: 'PAYMENT_METHODS',
        sourceNamespace: 'FINANCE',
        sourceType: 'Table',
        sourceKeyFact: 'PK: PM_ID',
        sourceVolumeFact: '85,000 rows',
        sourceEstimatedRows: 85000,
        expectedTargetId: 'tgt-06',
        expectedTargetName: 'payment_methods',
        expectedTargetNamespace: 'public',
        expectedTargetType: 'Table',
        expectedTargetKeyFact: 'PK: pm_id',
        disposition: 'INCLUDED',
        provenance: 'MIGRATION_PLAN',
        provenanceBasis: 'Migration Plan: Graph Phase 2',
        observationStatus: 'DISCOVERED',
        isDecisionRequired: false,
        targetStatus: 'INHERITED_CONFIRMED',
        targetName: 'payment_methods'
      },
      {
        id: 'unit-07',
        sourceId: 'src-07',
        sourceName: 'INVOICES',
        sourceNamespace: 'FINANCE',
        sourceType: 'Table',
        sourceKeyFact: 'PK: INV_ID',
        sourceVolumeFact: '3.2M rows',
        sourceEstimatedRows: 3200000,
        expectedTargetId: 'tgt-07',
        expectedTargetName: 'invoices',
        expectedTargetNamespace: 'public',
        expectedTargetType: 'Table',
        expectedTargetKeyFact: 'PK: inv_id',
        disposition: 'INCLUDED',
        provenance: 'MIGRATION_PLAN',
        provenanceBasis: 'Migration Plan: Graph Phase 2',
        observationStatus: 'DISCOVERED',
        isDecisionRequired: false,
        targetStatus: 'INHERITED_CONFIRMED',
        targetName: 'invoices'
      },
      {
        id: 'unit-08',
        sourceId: 'src-08',
        sourceName: 'SETTLEMENTS',
        sourceNamespace: 'FINANCE',
        sourceType: 'Table',
        sourceKeyFact: 'PK: SETTLE_ID',
        sourceVolumeFact: '1.1M rows',
        sourceEstimatedRows: 1100000,
        expectedTargetId: 'tgt-08',
        expectedTargetName: 'settlements',
        expectedTargetNamespace: 'public',
        expectedTargetType: 'Table',
        expectedTargetKeyFact: 'PK: settle_id',
        disposition: 'INCLUDED',
        provenance: 'MIGRATION_PLAN',
        provenanceBasis: 'Migration Plan: Graph Phase 2',
        observationStatus: 'DISCOVERED',
        isDecisionRequired: false,
        targetStatus: 'INHERITED_CONFIRMED',
        targetName: 'settlements'
      },
      {
        id: 'unit-09',
        sourceId: 'src-09',
        sourceName: 'TAX_RECORDS',
        sourceNamespace: 'FINANCE',
        sourceType: 'Table',
        sourceKeyFact: 'PK: TAX_ID',
        sourceVolumeFact: '720,000 rows',
        sourceEstimatedRows: 720000,
        expectedTargetId: 'tgt-09',
        expectedTargetName: 'tax_records',
        expectedTargetNamespace: 'public',
        expectedTargetType: 'Table',
        expectedTargetKeyFact: 'PK: tax_id',
        disposition: 'INCLUDED',
        provenance: 'MIGRATION_PLAN',
        provenanceBasis: 'Migration Plan: Graph Phase 2',
        observationStatus: 'DISCOVERED',
        isDecisionRequired: false,
        targetStatus: 'INHERITED_CONFIRMED',
        targetName: 'tax_records'
      },
      {
        id: 'unit-10',
        sourceId: 'src-10',
        sourceName: 'EMPLOYEES',
        sourceNamespace: 'HR',
        sourceType: 'Table',
        sourceKeyFact: 'PK: EMP_ID',
        sourceVolumeFact: '14,200 rows',
        sourceEstimatedRows: 14200,
        expectedTargetId: 'tgt-10',
        expectedTargetName: 'employees',
        expectedTargetNamespace: 'public',
        expectedTargetType: 'Table',
        expectedTargetKeyFact: 'PK: emp_id',
        disposition: 'INCLUDED',
        provenance: 'MIGRATION_PLAN',
        provenanceBasis: 'Migration Plan: Graph Phase 2',
        observationStatus: 'DISCOVERED',
        isDecisionRequired: false,
        targetStatus: 'INHERITED_CONFIRMED',
        targetName: 'employees'
      },
      {
        id: 'unit-11',
        sourceId: 'src-11',
        sourceName: 'DEPARTMENTS',
        sourceNamespace: 'HR',
        sourceType: 'Table',
        sourceKeyFact: 'PK: DEPT_ID',
        sourceVolumeFact: '120 rows',
        sourceEstimatedRows: 120,
        expectedTargetId: 'tgt-11',
        expectedTargetName: 'departments',
        expectedTargetNamespace: 'public',
        expectedTargetType: 'Table',
        expectedTargetKeyFact: 'PK: dept_id',
        disposition: 'INCLUDED',
        provenance: 'MIGRATION_PLAN',
        provenanceBasis: 'Migration Plan: Graph Phase 2',
        observationStatus: 'DISCOVERED',
        isDecisionRequired: false,
        targetStatus: 'INHERITED_CONFIRMED',
        targetName: 'departments'
      },
      {
        id: 'unit-12',
        sourceId: 'src-12',
        sourceName: 'SALARIES',
        sourceNamespace: 'HR',
        sourceType: 'Table',
        sourceKeyFact: 'PK: SAL_ID',
        sourceVolumeFact: '45,000 rows',
        sourceEstimatedRows: 45000,
        expectedTargetId: 'tgt-12',
        expectedTargetName: 'salaries',
        expectedTargetNamespace: 'public',
        expectedTargetType: 'Table',
        expectedTargetKeyFact: 'PK: sal_id',
        disposition: 'INCLUDED',
        provenance: 'MIGRATION_PLAN',
        provenanceBasis: 'Migration Plan: Graph Phase 2',
        observationStatus: 'DISCOVERED',
        isDecisionRequired: false,
        targetStatus: 'INHERITED_CONFIRMED',
        targetName: 'salaries'
      },
      {
        id: 'unit-13',
        sourceId: 'src-13',
        sourceName: 'PERFORMANCE_REVIEWS',
        sourceNamespace: 'HR',
        sourceType: 'Table',
        sourceKeyFact: 'PK: REV_ID',
        sourceVolumeFact: '28,000 rows',
        sourceEstimatedRows: 28000,
        expectedTargetId: 'tgt-13',
        expectedTargetName: 'performance_reviews',
        expectedTargetNamespace: 'public',
        expectedTargetType: 'Table',
        expectedTargetKeyFact: 'PK: rev_id',
        disposition: 'INCLUDED',
        provenance: 'MIGRATION_PLAN',
        provenanceBasis: 'Migration Plan: Graph Phase 2',
        observationStatus: 'DISCOVERED',
        isDecisionRequired: false,
        targetStatus: 'INHERITED_CONFIRMED',
        targetName: 'performance_reviews'
      }
    ];

    this.vs.updateDraft({
      step4Pathway: 'INHERIT',
      comparisonUnits: inherited
    });
  }

  public initCatalogDiscoveryScope(): void {
    const discoveredUnits: ComparisonUnit[] = [
      {
        id: 'disc-01',
        sourceId: 'src-01',
        sourceName: 'ACCOUNTS',
        sourceNamespace: 'FINANCE',
        sourceType: 'Table',
        sourceKeyFact: 'PK: ACC_ID',
        sourceVolumeFact: '1.2M rows',
        sourceEstimatedRows: 1200000,
        expectedTargetId: 'tgt-01',
        expectedTargetName: 'accounts',
        expectedTargetNamespace: 'public',
        expectedTargetType: 'Table',
        expectedTargetKeyFact: 'PK: acc_id',
        disposition: 'INCLUDED',
        provenance: 'DECLARED_RULE',
        provenanceBasis: 'Rule: Exact Match',
        observationStatus: 'DISCOVERED',
        isDecisionRequired: false,
        targetStatus: 'CONFIRMED',
        targetName: 'accounts'
      },
      {
        id: 'disc-02',
        sourceId: 'src-02',
        sourceName: 'TRANSACTIONS',
        sourceNamespace: 'FINANCE',
        sourceType: 'Table',
        sourceKeyFact: 'PK: TX_ID',
        sourceVolumeFact: '18.6M rows',
        sourceEstimatedRows: 18600000,
        expectedTargetId: 'tgt-02',
        expectedTargetName: 'transactions',
        expectedTargetNamespace: 'public',
        expectedTargetType: 'Table',
        expectedTargetKeyFact: 'PK: tx_id',
        disposition: 'INCLUDED',
        provenance: 'DECLARED_RULE',
        provenanceBasis: 'Rule: Exact Match',
        observationStatus: 'DISCOVERED',
        isDecisionRequired: false,
        targetStatus: 'CONFIRMED',
        targetName: 'transactions'
      },
      {
        id: 'disc-03',
        sourceId: 'src-03',
        sourceName: 'CUSTOMERS_LEGACY',
        sourceNamespace: 'FINANCE',
        sourceType: 'Table',
        sourceKeyFact: 'PK: CUST_ID',
        sourceVolumeFact: '120,400 rows',
        sourceEstimatedRows: 120400,
        disposition: 'INCLUDED',
        provenance: 'DECLARED_RULE',
        provenanceBasis: 'Rule: Exact Match',
        observationStatus: 'UNAVAILABLE',
        isDecisionRequired: true,
        decisionReason: 'No exact counterpart found in target schema "public"',
        targetStatus: 'UNRESOLVED'
      }
    ];

    this.vs.updateDraft({
      step4Pathway: 'DEFINE',
      comparisonUnits: discoveredUnits
    });
  }

  // ===========================================================================
  // SCOPE CUSTOMIZATION (Modal)
  // ===========================================================================
  public openCustomizeModal(): void {
    this.isCustomizeModalOpen.set(true);
  }

  public closeCustomizeModal(): void {
    this.isCustomizeModalOpen.set(false);
  }

  public toggleUnitDisposition(unitId: string): void {
    const updated = this.units().map(u => {
      if (u.id === unitId) {
        const nextDisp: ScopeDisposition = u.disposition === 'INCLUDED' ? 'EXCLUDED' : 'INCLUDED';
        return { ...u, disposition: nextDisp };
      }
      return u;
    });
    this.vs.updateDraft({ comparisonUnits: updated });
  }

  public selectAllCustomUnits(): void {
    const updated = this.units().map(u => ({ ...u, disposition: 'INCLUDED' as ScopeDisposition }));
    this.vs.updateDraft({ comparisonUnits: updated });
  }

  public deselectAllCustomUnits(): void {
    const updated = this.units().map(u => ({ ...u, disposition: 'EXCLUDED' as ScopeDisposition }));
    this.vs.updateDraft({ comparisonUnits: updated });
  }

  // ===========================================================================
  // INSPECT SCOPE DRAWER
  // ===========================================================================
  public openInspectDrawer(): void {
    this.isInspectDrawerOpen.set(true);
  }

  public closeInspectDrawer(): void {
    this.isInspectDrawerOpen.set(false);
  }

  // ===========================================================================
  // SECONDARY COLUMN DRAWER
  // ===========================================================================
  public openColumnDrawer(unit: ComparisonUnit): void {
    this.activeColumnDrawerPair.set(unit);
  }

  public closeColumnDrawer(): void {
    this.activeColumnDrawerPair.set(null);
  }

  public defaultColumnsForPair(pair: ComparisonUnit): ColumnCorrespondenceItem[] {
    if (pair.columns && pair.columns.length > 0) {
      return pair.columns;
    }
    return [
      { sourceColumn: `${pair.sourceName.toUpperCase()}_ID`, sourceType: 'NUMBER(10)', targetColumn: `${pair.sourceName.toLowerCase()}_id`, targetType: 'bigint', isPrimaryKey: true },
      { sourceColumn: 'NAME', sourceType: 'VARCHAR2(128)', targetColumn: 'name', targetType: 'varchar(128)' },
      { sourceColumn: 'CODE', sourceType: 'VARCHAR2(32)', targetColumn: 'code', targetType: 'varchar(32)' },
      { sourceColumn: 'STATUS', sourceType: 'VARCHAR2(16)', targetColumn: 'status', targetType: 'varchar(16)' },
      { sourceColumn: 'UPDATED_AT', sourceType: 'TIMESTAMP', targetColumn: 'updated_at', targetType: 'timestamptz' }
    ];
  }

  // ===========================================================================
  // DECISION RESOLUTION & RE-OPENING
  // ===========================================================================
  public getDecisionCandidateOptions(d?: OperatorDecisionItem): CustomSelectOption[] {
    const options: CustomSelectOption[] = [];
    if (d?.suggestedCandidates && d.suggestedCandidates.length > 0) {
      for (const c of d.suggestedCandidates) {
        options.push({
          label: `${c.namespace}.${c.name}`,
          value: c.name,
          desc: 'Discovered in target catalog',
          badge: 'Candidate',
          icon: 'table'
        });
      }
    }
    options.push({
      label: 'public.accounts',
      value: 'accounts',
      desc: 'Discovered in target catalog',
      icon: 'table'
    });
    options.push({
      label: 'public.transactions',
      value: 'transactions',
      desc: 'Discovered in target catalog',
      icon: 'table'
    });
    return options;
  }

  public onSelectDecisionTarget(unitId: string, eventOrValue: any): void {
    let target = '';
    if (typeof eventOrValue === 'string') {
      target = eventOrValue;
    } else if (eventOrValue?.target?.value) {
      target = eventOrValue.target.value;
    }
    if (!target) return;
    this.resolveDecisionTarget(unitId, target);
  }

  public onSelectDecisionTargetCustom(unitId: string, target: string): void {
    if (!target) return;
    this.resolveDecisionTarget(unitId, target);
  }

  public resolveDecisionTarget(unitId: string, target: string): void {
    const updated = this.units().map(u => {
      if (u.id === unitId) {
        return {
          ...u,
          expectedTargetId: `manual-${target}`,
          expectedTargetName: target,
          expectedTargetNamespace: 'public',
          expectedTargetType: 'Table',
          expectedTargetKeyFact: 'PK matched',
          isDecisionRequired: false,
          previousDecisionReason: u.decisionReason || 'Manual counterpart selection required',
          decisionReason: undefined,
          targetStatus: 'CONFIRMED' as const,
          targetName: target,
          observationStatus: 'DISCOVERED' as PhysicalObservationStatus,
          provenance: 'OPERATOR_DEFINED' as CorrespondenceProvenance,
          provenanceBasis: 'Operator Selected'
        };
      }
      return u;
    });

    this.vs.updateDraft({ comparisonUnits: updated });
  }

  public reopenDecision(unitId: string): void {
    const updated = this.units().map(u => {
      if (u.id === unitId) {
        return {
          ...u,
          isDecisionRequired: true,
          disposition: 'INCLUDED' as ScopeDisposition,
          decisionReason: u.previousDecisionReason || 'No exact counterpart found in target schema',
          targetStatus: 'UNRESOLVED' as const,
          targetName: undefined,
          expectedTargetName: undefined,
          observationStatus: 'UNAVAILABLE' as PhysicalObservationStatus,
          provenance: 'OPERATOR_DEFINED' as CorrespondenceProvenance,
          provenanceBasis: 'Decision Reopened'
        };
      }
      return u;
    });

    this.vs.updateDraft({ comparisonUnits: updated });
  }

  public excludeDecisionUnit(unitId: string): void {
    const updated = this.units().map(u => {
      if (u.id === unitId) {
        return {
          ...u,
          disposition: 'EXCLUDED' as ScopeDisposition,
          previousDecisionReason: u.decisionReason || 'Excluded from validation scope',
          isDecisionRequired: false,
          provenance: 'OPERATOR_DEFINED' as CorrespondenceProvenance,
          provenanceBasis: 'Operator Excluded'
        };
      }
      return u;
    });
    this.vs.updateDraft({ comparisonUnits: updated });
  }

  // ===========================================================================
  // OBSERVATION REFRESH
  // ===========================================================================
  public refreshObservation(): void {
    this.isRefreshing.set(true);
    setTimeout(() => {
      this.isRefreshing.set(false);
    }, 600);
  }

  // ===========================================================================
  // PATHWAY C CONTROLS
  // ===========================================================================
  public onSourceNamespaceChange(val: string): void {
    this.selectedSourceNamespace.set(val);
  }

  public onTargetNamespaceChange(val: string): void {
    this.selectedTargetNamespace.set(val);
  }

  public onCorrespondenceRuleChange(val: string): void {
    this.selectedCorrespondenceRule.set(val);
  }

  // ===========================================================================
  // BACKWARD COMPATIBILITY HOOKS (For legacy test/consumer compatibility)
  // ===========================================================================
  public activeSelectorPair = signal<ComparisonUnit | null>(null);
  public selectedTargetCandidateId = signal<string | null>(null);
  public selectedTargetCandidateName = signal<string | null>(null);
  public targetSearchQuery: string = '';

  public targetObjects = signal<DiscoveredComparisonUnit[]>([
    {
      id: 'tgt-accounts',
      name: 'accounts',
      qualifiedName: 'public.accounts',
      type: 'Table',
      typeLabel: 'Table',
      icon: 'table',
      keyFact: 'PK: acc_id',
      volumeFact: '1.2M rows'
    }
  ]);

  public filteredTargetObjects = computed(() => {
    return this.targetObjects();
  });

  public openTargetSelectorModal(pair: ComparisonUnit): void {
    this.activeSelectorPair.set(pair);
  }

  public selectDiscoveredTarget(t: DiscoveredComparisonUnit): void {
    this.selectedTargetCandidateId.set(t.id);
    this.selectedTargetCandidateName.set(t.name);
  }

  public confirmTargetSelection(): void {
    const pair = this.activeSelectorPair();
    const targetName = this.selectedTargetCandidateName();
    if (pair && targetName) {
      const updated = this.units().map(u => {
        if (u.id === pair.id) {
          return {
            ...u,
            targetId: this.selectedTargetCandidateId() || undefined,
            targetName: targetName,
            expectedTargetName: targetName,
            targetStatus: 'CONFIRMED' as const,
            isDecisionRequired: false,
            observationStatus: 'DISCOVERED' as const
          };
        }
        return u;
      });
      this.vs.updateDraft({ comparisonUnits: updated });
    }
    this.activeSelectorPair.set(null);
  }

  public applyCandidateCounterpart(pair: ComparisonUnit): void {
    const updated = this.units().map(u => {
      if (u.id === pair.id) {
        const tgt = u.candidateTargetName || u.expectedTargetName || 'accounts';
        return {
          ...u,
          targetName: tgt,
          expectedTargetName: tgt,
          targetStatus: 'INHERITED_CONFIRMED' as const,
          isDecisionRequired: false
        };
      }
      return u;
    });
    this.vs.updateDraft({ comparisonUnits: updated });
  }

  public removePair(pair: ComparisonUnit): void {
    const updated = this.units().filter(u => u.id !== pair.id);
    this.vs.updateDraft({ comparisonUnits: updated });
  }

  public flattenedSourceNodes = signal<FlattenedScopeNode[]>([
    {
      level: 0,
      isExpanded: true,
      isVisible: true,
      hasChildren: false,
      isIndeterminate: false,
      isSelected: false,
      node: {
        id: 'node-accounts',
        name: 'ACCOUNTS',
        type: 'LEAF',
        typeLabel: 'Table',
        icon: 'table',
        isLeaf: true
      }
    }
  ]);

  public toggleNodeSelection(node: DiscoveredHierarchyNode): void {
    const exists = this.units().find(u => u.sourceName === node.name);
    if (!exists) {
      const newUnit: ComparisonUnit = {
        id: `unit-${node.id}`,
        sourceId: node.id,
        sourceName: node.name,
        sourceNamespace: 'FINANCE',
        sourceType: 'Table',
        sourceKeyFact: 'PK: ACC_ID',
        sourceVolumeFact: '1.2M rows',
        disposition: 'INCLUDED',
        provenance: 'OPERATOR_DEFINED',
        provenanceBasis: 'Operator Selection',
        observationStatus: 'DISCOVERED',
        isDecisionRequired: false,
        targetStatus: 'UNRESOLVED'
      };
      this.vs.updateDraft({ comparisonUnits: [...this.units(), newUnit] });
    }
  }

  public deselectAll(): void {
    this.vs.updateDraft({ comparisonUnits: [] });
  }

  public getProviderIcon(provider: PhysicalProviderId): string {
    switch (provider) {
      case 'Oracle':
        return 'database';
      case 'PostgreSQL':
        return 'database';
      case 'Snowflake':
        return 'snowflake';
      case 'MongoDB':
        return 'leaf';
      default:
        return 'database';
    }
  }
}
