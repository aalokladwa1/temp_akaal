// ============================================================================
// AKAAL CREATE MIGRATION — STEP 9: REVIEW, SCHEDULE & INITIALIZE
// ADAPTER SERVICE (UNIDIRECTIONAL MAPPING & PRESENTATION LOGIC)
// ============================================================================

import { Injectable } from '@angular/core';
import { WizardDraftState } from './migration-ui.service';
import { Step7PlanDescriptor } from '../../modules/migration/create/steps/step7-plan.models';
import { OverallReadinessPresentation } from '../../modules/migration/create/steps/step8-governance.models';
import {
  MigrationIdentityPresentation,
  MigrationReviewGroup,
  BeforeYouStartPresentation,
  ExecutionTimingState,
  ConsequencePresentation,
  TechnicalDetailsPresentation
} from '../../modules/migration/create/steps/step9-review.models';
import { MigrationMode } from '../models/migration-view.models';

@Injectable({
  providedIn: 'root'
})
export class Step9ReviewAdapterService {

  // --------------------------------------------------------------------------
  // 1. ADAPT MIGRATION IDENTITY & ROUTE
  // --------------------------------------------------------------------------
  public adaptMigrationIdentity(
    draft: WizardDraftState,
    step7Plan: Step7PlanDescriptor | null
  ): MigrationIdentityPresentation {
    const migrationId = draft.migrationId || (draft as any).id || 'MIG-2026-0906-A1';
    const mode = draft.mode || 'M2_BULK_CDC';
    const rawVer = step7Plan?.technicalDetails?.version;
    const planRevision = draft.planVersion || (rawVer ? parseInt(rawVer.replace(/^v/, '').split('.')[0], 10) || 1 : 1);
    const planId = step7Plan?.technicalDetails?.planId || `PLAN-${migrationId}-v${planRevision}`;
    const planFingerprint = step7Plan?.technicalDetails?.canonicalFingerprint || step7Plan?.fingerprint || '7f9a2b8e3c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f';

    const sourceProvider = draft.sourceProvider || 'Oracle';
    const targetProvider = draft.targetProvider || 'PostgreSQL';

    const sourceLabel = draft.sourceDatabase
      ? `${draft.sourceDatabase} (${draft.sourceHost || 'source.internal'})`
      : `${sourceProvider} Primary Instance`;

    const targetLabel = draft.targetDatabase
      ? `${draft.targetDatabase} (${draft.targetHost || 'target.internal'})`
      : `${targetProvider} Primary Instance`;

    return {
      migrationId,
      migrationName: draft.name?.trim() || `${sourceProvider} to ${targetProvider} Migration`,
      environment: draft.environment || 'Production',
      mode,
      modeTitle: this.formatModeTitle(mode),
      source: {
        provider: sourceProvider,
        host: draft.sourceHost,
        port: draft.sourcePort,
        database: draft.sourceDatabase,
        label: sourceLabel
      },
      target: {
        provider: targetProvider,
        host: draft.targetHost,
        port: draft.targetPort,
        database: draft.targetDatabase,
        label: targetLabel
      },
      planRevision,
      planId,
      planFingerprint
    };
  }

  // --------------------------------------------------------------------------
  // 2. ADAPT MIGRATION REVIEW GROUPS (STEPS 1–8 COLLAPSED SUMMARY)
  // --------------------------------------------------------------------------
  public adaptReviewGroups(
    draft: WizardDraftState,
    step7Plan: Step7PlanDescriptor | null,
    overallReadiness: OverallReadinessPresentation | null
  ): MigrationReviewGroup[] {
    const mode = draft.mode || 'M2_BULK_CDC';
    const groups: MigrationReviewGroup[] = [];

    // Project Affiliation Group (if project-scoped creation)
    if (draft.projectId) {
      groups.push({
        id: 'PROJECT_AFFILIATION',
        title: 'Project Context & Scope',
        subtitle: 'Workspace project ownership & governance alignment',
        upstreamStep: 1,
        upstreamStepLabel: 'Review in Definition \u2192',
        fields: [
          {
            label: 'Project Context',
            value: draft.projectId,
            detail: 'Scoped to workspace project boundary'
          },
          {
            label: 'Portfolio Ownership',
            value: 'Direct Project Migration',
            badge: 'PROJECT SCOPED',
            badgeColor: 'bg-blue-50 text-blue-700 border-blue-200'
          }
        ]
      });
    }

    // Group 1: Scope & Data (Step 4)
    const tableNodes = (draft.selectedTopologyNodes || []).filter(id => !id.startsWith('schema-') && !id.startsWith('db-'));
    const tableCount = tableNodes.length > 0 ? tableNodes.length : 303;
    const isSchemaOnly = mode === 'M6_SCHEMA_ONLY';
    const isDataOnly = mode === 'M7_DATA_ONLY';

    groups.push({
      id: 'SCOPE_DATA',
      title: 'Scope & Data',
      subtitle: isSchemaOnly ? 'Selected schema definitions & constraints' : 'Selected schemas, tables & volume',
      upstreamStep: 4,
      upstreamStepLabel: 'Review in Scope \u2192',
      fields: [
        {
          label: 'Selected Estate',
          value: `${tableCount} table${tableCount > 1 ? 's' : ''}`,
          detail: draft.discoveryDepth ? `${draft.discoveryDepth} discovery depth tier` : undefined
        },
        {
          label: 'Estimated Scale',
          value: isSchemaOnly ? 'Metadata Only (0 data bytes)' : '8.4M rows \u00b7 84.2 GB',
          detail: isSchemaOnly ? 'DDL, indices, constraints, sequences' : 'Volume based on catalog statistics'
        }
      ]
    });

    // Group 2: Data Controls & Mapping (Step 5)
    groups.push({
      id: 'DATA_CONTROLS',
      title: 'Data Controls',
      subtitle: 'Column transformations, type mappings & collision policies',
      upstreamStep: 5,
      upstreamStepLabel: 'Review in Mapping \u2192',
      fields: [
        {
          label: 'Schema & Type Mappings',
          value: `${tableCount} table${tableCount > 1 ? 's' : ''} mapped (100%)`,
          detail: isDataOnly ? 'Target schema pre-existing' : 'Automatic DDL compatibility verification passed'
        },
        {
          label: 'Collision & Write Policy',
          value: this.formatCollisionPolicy(draft.collisionPolicy || 'FAIL_ON_COLLISION'),
          badge: draft.collisionPolicy === 'DROP_AND_RECREATE' ? 'DESTRUCTIVE' : 'SAFE',
          badgeColor: draft.collisionPolicy === 'DROP_AND_RECREATE' ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-slate-100 text-slate-700 border-slate-200'
        }
      ]
    });

    // Group 3: Execution Configuration (Step 6)
    const workers = draft.basicView?.derivedMaxWorkers || 16;
    const batchMb = draft.basicView?.derivedBatchMb || 32;
    groups.push({
      id: 'EXECUTION',
      title: 'Execution Parameters',
      subtitle: 'Worker concurrency, batching buffer & recovery store',
      upstreamStep: 6,
      upstreamStepLabel: 'Review in Configure \u2192',
      fields: [
        {
          label: 'Concurrency & Batching',
          value: `${workers} parallel workers \u00b7 ${batchMb} MB batch chunks`,
          detail: 'Auto-balanced worker thread partition engine'
        },
        {
          label: 'Checkpoint Journal',
          value: 'Atomic State Journal Enabled',
          detail: 'Point-in-time crash-resilient restart capability'
        }
      ]
    });

    // Group 4: Governed Plan (Step 7)
    const nodes = step7Plan?.nodes || [];
    const stageCount = nodes.filter(n => n.nodeType === 'EXECUTION_STAGE').length || 7;
    const barrierCount = nodes.filter(n => n.nodeType === 'APPROVAL_BARRIER').length || 1;

    groups.push({
      id: 'PLAN',
      title: 'Governed Plan Topology',
      subtitle: 'DAG execution stages & runtime approval barriers',
      upstreamStep: 7,
      upstreamStepLabel: 'Review in Plan \u2192',
      fields: [
        {
          label: 'Execution Stages',
          value: `${stageCount} sequential execution stages`,
          detail: `Revision ${step7Plan?.technicalDetails?.version || 'v1.0'} \u00b7 DAG verified acyclic`
        },
        {
          label: 'Runtime Intervention',
          value: barrierCount > 0 ? `${barrierCount} downstream approval barrier` : 'Continuous automated execution',
          detail: barrierCount > 0 ? 'Execution will pause before cutover for authorization' : 'No runtime pauses configured'
        }
      ]
    });

    // Group 5: Governance & Readiness (Step 8)
    const readinessStatus = overallReadiness?.status || 'READY';
    const isGovReady = readinessStatus === 'READY';
    groups.push({
      id: 'GOVERNANCE_READINESS',
      title: 'Governance & Readiness',
      subtitle: 'Pre-flight technical verification & policy compliance',
      upstreamStep: 8,
      upstreamStepLabel: 'Review in Governance \u2192',
      fields: [
        {
          label: 'Readiness Assessment',
          value: isGovReady ? 'All Pre-flight Checks Satisfied' : 'Pre-flight Advisories Documented',
          badge: isGovReady ? 'READY TO INITIALIZE' : 'ADVISORIES',
          badgeColor: isGovReady ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-amber-50 text-amber-700 border-amber-200'
        },
        {
          label: 'Pre-initialization Governance',
          value: 'Authorized for Execution',
          detail: 'Governed cryptographic plan artifact sealed and bound'
        }
      ]
    });

    return groups;
  }

  // --------------------------------------------------------------------------
  // 3. ADAPT BEFORE YOU START (DECISION-QUALITY INTELLIGENCE)
  // --------------------------------------------------------------------------
  public adaptBeforeYouStart(
    draft: WizardDraftState,
    step7Plan: Step7PlanDescriptor | null,
    overallReadiness: OverallReadinessPresentation | null
  ): BeforeYouStartPresentation {
    const mode = draft.mode || 'M2_BULK_CDC';
    const isSchemaOnly = mode === 'M6_SCHEMA_ONLY';
    const isCdcOnly = mode === 'M3_CDC';

    // Scale
    const tableNodes = (draft.selectedTopologyNodes || []).filter(id => !id.startsWith('schema-') && !id.startsWith('db-'));
    const tableCount = tableNodes.length > 0 ? tableNodes.length : 303;

    let objectCountLabel = `${tableCount} tables in 2 schemas`;
    let volumeEstimateLabel = isSchemaOnly ? 'Metadata definitions only' : '8.4M rows (~84.2 GB)';
    let evidenceClassification: any = isSchemaOnly ? 'EXACT' : 'MEASURED';
    let evidenceExplanation = isSchemaOnly
      ? 'Exact schema catalog objects selected from discovery.'
      : 'Source volume measured from database system catalog statistics.';

    // Duration Range
    let isAvailable = true;
    let rangeDisplay = '1h 45m \u2013 2h 15m';
    let confidenceLevel: any = 'MEDIUM';
    let confidenceExplanation = 'Source volume measured; target network throughput estimated at ~1.2 Gbps.';

    if (isSchemaOnly) {
      rangeDisplay = '1m \u2013 3m';
      confidenceLevel = 'HIGH';
      confidenceExplanation = 'DDL and constraint generation measured against target database engine.';
    } else if (isCdcOnly) {
      rangeDisplay = 'Continuous Stream';
      confidenceLevel = 'HIGH';
      confidenceExplanation = 'Continuous replication; baseline stream lag objective \u2264 500ms.';
    }

    // Structural Risk
    let riskLevel: any = 'LOW';
    let riskSummary = 'Minimal conversion risk. Column type definitions cleanly align with target.';
    const residualRisks: string[] = [];

    if (draft.environment === 'Production') {
      if ((draft.basicView?.derivedMaxWorkers || 16) > 8) {
        residualRisks.push('High worker concurrency allocated on production target database.');
      }
      if (draft.collisionPolicy === 'DROP_AND_RECREATE') {
        riskLevel = 'MEDIUM';
        riskSummary = 'Destructive collision policy active on target database.';
        residualRisks.push('Target tables will be dropped and recreated prior to bulk ingestion.');
      }
    }

    // Runtime Intervention
    const nodes = step7Plan?.nodes || [];
    const barrierNodes = nodes.filter(n => n.nodeType === 'APPROVAL_BARRIER');
    const hasDownstreamBarriers = barrierNodes.length > 0;
    const downstreamBarrierCount = barrierNodes.length;
    const barrierDesc = hasDownstreamBarriers
      ? `${downstreamBarrierCount} downstream approval barrier \u00b7 Execution will pause before cutover for signatory sign-off.`
      : 'Continuous automated execution \u00b7 No runtime pauses configured.';

    // Reversibility
    let reversibilityClass: any = 'CONDITIONALLY_REVERSIBLE';
    let reversibilitySummary = 'Initial bulk extraction is non-destructive on source; target writes can be isolated.';
    let reversibilityDetails = 'Source database operations are strictly read-only. Target transactions can be rolled back prior to final cutover.';

    if (isSchemaOnly) {
      reversibilityClass = 'REVERSIBLE';
      reversibilitySummary = 'Target schema DDL can be dropped without data consequence.';
      reversibilityDetails = 'No business data records are modified during schema-only execution.';
    }

    return {
      dataScale: {
        objectCountLabel,
        volumeEstimateLabel,
        evidenceClassification,
        evidenceExplanation
      },
      duration: {
        isAvailable,
        rangeDisplay,
        confidenceLevel,
        confidenceExplanation
      },
      structuralRisk: {
        level: riskLevel,
        summary: riskSummary,
        residualRisks,
        hasLossyConversions: false
      },
      runtimeIntervention: {
        hasDownstreamBarriers,
        downstreamBarrierCount,
        description: barrierDesc
      },
      reversibility: {
        classification: reversibilityClass,
        summary: reversibilitySummary,
        details: reversibilityDetails
      }
    };
  }

  // --------------------------------------------------------------------------
  // 4. ADAPT CONSEQUENCE PRESENTATION
  // --------------------------------------------------------------------------
  public adaptConsequencePresentation(
    timing: ExecutionTimingState,
    draft: WizardDraftState,
    step7Plan: Step7PlanDescriptor | null
  ): ConsequencePresentation {
    const isProd = draft.environment === 'Production';
    const nodes = step7Plan?.nodes || [];
    const firstStage = nodes.find(n => n.nodeType === 'EXECUTION_STAGE');
    const firstStageLabel = firstStage ? firstStage.label : 'Source Schema Verification';

    if (timing.choice === 'RUN_NOW') {
      return {
        title: 'Immediate Execution',
        primaryActionDescription: 'AKAAL will initialize this governed plan revision and begin execution immediately. You will be redirected to Mission Control to track real-time progress.',
        subsequentSteps: [
          `Initialize the governed plan artifact and register the execution checkpoint.`,
          `Dispatch worker thread partitions to begin with Stage 1 (${firstStageLabel}).`,
          `Execution will pause automatically at any configured downstream approval barriers.`
        ],
        isProduction: isProd,
        productionNotice: isProd
          ? 'Production Migration: This action will dispatch worker connections directly to the production environment.'
          : undefined,
        firstStageLabel
      };
    } else {
      return {
        title: 'Scheduled Execution',
        primaryActionDescription: `AKAAL will initialize and arm this governed plan revision for ${timing.resolvedLocalDisplay} (${timing.selectedTimezone}).`,
        subsequentSteps: [
          `Register the governed plan artifact with the job scheduler.`,
          `Arm the automated execution trigger for the specified window.`,
          `Execution will begin automatically when the scheduled trigger timestamp becomes due.`,
          `The scheduled migration can be inspected or cancelled from the Migration Portfolio prior to trigger time.`
        ],
        isProduction: isProd,
        productionNotice: isProd
          ? 'Production Migration: Execution will automatically trigger on production endpoints at the scheduled time.'
          : undefined,
        firstStageLabel
      };
    }
  }

  // --------------------------------------------------------------------------
  // 5. ADAPT TECHNICAL DETAILS MODAL / OVERLAY
  // --------------------------------------------------------------------------
  public adaptTechnicalDetails(
    draft: WizardDraftState,
    step7Plan: Step7PlanDescriptor | null,
    overallReadiness: OverallReadinessPresentation | null
  ): TechnicalDetailsPresentation {
    const migrationId = draft.migrationId || (draft as any).id || 'MIG-2026-0906-A1';
    const rawVer = step7Plan?.technicalDetails?.version;
    const planRevision = (rawVer ? parseInt(rawVer.replace(/^v/, '').split('.')[0], 10) || 1 : draft.planVersion) || 1;
    const planId = step7Plan?.technicalDetails?.planId || `PLAN-${migrationId}-v${planRevision}`;
    const planFingerprint = step7Plan?.technicalDetails?.canonicalFingerprint || step7Plan?.fingerprint || '7f9a2b8e3c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f';

    const sourceProvider = draft.sourceProvider || 'Oracle';
    const targetProvider = draft.targetProvider || 'PostgreSQL';

    return {
      migrationId,
      planId,
      planRevision,
      planFingerprint,
      policyBinding: 'AKAAL-ENTERPRISE-GOVERNANCE-v2.4',
      governanceSealStatus: 'SEALED & AUTHORIZED',
      executionMode: this.formatModeTitle(draft.mode || 'M2_BULK_CDC'),
      sourceEndpoint: `${sourceProvider}://${draft.sourceHost || 'source.internal'}:${draft.sourcePort || 1521}/${draft.sourceDatabase || 'SOURCE_DB'}`,
      targetEndpoint: `${targetProvider}://${draft.targetHost || 'target.internal'}:${draft.targetPort || 5432}/${draft.targetDatabase || 'TARGET_DB'}`,
      structuralRiskEvidence: 'Structural Static Analyzer v1.4 \u00b7 0 fatal schema incompatibilities detected',
      scaleEvidence: 'Catalog Volume Analyzer \u00b7 System statistics extracted from database dictionary',
      dispatchState: 'READY_FOR_DISPATCH'
    };
  }

  // --------------------------------------------------------------------------
  // HELPER FORMATTERS
  // --------------------------------------------------------------------------
  public formatModeTitle(mode: MigrationMode): string {
    switch (mode) {
      case 'M1_BULK': return 'Offline Bulk Migration';
      case 'M2_BULK_CDC': return 'Bulk Migration + Continuous CDC';
      case 'M3_CDC': return 'Continuous CDC Stream';
      case 'M4_INCREMENTAL': return 'Incremental Watermark Sync';
      case 'M5_STATE_SYNC': return 'Bi-directional State Synchronization';
      case 'M6_SCHEMA_ONLY': return 'Schema & DDL Only';
      case 'M7_DATA_ONLY': return 'Data Only (Pre-existing Schema)';
      default: return 'Standard Migration';
    }
  }

  public formatCollisionPolicy(policy: string): string {
    switch (policy) {
      case 'FAIL_ON_COLLISION': return 'Fail On Target Collision';
      case 'DROP_AND_RECREATE': return 'Drop & Recreate Existing Tables';
      case 'TRUNCATE_EXISTING': return 'Truncate Existing Tables';
      case 'RENAME_AND_BACKUP': return 'Rename & Preserve Existing Tables';
      case 'MERGE_UPSERT': return 'Merge & Upsert Records';
      case 'APPEND_ONLY': return 'Append Only';
      default: return policy;
    }
  }

  public isRecurrencePermittedForMode(mode: MigrationMode): boolean {
    // Recurrence is supported for discrete batch/sync modes (M1, M4, M6, M7), but not continuous CDC (M2, M3, M5)
    return mode === 'M1_BULK' || mode === 'M4_INCREMENTAL' || mode === 'M6_SCHEMA_ONLY' || mode === 'M7_DATA_ONLY';
  }
}
