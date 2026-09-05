import { Injectable, signal, computed, inject, effect } from '@angular/core';
import {
  Step5WorkspaceTab,
  MappingSubWorkspace,
  DataControlCategory,
  MappingStatusBucket,
  UiWorkState,
  ConversionSafetyState,
  ReadinessState,
  ObjectMappingContract,
  ColumnMappingContract,
  TranspilerObjectContract,
  NamespaceRoutingRule,
  PrivacyItemContract,
  CleansingItemContract,
  FilterItemContract,
  DeduplicationItemContract,
  QualityItemContract,
  CapabilityOptionRef,
  CompatibilityHelperRef,
  Step5MappingPacket,
  Step5SummaryMetrics,
  DeduplicationConfig,
  TranspilerDiagnostic
} from '../../modules/migration/create/steps/step5-mapping.models';
import { MigrationUiService } from './migration-ui.service';
import { Step5MappingAdapterService } from './step5-mapping-adapter.service';

export interface PendingNavigationAction {
  title: string;
  description: string;
  proceed: () => void;
}

/**
 * Step5MappingStoreService
 *
 * PURE UI STATE STORE:
 * Manages active workspace (Mapping Studio vs Transpiler Studio),
 * Mapping Studio sub-workspaces (Overview, Structure, Fields, Data Controls),
 * Data Controls categories, draft vs applied state, dirty tracking, Apply/Revert execution,
 * Unsaved Changes protection, and Step 5 UI Workflow Readiness.
 *
 * ZERO BACKEND / CONVERSION AUTHORITY:
 * Strictly delegates domain packets to Step5MappingAdapterService (P7.D boundary).
 */
@Injectable({
  providedIn: 'root'
})
export class Step5MappingStoreService {
  private ms: MigrationUiService;
  private adapter: Step5MappingAdapterService;

  // =========================================================================
  // WORKSPACE NAVIGATION
  // =========================================================================
  public readonly activeWorkspace = signal<Step5WorkspaceTab>('MAPPING');
  public readonly activeSubWorkspace = signal<MappingSubWorkspace>('OVERVIEW');
  public readonly activeControlsCategory = signal<DataControlCategory>('PRIVACY');

  // Legacy workMode support for backward compatibility with specs
  public readonly workMode = computed<'REVIEW' | 'MAP'>(() => {
    return this.activeSubWorkspace() === 'OVERVIEW' ? 'REVIEW' : 'MAP';
  });

  // Selection & Focus
  public readonly selectedNamespaceName = signal<string | null>(null);
  public readonly selectedObjectId = signal<string | null>(null);
  public readonly selectedCodeObjectId = signal<string | null>(null);
  public readonly activeFieldDetailId = signal<string | null>(null);

  // Search & Filter
  public readonly searchQuery = signal<string>('');
  public readonly statusFilter = signal<MappingStatusBucket>('ALL');

  // Bulk Selection (Fields & Objects)
  public readonly selectedFieldIds = signal<Set<string>>(new Set());
  public readonly selectedObjectIds = signal<Set<string>>(new Set());

  // Transpiler Studio Modes
  public readonly transpilerViewMode = signal<'SOURCE' | 'SIDE_BY_SIDE' | 'TARGET'>('SIDE_BY_SIDE');
  public readonly isTranspilerFocusMode = signal<boolean>(false);
  public readonly isDiagnosticsExpanded = signal<boolean>(false);
  public readonly isManualCodeEditing = signal<boolean>(false);
  public readonly selectedDiagnostic = signal<TranspilerDiagnostic | null>(null);
  public readonly showCompatibilityPackModal = signal<boolean>(false);

  // Structural Impact & Modals
  public readonly showImpactModal = signal<boolean>(false);
  public readonly impactModalObject = signal<ObjectMappingContract | null>(null);
  public readonly pendingNavigation = signal<PendingNavigationAction | null>(null);
  public readonly pendingRevertObject = signal<ObjectMappingContract | null>(null);
  public readonly pendingRevertCodeObject = signal<TranspilerObjectContract | null>(null);

  // =========================================================================
  // APPLIED STATE (Committed in UI Frontend Store)
  // =========================================================================
  public readonly objects = signal<ObjectMappingContract[]>([]);
  public readonly namespaces = signal<NamespaceRoutingRule[]>([]);
  public readonly codeObjects = signal<TranspilerObjectContract[]>([]);
  public readonly compatibilityHelpers = signal<CompatibilityHelperRef[]>([]);

  public readonly privacyItems = signal<PrivacyItemContract[]>([]);
  public readonly cleansingItems = signal<CleansingItemContract[]>([]);
  public readonly filterItems = signal<FilterItemContract[]>([]);
  public readonly deduplicationItems = signal<DeduplicationItemContract[]>([]);
  public readonly qualityItems = signal<QualityItemContract[]>([]);

  public readonly privacyOptions = signal<CapabilityOptionRef[]>([]);
  public readonly cleansingOptions = signal<CapabilityOptionRef[]>([]);
  public readonly survivorPolicyOptions = signal<CapabilityOptionRef[]>([]);

  // =========================================================================
  // ACTIVE DRAFTS (Uncommitted Working States)
  // =========================================================================
  public readonly namespaceDraft = signal<NamespaceRoutingRule | null>(null);
  public readonly objectDraft = signal<ObjectMappingContract | null>(null);
  public readonly fieldDraft = signal<ColumnMappingContract | null>(null);
  public readonly transpilerCodeDraft = signal<string | null>(null);

  public readonly privacyDraft = signal<PrivacyItemContract | null>(null);
  public readonly cleansingDraft = signal<CleansingItemContract | null>(null);
  public readonly filterDraft = signal<FilterItemContract | null>(null);
  public readonly dedupDraft = signal<DeduplicationItemContract | null>(null);
  public readonly qualityDraft = signal<QualityItemContract | null>(null);

  // =========================================================================
  // COMPUTED ENTITIES & SELECTIONS
  // =========================================================================
  public readonly selectedNamespace = computed(() => {
    const name = this.selectedNamespaceName();
    const list = this.namespaces();
    if (!name) return list[0] || null;
    return list.find(n => n.sourceNamespace === name) || list[0] || null;
  });

  public readonly selectedObject = computed(() => {
    const id = this.selectedObjectId();
    const list = this.objects();
    if (!id) return list[0] || null;
    return list.find(o => o.id === id) || list[0] || null;
  });

  public readonly selectedCodeObject = computed(() => {
    const id = this.selectedCodeObjectId();
    const list = this.codeObjects();
    if (!id) return list[0] || null;
    return list.find(c => c.id === id) || list[0] || null;
  });

  // Mode Applicability
  public readonly isTranspilerApplicable = computed(() => {
    const draft = this.ms.wizardDraft();
    const isDataOnly = draft.mode === 'M7_DATA_ONLY';
    const target = draft.targetProvider;
    const isNonProceduralTarget = target === 'Apache Kafka' || target === 'Amazon S3' || target === 'Apache HDFS';
    return !isDataOnly && !isNonProceduralTarget && this.codeObjects().length > 0;
  });

  public readonly transpilerDisabledReason = computed(() => {
    const draft = this.ms.wizardDraft();
    if (draft.mode === 'M7_DATA_ONLY') {
      return 'Transpiler is not applicable for Data Only migration mode.';
    }
    const target = draft.targetProvider;
    if (target === 'Apache Kafka' || target === 'Amazon S3' || target === 'Apache HDFS') {
      return `Target ${target} does not host procedural schema code.`;
    }
    if (this.codeObjects().length === 0) {
      return 'No procedural or code objects were selected in Step 4 scope.';
    }
    return null;
  });

  // =========================================================================
  // DIRTY STATE TRACKING
  // =========================================================================
  public readonly isNamespaceDirty = computed(() => {
    const draft = this.namespaceDraft();
    const current = this.selectedNamespace();
    if (!draft || !current) return false;
    return (
      draft.currentTargetNamespace !== current.currentTargetNamespace ||
      draft.prefix !== current.prefix ||
      draft.suffix !== current.suffix ||
      draft.advancedPattern !== current.advancedPattern ||
      draft.advancedReplacement !== current.advancedReplacement
    );
  });

  public readonly isObjectDirty = computed(() => {
    const draft = this.objectDraft();
    const current = this.selectedObject();
    if (!draft || !current) return false;
    return (
      draft.currentTargetNamespace !== current.currentTargetNamespace ||
      draft.currentTargetName !== current.currentTargetName ||
      draft.isIncluded !== current.isIncluded ||
      draft.rowFilterMode !== current.rowFilterMode ||
      draft.rowFilterPredicate !== current.rowFilterPredicate
    );
  });

  public readonly isFieldDirty = computed(() => {
    const draft = this.fieldDraft();
    if (!draft) return false;
    const currentObj = this.selectedObject();
    if (!currentObj) return false;
    const original = currentObj.columns.find(c => c.id === draft.id);
    if (!original) return false;
    return (
      draft.currentTargetField !== original.currentTargetField ||
      draft.currentTargetType !== original.currentTargetType ||
      draft.currentLength !== original.currentLength ||
      draft.currentPrecision !== original.currentPrecision ||
      draft.currentScale !== original.currentScale ||
      draft.currentDefaultExpression !== original.currentDefaultExpression ||
      draft.isIncluded !== original.isIncluded ||
      draft.privacyOptionId !== original.privacyOptionId ||
      draft.privacyParam !== original.privacyParam ||
      draft.cleansingOptionId !== original.cleansingOptionId ||
      draft.operatorReason !== original.operatorReason
    );
  });

  public readonly isTranspilerDirty = computed(() => {
    const draft = this.transpilerCodeDraft();
    const current = this.selectedCodeObject();
    if (draft === null || !current) return false;
    return draft !== current.currentTargetCode;
  });

  public readonly isControlsDirty = computed(() => {
    return (
      this.privacyDraft() !== null ||
      this.cleansingDraft() !== null ||
      this.filterDraft() !== null ||
      this.dedupDraft() !== null ||
      this.qualityDraft() !== null
    );
  });

  public readonly hasAnyUnsavedDraft = computed(() => {
    return (
      this.isNamespaceDirty() ||
      this.isObjectDirty() ||
      this.isFieldDirty() ||
      this.isTranspilerDirty() ||
      this.isControlsDirty()
    );
  });

  // =========================================================================
  // SUMMARY METRICS & ATTENTION QUEUE COUNTS
  // =========================================================================
  public readonly metrics = computed<Step5SummaryMetrics>(() => {
    const objs = this.objects();
    const codes = this.codeObjects();
    const priv = this.privacyItems();
    const cln = this.cleansingItems();
    const flt = this.filterItems();
    const ddp = this.deduplicationItems();
    const qlt = this.qualityItems();

    let govCount = 0;
    for (const o of objs) {
      if (o.structuralImpact?.requiresGovernanceWaiver || o.readiness === 'WAIVER_REQUIRED') {
        govCount++;
      }
    }

    return {
      totalObjects: objs.length,
      autoMappedCount: objs.filter(o => o.status === 'AUTO_MAPPED').length,
      modifiedCount: objs.filter(o => o.status === 'MODIFIED' || o.isModified).length,
      needsReviewCount: objs.filter(o => o.status === 'NEEDS_REVIEW').length,
      blockedCount: objs.filter(o => o.status === 'BLOCKED' || o.readiness === 'BLOCKED' || (o.issues && o.issues.some(i => i.severity === 'BLOCKED'))).length,
      governanceRequiredCount: govCount,
      totalCodeObjects: codes.length,
      codeConvertedCount: codes.filter(c => c.status === 'CONVERTED').length,
      codeModifiedCount: codes.filter(c => c.status === 'MODIFIED' || c.isModified).length,
      codeNeedsReviewCount: codes.filter(c => c.status === 'NEEDS_REVIEW').length,
      codeBlockedCount: codes.filter(c => c.status === 'BLOCKED' || (c.diagnostics && c.diagnostics.some(d => d.severity === 'ERROR'))).length,
      totalPrivacyCount: priv.length,
      totalCleansingCount: cln.length,
      totalFilterCount: flt.length,
      totalDedupCount: ddp.length,
      totalQualityCount: qlt.length
    };
  });

  // UI Workflow Readiness Gate (Step 5 UI Readiness Seam for P7.D)
  public readonly isUiWorkflowReady = computed(() => {
    const m = this.metrics();
    const hasScope = m.totalObjects > 0;
    const hasNoBlockers = m.blockedCount === 0 && m.codeBlockedCount === 0;
    return hasScope && hasNoBlockers;
  });

  // Filtered Objects for Search & Status
  public readonly filteredObjects = computed(() => {
    const list = this.objects();
    const q = this.searchQuery().trim().toLowerCase();
    const filter = this.statusFilter();

    return list.filter(obj => {
      if (filter !== 'ALL' && obj.status !== filter) return false;

      if (!q) return true;
      const matchName = obj.sourceName.toLowerCase().includes(q) || obj.currentTargetName.toLowerCase().includes(q);
      const matchNamespace = obj.sourceNamespace.toLowerCase().includes(q) || obj.currentTargetNamespace.toLowerCase().includes(q);
      const matchCols = obj.columns.some(c => c.sourceField.toLowerCase().includes(q) || c.currentTargetField.toLowerCase().includes(q));
      return matchName || matchNamespace || matchCols;
    });
  });

  public readonly blockedObjects = computed(() => this.filteredObjects().filter(o => o.status === 'BLOCKED' || o.readiness === 'BLOCKED' || (o.issues && o.issues.some(i => i.severity === 'BLOCKED'))));
  public readonly needsReviewObjects = computed(() => this.filteredObjects().filter(o => o.status === 'NEEDS_REVIEW'));
  public readonly modifiedObjects = computed(() => this.filteredObjects().filter(o => o.status === 'MODIFIED'));
  public readonly autoMappedObjects = computed(() => this.filteredObjects().filter(o => o.status === 'AUTO_MAPPED'));

  constructor(ms?: MigrationUiService, adapter?: Step5MappingAdapterService) {
    try {
      this.ms = ms || inject(MigrationUiService);
    } catch {
      this.ms = ms || new MigrationUiService();
    }
    try {
      this.adapter = adapter || inject(Step5MappingAdapterService);
    } catch {
      this.adapter = adapter || new Step5MappingAdapterService();
    }
    this.initializeFromDraft();

    try {
      effect(() => {
        this.syncDraftReadiness();
      }, { allowSignalWrites: true });
    } catch {
      // In isolated non-injection testing environments
    }
  }

  public syncDraftReadiness(): void {
    const ready = this.isUiWorkflowReady();
    const m = this.metrics();
    this.ms.updateDraft({
      hasStep5Blockers: !ready,
      step5BlockerCount: m.blockedCount + m.codeBlockedCount,
      step5GovernanceCount: m.governanceRequiredCount
    });
  }

  public initializeFromDraft(): void {
    const draft = this.ms.wizardDraft();
    const packet = this.adapter.getProposedMappingPacket(
      draft.sourceProvider,
      draft.targetProvider,
      draft.mode,
      draft.selectedTopologyNodes
    );
    this.loadPacket(packet);
  }

  public loadPacket(packet: Step5MappingPacket): void {
    this.objects.set(packet.objects);
    this.namespaces.set(packet.namespaces);
    this.codeObjects.set(packet.codeObjects);
    this.compatibilityHelpers.set(packet.compatibilityHelpers);
    this.privacyItems.set(packet.privacyItems);
    this.cleansingItems.set(packet.cleansingItems);
    this.filterItems.set(packet.filterItems);
    this.deduplicationItems.set(packet.deduplicationItems);
    this.qualityItems.set(packet.qualityItems);
    this.privacyOptions.set(packet.privacyOptions);
    this.cleansingOptions.set(packet.cleansingOptions);
    this.survivorPolicyOptions.set(packet.survivorPolicyOptions);

    if (packet.namespaces.length > 0 && !this.selectedNamespaceName()) {
      this.selectNamespace(packet.namespaces[0].sourceNamespace);
    }
    if (packet.objects.length > 0 && !this.selectedObjectId()) {
      this.selectObject(packet.objects[0].id);
    }
    if (packet.codeObjects.length > 0 && !this.selectedCodeObjectId()) {
      this.selectCodeObject(packet.codeObjects[0].id);
    }

    this.checkLocalDraftConflicts();
    this.syncDraftReadiness();
  }

  // =========================================================================
  // SAFE NAVIGATION WITH UNSAVED CHANGE PROTECTION
  // =========================================================================

  public navigateWithGuard(action: () => void, description: string = 'You have unapplied draft changes.'): void {
    if (this.hasAnyUnsavedDraft()) {
      this.pendingNavigation.set({
        title: 'Unsaved Changes',
        description: `${description} Applying commits your changes into this session, or you may discard them.`,
        proceed: action
      });
    } else {
      action();
    }
  }

  public discardPendingNavigation(): void {
    this.resetAllDrafts();
    const pending = this.pendingNavigation();
    this.pendingNavigation.set(null);
    if (pending) {
      pending.proceed();
    }
  }

  public applyAndProceedPendingNavigation(): void {
    this.applyAllActiveDrafts();
    const pending = this.pendingNavigation();
    this.pendingNavigation.set(null);
    if (pending) {
      pending.proceed();
    }
  }

  public cancelPendingNavigation(): void {
    this.pendingNavigation.set(null);
  }

  public resetAllDrafts(): void {
    this.namespaceDraft.set(null);
    this.objectDraft.set(null);
    this.fieldDraft.set(null);
    this.transpilerCodeDraft.set(null);
    this.privacyDraft.set(null);
    this.cleansingDraft.set(null);
    this.filterDraft.set(null);
    this.dedupDraft.set(null);
    this.qualityDraft.set(null);
    this.isManualCodeEditing.set(false);
  }

  public applyAllActiveDrafts(): void {
    if (this.isNamespaceDirty()) this.applyNamespaceDraft();
    if (this.isObjectDirty()) this.applyObjectDraft();
    if (this.isFieldDirty()) this.applyFieldDraft();
    if (this.isTranspilerDirty()) this.applyTranspilerCodeDraft();
    if (this.privacyDraft()) this.applyPrivacyDraft();
    if (this.cleansingDraft()) this.applyCleansingDraft();
    if (this.filterDraft()) this.applyFilterDraft();
    if (this.dedupDraft()) this.applyDedupDraft();
    if (this.qualityDraft()) this.applyQualityDraft();
  }

  // =========================================================================
  // NAVIGATION ROUTING METHODS
  // =========================================================================

  public setWorkspace(tab: Step5WorkspaceTab): void {
    this.navigateWithGuard(() => {
      this.activeWorkspace.set(tab);
    }, 'Switching workspaces');
  }

  public setSubWorkspace(sub: MappingSubWorkspace): void {
    this.navigateWithGuard(() => {
      this.activeSubWorkspace.set(sub);
    }, 'Navigating within Mapping Studio');
  }

  public setWorkMode(mode: 'REVIEW' | 'MAP'): void {
    this.navigateWithGuard(() => {
      if (mode === 'REVIEW') {
        this.activeSubWorkspace.set('OVERVIEW');
      } else {
        this.activeSubWorkspace.set('FIELDS');
      }
    });
  }

  public setControlsCategory(cat: DataControlCategory): void {
    this.navigateWithGuard(() => {
      this.activeControlsCategory.set(cat);
    }, 'Switching Data Control categories');
  }

  public setStatusFilter(filter: MappingStatusBucket): void {
    this.statusFilter.set(filter);
  }

  public setSearchQuery(q: string): void {
    this.searchQuery.set(q);
  }

  public selectNamespace(name: string): void {
    this.selectedNamespaceName.set(name);
    const ns = this.namespaces().find(n => n.sourceNamespace === name);
    if (ns) {
      this.namespaceDraft.set({ ...ns });
    }
  }

  public selectObject(id: string): void {
    this.selectedObjectId.set(id);
    this.activeFieldDetailId.set(null);
    const obj = this.objects().find(o => o.id === id);
    if (obj) {
      this.objectDraft.set(JSON.parse(JSON.stringify(obj)));
    }
  }

  public selectCodeObject(id: string): void {
    this.selectedCodeObjectId.set(id);
    this.isManualCodeEditing.set(false);
    this.transpilerCodeDraft.set(null);
  }

  public toggleFieldDetail(fieldId: string): void {
    if (this.activeFieldDetailId() === fieldId) {
      this.activeFieldDetailId.set(null);
      this.fieldDraft.set(null);
    } else {
      this.activeFieldDetailId.set(fieldId);
      const curObj = this.selectedObject();
      if (curObj) {
        const col = curObj.columns.find(c => c.id === fieldId);
        if (col) {
          this.fieldDraft.set({ ...col });
        }
      }
    }
  }

  /**
   * Patches the active field draft with partial changes.
   * MUST be used instead of direct property mutation so that
   * isFieldDirty (a computed signal) re-evaluates correctly.
   */
  public patchFieldDraft(patch: Partial<import('../../modules/migration/create/steps/step5-mapping.models').ColumnMappingContract>): void {
    this.fieldDraft.update(d => d ? { ...d, ...patch } : d);
  }

  // One-click routing from Overview Attention Queue
  public routeToStructure(namespaceName?: string): void {
    this.navigateWithGuard(() => {
      this.activeWorkspace.set('MAPPING');
      this.activeSubWorkspace.set('STRUCTURE');
      if (namespaceName) {
        this.selectNamespace(namespaceName);
      }
    });
  }

  public routeToFields(objectId?: string, fieldId?: string): void {
    this.navigateWithGuard(() => {
      this.activeWorkspace.set('MAPPING');
      this.activeSubWorkspace.set('FIELDS');
      if (objectId) {
        this.selectObject(objectId);
      }
      if (fieldId) {
        this.toggleFieldDetail(fieldId);
      }
    });
  }

  public routeToMapObject(objectId: string, fieldId?: string): void {
    this.routeToFields(objectId, fieldId);
  }

  public routeToControls(category: DataControlCategory): void {
    this.navigateWithGuard(() => {
      this.activeWorkspace.set('MAPPING');
      this.activeSubWorkspace.set('CONTROLS');
      this.activeControlsCategory.set(category);
    });
  }

  public routeToTranspiler(codeObjectId?: string): void {
    this.navigateWithGuard(() => {
      this.activeWorkspace.set('TRANSPILER');
      if (codeObjectId) {
        this.selectCodeObject(codeObjectId);
      }
    });
  }

  public routeToTranspilerObject(codeObjectId: string): void {
    this.routeToTranspiler(codeObjectId);
  }

  // =========================================================================
  // DRAFT CONFLICT GUARD (Immediate UI collision detection)
  // =========================================================================

  public checkLocalDraftConflicts(): void {
    const list = this.objects();
    const targetMap = new Map<string, string[]>();

    for (const obj of list) {
      const targetKey = `${obj.currentTargetNamespace.trim().toLowerCase()}.${obj.currentTargetName.trim().toLowerCase()}`;
      if (!targetMap.has(targetKey)) {
        targetMap.set(targetKey, []);
      }
      targetMap.get(targetKey)!.push(obj.id);
    }

    const updatedList = list.map(obj => {
      const targetKey = `${obj.currentTargetNamespace.trim().toLowerCase()}.${obj.currentTargetName.trim().toLowerCase()}`;
      const conflicts = targetMap.get(targetKey) || [];
      const hasConflict = conflicts.length > 1;

      const issuesWithoutCollision = obj.issues.filter(i => i.code !== 'TARGET_NAMING_COLLISION');

      if (hasConflict) {
        return {
          ...obj,
          status: 'BLOCKED' as const,
          readiness: 'BLOCKED' as const,
          uiWorkState: 'BLOCKED' as const,
          issues: [
            ...issuesWithoutCollision,
            {
              id: `collision-${obj.id}`,
              severity: 'BLOCKED' as const,
              code: 'TARGET_NAMING_COLLISION',
              title: 'Target Name Collision',
              reason: `Target object "${targetKey}" conflicts with another mapped object.`,
              recommendation: 'Specify a distinct target object name or target namespace.',
              targetObject: targetKey
            }
          ]
        };
      } else {
        const wasBlockedSolelyByCollision = (obj.status === 'BLOCKED' || obj.readiness === 'BLOCKED') && obj.issues.some(i => i.code === 'TARGET_NAMING_COLLISION') && issuesWithoutCollision.length === 0;
        return {
          ...obj,
          status: wasBlockedSolelyByCollision ? (obj.isModified ? 'MODIFIED' : 'AUTO_MAPPED') : obj.status,
          readiness: wasBlockedSolelyByCollision ? 'READY' : obj.readiness,
          uiWorkState: wasBlockedSolelyByCollision ? (obj.isModified ? 'MODIFIED' : 'AUTOMATIC') : obj.uiWorkState,
          issues: issuesWithoutCollision
        };
      }
    });

    this.objects.set(updatedList);
    this.syncDraftReadiness();
  }

  // =========================================================================
  // OBJECT & COLUMN DIRECT UPDATE METHODS (TEST & STORE INTERFACE)
  // =========================================================================

  public updateTargetNamespace(objectId: string, targetNamespace: string): void {
    this.objects.update(list =>
      list.map(obj => {
        if (obj.id === objectId) {
          return {
            ...obj,
            currentTargetNamespace: targetNamespace,
            isModified: true,
            status: 'MODIFIED',
            uiWorkState: 'MODIFIED'
          };
        }
        return obj;
      })
    );
    this.checkLocalDraftConflicts();
  }

  public updateTargetName(objectId: string, targetName: string): void {
    this.objects.update(list =>
      list.map(obj => {
        if (obj.id === objectId) {
          return {
            ...obj,
            currentTargetName: targetName,
            isModified: true,
            status: 'MODIFIED',
            uiWorkState: 'MODIFIED'
          };
        }
        return obj;
      })
    );
    this.checkLocalDraftConflicts();
  }

  public updateTargetObjectName(objectId: string, targetName: string): void {
    this.updateTargetName(objectId, targetName);
  }

  public toggleObjectInclusion(objectId: string): void {
    this.objects.update(list =>
      list.map(obj => {
        if (obj.id === objectId) {
          return {
            ...obj,
            isIncluded: !obj.isIncluded,
            isModified: true,
            status: 'MODIFIED',
            uiWorkState: 'MODIFIED'
          };
        }
        return obj;
      })
    );
  }

  public setRowFilter(objectId: string, mode: 'ALL' | 'CUSTOM', predicate?: string): void {
    this.updateRowFilter(objectId, mode, predicate);
  }

  public updateRowFilter(objectId: string, mode: 'ALL' | 'CUSTOM', predicate?: string): void {
    this.objects.update(list =>
      list.map(obj => {
        if (obj.id === objectId) {
          return {
            ...obj,
            rowFilterMode: mode,
            rowFilterPredicate: predicate,
            isModified: true,
            status: 'MODIFIED',
            uiWorkState: 'MODIFIED'
          };
        }
        return obj;
      })
    );
  }

  public updateDeduplication(objectId: string, config: Partial<DeduplicationConfig>): void {
    this.objects.update(list =>
      list.map(obj => {
        if (obj.id === objectId) {
          return {
            ...obj,
            deduplication: {
              ...obj.deduplication,
              ...config
            },
            isModified: true,
            status: 'MODIFIED',
            uiWorkState: 'MODIFIED'
          };
        }
        return obj;
      })
    );
  }

  public updateTargetFieldName(objectId: string, colId: string, newName: string): void {
    this.objects.update(list =>
      list.map(obj => {
        if (obj.id === objectId) {
          return {
            ...obj,
            isModified: true,
            columns: obj.columns.map(c => {
              if (c.id === colId) {
                return {
                  ...c,
                  currentTargetField: newName,
                  isModified: true,
                  status: 'MODIFIED',
                  uiWorkState: 'MODIFIED'
                };
              }
              return c;
            })
          };
        }
        return obj;
      })
    );
  }

  public updateTargetFieldType(
    objectId: string,
    colId: string,
    targetType: string,
    params?: { length?: number; precision?: number; scale?: number }
  ): void {
    this.objects.update(list =>
      list.map(obj => {
        if (obj.id === objectId) {
          return {
            ...obj,
            isModified: true,
            columns: obj.columns.map(c => {
              if (c.id === colId) {
                return {
                  ...c,
                  currentTargetType: targetType,
                  currentLength: params?.length ?? c.currentLength,
                  currentPrecision: params?.precision ?? c.currentPrecision,
                  currentScale: params?.scale ?? c.currentScale,
                  length: params?.length ?? c.length,
                  precision: params?.precision ?? c.precision,
                  scale: params?.scale ?? c.scale,
                  isModified: true,
                  status: 'MODIFIED',
                  uiWorkState: 'MODIFIED'
                };
              }
              return c;
            })
          };
        }
        return obj;
      })
    );
  }

  public updateDefaultExpression(objectId: string, colId: string, expr: string): void {
    this.objects.update(list =>
      list.map(obj => {
        if (obj.id === objectId) {
          return {
            ...obj,
            isModified: true,
            columns: obj.columns.map(c => {
              if (c.id === colId) {
                return {
                  ...c,
                  currentDefaultExpression: expr,
                  isDefaultExpressionOverridden: true,
                  isModified: true,
                  status: 'MODIFIED',
                  uiWorkState: 'MODIFIED'
                };
              }
              return c;
            })
          };
        }
        return obj;
      })
    );
  }

  public updatePrivacyControl(objectId: string, colId: string, optionId: string, param?: string): void {
    this.objects.update(list =>
      list.map(obj => {
        if (obj.id === objectId) {
          return {
            ...obj,
            isModified: true,
            columns: obj.columns.map(c => {
              if (c.id === colId) {
                return {
                  ...c,
                  privacyOptionId: optionId,
                  privacyParam: param,
                  isModified: true,
                  status: 'MODIFIED',
                  uiWorkState: 'MODIFIED'
                };
              }
              return c;
            })
          };
        }
        return obj;
      })
    );
  }

  public updateCleansingControl(objectId: string, colId: string, optionId: string): void {
    this.objects.update(list =>
      list.map(obj => {
        if (obj.id === objectId) {
          return {
            ...obj,
            isModified: true,
            columns: obj.columns.map(c => {
              if (c.id === colId) {
                return {
                  ...c,
                  cleansingOptionId: optionId,
                  isModified: true,
                  status: 'MODIFIED',
                  uiWorkState: 'MODIFIED'
                };
              }
              return c;
            })
          };
        }
        return obj;
      })
    );
  }

  public toggleColumnInclusion(objectId: string, colId: string): void {
    this.objects.update(list =>
      list.map(obj => {
        if (obj.id === objectId) {
          return {
            ...obj,
            isModified: true,
            columns: obj.columns.map(c => {
              if (c.id === colId) {
                return {
                  ...c,
                  isIncluded: !c.isIncluded,
                  isModified: true,
                  status: 'MODIFIED',
                  uiWorkState: 'MODIFIED'
                };
              }
              return c;
            })
          };
        }
        return obj;
      })
    );
  }

  public updateTargetCode(codeId: string, code: string): void {
    this.codeObjects.update(list =>
      list.map(c => {
        if (c.id === codeId) {
          return {
            ...c,
            currentTargetCode: code,
            isModified: true,
            status: 'MODIFIED'
          };
        }
        return c;
      })
    );
  }

  // =========================================================================
  // APPLY ACTIONS (APPLY BUTTON LAW - FUNCTIONAL FRONTEND COMMIT)
  // =========================================================================

  public applyNamespaceDraft(): void {
    const draft = this.namespaceDraft();
    if (!draft) return;

    this.namespaces.update(list =>
      list.map(ns => {
        if (ns.sourceNamespace === draft.sourceNamespace) {
          return {
            ...draft,
            origin: 'MODIFIED',
            isModified: true
          };
        }
        return ns;
      })
    );
    this.checkLocalDraftConflicts();
  }

  public revertNamespaceToProposal(name: string): void {
    this.namespaces.update(list =>
      list.map(ns => {
        if (ns.sourceNamespace === name) {
          return {
            ...ns,
            currentTargetNamespace: ns.originalProposal.targetNamespace,
            prefix: ns.originalProposal.prefix,
            suffix: ns.originalProposal.suffix,
            advancedPattern: ns.originalProposal.advancedPattern || '',
            advancedReplacement: ns.originalProposal.advancedReplacement || '',
            origin: 'AUTOMATIC',
            isModified: false
          };
        }
        return ns;
      })
    );
    const updated = this.namespaces().find(n => n.sourceNamespace === name);
    if (updated) {
      this.namespaceDraft.set({ ...updated });
    }
    this.checkLocalDraftConflicts();
  }

  public applyObjectDraft(): void {
    const draft = this.objectDraft();
    if (!draft) return;

    this.objects.update(list =>
      list.map(obj => {
        if (obj.id === draft.id) {
          return {
            ...draft,
            uiWorkState: 'MODIFIED',
            status: 'MODIFIED',
            isModified: true
          };
        }
        return obj;
      })
    );
    this.checkLocalDraftConflicts();
  }

  public revertObjectToProposal(objectId: string): void {
    this.objects.update(list =>
      list.map(obj => {
        if (obj.id === objectId) {
          return {
            ...obj,
            currentTargetNamespace: obj.originalProposal.targetNamespace,
            currentTargetName: obj.originalProposal.targetName,
            isIncluded: obj.originalProposal.isIncluded,
            rowFilterMode: obj.originalProposal.rowFilterMode,
            rowFilterPredicate: obj.originalProposal.rowFilterPredicate,
            deduplication: { ...obj.originalProposal.deduplication },
            uiWorkState: 'AUTOMATIC',
            status: 'AUTO_MAPPED',
            isModified: false
          };
        }
        return obj;
      })
    );
    const updated = this.objects().find(o => o.id === objectId);
    if (updated) {
      this.objectDraft.set(JSON.parse(JSON.stringify(updated)));
    }
    this.checkLocalDraftConflicts();
  }

  public promptRevertObject(objectId: string): void {
    const obj = this.objects().find(o => o.id === objectId);
    if (obj) {
      this.pendingRevertObject.set(obj);
    }
  }

  public confirmRevertObject(): void {
    const obj = this.pendingRevertObject();
    if (obj) {
      this.revertObjectToProposal(obj.id);
      this.pendingRevertObject.set(null);
    }
  }

  public cancelRevertObject(): void {
    this.pendingRevertObject.set(null);
  }

  public applyFieldDraft(): void {
    const draft = this.fieldDraft();
    const curObj = this.selectedObject();
    if (!draft || !curObj) return;

    this.objects.update(list =>
      list.map(obj => {
        if (obj.id === curObj.id) {
          const updatedCols: ColumnMappingContract[] = obj.columns.map(col => {
            if (col.id === draft.id) {
              return {
                ...draft,
                length: draft.currentLength,
                precision: draft.currentPrecision,
                scale: draft.currentScale,
                uiWorkState: 'MODIFIED' as const,
                status: 'MODIFIED' as const,
                isModified: true
              };
            }
            return col;
          });
          return {
            ...obj,
            columns: updatedCols,
            isModified: true,
            uiWorkState: 'MODIFIED' as const,
            status: 'MODIFIED' as const
          };
        }
        return obj;
      })
    );
  }

  public revertFieldToProposal(fieldId: string): void {
    const curObj = this.selectedObject();
    if (!curObj) return;

    this.objects.update(list =>
      list.map(obj => {
        if (obj.id === curObj.id) {
          const updatedCols: ColumnMappingContract[] = obj.columns.map(col => {
            if (col.id === fieldId) {
              return {
                ...col,
                currentTargetField: col.originalProposal.targetField,
                currentTargetType: col.originalProposal.targetType,
                isIncluded: col.originalProposal.isIncluded,
                currentPrecision: col.originalProposal.precision,
                currentScale: col.originalProposal.scale,
                currentLength: col.originalProposal.length,
                length: col.originalProposal.length,
                precision: col.originalProposal.precision,
                scale: col.originalProposal.scale,
                currentDefaultExpression: col.originalProposal.defaultExpression,
                uiWorkState: 'AUTOMATIC' as const,
                status: 'AUTO_MAPPED' as const,
                isModified: false,
                operatorReason: undefined
              };
            }
            return col;
          });
          return {
            ...obj,
            columns: updatedCols
          };
        }
        return obj;
      })
    );

    const refreshedObj = this.objects().find(o => o.id === curObj.id);
    const refCol = refreshedObj?.columns.find(c => c.id === fieldId);
    if (refCol) {
      this.fieldDraft.set({ ...refCol });
    }
  }

  public applyTranspilerCodeDraft(): void {
    const code = this.transpilerCodeDraft();
    const curCodeObj = this.selectedCodeObject();
    if (code === null || !curCodeObj) return;

    this.codeObjects.update(list =>
      list.map(c => {
        if (c.id === curCodeObj.id) {
          return {
            ...c,
            currentTargetCode: code,
            status: 'MODIFIED',
            isModified: true
          };
        }
        return c;
      })
    );
    this.isManualCodeEditing.set(false);
  }

  public revertTranspilerCodeToProposal(codeObjectId: string): void {
    this.codeObjects.update(list =>
      list.map(c => {
        if (c.id === codeObjectId) {
          return {
            ...c,
            currentTargetCode: c.proposedTargetCode,
            status: 'CONVERTED',
            isModified: false
          };
        }
        return c;
      })
    );
    this.transpilerCodeDraft.set(null);
    this.isManualCodeEditing.set(false);
  }

  public promptRevertCodeObject(codeObjectId: string): void {
    const code = this.codeObjects().find(c => c.id === codeObjectId);
    if (code) {
      this.pendingRevertCodeObject.set(code);
    }
  }

  public confirmRevertCodeObject(): void {
    const code = this.pendingRevertCodeObject();
    if (code) {
      this.revertTranspilerCodeToProposal(code.id);
      this.pendingRevertCodeObject.set(null);
    }
  }

  public cancelRevertCodeObject(): void {
    this.pendingRevertCodeObject.set(null);
  }

  // =========================================================================
  // DATA CONTROLS APPLY ACTIONS
  // =========================================================================

  public applyPrivacyDraft(): void {
    const draft = this.privacyDraft();
    if (!draft) return;
    this.privacyItems.update(list =>
      list.map(p => (p.id === draft.id ? { ...draft, status: 'CONFIGURED', isModified: true } : p))
    );
    this.privacyDraft.set(null);
  }

  public applyCleansingDraft(): void {
    const draft = this.cleansingDraft();
    if (!draft) return;
    this.cleansingItems.update(list =>
      list.map(c => (c.id === draft.id ? { ...draft, status: 'CONFIGURED', isModified: true } : c))
    );
    this.cleansingDraft.set(null);
  }

  public applyFilterDraft(): void {
    const draft = this.filterDraft();
    if (!draft) return;
    this.filterItems.update(list =>
      list.map(f => (f.id === draft.id ? { ...draft, status: 'CONFIGURED', isModified: true } : f))
    );
    this.filterDraft.set(null);
  }

  public applyDedupDraft(): void {
    const draft = this.dedupDraft();
    if (!draft) return;
    this.deduplicationItems.update(list =>
      list.map(d => (d.id === draft.id ? { ...draft, status: 'CONFIGURED', isModified: true } : d))
    );
    this.dedupDraft.set(null);
  }

  public applyQualityDraft(): void {
    const draft = this.qualityDraft();
    if (!draft) return;
    this.qualityItems.update(list =>
      list.map(q => (q.id === draft.id ? { ...draft, status: 'CONFIGURED', isModified: true } : q))
    );
    this.qualityDraft.set(null);
  }

  // =========================================================================
  // BULK ACTIONS
  // =========================================================================

  public toggleSelectAllFields(checked: boolean): void {
    const curObj = this.selectedObject();
    if (!curObj) return;
    if (checked) {
      this.selectedFieldIds.set(new Set(curObj.columns.map(c => c.id)));
    } else {
      this.selectedFieldIds.set(new Set());
    }
  }

  public toggleFieldSelection(fieldId: string): void {
    const set = new Set(this.selectedFieldIds());
    if (set.has(fieldId)) {
      set.delete(fieldId);
    } else {
      set.add(fieldId);
    }
    this.selectedFieldIds.set(set);
  }

  public bulkIncludeFields(include: boolean): void {
    const set = this.selectedFieldIds();
    const curObj = this.selectedObject();
    if (!curObj || set.size === 0) return;

    this.objects.update(list =>
      list.map(obj => {
        if (obj.id === curObj.id) {
          return {
            ...obj,
            columns: obj.columns.map(c => {
              if (set.has(c.id)) {
                return { ...c, isIncluded: include, uiWorkState: 'MODIFIED', status: 'MODIFIED', isModified: true };
              }
              return c;
            })
          };
        }
        return obj;
      })
    );
    this.selectedFieldIds.set(new Set());
  }

  public addGeneratedTargetField(fieldName: string = 'created_epoch', fieldType: string = 'BIGINT'): void {
    const curObj = this.selectedObject();
    if (!curObj) return;

    const newCol: ColumnMappingContract = {
      id: `col-gen-${Date.now()}`,
      sourceField: '(GENERATED)',
      sourceType: 'SYSTEM_COMPUTED',
      proposedTargetField: fieldName,
      currentTargetField: fieldName,
      proposedTargetType: fieldType,
      currentTargetType: fieldType,
      isIncluded: true,
      isGenerated: true,
      uiWorkState: 'MODIFIED',
      conversionSafety: 'EXACT',
      readiness: 'READY',
      status: 'MODIFIED',
      isModified: true,
      defaultExpression: 'EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)',
      originalProposal: {
        targetField: fieldName,
        targetType: fieldType,
        isIncluded: true
      }
    };

    this.objects.update(list =>
      list.map(obj => {
        if (obj.id === curObj.id) {
          return {
            ...obj,
            columns: [...obj.columns, newCol],
            isModified: true
          };
        }
        return obj;
      })
    );
  }

  // Modal Triggers
  public openImpactModal(obj: ObjectMappingContract): void {
    this.impactModalObject.set(obj);
    this.showImpactModal.set(true);
  }

  public closeImpactModal(): void {
    this.showImpactModal.set(false);
    this.impactModalObject.set(null);
  }
}
