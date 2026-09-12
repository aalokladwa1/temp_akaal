import { Injectable, signal, computed, inject, Optional } from '@angular/core';
import { Router } from '@angular/router';
import {
  CreateTemplateDraftState,
  CreateTemplateStepIndex,
  INITIAL_CREATE_TEMPLATE_DRAFT,
  Step1DefinitionState,
  Step2DefaultsState,
  Step3ScopeMappingState,
  Step4EnterpriseConfigState,
  Step5GovernanceState,
  ObjectScopeRule,
  SchemaMappingRule,
  ColumnTypeOverride,
  MaskingRule
} from './create-template.models';
import { TemplatesService } from '../templates.service';
import { TemplateItem, TEMPLATE_MODE_DESCRIPTORS } from '../templates.models';

@Injectable({
  providedIn: 'root'
})
export class CreateTemplateService {
  private router: Router;
  private templatesService: TemplatesService;

  constructor(
    @Optional() router?: Router,
    @Optional() templatesService?: TemplatesService
  ) {
    if (router) {
      this.router = router;
    } else {
      try {
        this.router = inject(Router, { optional: true }) || ({ navigate: () => {} } as any);
      } catch {
        this.router = { navigate: () => {} } as any;
      }
    }

    if (templatesService) {
      this.templatesService = templatesService;
    } else {
      try {
        this.templatesService = inject(TemplatesService, { optional: true }) || new TemplatesService();
      } catch {
        this.templatesService = new TemplatesService();
      }
    }
  }

  public currentStep = signal<CreateTemplateStepIndex>(1);
  public draft = signal<CreateTemplateDraftState>(JSON.parse(JSON.stringify(INITIAL_CREATE_TEMPLATE_DRAFT)));
  public completedSteps = signal<Set<number>>(new Set<number>());

  // Step 1 Computed Fields
  public definition = computed<Step1DefinitionState>(() => this.draft().definition);
  public migrationDefaults = computed<Step2DefaultsState>(() => this.draft().migrationDefaults);
  public scopeMapping = computed<Step3ScopeMappingState>(() => this.draft().scopeMapping);
  public enterpriseConfig = computed<Step4EnterpriseConfigState>(() => this.draft().enterpriseConfig);
  public governance = computed<Step5GovernanceState>(() => this.draft().governance);

  public isDirty = computed<boolean>(() => {
    const d = this.draft();
    return d.definition.name.trim().length > 0;
  });

  public validationErrors = computed<string[]>(() => {
    const step = this.currentStep();
    const d = this.draft();
    const errors: string[] = [];

    if (step === 1) {
      if (!d.definition.name.trim()) {
        errors.push('Template Name is required.');
      }
      if (!d.definition.sourceProvider) {
        errors.push('Source Provider is required.');
      }
      if (!d.definition.targetProvider) {
        errors.push('Target Provider is required.');
      }
      if (!d.definition.mode || !TEMPLATE_MODE_DESCRIPTORS[d.definition.mode]) {
        errors.push('A valid Migration Mode is required.');
      }
    } else if (step === 2) {
      if (!d.migrationDefaults.migrationNamePattern.trim()) {
        errors.push('Migration Name Pattern is required.');
      }
    } else if (step === 3) {
      if (d.scopeMapping.objectScopeRules.length === 0) {
        errors.push('At least one Object Scope Rule is required.');
      }
    } else if (step === 4) {
      if (d.enterpriseConfig.performance.extractThreads < 1) {
        errors.push('Extract threads must be at least 1.');
      }
      if (d.enterpriseConfig.performance.batchSize < 100) {
        errors.push('Batch size must be at least 100 rows.');
      }
    } else if (step === 5) {
      if (!d.governance.secretReferenceRules.keyPathPrefix.trim()) {
        errors.push('Vault Key Path Prefix is required.');
      }
    }

    return errors;
  });

  public canProceed = computed<boolean>(() => {
    return this.validationErrors().length === 0;
  });

  public isStepComplete(stepIndex: number): boolean {
    return this.completedSteps().has(stepIndex);
  }

  // =========================================================================
  // NAVIGATION ACTIONS
  // =========================================================================

  public goToStep(stepIndex: CreateTemplateStepIndex): void {
    if (stepIndex < 1 || stepIndex > 6) return;
    
    // Can always jump backwards or to currently completed steps
    if (stepIndex < this.currentStep() || this.completedSteps().has(stepIndex) || this.canProceed()) {
      this.currentStep.set(stepIndex);
    }
  }

  public nextStep(): void {
    if (!this.canProceed()) return;

    const curr = this.currentStep();
    this.completedSteps.update(set => {
      const next = new Set(set);
      next.add(curr);
      return next;
    });

    if (curr < 6) {
      this.currentStep.set((curr + 1) as CreateTemplateStepIndex);
    }
  }

  public prevStep(): void {
    const curr = this.currentStep();
    if (curr > 1) {
      this.currentStep.set((curr - 1) as CreateTemplateStepIndex);
    }
  }

  public cancel(): void {
    this.resetDraft();
    this.router.navigate(['/migration/templates']);
  }

  public resetDraft(): void {
    this.currentStep.set(1);
    this.completedSteps.set(new Set<number>());
    this.draft.set(JSON.parse(JSON.stringify(INITIAL_CREATE_TEMPLATE_DRAFT)));
  }

  // =========================================================================
  // DRAFT UPDATE HELPERS
  // =========================================================================

  public updateDefinition(partial: Partial<Step1DefinitionState>): void {
    this.draft.update(d => ({
      ...d,
      definition: { ...d.definition, ...partial }
    }));
  }

  public updateDefaults(partial: Partial<Step2DefaultsState>): void {
    this.draft.update(d => ({
      ...d,
      migrationDefaults: { ...d.migrationDefaults, ...partial }
    }));
  }

  public updateScopeMapping(partial: Partial<Step3ScopeMappingState>): void {
    this.draft.update(d => ({
      ...d,
      scopeMapping: { ...d.scopeMapping, ...partial }
    }));
  }

  public updateEnterpriseConfig(partial: Partial<Step4EnterpriseConfigState>): void {
    this.draft.update(d => ({
      ...d,
      enterpriseConfig: { ...d.enterpriseConfig, ...partial }
    }));
  }

  public updateGovernance(partial: Partial<Step5GovernanceState>): void {
    this.draft.update(d => ({
      ...d,
      governance: { ...d.governance, ...partial }
    }));
  }

  // Step 3 Sub-helpers
  public addScopeRule(rule: Omit<ObjectScopeRule, 'id'>): void {
    const newRule: ObjectScopeRule = {
      ...rule,
      id: 'rule-' + Math.random().toString(36).substring(2, 9)
    };
    this.draft.update(d => ({
      ...d,
      scopeMapping: {
        ...d.scopeMapping,
        objectScopeRules: [...d.scopeMapping.objectScopeRules, newRule]
      }
    }));
  }

  public removeScopeRule(id: string): void {
    this.draft.update(d => ({
      ...d,
      scopeMapping: {
        ...d.scopeMapping,
        objectScopeRules: d.scopeMapping.objectScopeRules.filter(r => r.id !== id)
      }
    }));
  }

  public addSchemaMapping(sourceSchema: string, targetSchema: string): void {
    if (!sourceSchema.trim() || !targetSchema.trim()) return;
    const newMapping: SchemaMappingRule = {
      id: 'sm-' + Math.random().toString(36).substring(2, 9),
      sourceSchema: sourceSchema.trim(),
      targetSchema: targetSchema.trim()
    };
    this.draft.update(d => ({
      ...d,
      scopeMapping: {
        ...d.scopeMapping,
        schemaMappings: [...d.scopeMapping.schemaMappings, newMapping]
      }
    }));
  }

  public removeSchemaMapping(id: string): void {
    this.draft.update(d => ({
      ...d,
      scopeMapping: {
        ...d.scopeMapping,
        schemaMappings: d.scopeMapping.schemaMappings.filter(m => m.id !== id)
      }
    }));
  }

  public addColumnTypeOverride(sourceType: string, targetType: string): void {
    if (!sourceType.trim() || !targetType.trim()) return;
    const newOverride: ColumnTypeOverride = {
      id: 'co-' + Math.random().toString(36).substring(2, 9),
      sourceType: sourceType.trim(),
      targetType: targetType.trim()
    };
    this.draft.update(d => ({
      ...d,
      scopeMapping: {
        ...d.scopeMapping,
        columnTypeOverrides: [...d.scopeMapping.columnTypeOverrides, newOverride]
      }
    }));
  }

  public removeColumnTypeOverride(id: string): void {
    this.draft.update(d => ({
      ...d,
      scopeMapping: {
        ...d.scopeMapping,
        columnTypeOverrides: d.scopeMapping.columnTypeOverrides.filter(c => c.id !== id)
      }
    }));
  }

  public addMaskingRule(targetPattern: string, maskingType: MaskingRule['maskingType'], note?: string): void {
    if (!targetPattern.trim()) return;
    const newRule: MaskingRule = {
      id: 'mr-' + Math.random().toString(36).substring(2, 9),
      targetPattern: targetPattern.trim(),
      maskingType,
      note: note?.trim()
    };
    this.draft.update(d => ({
      ...d,
      scopeMapping: {
        ...d.scopeMapping,
        maskingRules: [...d.scopeMapping.maskingRules, newRule]
      }
    }));
  }

  public removeMaskingRule(id: string): void {
    this.draft.update(d => ({
      ...d,
      scopeMapping: {
        ...d.scopeMapping,
        maskingRules: d.scopeMapping.maskingRules.filter(m => m.id !== id)
      }
    }));
  }

  // =========================================================================
  // FINAL TRANSACTION: CREATE TEMPLATE
  // =========================================================================

  public createTemplate(): void {
    const d = this.draft();
    const newTemplateId = 'tmpl-' + Math.random().toString(36).substring(2, 9);
    const nowIso = new Date().toISOString();

    const providerDisplay = (id: string) => {
      const map: Record<string, string> = {
        oracle: 'Oracle',
        postgresql: 'PostgreSQL',
        mysql: 'MySQL',
        sqlserver: 'SQL Server',
        mongodb: 'MongoDB',
        snowflake: 'Snowflake',
        bigquery: 'BigQuery',
        kafka: 'Kafka',
        s3: 'Amazon S3',
        universal: 'Universal Any'
      };
      return map[id.toLowerCase()] || id.charAt(0).toUpperCase() + id.slice(1);
    };

    const newTemplate: TemplateItem = {
      id: newTemplateId,
      name: d.definition.name.trim(),
      description: d.definition.description.trim() || 'Custom instantiated migration template.',
      mode: d.definition.mode,
      applicability: {
        sourceProviderName: providerDisplay(d.definition.sourceProvider),
        targetProviderName: providerDisplay(d.definition.targetProvider)
      },
      scope: d.definition.scope,
      versionLabel: 'v1.0.0',
      lifecycle: 'PUBLISHED',
      usage: {
        referencedProjectCount: 0,
        migrationCount: 0,
        lastUsedAt: null,
        isUsageKnown: true,
        isUnused: true
      },
      createdAt: nowIso,
      updatedAt: nowIso
    };

    this.templatesService.addTemplate(newTemplate);
    this.resetDraft();
    this.router.navigate(['/migration/templates']);
  }
}
