import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CreateConnectionService } from '../create-connection.service';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { AccordionComponent } from '../../../../shared/components/accordion.component';

// Import Custom Extensions
import { OracleExtensionComponent } from './step2-extensions/oracle-extension.component';
import { BigQueryExtensionComponent } from './step2-extensions/bigquery-extension.component';
import { SpannerExtensionComponent } from './step2-extensions/spanner-extension.component';
import { SalesforceExtensionComponent } from './step2-extensions/salesforce-extension.component';
import { ServiceNowExtensionComponent } from './step2-extensions/servicenow-extension.component';
import { SapAppExtensionComponent } from './step2-extensions/sap-app-extension.component';

@Component({
  selector: 'app-step2-connection',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    CustomSelectComponent,
    LucideIconComponent,
    AccordionComponent,
    OracleExtensionComponent,
    BigQueryExtensionComponent,
    SpannerExtensionComponent,
    SalesforceExtensionComponent,
    ServiceNowExtensionComponent,
    SapAppExtensionComponent
  ],
  template: `
    <div class="max-w-5xl mx-auto w-full space-y-6 select-none animate-in fade-in duration-150 text-xs font-sans">
      
      <!-- Top Section Header -->
      <div class="flex flex-col gap-1 border-b border-slate-200 pb-3">
        <h2 class="text-base font-bold text-slate-900 tracking-tight">Connection &amp; Addressing Parameters</h2>
        <p class="text-xs text-slate-500 font-normal">
          Configure identity, addressing endpoints, and provider-specific topology options.
        </p>
      </div>

      <!-- Active Provider Context Bar -->
      @if (cs.selectedProvider(); as provider) {
        <div class="p-3.5 bg-blue-50/40 border border-blue-200 rounded-xl flex items-center justify-between flex-wrap gap-2">
          <div class="flex items-center gap-3 min-w-0">
            <div class="w-9 h-9 rounded-lg bg-white border border-blue-200 flex items-center justify-center text-blue-600 shrink-0 shadow-2xs">
              <app-lucide-icon [name]="provider.icon" [size]="18"></app-lucide-icon>
            </div>
            <div class="flex flex-col min-w-0">
              <div class="flex items-center gap-2">
                <span class="text-xs font-bold text-slate-900 truncate">{{ provider.name }}</span>
                <span class="px-1.5 py-0.2 text-[9px] font-mono font-bold bg-blue-100 text-blue-800 rounded">
                  {{ provider.id }}
                </span>
                @if (cs.draft().isManagedCloud) {
                  <span class="px-1.5 py-0.2 text-[9px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 rounded">
                    Managed Cloud Resolver
                  </span>
                }
              </div>
              <span class="text-[11px] text-slate-500">
                {{ provider.categoryLabel }} &middot; {{ provider.vendorName }}
              </span>
            </div>
          </div>

          <button
            type="button"
            (click)="cs.goToStep(1)"
            class="h-7 px-3 text-xs font-semibold text-blue-700 bg-white border border-blue-300 hover:bg-blue-50 rounded-md transition-colors flex items-center gap-1.5 cursor-pointer shadow-2xs">
            <app-lucide-icon name="arrow-left" [size]="12"></app-lucide-icon>
            <span>Change Provider</span>
          </button>
        </div>
      }

      <!-- ========================================================================= -->
      <!-- CARD 1: CONNECTION IDENTITY                                               -->
      <!-- ========================================================================= -->
      <div class="p-5 bg-white border border-slate-200 rounded-xl space-y-4 shadow-2xs">
        <div class="pb-2 border-b border-slate-100 flex items-center justify-between">
          <span class="text-xs font-bold text-slate-900">1. Connection Identity</span>
          <span class="text-[11px] text-slate-400 font-normal">Core resource naming &amp; governance environment</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          
          <!-- Connection Name -->
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">
              Connection Name <span class="text-rose-500">*</span>
            </label>
            <input
              type="text"
              [(ngModel)]="cs.draft().name"
              (ngModelChange)="cs.markConfigurationMutated()"
              placeholder="e.g. Finance Postgres Aurora Cluster"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600 transition-colors" />
            <span class="text-[11px] text-slate-400">
              Descriptive human-readable identifier shown on Connections Home and Workspaces.
            </span>
          </div>

          <!-- Environment -->
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">
              Operating Environment <span class="text-rose-500">*</span>
            </label>
            <app-custom-select
              [options]="environmentOptions"
              [value]="cs.draft().environment"
              (valueChange)="onEnvironmentChange($event)">
            </app-custom-select>
            <span class="text-[11px] text-slate-400">
              Governs security baseline, secret vault policies, and audit gating.
            </span>
          </div>

        </div>

        <!-- Description (Optional) -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-semibold text-slate-700">
            Description <span class="text-slate-400 font-normal">(Optional)</span>
          </label>
          <textarea
            rows="2"
            [(ngModel)]="cs.draft().description"
            (ngModelChange)="cs.markConfigurationMutated()"
            placeholder="Primary transactional database for billing reconciliation and ledger records..."
            class="w-full p-2.5 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600 transition-colors"></textarea>
        </div>

      </div>

      <!-- ========================================================================= -->
      <!-- CARD 2: ENDPOINT & ADDRESSING (Generic Schema vs Custom Extension)         -->
      <!-- ========================================================================= -->
      <div class="p-5 bg-white border border-slate-200 rounded-xl space-y-4 shadow-2xs">
        <div class="pb-2 border-b border-slate-100 flex items-center justify-between">
          <span class="text-xs font-bold text-slate-900">2. Endpoint &amp; Addressing Configuration</span>
          <span class="text-[11px] text-slate-400 font-normal">
            {{ cs.selectedProvider()?.isCustomExtension ? 'Dedicated Extension UX' : 'Schema-Driven Parameter Contract' }}
          </span>
        </div>

        <!-- Custom Extension Dispatcher -->
        @if (cs.selectedProvider(); as p) {
          @if (p.isCustomExtension) {
            @switch (p.customExtensionType) {
              @case ('ORACLE') {
                <app-oracle-extension [draft]="cs.draft()"></app-oracle-extension>
              }
              @case ('BIGQUERY') {
                <app-bigquery-extension [draft]="cs.draft()"></app-bigquery-extension>
              }
              @case ('SPANNER') {
                <app-spanner-extension [draft]="cs.draft()"></app-spanner-extension>
              }
              @case ('SALESFORCE') {
                <app-salesforce-extension [draft]="cs.draft()"></app-salesforce-extension>
              }
              @case ('SERVICENOW') {
                <app-servicenow-extension [draft]="cs.draft()"></app-servicenow-extension>
              }
              @case ('SAP_APPLICATION') {
                <app-sap-app-extension [draft]="cs.draft()"></app-sap-app-extension>
              }
            }
          }

          <!-- Generic Schema-Driven Rendering (43 Providers + File Dataset) -->
          @if (!p.isCustomExtension) {
            <div class="space-y-4">
              
              <!-- 1. SQLite File Path -->
              @if (p.id === 'sqlite') {
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div class="flex flex-col gap-1.5 md:col-span-2">
                    <label class="text-xs font-semibold text-slate-700">
                      Database File Path <span class="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      [(ngModel)]="cs.draft().parameters['database_path']"
                      (ngModelChange)="cs.markConfigurationMutated()"
                      placeholder="/var/data/enterprise.db or :memory: or C:\sqlite\app.db"
                      class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                  </div>
                  <div class="flex flex-col gap-1.5">
                    <label class="text-xs font-semibold text-slate-700">Journal Mode</label>
                    <app-custom-select
                      [options]="sqliteJournalOptions"
                      [value]="cs.draft().parameters['journal_mode'] || 'WAL'"
                      (valueChange)="setParam('journal_mode', $event)">
                    </app-custom-select>
                  </div>
                  <div class="flex flex-col gap-1.5">
                    <label class="text-xs font-semibold text-slate-700">Synchronous Mode</label>
                    <app-custom-select
                      [options]="sqliteSyncOptions"
                      [value]="cs.draft().parameters['synchronous_mode'] || 'NORMAL'"
                      (valueChange)="setParam('synchronous_mode', $event)">
                    </app-custom-select>
                  </div>
                </div>
              }

              <!-- 2. Object Storage (S3 / GCS / Azure Blob / MinIO / OCI) -->
              @else if (p.family === 'OBJECT_STORAGE' && p.id !== 'file_dataset') {
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  @if (p.id === 's3' || p.id === 'gcs' || p.id === 'minio' || p.id === 'oci_object_storage') {
                    <div class="flex flex-col gap-1.5">
                      <label class="text-xs font-semibold text-slate-700">
                        Bucket Name <span class="text-rose-500">*</span>
                      </label>
                      <input
                        type="text"
                        [(ngModel)]="cs.draft().parameters['bucket']"
                        (ngModelChange)="cs.markConfigurationMutated()"
                        placeholder="enterprise-financial-lake"
                        class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                    </div>
                  }

                  @if (p.id === 'azure_blob') {
                    <div class="flex flex-col gap-1.5">
                      <label class="text-xs font-semibold text-slate-700">
                        Storage Account Name <span class="text-rose-500">*</span>
                      </label>
                      <input
                        type="text"
                        [(ngModel)]="cs.draft().parameters['account_name']"
                        (ngModelChange)="cs.markConfigurationMutated()"
                        placeholder="mystorageaccount"
                        class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                    </div>
                    <div class="flex flex-col gap-1.5">
                      <label class="text-xs font-semibold text-slate-700">
                        Container Name <span class="text-rose-500">*</span>
                      </label>
                      <input
                        type="text"
                        [(ngModel)]="cs.draft().parameters['container_name']"
                        (ngModelChange)="cs.markConfigurationMutated()"
                        placeholder="lakehouse-data"
                        class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                    </div>
                  }

                  @if (p.id === 's3' || p.id === 'dynamodb' || p.id === 'kinesis') {
                    <div class="flex flex-col gap-1.5">
                      <label class="text-xs font-semibold text-slate-700">AWS Region</label>
                      <input
                        type="text"
                        [(ngModel)]="cs.draft().parameters['region']"
                        (ngModelChange)="cs.markConfigurationMutated()"
                        placeholder="us-east-1 or ap-south-1"
                        class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                    </div>
                  }

                  @if (p.id === 'oci_object_storage') {
                    <div class="flex flex-col gap-1.5">
                      <label class="text-xs font-semibold text-slate-700">OCI Namespace <span class="text-rose-500">*</span></label>
                      <input
                        type="text"
                        [(ngModel)]="cs.draft().parameters['namespace']"
                        (ngModelChange)="cs.markConfigurationMutated()"
                        placeholder="my_tenancy_namespace"
                        class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                    </div>
                  }

                  <div class="flex flex-col gap-1.5">
                    <label class="text-xs font-semibold text-slate-700">Object Key Prefix <span class="text-slate-400 font-normal">(Optional)</span></label>
                    <input
                      type="text"
                      [(ngModel)]="cs.draft().parameters['prefix']"
                      (ngModelChange)="cs.markConfigurationMutated()"
                      placeholder="finance/2026/q1/"
                      class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                  </div>
                </div>
              }

              <!-- 3. Streaming (Kafka / Pulsar / Kinesis / EventHubs / PubSub / RabbitMQ) -->
              @else if (p.family === 'STREAMING') {
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  @if (p.id === 'kafka') {
                    <div class="flex flex-col gap-1.5 md:col-span-2">
                      <label class="text-xs font-semibold text-slate-700">
                        Bootstrap Servers <span class="text-rose-500">*</span>
                      </label>
                      <input
                        type="text"
                        [(ngModel)]="cs.draft().parameters['bootstrap_servers']"
                        (ngModelChange)="cs.markConfigurationMutated()"
                        placeholder="kafka-broker1.corp:9092,kafka-broker2.corp:9092"
                        class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600 font-mono" />
                    </div>
                    <div class="flex flex-col gap-1.5">
                      <label class="text-xs font-semibold text-slate-700">Consumer Group ID</label>
                      <input
                        type="text"
                        [(ngModel)]="cs.draft().parameters['consumer_group']"
                        (ngModelChange)="cs.markConfigurationMutated()"
                        placeholder="akaal-migration-group"
                        class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                    </div>
                    <div class="flex flex-col gap-1.5">
                      <label class="text-xs font-semibold text-slate-700">Schema Registry URL <span class="text-slate-400 font-normal">(Optional)</span></label>
                      <input
                        type="text"
                        [(ngModel)]="cs.draft().parameters['schema_registry']"
                        (ngModelChange)="cs.markConfigurationMutated()"
                        placeholder="http://schema-registry.corp:8081"
                        class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                    </div>
                  }
                  @if (p.id === 'pulsar') {
                    <div class="flex flex-col gap-1.5 md:col-span-2">
                      <label class="text-xs font-semibold text-slate-700">Pulsar Service URL <span class="text-rose-500">*</span></label>
                      <input
                        type="text"
                        [(ngModel)]="cs.draft().parameters['service_url']"
                        (ngModelChange)="cs.markConfigurationMutated()"
                        placeholder="pulsar://pulsar-proxy.corp:6650 or pulsar+ssl://..."
                        class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600 font-mono" />
                    </div>
                  }
                  @if (p.id === 'eventhubs') {
                    <div class="flex flex-col gap-1.5 md:col-span-2">
                      <label class="text-xs font-semibold text-slate-700">Event Hubs Namespace <span class="text-rose-500">*</span></label>
                      <input
                        type="text"
                        [(ngModel)]="cs.draft().parameters['namespace']"
                        (ngModelChange)="cs.markConfigurationMutated()"
                        placeholder="myeventhubns.servicebus.windows.net"
                        class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                    </div>
                  }
                  @if (p.id === 'pubsub') {
                    <div class="flex flex-col gap-1.5 md:col-span-2">
                      <label class="text-xs font-semibold text-slate-700">Google Cloud Project ID <span class="text-rose-500">*</span></label>
                      <input
                        type="text"
                        [(ngModel)]="cs.draft().parameters['project_id']"
                        (ngModelChange)="cs.markConfigurationMutated()"
                        placeholder="enterprise-streaming-prod"
                        class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                    </div>
                  }
                </div>
              }

              <!-- 4. File Dataset Transport -->
              @else if (p.id === 'file_dataset') {
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div class="flex flex-col gap-1.5 md:col-span-2">
                    <label class="text-xs font-semibold text-slate-700">
                      Dataset File / Directory Path <span class="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      [(ngModel)]="cs.draft().parameters['file_path']"
                      (ngModelChange)="cs.markConfigurationMutated()"
                      placeholder="/data/lake/exports/transactions.parquet or C:\data\export.csv"
                      class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                  </div>
                  @if (cs.draft().fileDatasetFormat === 'CSV') {
                    <div class="flex flex-col gap-1.5">
                      <label class="text-xs font-semibold text-slate-700">Delimiter</label>
                      <input
                        type="text"
                        [(ngModel)]="cs.draft().parameters['csv_delimiter']"
                        placeholder=","
                        class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600 font-mono" />
                    </div>
                    <div class="flex flex-col justify-center gap-1.5 pt-4">
                      <label class="flex items-center gap-2 cursor-pointer select-none">
                        <input
                          type="checkbox"
                          [(ngModel)]="cs.draft().parameters['csv_header']"
                          class="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer" />
                        <span class="text-xs font-medium text-slate-700">First row contains column headers</span>
                      </label>
                    </div>
                  }
                </div>
              }

              <!-- 5. Default Relational / NoSQL / Warehouse Form (Host, Port, Database, Schema) -->
              @else {
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                  
                  <!-- Host -->
                  <div class="flex flex-col gap-1.5 md:col-span-2">
                    <label class="text-xs font-semibold text-slate-700">
                      Host / Primary Endpoint <span class="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      [(ngModel)]="cs.draft().parameters['host']"
                      (ngModelChange)="cs.markConfigurationMutated()"
                      placeholder="db-cluster.corp.internal or 10.0.4.15"
                      class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                  </div>

                  <!-- Port -->
                  <div class="flex flex-col gap-1.5">
                    <label class="text-xs font-semibold text-slate-700">
                      Port <span class="text-rose-500">*</span>
                    </label>
                    <input
                      type="number"
                      [(ngModel)]="cs.draft().parameters['port']"
                      (ngModelChange)="cs.markConfigurationMutated()"
                      [placeholder]="p.defaultPort ? '' + p.defaultPort : '5432'"
                      class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                  </div>

                  <!-- Database / Keyspace / Warehouse -->
                  <div class="flex flex-col gap-1.5">
                    <label class="text-xs font-semibold text-slate-700">
                      {{ p.family === 'NOSQL_GRAPH' ? 'Database / Keyspace' : (p.id === 'snowflake' ? 'Warehouse / Database' : 'Database Name') }}
                    </label>
                    <input
                      type="text"
                      [(ngModel)]="cs.draft().parameters['database']"
                      (ngModelChange)="cs.markConfigurationMutated()"
                      placeholder="finance_prod"
                      class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                  </div>

                  <!-- Schema / Namespace -->
                  <div class="flex flex-col gap-1.5">
                    <label class="text-xs font-semibold text-slate-700">Schema / Namespace</label>
                    <input
                      type="text"
                      [(ngModel)]="cs.draft().parameters['schema']"
                      (ngModelChange)="cs.markConfigurationMutated()"
                      placeholder="public"
                      class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                  </div>

                  <!-- Snowflake Account or Cassandra Datacenter -->
                  @if (p.id === 'snowflake') {
                    <div class="flex flex-col gap-1.5">
                      <label class="text-xs font-semibold text-slate-700">Snowflake Account Identifier</label>
                      <input
                        type="text"
                        [(ngModel)]="cs.draft().parameters['account']"
                        (ngModelChange)="cs.markConfigurationMutated()"
                        placeholder="xy12345.us-east-1"
                        class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                    </div>
                  }
                  @if (p.id === 'cassandra' || p.id === 'scylladb') {
                    <div class="flex flex-col gap-1.5">
                      <label class="text-xs font-semibold text-slate-700">Local Datacenter Name</label>
                      <input
                        type="text"
                        [(ngModel)]="cs.draft().parameters['datacenter']"
                        (ngModelChange)="cs.markConfigurationMutated()"
                        placeholder="datacenter1"
                        class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
                    </div>
                  }
                </div>
              }

            </div>
          }
        }

      </div>

      <!-- ========================================================================= -->
      <!-- CARD 3: ADVANCED SETTINGS ACCORDION                                       -->
      <!-- ========================================================================= -->
      <app-accordion
        title="Advanced Addressing &amp; Driver Settings"
        subtitle="Timeouts, Charsets, Application Name"
        icon="sliders"
        [isOpen]="false">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">Connect Timeout (seconds)</label>
            <input
              type="number"
              [(ngModel)]="cs.draft().parameters['connect_timeout']"
              placeholder="15"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">Application Name / Session Tag</label>
            <input
              type="text"
              [(ngModel)]="cs.draft().parameters['application_name']"
              placeholder="AKAAL_Enterprise_Bridge"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-slate-700">Character Set</label>
            <input
              type="text"
              [(ngModel)]="cs.draft().parameters['charset']"
              placeholder="utf8mb4 / UTF8"
              class="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-blue-600" />
          </div>
        </div>
      </app-accordion>

    </div>
  `
})
export class Step2ConnectionComponent {
  public cs = inject(CreateConnectionService);

  public environmentOptions: CustomSelectOption[] = [
    { label: 'Production (Enforced TLS & Strict Secrets)', value: 'Production' },
    { label: 'Staging / Pre-Production', value: 'Staging' },
    { label: 'Development / QA Sandbox', value: 'Development' },
    { label: 'Disaster Recovery (Standby Target)', value: 'Disaster Recovery' }
  ];

  public sqliteJournalOptions: CustomSelectOption[] = [
    { label: 'WAL (Write-Ahead Log - Recommended)', value: 'WAL' },
    { label: 'DELETE', value: 'DELETE' },
    { label: 'TRUNCATE', value: 'TRUNCATE' },
    { label: 'MEMORY', value: 'MEMORY' },
    { label: 'OFF', value: 'OFF' }
  ];

  public sqliteSyncOptions: CustomSelectOption[] = [
    { label: 'NORMAL (Balanced Safety/Speed)', value: 'NORMAL' },
    { label: 'FULL (Strict Sync)', value: 'FULL' },
    { label: 'OFF (Maximum Throughput)', value: 'OFF' }
  ];

  public onEnvironmentChange(val: string): void {
    this.cs.draft().environment = val as any;
    this.cs.markConfigurationMutated();
  }

  public setParam(key: string, val: any): void {
    this.cs.draft().parameters[key] = val;
    this.cs.markConfigurationMutated();
  }
}
