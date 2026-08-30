import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MigrationUiService } from '../../../../core/services/migration-ui.service';
import { DagViewerComponent } from '../../components/dag-viewer.component';

@Component({
  selector: 'app-plan-view',
  standalone: true,
  imports: [CommonModule, DagViewerComponent],
  template: `
    <div class="flex flex-col gap-6 animate-in fade-in duration-150">
      <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-xs flex items-center justify-between">
        <div class="flex flex-col">
          <span class="text-xs font-bold text-slate-900">Compiled Execution Plan • Version {{ ms.activeExecutionPlan().version }}</span>
          <span class="text-xs text-slate-500 font-mono">Fingerprint: {{ ms.activeExecutionPlan().fingerprint }}</span>
        </div>
      </div>
      <app-dag-viewer [plan]="ms.activeExecutionPlan()"></app-dag-viewer>
    </div>
  `
})
export class PlanViewComponent {
  public ms = inject(MigrationUiService);
}
