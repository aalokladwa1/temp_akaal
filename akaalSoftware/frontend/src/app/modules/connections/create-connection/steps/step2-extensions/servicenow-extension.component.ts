import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CreateConnectionDraft } from '../../create-connection.models';
import { CustomSelectComponent, CustomSelectOption } from '../../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-servicenow-extension',
  standalone: true,
  imports: [CommonModule, FormsModule, CustomSelectComponent],
  template: `
    <div class="space-y-4 select-none">
      
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        <!-- ServiceNow Instance URL / Name -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-semibold text-slate-700">
            ServiceNow Instance URL / Name <span class="text-rose-500">*</span>
          </label>
          <input
            type="text"
            [(ngModel)]="draft.servicenowInstanceUrl"
            placeholder="https://company.service-now.com or dev12345"
            class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          <span class="text-[11px] text-slate-400">
            Fully-qualified ServiceNow instance domain or instance ID.
          </span>
        </div>

        <!-- Auth Mode Selector -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-semibold text-slate-700">
            Authentication Protocol <span class="text-rose-500">*</span>
          </label>
          <app-custom-select
            [options]="authModeOptions"
            [value]="draft.servicenowAuthMode"
            (valueChange)="onAuthModeChange($event)">
          </app-custom-select>
        </div>

      </div>

      <!-- Page Size & Limit Configuration -->
      <div class="flex flex-col gap-1.5">
        <label class="text-xs font-semibold text-slate-700">
          sysparm_limit (Default Page Batch Size)
        </label>
        <input
          type="number"
          [(ngModel)]="draft.servicenowPageSize"
          placeholder="1000"
          class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
        <span class="text-[11px] text-slate-400">
          Number of Table API records fetched per batch iteration (default 1000).
        </span>
      </div>

    </div>
  `
})
export class ServiceNowExtensionComponent {
  @Input() draft!: CreateConnectionDraft;

  public authModeOptions: CustomSelectOption[] = [
    { label: 'Basic Authentication (Username / Password)', value: 'BASIC' },
    { label: 'OAuth 2.0 (Client Credentials / Refresh Token)', value: 'OAUTH' }
  ];

  public onAuthModeChange(val: string): void {
    this.draft.servicenowAuthMode = val as any;
  }
}
