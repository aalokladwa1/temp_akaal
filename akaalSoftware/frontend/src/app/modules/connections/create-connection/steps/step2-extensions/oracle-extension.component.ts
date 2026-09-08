import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CreateConnectionDraft } from '../../create-connection.models';
import { CustomSelectComponent, CustomSelectOption } from '../../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-oracle-extension',
  standalone: true,
  imports: [CommonModule, FormsModule, CustomSelectComponent],
  template: `
    <div class="space-y-4 select-none">
      
      <!-- Addressing Mode & Driver Configuration -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        <!-- Addressing Mode Selector -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-semibold text-slate-700">
            Addressing Method <span class="text-rose-500">*</span>
          </label>
          <app-custom-select
            [options]="addressingOptions"
            [value]="draft.oracleAddressingMode"
            (valueChange)="onAddressingChange($event)">
          </app-custom-select>
          <span class="text-[11px] text-slate-400">
            Choose how Oracle endpoints resolve (Service, SID, TNS, or Cloud Wallet).
          </span>
        </div>

        <!-- Driver Mode Selector -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-semibold text-slate-700">
            Driver Mode <span class="text-rose-500">*</span>
          </label>
          <app-custom-select
            [options]="driverOptions"
            [value]="draft.oracleDriverMode"
            (valueChange)="onDriverModeChange($event)">
          </app-custom-select>
          <span class="text-[11px] text-slate-400">
            Thin uses pure TCP protocol; Thick requires Oracle Instant Client libraries.
          </span>
        </div>

      </div>

      <!-- Mode 1: Host + Service Name -->
      @if (draft.oracleAddressingMode === 'HOST_SERVICE') {
        <div class="p-4 bg-slate-50/60 border border-slate-200 rounded-xl grid grid-cols-1 md:grid-cols-3 gap-3.5">
          <div class="flex flex-col gap-1.5 md:col-span-1">
            <label class="text-xs font-semibold text-slate-700">
              Host / SCAN Listener <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="draft.oracleHost"
              placeholder="oracle-scan.corp.internal"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">
              Port <span class="text-rose-500">*</span>
            </label>
            <input
              type="number"
              [(ngModel)]="draft.oraclePort"
              placeholder="1521"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">
              Service Name <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="draft.oracleServiceName"
              placeholder="PDB1.WORLD or ORCLPDB"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          </div>
        </div>
      }

      <!-- Mode 2: Host + SID -->
      @if (draft.oracleAddressingMode === 'HOST_SID') {
        <div class="p-4 bg-slate-50/60 border border-slate-200 rounded-xl grid grid-cols-1 md:grid-cols-3 gap-3.5">
          <div class="flex flex-col gap-1.5 md:col-span-1">
            <label class="text-xs font-semibold text-slate-700">
              Host <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="draft.oracleHost"
              placeholder="oracle-db.internal"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">
              Port <span class="text-rose-500">*</span>
            </label>
            <input
              type="number"
              [(ngModel)]="draft.oraclePort"
              placeholder="1521"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">
              System Identifier (SID) <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="draft.oracleSid"
              placeholder="ORCL"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          </div>
        </div>
      }

      <!-- Mode 3: TNS Entry -->
      @if (draft.oracleAddressingMode === 'TNS_ENTRY') {
        <div class="p-4 bg-slate-50/60 border border-slate-200 rounded-xl grid grid-cols-1 md:grid-cols-2 gap-3.5">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">
              TNS Entry Alias <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="draft.oracleTnsName"
              placeholder="FINPROD_HIGH"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">
              TNS_ADMIN / Config Directory
            </label>
            <input
              type="text"
              [(ngModel)]="draft.oracleTnsAdminPath"
              placeholder="/opt/oracle/network/admin or C:\oracle\tns"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          </div>
        </div>
      }

      <!-- Mode 4: Oracle Wallet -->
      @if (draft.oracleAddressingMode === 'ORACLE_WALLET') {
        <div class="p-4 bg-slate-50/60 border border-slate-200 rounded-xl flex flex-col gap-3.5">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">
              Oracle Cloud Wallet Path (cwallet.sso / tnsnames.ora) <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="draft.oracleWalletPath"
              placeholder="/etc/oracle/wallets/finance_db_wallet or C:\oracle\wallet"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          </div>
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">
              TNS Service Alias from Wallet <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="draft.oracleTnsName"
              placeholder="finance_high or db2026_low"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          </div>
        </div>
      }

      <!-- Conditional Thick Driver Client Path -->
      @if (draft.oracleDriverMode === 'THICK') {
        <div class="p-3.5 bg-amber-50/40 border border-amber-200 rounded-xl flex flex-col gap-1.5">
          <label class="text-xs font-semibold text-slate-800">
            Oracle Instant Client Library Path <span class="text-rose-500">*</span>
          </label>
          <input
            type="text"
            [(ngModel)]="draft.oracleClientLibPath"
            placeholder="/opt/oracle/instantclient_19_8 or C:\oracle\instantclient_19_8"
            class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
          <span class="text-[11px] text-amber-800">
            Required for Advanced Features (XA, OCI, and thick client connection pooling).
          </span>
        </div>
      }

      <!-- Privilege Mode Selector -->
      <div class="flex flex-col gap-1.5">
        <label class="text-xs font-semibold text-slate-700">
          Privilege Connection Mode
        </label>
        <app-custom-select
          [options]="privilegeOptions"
          [value]="draft.oraclePrivilegeMode"
          (valueChange)="onPrivilegeChange($event)">
        </app-custom-select>
        <span class="text-[11px] text-slate-400">
          SYSDBA / SYSOPER privileges should only be requested when CDC LogMiner setup or dictionary views mandate DBA role.
        </span>
      </div>

    </div>
  `
})
export class OracleExtensionComponent {
  @Input() draft!: CreateConnectionDraft;

  public addressingOptions: CustomSelectOption[] = [
    { label: 'Host + Service Name (Recommended)', value: 'HOST_SERVICE' },
    { label: 'Host + SID (Legacy)', value: 'HOST_SID' },
    { label: 'TNS Entry Name', value: 'TNS_ENTRY' },
    { label: 'Oracle Cloud Wallet / Mutual TLS', value: 'ORACLE_WALLET' }
  ];

  public driverOptions: CustomSelectOption[] = [
    { label: 'Thin Driver (Pure Python/Socket)', value: 'THIN' },
    { label: 'Thick Driver (Oracle Client / OCI)', value: 'THICK' }
  ];

  public privilegeOptions: CustomSelectOption[] = [
    { label: 'Normal (Standard Application Role)', value: 'NORMAL' },
    { label: 'SYSDBA (Database Administrator)', value: 'SYSDBA' },
    { label: 'SYSOPER (Operator)', value: 'SYSOPER' }
  ];

  public onAddressingChange(val: string): void {
    this.draft.oracleAddressingMode = val as any;
  }

  public onDriverModeChange(val: string): void {
    this.draft.oracleDriverMode = val as any;
  }

  public onPrivilegeChange(val: string): void {
    this.draft.oraclePrivilegeMode = val as any;
  }
}
