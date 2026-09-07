import { Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { EntityAvailabilityState } from '../projects.models';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-projects-state-fallback',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="p-8 sm:p-12 rounded-xl bg-white border border-slate-200 shadow-2xs flex flex-col items-center justify-center text-center gap-3 select-none">
      
      @switch (state()) {
        
        @case ('LOADING') {
          <div class="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 animate-spin">
            <app-lucide-icon name="refresh-cw" [size]="20"></app-lucide-icon>
          </div>
          <h3 class="text-sm font-bold text-slate-900 font-heading">Loading Portfolio Entities...</h3>
          <p class="text-xs text-slate-500 max-w-md font-medium leading-relaxed">
            Synchronizing projects, initiatives, and operational state for the active workspace.
          </p>
        }

        @case ('NOT_CONNECTED') {
          <div class="w-10 h-10 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600">
            <app-lucide-icon name="unplug" [size]="20"></app-lucide-icon>
          </div>
          <h3 class="text-sm font-bold text-slate-900 font-heading">Backend Authority Not Connected</h3>
          <p class="text-xs text-slate-500 max-w-md font-medium leading-relaxed">
            Projects &amp; Initiatives authority integration is in-flight for P7D. The module is operating in local preview mode.
          </p>
          <button
            type="button"
            (click)="retry.emit()"
            class="mt-2 h-8 px-3.5 rounded-md bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-semibold shadow-2xs cursor-pointer inline-flex items-center justify-center">
            Retry Connection
          </button>
        }

        @case ('UNAVAILABLE') {
          <div class="w-10 h-10 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600">
            <app-lucide-icon name="alert-triangle" [size]="20"></app-lucide-icon>
          </div>
          <h3 class="text-sm font-bold text-slate-900 font-heading">Service Currently Unavailable</h3>
          <p class="text-xs text-slate-500 max-w-md font-medium leading-relaxed">
            Unable to communicate with the migration orchestration kernel. Verify engine daemon status.
          </p>
          <button
            type="button"
            (click)="retry.emit()"
            class="mt-2 h-8 px-3.5 rounded-md bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-semibold shadow-2xs cursor-pointer inline-flex items-center justify-center">
            Retry Connection
          </button>
        }

        @case ('UNAUTHORIZED') {
          <div class="w-10 h-10 rounded-lg bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-600">
            <app-lucide-icon name="shield-alert" [size]="20"></app-lucide-icon>
          </div>
          <h3 class="text-sm font-bold text-slate-900 font-heading">Access Denied</h3>
          <p class="text-xs text-slate-500 max-w-md font-medium leading-relaxed">
            Your principal does not have read permissions for projects within this workspace. Contact your security administrator.
          </p>
        }

        @case ('ERROR') {
          <div class="w-10 h-10 rounded-lg bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-600">
            <app-lucide-icon name="circle-alert" [size]="20"></app-lucide-icon>
          </div>
          <h3 class="text-sm font-bold text-slate-900 font-heading">Failed to Retrieve Portfolio</h3>
          <p class="text-xs text-slate-500 max-w-md font-medium leading-relaxed">
            {{ customErrorMessage() || 'An unexpected error occurred while querying the portfolio repository.' }}
          </p>
          <button
            type="button"
            (click)="retry.emit()"
            class="mt-2 h-8 px-3.5 rounded-md bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-semibold shadow-2xs cursor-pointer inline-flex items-center justify-center">
            Retry Request
          </button>
        }

        @default {
          <!-- EMPTY STATE -->
          <div class="w-10 h-10 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-400">
            <app-lucide-icon name="folder-open" [size]="20"></app-lucide-icon>
          </div>
          <h3 class="text-sm font-bold text-slate-900 font-heading">
            {{ entityName() === 'initiatives' ? 'No Initiatives Configured' : (entityName() === 'migrations' ? 'No Migrations in this Project' : (entityName() === 'validations' ? 'No Validation Missions in this Project' : (entityName() === 'resources' ? 'No Resources Available' : (entityName() === 'activity' ? 'No Activity Events Recorded' : (entityName() === 'access' ? 'No Access Grants Found' : (entityName() === 'governance' ? 'No Governance Policies Active' : 'No Projects in this Workspace')))))) }}
          </h3>
          <p class="text-xs text-slate-500 max-w-md font-medium leading-relaxed">
            {{ entityName() === 'initiatives'
              ? 'Initiatives group multiple related migration projects toward a strategic objective.'
              : (entityName() === 'migrations'
                ? 'Create a migration pipeline to begin planning data movement within this project context.'
                : (entityName() === 'validations'
                  ? 'Create a Validation Mission to verify schema parity, row cardinality, or full attribute integrity.'
                  : (entityName() === 'resources'
                    ? 'Ensure connection profiles have been registered in the workspace inventory.'
                    : (entityName() === 'activity'
                      ? 'Operator events will appear as pipelines and validations are exercised.'
                      : (entityName() === 'access'
                        ? 'Assign project-scoped roles to users, groups, or automated service accounts.'
                        : (entityName() === 'governance'
                          ? 'Governance gates and policy requirements will appear as workflows are defined.'
                          : 'Create a governed Project to organize and track migration workflows and validation missions.')))))) }}
          </p>
        }

      }

    </div>
  `
})
export class ProjectsStateFallbackComponent {
  public state = input<EntityAvailabilityState>('EMPTY');
  public entityName = input<string>('projects');
  public customErrorMessage = input<string>('');
  public retry = output<void>();
}
