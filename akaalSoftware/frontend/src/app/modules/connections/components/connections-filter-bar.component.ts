import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ConnectionsService } from '../connections.service';
import { ConnectionFamily, ConnectionVerificationState, ConnectionSortField } from '../connections.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../shared/components/custom-select.component';

@Component({
  selector: 'app-connections-filter-bar',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideIconComponent,
    CustomSelectComponent
  ],
  template: `
    <div class="flex flex-col gap-3 p-4 rounded-xl bg-white border border-slate-200 shadow-2xs select-none">
      
      <!-- Top Row: Search Input + Active Filter Count + Clear Action -->
      <div class="flex items-center justify-between gap-3 flex-wrap">
        
        <!-- Search Input with Search Icon -->
        <div class="relative flex-1 min-w-[280px] max-w-xl">
          <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <app-lucide-icon name="search" [size]="14"></app-lucide-icon>
          </div>
          <input
            type="text"
            [ngModel]="cs.filters().searchQuery"
            (ngModelChange)="onSearchChange($event)"
            placeholder="Search connections by name, provider, endpoint, or project reference..."
            class="w-full h-9 pl-9 pr-8 rounded-md bg-slate-50 hover:bg-slate-100/70 focus:bg-white border border-slate-300 text-xs font-medium text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-2xs"
          />
          @if (cs.filters().searchQuery) {
            <button
              type="button"
              (click)="onSearchChange('')"
              class="absolute inset-y-0 right-0 pr-2.5 flex items-center text-slate-400 hover:text-slate-700 cursor-pointer">
              <app-lucide-icon name="x" [size]="13"></app-lucide-icon>
            </button>
          }
        </div>

        <!-- Filter Count & Clear Button -->
        <div class="flex items-center gap-2.5 shrink-0">
          @if (cs.isFiltered()) {
            <span class="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
              {{ cs.activeFilterCount() }} active filter{{ cs.activeFilterCount() > 1 ? 's' : '' }}
            </span>
            <button
              type="button"
              (click)="cs.clearFilters()"
              class="h-8 px-3 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors cursor-pointer">
              Clear filters
            </button>
          }
        </div>

      </div>

      <!-- Bottom Row: Global Design System Custom Select Dropdowns -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5 pt-2 border-t border-slate-100">
        
        <!-- 1. Family Filter -->
        <div class="flex flex-col gap-1">
          <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Provider Family</label>
          <app-custom-select
            [options]="familyOptions"
            [value]="cs.filters().family"
            (valueChange)="onFamilyChange($event)"
            [size]="'sm'">
          </app-custom-select>
        </div>

        <!-- 2. Verification State Filter -->
        <div class="flex flex-col gap-1">
          <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Verification Status</label>
          <app-custom-select
            [options]="verificationOptions"
            [value]="cs.filters().verificationState"
            (valueChange)="onVerificationChange($event)"
            [size]="'sm'">
          </app-custom-select>
        </div>

        <!-- 3. Usage Context Filter -->
        <div class="flex flex-col gap-1">
          <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Workload Usage</label>
          <app-custom-select
            [options]="usageOptions"
            [value]="cs.filters().usageFilter"
            (valueChange)="onUsageChange($event)"
            [size]="'sm'">
          </app-custom-select>
        </div>

        <!-- 4. Environment Filter -->
        <div class="flex flex-col gap-1">
          <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Environment</label>
          <app-custom-select
            [options]="environmentOptions"
            [value]="cs.filters().environment"
            (valueChange)="onEnvironmentChange($event)"
            [size]="'sm'">
          </app-custom-select>
        </div>

        <!-- 5. Sort By -->
        <div class="flex flex-col gap-1">
          <label class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Sort By</label>
          <app-custom-select
            [options]="sortOptions"
            [value]="cs.filters().sortBy"
            (valueChange)="onSortChange($event)"
            [size]="'sm'">
          </app-custom-select>
        </div>

      </div>

    </div>
  `
})
export class ConnectionsFilterBarComponent {
  public cs = inject(ConnectionsService);

  public familyOptions: CustomSelectOption[] = [
    { label: 'All Provider Families', value: 'ALL', desc: '49 supported provider engines across 8 families' },
    { label: 'Relational Databases', value: 'RELATIONAL', desc: 'Oracle, PostgreSQL, MySQL, Db2, CockroachDB, SQL Server, Spanner, etc. (17)' },
    { label: 'Cloud Warehouses & Lakes', value: 'WAREHOUSE_LAKE', desc: 'Snowflake, BigQuery, Redshift, Databricks, ClickHouse (5)' },
    { label: 'NoSQL & Graph Stores', value: 'NOSQL_GRAPH', desc: 'MongoDB, Cassandra, ScyllaDB, Neo4j, Redis, Elasticsearch, DynamoDB (11)' },
    { label: 'Streaming & Messaging', value: 'STREAMING', desc: 'Kafka, Kinesis, Azure Event Hubs, Pub/Sub, RabbitMQ, Pulsar (6)' },
    { label: 'Object Storage', value: 'OBJECT_STORAGE', desc: 'Amazon S3, Google Cloud Storage, Azure Blob, MinIO, HDFS, OCI (6)' },
    { label: 'Time-Series Stores', value: 'TIME_SERIES', desc: 'InfluxDB (1)' },
    { label: 'SaaS & Enterprise Apps', value: 'APPLICATION', desc: 'Salesforce, ServiceNow, SAP NetWeaver (3)' },
    { label: 'Managed Cloud Profiles', value: 'MANAGED_CLOUD', desc: 'AWS, Azure, GCP, OCI Profile Resolvers (4)' }
  ];

  public verificationOptions: CustomSelectOption[] = [
    { label: 'All Verification States', value: 'ALL', desc: 'Truthful point-in-time verification statuses' },
    { label: 'Verified (Point-in-Time)', value: 'VERIFIED_GROUP', desc: 'Recent or point-in-time probe verified', badge: 'PROBED' },
    { label: 'Needs Attention', value: 'ATTENTION_GROUP', desc: 'Failed, stale, or mutated since last probe', badge: 'ATTN' },
    { label: 'Verified Recently', value: 'VERIFIED_RECENT', desc: 'Tested within current operational freshness window' },
    { label: 'Verified (Historical)', value: 'VERIFIED_POINT_IN_TIME', desc: 'Passed point-in-time probe in past' },
    { label: 'Verification Stale', value: 'VERIFIED_STALE', desc: 'Verification timestamp exceeds recommended threshold' },
    { label: 'Config Changed Since Test', value: 'CONFIG_CHANGED_SINCE_TEST', desc: 'Credentials or route mutated since last test' },
    { label: 'Partially Verified', value: 'PARTIAL_VERIFIED', desc: 'Connectivity OK · Permissions or schema unprobed' },
    { label: 'Never Tested', value: 'NEVER_TESTED', desc: 'Newly authored profile · Unprobed' },
    { label: 'Verification Failed', value: 'VERIFICATION_FAILED', desc: 'Most recent probe encountered an error' },
    { label: 'Verification Unavailable', value: 'UNAVAILABLE', desc: 'Verification authority unreachable' }
  ];

  public usageOptions: CustomSelectOption[] = [
    { label: 'All Usage Contexts', value: 'ALL', desc: 'All configured connections' },
    { label: 'In Active Workloads', value: 'IN_USE', desc: 'Bound to running migrations or validations' },
    { label: 'Referenced by Projects', value: 'REFERENCED_PROJECTS', desc: 'Associated with 1 or more projects' },
    { label: 'Unused (Zero Workloads)', value: 'UNUSED', desc: 'No project or migration bindings' }
  ];

  public environmentOptions: CustomSelectOption[] = [
    { label: 'All Environments', value: 'ALL', desc: 'All environment tiers' },
    { label: 'Production', value: 'Production', desc: 'Production workloads' },
    { label: 'Staging', value: 'Staging', desc: 'Pre-flight staging' },
    { label: 'Development', value: 'Development', desc: 'Dev and sandbox environments' }
  ];

  public sortOptions: CustomSelectOption[] = [
    { label: 'Name (A → Z)', value: 'name', desc: 'Alphabetical by connection name' },
    { label: 'Provider Engine', value: 'provider', desc: 'Grouped by physical provider' },
    { label: 'Provider Family', value: 'family', desc: 'Grouped by system family' },
    { label: 'Last Verified', value: 'lastVerified', desc: 'Most recently probed first' },
    { label: 'Recently Updated', value: 'updatedAt', desc: 'Newest configurations first' },
    { label: 'Workload Count', value: 'usageCount', desc: 'Most active workloads first' }
  ];

  public onSearchChange(q: string): void {
    this.cs.setSearchQuery(q);
  }

  public onFamilyChange(val: any): void {
    this.cs.setFamilyFilter(val as ConnectionFamily | 'ALL');
  }

  public onVerificationChange(val: any): void {
    this.cs.setVerificationFilter(val as any);
  }

  public onUsageChange(val: any): void {
    this.cs.setUsageFilter(val as any);
  }

  public onEnvironmentChange(val: any): void {
    this.cs.setEnvironmentFilter(val as any);
  }

  public onSortChange(val: any): void {
    this.cs.setSort(val as ConnectionSortField);
  }
}
