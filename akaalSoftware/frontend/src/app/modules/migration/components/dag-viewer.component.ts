import {
  Component,
  Input,
  Output,
  EventEmitter,
  inject,
  signal,
  computed,
  OnChanges,
  SimpleChanges
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { ExecutionPlanViewModel, DagNodeViewModel } from '../../../core/models/migration-view.models';
import { MigrationUiService } from '../../../core/services/migration-ui.service';

export interface PipelineStageItem {
  id: string;
  name: string;
  stageType: 'PRE_FLIGHT' | 'SCHEMA_DDL' | 'BULK_EXTRACT' | 'CDC_STREAM' | 'STATE_COMPARE' | 'APPROVAL_GATE' | 'CUTOVER' | 'VALIDATION';
  description: string;
  icon: string;
  isGate: boolean;
  status: 'PENDING' | 'CONFIGURED' | 'READY';
  estimatedDuration: string;
  workerAllocation?: string;
  // Gate specific config
  gateConfig?: {
    gateName: string;
    signerPolicy: 'FOUR_EYES' | 'LEAD_DBA' | 'OWNER' | 'CUSTOM';
    requiredSignatures: number;
    approverRoles: string[];
    cdcMaxLagMs: number;
    requireDlqEmpty: boolean;
    requireCheckpointClean: boolean;
  };
}

@Component({
  selector: 'app-dag-viewer',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="relative w-full bg-white rounded-2xl border border-slate-200 shadow-2xs flex flex-col select-none text-xs">
      
      <!-- TOP CONTROL TOOLBAR -->
      <div class="p-4 border-b border-slate-200 flex items-center justify-between gap-3 flex-wrap bg-slate-50/70">
        
        <div class="flex items-center gap-3">
          <div class="flex items-center gap-2">
            <span class="w-2.5 h-2.5 rounded-full bg-blue-600"></span>
            <span class="font-bold text-slate-900 text-xs">STRUCTURED EXECUTION PIPELINE DAG</span>
          </div>
          <span class="px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-bold border border-blue-200 text-[10.5px]">
            Mode: {{ ms.wizardDraft().mode }}
          </span>
          <span class="text-[11px] text-slate-500 font-medium">
            {{ pipelineStages.length }} Stages &bull; {{ getGateCount() }} Approval Gates Configured
          </span>
        </div>

        <div class="flex items-center gap-2">
          <!-- Reset to Standard DAG -->
          <button
            type="button"
            (click)="resetPipeline()"
            class="h-8 px-3 rounded-lg bg-white hover:bg-slate-100 border border-slate-200 text-slate-700 text-xs font-bold transition-all shadow-2xs cursor-pointer flex items-center gap-1.5">
            <app-lucide-icon name="rotate-ccw" [size]="13"></app-lucide-icon>
            <span>Reset Pipeline</span>
          </button>
        </div>

      </div>

      <!-- MAIN STRUCTURED PIPELINE GRAPH (No Canvas / No Zoom - Clean Linear & Branching Workflow) -->
      <div class="p-6 overflow-x-auto">
        <div class="flex flex-col gap-4 min-w-[700px] max-w-4xl mx-auto py-2">
          
          @for (stage of pipelineStages; track stage.id; let idx = $index; let isLast = $last) {
            
            <!-- STAGE CARD -->
            <div
              (click)="openStageDrawer(stage)"
              class="p-4 rounded-xl border-2 transition-all cursor-pointer flex items-center justify-between gap-4"
              [class.border-amber-400]="stage.isGate && activeSelectedStage?.id !== stage.id"
              [class.bg-amber-50]="stage.isGate && activeSelectedStage?.id !== stage.id"
              [class.border-blue-600]="activeSelectedStage?.id === stage.id"
              [class.bg-blue-50]="activeSelectedStage?.id === stage.id"
              [class.border-slate-200]="!stage.isGate && activeSelectedStage?.id !== stage.id"
              [class.bg-white]="!stage.isGate && activeSelectedStage?.id !== stage.id"
              [class.hover:border-blue-400]="activeSelectedStage?.id !== stage.id">
              
              <!-- Left Info -->
              <div class="flex items-center gap-3.5 min-w-0">
                
                <!-- Stage Step Number or Shield Icon -->
                <div
                  class="w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm shrink-0 shadow-2xs"
                  [class.bg-amber-500]="stage.isGate"
                  [class.text-white]="stage.isGate"
                  [class.bg-blue-600]="!stage.isGate"
                  [class.text-white]="!stage.isGate">
                  @if (stage.isGate) {
                    <app-lucide-icon name="shield-check" [size]="20"></app-lucide-icon>
                  } @else {
                    <app-lucide-icon [name]="stage.icon" [size]="18"></app-lucide-icon>
                  }
                </div>

                <div class="flex flex-col min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="font-bold text-slate-900 text-xs truncate">{{ stage.name }}</span>
                    @if (stage.isGate) {
                      <span class="px-2 py-0.5 rounded bg-amber-100 text-amber-900 text-[10px] font-extrabold uppercase">
                        APPROVAL BARRIER
                      </span>
                    } @else {
                      <span class="px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-[10px] font-semibold">
                        {{ stage.stageType }}
                      </span>
                    }
                  </div>
                  <span class="text-[11px] text-slate-600 font-medium truncate">{{ stage.description }}</span>
                </div>

              </div>

              <!-- Right Metadata & Actions -->
              <div class="flex items-center gap-3 shrink-0">
                
                @if (stage.isGate && stage.gateConfig) {
                  <div class="flex items-center gap-2">
                    <span class="px-2 py-1 rounded-md bg-amber-100/80 border border-amber-200 text-amber-900 font-bold text-[10.5px]">
                      {{ stage.gateConfig.requiredSignatures }} Signer(s) Required
                    </span>
                    <span class="px-2 py-1 rounded-md bg-slate-100 text-slate-700 font-semibold text-[10.5px]">
                      Lag &lt; {{ stage.gateConfig.cdcMaxLagMs }}ms
                    </span>
                  </div>
                } @else {
                  <div class="flex flex-col items-end text-right">
                    <span class="font-bold text-slate-900 text-xs">{{ stage.estimatedDuration }}</span>
                    @if (stage.workerAllocation) {
                      <span class="text-[10.5px] text-slate-500 font-medium">{{ stage.workerAllocation }}</span>
                    }
                  </div>
                }

                <button
                  type="button"
                  (click)="openStageDrawer(stage); $event.stopPropagation()"
                  class="p-2 rounded-lg hover:bg-white text-slate-700 font-bold text-xs border border-slate-200 transition-colors shadow-2xs flex items-center gap-1">
                  <app-lucide-icon [name]="stage.isGate ? 'settings' : 'info'" [size]="13"></app-lucide-icon>
                  <span>{{ stage.isGate ? 'Configure Gate' : 'Details' }}</span>
                </button>

                @if (stage.isGate) {
                  <button
                    type="button"
                    (click)="deleteGate(stage.id); $event.stopPropagation()"
                    class="p-2 rounded-lg hover:bg-rose-50 text-slate-400 hover:text-rose-600 transition-colors"
                    title="Remove Approval Gate">
                    <app-lucide-icon name="trash-2" [size]="14"></app-lucide-icon>
                  </button>
                }

              </div>

            </div>

            <!-- CONNECTOR LINE WITH UNIVERSAL "+ ADD APPROVAL GATE" BUTTON -->
            @if (!isLast) {
              <div class="flex items-center justify-center my-1 relative">
                <div class="w-0.5 h-10 bg-slate-200 absolute"></div>
                
                <button
                  type="button"
                  (click)="insertGateAt(idx)"
                  class="relative z-10 h-7 px-3 rounded-full bg-white hover:bg-amber-50 hover:text-amber-800 hover:border-amber-400 border border-slate-300 text-slate-700 font-bold text-[11px] flex items-center gap-1.5 shadow-2xs transition-all cursor-pointer">
                  <app-lucide-icon name="plus-circle" [size]="12" class="text-amber-600"></app-lucide-icon>
                  <span>+ Add Approval Gate</span>
                </button>
              </div>
            }

          }

        </div>
      </div>

      <!-- =============================================================== -->
      <!-- RIGHT SLIDE-OVER DRAWER: APPROVAL GATE CONFIGURATION            -->
      <!-- =============================================================== -->
      @if (isDrawerOpen && activeSelectedStage) {
        <div class="fixed inset-0 bg-slate-900/20 backdrop-blur-2xs z-50 flex justify-end animate-in fade-in duration-150"
          (click)="isDrawerOpen = false">
          
          <div
            (click)="$event.stopPropagation()"
            class="w-full max-w-lg bg-white h-full shadow-2xl p-6 flex flex-col justify-between overflow-y-auto animate-in slide-in-from-right duration-200 text-xs">
            
            <div class="flex flex-col gap-5">
              
              <!-- Drawer Header -->
              <div class="flex items-center justify-between pb-3 border-b border-slate-200">
                <div class="flex items-center gap-2.5">
                  <div
                    class="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs"
                    [class.bg-amber-500]="activeSelectedStage.isGate"
                    [class.text-white]="activeSelectedStage.isGate"
                    [class.bg-blue-600]="!activeSelectedStage.isGate"
                    [class.text-white]="!activeSelectedStage.isGate">
                    <app-lucide-icon [name]="activeSelectedStage.isGate ? 'shield-check' : 'server'" [size]="16"></app-lucide-icon>
                  </div>
                  <div>
                    <h3 class="font-bold text-slate-900 text-sm">
                      {{ activeSelectedStage.isGate ? 'Configure Approval Gate' : 'Stage Telemetry' }}
                    </h3>
                    <p class="text-[11px] text-slate-500 font-medium">Pipeline Execution Governance</p>
                  </div>
                </div>

                <button
                  type="button"
                  (click)="isDrawerOpen = false"
                  class="p-1 rounded-lg hover:bg-slate-100 text-slate-500 cursor-pointer">
                  <app-lucide-icon name="x" [size]="16"></app-lucide-icon>
                </button>
              </div>

              <!-- Content for Approval Gate -->
              @if (activeSelectedStage.isGate && activeSelectedStage.gateConfig) {
                <div class="flex flex-col gap-4">
                  
                  <!-- Gate Name -->
                  <div class="flex flex-col gap-1.5">
                    <label class="font-bold text-slate-800">Gate Name / Label *</label>
                    <input
                      type="text"
                      [(ngModel)]="activeSelectedStage.name"
                      class="h-9 px-3 rounded-lg bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500" />
                  </div>

                  <!-- Signer Requirement Policy -->
                  <div class="flex flex-col gap-2 pt-2 border-t border-slate-100">
                    <label class="font-bold text-slate-800">Signer Requirement Policy *</label>
                    
                    <div class="grid grid-cols-1 gap-2">
                      <div
                        (click)="setGatePolicy('FOUR_EYES')"
                        class="p-3 rounded-xl border-2 cursor-pointer transition-all flex items-center justify-between"
                        [class.border-amber-500]="activeSelectedStage.gateConfig.signerPolicy === 'FOUR_EYES'"
                        [class.bg-amber-50]="activeSelectedStage.gateConfig.signerPolicy === 'FOUR_EYES'"
                        [class.border-slate-200]="activeSelectedStage.gateConfig.signerPolicy !== 'FOUR_EYES'">
                        <div class="flex flex-col">
                          <span class="font-bold text-slate-900">Four-Eyes Dual Sign-Off (2 Approvers)</span>
                          <span class="text-[11px] text-slate-600">Lead DBA + Security Officer approval required</span>
                        </div>
                        <span class="px-2 py-0.5 rounded bg-amber-100 text-amber-900 font-extrabold text-[10px]">STRICT</span>
                      </div>

                      <div
                        (click)="setGatePolicy('LEAD_DBA')"
                        class="p-3 rounded-xl border-2 cursor-pointer transition-all flex items-center justify-between"
                        [class.border-amber-500]="activeSelectedStage.gateConfig.signerPolicy === 'LEAD_DBA'"
                        [class.bg-amber-50]="activeSelectedStage.gateConfig.signerPolicy === 'LEAD_DBA'"
                        [class.border-slate-200]="activeSelectedStage.gateConfig.signerPolicy !== 'LEAD_DBA'">
                        <div class="flex flex-col">
                          <span class="font-bold text-slate-900">Lead DBA Sign-Off Only (1 Approver)</span>
                          <span class="text-[11px] text-slate-600">Any authorized principal database administrator</span>
                        </div>
                        <span class="px-2 py-0.5 rounded bg-blue-100 text-blue-900 font-extrabold text-[10px]">STANDARD</span>
                      </div>

                      <div
                        (click)="setGatePolicy('OWNER')"
                        class="p-3 rounded-xl border-2 cursor-pointer transition-all flex items-center justify-between"
                        [class.border-amber-500]="activeSelectedStage.gateConfig.signerPolicy === 'OWNER'"
                        [class.bg-amber-50]="activeSelectedStage.gateConfig.signerPolicy === 'OWNER'"
                        [class.border-slate-200]="activeSelectedStage.gateConfig.signerPolicy !== 'OWNER'">
                        <div class="flex flex-col">
                          <span class="font-bold text-slate-900">Project Owner Sign-Off</span>
                          <span class="text-[11px] text-slate-600">Only the authored pipeline creator</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Automated Safety Thresholds -->
                  <div class="flex flex-col gap-2.5 pt-2 border-t border-slate-100">
                    <label class="font-bold text-slate-800">Automated Pre-Conditions (Must Pass to Enable Sign-Off):</label>
                    
                    <div class="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-200">
                      <span class="font-semibold text-slate-800 text-xs">Max CDC Lag Threshold (ms):</span>
                      <input
                        type="number"
                        [(ngModel)]="activeSelectedStage.gateConfig.cdcMaxLagMs"
                        class="w-24 h-7 px-2 rounded-lg bg-white border border-slate-200 text-xs font-bold font-mono text-slate-900" />
                    </div>

                    <label class="flex items-center gap-2 p-2.5 rounded-lg bg-slate-50 border border-slate-200 cursor-pointer">
                      <input
                        type="checkbox"
                        [(ngModel)]="activeSelectedStage.gateConfig.requireDlqEmpty"
                        class="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 cursor-pointer" />
                      <span class="font-semibold text-slate-800">Dead-Letter Queue Count = 0 (Zero In-Flight Row Errors)</span>
                    </label>

                    <label class="flex items-center gap-2 p-2.5 rounded-lg bg-slate-50 border border-slate-200 cursor-pointer">
                      <input
                        type="checkbox"
                        [(ngModel)]="activeSelectedStage.gateConfig.requireCheckpointClean"
                        class="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 cursor-pointer" />
                      <span class="font-semibold text-slate-800">Checkpoint Journal Flushed &amp; Verified</span>
                    </label>
                  </div>

                </div>
              } @else {
                <!-- Non-gate stage telemetry -->
                <div class="flex flex-col gap-3 text-slate-700">
                  <div class="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-1">
                    <span class="font-bold text-slate-900">{{ activeSelectedStage.name }}</span>
                    <span class="text-[11px] text-slate-600">{{ activeSelectedStage.description }}</span>
                  </div>
                  <div class="grid grid-cols-2 gap-2 text-xs">
                    <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col">
                      <span class="text-[10px] font-bold text-slate-500 uppercase">Estimated Runtime</span>
                      <span class="font-bold text-slate-900">{{ activeSelectedStage.estimatedDuration }}</span>
                    </div>
                    <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col">
                      <span class="text-[10px] font-bold text-slate-500 uppercase">Allocation</span>
                      <span class="font-bold text-slate-900">{{ activeSelectedStage.workerAllocation || 'Adaptive' }}</span>
                    </div>
                  </div>
                </div>
              }

            </div>

            <!-- Drawer Footer Actions -->
            <div class="pt-4 border-t border-slate-200 flex items-center justify-between gap-3">
              @if (activeSelectedStage.isGate) {
                <button
                  type="button"
                  (click)="deleteGate(activeSelectedStage.id)"
                  class="h-9 px-4 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-700 font-bold text-xs border border-rose-200 cursor-pointer flex items-center gap-1.5">
                  <app-lucide-icon name="trash-2" [size]="13"></app-lucide-icon>
                  <span>Remove Gate</span>
                </button>
              } @else {
                <div></div>
              }

              <button
                type="button"
                (click)="isDrawerOpen = false"
                class="h-9 px-5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-xs cursor-pointer">
                Save &amp; Close
              </button>
            </div>

          </div>
        </div>
      }

    </div>
  `
})
export class DagViewerComponent implements OnChanges {
  public ms = inject(MigrationUiService);

  @Input() plan?: ExecutionPlanViewModel;
  @Input() draftCustomBarriers: DagNodeViewModel[] = [];
  @Output() addCustomBarrier = new EventEmitter<DagNodeViewModel>();
  @Output() removeCustomBarrier = new EventEmitter<string>();

  public isDrawerOpen = false;
  public activeSelectedStage: PipelineStageItem | null = null;

  public pipelineStages: PipelineStageItem[] = [];

  constructor() {
    this.initDefaultPipeline();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['plan']) {
      this.initDefaultPipeline();
    }
  }

  public initDefaultPipeline(): void {
    const mode = this.ms.wizardDraft().mode;
    const isProd = this.ms.wizardDraft().environment === 'Production';

    if (mode === 'M1_BULK') {
      this.pipelineStages = [
        { id: 'stg_1', name: 'Pre-Flight Topology & Locks Check', stageType: 'PRE_FLIGHT', description: 'Checks network, credentials, and locks', icon: 'shield-check', isGate: false, status: 'READY', estimatedDuration: '1.2s' },
        { id: 'stg_2', name: 'Schema & DDL Target Initialization', stageType: 'SCHEMA_DDL', description: 'Creates table structures on target database', icon: 'database', isGate: false, status: 'READY', estimatedDuration: '4.5s' },
        { id: 'stg_3', name: 'Parallel Snapshot Extraction (8 Workers)', stageType: 'BULK_EXTRACT', description: 'Concurrent direct-path extraction across 4 tables', icon: 'cpu', isGate: false, status: 'READY', estimatedDuration: '38 mins', workerAllocation: '8 Worker Cores' },
        { id: 'stg_4', name: 'Post-Load Row Count & Hash Verification', stageType: 'VALIDATION', description: 'Performs checksum validation across all rows', icon: 'check-circle-2', isGate: false, status: 'READY', estimatedDuration: '2.1 mins' }
      ];
    } else if (mode === 'M3_CDC') {
      this.pipelineStages = [
        { id: 'stg_1', name: 'Pre-Flight CDC Slot Verification', stageType: 'PRE_FLIGHT', description: 'Confirms LogMiner/WAL reader status', icon: 'shield-check', isGate: false, status: 'READY', estimatedDuration: '1.1s' },
        { id: 'stg_2', name: 'Continuous CDC Stream Consumer Engine', stageType: 'CDC_STREAM', description: 'Streams real-time mutation events', icon: 'radio', isGate: false, status: 'READY', estimatedDuration: 'Continuous', workerAllocation: 'Dedicated CDC Stream' },
        {
          id: 'gate_cutover',
          name: 'Production Cutover Sign-Off Gate',
          stageType: 'APPROVAL_GATE',
          description: 'Requires authorization before redirecting write traffic',
          icon: 'shield-check',
          isGate: true,
          status: 'CONFIGURED',
          estimatedDuration: 'Manual Sign-Off',
          gateConfig: {
            gateName: 'Production Cutover Sign-Off Gate',
            signerPolicy: isProd ? 'FOUR_EYES' : 'LEAD_DBA',
            requiredSignatures: isProd ? 2 : 1,
            approverRoles: isProd ? ['Lead DBA', 'Security Officer'] : ['Lead DBA'],
            cdcMaxLagMs: 500,
            requireDlqEmpty: true,
            requireCheckpointClean: true
          }
        },
        { id: 'stg_3', name: 'Final Cutover & Post-Validation', stageType: 'CUTOVER', description: 'Validates target integrity and completes migration', icon: 'check-circle-2', isGate: false, status: 'READY', estimatedDuration: '1.5 mins' }
      ];
    } else {
      // M2_BULK_CDC (Default Enterprise Standard)
      this.pipelineStages = [
        { id: 'stg_1', name: 'Pre-Flight Topology & Permissions Check', stageType: 'PRE_FLIGHT', description: 'Verifies network reachability and CDC permissions', icon: 'shield-check', isGate: false, status: 'READY', estimatedDuration: '1.5s' },
        { id: 'stg_2', name: 'Schema & DDL Target Initialization', stageType: 'SCHEMA_DDL', description: 'Creates table structures on target database', icon: 'database', isGate: false, status: 'READY', estimatedDuration: '4.8s' },
        { id: 'stg_3', name: 'Parallel Snapshot Bulk Extraction', stageType: 'BULK_EXTRACT', description: 'Direct-path extraction of baseline table snapshots', icon: 'cpu', isGate: false, status: 'READY', estimatedDuration: '42 mins', workerAllocation: '8 Worker Cores' },
        { id: 'stg_4', name: 'CDC Delta Stream Engine (Catch-up)', stageType: 'CDC_STREAM', description: 'Streams delta mutations from in-memory ring buffers', icon: 'radio', isGate: false, status: 'READY', estimatedDuration: 'Continuous (<1s lag)', workerAllocation: '4 Applier Threads' },
        {
          id: 'gate_cutover',
          name: 'Gate 2: Production Cutover Sign-Off',
          stageType: 'APPROVAL_GATE',
          description: 'Four-eyes sign-off barrier before primary traffic redirection',
          icon: 'shield-check',
          isGate: true,
          status: 'CONFIGURED',
          estimatedDuration: 'Manual Sign-Off',
          gateConfig: {
            gateName: 'Gate 2: Production Cutover Sign-Off',
            signerPolicy: isProd ? 'FOUR_EYES' : 'LEAD_DBA',
            requiredSignatures: isProd ? 2 : 1,
            approverRoles: isProd ? ['Lead DBA', 'Security Officer'] : ['Lead DBA'],
            cdcMaxLagMs: 500,
            requireDlqEmpty: true,
            requireCheckpointClean: true
          }
        },
        { id: 'stg_5', name: 'Final Traffic Cutover & Post-Validation', stageType: 'CUTOVER', description: 'Verifies checksum fingerprints and seals migration', icon: 'check-circle-2', isGate: false, status: 'READY', estimatedDuration: '2.0 mins' }
      ];
    }
  }

  public getGateCount(): number {
    return this.pipelineStages.filter(s => s.isGate).length;
  }

  public insertGateAt(index: number): void {
    const isProd = this.ms.wizardDraft().environment === 'Production';
    const gateId = `gate_custom_${Date.now()}`;
    const newGate: PipelineStageItem = {
      id: gateId,
      name: `Approval Gate (Stage ${index + 1})`,
      stageType: 'APPROVAL_GATE',
      description: 'Operator-authored safety gate requiring explicit governance sign-off',
      icon: 'shield-check',
      isGate: true,
      status: 'CONFIGURED',
      estimatedDuration: 'Manual Sign-Off',
      gateConfig: {
        gateName: `Approval Gate (Stage ${index + 1})`,
        signerPolicy: isProd ? 'FOUR_EYES' : 'LEAD_DBA',
        requiredSignatures: isProd ? 2 : 1,
        approverRoles: isProd ? ['Lead DBA', 'Security Officer'] : ['Lead DBA'],
        cdcMaxLagMs: 500,
        requireDlqEmpty: true,
        requireCheckpointClean: true
      }
    };

    // Insert directly into array at index + 1
    this.pipelineStages.splice(index + 1, 0, newGate);
    this.openStageDrawer(newGate);
  }

  public deleteGate(gateId: string): void {
    this.pipelineStages = this.pipelineStages.filter(s => s.id !== gateId);
    if (this.activeSelectedStage?.id === gateId) {
      this.isDrawerOpen = false;
      this.activeSelectedStage = null;
    }
  }

  public openStageDrawer(stage: PipelineStageItem): void {
    this.activeSelectedStage = stage;
    this.isDrawerOpen = true;
  }

  public setGatePolicy(policy: 'FOUR_EYES' | 'LEAD_DBA' | 'OWNER'): void {
    if (!this.activeSelectedStage?.gateConfig) return;
    this.activeSelectedStage.gateConfig.signerPolicy = policy;
    if (policy === 'FOUR_EYES') {
      this.activeSelectedStage.gateConfig.requiredSignatures = 2;
      this.activeSelectedStage.gateConfig.approverRoles = ['Lead DBA', 'Security Officer'];
    } else {
      this.activeSelectedStage.gateConfig.requiredSignatures = 1;
      this.activeSelectedStage.gateConfig.approverRoles = ['Lead DBA'];
    }
  }

  public resetPipeline(): void {
    this.initDefaultPipeline();
    this.isDrawerOpen = false;
  }
}
