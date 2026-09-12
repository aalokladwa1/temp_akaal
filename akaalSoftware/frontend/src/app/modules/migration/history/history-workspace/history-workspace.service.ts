import { Injectable, computed, signal } from '@angular/core';
import {
  HistoryWorkspaceTab,
  MigrationHistoryWorkspaceRecord,
  TimelineEventItem,
  TimelineCategory,
  TimelineSeverity,
  ExecutionRunDetail,
  ValidationRunRecord,
  AuditTrailEvent,
  PlanRevision
} from './history-workspace.models';
import { HISTORY_WORKSPACE_FIXTURES } from './history-workspace.fixtures';
import { HISTORY_FIXTURES } from '../history-home.fixtures';
import { HistoryMode, HistoryOutcome, ValidationReconciliationState } from '../history-home.models';

export type WorkspaceViewState = 'READY' | 'LOADING' | 'EMPTY' | 'ERROR' | 'UNAVAILABLE';

@Injectable({
  providedIn: 'root'
})
export class HistoryWorkspaceService {
  // Core Route & Identification State
  public readonly activeMigrationId = signal<string>('mig-fin-core-01');
  public readonly activeTab = signal<HistoryWorkspaceTab>('overview');
  public readonly viewState = signal<WorkspaceViewState>('READY');
  public readonly errorMessage = signal<string | null>(null);

  // Tab 3: Execution Selection
  public readonly selectedExecutionRunId = signal<string>('');

  // Tab 4: Plan Revision Diff Selection
  public readonly selectedDiffRevA = signal<number>(1);
  public readonly selectedDiffRevB = signal<number>(2);

  // Tab 6: Validation Run Selection
  public readonly selectedValidationRunId = signal<string>('');

  // Tab 2: Timeline Filters
  public readonly timelineSearch = signal<string>('');
  public readonly timelineCategory = signal<string>('ALL');
  public readonly timelineSeverity = signal<string>('ALL');

  // Tab 10: Audit Trail Filters & Modal
  public readonly auditSearch = signal<string>('');
  public readonly auditActor = signal<string>('ALL');
  public readonly auditAction = signal<string>('ALL');
  public readonly activeAuditInspection = signal<AuditTrailEvent | null>(null);

  // Active Record computation
  public readonly currentRecord = computed<MigrationHistoryWorkspaceRecord | null>(() => {
    const id = this.activeMigrationId();
    if (!id) return null;

    // Check direct workspace fixtures
    if (HISTORY_WORKSPACE_FIXTURES[id]) {
      return HISTORY_WORKSPACE_FIXTURES[id];
    }

    // Fallback: Generate full rich workspace record from home fixtures
    const homeRecord = HISTORY_FIXTURES.find(f => f.id === id || f.migrationId === id);
    if (homeRecord) {
      return this.generateWorkspaceRecordFromHome(homeRecord);
    }

    // Fallback default
    if (HISTORY_WORKSPACE_FIXTURES['mig-fin-core-01']) {
      return HISTORY_WORKSPACE_FIXTURES['mig-fin-core-01'];
    }

    return null;
  });

  // Selected Execution Run
  public readonly currentExecutionRun = computed<ExecutionRunDetail | null>(() => {
    const record = this.currentRecord();
    if (!record || !record.executionRuns || record.executionRuns.length === 0) {
      return null;
    }
    const selectedId = this.selectedExecutionRunId();
    if (selectedId) {
      const match = record.executionRuns.find(r => r.runId === selectedId);
      if (match) return match;
    }
    return record.executionRuns[0];
  });

  // Selected Validation Run
  public readonly currentValidationRun = computed<ValidationRunRecord | null>(() => {
    const record = this.currentRecord();
    if (!record || !record.validationRuns || record.validationRuns.length === 0) {
      return null;
    }
    const selectedId = this.selectedValidationRunId();
    if (selectedId) {
      const match = record.validationRuns.find(v => v.validationRunId === selectedId);
      if (match) return match;
    }
    return record.validationRuns[0];
  });

  // Filtered Timeline Events
  public readonly filteredTimelineEvents = computed<TimelineEventItem[]>(() => {
    const record = this.currentRecord();
    if (!record || !record.timeline) return [];

    const search = this.timelineSearch().toLowerCase().trim();
    const cat = this.timelineCategory();
    const sev = this.timelineSeverity();

    return record.timeline.filter(event => {
      if (cat !== 'ALL' && event.category !== cat) return false;
      if (sev !== 'ALL' && event.severity !== sev) return false;
      if (search) {
        const text = `${event.title} ${event.description} ${event.actor} ${event.category}`.toLowerCase();
        if (!text.includes(search)) return false;
      }
      return true;
    });
  });

  // Filtered Audit Trail Events
  public readonly filteredAuditEvents = computed<AuditTrailEvent[]>(() => {
    const record = this.currentRecord();
    if (!record || !record.auditTrail) return [];

    const search = this.auditSearch().toLowerCase().trim();
    const actor = this.auditActor();
    const action = this.auditAction();

    return record.auditTrail.filter(ev => {
      if (actor !== 'ALL' && ev.actorPrincipal !== actor && ev.actorRole !== actor) return false;
      if (action !== 'ALL' && ev.action !== action) return false;
      if (search) {
        const text = `${ev.actorPrincipal} ${ev.actorRole} ${ev.action} ${ev.resourceTarget} ${ev.outcome} ${ev.hashChainLinkSha256}`.toLowerCase();
        if (!text.includes(search)) return false;
      }
      return true;
    });
  });

  // Distinct Audit Actors & Actions for Filter Dropdowns
  public readonly auditDistinctActors = computed<string[]>(() => {
    const record = this.currentRecord();
    if (!record || !record.auditTrail) return [];
    const set = new Set<string>();
    record.auditTrail.forEach(a => set.add(a.actorPrincipal));
    return Array.from(set);
  });

  public readonly auditDistinctActions = computed<string[]>(() => {
    const record = this.currentRecord();
    if (!record || !record.auditTrail) return [];
    const set = new Set<string>();
    record.auditTrail.forEach(a => set.add(a.action));
    return Array.from(set);
  });

  // Public Methods
  public loadMigration(id: string): void {
    if (!id || id.trim() === '') {
      this.viewState.set('EMPTY');
      this.errorMessage.set('No migration identifier provided.');
      return;
    }

    this.viewState.set('LOADING');
    this.activeMigrationId.set(id.trim());

    // Check if record exists
    const rec = this.currentRecord();
    if (rec) {
      this.viewState.set('READY');
      this.errorMessage.set(null);
      // Reset run selections to defaults
      if (rec.executionRuns && rec.executionRuns.length > 0) {
        this.selectedExecutionRunId.set(rec.executionRuns[0].runId);
      }
      if (rec.validationRuns && rec.validationRuns.length > 0) {
        this.selectedValidationRunId.set(rec.validationRuns[0].validationRunId);
      }
    } else {
      this.viewState.set('ERROR');
      this.errorMessage.set(`Migration historical record '${id}' could not be located in the ledger.`);
    }
  }

  public setActiveTab(tab: HistoryWorkspaceTab): void {
    this.activeTab.set(tab);
  }

  public selectExecutionRun(runId: string): void {
    this.selectedExecutionRunId.set(runId);
  }

  public selectValidationRun(runId: string): void {
    this.selectedValidationRunId.set(runId);
  }

  public setTimelineFilters(category: string, severity: string, search: string): void {
    this.timelineCategory.set(category);
    this.timelineSeverity.set(severity);
    this.timelineSearch.set(search);
  }

  public resetTimelineFilters(): void {
    this.timelineCategory.set('ALL');
    this.timelineSeverity.set('ALL');
    this.timelineSearch.set('');
  }

  public setAuditFilters(actor: string, action: string, search: string): void {
    this.auditActor.set(actor);
    this.auditAction.set(action);
    this.auditSearch.set(search);
  }

  public resetAuditFilters(): void {
    this.auditActor.set('ALL');
    this.auditAction.set('ALL');
    this.auditSearch.set('');
  }

  public inspectAuditEvent(event: AuditTrailEvent | null): void {
    this.activeAuditInspection.set(event);
  }

  public setDiffRevisions(revA: number, revB: number): void {
    this.selectedDiffRevA.set(revA);
    this.selectedDiffRevB.set(revB);
  }

  public retry(): void {
    const id = this.activeMigrationId() || 'mig-fin-core-01';
    this.loadMigration(id);
  }

  // Smart Generator from HistoryHome item
  private generateWorkspaceRecordFromHome(homeItem: any): MigrationHistoryWorkspaceRecord {
    const isModeCutoverApplicable = ['M2_BULK_CDC', 'M3_CDC', 'M4_INCREMENTAL', 'M5_STATE_SYNC'].includes(homeItem.mode);
    const modeName = homeItem.mode || 'M1_BULK';
    const isValidationMode = modeName === 'M8_VALIDATION_ONLY';

    return {
      id: homeItem.id || homeItem.migrationId,
      migrationId: homeItem.migrationId || homeItem.id,
      migrationName: homeItem.migrationName,
      executionId: homeItem.executionId || `exec-${homeItem.id}-01`,
      projectId: homeItem.projectId || 'proj-core',
      projectName: homeItem.projectName || 'Enterprise Core Modernization',
      initiativeName: homeItem.initiativeName || 'Strategic Modernization Initiative',
      sourceProvider: homeItem.sourceProvider,
      sourceProviderCode: homeItem.sourceProviderCode || 'oracle',
      targetProvider: homeItem.targetProvider,
      targetProviderCode: homeItem.targetProviderCode || 'postgres',
      mode: homeItem.mode as HistoryMode,
      outcome: homeItem.outcome as HistoryOutcome,
      lifecycleState: homeItem.lifecycleState || 'COMPLETED',
      startedAt: homeItem.startedAt,
      completedAt: homeItem.completedAt,
      durationString: homeItem.durationString || '1h 24m 10s',
      totalRowsProcessed: homeItem.totalRowsProcessed || 1250000,
      throughputFormatted: homeItem.throughputFormatted || '42,100 rows/s',
      errorMessage: homeItem.errorMessage || null,
      operator: homeItem.operator || 'A. Ladwa (Lead DBA)',
      materialExceptions: homeItem.errorMessage ? [homeItem.errorMessage] : [],

      timeline: [
        {
          id: 'tl-gen-01',
          timestamp: homeItem.startedAt || '2026-09-08T01:00:00Z',
          title: 'Plan Initialized & Fingerprinted',
          description: `Execution compiled under mode ${modeName} with authoritative SHA-256 fingerprint.`,
          category: 'PLANNING',
          severity: 'INFO',
          actor: homeItem.operator || 'System Planner'
        },
        {
          id: 'tl-gen-02',
          timestamp: homeItem.startedAt || '2026-09-08T01:05:00Z',
          title: 'Governance Barrier Satisfied',
          description: 'Production execution authorized by maker-checker quorum.',
          category: 'GOVERNANCE',
          severity: 'SUCCESS',
          actor: 'Quorum Governance Engine'
        },
        {
          id: 'tl-gen-03',
          timestamp: homeItem.startedAt || '2026-09-08T01:10:00Z',
          title: 'Execution Stage Initialized',
          description: `Pipeline workers attached to ${homeItem.sourceProvider}.`,
          category: 'EXECUTION',
          severity: 'INFO',
          actor: 'Pipeline Engine'
        },
        {
          id: 'tl-gen-04',
          timestamp: homeItem.completedAt || '2026-09-08T02:30:00Z',
          title: homeItem.outcome === 'SUCCEEDED' ? 'Execution Completed' : 'Execution Halted',
          description: homeItem.errorMessage || `Successfully processed ${homeItem.totalRowsProcessed?.toLocaleString() || '1,250,000'} rows.`,
          category: 'EXECUTION',
          severity: homeItem.outcome === 'SUCCEEDED' ? 'SUCCESS' : 'ERROR',
          actor: 'Pipeline Engine'
        },
        {
          id: 'tl-gen-05',
          timestamp: homeItem.completedAt || '2026-09-08T02:35:00Z',
          title: 'Forensic Validation & Parity Sealed',
          description: `Validation verdict: ${homeItem.validationState || 'PASSED'}. Evidence sealed.`,
          category: 'VALIDATION',
          severity: homeItem.validationState === 'PASSED' ? 'SUCCESS' : 'INFO',
          actor: 'Validation Engine'
        }
      ],

      executionRuns: [
        {
          runId: `run-${homeItem.id}-01`,
          executionId: homeItem.executionId || `exec-${homeItem.id}-01`,
          runNumber: 1,
          outcome: homeItem.outcome as HistoryOutcome,
          startedAt: homeItem.startedAt || '2026-09-08T01:00:00Z',
          completedAt: homeItem.completedAt || '2026-09-08T02:30:00Z',
          duration: homeItem.durationString || '1h 30m',
          totalRowsProcessed: homeItem.totalRowsProcessed || 1250000,
          totalBytesProcessed: '4.82 GB',
          avgThroughput: homeItem.throughputFormatted || '42,100 rows/s',
          cdcBacklogSeconds: isModeCutoverApplicable ? 0 : null,
          cdcEventsProcessed: isModeCutoverApplicable ? 184200 : null,
          watermarkProgression: 'SCN: 91048291 -> SCN: 91054100',
          errorMessage: homeItem.errorMessage || null,
          attempts: [
            {
              attemptNumber: 1,
              invocationId: `inv-${homeItem.id}-001`,
              state: homeItem.outcome === 'SUCCEEDED' ? 'SUCCEEDED' : 'FAILED',
              startedAt: homeItem.startedAt || '2026-09-08T01:00:00Z',
              completedAt: homeItem.completedAt || '2026-09-08T02:30:00Z',
              duration: homeItem.durationString || '1h 30m',
              errorReason: homeItem.errorMessage || null,
              checkpointResumeId: null,
              fenceEpoch: 1
            }
          ],
          stages: [
            {
              id: 'stg-01',
              name: 'Schema Pre-Validation & DDL Preparation',
              stageType: 'DDL_APPLY',
              status: 'COMPLETED',
              startedAt: homeItem.startedAt || '2026-09-08T01:00:00Z',
              completedAt: homeItem.startedAt || '2026-09-08T01:05:00Z',
              duration: '5m 00s',
              rowsIn: 0,
              rowsOut: 0,
              throughput: 'N/A'
            },
            {
              id: 'stg-02',
              name: isValidationMode ? 'Merkle Stream Audit Probe' : 'Bulk Data Partition Extract & Ingest',
              stageType: isValidationMode ? 'VALIDATE' : 'LOAD',
              status: homeItem.outcome === 'SUCCEEDED' ? 'COMPLETED' : 'FAILED',
              startedAt: homeItem.startedAt || '2026-09-08T01:05:00Z',
              completedAt: homeItem.completedAt || '2026-09-08T02:25:00Z',
              duration: '1h 20m',
              rowsIn: homeItem.totalRowsProcessed || 1250000,
              rowsOut: homeItem.totalRowsProcessed || 1250000,
              throughput: homeItem.throughputFormatted || '42,100 rows/s',
              errorMessage: homeItem.errorMessage || undefined
            },
            {
              id: 'stg-03',
              name: 'Forensic Parity & Evidence Seal',
              stageType: 'VALIDATE',
              status: homeItem.outcome === 'SUCCEEDED' ? 'COMPLETED' : 'SKIPPED',
              startedAt: homeItem.completedAt || '2026-09-08T02:25:00Z',
              completedAt: homeItem.completedAt || '2026-09-08T02:30:00Z',
              duration: '5m 00s',
              rowsIn: homeItem.totalRowsProcessed || 1250000,
              rowsOut: homeItem.totalRowsProcessed || 1250000,
              throughput: '120,000 rows/s'
            }
          ]
        }
      ],

      planAndConfig: {
        currentPlanId: `plan-${homeItem.id}-v1`,
        planFingerprint: 'sha256:e4b8192a01f9284ca019284bc910284ab019284cf910284bd019284ca019284d',
        revisions: [
          {
            revisionNumber: 1,
            planId: `plan-${homeItem.id}-v1`,
            fingerprint: 'sha256:e4b8192a01f9284ca019284bc910284ab019284cf910284bd019284ca019284d',
            createdAt: homeItem.startedAt || '2026-09-08T00:45:00Z',
            createdBy: homeItem.operator || 'Lead DBA',
            changeSummary: 'Initial compiled execution plan.',
            isCurrentExecutionPlan: true
          }
        ],
        sections: [
          {
            title: 'Migration Scope & Topology',
            description: 'Defined source, target, and dataset partitions for this execution.',
            entries: [
              { label: 'Source System', value: homeItem.sourceProvider },
              { label: 'Target System', value: homeItem.targetProvider },
              { label: 'Mode', value: homeItem.mode },
              { label: 'Object Scope', value: 'All tables in public and core schemas' }
            ]
          },
          {
            title: 'Performance & Concurrency Tuning',
            description: 'Engine concurrency, batch boundaries, and memory buffers.',
            entries: [
              { label: 'Worker Threads', value: '16 Parallel Partitions' },
              { label: 'Batch Commit Size', value: '5,000 rows / batch' },
              { label: 'Memory Buffer Limit', value: '2,048 MB' },
              { label: 'Network Compression', value: 'Zstandard (Level 3)' }
            ]
          },
          {
            title: 'Data Privacy & Masking Rules',
            description: 'Cryptographic tokenization and PII masking policies.',
            entries: [
              { label: 'PII Protection Policy', value: 'Standard Enterprise Masking' },
              { label: 'Encrypted Columns', value: 'ssn, card_token, email' },
              { label: 'Masking Algorithm', value: 'HMAC-SHA256 Tokenization' }
            ]
          }
        ],
        semanticDiffs: []
      },

      governance: [
        {
          barrierId: `gov-${homeItem.id}-01`,
          protectedOperation: 'Execution Authorization Barrier',
          requestedAt: homeItem.startedAt || '2026-09-08T00:50:00Z',
          requesterName: homeItem.operator || 'Lead DBA',
          makerCheckerSatisfied: true,
          quorumRequired: 2,
          quorumSatisfied: 2,
          status: 'APPROVED',
          planFingerprintBinding: 'sha256:e4b8192a01f9284ca019284bc910284ab019284cf910284bd019284ca019284d',
          expiresAt: null,
          approvers: [
            {
              approverName: 'R. Simmons',
              role: 'Security & Compliance Officer',
              decision: 'APPROVED',
              decidedAt: homeItem.startedAt || '2026-09-08T00:55:00Z',
              comment: 'Data masking parameters and scope verified.'
            },
            {
              approverName: 'M. Vance',
              role: 'VP Infrastructure Engineering',
              decision: 'APPROVED',
              decidedAt: homeItem.startedAt || '2026-09-08T00:58:00Z',
              comment: 'Production change window authorized.'
            }
          ],
          decisionNotes: 'Maker-checker dual control satisfied prior to pipeline trigger.'
        }
      ],

      validationRuns: [
        {
          validationRunId: `val-${homeItem.id}-01`,
          phase: 'POST_MIGRATION',
          startedAt: homeItem.completedAt || '2026-09-08T02:25:00Z',
          completedAt: homeItem.completedAt || '2026-09-08T02:30:00Z',
          duration: '5m 00s',
          verdict: (homeItem.validationState || 'PASSED') as ValidationReconciliationState,
          rowCountSource: homeItem.totalRowsProcessed || 1250000,
          rowCountTarget: homeItem.totalRowsProcessed || 1250000,
          rowCountDelta: 0,
          merkleTreeRootMatch: homeItem.validationState === 'PASSED',
          discrepancyCount: homeItem.validationState === 'MISMATCHES_DETECTED' ? 3 : 0,
          discrepancies: homeItem.validationState === 'MISMATCHES_DETECTED' ? [
            {
              id: 'disc-01',
              tableName: 'financial_ledger',
              primaryKey: 'LEDGER_ID=90841',
              discrepancyType: 'VALUE_MISMATCH',
              sourceValue: 'AMOUNT=14500.00',
              targetValue: 'AMOUNT=1450.00',
              progression: 'LOCALIZED',
              reconciledAt: null,
              repairScriptSnippet: 'UPDATE financial_ledger SET AMOUNT = 14500.00 WHERE LEDGER_ID = 90841;'
            }
          ] : []
        }
      ],

      cutover: {
        isApplicableToMode: isModeCutoverApplicable,
        cutoverStatus: isModeCutoverApplicable ? (homeItem.outcome === 'SUCCEEDED' ? 'COMPLETED' : 'ABORTED') : 'NOT_APPLICABLE',
        recoveryStatus: 'NONE',
        cutoverPlannedAt: isModeCutoverApplicable ? homeItem.completedAt : null,
        cutoverExecutedAt: isModeCutoverApplicable ? homeItem.completedAt : null,
        downtimeSeconds: isModeCutoverApplicable ? 28 : null,
        cdcFinalLagSeconds: isModeCutoverApplicable ? 0.0 : null,
        finalSyncCatchupSeconds: isModeCutoverApplicable ? 12 : null,
        postCutoverVerificationPassed: homeItem.outcome === 'SUCCEEDED',
        failbackReady: isModeCutoverApplicable,
        failbackInvoked: false,
        failbackReason: null,
        chronology: isModeCutoverApplicable ? [
          {
            stepName: 'Cutover Gate Readiness Verification',
            status: 'COMPLETED',
            timestamp: homeItem.completedAt || '2026-09-08T02:20:00Z',
            duration: '45s',
            details: 'Replication lag verified at 0.0s threshold.'
          },
          {
            stepName: 'Source Write Quiesce',
            status: 'COMPLETED',
            timestamp: homeItem.completedAt || '2026-09-08T02:20:45Z',
            duration: '10s',
            details: 'Source database write transactions safely quiesced.'
          },
          {
            stepName: 'Final CDC Catch-up Drain',
            status: 'COMPLETED',
            timestamp: homeItem.completedAt || '2026-09-08T02:20:55Z',
            duration: '12s',
            details: 'Remaining delta events drained to zero.'
          },
          {
            stepName: 'Target Database Role Promotion',
            status: 'COMPLETED',
            timestamp: homeItem.completedAt || '2026-09-08T02:21:07Z',
            duration: '6s',
            details: 'Target promoted to primary read/write database.'
          }
        ] : []
      },

      recovery: {
        hasRecoveryOccurred: false,
        recoveryTriggerReason: null,
        recoveryTriggeredAt: null,
        recoveredAt: null,
        checkpointResumedFrom: null,
        fenceEpoch: 1,
        dataSafetyAttestation: `Execution completed under fence epoch 1. Exactly-once idempotency preserved.`,
        checkpoints: [
          {
            checkpointId: `chk-${homeItem.id}-001`,
            generation: 1,
            createdAt: homeItem.startedAt || '2026-09-08T01:30:00Z',
            associatedStage: 'Bulk Data Partition Extract',
            isSelectedForResume: true,
            isSuperseded: false,
            fenceEpoch: 1,
            committedRowsWatermark: homeItem.totalRowsProcessed || 1250000
          }
        ],
        residualExceptions: homeItem.errorMessage ? [homeItem.errorMessage] : []
      },

      evidence: {
        availability: 'SEALED',
        integrity: 'SHA256_VERIFIED',
        completeness: 'COMPLETE',
        manifests: [
          {
            manifestId: `man-${homeItem.id}-01`,
            executionId: homeItem.executionId || `exec-${homeItem.id}-01`,
            generatedAt: homeItem.completedAt || '2026-09-08T02:30:00Z',
            completeness: 'COMPLETE',
            artifactCount: 5,
            totalSizeBytes: 1420500,
            digestVerification: 'SHA256_VERIFIED',
            rootDigestSha256: 'sha256:e4b8192a01f9284ca019284bc910284ab019284cf910284bd019284ca019284d'
          }
        ],
        artifacts: [
          {
            id: 'art-01',
            category: 'PLAN',
            name: 'execution_plan_spec.json',
            digest: 'sha256:e4b8192a01f9284ca019284bc910284ab019284cf910284bd019284ca019284d',
            recordedAt: homeItem.startedAt || '2026-09-08T01:00:00Z',
            verified: true
          },
          {
            id: 'art-02',
            category: 'VALIDATION',
            name: 'parity_merkle_root.json',
            digest: 'sha256:8f12a9401b9284ce019284bc910284ab019284cf910284bd019284ca019284e',
            recordedAt: homeItem.completedAt || '2026-09-08T02:30:00Z',
            verified: true
          }
        ],
        identitySeal: {
          sealVersion: 'v1.0.0-PROD',
          fingerprintSha256: 'sha256:e4b8192a01f9284ca019284bc910284ab019284cf910284bd019284ca019284d',
          fields: [
            { name: 'Migration ID', value: homeItem.migrationId || homeItem.id },
            { name: 'Execution ID', value: homeItem.executionId || `exec-${homeItem.id}-01` },
            { name: 'Plan Fingerprint', value: 'sha256:e4b8192a01f9...' },
            { name: 'Mode', value: homeItem.mode },
            { name: 'Outcome', value: homeItem.outcome },
            { name: 'Total Rows Processed', value: (homeItem.totalRowsProcessed || 1250000).toLocaleString() },
            { name: 'Validation Verdict', value: homeItem.validationState || 'PASSED' },
            { name: 'Operator', value: homeItem.operator || 'Lead DBA' }
          ]
        },
        lastIntegrityCheckAt: homeItem.completedAt || '2026-09-08T02:35:00Z',
        integrityVerificationNotes: 'Authoritative SHA-256 digest match against cold storage manifest.'
      },

      auditTrail: [
        {
          id: `aud-${homeItem.id}-01`,
          timestamp: homeItem.startedAt || '2026-09-08T01:00:00Z',
          actorPrincipal: homeItem.operator || 'Lead DBA',
          actorRole: 'Lead Operator',
          action: 'MIGRATION_EXECUTION_TRIGGERED',
          resourceTarget: homeItem.migrationId || homeItem.id,
          outcome: 'SUCCESS',
          correlationExecutionId: homeItem.executionId || `exec-${homeItem.id}-01`,
          beforeSnapshotJson: null,
          afterSnapshotJson: JSON.stringify({ state: 'RUNNING', mode: homeItem.mode }),
          evidenceRefId: null,
          hashChainLinkSha256: 'sha256:a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0'
        },
        {
          id: `aud-${homeItem.id}-02`,
          timestamp: homeItem.completedAt || '2026-09-08T02:30:00Z',
          actorPrincipal: 'pipeline_engine@akaal.internal',
          actorRole: 'Core Engine',
          action: 'MIGRATION_EXECUTION_SEALED',
          resourceTarget: homeItem.migrationId || homeItem.id,
          outcome: homeItem.outcome === 'SUCCEEDED' ? 'SUCCESS' : 'FAILED',
          correlationExecutionId: homeItem.executionId || `exec-${homeItem.id}-01`,
          beforeSnapshotJson: JSON.stringify({ state: 'RUNNING' }),
          afterSnapshotJson: JSON.stringify({ state: homeItem.lifecycleState || 'COMPLETED', outcome: homeItem.outcome }),
          evidenceRefId: `man-${homeItem.id}-01`,
          hashChainLinkSha256: 'sha256:f0e1d2c3b4a5968778695a4b3c2d1e0f0123456789abcdef0123456789abcdef1'
        }
      ]
    };
  }
}
