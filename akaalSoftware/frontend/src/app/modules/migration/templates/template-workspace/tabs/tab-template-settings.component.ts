import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TemplateWorkspaceService } from '../template-workspace.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';
import { TemplateScope } from '../../templates.models';

@Component({
  selector: 'app-tab-template-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 text-xs font-sans animate-in fade-in duration-150">
      
      @if (ws.template(); as tmpl) {
        
        <!-- SECTION 1: GENERAL METADATA SETTINGS -->
        <div class="p-5 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between border-b border-slate-100 pb-3">
            <div class="flex flex-col">
              <span class="font-bold text-slate-900 text-sm">General Template Metadata</span>
              <span class="text-xs text-slate-500 font-normal">Identities and descriptive metadata used across workspace and migration catalogs.</span>
            </div>
          </div>

          <div class="grid grid-cols-1 gap-4 max-w-2xl">
            
            <!-- Name -->
            <div class="flex flex-col gap-1.5">
              <label for="settings-name" class="font-semibold text-slate-800">Template Name</label>
              <input
                id="settings-name"
                type="text"
                [ngModel]="tmpl.name"
                class="h-9 px-3 bg-white border border-slate-200 rounded-md text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-600 shadow-2xs" />
            </div>

            <!-- Description -->
            <div class="flex flex-col gap-1.5">
              <label for="settings-desc" class="font-semibold text-slate-800">Description & Purpose</label>
              <textarea
                id="settings-desc"
                rows="3"
                [ngModel]="tmpl.description"
                class="p-3 bg-white border border-slate-200 rounded-md text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-600 shadow-2xs resize-none"></textarea>
            </div>

          </div>
        </div>

        <!-- SECTION 2: AVAILABILITY & SCOPE BOUNDARY -->
        <div class="p-5 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between border-b border-slate-100 pb-3">
            <div class="flex flex-col">
              <span class="font-bold text-slate-900 text-sm">Availability Perimeter</span>
              <span class="text-xs text-slate-500 font-normal">Controls which organizations, workspaces, and projects can view and instantiate this template.</span>
            </div>
            <span class="px-2.5 py-0.5 text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200 rounded-md uppercase">
              Current: {{ tmpl.scope }}
            </span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            
            <div
              class="p-3.5 rounded-lg border flex flex-col gap-1.5 cursor-pointer transition-all"
              [class]="tmpl.scope === 'ORGANIZATION' ? 'bg-blue-50/50 border-blue-600 shadow-xs' : 'bg-white border-slate-200 hover:bg-slate-50'">
              <div class="flex items-center justify-between">
                <span class="font-bold text-slate-900">Organization</span>
                @if (tmpl.scope === 'ORGANIZATION') {
                  <span class="w-2 h-2 rounded-full bg-blue-600"></span>
                }
              </div>
              <p class="text-[11px] text-slate-600 font-normal m-0 leading-relaxed">
                Available to all operators across all workspaces in this organization.
              </p>
            </div>

            <div
              class="p-3.5 rounded-lg border flex flex-col gap-1.5 cursor-pointer transition-all"
              [class]="tmpl.scope === 'WORKSPACE' ? 'bg-blue-50/50 border-blue-600 shadow-xs' : 'bg-white border-slate-200 hover:bg-slate-50'">
              <div class="flex items-center justify-between">
                <span class="font-bold text-slate-900">Workspace</span>
                @if (tmpl.scope === 'WORKSPACE') {
                  <span class="w-2 h-2 rounded-full bg-blue-600"></span>
                }
              </div>
              <p class="text-[11px] text-slate-600 font-normal m-0 leading-relaxed">
                Restricted to migration pipelines within the current workspace boundary.
              </p>
            </div>

            <div
              class="p-3.5 rounded-lg border flex flex-col gap-1.5 cursor-pointer transition-all"
              [class]="tmpl.scope === 'PROJECT' ? 'bg-blue-50/50 border-blue-600 shadow-xs' : 'bg-white border-slate-200 hover:bg-slate-50'">
              <div class="flex items-center justify-between">
                <span class="font-bold text-slate-900">Project</span>
                @if (tmpl.scope === 'PROJECT') {
                  <span class="w-2 h-2 rounded-full bg-blue-600"></span>
                }
              </div>
              <p class="text-[11px] text-slate-600 font-normal m-0 leading-relaxed">
                Restricted exclusively to a designated project.
              </p>
            </div>

          </div>
        </div>

        <!-- SECTION 3: LIFECYCLE MANAGEMENT -->
        <div class="p-5 bg-white border border-slate-200 rounded-lg shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between border-b border-slate-100 pb-3">
            <div class="flex flex-col">
              <span class="font-bold text-slate-900 text-sm">Lifecycle Management</span>
              <span class="text-xs text-slate-500 font-normal">Govern the operational state of this template.</span>
            </div>
            <span class="px-2.5 py-0.5 text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-md">
              {{ tmpl.lifecycle }}
            </span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            <!-- Deprecate Card -->
            <div class="p-4 bg-slate-50 border border-slate-200 rounded-lg flex flex-col justify-between gap-3">
              <div class="flex flex-col gap-1">
                <span class="font-bold text-slate-900 text-xs">Deprecate Template</span>
                <p class="text-[11px] text-slate-600 m-0 leading-relaxed font-normal">
                  Marks the template as deprecated to discourage new migrations. Existing running migrations remain unaffected.
                </p>
              </div>
              <button
                type="button"
                [disabled]="tmpl.lifecycle === 'DEPRECATED' || tmpl.lifecycle === 'ARCHIVED'"
                (click)="ws.openDeprecateDialog()"
                class="h-8 px-3.5 rounded-md bg-white hover:bg-slate-100 border border-slate-200 text-slate-800 font-semibold text-xs transition-colors cursor-pointer disabled:opacity-40 disabled:pointer-events-none self-start shadow-2xs">
                Deprecate Template
              </button>
            </div>

            <!-- Archive Card -->
            <div class="p-4 bg-slate-50 border border-slate-200 rounded-lg flex flex-col justify-between gap-3">
              <div class="flex flex-col gap-1">
                <span class="font-bold text-slate-900 text-xs">Archive Template</span>
                <p class="text-[11px] text-slate-600 m-0 leading-relaxed font-normal">
                  Archives the template into read-only cold storage. Historical audit records and lineage remain fully preserved.
                </p>
              </div>
              <button
                type="button"
                [disabled]="tmpl.lifecycle === 'ARCHIVED'"
                (click)="ws.openArchiveDialog()"
                class="h-8 px-3.5 rounded-md bg-white hover:bg-slate-100 border border-slate-200 text-slate-800 font-semibold text-xs transition-colors cursor-pointer disabled:opacity-40 disabled:pointer-events-none self-start shadow-2xs">
                Archive Template
              </button>
            </div>

          </div>
        </div>

        <!-- SECTION 4: DESTRUCTIVE ACTIONS ZONE -->
        <div class="p-5 bg-white border border-rose-200 rounded-lg shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between border-b border-rose-100 pb-3">
            <div class="flex flex-col">
              <span class="font-bold text-rose-900 text-sm">Destructive Actions Zone</span>
              <span class="text-xs text-rose-600 font-normal">Permanent deletion of this template specification.</span>
            </div>
            <app-lucide-icon name="alert-triangle" [size]="16" class="text-rose-600"></app-lucide-icon>
          </div>

          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 bg-rose-50/50 border border-rose-200 rounded-md">
            <div class="flex flex-col gap-1">
              <span class="font-bold text-slate-900 text-xs">Delete Template Specification</span>
              <p class="text-[11px] text-slate-600 m-0 font-normal leading-relaxed max-w-xl">
                @if (tmpl.referenceProtection.isProtected) {
                  <span class="text-rose-700 font-semibold">Deletion Blocked:</span> {{ tmpl.referenceProtection.reason }}
                } @else {
                  Permanently deletes this template definition. Historical migrations created from this template retain their independent configuration.
                }
              </p>
            </div>

            <button
              type="button"
              [disabled]="tmpl.referenceProtection.isProtected"
              (click)="ws.openDeleteDialog()"
              class="h-8 px-4 rounded-md bg-rose-600 hover:bg-rose-700 text-white font-semibold text-xs transition-colors cursor-pointer disabled:opacity-40 disabled:pointer-events-none shrink-0 shadow-2xs">
              Delete Template
            </button>
          </div>
        </div>

      }

    </div>
  `
})
export class TabTemplateSettingsComponent {
  public ws = inject(TemplateWorkspaceService);
}
