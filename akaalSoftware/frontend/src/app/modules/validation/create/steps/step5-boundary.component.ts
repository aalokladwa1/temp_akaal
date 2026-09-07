import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ValidationUiService } from '../../../../core/services/validation-ui.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import {
  OperatorBaselineIntent,
  OperatorMaintenanceCondition,
  BaselineConceptOption,
  TechnicalDetailItem
} from './step5-boundary.models';

@Component({
  selector: 'app-step5-boundary',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideIconComponent
  ],
  template: `
    <div class="max-w-7xl mx-auto w-full space-y-6 pb-12 select-none font-sans text-xs">
      
      <!-- ========================================================================= -->
      <!-- 0. HEADER & RESTRAINED CONTEXT AREA                                       -->
      <!-- ========================================================================= -->
      <div class="flex flex-col gap-3.5 border-b border-slate-200 pb-4">
        <div class="flex items-start justify-between flex-wrap gap-4">
          <div class="flex flex-col gap-1">
            <h1 class="text-xl font-bold text-slate-900 tracking-tight">Boundary &amp; Consistency Baseline</h1>
            <p class="text-sm text-slate-500 font-normal leading-relaxed">
              Establish the common state AKAAL should use for this validation.
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
              <span class="ml-1.5 px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 text-[10px] font-bold flex items-center gap-1">
                <app-lucide-icon name="git-merge" [size]="10"></app-lucide-icon>
                <span>Project Linked</span>
              </span>
            }
          </div>
        </div>
      </div>

      <!-- ========================================================================= -->
      <!-- 1. PRIMARY SECTION: COMPARISON BASELINE                                   -->
      <!-- ========================================================================= -->
      <section aria-label="Comparison Baseline Configuration" class="space-y-4">
        <div class="flex items-center justify-between">
          <div class="flex flex-col gap-0.5">
            <h2 class="text-sm font-bold text-slate-900 tracking-tight">Comparison baseline</h2>
            <p class="text-xs text-slate-500 font-normal">
              Defines the logical alignment and physical stability contract between Source and Target.
            </p>
          </div>
          
          @if (isInheritedPathway()) {
            <span class="px-2.5 py-1 rounded bg-slate-100 text-slate-700 border border-slate-200 text-xs font-medium flex items-center gap-1.5">
              <app-lucide-icon name="git-merge" [size]="13" class="text-slate-500"></app-lucide-icon>
              <span>Inherited Context</span>
            </span>
          }
        </div>

        <!-- ======================================================================= -->
        <!-- STATE A: INHERITED FROM MIGRATION (validationContext === 'EXISTING_PROJECT') -->
        <!-- ======================================================================= -->
        @if (isInheritedPathway()) {
          <div class="rounded-xl bg-white border border-slate-200 p-6 shadow-xs space-y-5">
            
            <div class="flex items-start justify-between gap-4">
              <div class="flex items-start gap-3.5">
                <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center shrink-0">
                  <app-lucide-icon name="shield-check" [size]="20"></app-lucide-icon>
                </div>
                <div class="space-y-1">
                  <div class="flex items-center gap-2">
                    <h3 class="text-sm font-bold text-slate-900">Inherited from migration</h3>
                    <span class="px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 text-[10px] font-bold flex items-center gap-1">
                      <app-lucide-icon name="shield-check" [size]="11"></app-lucide-icon>
                      <span>Authoritative Provenance</span>
                    </span>
                  </div>
                  <p class="text-xs text-slate-600 leading-relaxed font-normal max-w-2xl">
                    AKAAL has migration provenance that establishes the intended relationship between the selected Source and Target scope.
                  </p>
                </div>
              </div>
            </div>

            <!-- Alignment vs Stability Two-Column Factual Grid -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-slate-100">
              
              <!-- 1. Alignment Basis -->
              <div class="p-3.5 rounded-lg bg-slate-50/70 border border-slate-200/80 space-y-1.5">
                <div class="flex items-center gap-2 text-slate-500 text-[11px] font-bold uppercase tracking-wider">
                  <app-lucide-icon name="git-commit-horizontal" [size]="14" class="text-blue-600"></app-lucide-icon>
                  <span>Alignment Basis</span>
                </div>
                <div class="text-xs font-bold text-slate-900">
                  Migration cutover / synchronization frontier
                </div>
                <p class="text-xs text-slate-500 font-normal leading-relaxed">
                  Logical correspondence established directly by migration execution graph.
                </p>
              </div>

              <!-- 2. Stability Basis -->
              <div class="p-3.5 rounded-lg bg-slate-50/70 border border-slate-200/80 space-y-1.5">
                <div class="flex items-center gap-2 text-slate-500 text-[11px] font-bold uppercase tracking-wider">
                  <app-lucide-icon name="lock" [size]="13" class="text-emerald-600"></app-lucide-icon>
                  <span>Stability Basis</span>
                </div>
                <div class="text-xs font-bold text-slate-900">
                  Established using supported provider mechanisms
                </div>
                <p class="text-xs text-slate-500 font-normal leading-relaxed">
                  Provider-native consistent read frontier captured when this validation initializes.
                </p>
              </div>

            </div>

            <!-- Footer Note: Zero operator clicks needed -->
            <div class="pt-2 flex items-center justify-between border-t border-slate-100 text-xs">
              <span class="text-slate-500 font-normal flex items-center gap-1.5">
                <span>No operator decision required. Provenance is bound to linked project:</span>
                <span class="inline-flex items-center gap-1 text-slate-700 font-medium bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                  <app-lucide-icon name="folder" [size]="12" class="text-slate-500"></app-lucide-icon>
                  <span>{{ vs.newValidationDraft().projectName || 'Cloud Modernization' }}</span>
                </span>
              </span>
              <span class="text-emerald-700 font-semibold flex items-center gap-1.5">
                <app-lucide-icon name="check" [size]="14" class="text-emerald-600"></app-lucide-icon>
                <span>Baseline Intent Established</span>
              </span>
            </div>

          </div>
        }

        <!-- ======================================================================= -->
        <!-- STATE C: INDEPENDENT VALIDATION (validationContext === 'INDEPENDENT')     -->
        <!-- ======================================================================= -->
        @if (!isInheritedPathway()) {
          <div class="space-y-4">
            
            <div class="text-xs text-slate-600 font-medium">
              How are these systems known to represent corresponding data?
            </div>

            <!-- 2x2 Concept Selection Cards Grid -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              @for (opt of independentOptions; track opt.id) {
                <div
                  (click)="selectBaselineIntent(opt.id)"
                  class="rounded-xl border p-4 transition-all cursor-pointer relative flex flex-col justify-between gap-3 text-left shadow-2xs"
                  [ngClass]="{
                    'bg-blue-50/30 border-blue-500 ring-2 ring-blue-500/20': selectedIntent() === opt.id && opt.isSupported,
                    'bg-white border-slate-200 hover:border-slate-300': selectedIntent() !== opt.id
                  }">
                  
                  <div class="space-y-2">
                    <div class="flex items-start justify-between gap-3">
                      <div class="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                        [ngClass]="selectedIntent() === opt.id && opt.isSupported ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-700'">
                        <app-lucide-icon [name]="opt.icon" [size]="16"></app-lucide-icon>
                      </div>

                      <!-- Radio Selection Indicator (Curved Corner Rectangle) -->
                      <div class="w-4 h-4 rounded-md border flex items-center justify-center transition-colors shrink-0 mt-1"
                        [ngClass]="selectedIntent() === opt.id ? 'border-blue-600 bg-blue-600' : 'border-slate-300'">
                        @if (selectedIntent() === opt.id) {
                          <span class="w-1.5 h-1.5 rounded-xs bg-white"></span>
                        }
                      </div>
                    </div>

                    <div class="space-y-1">
                      <h3 class="text-xs font-bold text-slate-900 leading-snug">
                        {{ opt.title }}
                      </h3>
                      <p class="text-xs text-slate-500 font-normal leading-relaxed">
                        {{ opt.description }}
                      </p>
                    </div>
                  </div>

                  @if (!opt.isSupported) {
                    <div class="mt-1 px-2.5 py-1.5 rounded bg-slate-50 border border-slate-200 text-[11px] text-slate-600 flex items-start gap-1.5">
                      <app-lucide-icon name="info" [size]="13" class="text-slate-500 shrink-0 mt-0.5"></app-lucide-icon>
                      <span>{{ opt.unsupportedNotice }}</span>
                    </div>
                  }

                </div>
              }
            </div>

            <!-- =================================================================== -->
            <!-- CONDITIONAL SUB-CONFIG: MAINTENANCE / COORDINATED BASELINE           -->
            <!-- =================================================================== -->
            @if (selectedIntent() === 'MAINTENANCE_COORDINATED') {
              <div class="rounded-xl bg-slate-50/70 border border-slate-200 p-4 space-y-3 mt-3">
                <div class="flex items-center gap-2">
                  <app-lucide-icon name="sliders" [size]="14" class="text-slate-600"></app-lucide-icon>
                  <h4 class="text-xs font-bold text-slate-900">Operational Condition Declaration</h4>
                </div>
                <p class="text-xs text-slate-500 font-normal">
                  Specify what operational coordination condition applies to Source and Target during this validation mission.
                </p>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                  <!-- Condition 1: Writes Stopped -->
                  <div
                    (click)="selectMaintenanceCondition('WRITES_STOPPED_DECLARED')"
                    class="p-3 rounded-lg border bg-white cursor-pointer transition-all flex items-start gap-2.5"
                    [ngClass]="maintenanceCondition() === 'WRITES_STOPPED_DECLARED' ? 'border-blue-500 ring-1 ring-blue-500' : 'border-slate-200'">
                    <div class="w-4 h-4 rounded-md border flex items-center justify-center shrink-0 mt-0.5"
                      [ngClass]="maintenanceCondition() === 'WRITES_STOPPED_DECLARED' ? 'border-blue-600 bg-blue-600' : 'border-slate-300'">
                      @if (maintenanceCondition() === 'WRITES_STOPPED_DECLARED') {
                        <span class="w-1.5 h-1.5 rounded-xs bg-white"></span>
                      }
                    </div>
                    <div class="space-y-0.5">
                      <div class="text-xs font-semibold text-slate-900 flex items-center gap-1.5">
                        <app-lucide-icon name="pause" [size]="12" class="text-amber-600 shrink-0"></app-lucide-icon>
                        <span>Writes will be stopped before initialization</span>
                      </div>
                      <p class="text-[11px] text-slate-500 font-normal">
                        Workload is halted; no active transactions execute during read operations.
                      </p>
                    </div>
                  </div>

                  <!-- Condition 2: External Coordination -->
                  <div
                    (click)="selectMaintenanceCondition('EXTERNAL_COORDINATION_DECLARED')"
                    class="p-3 rounded-lg border bg-white cursor-pointer transition-all flex items-start gap-2.5"
                    [ngClass]="maintenanceCondition() === 'EXTERNAL_COORDINATION_DECLARED' ? 'border-blue-500 ring-1 ring-blue-500' : 'border-slate-200'">
                    <div class="w-4 h-4 rounded-md border flex items-center justify-center shrink-0 mt-0.5"
                      [ngClass]="maintenanceCondition() === 'EXTERNAL_COORDINATION_DECLARED' ? 'border-blue-600 bg-blue-600' : 'border-slate-300'">
                      @if (maintenanceCondition() === 'EXTERNAL_COORDINATION_DECLARED') {
                        <span class="w-1.5 h-1.5 rounded-xs bg-white"></span>
                      }
                    </div>
                    <div class="space-y-0.5">
                      <div class="text-xs font-semibold text-slate-900 flex items-center gap-1.5">
                        <app-lucide-icon name="arrow-left-right" [size]="12" class="text-blue-600 shrink-0"></app-lucide-icon>
                        <span>An external process coordinates the common baseline</span>
                      </div>
                      <p class="text-[11px] text-slate-500 font-normal">
                        Upstream orchestration, ETL fencing, or snapshot tooling establishes alignment.
                      </p>
                    </div>
                  </div>
                </div>

                <!-- Strict Truth Label: Declared != Observed != Enforced -->
                <div class="p-2.5 bg-slate-100/80 rounded-md border border-slate-200 flex items-center gap-2 text-[11px] text-slate-600">
                  <app-lucide-icon name="info" [size]="13" class="text-slate-500 shrink-0"></app-lucide-icon>
                  <span>
                    <strong>Operational condition:</strong> Declared by operator &middot; Evaluated during readiness and initialization.
                  </span>
                </div>
              </div>
            }

            <!-- =================================================================== -->
            <!-- STATE D: INSUFFICIENT BASELINE / DECISION REQUIRED BANNER            -->
            <!-- =================================================================== -->
            @if (!selectedIntent()) {
              <div class="p-4 bg-amber-50/60 border border-amber-200/80 rounded-xl flex items-start gap-3 text-xs text-amber-900">
                <app-lucide-icon name="alert-triangle" [size]="16" class="text-amber-600 shrink-0 mt-0.5"></app-lucide-icon>
                <div class="space-y-1">
                  <div class="font-bold text-slate-900">Baseline cannot yet be established</div>
                  <p class="text-slate-600 leading-relaxed font-normal">
                    AKAAL does not currently have enough information to establish that the selected Source and Target states are legitimately comparable. Choose how these systems are known to represent the same state before continuing.
                  </p>
                </div>
              </div>
            }

            <!-- Fail-closed warning if unsupported External Replication is picked -->
            @if (selectedIntent() === 'EXTERNAL_REPLICATION') {
              <div class="p-4 bg-amber-50/60 border border-amber-200/80 rounded-xl flex items-start gap-3 text-xs text-amber-900">
                <app-lucide-icon name="alert-circle" [size]="16" class="text-amber-600 shrink-0 mt-0.5"></app-lucide-icon>
                <div class="space-y-1">
                  <div class="font-bold text-slate-900">External baseline integration unavailable</div>
                  <p class="text-slate-600 leading-relaxed font-normal">
                    External baseline integration is not currently available for this configuration. Select an alternative baseline concept above to continue.
                  </p>
                </div>
              </div>
            }

          </div>
        }

      </section>

      <!-- ========================================================================= -->
      <!-- 2. BASELINE ESTABLISHMENT SECTION (Restrained Policy Overview)             -->
      <!-- ========================================================================= -->
      <section aria-label="Baseline Establishment Policy" class="rounded-xl bg-white border border-slate-200 p-5 shadow-xs space-y-3">
        <div class="flex items-center gap-2 text-slate-900 font-bold text-xs">
          <app-lucide-icon name="clock" [size]="15" class="text-slate-600"></app-lucide-icon>
          <span>Baseline establishment</span>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
          <div class="space-y-1">
            <span class="text-[11px] font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
              <app-lucide-icon name="clock" [size]="12" class="text-slate-400"></app-lucide-icon>
              <span>When</span>
            </span>
            <p class="text-xs font-bold text-slate-900">At mission initialization</p>
          </div>
          <div class="space-y-1 sm:col-span-2">
            <span class="text-[11px] font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
              <app-lucide-icon name="shield-check" [size]="12" class="text-slate-400"></app-lucide-icon>
              <span>What AKAAL will do</span>
            </span>
            <p class="text-xs text-slate-600 font-normal leading-relaxed">
              Establish and verify the concrete provider-supported states required by this baseline.
            </p>
          </div>
        </div>

        <!-- Fail-Closed Law -->
        <div class="pt-2 border-t border-slate-100 flex items-start gap-2 text-[11px] text-slate-500">
          <app-lucide-icon name="shield-alert" [size]="13" class="text-slate-400 shrink-0 mt-0.5"></app-lucide-icon>
          <span>
            <strong>Fail-Closed Consistency Guarantee:</strong> If the requested baseline cannot be honored, initialization stops rather than silently falling back to a weaker consistency model.
          </span>
        </div>
      </section>

      <!-- ========================================================================= -->
      <!-- 3. CONTEXTUAL INTELLIGENCE SLOT (Conditionally Rendered, No Placeholders)   -->
      <!-- ========================================================================= -->
      @if (contextualIntelligence()) {
        <section aria-label="Contextual Intelligence" class="rounded-xl bg-blue-50/50 border border-blue-200 p-4 space-y-2">
          <div class="flex items-center gap-2 text-blue-900 font-bold text-xs">
            <app-lucide-icon name="sparkles" [size]="14" class="text-blue-600"></app-lucide-icon>
            <span>{{ contextualIntelligence()?.title }}</span>
          </div>
          <p class="text-xs text-blue-800 font-normal leading-relaxed">
            {{ contextualIntelligence()?.body }}
          </p>
        </section>
      }

      <!-- ========================================================================= -->
      <!-- 4. TECHNICAL DETAILS (Read-Only Progressive Disclosure)                   -->
      <!-- ========================================================================= -->
      <section aria-label="Technical Baseline Details" class="pt-1">
        <button
          type="button"
          (click)="toggleTechnicalDetails()"
          class="flex items-center gap-2 text-xs font-semibold text-slate-600 hover:text-slate-900 cursor-pointer transition-colors select-none">
          <app-lucide-icon [name]="isTechnicalDetailsOpen() ? 'chevron-down' : 'chevron-right'" [size]="14" class="text-slate-400"></app-lucide-icon>
          <span>{{ isTechnicalDetailsOpen() ? 'Hide technical details' : 'View technical details' }}</span>
        </button>

        @if (isTechnicalDetailsOpen()) {
          <div class="mt-3 rounded-xl bg-slate-50/70 border border-slate-200 p-4 animate-in fade-in duration-100 space-y-3">
            <div class="flex items-center justify-between border-b border-slate-200 pb-2">
              <span class="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                <app-lucide-icon name="sliders" [size]="13" class="text-slate-500"></app-lucide-icon>
                <span>Baseline Technical Contract</span>
              </span>
              <span class="px-2 py-0.5 rounded bg-white border border-slate-200 text-[10px] font-mono text-slate-600">
                Read-Only Configuration
              </span>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              @for (item of technicalDetailsList(); track item.label) {
                <div class="p-2.5 rounded-lg bg-white border border-slate-200/80 space-y-1 shadow-2xs">
                  <div class="flex items-center gap-1.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                    <app-lucide-icon [name]="item.icon || 'shield'" [size]="12" class="text-slate-500 shrink-0"></app-lucide-icon>
                    <span>{{ item.label }}</span>
                  </div>
                  <div class="text-xs font-semibold text-slate-900 truncate" [title]="item.value">{{ item.value }}</div>
                  <div class="text-[10px] text-slate-500 font-normal leading-tight">{{ item.provenance }}</div>
                </div>
              }
            </div>
          </div>
        }
      </section>

    </div>
  `
})
export class Step5BoundaryComponent {
  public vs: ValidationUiService;

  // Technical details disclosure state
  public isTechnicalDetailsOpen = signal<boolean>(false);

  // Optional contextual intelligence slot (null by default; collapses with zero height/whitespace)
  public contextualIntelligence = signal<{ title: string; body: string } | null>(null);

  // 5 Independent Baseline Concepts (concise, neat, restrained)
  public readonly independentOptions: BaselineConceptOption[] = [
    {
      id: 'CURRENT_OPERATIONAL',
      title: 'Current operational baseline',
      description: 'These systems are expected to represent the same current business state. AKAAL will determine whether a defensible stable comparison can be established using their supported capabilities.',
      icon: 'activity',
      isSupported: true
    },
    {
      id: 'MAINTENANCE_COORDINATED',
      title: 'Maintenance / coordinated baseline',
      description: 'Source and Target will be brought to a known comparable operational state before validation begins.',
      icon: 'pause-circle',
      isSupported: true
    },
    {
      id: 'INHERITED_MIGRATION',
      title: 'AKAAL migration baseline',
      description: 'Derive baseline cutover boundary and synchronization state from an existing AKAAL migration project.',
      icon: 'git-merge',
      isSupported: true
    },
    {
      id: 'EXTERNAL_REPLICATION',
      title: 'External replication baseline',
      description: 'Systems synchronized via external replication tools (GoldenGate, AWS DMS, Debezium, or external CSN log sequence).',
      icon: 'folder-input',
      isSupported: false,
      unsupportedNotice: 'This capability is not currently available.'
    },
    {
      id: 'STATIC_IMMUTABLE',
      title: 'Static / immutable data',
      description: 'The selected Source and Target scope represents data that does not change during this validation.',
      icon: 'database',
      isSupported: true
    }
  ];

  // Computed state
  public isInheritedPathway = computed<boolean>(() => {
    return this.vs.newValidationDraft().validationContext === 'EXISTING_PROJECT';
  });

  public selectedIntent = computed<OperatorBaselineIntent | undefined>(() => {
    const draft = this.vs.newValidationDraft();
    if (draft.validationContext === 'EXISTING_PROJECT') {
      return 'INHERITED_MIGRATION';
    }
    return draft.baselineIntent;
  });

  public maintenanceCondition = computed<OperatorMaintenanceCondition | undefined>(() => {
    return this.vs.newValidationDraft().maintenanceCondition;
  });

  public sourceProvider = computed<string>(() => {
    return this.vs.newValidationDraft().sourceProvider || 'Oracle';
  });

  public sourceEndpointLabel = computed<string>(() => {
    const draft = this.vs.newValidationDraft();
    return draft.sourceHost || draft.sourceDatabase || 'Source Catalog';
  });

  public targetProvider = computed<string>(() => {
    return this.vs.newValidationDraft().targetProvider || 'PostgreSQL';
  });

  public targetEndpointLabel = computed<string>(() => {
    const draft = this.vs.newValidationDraft();
    return draft.targetHost || draft.targetDatabase || 'Target Catalog';
  });

  // Technical Details Grid
  public technicalDetailsList = computed<TechnicalDetailItem[]>(() => {
    const intent = this.selectedIntent();
    const isInherited = this.isInheritedPathway();

    let alignmentValue = 'Not established';
    let alignmentProv = 'Operator intent required';

    if (isInherited) {
      alignmentValue = 'Migration cutover / synchronization frontier';
      alignmentProv = 'Derived from linked migration project execution graph';
    } else if (intent === 'CURRENT_OPERATIONAL') {
      alignmentValue = 'Expected business state convergence';
      alignmentProv = 'Operator declared intent · Verified during readiness';
    } else if (intent === 'MAINTENANCE_COORDINATED') {
      const cond = this.maintenanceCondition();
      alignmentValue = cond === 'WRITES_STOPPED_DECLARED'
        ? 'Declared workload cessation'
        : 'External baseline coordination';
      alignmentProv = 'Operator declaration · Verified during readiness';
    } else if (intent === 'STATIC_IMMUTABLE') {
      alignmentValue = 'Declared unchanging datasets';
      alignmentProv = 'Selected comparison correspondence';
    } else if (intent === 'EXTERNAL_REPLICATION') {
      alignmentValue = 'External replication boundary';
      alignmentProv = 'Integration unavailable for current configuration';
    }

    return [
      {
        key: 'ALIGNMENT_BASIS',
        label: 'Alignment Basis',
        value: alignmentValue,
        provenance: alignmentProv,
        icon: 'git-commit-horizontal'
      },
      {
        key: 'SOURCE_STABILITY',
        label: 'Source Stability',
        value: 'Resolved during initialization',
        provenance: 'Provider-native read consistency evaluated at runtime',
        icon: 'shield-check'
      },
      {
        key: 'TARGET_STABILITY',
        label: 'Target Stability',
        value: 'Resolved during initialization',
        provenance: 'Provider-native read consistency evaluated at runtime',
        icon: 'shield-check'
      },
      {
        key: 'BOUNDARY_CAPTURE',
        label: 'Boundary Capture',
        value: 'At mission initialization',
        provenance: 'Ephemeral/native frontier values captured at execution start',
        icon: 'crosshair'
      },
      {
        key: 'FAIL_CLOSED_RESTART',
        label: 'Restart Behavior',
        value: 'Deterministic continuation',
        provenance: 'Captured baseline must remain valid for restart safety',
        icon: 'refresh-cw'
      },
      {
        key: 'EVIDENCE_RECORDING',
        label: 'Evidence Provenance',
        value: 'Evidence #12 logging',
        provenance: 'Captured baseline metadata recorded with mission evidence',
        icon: 'file-text'
      }
    ];
  });

  // Convenience computed properties for template and tests
  public isInheritedMode = computed<boolean>(() => this.isInheritedPathway());
  public baselineConceptCards = computed<BaselineConceptOption[]>(() => this.independentOptions);
  public technicalDetails = computed<TechnicalDetailItem[]>(() => this.technicalDetailsList());
  public isMaintenanceSelected = computed<boolean>(() => this.selectedIntent() === 'MAINTENANCE_COORDINATED');
  public isInsufficientBaseline = computed<boolean>(() => !this.selectedIntent() || this.selectedIntent() === 'EXTERNAL_REPLICATION');
  public baselineCardSummary = computed(() => ({
    title: this.isInheritedPathway() ? 'Inherited Migration Baseline' : 'Comparison baseline',
    intent: this.selectedIntent()
  }));

  constructor(vs?: ValidationUiService) {
    this.vs = vs || inject(ValidationUiService);
  }

  public ngOnInit(): void {
    const draft = this.vs.newValidationDraft();
    if (draft.validationContext === 'EXISTING_PROJECT' && draft.baselineIntent !== 'INHERITED_MIGRATION') {
      this.vs.updateDraft({ baselineIntent: 'INHERITED_MIGRATION' });
    }
  }

  public selectBaselineIntent(intent: OperatorBaselineIntent): void {
    const draft = this.vs.newValidationDraft();
    if (draft.validationContext === 'EXISTING_PROJECT') return;

    this.vs.updateDraft({
      baselineIntent: intent,
      // Strictly fail-closed: unselect condition when newly picking MAINTENANCE_COORDINATED unless already set
      maintenanceCondition: intent === 'MAINTENANCE_COORDINATED' ? draft.maintenanceCondition : undefined
    });
  }

  public selectIntent(intent: OperatorBaselineIntent): void {
    this.selectBaselineIntent(intent);
  }

  public selectMaintenanceCondition(cond: OperatorMaintenanceCondition): void {
    this.vs.updateDraft({
      maintenanceCondition: cond
    });
  }

  public onNotesChange(notes: string): void {
    this.vs.updateDraft({ operatorNotes: notes });
  }

  public toggleTechnicalDetails(): void {
    this.isTechnicalDetailsOpen.update(v => !v);
  }

  public getProviderIcon(provider?: string): string {
    switch (provider) {
      case 'Oracle':
      case 'PostgreSQL':
      case 'MySQL':
      case 'SQL Server':
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
