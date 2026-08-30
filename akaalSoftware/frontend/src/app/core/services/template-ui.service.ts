import { Injectable, signal, computed } from '@angular/core';
import { MigrationDevFixturesAdapter } from '../fixtures/migration-dev-fixtures.adapter';
import {
  MigrationTemplateItem,
  TemplateStrength,
  MigrationMode,
  PhysicalProviderId,
  TemplateCompatibilityVerdict
} from '../models/migration-view.models';

export interface TemplateBuilderDraftState {
  title: string;
  version: string;
  category: 'ORGANIZATION_STANDARD' | 'RECOMMENDED' | 'TEAM' | 'PROJECT' | 'DRAFT';
  description: string;
  sourceTypes: PhysicalProviderId[];
  targetTypes: PhysicalProviderId[];
  compatibleModes: MigrationMode[];
  strength: TemplateStrength;
  recommendedWorkers: number;
  currentStep: number;
}

@Injectable({
  providedIn: 'root'
})
export class TemplateUiService {
  private fixtures: MigrationDevFixturesAdapter;

  public templates = signal<MigrationTemplateItem[]>([]);
  public filterCategory = signal<string>('ALL');

  public filteredTemplates = computed<MigrationTemplateItem[]>(() => {
    const list = this.templates();
    const cat = this.filterCategory();
    if (cat === 'ALL') return list;
    return list.filter(t => t.category === cat);
  });

  public builderDraft = signal<TemplateBuilderDraftState>({
    title: '',
    version: 'v1.0.0',
    category: 'TEAM',
    description: '',
    sourceTypes: ['Oracle'],
    targetTypes: ['PostgreSQL'],
    compatibleModes: ['M2_BULK_CDC'],
    strength: 'RECOMMENDATION',
    recommendedWorkers: 8,
    currentStep: 1
  });

  constructor(fixtures?: MigrationDevFixturesAdapter) {
    this.fixtures = fixtures || new MigrationDevFixturesAdapter();
    this.templates.set(this.fixtures.getTemplates());
  }

  public assessCompatibility(tmpl: MigrationTemplateItem, targetMode: MigrationMode, source: PhysicalProviderId, target: PhysicalProviderId): TemplateCompatibilityVerdict {
    if (!tmpl.compatibleModes.includes(targetMode)) return 'INCOMPATIBLE';
    if (!tmpl.sourceTypes.includes(source) || !tmpl.targetTypes.includes(target)) return 'REVIEW_REQUIRED';
    return 'COMPATIBLE';
  }
}
