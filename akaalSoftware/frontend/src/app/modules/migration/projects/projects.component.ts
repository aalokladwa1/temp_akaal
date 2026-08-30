import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { DialogModule } from 'primeng/dialog';
import { MigrationUiService } from '../../../core/services/migration-ui.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { ProjectItem } from '../../../core/models/migration-view.models';

@Component({
  selector: 'app-projects',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, DialogModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto pb-16 font-sans select-none animate-in fade-in duration-150">
      
      <!-- Header -->
      <div class="flex items-center justify-between gap-4 pb-4 border-b border-slate-200 flex-wrap">
        <div class="flex flex-col gap-1">
          <span class="text-xs font-semibold text-slate-500">Initiatives &amp; Coordination</span>
          <h1 class="text-2xl font-bold font-heading text-slate-900 tracking-tight">Projects &amp; Workspaces</h1>
          <p class="text-xs text-slate-600 font-medium">Multi-migration initiatives with dependency coordination and team access governance.</p>
        </div>

        <button
          type="button"
          (click)="isCreateModalOpen.set(true)"
          class="h-9 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-xs flex items-center gap-2 transition-colors cursor-pointer">
          <app-lucide-icon name="plus" [size]="15"></app-lucide-icon>
          <span>Create Project</span>
        </button>
      </div>

      <!-- Projects Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
        @for (proj of ms.projects(); track proj.id) {
          <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col justify-between gap-5">
            <div class="flex flex-col gap-3">
              <div class="flex items-center justify-between">
                <span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">{{ proj.key }}</span>
                <span class="text-xs font-semibold text-slate-500">{{ proj.membersCount }} Members</span>
              </div>
              <h3 class="text-base font-bold text-slate-900">{{ proj.name }}</h3>
              <p class="text-xs text-slate-600 font-medium leading-relaxed">{{ proj.description }}</p>
            </div>

            <div class="pt-4 border-t border-slate-100 flex items-center justify-between">
              <div class="flex items-center gap-4 text-xs font-medium text-slate-600">
                <span>{{ proj.activeMigrationsCount }} Active Migrations</span>
                <span>Target: {{ proj.targetMilestone }}</span>
              </div>

              <a
                [routerLink]="['/migration/projects', proj.id]"
                class="px-4 py-2 rounded-xl bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-bold transition-colors inline-flex items-center gap-1.5 cursor-pointer">
                <span>Open Project Workspace</span>
                <app-lucide-icon name="chevron-right" [size]="14"></app-lucide-icon>
              </a>
            </div>
          </div>
        }
      </div>

      <!-- Fast Create Project Modal -->
      <p-dialog
        [(visible)]="isCreateModalOpen"
        [modal]="true"
        [closable]="true"
        [draggable]="false"
        [style]="{ width: '90vw', maxWidth: '540px' }">
        <ng-template #header>
          <h3 class="text-sm font-bold text-slate-900">Create New Project Initiative</h3>
        </ng-template>
        
        <div class="flex flex-col gap-3 text-xs font-medium">
          <div class="flex flex-col gap-1">
            <label class="font-bold text-slate-800">Project Name *</label>
            <input type="text" placeholder="e.g. Payments Cloud Migration 2026" class="px-3.5 py-2.5 rounded-xl bg-slate-50 border border-slate-200" />
          </div>
          <div class="flex flex-col gap-1">
            <label class="font-bold text-slate-800">Project Key *</label>
            <input type="text" placeholder="PAY-2026" class="px-3.5 py-2.5 rounded-xl bg-slate-50 border border-slate-200 uppercase font-mono" />
          </div>
        </div>

        <ng-template #footer>
          <div class="flex justify-end gap-2">
            <button type="button" (click)="isCreateModalOpen.set(false)" class="px-4 py-2 rounded-xl bg-slate-100 text-slate-700 text-xs font-bold">Cancel</button>
            <button type="button" (click)="isCreateModalOpen.set(false)" class="px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-bold">Create</button>
          </div>
        </ng-template>
      </p-dialog>

    </div>
  `
})
export class ProjectsComponent {
  public ms = inject(MigrationUiService);
  public isCreateModalOpen = signal<boolean>(false);
}
