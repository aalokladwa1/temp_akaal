import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ConnectionWorkspaceService } from '../connection-workspace.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-tab-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    @if (ws.connection(); as conn) {
      <div class="flex flex-col gap-6 animate-in fade-in duration-150 text-xs select-none">
        
        <!-- Top Header -->
        <div class="flex items-center justify-between pb-3 border-b border-slate-200">
          <div class="flex flex-col gap-0.5">
            <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider font-heading">
              Connection Settings &amp; Governance
            </h2>
            <p class="text-xs text-slate-500 font-normal">
              Resource-level metadata, organizational context, lifecycle deactivation, and controlled deletion.
            </p>
          </div>
        </div>

        <!-- ========================================================================= -->
        <!-- 1. GENERAL METADATA SECTION                                               -->
        <!-- ========================================================================= -->
        <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div class="flex items-center gap-2">
              <app-lucide-icon name="edit-3" [size]="16" class="text-blue-600"></app-lucide-icon>
              <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
                1. General Resource Metadata
              </span>
            </div>
            
            <button
              type="button"
              (click)="onSaveMetadata()"
              class="h-8 px-4 rounded-md text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white transition-colors cursor-pointer shadow-2xs">
              Save Metadata
            </button>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1">
              <label class="text-[11px] font-semibold text-slate-700">Connection Display Name</label>
              <input
                type="text"
                [(ngModel)]="editName"
                class="h-8 px-3 rounded-md bg-white border border-slate-300 text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-500 shadow-2xs" />
            </div>

            <div class="flex flex-col gap-1">
              <label class="text-[11px] font-semibold text-slate-700">Environment Tag</label>
              <input
                type="text"
                [value]="conn.environment"
                disabled
                class="h-8 px-3 rounded-md bg-slate-50 border border-slate-200 text-xs font-medium text-slate-500 cursor-not-allowed" />
            </div>

            <div class="col-span-full flex flex-col gap-1">
              <label class="text-[11px] font-semibold text-slate-700">Description</label>
              <textarea
                rows="2"
                [(ngModel)]="editDescription"
                class="p-2.5 rounded-md bg-white border border-slate-300 text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-500 shadow-2xs resize-none"></textarea>
            </div>
          </div>
        </div>

        <!-- ========================================================================= -->
        <!-- 2. ACCESS & ASSOCIATION CONTEXT                                           -->
        <!-- ========================================================================= -->
        <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div class="flex items-center gap-2">
              <app-lucide-icon name="building-2" [size]="16" class="text-blue-600"></app-lucide-icon>
              <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
                2. Organizational &amp; Access Context
              </span>
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg flex flex-col gap-1">
              <span class="text-[10px] font-medium text-slate-400">Owning Organization</span>
              <span class="text-xs font-bold text-slate-900">{{ conn.organizationName }}</span>
              <span class="text-[10px] font-mono text-slate-400">{{ conn.organizationId }}</span>
            </div>

            <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg flex flex-col gap-1">
              <span class="text-[10px] font-medium text-slate-400">Assigned Workspace</span>
              <span class="text-xs font-bold text-slate-900">{{ conn.workspaceName }}</span>
              <span class="text-[10px] font-mono text-slate-400">{{ conn.workspaceId }}</span>
            </div>

            <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg flex flex-col gap-1">
              <span class="text-[10px] font-medium text-slate-400">Sharing &amp; Governance Scope</span>
              <span class="text-xs font-bold text-slate-900">Workspace Shared</span>
              <span class="text-[10px] text-slate-500">Reusable across all projects</span>
            </div>
          </div>
        </div>

        <!-- ========================================================================= -->
        <!-- 3. LIFECYCLE MANAGEMENT (DISABLE / ARCHIVE)                               -->
        <!-- ========================================================================= -->
        <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-5">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div class="flex items-center gap-2">
              <app-lucide-icon name="archive" [size]="16" class="text-blue-600"></app-lucide-icon>
              <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
                3. Lifecycle Governance
              </span>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            <!-- Disable Action -->
            <div class="p-4 bg-slate-50/70 border border-slate-200 rounded-xl flex flex-col justify-between gap-3">
              <div class="flex flex-col gap-1">
                <span class="text-xs font-bold text-slate-900">
                  {{ conn.lifecycleState === 'ACTIVE' ? 'Disable Connection Profile' : 'Re-Enable Connection Profile' }}
                </span>
                <p class="text-xs text-slate-500 leading-relaxed">
                  Temporarily prevent new migration projects from selecting this connection. Active executions continue running without interruption.
                </p>
              </div>

              <div class="pt-2">
                <button
                  type="button"
                  (click)="ws.toggleDisableConnection()"
                  class="h-8 px-3.5 rounded-md text-xs font-semibold border transition-colors cursor-pointer"
                  [class.bg-white]="conn.lifecycleState === 'ACTIVE'"
                  [class.hover:bg-amber-50]="conn.lifecycleState === 'ACTIVE'"
                  [class.text-amber-800]="conn.lifecycleState === 'ACTIVE'"
                  [class.border-amber-300]="conn.lifecycleState === 'ACTIVE'"
                  [class.bg-emerald-600]="conn.lifecycleState !== 'ACTIVE'"
                  [class.hover:bg-emerald-700]="conn.lifecycleState !== 'ACTIVE'"
                  [class.text-white]="conn.lifecycleState !== 'ACTIVE'"
                  [class.border-emerald-600]="conn.lifecycleState !== 'ACTIVE'">
                  {{ conn.lifecycleState === 'ACTIVE' ? 'Disable Connection' : 'Enable Connection' }}
                </button>
              </div>
            </div>

            <!-- Archive Action -->
            <div class="p-4 bg-slate-50/70 border border-slate-200 rounded-xl flex flex-col justify-between gap-3">
              <div class="flex flex-col gap-1">
                <span class="text-xs font-bold text-slate-900">Archive Connection</span>
                <p class="text-xs text-slate-500 leading-relaxed">
                  Preserve complete audit records and historical migration references while permanently retiring this profile from active work.
                </p>
              </div>

              <div class="pt-2">
                <button
                  type="button"
                  (click)="ws.archiveConnection()"
                  [disabled]="conn.lifecycleState === 'ARCHIVED'"
                  class="h-8 px-3.5 rounded-md text-xs font-semibold bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 transition-colors cursor-pointer disabled:opacity-50">
                  {{ conn.lifecycleState === 'ARCHIVED' ? 'Archived' : 'Archive Connection' }}
                </button>
              </div>
            </div>

          </div>
        </div>

        <!-- ========================================================================= -->
        <!-- 4. DANGER ZONE (RESTRICTED PERMISSION / DELETION BLOCKED CONTEXT)          -->
        <!-- ========================================================================= -->
        <div class="p-6 bg-white border border-rose-200 rounded-xl shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-rose-100">
            <div class="flex items-center gap-2">
              <app-lucide-icon name="alert-triangle" [size]="16" class="text-rose-600"></app-lucide-icon>
              <span class="text-xs font-bold text-rose-900 uppercase tracking-wider font-heading">
                4. Permanent Deletion (Danger Zone)
              </span>
            </div>
          </div>

          <div class="flex items-start justify-between gap-6 flex-wrap">
            <div class="flex flex-col gap-1 max-w-xl">
              <span class="text-xs font-bold text-slate-900">Delete Connection Resource</span>
              
              @if (!conn.usage.referenceProtection.canDelete) {
                <div class="p-3 bg-rose-50/60 border border-rose-200 rounded-lg text-xs text-rose-900 mt-1">
                  <strong class="font-bold">Permanent Deletion Blocked by Enterprise Governance:</strong>
                  <p class="pt-1 text-rose-800 leading-relaxed">
                    {{ conn.usage.referenceProtection.blockReason || 'This Connection has active or historical references in Projects and Migrations. Use Archive to safely retire this profile.' }}
                  </p>
                </div>
              } @else {
                <p class="text-xs text-slate-500 leading-relaxed">
                  Permanently remove this unused connection profile. This action cannot be undone.
                </p>
              }
            </div>

            <div class="pt-1">
              @if (conn.usage.referenceProtection.canDelete) {
                <button
                  type="button"
                  (click)="ws.deleteConnection()"
                  class="h-8 px-4 rounded-md text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white transition-colors cursor-pointer shadow-2xs">
                  Delete Connection
                </button>
              } @else {
                <button
                  type="button"
                  disabled
                  class="h-8 px-4 rounded-md text-xs font-semibold bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed"
                  title="Deletion is blocked because this Connection is referenced by active workflows.">
                  Delete Connection
                </button>
              }
            </div>
          </div>
        </div>

      </div>
    }
  `
})
export class TabSettingsComponent {
  public ws = inject(ConnectionWorkspaceService);

  public editName = '';
  public editDescription = '';

  constructor() {
    const conn = this.ws.connection();
    if (conn) {
      this.editName = conn.name;
      this.editDescription = conn.description;
    }
  }

  public onSaveMetadata(): void {
    const conn = this.ws.connection();
    if (!conn) return;
    this.ws.saveMetadata(this.editName, this.editDescription, conn.tags);
  }
}
