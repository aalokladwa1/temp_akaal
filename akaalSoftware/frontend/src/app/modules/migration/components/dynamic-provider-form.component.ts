import {
  Component,
  Input,
  Output,
  EventEmitter,
  signal,
  computed
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { PhysicalProviderId, NetworkRouteType } from '../../../core/models/migration-view.models';
import { ALL_28_PROVIDER_SCHEMAS, ProviderFormField, ProviderFormSchema } from '../../../core/models/provider-form-schemas';

@Component({
  selector: 'app-dynamic-provider-form',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-5 text-xs select-none">
      
      <!-- Provider Header & Info Badge -->
      <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between gap-4">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 flex items-center justify-center font-bold text-sm">
            <app-lucide-icon [name]="schema()?.icon || 'database'" [size]="18"></app-lucide-icon>
          </div>
          <div class="flex flex-col">
            <span class="font-bold text-slate-900 text-sm">{{ schema()?.name || currentProviderId() }}</span>
            <span class="text-slate-600 text-xs">Configure connection endpoint parameters, authentication credentials, and network routing.</span>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <span class="px-2 py-0.5 rounded bg-white border border-slate-200 text-[11px] font-bold text-slate-700 uppercase">
            {{ schema()?.category }}
          </span>
          @if (schema()?.defaultPort) {
            <span class="px-2 py-0.5 rounded bg-blue-50 border border-blue-200 text-[11px] font-bold text-blue-700">
              Port {{ schema()?.defaultPort }}
            </span>
          }
        </div>
      </div>

      <!-- SECTION 1: Identity & Endpoint Parameters -->
      @if (getVisibleFieldsByGroup('ENDPOINT').length > 0) {
        <div class="flex flex-col gap-3 p-5 rounded-xl bg-white border border-slate-200 shadow-2xs">
          <div class="flex items-center gap-2 pb-2.5 border-b border-slate-100">
            <app-lucide-icon name="server" [size]="15" class="text-blue-600"></app-lucide-icon>
            <h4 class="font-bold text-slate-900 uppercase tracking-wider text-[11px]">1. IDENTITY &amp; ENDPOINT PARAMETERS</h4>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
            @for (field of getVisibleFieldsByGroup('ENDPOINT'); track field.id) {
              <div class="flex flex-col gap-1.5" [class.md:col-span-2]="field.type === 'textarea' || field.id === 'database_path' || field.id === 'replica_endpoints' || field.id === 'bootstrap_brokers' || field.id === 'node_urls'">
                <div class="flex items-center justify-between">
                  <label class="font-bold text-slate-800">{{ field.label }}</label>
                  @if (field.helpText) {
                    <span class="text-[11px] text-slate-500 font-normal">{{ field.helpText }}</span>
                  }
                </div>

                <!-- Input Types -->
                @switch (field.type) {
                  @case ('text') {
                    <input
                      type="text"
                      [ngModel]="getFieldValue(field.id)"
                      (ngModelChange)="setFieldValue(field.id, $event)"
                      [placeholder]="field.placeholder || ''"
                      class="h-9 px-3 rounded-lg bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all" />
                  }
                  @case ('number') {
                    <input
                      type="number"
                      [ngModel]="getFieldValue(field.id)"
                      (ngModelChange)="setFieldValue(field.id, $event)"
                      [placeholder]="field.placeholder || ''"
                      class="h-9 px-3 rounded-lg bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all" />
                  }
                  @case ('select') {
                    <select
                      [ngModel]="getFieldValue(field.id)"
                      (ngModelChange)="setFieldValue(field.id, $event)"
                      class="h-9 px-3 rounded-lg bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer">
                      @for (opt of field.options; track opt.value) {
                        <option [value]="opt.value">{{ opt.label }}</option>
                      }
                    </select>
                  }
                  @case ('file_path') {
                    <div class="relative flex items-center">
                      <input
                        type="text"
                        [ngModel]="getFieldValue(field.id)"
                        (ngModelChange)="setFieldValue(field.id, $event)"
                        [placeholder]="field.placeholder || ''"
                        class="w-full h-9 pl-3 pr-8 rounded-lg bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all" />
                      <div class="absolute right-2.5 pointer-events-none text-slate-400">
                        <app-lucide-icon name="folder" [size]="14"></app-lucide-icon>
                      </div>
                    </div>
                  }
                  @case ('textarea') {
                    <textarea
                      rows="2"
                      [ngModel]="getFieldValue(field.id)"
                      (ngModelChange)="setFieldValue(field.id, $event)"
                      [placeholder]="field.placeholder || ''"
                      class="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all resize-none"></textarea>
                  }
                }
              </div>
            }
          </div>
        </div>
      }

      <!-- SECTION 2: Authentication & Credentials -->
      @if (getVisibleFieldsByGroup('AUTH').length > 0) {
        <div class="flex flex-col gap-3 p-5 rounded-xl bg-white border border-slate-200 shadow-2xs">
          <div class="flex items-center justify-between pb-2.5 border-b border-slate-100">
            <div class="flex items-center gap-2">
              <app-lucide-icon name="shield-check" [size]="15" class="text-emerald-600"></app-lucide-icon>
              <h4 class="font-bold text-slate-900 uppercase tracking-wider text-[11px]">2. AUTHENTICATION &amp; VAULT SECRET REFERENCES</h4>
            </div>
            <span class="text-[11px] text-slate-500 font-medium">Zero plaintext secret storage</span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
            @for (field of getVisibleFieldsByGroup('AUTH'); track field.id) {
              <div class="flex flex-col gap-1.5" [class.md:col-span-2]="field.type === 'textarea' || field.id === 'service_account_json' || field.id === 'connection_string'">
                <div class="flex items-center justify-between">
                  <label class="font-bold text-slate-800">{{ field.label }}</label>
                  @if (field.helpText) {
                    <span class="text-[11px] text-slate-500 font-normal">{{ field.helpText }}</span>
                  }
                </div>

                @switch (field.type) {
                  @case ('text') {
                    <input
                      type="text"
                      [ngModel]="getFieldValue(field.id)"
                      (ngModelChange)="setFieldValue(field.id, $event)"
                      [placeholder]="field.placeholder || ''"
                      class="h-9 px-3 rounded-lg bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all" />
                  }
                  @case ('password') {
                    <input
                      type="password"
                      [ngModel]="getFieldValue(field.id)"
                      (ngModelChange)="setFieldValue(field.id, $event)"
                      [placeholder]="field.placeholder || '••••••••••••'"
                      class="h-9 px-3 rounded-lg bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all" />
                  }
                  @case ('secret_ref') {
                    <div class="relative flex items-center">
                      <div class="absolute left-3 pointer-events-none text-emerald-600">
                        <app-lucide-icon name="lock" [size]="13"></app-lucide-icon>
                      </div>
                      <input
                        type="text"
                        [ngModel]="getFieldValue(field.id)"
                        (ngModelChange)="setFieldValue(field.id, $event)"
                        [placeholder]="field.placeholder || 'vault://secret/prod/database_pass'"
                        class="w-full h-9 pl-8 pr-3.5 rounded-lg bg-emerald-50/40 border border-emerald-200/80 text-xs font-semibold text-emerald-950 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all shadow-2xs" />
                    </div>
                  }
                  @case ('select') {
                    <select
                      [ngModel]="getFieldValue(field.id)"
                      (ngModelChange)="setFieldValue(field.id, $event)"
                      class="h-9 px-3 rounded-lg bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer">
                      @for (opt of field.options; track opt.value) {
                        <option [value]="opt.value">{{ opt.label }}</option>
                      }
                    </select>
                  }
                  @case ('textarea') {
                    <textarea
                      rows="3"
                      [ngModel]="getFieldValue(field.id)"
                      (ngModelChange)="setFieldValue(field.id, $event)"
                      [placeholder]="field.placeholder || ''"
                      class="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all resize-none"></textarea>
                  }
                }
              </div>
            }
          </div>
        </div>
      }

      <!-- SECTION 3: Security & Network Route Topology -->
      <div class="flex flex-col gap-3 p-5 rounded-xl bg-white border border-slate-200 shadow-2xs">
        <div class="flex items-center gap-2 pb-2.5 border-b border-slate-100">
          <app-lucide-icon name="network" [size]="15" class="text-blue-600"></app-lucide-icon>
          <h4 class="font-bold text-slate-900 uppercase tracking-wider text-[11px]">3. SECURITY &amp; NETWORK ROUTE TOPOLOGY</h4>
        </div>

        <div class="flex flex-col gap-4 pt-1">
          <!-- Route Type Cards -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
            @for (r of networkRoutes; track r.id) {
              <div
                (click)="onRouteSelect(r.id)"
                class="p-3 rounded-xl border-2 cursor-pointer transition-all flex flex-col gap-1 hover:border-blue-400"
                [class.border-blue-600]="networkRoute === r.id"
                [class.bg-blue-50]="networkRoute === r.id"
                [class.border-slate-200]="networkRoute !== r.id"
                [class.bg-slate-50]="networkRoute !== r.id">
                <span class="font-bold text-slate-900 text-xs">{{ r.label }}</span>
                <span class="text-[10.5px] text-slate-500">{{ r.desc }}</span>
              </div>
            }
          </div>

          <!-- SSH Bastion Config Drawer (When SSH_BASTION is selected) -->
          @if (networkRoute === 'SSH_BASTION') {
            <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200/90 flex flex-col gap-3 animate-in fade-in duration-150">
              <span class="font-bold text-slate-800 text-xs">SSH Bastion / Jump Host Parameters:</span>
              <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div class="flex flex-col gap-1">
                  <label class="font-semibold text-slate-700 text-[11px]">Bastion Host / IP *</label>
                  <input
                    type="text"
                    [ngModel]="bastionHost"
                    (ngModelChange)="bastionHostChange.emit($event)"
                    placeholder="bastion.prod.company.com"
                    class="h-8 px-2.5 rounded-md bg-white border border-slate-200 text-xs font-semibold text-slate-900" />
                </div>
                <div class="flex flex-col gap-1">
                  <label class="font-semibold text-slate-700 text-[11px]">SSH User *</label>
                  <input
                    type="text"
                    [ngModel]="bastionUser"
                    (ngModelChange)="bastionUserChange.emit($event)"
                    placeholder="ec2-user"
                    class="h-8 px-2.5 rounded-md bg-white border border-slate-200 text-xs font-semibold text-slate-900" />
                </div>
                <div class="flex flex-col gap-1">
                  <label class="font-semibold text-slate-700 text-[11px]">SSH Key Secret Reference *</label>
                  <input
                    type="text"
                    [ngModel]="bastionKeyRef"
                    (ngModelChange)="bastionKeyRefChange.emit($event)"
                    placeholder="vault://secret/ssh/bastion_rsa"
                    class="h-8 px-2.5 rounded-md bg-white border border-slate-200 text-xs font-semibold text-slate-900" />
                </div>
              </div>
            </div>
          }

          <!-- Security Group Fields from Schema (e.g. SSL Mode) -->
          @for (field of getVisibleFieldsByGroup('SECURITY'); track field.id) {
            <div class="flex flex-col gap-1.5 pt-2 border-t border-slate-100">
              <div class="flex items-center justify-between">
                <label class="font-bold text-slate-800">{{ field.label }}</label>
                @if (field.helpText) {
                  <span class="text-[11px] text-slate-500 font-normal">{{ field.helpText }}</span>
                }
              </div>

              @if (field.type === 'select') {
                <select
                  [ngModel]="getFieldValue(field.id)"
                  (ngModelChange)="setFieldValue(field.id, $event)"
                  class="h-9 px-3 rounded-lg bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer max-w-sm">
                  @for (opt of field.options; track opt.value) {
                    <option [value]="opt.value">{{ opt.label }}</option>
                  }
                </select>
              }
            </div>
          }
        </div>
      </div>

      <!-- SECTION 4: Connector-Specific Advanced Options -->
      @if (getVisibleFieldsByGroup('OPTIONS').length > 0) {
        <div class="flex flex-col gap-3 p-5 rounded-xl bg-white border border-slate-200 shadow-2xs">
          <div class="flex items-center gap-2 pb-2.5 border-b border-slate-100">
            <app-lucide-icon name="sliders" [size]="15" class="text-blue-600"></app-lucide-icon>
            <h4 class="font-bold text-slate-900 uppercase tracking-wider text-[11px]">4. CONNECTOR-SPECIFIC OPTIONS</h4>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
            @for (field of getVisibleFieldsByGroup('OPTIONS'); track field.id) {
              <div class="flex flex-col gap-1.5" [class.md:col-span-2]="field.type === 'textarea'">
                <div class="flex items-center justify-between">
                  <label class="font-bold text-slate-800">{{ field.label }}</label>
                  @if (field.helpText) {
                    <span class="text-[11px] text-slate-500 font-normal">{{ field.helpText }}</span>
                  }
                </div>

                @switch (field.type) {
                  @case ('text') {
                    <input
                      type="text"
                      [ngModel]="getFieldValue(field.id)"
                      (ngModelChange)="setFieldValue(field.id, $event)"
                      [placeholder]="field.placeholder || ''"
                      class="h-9 px-3 rounded-lg bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all" />
                  }
                  @case ('number') {
                    <input
                      type="number"
                      [ngModel]="getFieldValue(field.id)"
                      (ngModelChange)="setFieldValue(field.id, $event)"
                      [placeholder]="field.placeholder || ''"
                      class="h-9 px-3 rounded-lg bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all" />
                  }
                  @case ('select') {
                    <select
                      [ngModel]="getFieldValue(field.id)"
                      (ngModelChange)="setFieldValue(field.id, $event)"
                      class="h-9 px-3 rounded-lg bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer">
                      @for (opt of field.options; track opt.value) {
                        <option [value]="opt.value">{{ opt.label }}</option>
                      }
                    </select>
                  }
                  @case ('boolean') {
                    <label class="flex items-center gap-2.5 pt-2 cursor-pointer">
                      <input
                        type="checkbox"
                        [ngModel]="getFieldValue(field.id)"
                        (ngModelChange)="setFieldValue(field.id, $event)"
                        class="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 cursor-pointer" />
                      <span class="font-semibold text-slate-800">{{ field.label }}</span>
                    </label>
                  }
                }
              </div>
            }
          </div>
        </div>
      }

    </div>
  `
})
export class DynamicProviderFormComponent {
  public currentProviderId = signal<PhysicalProviderId>('Oracle');

  @Input() set providerId(val: PhysicalProviderId) {
    if (val) {
      this.currentProviderId.set(val);
      this.initDefaultsForProvider(val);
    }
  }
  get providerId(): PhysicalProviderId {
    return this.currentProviderId();
  }

  @Input() formData: Record<string, any> = {};
  @Input() networkRoute: NetworkRouteType = 'DIRECT';
  @Input() bastionHost?: string;
  @Input() bastionUser?: string;
  @Input() bastionKeyRef?: string;

  @Output() formDataChange = new EventEmitter<Record<string, any>>();
  @Output() networkRouteChange = new EventEmitter<NetworkRouteType>();
  @Output() bastionHostChange = new EventEmitter<string>();
  @Output() bastionUserChange = new EventEmitter<string>();
  @Output() bastionKeyRefChange = new EventEmitter<string>();

  public schema = computed<ProviderFormSchema | undefined>(() => {
    return ALL_28_PROVIDER_SCHEMAS[this.currentProviderId()];
  });

  public networkRoutes: { id: NetworkRouteType; label: string; desc: string }[] = [
    { id: 'DIRECT', label: 'Direct TCP', desc: 'Direct network routing' },
    { id: 'SSH_BASTION', label: 'SSH Bastion', desc: 'Encrypted jump host tunnel' },
    { id: 'PROXY', label: 'Proxy / SOCKS5', desc: 'HTTP or SOCKS5 transit' },
    { id: 'PRIVATE_ENDPOINT', label: 'PrivateLink', desc: 'VPC private endpoint' }
  ];

  private initDefaultsForProvider(provider: PhysicalProviderId): void {
    const s = ALL_28_PROVIDER_SCHEMAS[provider];
    if (!s) return;
    const updated: Record<string, any> = {};
    for (const field of s.fields) {
      if (field.defaultValue !== undefined) {
        updated[field.id] = field.defaultValue;
      }
    }
    this.formDataChange.emit(updated);
  }

  public getVisibleFieldsByGroup(group: 'ENDPOINT' | 'AUTH' | 'SECURITY' | 'OPTIONS'): ProviderFormField[] {
    const s = this.schema();
    if (!s) return [];
    return s.fields.filter(f => {
      if (f.group !== group) return false;
      if (f.dependsOn && f.conditionValue !== undefined) {
        const parentVal = this.formData[f.dependsOn];
        return parentVal === f.conditionValue;
      }
      return true;
    });
  }

  public getFieldValue(fieldId: string): any {
    return this.formData[fieldId];
  }

  public setFieldValue(fieldId: string, value: any): void {
    const updated = { ...this.formData, [fieldId]: value };
    this.formDataChange.emit(updated);
  }

  public onRouteSelect(route: NetworkRouteType): void {
    this.networkRouteChange.emit(route);
  }
}
