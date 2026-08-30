import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MigrationUiService } from '../../../../core/services/migration-ui.service';
import { DagViewerComponent } from '../../components/dag-viewer.component';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { DagNodeViewModel } from '../../../../core/models/migration-view.models';

@Component({
  selector: 'app-step7-plan',
  standalone: true,
  imports: [CommonModule, FormsModule, DagViewerComponent, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 animate-in fade-in duration-150 text-xs select-none">
      
      <!-- Header -->
      <div class="flex items-center justify-between pb-2 border-b border-slate-200">
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center font-bold">
            <app-lucide-icon name="workflow" [size]="16"></app-lucide-icon>
          </div>
          <div>
            <h2 class="text-base font-bold text-slate-900">Step 7 &bull; EXECUTION PLAN &amp; APPROVAL GATES</h2>
            <p class="text-xs text-slate-600 font-medium">Structured execution pipeline graph. Click '+ Add Approval Gate' between any two stages to insert governance sign-off barriers.</p>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <span class="text-slate-600 font-medium">Pipeline Mode:</span>
          <span class="px-2.5 py-1 rounded-md bg-blue-50 text-blue-700 font-bold border border-blue-200 font-mono">
            {{ ms.wizardDraft().mode }}
          </span>
        </div>
      </div>

      <!-- Informational Banner about Governance & Authority -->
      <div class="p-3.5 rounded-xl bg-blue-50/70 border border-blue-200/80 flex items-start justify-between gap-3">
        <div class="flex items-start gap-2.5">
          <app-lucide-icon name="shield-check" [size]="16" class="text-blue-600 shrink-0 mt-0.5"></app-lucide-icon>
          <div class="flex flex-col gap-0.5">
            <span class="font-bold text-blue-950 text-xs">Structured Execution Pipeline &amp; Universal Gate Insertion</span>
            <span class="text-blue-950 text-[11px] leading-relaxed">
              Standard production cutover gates are automatically pre-configured for CDC modes. You can insert and customize approval gates between any stages in the pipeline, or click any gate to customize signer quorums and lag safety conditions.
            </span>
          </div>
        </div>
      </div>

      <!-- Plan DAG Viewer Surface -->
      <app-dag-viewer
        [plan]="ms.wizardExecutionPlan()">
      </app-dag-viewer>

    </div>
  `
})
export class Step7PlanComponent {
  public ms = inject(MigrationUiService);

  public onNodeSelect(node: DagNodeViewModel): void {
    // Handled in DAG inspector
  }

  public quickInsertBarrier(pos: 'BEFORE' | 'AFTER' | 'BETWEEN'): void {
    this.ms.insertApprovalBarrier(pos, 'n4');
  }
}
