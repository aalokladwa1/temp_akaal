import { Component, inject, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SettingsService } from '../services/settings.service';
import { ContextService } from '../../../core/services/context.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../shared/components/custom-select.component';
import {
  LandingSurfaceOption,
  TimezoneOption,
  DateFormatOption,
  TimeFormatOption,
  DataUnitStandard,
  NumberGroupingSeparator
} from '../models/settings.models';

@Component({
  selector: 'app-settings-general',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-6 animate-in fade-in duration-150 max-w-4xl pb-12">
      
      <!-- Section Top Header & Actions -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div class="flex items-center gap-2">
            <span class="text-[11px] font-bold text-blue-600 tracking-wider uppercase font-mono">
              WORKSTATION PREFERENCES
            </span>
          </div>
          <h2 class="text-xl font-bold text-slate-900 tracking-tight">
            General Settings
          </h2>
          <p class="text-xs text-slate-500 max-w-2xl mt-0.5">
            Configure default startup navigation, temporal formats, data units, and destructive action safety gates.
          </p>
        </div>

        <div class="flex items-center gap-2.5 shrink-0">
          <button
            type="button"
            (click)="resetDefaults()"
            class="h-9 px-3.5 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-semibold flex items-center gap-2 transition-colors cursor-pointer shadow-2xs">
            <app-lucide-icon name="rotate-ccw" [size]="14" class="text-slate-500"></app-lucide-icon>
            <span>Reset Defaults</span>
          </button>
        </div>
      </div>

      <!-- Notification / Save Status Banner -->
      @if (saveMessage()) {
        <div class="p-3 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-between animate-in fade-in duration-150">
          <div class="flex items-center gap-2 text-xs font-medium text-blue-800">
            <app-lucide-icon name="check" [size]="14" class="text-blue-600"></app-lucide-icon>
            <span>{{ saveMessage() }}</span>
          </div>
          <button type="button" (click)="saveMessage.set(null)" class="text-blue-500 hover:text-blue-700 cursor-pointer">
            <app-lucide-icon name="x" [size]="14"></app-lucide-icon>
          </button>
        </div>
      }

      <!-- =============================================================== -->
      <!-- 1. DEFAULT LANDING SURFACE                                      -->
      <!-- =============================================================== -->
      <section aria-labelledby="landing-heading" class="p-5 rounded-xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-start gap-3">
          <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 shrink-0 mt-0.5">
            <app-lucide-icon name="layout-dashboard" [size]="16"></app-lucide-icon>
          </div>
          <div class="flex flex-col">
            <h3 id="landing-heading" class="text-sm font-bold text-slate-900">Default Landing Surface</h3>
            <p class="text-xs text-slate-500 leading-relaxed">
              Select the initial operational viewport rendered immediately when opening DevKros or clicking the brand logo.
            </p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">Initial Viewport</label>
            <app-custom-select
              [options]="landingSurfaceOptions"
              [ngModel]="settings.generalSettings().defaultLandingSurface"
              (ngModelChange)="onLandingSurfaceChange($event)"
              placeholder="Select landing surface">
            </app-custom-select>
          </div>

          <div class="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center gap-3">
            <app-lucide-icon name="info" [size]="16" class="text-blue-600 shrink-0"></app-lucide-icon>
            <div class="flex flex-col">
              <span class="text-xs font-semibold text-slate-800">Current Target Route</span>
              <span class="text-[11px] font-mono text-slate-600">/{{ settings.generalSettings().defaultLandingSurface }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- =============================================================== -->
      <!-- 2. TIMEZONE & DATE PRESENTATION                                 -->
      <!-- =============================================================== -->
      <section aria-labelledby="time-heading" class="p-5 rounded-xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-5">
        <div class="flex items-start gap-3">
          <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 shrink-0 mt-0.5">
            <app-lucide-icon name="clock" [size]="16"></app-lucide-icon>
          </div>
          <div class="flex flex-col">
            <h3 id="time-heading" class="text-sm font-bold text-slate-900">Timezone &amp; Date Presentation</h3>
            <p class="text-xs text-slate-500 leading-relaxed">
              Specify how timestamps, audit logs, barrier records, and event chronologies are rendered throughout the workstation.
            </p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          
          <!-- Timezone Preference -->
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">Timezone Reference</label>
            <app-custom-select
              [options]="timezoneOptions"
              [ngModel]="settings.generalSettings().timezonePreference"
              (ngModelChange)="onTimezoneChange($event)"
              placeholder="Select timezone">
            </app-custom-select>
          </div>

          <!-- Date Format Preference -->
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">Date Display Format</label>
            <app-custom-select
              [options]="dateFormatOptions"
              [ngModel]="settings.generalSettings().dateFormat"
              (ngModelChange)="onDateFormatChange($event)"
              placeholder="Select date format">
            </app-custom-select>
          </div>

          <!-- Time Format Preference -->
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">Time Display Format</label>
            <app-custom-select
              [options]="timeFormatOptions"
              [ngModel]="settings.generalSettings().timeFormat"
              (ngModelChange)="onTimeFormatChange($event)"
              placeholder="Select time format">
            </app-custom-select>
          </div>

        </div>

        <!-- Live Clock Preview -->
        <div class="p-3.5 rounded-lg bg-slate-50 border border-slate-200/80 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <span class="text-xs font-semibold text-slate-700">Active Timestamp Format Preview:</span>
          </div>
          <div class="px-3 py-1 rounded bg-white border border-slate-200 font-mono text-xs font-bold text-blue-700">
            {{ settings.formatDatePreview() }}
          </div>
        </div>
      </section>

      <!-- =============================================================== -->
      <!-- 3. NUMBER & DATA-UNIT FORMATTING                                -->
      <!-- =============================================================== -->
      <section aria-labelledby="units-heading" class="p-5 rounded-xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-5">
        <div class="flex items-start gap-3">
          <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 shrink-0 mt-0.5">
            <app-lucide-icon name="hard-drive" [size]="16"></app-lucide-icon>
          </div>
          <div class="flex flex-col">
            <h3 id="units-heading" class="text-sm font-bold text-slate-900">Number &amp; Data-Unit Formatting</h3>
            <p class="text-xs text-slate-500 leading-relaxed">
              Standardize binary vs decimal unit exponents for byte counters and choose integer grouping separators.
            </p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          
          <!-- Data Unit Standard -->
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">Data Unit Metric Base</label>
            <app-custom-select
              [options]="dataUnitOptions"
              [ngModel]="settings.generalSettings().dataUnitStandard"
              (ngModelChange)="onDataUnitChange($event)"
              placeholder="Select data unit">
            </app-custom-select>
          </div>

          <!-- Number Grouping Separator -->
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">Number Grouping Separator</label>
            <app-custom-select
              [options]="numberSeparatorOptions"
              [ngModel]="settings.generalSettings().numberGroupingSeparator"
              (ngModelChange)="onNumberSeparatorChange($event)"
              placeholder="Select separator">
            </app-custom-select>
          </div>

        </div>

        <!-- Live Data & Number Previews -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div class="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
            <span class="text-xs font-medium text-slate-600">Sample Est. Database Size:</span>
            <span class="font-mono text-xs font-bold text-slate-900">
              {{ sampleBytePreview() }}
            </span>
          </div>
          <div class="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
            <span class="text-xs font-medium text-slate-600">Sample Row Count:</span>
            <span class="font-mono text-xs font-bold text-slate-900">
              {{ sampleNumberPreview() }} records
            </span>
          </div>
        </div>
      </section>

      <!-- =============================================================== -->
      <!-- 4. DEFAULT WORKSPACE & PROJECT CONTEXT                          -->
      <!-- =============================================================== -->
      <section aria-labelledby="context-heading" class="p-5 rounded-xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-5">
        <div class="flex items-start gap-3">
          <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 shrink-0 mt-0.5">
            <app-lucide-icon name="building-2" [size]="16"></app-lucide-icon>
          </div>
          <div class="flex flex-col">
            <h3 id="context-heading" class="text-sm font-bold text-slate-900">Default Operational Context</h3>
            <p class="text-xs text-slate-500 leading-relaxed">
              Default operational boundary pre-selected when launching a new terminal or session. Synchronized with available context bounds.
            </p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          
          <!-- Default Org -->
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">Preferred Organization</label>
            <app-custom-select
              [options]="orgOptions()"
              [ngModel]="settings.generalSettings().defaultOrgId"
              (ngModelChange)="onOrgChange($event)"
              placeholder="Select organization">
            </app-custom-select>
          </div>

          <!-- Default Workspace -->
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">Preferred Workspace</label>
            <app-custom-select
              [options]="workspaceOptions()"
              [ngModel]="settings.generalSettings().defaultWorkspaceId"
              (ngModelChange)="onWorkspaceChange($event)"
              placeholder="Select workspace">
            </app-custom-select>
          </div>

          <!-- Default Environment -->
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">Preferred Environment</label>
            <app-custom-select
              [options]="environmentOptions()"
              [ngModel]="settings.generalSettings().defaultEnvironmentId"
              (ngModelChange)="onEnvironmentChange($event)"
              placeholder="Select environment">
            </app-custom-select>
          </div>

        </div>

        <div class="p-3 rounded-lg bg-slate-50 border border-slate-200/80 flex items-center gap-2.5">
          <app-lucide-icon name="shield-check" [size]="16" class="text-emerald-600 shrink-0"></app-lucide-icon>
          <span class="text-xs text-slate-600">
            Current active session: <strong class="text-slate-900">{{ cs.effectiveContextLabel() }}</strong>
          </span>
        </div>
      </section>

      <!-- =============================================================== -->
      <!-- 5. CONFIRMATION & SAFETY PREFERENCES                            -->
      <!-- =============================================================== -->
      <section aria-labelledby="safety-heading" class="p-5 rounded-xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4">
        <div class="flex items-start gap-3">
          <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 shrink-0 mt-0.5">
            <app-lucide-icon name="shield" [size]="16"></app-lucide-icon>
          </div>
          <div class="flex flex-col">
            <h3 id="safety-heading" class="text-sm font-bold text-slate-900">Confirmation &amp; Safety Verification</h3>
            <p class="text-xs text-slate-500 leading-relaxed">
              Enforce interactive guards, safety gates, and local telemetry generation for high-impact operations.
            </p>
          </div>
        </div>

        <div class="flex flex-col divide-y divide-slate-100 pt-1">
          
          <!-- Destructive Action Guard (Locked) -->
          <div class="py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div class="flex flex-col gap-0.5 pr-4">
              <div class="flex items-center gap-2">
                <span class="text-xs font-bold text-slate-900">Destructive Action Phrase Barrier</span>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
                  Enforced by Enterprise Policy
                </span>
              </div>
              <p class="text-[11px] text-slate-500">
                Always require double-key phrase confirmation before irreversible actions (schema drops, cutover execution, node decommission).
              </p>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <span class="text-xs font-semibold text-slate-500">Locked Active</span>
              <input
                type="checkbox"
                [checked]="true"
                disabled
                class="w-4 h-4 rounded border-slate-300 text-blue-600 opacity-80 cursor-not-allowed">
            </div>
          </div>

          <!-- Unsaved Changes Guard -->
          <div class="py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div class="flex flex-col gap-0.5 pr-4">
              <span class="text-xs font-bold text-slate-900">Unsaved Changes Navigation Guard</span>
              <p class="text-[11px] text-slate-500">
                Prompt for explicit confirmation before navigating away from wizards or forms with pending uncommitted changes.
              </p>
            </div>
            <label class="flex items-center gap-2 cursor-pointer shrink-0">
              <input
                type="checkbox"
                [checked]="settings.generalSettings().warnUnsavedChanges"
                (change)="toggleUnsavedChanges($event)"
                class="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500">
              <span class="text-xs font-semibold text-slate-700">
                {{ settings.generalSettings().warnUnsavedChanges ? 'Enabled' : 'Disabled' }}
              </span>
            </label>
          </div>

          <!-- Local Crash & Diagnostics Telemetry -->
          <div class="py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div class="flex flex-col gap-0.5 pr-4">
              <span class="text-xs font-bold text-slate-900">Local Diagnostics &amp; Crash Report Generation</span>
              <p class="text-[11px] text-slate-500">
                Generate local encrypted crash diagnostics on disk to assist support personnel during incident investigation.
              </p>
            </div>
            <label class="flex items-center gap-2 cursor-pointer shrink-0">
              <input
                type="checkbox"
                [checked]="settings.generalSettings().enableLocalCrashTelemetry"
                (change)="toggleCrashTelemetry($event)"
                class="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500">
              <span class="text-xs font-semibold text-slate-700">
                {{ settings.generalSettings().enableLocalCrashTelemetry ? 'Enabled' : 'Disabled' }}
              </span>
            </label>
          </div>

        </div>
      </section>

    </div>
  `
})
export class SettingsGeneralComponent {
  public settings = inject(SettingsService);
  public cs = inject(ContextService);

  public saveMessage = signal<string | null>(null);

  // Dropdown Options
  public landingSurfaceOptions: CustomSelectOption[] = [
    { label: 'Dashboard (/dashboard)', value: 'dashboard', desc: 'Executive system health, active migrations & KPIs' },
    { label: 'Migration Operations (/migration)', value: 'migration', desc: 'Active execution pipelines and cutover controls' },
    { label: 'Observability & Monitoring (/monitoring)', value: 'monitoring', desc: 'Real-time telemetry, stream metrics & alerts' },
    { label: 'Compliance & Reports (/reports)', value: 'reports', desc: 'Regulatory evidence dossiers and audit ledgers' },
    { label: 'Administration (/administration)', value: 'administration', desc: 'Multi-tenant identity, cloud connectors & governance' }
  ];

  public timezoneOptions: CustomSelectOption[] = [
    { label: `Local System (${this.settings.getDetectedLocalTimezone()})`, value: 'LOCAL' },
    { label: 'UTC (Coordinated Universal Time)', value: 'UTC' },
    { label: 'America / New York (UTC-05:00 / -04:00)', value: 'America/New_York' },
    { label: 'Europe / London (UTC+00:00 / +01:00)', value: 'Europe/London' },
    { label: 'Asia / Kolkata (UTC+05:30)', value: 'Asia/Kolkata' },
    { label: 'Asia / Singapore (UTC+08:00)', value: 'Asia/Singapore' },
    { label: 'Asia / Tokyo (UTC+09:00)', value: 'Asia/Tokyo' }
  ];

  public dateFormatOptions: CustomSelectOption[] = [
    { label: 'YYYY-MM-DD (ISO 8601 Standard)', value: 'YYYY-MM-DD', desc: 'Recommended for enterprise audit logs' },
    { label: 'MM/DD/YYYY (US Standard)', value: 'MM/DD/YYYY', desc: 'Traditional United States format' },
    { label: 'DD/MM/YYYY (International Standard)', value: 'DD/MM/YYYY', desc: 'Commonwealth & European standard' }
  ];

  public timeFormatOptions: CustomSelectOption[] = [
    { label: '24-Hour Military Standard (14:30:00)', value: '24h', desc: 'Standard for mission-control telemetry' },
    { label: '12-Hour AM/PM Standard (02:30:00 PM)', value: '12h', desc: 'Standard commercial clock' }
  ];

  public dataUnitOptions: CustomSelectOption[] = [
    { label: 'Binary IEC (1024 Base: KiB, MiB, GiB, TiB)', value: 'BINARY_IEC', desc: 'Recommended for memory & storage capacity' },
    { label: 'Decimal SI (1000 Base: KB, MB, GB, TB)', value: 'DECIMAL_SI', desc: 'Standard for network transmission metrics' }
  ];

  public numberSeparatorOptions: CustomSelectOption[] = [
    { label: 'Comma Separator (1,234,567.89)', value: 'COMMA', desc: 'Standard English comma notation' },
    { label: 'Period Separator (1.234.567,89)', value: 'PERIOD', desc: 'European decimal comma notation' },
    { label: 'Space Separator (1 234 567.89)', value: 'SPACE', desc: 'International SI space notation' }
  ];

  // Dynamic Context Options
  public orgOptions = computed<CustomSelectOption[]>(() => {
    const orgs = this.cs.organizations();
    if (orgs.length === 0) {
      return [
        { label: 'Default Enterprise Org (org-enterprise)', value: 'org-enterprise' },
        { label: 'Global Migration Services (org-global)', value: 'org-global' }
      ];
    }
    return orgs.map(o => ({ label: o.name, value: o.id, desc: o.description }));
  });

  public workspaceOptions = computed<CustomSelectOption[]>(() => {
    const wss = this.cs.workspaces();
    if (wss.length === 0) {
      return [
        { label: 'Production Migration Workspace (ws-prod-migration)', value: 'ws-prod-migration' },
        { label: 'Staging Validation Workspace (ws-staging)', value: 'ws-staging' }
      ];
    }
    return wss.map(w => ({ label: w.name, value: w.id, desc: w.description }));
  });

  public environmentOptions = computed<CustomSelectOption[]>(() => {
    const envs = this.cs.environments();
    if (envs.length === 0) {
      return [
        { label: 'Production Tier 1 (env-prod-01)', value: 'env-prod-01', badge: 'PROD' },
        { label: 'Pre-Production Staging (env-stage-01)', value: 'env-stage-01' }
      ];
    }
    return envs.map(e => ({ label: e.name, value: e.id, badge: e.isProduction ? 'PROD' : undefined }));
  });

  // Previews
  public sampleBytePreview = computed(() => {
    return this.settings.formatBytes(1572864000); // ~1.46 GiB or 1.57 GB
  });

  public sampleNumberPreview = computed(() => {
    return this.settings.formatNumber(12849204);
  });

  // Change handlers
  public onLandingSurfaceChange(val: any): void {
    if (!val) return;
    this.settings.updateGeneral({ defaultLandingSurface: val as LandingSurfaceOption });
    this.flashSaved('Default landing surface updated');
  }

  public onTimezoneChange(val: any): void {
    if (!val) return;
    this.settings.updateGeneral({ timezonePreference: val as TimezoneOption });
    this.flashSaved('Timezone reference updated');
  }

  public onDateFormatChange(val: any): void {
    if (!val) return;
    this.settings.updateGeneral({ dateFormat: val as DateFormatOption });
    this.flashSaved('Date display format updated');
  }

  public onTimeFormatChange(val: any): void {
    if (!val) return;
    this.settings.updateGeneral({ timeFormat: val as TimeFormatOption });
    this.flashSaved('Time display format updated');
  }

  public onDataUnitChange(val: any): void {
    if (!val) return;
    this.settings.updateGeneral({ dataUnitStandard: val as DataUnitStandard });
    this.flashSaved('Data unit metric standard updated');
  }

  public onNumberSeparatorChange(val: any): void {
    if (!val) return;
    this.settings.updateGeneral({ numberGroupingSeparator: val as NumberGroupingSeparator });
    this.flashSaved('Number grouping separator updated');
  }

  public onOrgChange(val: any): void {
    if (!val) return;
    this.settings.updateGeneral({ defaultOrgId: String(val) });
    this.flashSaved('Preferred organization context updated');
  }

  public onWorkspaceChange(val: any): void {
    if (!val) return;
    this.settings.updateGeneral({ defaultWorkspaceId: String(val) });
    this.flashSaved('Preferred workspace context updated');
  }

  public onEnvironmentChange(val: any): void {
    if (!val) return;
    this.settings.updateGeneral({ defaultEnvironmentId: String(val) });
    this.flashSaved('Preferred environment context updated');
  }

  public toggleUnsavedChanges(event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    this.settings.updateGeneral({ warnUnsavedChanges: checked });
    this.flashSaved('Unsaved changes guard preference updated');
  }

  public toggleCrashTelemetry(event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    this.settings.updateGeneral({ enableLocalCrashTelemetry: checked });
    this.flashSaved('Local crash diagnostic telemetry updated');
  }

  public resetDefaults(): void {
    this.settings.resetGeneral();
    this.flashSaved('General settings restored to enterprise defaults');
  }

  private flashSaved(msg: string): void {
    this.saveMessage.set(msg);
  }
}
