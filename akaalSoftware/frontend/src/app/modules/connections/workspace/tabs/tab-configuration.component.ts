import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ConnectionWorkspaceService } from '../connection-workspace.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-tab-configuration',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    @if (ws.connection(); as conn) {
      <div class="flex flex-col gap-6 animate-in fade-in duration-150 text-xs select-none">
        
        <!-- Notice / Staleness Alert after edit -->
        @if (ws.configNotice(); as notice) {
          <div class="p-4 bg-blue-50/80 border border-blue-200 rounded-xl flex items-center justify-between gap-4 text-xs text-blue-900 shadow-2xs">
            <div class="flex items-center gap-2.5">
              <app-lucide-icon name="info" [size]="16" class="text-blue-600 shrink-0"></app-lucide-icon>
              <span>{{ notice }}</span>
            </div>
            @if (ws.isVerificationStale()) {
              <button
                type="button"
                (click)="ws.testConnection()"
                class="px-3 py-1 rounded text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white transition-colors cursor-pointer shrink-0">
                Retest Connection Now
              </button>
            }
          </div>
        }

        <!-- Top Header & Action Controls -->
        <div class="flex items-center justify-between pb-3 border-b border-slate-200 flex-wrap gap-3">
          <div class="flex flex-col gap-0.5">
            <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider font-heading">
              Connection Configuration &amp; Topology
            </h2>
            <p class="text-xs text-slate-500 font-normal">
              Canonical provider addressing, credential references, TLS transport, and network routing specifications.
            </p>
          </div>

          <!-- Edit Mode Actions (Text Only, No Icons) -->
          <div class="flex items-center gap-2">
            @if (!ws.isEditingConfig()) {
              <button
                type="button"
                (click)="ws.startEditingConfig()"
                class="h-8 px-4 rounded-md text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white transition-colors cursor-pointer shadow-2xs">
                Edit Configuration
              </button>
            } @else {
              <button
                type="button"
                (click)="ws.cancelEditingConfig()"
                class="h-8 px-3.5 rounded-md text-xs font-semibold bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 transition-colors cursor-pointer">
                Cancel
              </button>
              <button
                type="button"
                (click)="ws.saveConfigChanges()"
                [disabled]="ws.isSavingConfig()"
                class="h-8 px-4 rounded-md text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white transition-colors cursor-pointer shadow-2xs disabled:opacity-50">
                {{ ws.isSavingConfig() ? 'Saving Changes...' : 'Save Changes' }}
              </button>
            }
          </div>
        </div>

        <!-- Edit Mode Governance Notice -->
        @if (ws.isEditingConfig()) {
          <div class="p-3.5 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-start gap-2.5">
            <app-lucide-icon name="alert-triangle" [size]="16" class="text-amber-600 shrink-0 mt-0.5"></app-lucide-icon>
            <div>
              <strong class="font-bold">Execution Snapshot Isolation:</strong>
              <span class="ml-1">
                Editing this reusable Connection updates future workflow executions. Initialized or currently active migrations hold frozen execution plan snapshots and are not mutated.
              </span>
            </div>
          </div>
        }

        <!-- ========================================================================= -->
        <!-- SECTION 1: ENDPOINT & NAMESPACE ADDRESSING (PROVIDER-AWARE)               -->
        <!-- ========================================================================= -->
        <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div class="flex items-center gap-2">
              <app-lucide-icon name="database" [size]="16" class="text-blue-600"></app-lucide-icon>
              <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
                1. Endpoint &amp; Addressing ({{ conn.providerName }})
              </span>
            </div>
          </div>

          <!-- READ VIEW -->
          @if (!ws.isEditingConfig()) {
            <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              
              <!-- Relational / Oracle / MySQL / Postgres / Sybase -->
              @if (conn.endpointConfig.host) {
                <div>
                  <span class="text-[11px] font-medium text-slate-400">Host / Addressing</span>
                  <div class="text-xs font-mono font-bold text-slate-900 pt-0.5">{{ conn.endpointConfig.host }}</div>
                </div>
              }

              @if (conn.endpointConfig.port) {
                <div>
                  <span class="text-[11px] font-medium text-slate-400">Port</span>
                  <div class="text-xs font-mono font-bold text-slate-900 pt-0.5">{{ conn.endpointConfig.port }}</div>
                </div>
              }

              @if (conn.endpointConfig.database) {
                <div>
                  <span class="text-[11px] font-medium text-slate-400">Database Name</span>
                  <div class="text-xs font-semibold text-slate-900 pt-0.5">{{ conn.endpointConfig.database }}</div>
                </div>
              }

              @if (conn.endpointConfig.serviceName) {
                <div>
                  <span class="text-[11px] font-medium text-slate-400">Oracle Service Name</span>
                  <div class="text-xs font-semibold text-slate-900 pt-0.5">{{ conn.endpointConfig.serviceName }}</div>
                </div>
              }

              @if (conn.endpointConfig.driverMode) {
                <div>
                  <span class="text-[11px] font-medium text-slate-400">Driver Mode</span>
                  <div class="text-xs font-semibold text-slate-800 pt-0.5">{{ conn.endpointConfig.driverMode }}</div>
                </div>
              }

              @if (conn.endpointConfig.schema) {
                <div>
                  <span class="text-[11px] font-medium text-slate-400">Target / Active Schemas</span>
                  <div class="text-xs font-semibold text-slate-800 pt-0.5">{{ conn.endpointConfig.schema }}</div>
                </div>
              }

              <!-- Streaming Kafka -->
              @if (conn.endpointConfig.bootstrapServers) {
                <div class="col-span-2">
                  <span class="text-[11px] font-medium text-slate-400">Kafka Bootstrap Servers</span>
                  <div class="text-xs font-mono font-bold text-slate-900 pt-0.5 break-all">{{ conn.endpointConfig.bootstrapServers }}</div>
                </div>
              }

              <!-- Object Storage S3 -->
              @if (conn.endpointConfig.bucketName) {
                <div>
                  <span class="text-[11px] font-medium text-slate-400">Bucket Name</span>
                  <div class="text-xs font-mono font-bold text-slate-900 pt-0.5">{{ conn.endpointConfig.bucketName }}</div>
                </div>
                <div>
                  <span class="text-[11px] font-medium text-slate-400">AWS Region</span>
                  <div class="text-xs font-semibold text-slate-800 pt-0.5">{{ conn.endpointConfig.region }}</div>
                </div>
                @if (conn.endpointConfig.prefix) {
                  <div>
                    <span class="text-[11px] font-medium text-slate-400">Prefix Path</span>
                    <div class="text-xs font-mono text-slate-800 pt-0.5">{{ conn.endpointConfig.prefix }}</div>
                  </div>
                }
              }

              <!-- BigQuery -->
              @if (conn.endpointConfig.projectId) {
                <div>
                  <span class="text-[11px] font-medium text-slate-400">GCP Project ID</span>
                  <div class="text-xs font-mono font-bold text-slate-900 pt-0.5">{{ conn.endpointConfig.projectId }}</div>
                </div>
                <div>
                  <span class="text-[11px] font-medium text-slate-400">Dataset</span>
                  <div class="text-xs font-semibold text-slate-800 pt-0.5">{{ conn.endpointConfig.datasetId }}</div>
                </div>
              }

              <!-- Salesforce -->
              @if (conn.endpointConfig.instanceUrl) {
                <div class="col-span-2">
                  <span class="text-[11px] font-medium text-slate-400">Salesforce Instance URL</span>
                  <div class="text-xs font-mono font-bold text-slate-900 pt-0.5">{{ conn.endpointConfig.instanceUrl }}</div>
                </div>
              }

              <!-- SQLite -->
              @if (conn.endpointConfig.filePath) {
                <div class="col-span-2">
                  <span class="text-[11px] font-medium text-slate-400">Database File Path</span>
                  <div class="text-xs font-mono font-bold text-slate-900 pt-0.5">{{ conn.endpointConfig.filePath }}</div>
                </div>
              }

            </div>
          } @else {
            <!-- EDIT FORM CONTROLS -->
            <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              @if (conn.endpointConfig.host !== undefined) {
                <div class="flex flex-col gap-1">
                  <label class="text-[11px] font-semibold text-slate-700">Host / Server</label>
                  <input
                    type="text"
                    [(ngModel)]="ws.configDraft().host"
                    class="h-8 px-3 rounded-md bg-white border border-slate-300 text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-500 shadow-2xs" />
                </div>
              }

              @if (conn.endpointConfig.port !== undefined) {
                <div class="flex flex-col gap-1">
                  <label class="text-[11px] font-semibold text-slate-700">Port</label>
                  <input
                    type="number"
                    [(ngModel)]="ws.configDraft().port"
                    class="h-8 px-3 rounded-md bg-white border border-slate-300 text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-500 shadow-2xs" />
                </div>
              }

              @if (conn.endpointConfig.database !== undefined) {
                <div class="flex flex-col gap-1">
                  <label class="text-[11px] font-semibold text-slate-700">Database Name</label>
                  <input
                    type="text"
                    [(ngModel)]="ws.configDraft().database"
                    class="h-8 px-3 rounded-md bg-white border border-slate-300 text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-500 shadow-2xs" />
                </div>
              }

              @if (conn.endpointConfig.serviceName !== undefined) {
                <div class="flex flex-col gap-1">
                  <label class="text-[11px] font-semibold text-slate-700">Service Name</label>
                  <input
                    type="text"
                    [(ngModel)]="ws.configDraft().serviceName"
                    class="h-8 px-3 rounded-md bg-white border border-slate-300 text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-500 shadow-2xs" />
                </div>
              }

              @if (conn.endpointConfig.schema !== undefined) {
                <div class="flex flex-col gap-1">
                  <label class="text-[11px] font-semibold text-slate-700">Schema</label>
                  <input
                    type="text"
                    [(ngModel)]="ws.configDraft().schema"
                    class="h-8 px-3 rounded-md bg-white border border-slate-300 text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-500 shadow-2xs" />
                </div>
              }

              @if (conn.endpointConfig.bootstrapServers !== undefined) {
                <div class="col-span-2 flex flex-col gap-1">
                  <label class="text-[11px] font-semibold text-slate-700">Bootstrap Servers</label>
                  <input
                    type="text"
                    [(ngModel)]="ws.configDraft().bootstrapServers"
                    class="h-8 px-3 rounded-md bg-white border border-slate-300 text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-500 shadow-2xs" />
                </div>
              }

              @if (conn.endpointConfig.bucketName !== undefined) {
                <div class="flex flex-col gap-1">
                  <label class="text-[11px] font-semibold text-slate-700">Bucket Name</label>
                  <input
                    type="text"
                    [(ngModel)]="ws.configDraft().bucketName"
                    class="h-8 px-3 rounded-md bg-white border border-slate-300 text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-500 shadow-2xs" />
                </div>
                <div class="flex flex-col gap-1">
                  <label class="text-[11px] font-semibold text-slate-700">Region</label>
                  <input
                    type="text"
                    [(ngModel)]="ws.configDraft().region"
                    class="h-8 px-3 rounded-md bg-white border border-slate-300 text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-500 shadow-2xs" />
                </div>
              }
            </div>
          }
        </div>

        <!-- ========================================================================= -->
        <!-- SECTION 2: AUTHENTICATION & SECRET REFERENCES                             -->
        <!-- ========================================================================= -->
        <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-100">
            <div class="flex items-center gap-2">
              <app-lucide-icon name="lock" [size]="16" class="text-blue-600"></app-lucide-icon>
              <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
                2. Authentication &amp; Secret References
              </span>
            </div>
            <span class="text-[11px] text-emerald-700 font-semibold flex items-center gap-1.5">
              <app-lucide-icon name="shield-check" [size]="13"></app-lucide-icon>
              <span>Zero Plaintext Credentials Expose</span>
            </span>
          </div>

          @if (!ws.isEditingConfig()) {
            <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              <div>
                <span class="text-[11px] font-medium text-slate-400">Auth Method</span>
                <div class="text-xs font-bold text-slate-900 pt-0.5">{{ conn.authConfig.authMethod }}</div>
              </div>

              @if (conn.authConfig.username) {
                <div>
                  <span class="text-[11px] font-medium text-slate-400">Username / Principal</span>
                  <div class="text-xs font-mono font-semibold text-slate-900 pt-0.5">{{ conn.authConfig.username }}</div>
                </div>
              }

              <div>
                <span class="text-[11px] font-medium text-slate-400">Secret Management Source</span>
                <div class="text-xs font-semibold text-slate-800 pt-0.5">{{ conn.authConfig.secretSource || 'Vault' }}</div>
              </div>

              @if (conn.authConfig.secretRef) {
                <div class="col-span-2">
                  <span class="text-[11px] font-medium text-slate-400">Secret Reference URI (Safe Metadata)</span>
                  <div class="text-xs font-mono text-slate-700 pt-0.5">{{ conn.authConfig.secretRef }}</div>
                </div>
              }

              @if (conn.authConfig.roleArn) {
                <div class="col-span-2">
                  <span class="text-[11px] font-medium text-slate-400">IAM Role ARN</span>
                  <div class="text-xs font-mono text-slate-700 pt-0.5">{{ conn.authConfig.roleArn }}</div>
                </div>
              }
            </div>
          } @else {
            <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              <div class="flex flex-col gap-1">
                <label class="text-[11px] font-semibold text-slate-700">Username / Principal</label>
                <input
                  type="text"
                  [(ngModel)]="ws.configDraft().username"
                  class="h-8 px-3 rounded-md bg-white border border-slate-300 text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-500 shadow-2xs" />
              </div>

              <div class="col-span-2 flex flex-col gap-1">
                <label class="text-[11px] font-semibold text-slate-700">Secret Reference Path</label>
                <input
                  type="text"
                  [(ngModel)]="ws.configDraft().secretRef"
                  placeholder="e.g. kv/data/production/credentials"
                  class="h-8 px-3 rounded-md bg-white border border-slate-300 text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-500 shadow-2xs" />
              </div>
            </div>
          }
        </div>

        <!-- ========================================================================= -->
        <!-- SECTION 3: TRANSPORT SECURITY (TLS / MTLS) & NETWORK ROUTE                -->
        <!-- ========================================================================= -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          <!-- TLS Card -->
          <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
            <div class="flex items-center justify-between pb-3 border-b border-slate-100">
              <div class="flex items-center gap-2">
                <app-lucide-icon name="shield" [size]="16" class="text-blue-600"></app-lucide-icon>
                <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
                  3. Transport Security (TLS)
                </span>
              </div>
            </div>

            @if (!ws.isEditingConfig()) {
              <div class="grid grid-cols-2 gap-3.5">
                <div>
                  <span class="text-[11px] font-medium text-slate-400">TLS Enforcement Mode</span>
                  <div class="text-xs font-bold text-slate-900 pt-0.5">{{ conn.tlsConfig.mode }}</div>
                </div>
                <div>
                  <span class="text-[11px] font-medium text-slate-400">Minimum Protocol</span>
                  <div class="text-xs font-semibold text-slate-800 pt-0.5">{{ conn.tlsConfig.minVersion }}</div>
                </div>
                @if (conn.tlsConfig.caCertRef) {
                  <div class="col-span-2">
                    <span class="text-[11px] font-medium text-slate-400">CA Certificate Reference</span>
                    <div class="text-xs font-mono text-slate-700 pt-0.5">{{ conn.tlsConfig.caCertRef }}</div>
                  </div>
                }
                <div>
                  <span class="text-[11px] font-medium text-slate-400">Mutual TLS (mTLS)</span>
                  <div class="text-xs font-semibold text-slate-800 pt-0.5">{{ conn.tlsConfig.isMtlsEnabled ? 'Enabled' : 'Disabled' }}</div>
                </div>
              </div>
            } @else {
              <div class="grid grid-cols-2 gap-3.5">
                <div class="flex flex-col gap-1">
                  <label class="text-[11px] font-semibold text-slate-700">TLS Mode</label>
                  <select
                    [(ngModel)]="ws.configDraft().tlsMode"
                    class="h-8 px-2.5 rounded-md bg-white border border-slate-300 text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-500 shadow-2xs">
                    <option value="DISABLED">DISABLED</option>
                    <option value="PREFERRED">PREFERRED</option>
                    <option value="REQUIRED">REQUIRED</option>
                    <option value="VERIFY_CA">VERIFY_CA</option>
                    <option value="VERIFY_FULL">VERIFY_FULL</option>
                  </select>
                </div>
                <div class="flex flex-col gap-1">
                  <label class="text-[11px] font-semibold text-slate-700">Min Version</label>
                  <select
                    [(ngModel)]="ws.configDraft().minTlsVersion"
                    class="h-8 px-2.5 rounded-md bg-white border border-slate-300 text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-500 shadow-2xs">
                    <option value="TLS_1_2">TLS 1.2</option>
                    <option value="TLS_1_3">TLS 1.3</option>
                  </select>
                </div>
              </div>
            }
          </div>

          <!-- Network Route Card -->
          <div class="p-6 bg-white border border-slate-200 rounded-xl shadow-2xs flex flex-col gap-4">
            <div class="flex items-center justify-between pb-3 border-b border-slate-100">
              <div class="flex items-center gap-2">
                <app-lucide-icon name="network" [size]="16" class="text-blue-600"></app-lucide-icon>
                <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
                  4. Network Route &amp; Transit
                </span>
              </div>
            </div>

            @if (!ws.isEditingConfig()) {
              <div class="grid grid-cols-2 gap-3.5">
                <div>
                  <span class="text-[11px] font-medium text-slate-400">Route Type</span>
                  <div class="text-xs font-bold text-slate-900 pt-0.5">{{ conn.routeConfig.type.replace('_', ' ') }}</div>
                </div>
                <div>
                  <span class="text-[11px] font-medium text-slate-400">Transit VPC / Route</span>
                  <div class="text-xs font-mono text-slate-800 pt-0.5">{{ conn.fabric.transitVpc || 'Direct Route' }}</div>
                </div>
                @if (conn.routeConfig.sshHost) {
                  <div>
                    <span class="text-[11px] font-medium text-slate-400">SSH Bastion Host</span>
                    <div class="text-xs font-mono text-slate-700 pt-0.5">{{ conn.routeConfig.sshHost }}:{{ conn.routeConfig.sshPort }}</div>
                  </div>
                }
                @if (conn.routeConfig.privateEndpointUrl) {
                  <div class="col-span-2">
                    <span class="text-[11px] font-medium text-slate-400">Private Endpoint</span>
                    <div class="text-xs font-mono text-slate-700 pt-0.5">{{ conn.routeConfig.privateEndpointUrl }}</div>
                  </div>
                }
              </div>
            } @else {
              <div class="grid grid-cols-2 gap-3.5">
                <div class="flex flex-col gap-1">
                  <label class="text-[11px] font-semibold text-slate-700">Route Type</label>
                  <select
                    [(ngModel)]="ws.configDraft().routeType"
                    class="h-8 px-2.5 rounded-md bg-white border border-slate-300 text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-500 shadow-2xs">
                    <option value="DIRECT">DIRECT</option>
                    <option value="HAPPY_EYEBALLS">DNS HAPPY EYEBALLS</option>
                    <option value="SSH_BASTION">SSH BASTION TUNNEL</option>
                    <option value="HTTP_PROXY">HTTP PROXY</option>
                    <option value="PRIVATE_ENDPOINT">PRIVATE ENDPOINT</option>
                  </select>
                </div>
                @if (ws.configDraft().routeType === 'SSH_BASTION') {
                  <div class="flex flex-col gap-1">
                    <label class="text-[11px] font-semibold text-slate-700">Bastion Host</label>
                    <input
                      type="text"
                      [(ngModel)]="ws.configDraft().sshHost"
                      class="h-8 px-3 rounded-md bg-white border border-slate-300 text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-500 shadow-2xs" />
                  </div>
                }
              </div>
            }
          </div>

        </div>

      </div>
    }
  `
})
export class TabConfigurationComponent {
  public ws = inject(ConnectionWorkspaceService);
}
