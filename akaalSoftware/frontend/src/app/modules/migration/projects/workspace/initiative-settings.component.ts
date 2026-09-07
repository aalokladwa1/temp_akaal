import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-initiative-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 max-w-4xl mx-auto py-2">
      
      @if (ps.activeInitiative(); as init) {
        
        <!-- =============================================================== -->
        <!-- 1. GENERAL INITIATIVE SETTINGS                                  -->
        <!-- =============================================================== -->
        <div class="p-6 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-5">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div class="flex items-center gap-2">
              <app-lucide-icon name="sliders" [size]="16" class="text-blue-600"></app-lucide-icon>
              <h3 class="text-sm font-bold text-slate-900 uppercase tracking-wider font-heading">
                General Settings
              </h3>
            </div>
            @if (isSavedSuccess()) {
              <span class="text-xs font-semibold text-emerald-600 flex items-center gap-1">
                <app-lucide-icon name="check" [size]="13"></app-lucide-icon>
                <span>Changes applied</span>
              </span>
            }
          </div>

          <div class="flex flex-col gap-4">
            
            <!-- Initiative Name -->
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-800">
                <span>Initiative Name</span>
                <span class="text-rose-500 font-bold">*</span>
              </label>
              <input
                type="text"
                [(ngModel)]="editName"
                placeholder="Initiative title..."
                class="w-full h-9.5 px-3.5 text-xs bg-white border border-slate-300 rounded-md text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-medium transition-all"
              />
            </div>

            <!-- Objective / Description -->
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-800">
                <span>Strategic Objective &amp; Scope</span>
              </label>
              <textarea
                rows="4"
                [(ngModel)]="editObjective"
                placeholder="Strategic objective details..."
                class="w-full p-3 text-xs bg-white border border-slate-300 rounded-md text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-normal leading-relaxed resize-y">
              </textarea>
            </div>

          </div>

          <div class="pt-3 border-t border-slate-100 flex items-center justify-between">
            <span class="text-[11px] text-slate-500 font-medium">
              Changes record local operator intent. Canonical persistence connects in Pre-P7D.
            </span>
            <div class="flex items-center gap-2">
              <button
                type="button"
                (click)="resetForm()"
                [disabled]="!isDirty()"
                class="h-8.5 px-3 rounded-md border border-slate-200 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-colors shadow-2xs">
                Reset
              </button>
              <button
                type="button"
                (click)="saveGeneral()"
                [disabled]="!isDirty() || !editName.trim()"
                class="h-8.5 px-4 rounded-md bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-semibold cursor-pointer transition-colors shadow-2xs">
                Save Changes
              </button>
            </div>
          </div>

        </div>

        <!-- =============================================================== -->
        <!-- 2. PROJECT ASSOCIATIONS MANAGEMENT                              -->
        <!-- =============================================================== -->
        <div class="p-6 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4">
          <div class="flex items-center gap-2 pb-3 border-b border-slate-100">
            <app-lucide-icon name="layers" [size]="16" class="text-blue-600"></app-lucide-icon>
            <h3 class="text-sm font-bold text-slate-900 uppercase tracking-wider font-heading">
              Project Association Scope
            </h3>
          </div>

          <div class="flex items-center justify-between gap-4 text-xs">
            <div class="flex flex-col gap-1">
              <span class="font-bold text-slate-900">{{ init.associatedProjectIds.length }} Associated Projects</span>
              <p class="text-slate-500 font-normal">Manage which database migration projects belong to this portfolio group.</p>
            </div>
            <button
              type="button"
              (click)="ps.setActiveTab('projects')"
              class="h-8.5 px-3.5 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold transition-colors cursor-pointer shadow-2xs">
              Manage in Projects Tab &rarr;
            </button>
          </div>
        </div>

        <!-- =============================================================== -->
        <!-- 3. GOVERNANCE & LIFECYCLE MANAGEMENT                           -->
        <!-- =============================================================== -->
        <div class="p-6 rounded-xl bg-white border border-rose-200/80 shadow-xs flex flex-col gap-4">
          <div class="flex items-center gap-2 pb-3 border-b border-rose-100 text-rose-700">
            <app-lucide-icon name="alert-triangle" [size]="16"></app-lucide-icon>
            <h3 class="text-sm font-bold uppercase tracking-wider font-heading">
              Governance &amp; Lifecycle
            </h3>
          </div>

          <div class="flex items-center justify-between gap-4 text-xs">
            <div class="flex flex-col gap-1">
              <span class="font-bold text-slate-900">Archive Initiative</span>
              <p class="text-slate-500 font-normal">
                Archiving marks the initiative as closed. Associated projects remain operational as standalone entities.
              </p>
            </div>

            @if (init.status !== 'ARCHIVED') {
              <button
                type="button"
                (click)="isArchiveModalOpen.set(true)"
                class="h-8.5 px-3.5 rounded-md bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 text-xs font-semibold cursor-pointer transition-colors shadow-2xs shrink-0">
                Archive Initiative
              </button>
            } @else {
              <span class="px-2.5 py-1 rounded-md bg-slate-100 text-slate-600 border border-slate-200 font-semibold text-xs">
                Archived
              </span>
            }
          </div>
        </div>

      }

      <!-- Archive Confirmation Guardrail Modal -->
      @if (isArchiveModalOpen()) {
        <div
          class="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150"
          (click)="isArchiveModalOpen.set(false)">
          <div
            class="w-full max-w-md bg-white border border-slate-200 rounded-xl shadow-2xl p-6 space-y-4"
            (click)="$event.stopPropagation()">
            
            <div class="flex items-center gap-3 text-rose-600">
              <div class="w-10 h-10 rounded-lg bg-rose-50 border border-rose-200 flex items-center justify-center shrink-0">
                <app-lucide-icon name="alert-triangle" [size]="20"></app-lucide-icon>
              </div>
              <div class="flex flex-col">
                <h3 class="text-base font-bold text-slate-900 font-heading">Archive Initiative</h3>
                <span class="text-[11px] text-rose-600 font-semibold uppercase tracking-wider">Governed Lifecycle Operation</span>
              </div>
            </div>

            <p class="text-xs text-slate-700 leading-relaxed font-normal">
              You are archiving <strong>{{ ps.activeInitiative()?.name }}</strong>. This will close portfolio rollup tracking for this initiative.
            </p>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-semibold text-slate-700">
                Type <span class="font-mono font-bold text-rose-700 select-all">ARCHIVE INITIATIVE</span> to confirm:
              </label>
              <input
                type="text"
                [(ngModel)]="archiveConfirmInput"
                placeholder="ARCHIVE INITIATIVE"
                class="w-full h-9 px-3 text-xs bg-white border border-slate-300 focus:border-rose-600 rounded-md text-slate-900 font-mono focus:outline-none"
                autofocus
              />
            </div>

            <div class="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100">
              <button
                type="button"
                (click)="isArchiveModalOpen.set(false)"
                class="h-8.5 px-3.5 text-xs font-medium text-slate-600 hover:text-slate-800 bg-white border border-slate-200 rounded-md cursor-pointer hover:bg-slate-50 transition-colors shadow-2xs">
                Cancel
              </button>
              <button
                type="button"
                (click)="confirmArchive()"
                [disabled]="archiveConfirmInput.trim() !== 'ARCHIVE INITIATIVE'"
                class="h-8.5 px-4 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 disabled:opacity-40 disabled:cursor-not-allowed rounded-md shadow-2xs transition-colors cursor-pointer">
                Confirm &amp; Archive
              </button>
            </div>

          </div>
        </div>
      }

    </div>
  `
})
export class InitiativeSettingsComponent implements OnInit {
  public ps = inject(ProjectsService);
  private router = inject(Router);

  public editName = '';
  public editObjective = '';
  public isSavedSuccess = signal<boolean>(false);
  public isArchiveModalOpen = signal<boolean>(false);
  public archiveConfirmInput = '';

  ngOnInit(): void {
    this.resetForm();
  }

  public resetForm(): void {
    const init = this.ps.activeInitiative();
    if (init) {
      this.editName = init.name;
      this.editObjective = init.objective || init.description || '';
    }
  }

  public isDirty(): boolean {
    const init = this.ps.activeInitiative();
    if (!init) return false;
    return this.editName.trim() !== init.name ||
      this.editObjective.trim() !== (init.objective || init.description || '').trim();
  }

  public saveGeneral(): void {
    const init = this.ps.activeInitiative();
    if (init && this.editName.trim()) {
      this.ps.updateInitiativeGeneral(init.id, this.editName.trim(), this.editObjective.trim());
      this.isSavedSuccess.set(true);
      setTimeout(() => this.isSavedSuccess.set(false), 3000);
    }
  }

  public confirmArchive(): void {
    const init = this.ps.activeInitiative();
    if (init && this.archiveConfirmInput.trim() === 'ARCHIVE INITIATIVE') {
      this.ps.archiveInitiative(init.id);
      this.isArchiveModalOpen.set(false);
      this.archiveConfirmInput = '';
    }
  }
}
