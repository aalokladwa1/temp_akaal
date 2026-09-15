import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CreateConnectionDraft } from '../../create-connection.models';
import { CustomSelectComponent, CustomSelectOption } from '../../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-salesforce-extension',
  standalone: true,
  imports: [CommonModule, FormsModule, CustomSelectComponent],
  template: `
    <div class="space-y-4 select-none">
      
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        <!-- Salesforce Instance URL -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-semibold text-slate-700">
            Salesforce My Domain URL <span class="text-rose-500">*</span>
          </label>
          <input
            type="text"
            [(ngModel)]="draft.salesforceInstanceUrl"
            placeholder="https://company.my.salesforce.com or https://test.salesforce.com"
            class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          <span class="text-[11px] text-slate-400">
            Enterprise custom domain login URL for REST and Bulk v2 APIs.
          </span>
        </div>

        <!-- Auth Flow Mode Selector -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-semibold text-slate-700">
            Authentication Flow <span class="text-rose-500">*</span>
          </label>
          <app-custom-select
            [options]="authFlowOptions"
            [value]="draft.salesforceAuthFlow"
            (valueChange)="onAuthFlowChange($event)">
          </app-custom-select>
          <span class="text-[11px] text-slate-400">
            Connected App protocol (OAuth 2.0 Client Credentials, JWT, or Username/Password).
          </span>
        </div>

      </div>

      <!-- Flow 1: OAuth / JWT Connected App Client ID & Subject -->
      @if (draft.salesforceAuthFlow === 'OAUTH' || draft.salesforceAuthFlow === 'JWT_BEARER') {
        <div class="p-4 bg-slate-50/60 border border-slate-200 rounded-xl grid grid-cols-1 md:grid-cols-2 gap-3.5">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">
              Connected App Client ID (Consumer Key) <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="draft.salesforceClientId"
              placeholder="3MVG9...xxxx"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">
              Username / Subject <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="draft.salesforceSubject"
              placeholder="integration_user@company.com"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          </div>
        </div>
      }

      <!-- Common: API Version -->
      <div class="flex flex-col gap-1.5">
        <label class="text-xs font-semibold text-slate-700">
          Salesforce REST / Bulk API Version
        </label>
        <app-custom-select
          [options]="apiVersionOptions"
          [value]="draft.salesforceApiVersion"
          (valueChange)="onApiVersionChange($event)">
        </app-custom-select>
      </div>

    </div>
  `
})
export class SalesforceExtensionComponent {
  @Input() draft!: CreateConnectionDraft;

  public authFlowOptions: CustomSelectOption[] = [
    { label: 'OAuth 2.0 Client Credentials (Connected App)', value: 'OAUTH' },
    { label: 'JWT Bearer Token Flow (Server-to-Server)', value: 'JWT_BEARER' },
    { label: 'Username / Password + Security Token (Legacy)', value: 'USERNAME_PASSWORD' }
  ];

  public apiVersionOptions: CustomSelectOption[] = [
    { label: 'v59.0 (Winter 24 - Default)', value: 'v59.0' },
    { label: 'v58.0 (Summer 23)', value: 'v58.0' },
    { label: 'v57.0 (Spring 23)', value: 'v57.0' }
  ];

  public onAuthFlowChange(val: string): void {
    this.draft.salesforceAuthFlow = val as any;
  }

  public onApiVersionChange(val: string): void {
    this.draft.salesforceApiVersion = val;
  }
}
