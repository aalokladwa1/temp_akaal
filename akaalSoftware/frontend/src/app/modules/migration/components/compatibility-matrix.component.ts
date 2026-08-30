import { Component, Input, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';
import { PhysicalProviderId, MigrationMode } from '../../../core/models/migration-view.models';

export interface CompatibilityDimension {
  id: string;
  name: string;
  category: string;
  rating: 'SUPPORTED' | 'PARTIALLY_SUPPORTED' | 'CAPABILITY_DEPENDENT' | 'ASSESSMENT_REQUIRED' | 'UNSUPPORTED' | 'UNKNOWN';
  detail: string;
  prerequisite?: string;
}

@Component({
  selector: 'app-compatibility-matrix',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-4 text-xs select-none">
      
      <!-- Compatibility Overall Header -->
      <div class="p-4 rounded-xl border flex items-center justify-between gap-4 flex-wrap"
        [class.bg-blue-50]="isOverallSupported()"
        [class.border-blue-200]="isOverallSupported()"
        [class.bg-amber-50]="!isOverallSupported()"
        [class.border-amber-200]="!isOverallSupported()">
        
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg flex items-center justify-center font-bold"
            [class.bg-blue-600]="isOverallSupported()"
            [class.text-white]="isOverallSupported()"
            [class.bg-amber-600]="!isOverallSupported()"
            [class.text-white]="!isOverallSupported()">
            <app-lucide-icon [name]="isOverallSupported() ? 'shield-check' : 'alert-triangle'" [size]="16"></app-lucide-icon>
          </div>
          
          <div class="flex flex-col">
            <div class="flex items-center gap-2">
              <span class="font-bold text-slate-900 text-sm">
                {{ sourceProvider }} &rarr; {{ targetProvider }}
              </span>
              <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider"
                [class.bg-blue-100]="isOverallSupported()"
                [class.text-blue-800]="isOverallSupported()"
                [class.bg-amber-100]="!isOverallSupported()"
                [class.text-amber-800]="!isOverallSupported()">
                {{ getModeLabel(mode) }}
              </span>
            </div>
            <span class="text-xs text-slate-600 font-medium">
              Multi-dimensional route compatibility analysis across 8 engine dimensions.
            </span>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <span class="text-xs font-semibold text-slate-600">Route Feasibility:</span>
          <span class="px-2.5 py-1 rounded-md font-bold text-xs"
            [class.bg-emerald-100]="overallVerdict() === 'SUPPORTED'"
            [class.text-emerald-800]="overallVerdict() === 'SUPPORTED'"
            [class.bg-amber-100]="overallVerdict() === 'ASSESSMENT_REQUIRED' || overallVerdict() === 'PARTIALLY_SUPPORTED'"
            [class.text-amber-800]="overallVerdict() === 'ASSESSMENT_REQUIRED' || overallVerdict() === 'PARTIALLY_SUPPORTED'"
            [class.bg-rose-100]="overallVerdict() === 'UNSUPPORTED'"
            [class.text-rose-800]="overallVerdict() === 'UNSUPPORTED'">
            {{ formatRating(overallVerdict()) }}
          </span>
        </div>
      </div>

      <!-- 8-Dimensional Compatibility Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        @for (dim of dimensions(); track dim.id) {
          <div class="p-3.5 rounded-xl bg-white border border-slate-200/90 shadow-2xs flex flex-col justify-between gap-2.5">
            
            <div class="flex items-center justify-between gap-2">
              <div class="flex items-center gap-2">
                <span class="font-bold text-slate-900 text-xs">{{ dim.name }}</span>
              </div>
              <span class="px-2 py-0.5 rounded text-[10.5px] font-bold"
                [class.bg-emerald-50]="dim.rating === 'SUPPORTED'"
                [class.text-emerald-700]="dim.rating === 'SUPPORTED'"
                [class.border]="dim.rating === 'SUPPORTED'"
                [class.border-emerald-200]="dim.rating === 'SUPPORTED'"
                [class.bg-blue-50]="dim.rating === 'CAPABILITY_DEPENDENT'"
                [class.text-blue-700]="dim.rating === 'CAPABILITY_DEPENDENT'"
                [class.border-blue-200]="dim.rating === 'CAPABILITY_DEPENDENT'"
                [class.bg-amber-50]="dim.rating === 'PARTIALLY_SUPPORTED' || dim.rating === 'ASSESSMENT_REQUIRED'"
                [class.text-amber-800]="dim.rating === 'PARTIALLY_SUPPORTED' || dim.rating === 'ASSESSMENT_REQUIRED'"
                [class.border-amber-200]="dim.rating === 'PARTIALLY_SUPPORTED' || dim.rating === 'ASSESSMENT_REQUIRED'"
                [class.bg-rose-50]="dim.rating === 'UNSUPPORTED'"
                [class.text-rose-700]="dim.rating === 'UNSUPPORTED'"
                [class.border-rose-200]="dim.rating === 'UNSUPPORTED'">
                {{ formatRating(dim.rating) }}
              </span>
            </div>

            <p class="text-slate-600 text-[11.5px] leading-relaxed font-normal">
              {{ dim.detail }}
            </p>

            @if (dim.prerequisite) {
              <div class="pt-1.5 border-t border-slate-100 flex items-center gap-1.5 text-[11px] text-slate-500 font-medium">
                <app-lucide-icon name="info" [size]="12" class="text-blue-600 shrink-0"></app-lucide-icon>
                <span class="truncate"><strong>Prerequisite:</strong> {{ dim.prerequisite }}</span>
              </div>
            }

          </div>
        }
      </div>

    </div>
  `
})
export class CompatibilityMatrixComponent {
  @Input({ required: true }) sourceProvider!: PhysicalProviderId;
  @Input({ required: true }) targetProvider!: PhysicalProviderId;
  @Input({ required: true }) mode!: MigrationMode;

  public dimensions = computed<CompatibilityDimension[]>(() => {
    const src = this.sourceProvider;
    const tgt = this.targetProvider;
    const m = this.mode;

    const isHeterogeneous = src !== tgt;
    const isRelationalToRelational = ['Oracle', 'PostgreSQL', 'MySQL', 'Microsoft SQL Server', 'MariaDB', 'SQLite', 'IBM Db2'].includes(src) &&
      ['Oracle', 'PostgreSQL', 'MySQL', 'Microsoft SQL Server', 'MariaDB', 'SQLite', 'IBM Db2'].includes(tgt);
    const isToWarehouse = ['Snowflake', 'Google BigQuery', 'Amazon Redshift', 'Databricks / Delta Lake'].includes(tgt);
    const isToStreaming = ['Apache Kafka', 'Amazon Kinesis', 'Azure Event Hubs', 'Google Cloud Pub/Sub'].includes(tgt);

    return [
      {
        id: 'bulk_movement',
        name: '1. Bulk Data Movement',
        category: 'Data Plane',
        rating: 'SUPPORTED',
        detail: `High-throughput parallel partition streaming from ${src} to ${tgt} via native direct-path adapters.`,
        prerequisite: 'Network throughput and read replica capacity on source.'
      },
      {
        id: 'schema_translation',
        name: '2. Schema & DDL Translation',
        category: 'Schema Plane',
        rating: isHeterogeneous ? (isRelationalToRelational ? 'SUPPORTED' : 'PARTIALLY_SUPPORTED') : 'SUPPORTED',
        detail: isHeterogeneous
          ? `Automated AST schema translation from ${src} dialect to ${tgt} DDL with type coercion mapping.`
          : `Homogeneous 1:1 schema replication preserving exact native indexes and constraints.`,
        prerequisite: isHeterogeneous ? 'Review generated DDL in Step 5 Mapping Studio.' : undefined
      },
      {
        id: 'datatype_fidelity',
        name: '3. Data Type Mapping Fidelity',
        category: 'Data Plane',
        rating: isHeterogeneous ? 'PARTIALLY_SUPPORTED' : 'SUPPORTED',
        detail: isHeterogeneous
          ? `Specific proprietary datatypes (e.g. Oracle RAW, LOBs, Spatial, Arrays) require explicit coercion in Step 5.`
          : `Lossless native binary type fidelity verified.`,
        prerequisite: 'Inspect column mapping overrides before plan compilation.'
      },
      {
        id: 'code_conversion',
        name: '4. Code Conversion (PL/SQL / T-SQL / DDL)',
        category: 'Code Plane',
        rating: (src === 'Oracle' && tgt === 'PostgreSQL') || (src === 'Microsoft SQL Server' && tgt === 'PostgreSQL')
          ? 'ASSESSMENT_REQUIRED'
          : (m === 'M6_SCHEMA_ONLY' ? 'SUPPORTED' : 'CAPABILITY_DEPENDENT'),
        detail: (src === 'Oracle' && tgt === 'PostgreSQL')
          ? `Stored procedures, triggers, and packages require transpilation in Code Transpiler Studio (Step 5.2).`
          : `Engine conversion rules applied for views, sequences, and procedures.`,
        prerequisite: 'Review dual Monaco workbench findings.'
      },
      {
        id: 'cdc_route',
        name: '5. CDC Replication Route',
        category: 'Continuous Sync',
        rating: (m === 'M2_BULK_CDC' || m === 'M3_CDC')
          ? (['Oracle', 'PostgreSQL', 'MySQL', 'Microsoft SQL Server', 'MariaDB', 'MongoDB', 'ScyllaDB'].includes(src) ? 'SUPPORTED' : 'CAPABILITY_DEPENDENT')
          : 'SUPPORTED',
        detail: (m === 'M2_BULK_CDC' || m === 'M3_CDC')
          ? `Source log mining (LogMiner, WAL logical, or Oplog) streaming to target with watermark checkpointing.`
          : `CDC replication not requested under selected ${this.getModeLabel(m)} execution mode.`,
        prerequisite: (m === 'M2_BULK_CDC' || m === 'M3_CDC') ? 'Source database supplemental logging enabled.' : undefined
      },
      {
        id: 'write_authority',
        name: '6. Target Write & Transactional Authority',
        category: 'Target Plane',
        rating: isToWarehouse ? 'PARTIALLY_SUPPORTED' : (isToStreaming ? 'SUPPORTED' : 'SUPPORTED'),
        detail: isToWarehouse
          ? `Target is an analytical warehouse (micro-batch staged commits rather than single-row ACID locks).`
          : `Target supports ACID transactional writes and deferred constraint validation during bulk stream.`,
        prerequisite: 'Target service account requires DDL and INSERT/UPDATE grants.'
      },
      {
        id: 'environment_prereqs',
        name: '7. Prerequisites & Environment Readiness',
        category: 'Governance',
        rating: 'ASSESSMENT_REQUIRED',
        detail: `Preflight checks in Step 8 will evaluate network route latency, TLS handshake, and table lock policies.`,
        prerequisite: 'Ensure firewall permits TCP port routing from AKAAL cluster.'
      },
      {
        id: 'sandbox_support',
        name: '8. Transactional Sandbox / Rollback Support',
        category: 'Safety',
        rating: 'SUPPORTED',
        detail: `Target objects can be created in isolated temporary staging schemas prior to final cutover flip.`,
        prerequisite: 'Target user requires schema creation privileges.'
      }
    ];
  });

  public overallVerdict = computed<'SUPPORTED' | 'PARTIALLY_SUPPORTED' | 'ASSESSMENT_REQUIRED' | 'UNSUPPORTED'>(() => {
    const dims = this.dimensions();
    if (dims.some(d => d.rating === 'UNSUPPORTED')) return 'UNSUPPORTED';
    if (dims.some(d => d.rating === 'ASSESSMENT_REQUIRED')) return 'ASSESSMENT_REQUIRED';
    if (dims.some(d => d.rating === 'PARTIALLY_SUPPORTED')) return 'PARTIALLY_SUPPORTED';
    return 'SUPPORTED';
  });

  public isOverallSupported(): boolean {
    return this.overallVerdict() === 'SUPPORTED' || this.overallVerdict() === 'PARTIALLY_SUPPORTED';
  }

  public formatRating(rating: string): string {
    switch (rating) {
      case 'SUPPORTED': return 'Supported';
      case 'PARTIALLY_SUPPORTED': return 'Partially Supported';
      case 'CAPABILITY_DEPENDENT': return 'Capability Dependent';
      case 'ASSESSMENT_REQUIRED': return 'Assessment Required';
      case 'UNSUPPORTED': return 'Unsupported';
      default: return 'Unknown';
    }
  }

  public getModeLabel(mode: MigrationMode): string {
    switch (mode) {
      case 'M1_BULK': return 'Bulk Migration';
      case 'M2_BULK_CDC': return 'Bulk + CDC';
      case 'M3_CDC': return 'CDC Only';
      case 'M4_INCREMENTAL': return 'Incremental Query';
      case 'M5_STATE_SYNC': return 'State Synchronization';
      case 'M6_SCHEMA_ONLY': return 'Schema Only';
      case 'M7_DATA_ONLY': return 'Data Only';
    }
  }
}
