import { Injectable, signal, computed, inject, Optional } from '@angular/core';
import {
  TemplateItem,
  TemplateFilterState,
  TemplateAvailabilityState,
  TemplateMigrationMode,
  TemplateSortOption,
  TEMPLATE_MODE_DESCRIPTORS
} from './templates.models';
import { TEMPLATE_FIXTURES } from './templates.fixtures';
import { CustomSelectOption } from '../../../shared/components/custom-select.component';
import { MigrationIpc } from '../../../core/services/ipc/migration.ipc';
import { IpcService } from '../../../core/services/ipc.service';

@Injectable({
  providedIn: 'root'
})
export class TemplatesService {
  private migrationIpc?: MigrationIpc;
  private ipc?: IpcService;
  private unsubs: Array<() => void> = [];

  public templates = signal<TemplateItem[]>(TEMPLATE_FIXTURES);
  
  public filters = signal<TemplateFilterState>({
    searchQuery: '',
    mode: 'ALL',
    applicability: 'ALL',
    sortBy: 'name_asc'
  });

  public availabilityState = signal<TemplateAvailabilityState>('READY');
  public errorMessage = signal<string>('');

  constructor(
    @Optional() migrationIpc?: MigrationIpc,
    @Optional() ipc?: IpcService
  ) {
    if (ipc) {
      this.ipc = ipc;
    } else {
      try { this.ipc = inject(IpcService, { optional: true }) || undefined; } catch { this.ipc = undefined; }
    }
    if (migrationIpc) {
      this.migrationIpc = migrationIpc;
    } else {
      try { this.migrationIpc = inject(MigrationIpc, { optional: true }) || (this.ipc ? new MigrationIpc(this.ipc) : undefined); } catch { this.migrationIpc = undefined; }
    }

    this.setupSubscriptions();
    if (this.ipc && this.ipc.connectionState() === 'connected') {
      this.loadState();
    }
  }

  /**
   * Computed active filter indicator
   */
  public isFiltered = computed<boolean>(() => {
    const f = this.filters();
    return !!f.searchQuery.trim() || f.mode !== 'ALL' || f.applicability !== 'ALL';
  });

  /**
   * Filtered & sorted template catalog
   */
  public filteredTemplates = computed<TemplateItem[]>(() => {
    const all = this.templates();
    const f = this.filters();
    const q = f.searchQuery.trim().toLowerCase();

    let list = all.filter(tmpl => {
      // 1. Text search across name, description, mode, source, target
      if (q) {
        const modeDesc = TEMPLATE_MODE_DESCRIPTORS[tmpl.mode];
        const matchName = tmpl.name.toLowerCase().includes(q);
        const matchDesc = tmpl.description.toLowerCase().includes(q);
        const matchMode = modeDesc ? (modeDesc.label.toLowerCase().includes(q) || modeDesc.shortCode.toLowerCase().includes(q)) : false;
        const matchSource = tmpl.applicability.sourceProviderName.toLowerCase().includes(q);
        const matchTarget = tmpl.applicability.targetProviderName.toLowerCase().includes(q);
        const matchVersion = tmpl.versionLabel.toLowerCase().includes(q);

        if (!matchName && !matchDesc && !matchMode && !matchSource && !matchTarget && !matchVersion) {
          return false;
        }
      }

      // 2. Mode filter (M1-M7 only)
      if (f.mode !== 'ALL' && tmpl.mode !== f.mode) {
        return false;
      }

      // 3. Applicability filter
      if (f.applicability !== 'ALL') {
        const key = `${tmpl.applicability.sourceProviderName} -> ${tmpl.applicability.targetProviderName}`;
        if (key !== f.applicability) {
          return false;
        }
      }

      return true;
    });

    // Sort order
    list = [...list].sort((a, b) => {
      switch (f.sortBy) {
        case 'name_asc':
          return a.name.localeCompare(b.name);
        case 'name_desc':
          return b.name.localeCompare(a.name);
        case 'usage_desc': {
          const aUsage = a.usage.isUsageKnown ? (a.usage.migrationCount + a.usage.referencedProjectCount) : -1;
          const bUsage = b.usage.isUsageKnown ? (b.usage.migrationCount + b.usage.referencedProjectCount) : -1;
          return bUsage - aUsage;
        }
        case 'updated_desc':
          return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
        default:
          return a.name.localeCompare(b.name);
      }
    });

    return list;
  });

  /**
   * Mode options for GDS select dropdown (M1-M7 only, NEVER M8)
   */
  public modeOptions: CustomSelectOption[] = [
    { label: 'All Modes', value: 'ALL' },
    { label: TEMPLATE_MODE_DESCRIPTORS.M1_BULK.label, value: 'M1_BULK' },
    { label: TEMPLATE_MODE_DESCRIPTORS.M2_BULK_CDC.label, value: 'M2_BULK_CDC' },
    { label: TEMPLATE_MODE_DESCRIPTORS.M3_CDC.label, value: 'M3_CDC' },
    { label: TEMPLATE_MODE_DESCRIPTORS.M4_INCREMENTAL.label, value: 'M4_INCREMENTAL' },
    { label: TEMPLATE_MODE_DESCRIPTORS.M5_STATE_SYNC.label, value: 'M5_STATE_SYNC' },
    { label: TEMPLATE_MODE_DESCRIPTORS.M6_SCHEMA_ONLY.label, value: 'M6_SCHEMA_ONLY' },
    { label: TEMPLATE_MODE_DESCRIPTORS.M7_DATA_ONLY.label, value: 'M7_DATA_ONLY' },
  ];

  /**
   * Distinct applicability pairs derived from template catalog
   */
  public applicabilityOptions = computed<CustomSelectOption[]>(() => {
    const list = this.templates();
    const map = new Map<string, string>();
    for (const t of list) {
      const key = `${t.applicability.sourceProviderName} -> ${t.applicability.targetProviderName}`;
      const label = `${t.applicability.sourceProviderName} → ${t.applicability.targetProviderName}`;
      map.set(key, label);
    }

    const opts: CustomSelectOption[] = [{ label: 'All Applicabilities', value: 'ALL' }];
    for (const [key, label] of map.entries()) {
      opts.push({ label, value: key });
    }
    return opts;
  });

  /**
   * Sort options for GDS select dropdown
   */
  public sortOptions: CustomSelectOption[] = [
    { label: 'Name (A to Z)', value: 'name_asc' },
    { label: 'Name (Z to A)', value: 'name_desc' },
    { label: 'Most Used', value: 'usage_desc' },
    { label: 'Recently Updated', value: 'updated_desc' },
  ];

  public setSearchQuery(q: string): void {
    this.filters.update(curr => ({ ...curr, searchQuery: q }));
  }

  public setModeFilter(mode: TemplateMigrationMode | 'ALL'): void {
    this.filters.update(curr => ({ ...curr, mode }));
  }

  public setApplicabilityFilter(applicability: string | 'ALL'): void {
    this.filters.update(curr => ({ ...curr, applicability }));
  }

  public setSort(sortBy: TemplateSortOption): void {
    this.filters.update(curr => ({ ...curr, sortBy }));
  }

  public clearFilters(): void {
    this.filters.set({
      searchQuery: '',
      mode: 'ALL',
      applicability: 'ALL',
      sortBy: 'name_asc'
    });
  }

  private setupSubscriptions(): void {
    if (!this.ipc) return;

    const unsubConn = this.ipc.subscribe('akaal:engine:connected', () => {
      this.loadState();
    });
    this.unsubs.push(unsubConn);
  }

  public async loadState(): Promise<void> {
    if (!this.migrationIpc) {
      this.availabilityState.set('READY');
      return;
    }

    this.availabilityState.set('LOADING');
    this.errorMessage.set('');

    try {
      const res = await this.migrationIpc.listTemplates().catch(() => null);
      if (res && res.status === 'SUCCESS' && Array.isArray(res.data?.templates)) {
        const canonical = res.data.templates;
        if (canonical.length === 0) {
          this.templates.set([]);
          this.availabilityState.set('EMPTY');
          return;
        }

        const mapped: TemplateItem[] = canonical.map((t: any, idx: number) => {
          const cfg = t.configuration || {};
          const src = t.source_provider || cfg.definition?.sourceProvider || 'Oracle';
          const tgt = t.target_provider || cfg.definition?.targetProvider || 'PostgreSQL';
          return {
            id: t.id || t.template_id || `tmpl-canon-${idx + 1}`,
            name: t.name || 'Enterprise Migration Template',
            description: t.description || 'Configured template specification',
            mode: (t.mode || 'M1_BULK') as TemplateMigrationMode,
            applicability: {
              sourceProviderName: src,
              targetProviderName: tgt,
              description: `${src} to ${tgt}`
            },
            versionLabel: t.version || t.versionLabel || 'v1.0.0',
            updatedAt: t.updated_at || t.updatedAt || new Date().toISOString(),
            usage: {
              isUsageKnown: true,
              migrationCount: t.migration_count || 0,
              referencedProjectCount: t.project_count || 0
            }
          };
        });

        this.templates.set(mapped);
        this.availabilityState.set('READY');
      } else {
        this.availabilityState.set('READY');
        this.templates.set(TEMPLATE_FIXTURES);
      }
    } catch (err: any) {
      this.availabilityState.set('ERROR');
      this.errorMessage.set(err?.message || 'Failed to load templates');
    }
  }

  public reload(): void {
    this.availabilityState.set('READY');
    this.errorMessage.set('');
    this.templates.set(TEMPLATE_FIXTURES);
    if (this.ipc && this.ipc.connectionState() === 'connected') {
      this.loadState();
    }
  }

  public addTemplate(item: TemplateItem): void {
    this.templates.update(list => [item, ...list]);
  }

  public async deleteTemplate(id: string): Promise<boolean> {
    if (this.migrationIpc) {
      try {
        const res = await this.migrationIpc.deleteTemplate(id);
        if (res && res.status === 'SUCCESS') {
          this.templates.update(list => list.filter(t => t.id !== id));
          return true;
        }
      } catch (err: any) {
        this.errorMessage.set(err?.message || 'Failed to delete template');
        return false;
      }
    }
    this.templates.update(list => list.filter(t => t.id !== id));
    return true;
  }

  public loadFixturesForTesting(): void {
    this.availabilityState.set('READY');
    this.templates.set(TEMPLATE_FIXTURES);
    this.errorMessage.set('');
  }

  public setAvailabilityState(state: TemplateAvailabilityState, errorMsg?: string): void {
    this.availabilityState.set(state);
    if (errorMsg) {
      this.errorMessage.set(errorMsg);
    }
  }
}

