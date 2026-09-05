import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Step6ConfigurationStoreService } from '../../../../core/services/step6-configuration-store.service';
import { CustomActionItem, CustomActionHook } from './step6-configuration.models';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CodeEditorComponent } from '../../../../shared/components/code-editor.component';
import { CustomSelectComponent } from '../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-configuration-actions-modal',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent, CodeEditorComponent, CustomSelectComponent],
  template: `
    <div
      role="dialog"
      aria-modal="true"
      class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 animate-in fade-in duration-100 font-sans text-xs select-none"
      (click)="store.closeCustomActionModal()">
      
      <div
        class="w-full max-w-2xl bg-white rounded-xl border border-slate-200 overflow-hidden flex flex-col h-[580px] animate-in zoom-in-95 duration-100"
        (click)="$event.stopPropagation()">
        
        <!-- Modal Header -->
        <div class="px-6 py-4 border-b border-slate-200 bg-slate-50/70 flex items-center justify-between shrink-0">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center shrink-0">
              <app-lucide-icon name="file-code" [size]="16"></app-lucide-icon>
            </div>
            <div class="flex flex-col">
              <h3 class="text-sm font-bold text-slate-900">Custom SQL Execution Action</h3>
              <span class="text-[11px] text-slate-500 font-medium">Configure automated SQL scripts triggered at lifecycle boundaries</span>
            </div>
          </div>

          <button
            type="button"
            (click)="store.closeCustomActionModal()"
            class="text-slate-400 hover:text-slate-600 cursor-pointer">
            <app-lucide-icon name="x" [size]="16"></app-lucide-icon>
          </button>
        </div>

        <!-- Modal Body (Form & Code Editor) -->
        <div class="flex-1 p-6 overflow-y-auto flex flex-col gap-4 min-h-0">
          
          <!-- Top Row: Hook Selector & Action Name -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 shrink-0">
            
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-semibold text-slate-700">Execution Hook Stage <span class="text-rose-500">*</span></label>
              <app-custom-select
                [options]="hookOptions"
                [value]="actionDraft.hook"
                (valueChange)="onHookChange($event)">
              </app-custom-select>
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-semibold text-slate-700">Action Script Name <span class="text-rose-500">*</span></label>
              <input
                type="text"
                [(ngModel)]="actionDraft.name"
                placeholder="e.g. Set Target Search Path"
                class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
            </div>

          </div>

          <!-- Secondary Row: Timeout & Failure Policy -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 shrink-0">
            
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-semibold text-slate-700">Execution Timeout (Seconds)</label>
              <input
                type="number"
                [(ngModel)]="actionDraft.timeoutSec"
                min="10"
                max="3600"
                class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 font-mono focus:outline-none focus:border-blue-600" />
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-semibold text-slate-700">On Script Error Policy</label>
              <app-custom-select
                [options]="failurePolicyOptions"
                [value]="actionDraft.onFailure"
                (valueChange)="actionDraft.onFailure = $event">
              </app-custom-select>
            </div>

          </div>

          <!-- Code Editor Surface (Monaco / Fallback) -->
          <div class="flex-1 flex flex-col gap-1.5 min-h-[220px]">
            <div class="flex items-center justify-between">
              <label class="text-xs font-semibold text-slate-700">SQL Script Content <span class="text-rose-500">*</span></label>
              <span class="text-[11px] text-slate-400 font-mono">Target Database Dialect</span>
            </div>

            <div class="flex-1 border border-slate-200 rounded-lg overflow-hidden flex flex-col min-h-0 bg-white">
              <app-code-editor
                [code]="actionDraft.sql"
                [language]="'sql'"
                [ariaLabel]="'Custom SQL script editor'"
                (codeChange)="actionDraft.sql = $event">
              </app-code-editor>
            </div>
          </div>

        </div>

        <!-- Modal Footer -->
        <div class="px-6 py-3 border-t border-slate-200 bg-slate-50/70 flex items-center justify-between shrink-0">
          <div>
            @if (isExistingAction) {
              <button
                type="button"
                (click)="deleteAction()"
                class="h-8 px-3 text-xs font-semibold text-rose-700 hover:bg-rose-50 border border-rose-200 rounded-md cursor-pointer transition-colors">
                Delete Script
              </button>
            }
          </div>

          <div class="flex items-center gap-2">
            <button
              type="button"
              (click)="store.closeCustomActionModal()"
              class="h-8 px-3 text-xs font-medium text-slate-700 hover:text-slate-900 border border-slate-200 rounded-md bg-white hover:bg-slate-50 cursor-pointer transition-colors">
              Cancel
            </button>
            
            <button
              type="button"
              (click)="saveAction()"
              [disabled]="!isValid()"
              class="h-8 px-4 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:pointer-events-none rounded-md cursor-pointer transition-colors">
              Save Action Script
            </button>
          </div>
        </div>

      </div>

    </div>
  `
})
export class ConfigurationActionsModalComponent implements OnInit {
  public store = inject(Step6ConfigurationStoreService);

  public actionDraft: CustomActionItem = {
    id: '',
    hook: 'PRE_MIGRATION',
    hookLabel: 'Pre-migration',
    name: '',
    sql: '',
    timeoutSec: 120,
    onFailure: 'ABORT_MIGRATION',
    isEnabled: true
  };

  public isExistingAction: boolean = false;

  public readonly hookOptions = [
    { label: 'Pre-migration — Runs before any table/schema operations', value: 'PRE_MIGRATION' },
    { label: 'Post-schema — Runs immediately after DDL compilation', value: 'POST_SCHEMA' },
    { label: 'Post-bulk — Runs after initial data snapshot load', value: 'POST_BULK' },
    { label: 'Post-cutover — Runs after final cutover handoff', value: 'POST_CUTOVER' }
  ];

  public readonly failurePolicyOptions = [
    { label: 'Abort Migration — Stop and rollback if possible', value: 'ABORT_MIGRATION' },
    { label: 'Log & Continue — Record warning and proceed', value: 'LOG_AND_CONTINUE' }
  ];

  public ngOnInit(): void {
    const editing = this.store.editingAction();
    if (editing) {
      this.actionDraft = { ...editing };
      this.isExistingAction = this.store.draft().customActions.some(a => a.id === editing.id);
    }
  }

  public onHookChange(hook: CustomActionHook): void {
    this.actionDraft.hook = hook;
    this.actionDraft.hookLabel = this.store.getHookLabel(hook);
  }

  public isValid(): boolean {
    return !!(this.actionDraft.name.trim() && this.actionDraft.sql.trim());
  }

  public saveAction(): void {
    if (this.isValid()) {
      this.store.saveCustomAction(this.actionDraft);
    }
  }

  public deleteAction(): void {
    if (this.actionDraft.id) {
      this.store.deleteCustomAction(this.actionDraft.id);
      this.store.closeCustomActionModal();
    }
  }
}
