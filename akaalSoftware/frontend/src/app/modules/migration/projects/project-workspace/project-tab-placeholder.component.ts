import { Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ProjectWorkspaceDetail, ProjectWorkspaceTabType } from '../projects.models';

@Component({
  selector: 'app-project-tab-placeholder',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="p-8 sm:p-12 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col items-center text-center gap-5 select-none animate-in fade-in duration-150 max-w-3xl mx-auto my-6">
      
      <!-- Icon Container (Rectangular rounded-xl) -->
      <div class="w-14 h-14 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 shadow-2xs">
        <app-lucide-icon [name]="getTabIcon()" [size]="28"></app-lucide-icon>
      </div>

      <!-- Title & Context Scope -->
      <div class="flex flex-col gap-1.5 max-w-lg">
        <div class="flex items-center justify-center gap-2">
          <span class="px-2 py-0.5 rounded-md text-[10.5px] font-bold font-mono bg-blue-50 text-blue-700 border border-blue-200">
            {{ project()?.key || 'PRJ' }}
          </span>
          <h2 class="text-lg font-bold text-slate-900 font-heading capitalize">
            Project {{ getTabLabel() }}
          </h2>
        </div>
        <p class="text-xs text-slate-600 font-normal leading-relaxed">
          {{ getTabDescription() }}
        </p>
      </div>

      <!-- Capability Readiness Notice -->
      <div class="w-full p-4 rounded-lg bg-slate-50 border border-slate-200 flex items-start gap-3 text-left text-xs">
        <app-lucide-icon name="info" [size]="16" class="text-blue-600 shrink-0 mt-0.5"></app-lucide-icon>
        <div class="flex flex-col gap-1">
          <span class="font-bold text-slate-900">Convergence Roadmap: Part D / Part E</span>
          <p class="text-slate-600 text-[11px] leading-relaxed">
            Direct deep operations for {{ getTabLabel() }} connect in Part D (Migrations, Validations, Resources) and Part E (Governance &amp; Access). Factual summaries and active projections remain available in the Project Overview.
          </p>
        </div>
      </div>

      <!-- Back to Overview Button -->
      <button
        type="button"
        (click)="navigateOverview.emit()"
        class="h-9 px-4 rounded-md bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 text-xs font-semibold shadow-2xs transition-colors inline-flex items-center justify-center cursor-pointer">
        Return to Project Overview
      </button>

    </div>
  `
})
export class ProjectTabPlaceholderComponent {
  public tab = input.required<ProjectWorkspaceTabType>();
  public project = input<ProjectWorkspaceDetail | null>(null);
  public navigateOverview = output<void>();

  public getTabLabel(): string {
    switch (this.tab()) {
      case 'migrations': return 'Migrations Workload Management';
      case 'validations': return 'Validation Missions & Findings';
      case 'resources': return 'Resource Connections & Vault';
      case 'activity': return 'Audit & Activity Stream';
      case 'access': return 'Access Governance & RBAC';
      case 'governance': return 'Cutover Policies & Signoffs';
      case 'settings': return 'Project Settings & Configuration';
      default: return 'Workspace Surface';
    }
  }

  public getTabIcon(): string {
    switch (this.tab()) {
      case 'migrations': return 'arrow-left-right';
      case 'validations': return 'check-circle-2';
      case 'resources': return 'database';
      case 'activity': return 'activity';
      case 'access': return 'shield';
      case 'governance': return 'scale';
      case 'settings': return 'settings';
      default: return 'layers';
    }
  }

  public getTabDescription(): string {
    switch (this.tab()) {
      case 'migrations':
        return 'Manage and monitor continuous replication pipelines, snapshot tasks, and batch migrations scoped to this project.';
      case 'validations':
        return 'Execute data reconciliation missions, schema parity checks, and verify zero data loss guarantees.';
      case 'resources':
        return 'Review database connection endpoints, telemetry topics, and storage vaults associated with this project boundary.';
      case 'activity':
        return 'Inspect chronological operational events, pipeline transitions, and governance approvals.';
      case 'access':
        return 'Configure team permissions, service account tokens, and multi-principal signoff rules.';
      case 'governance':
        return 'Manage 4-eyes authorization gates, cutover checklists, and regulatory compliance artifacts.';
      case 'settings':
        return 'Update project general metadata, delete protection, and archive lifecycle policies.';
      default:
        return 'Surface information for this project scope.';
    }
  }
}
