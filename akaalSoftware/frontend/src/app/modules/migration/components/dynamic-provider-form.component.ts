import {
  Component,
  Input,
  Output,
  EventEmitter,
  signal,
  computed,
  OnChanges,
  SimpleChanges
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../shared/components/custom-select.component';
import { PhysicalProviderId, NetworkRouteType, MigrationMode } from '../../../core/models/migration-view.models';
import { ALL_28_PROVIDER_SCHEMAS, ProviderFormField, ProviderFormSchema } from '../../../core/models/provider-form-schemas';

@Component({
  selector: 'app-dynamic-provider-form',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <div class="flex flex-col gap-4 text-xs select-none antialiased">
      
      <!-- =============================================================== -->
      <!-- 1. ENDPOINT & IDENTITY PARAMETERS (BALANCED 2-COL GRID)         -->
      <!-- =============================================================== -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        @for (field of visibleEndpointFields(); track field.id) {
          <div
            class="flex flex-col gap-1.5"
            [class.md:col-span-2]="field.type === 'textarea' || field.id === 'database_path' || field.id === 'replica_endpoints' || field.id === 'bootstrap_brokers' || field.id === 'node_urls' || field.id === 'tns_descriptor'">
            
            <div class="flex items-center justify-between">
              <label class="font-semibold text-slate-800 text-xs">
                {{ field.label }}
              </label>
              @if (field.helpText) {
                <span class="text-[11px] text-slate-500 font-medium">{{ field.helpText }}</span>
              }
            </div>

            <!-- Field Input Controls -->
            @switch (field.type) {
              @case ('text') {
                <input
                  type="text"
                  [ngModel]="getFieldValue(field.id)"
                  (ngModelChange)="setFieldValue(field.id, $event)"
                  [placeholder]="field.placeholder || ''"
                  class="h-9 px-3 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 transition-colors" />
              }
              @case ('number') {
                <input
                  type="number"
                  [ngModel]="getFieldValue(field.id)"
                  (ngModelChange)="setFieldValue(field.id, $event)"
                  [placeholder]="field.placeholder || ''"
                  class="h-9 px-3 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 transition-colors" />
              }
              @case ('select') {
                <app-custom-select
                  [options]="getSelectOptions(field)"
                  [value]="getFieldValue(field.id)"
                  (valueChange)="setFieldValue(field.id, $event)">
                </app-custom-select>
              }
              @case ('file_path') {
                <div class="relative flex items-center">
                  <input
                    type="text"
                    [ngModel]="getFieldValue(field.id)"
                    (ngModelChange)="setFieldValue(field.id, $event)"
                    [placeholder]="field.placeholder || ''"
                    class="w-full h-9 pl-3 pr-8 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 transition-colors" />
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
                  class="p-2.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 transition-colors resize-none"></textarea>
              }
            }
          </div>
        }
      </div>

      <!-- =============================================================== -->
      <!-- 2. AUTHENTICATION & SECRET REFERENCES (2-COL GRID)              -->
      <!-- =============================================================== -->
      @if (visibleAuthFields().length > 0) {
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3.5 pt-1">
          @for (field of visibleAuthFields(); track field.id) {
            <div
              class="flex flex-col gap-1.5"
              [class.md:col-span-2]="field.type === 'textarea' || field.id === 'service_account_json' || field.id === 'connection_string' || field.id === 'access_token_ref' || field.id === 'api_key_ref'">
              
              <div class="flex items-center justify-between">
                <label class="font-semibold text-slate-800 text-xs">
                  {{ field.label }}
                </label>
                @if (field.helpText) {
                  <span class="text-[11px] text-slate-500 font-medium">{{ field.helpText }}</span>
                }
              </div>

              @switch (field.type) {
                @case ('text') {
                  <input
                    type="text"
                    [ngModel]="getFieldValue(field.id)"
                    (ngModelChange)="setFieldValue(field.id, $event)"
                    [placeholder]="field.placeholder || ''"
                    class="h-9 px-3 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 transition-colors" />
                }
                @case ('password') {
                  <input
                    type="password"
                    [ngModel]="getFieldValue(field.id)"
                    (ngModelChange)="setFieldValue(field.id, $event)"
                    [placeholder]="field.placeholder || '••••••••••••'"
                    class="h-9 px-3 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 transition-colors" />
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
                      class="w-full h-9 pl-8 pr-3 rounded-lg bg-emerald-50/40 border border-emerald-200/80 text-xs font-semibold text-emerald-950 placeholder-slate-400 focus:outline-none focus:border-emerald-500 transition-colors" />
                  </div>
                }
                @case ('select') {
                  <app-custom-select
                    [options]="getSelectOptions(field)"
                    [value]="getFieldValue(field.id)"
                    (valueChange)="setFieldValue(field.id, $event)">
                  </app-custom-select>
                }
                @case ('textarea') {
                  <textarea
                    rows="2"
                    [ngModel]="getFieldValue(field.id)"
                    (ngModelChange)="setFieldValue(field.id, $event)"
                    [placeholder]="field.placeholder || ''"
                    class="p-2.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 transition-colors resize-none"></textarea>
                }
              }
            </div>
          }
        </div>
      }

      <!-- =============================================================== -->
      <!-- 3. TRANSPORT & SECURITY FIELDS                                  -->
      <!-- =============================================================== -->
      @if (visibleSecurityFields().length > 0) {
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3.5 pt-1">
          @for (field of visibleSecurityFields(); track field.id) {
            <div class="flex flex-col gap-1.5">
              <div class="flex items-center justify-between">
                <label class="font-semibold text-slate-800 text-xs">
                  {{ field.label }}
                </label>
                @if (field.helpText) {
                  <span class="text-[11px] text-slate-500 font-medium">{{ field.helpText }}</span>
                }
              </div>

              @if (field.type === 'select') {
                <app-custom-select
                  [options]="getSelectOptions(field)"
                  [value]="getFieldValue(field.id)"
                  (valueChange)="setFieldValue(field.id, $event)">
                </app-custom-select>
              } @else if (field.type === 'text') {
                <input
                  type="text"
                  [ngModel]="getFieldValue(field.id)"
                  (ngModelChange)="setFieldValue(field.id, $event)"
                  [placeholder]="field.placeholder || ''"
                  class="h-9 px-3 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 transition-colors" />
              }
            </div>
          }
        </div>
      }

      <!-- =============================================================== -->
      <!-- 4. CONTEXTUAL CDC FIELDS (WHEN STEP 1 MODE IS CDC)              -->
      <!-- =============================================================== -->
      @if (isCdcMode()) {
        <div class="flex flex-col gap-2.5 p-3.5 rounded-xl bg-blue-50/50 border border-blue-200/80">
          <div class="flex items-center justify-between">
            <span class="font-semibold text-xs text-blue-900">CDC Continuous Replication Parameters</span>
            <span class="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-blue-100 text-blue-800">Required for {{ mode }}</span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
            @if (currentProviderId() === 'PostgreSQL') {
              <div class="flex flex-col gap-1">
                <label class="font-semibold text-slate-800 text-xs">Replication Slot Name *</label>
                <input
                  type="text"
                  [ngModel]="getFieldValue('replication_slot') || 'akaal_cdc_slot'"
                  (ngModelChange)="setFieldValue('replication_slot', $event)"
                  placeholder="akaal_cdc_slot"
                  class="h-9 px-2.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 focus:outline-none focus:border-blue-500" />
              </div>
              <div class="flex flex-col gap-1">
                <label class="font-semibold text-slate-800 text-xs">Publication Name *</label>
                <input
                  type="text"
                  [ngModel]="getFieldValue('publication') || 'akaal_pub'"
                  (ngModelChange)="setFieldValue('publication', $event)"
                  placeholder="akaal_pub"
                  class="h-9 px-2.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 focus:outline-none focus:border-blue-500" />
              </div>
            } @else if (currentProviderId() === 'Oracle') {
              <div class="flex flex-col gap-1">
                <label class="font-semibold text-slate-800 text-xs">LogMiner Capture Mode</label>
                <app-custom-select
                  [options]="oracleLogMinerOptions"
                  [value]="getFieldValue('logminer_mode') || 'ONLINE'"
                  (valueChange)="setFieldValue('logminer_mode', $event)">
                </app-custom-select>
              </div>
              <div class="flex flex-col gap-1">
                <label class="font-semibold text-slate-800 text-xs">Dictionary Source</label>
                <app-custom-select
                  [options]="oracleDictSourceOptions"
                  [value]="getFieldValue('dict_source') || 'ONLINE_CATALOG'"
                  (valueChange)="setFieldValue('dict_source', $event)">
                </app-custom-select>
              </div>
            } @else if (currentProviderId() === 'MySQL' || currentProviderId() === 'MariaDB') {
              <div class="flex flex-col gap-1">
                <label class="font-semibold text-slate-800 text-xs">Server ID (Unique Replication ID) *</label>
                <input
                  type="number"
                  [ngModel]="getFieldValue('server_id') || 9876"
                  (ngModelChange)="setFieldValue('server_id', $event)"
                  placeholder="9876"
                  class="h-9 px-2.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 focus:outline-none focus:border-blue-500" />
              </div>
            }
          </div>
        </div>
      }

      <!-- =============================================================== -->
      <!-- 5. NETWORK ROUTING & TRAVERSAL (COLLAPSIBLE DISCLOSURE)         -->
      <!-- =============================================================== -->
      <div class="pt-1">
        <button
          type="button"
          (click)="isNetworkRoutingOpen.set(!isNetworkRoutingOpen())"
          class="flex items-center gap-1.5 text-xs font-semibold text-slate-700 hover:text-slate-900 transition-colors cursor-pointer focus:outline-none">
          <app-lucide-icon
            [name]="isNetworkRoutingOpen() ? 'chevron-down' : 'chevron-right'"
            [size]="14"
            class="text-slate-500"></app-lucide-icon>
          <span>Network routing &amp; traversal ({{ getRouteLabel(networkRoute) }})</span>
        </button>

        @if (isNetworkRoutingOpen()) {
          <div class="flex flex-col gap-3.5 p-3.5 mt-2 rounded-xl bg-slate-50 border border-slate-200 animate-in fade-in duration-100">
            
            <!-- 6 Route Type Selection Cards -->
            <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
              @for (r of networkRoutes; track r.id) {
                <button
                  type="button"
                  (click)="onRouteSelect(r.id)"
                  class="p-2.5 rounded-lg border text-left cursor-pointer transition-colors flex flex-col gap-0.5 focus:outline-none"
                  [class.border-blue-600]="networkRoute === r.id"
                  [class.bg-blue-50]="networkRoute === r.id"
                  [class.border-slate-200]="networkRoute !== r.id"
                  [class.bg-white]="networkRoute !== r.id">
                  <span class="font-semibold text-xs text-slate-900">{{ r.label }}</span>
                  <span class="text-[10px] text-slate-500 font-medium">{{ r.desc }}</span>
                </button>
              }
            </div>

            <!-- Route Type 1: DIRECT TCP -->
            @if (networkRoute === 'DIRECT') {
              <div class="px-3 py-2 rounded-lg bg-white border border-slate-200 text-xs font-medium text-slate-600 flex items-center gap-2">
                <app-lucide-icon name="check-circle-2" [size]="14" class="text-emerald-600"></app-lucide-icon>
                <span>Direct TCP socket connectivity to target host and port.</span>
              </div>
            }

            <!-- Route Type 2: SSH BASTION TUNNEL -->
            @if (networkRoute === 'SSH_BASTION') {
              <div class="flex flex-col gap-2.5 pt-1 border-t border-slate-200/80">
                <div class="grid grid-cols-1 md:grid-cols-4 gap-2.5">
                  <div class="flex flex-col gap-1 md:col-span-2">
                    <label class="font-semibold text-slate-700 text-xs">Bastion Host / IP *</label>
                    <input
                      type="text"
                      [ngModel]="bastionHost"
                      (ngModelChange)="bastionHostChange.emit($event)"
                      placeholder="bastion.prod.company.com"
                      class="h-9 px-2.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 focus:outline-none focus:border-blue-500" />
                  </div>
                  <div class="flex flex-col gap-1">
                    <label class="font-semibold text-slate-700 text-xs">SSH Port</label>
                    <input
                      type="number"
                      [ngModel]="getFieldValue('ssh_port') || 22"
                      (ngModelChange)="setFieldValue('ssh_port', $event)"
                      placeholder="22"
                      class="h-9 px-2.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 focus:outline-none focus:border-blue-500" />
                  </div>
                  <div class="flex flex-col gap-1">
                    <label class="font-semibold text-slate-700 text-xs">SSH User *</label>
                    <input
                      type="text"
                      [ngModel]="bastionUser"
                      (ngModelChange)="bastionUserChange.emit($event)"
                      placeholder="ec2-user"
                      class="h-9 px-2.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 focus:outline-none focus:border-blue-500" />
                  </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                  <div class="flex flex-col gap-1">
                    <label class="font-semibold text-slate-700 text-xs">SSH Private Key Secret Reference *</label>
                    <input
                      type="text"
                      [ngModel]="bastionKeyRef"
                      (ngModelChange)="bastionKeyRefChange.emit($event)"
                      placeholder="vault://secret/ssh/bastion_rsa"
                      class="h-9 px-2.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 focus:outline-none focus:border-blue-500" />
                  </div>
                  <div class="flex flex-col gap-1">
                    <label class="font-semibold text-slate-700 text-xs">Host Key SHA-256 Fingerprint</label>
                    <input
                      type="text"
                      [ngModel]="getFieldValue('ssh_host_key_fingerprint')"
                      (ngModelChange)="setFieldValue('ssh_host_key_fingerprint', $event)"
                      placeholder="SHA256:abcd1234efgh5678..."
                      class="h-9 px-2.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 focus:outline-none focus:border-blue-500" />
                  </div>
                </div>
              </div>
            }

            <!-- Route Type 3: HTTP PROXY -->
            @if (networkRoute === 'HTTP_PROXY' || networkRoute === 'PROXY') {
              <div class="grid grid-cols-1 md:grid-cols-4 gap-2.5 pt-1 border-t border-slate-200/80">
                <div class="flex flex-col gap-1 md:col-span-2">
                  <label class="font-semibold text-slate-700 text-xs">HTTP Proxy Host / IP *</label>
                  <input
                    type="text"
                    [ngModel]="getFieldValue('proxy_host')"
                    (ngModelChange)="setFieldValue('proxy_host', $event)"
                    placeholder="proxy.corp.internal or 10.0.1.50"
                    class="h-9 px-2.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 focus:outline-none focus:border-blue-500" />
                </div>
                <div class="flex flex-col gap-1">
                  <label class="font-semibold text-slate-700 text-xs">Proxy Port *</label>
                  <input
                    type="number"
                    [ngModel]="getFieldValue('proxy_port') || 8080"
                    (ngModelChange)="setFieldValue('proxy_port', $event)"
                    placeholder="8080"
                    class="h-9 px-2.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 focus:outline-none focus:border-blue-500" />
                </div>
                <div class="flex flex-col gap-1">
                  <label class="font-semibold text-slate-700 text-xs">Proxy Auth Secret Reference</label>
                  <input
                    type="text"
                    [ngModel]="getFieldValue('proxy_auth_ref')"
                    (ngModelChange)="setFieldValue('proxy_auth_ref', $event)"
                    placeholder="vault://secret/proxy/creds"
                    class="h-9 px-2.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 focus:outline-none focus:border-blue-500" />
                </div>
              </div>
            }

            <!-- Route Type 4: SOCKS5 PROXY -->
            @if (networkRoute === 'SOCKS5_PROXY') {
              <div class="grid grid-cols-1 md:grid-cols-4 gap-2.5 pt-1 border-t border-slate-200/80">
                <div class="flex flex-col gap-1 md:col-span-2">
                  <label class="font-semibold text-slate-700 text-xs">SOCKS5 Proxy Host / IP *</label>
                  <input
                    type="text"
                    [ngModel]="getFieldValue('proxy_host')"
                    (ngModelChange)="setFieldValue('proxy_host', $event)"
                    placeholder="socks5.corp.internal or 10.0.2.100"
                    class="h-9 px-2.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 focus:outline-none focus:border-blue-500" />
                </div>
                <div class="flex flex-col gap-1">
                  <label class="font-semibold text-slate-700 text-xs">SOCKS5 Port *</label>
                  <input
                    type="number"
                    [ngModel]="getFieldValue('proxy_port') || 1080"
                    (ngModelChange)="setFieldValue('proxy_port', $event)"
                    placeholder="1080"
                    class="h-9 px-2.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 focus:outline-none focus:border-blue-500" />
                </div>
                <div class="flex flex-col gap-1">
                  <label class="font-semibold text-slate-700 text-xs">SOCKS5 Auth Secret Reference</label>
                  <input
                    type="text"
                    [ngModel]="getFieldValue('proxy_auth_ref')"
                    (ngModelChange)="setFieldValue('proxy_auth_ref', $event)"
                    placeholder="vault://secret/socks5/creds"
                    class="h-9 px-2.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 focus:outline-none focus:border-blue-500" />
                </div>
              </div>
            }

            <!-- Route Type 5: PRIVATELINK / VPC ENDPOINT -->
            @if (networkRoute === 'PRIVATE_ENDPOINT') {
              <div class="grid grid-cols-1 md:grid-cols-3 gap-2.5 pt-1 border-t border-slate-200/80">
                <div class="flex flex-col gap-1 md:col-span-2">
                  <label class="font-semibold text-slate-700 text-xs">VPC PrivateLink Endpoint ID *</label>
                  <input
                    type="text"
                    [ngModel]="getFieldValue('private_endpoint_id')"
                    (ngModelChange)="setFieldValue('private_endpoint_id', $event)"
                    placeholder="vpce-0a1b2c3d4e5f6g7h8"
                    class="h-9 px-2.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 focus:outline-none focus:border-blue-500" />
                </div>
                <div class="flex flex-col gap-1">
                  <label class="font-semibold text-slate-700 text-xs">Cloud Region</label>
                  <input
                    type="text"
                    [ngModel]="getFieldValue('cloud_region') || 'us-east-1'"
                    (ngModelChange)="setFieldValue('cloud_region', $event)"
                    placeholder="us-east-1"
                    class="h-9 px-2.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 focus:outline-none focus:border-blue-500" />
                </div>
              </div>
            }

            <!-- Route Type 6: DNS HAPPY EYEBALLS -->
            @if (networkRoute === 'DNS_HAPPY_EYEBALLS') {
              <div class="grid grid-cols-1 md:grid-cols-2 gap-2.5 pt-1 border-t border-slate-200/80">
                <div class="flex flex-col gap-1">
                  <label class="font-semibold text-slate-700 text-xs">DNS Resolution Timeout (ms)</label>
                  <input
                    type="number"
                    [ngModel]="getFieldValue('dns_timeout_ms') || 5000"
                    (ngModelChange)="setFieldValue('dns_timeout_ms', $event)"
                    placeholder="5000"
                    class="h-9 px-2.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-900 focus:outline-none focus:border-blue-500" />
                </div>
                <div class="flex items-center text-xs text-slate-600 font-medium pt-4">
                  <span>Attempts IPv6 and IPv4 parallel resolution with 250ms fallback.</span>
                </div>
              </div>
            }

          </div>
        }
      </div>

    </div>
  `
})
export class DynamicProviderFormComponent implements OnChanges {
  public currentProviderId = signal<PhysicalProviderId>('Oracle');
  public isNetworkRoutingOpen = signal<boolean>(false);

  @Input() set providerId(val: PhysicalProviderId | undefined) {
    if (val) {
      this.currentProviderId.set(val);
    }
  }
  get providerId(): PhysicalProviderId {
    return this.currentProviderId();
  }

  @Input() mode?: MigrationMode;
  @Input() environment?: string;

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

  public isCdcMode = computed<boolean>(() => {
    return this.mode === 'M2_BULK_CDC' || this.mode === 'M3_CDC';
  });

  public networkRoutes: { id: NetworkRouteType; label: string; desc: string }[] = [
    { id: 'DIRECT', label: 'Direct TCP', desc: 'Direct socket route' },
    { id: 'SSH_BASTION', label: 'SSH Bastion', desc: 'Encrypted jump host' },
    { id: 'HTTP_PROXY', label: 'HTTP Proxy', desc: 'Forward proxy' },
    { id: 'SOCKS5_PROXY', label: 'SOCKS5 Proxy', desc: 'Raw TCP proxy' },
    { id: 'PRIVATE_ENDPOINT', label: 'PrivateLink', desc: 'VPC endpoint' },
    { id: 'DNS_HAPPY_EYEBALLS', label: 'Happy Eyeballs', desc: 'Dual IPv6/IPv4' }
  ];

  public oracleLogMinerOptions: CustomSelectOption[] = [
    { label: 'Online Redo Logs (Low Latency)', value: 'ONLINE', desc: 'Captures live online redo stream' },
    { label: 'Archived Logs Only (Batch CDC)', value: 'ARCHIVED', desc: 'Extracts committed archives' }
  ];

  public oracleDictSourceOptions: CustomSelectOption[] = [
    { label: 'Online Catalog (Standard)', value: 'ONLINE_CATALOG', desc: 'Extracts directly from live data dictionary' },
    { label: 'Redo Log Dictionary (Standby/DataGuard)', value: 'REDO_LOGS', desc: 'Uses dictionary extracted in redo stream' }
  ];

  public visibleEndpointFields = computed<ProviderFormField[]>(() => {
    const s = this.schema();
    if (!s) return [];
    return s.fields.filter(f => {
      if (f.group !== 'ENDPOINT' && f.group !== 'OPTIONS') return false;
      if (f.dependsOn && f.conditionValue !== undefined) {
        const parentVal = this.formData[f.dependsOn];
        return parentVal === f.conditionValue;
      }
      return true;
    });
  });

  public visibleAuthFields = computed<ProviderFormField[]>(() => {
    const s = this.schema();
    if (!s) return [];
    return s.fields.filter(f => {
      if (f.group !== 'AUTH') return false;
      if (f.dependsOn && f.conditionValue !== undefined) {
        const parentVal = this.formData[f.dependsOn];
        return parentVal === f.conditionValue;
      }
      return true;
    });
  });

  public visibleSecurityFields = computed<ProviderFormField[]>(() => {
    const s = this.schema();
    if (!s) return [];
    return s.fields.filter(f => f.group === 'SECURITY');
  });

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['providerId'] && changes['providerId'].currentValue) {
      this.initDefaultsForProvider(changes['providerId'].currentValue);
    }
  }

  public getRouteLabel(route: NetworkRouteType): string {
    const match = this.networkRoutes.find(r => r.id === route);
    return match ? match.label : 'Direct TCP';
  }

  public getSelectOptions(field: ProviderFormField): CustomSelectOption[] {
    return (field.options || []).map(opt => ({
      label: opt.label,
      value: opt.value,
      desc: opt.desc
    }));
  }

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
