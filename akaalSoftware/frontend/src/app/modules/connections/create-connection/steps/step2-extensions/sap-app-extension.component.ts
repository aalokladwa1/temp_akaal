import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CreateConnectionDraft } from '../../create-connection.models';
import { CustomSelectComponent, CustomSelectOption } from '../../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-sap-app-extension',
  standalone: true,
  imports: [CommonModule, FormsModule, CustomSelectComponent],
  template: `
    <div class="space-y-4 select-none">
      
      <!-- Protocol & Server Mode -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        <!-- SAP Protocol Mode -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-semibold text-slate-700">
            Connection Protocol <span class="text-rose-500">*</span>
          </label>
          <app-custom-select
            [options]="protocolOptions"
            [value]="draft.sapConnectionMode"
            (valueChange)="onProtocolChange($event)">
          </app-custom-select>
        </div>

        <!-- RFC Server Mode (Conditional) -->
        @if (draft.sapConnectionMode === 'RFC_BAPI') {
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">
              SAP Topology Server Mode <span class="text-rose-500">*</span>
            </label>
            <app-custom-select
              [options]="serverModeOptions"
              [value]="draft.sapServerMode"
              (valueChange)="onServerModeChange($event)">
            </app-custom-select>
          </div>
        }

      </div>

      <!-- Mode 1: RFC -> Application Server -->
      @if (draft.sapConnectionMode === 'RFC_BAPI' && draft.sapServerMode === 'APPLICATION_SERVER') {
        <div class="p-4 bg-slate-50/60 border border-slate-200 rounded-xl grid grid-cols-1 md:grid-cols-3 gap-3.5">
          <div class="flex flex-col gap-1.5 md:col-span-1">
            <label class="text-xs font-semibold text-slate-700">
              Application Server Host (ashost) <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="draft.sapAppServerHost"
              placeholder="sapapp01.corp.internal"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">
              System Number (sysnr) <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="draft.sapSystemNumber"
              placeholder="00"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">
              Client Number (client) <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="draft.sapClient"
              placeholder="100"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          </div>
        </div>
      }

      <!-- Mode 2: RFC -> Message Server / Group Load Balancing -->
      @if (draft.sapConnectionMode === 'RFC_BAPI' && draft.sapServerMode === 'MESSAGE_SERVER') {
        <div class="p-4 bg-slate-50/60 border border-slate-200 rounded-xl grid grid-cols-1 md:grid-cols-3 gap-3.5">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">
              Message Server Host (mshost) <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="draft.sapMessageServerHost"
              placeholder="sapmsg.corp.internal"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">
              Server Group (group) <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="draft.sapGroup"
              placeholder="PUBLIC or BATCH"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">
              System ID (r3name / SID) <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="draft.sapSystemId"
              placeholder="PRD"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          </div>
        </div>
      }

      <!-- Mode 3: OData REST Service -->
      @if (draft.sapConnectionMode === 'ODATA') {
        <div class="p-4 bg-slate-50/60 border border-slate-200 rounded-xl grid grid-cols-1 md:grid-cols-2 gap-3.5">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">
              OData Gateway Base URL <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="draft.sapOdataServiceUrl"
              placeholder="https://sap-gw.corp.internal:44300/sap/opu/odata/sap/"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">
              SAP Client Number <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="draft.sapClient"
              placeholder="100"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          </div>
        </div>
      }

      <!-- Common SAP Language & SNC (Secure Network Communications) -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        <!-- Language -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-semibold text-slate-700">
            SAP Logon Language
          </label>
          <input
            type="text"
            [(ngModel)]="draft.sapLanguage"
            placeholder="EN"
            class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
        </div>

        <!-- SNC (Secure Network Communications) -->
        <div class="flex flex-col justify-center gap-1.5">
          <label class="flex items-center gap-2 cursor-pointer select-none pt-1">
            <input
              type="checkbox"
              [(ngModel)]="draft.sapSncEnabled"
              class="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer" />
            <span class="text-xs font-semibold text-slate-800">
              Enable SNC (Secure Network Communications / Kerberos)
            </span>
          </label>
        </div>

      </div>

      <!-- SNC Partner Name Input (Conditional) -->
      @if (draft.sapSncEnabled) {
        <div class="p-3.5 bg-blue-50/40 border border-blue-200 rounded-xl flex flex-col gap-1.5">
          <label class="text-xs font-semibold text-slate-800">
            SNC Partner Name (p:CN=SAP/...) <span class="text-rose-500">*</span>
          </label>
          <input
            type="text"
            [(ngModel)]="draft.sapSncPartnerName"
            placeholder="p:CN=SAP/PRD@CORP.INTERNAL"
            class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
        </div>
      }

    </div>
  `
})
export class SapAppExtensionComponent {
  @Input() draft!: CreateConnectionDraft;

  public protocolOptions: CustomSelectOption[] = [
    { label: 'RFC / BAPI (SAP NetWeaver RFC Protocol)', value: 'RFC_BAPI' },
    { label: 'OData REST Gateway Service', value: 'ODATA' }
  ];

  public serverModeOptions: CustomSelectOption[] = [
    { label: 'Application Server (Direct Host & System Number)', value: 'APPLICATION_SERVER' },
    { label: 'Message Server (Group Load Balancing & SID)', value: 'MESSAGE_SERVER' }
  ];

  public onProtocolChange(val: string): void {
    this.draft.sapConnectionMode = val as any;
  }

  public onServerModeChange(val: string): void {
    this.draft.sapServerMode = val as any;
  }
}
