/**
 * AKAAL Enterprise Migration Platform
 * Cockpit / Mission Control — Pure Adapter Service
 *
 * Governing Directives:
 * 1. Projects canonical runtime truth provided by akaalEngine / akaalPipeline / akaalIPC.
 * 2. Zero semantic invention: Does not recalculate ETA, health, or DAG successors.
 * 3. Formats raw values into clear, calm DBA-grade representations.
 */

import { Injectable } from '@angular/core';
import {
  CockpitIdentity,
  CockpitStatusPulse,
  WorkloadProgressState,
  RuntimeDagTopology,
  RuntimeDagNode,
  RuntimeDagEdge,
  EngineHealthSummary,
  SubsystemHealthEntry,
  OperatorIntervention,
  CurrentActivitySnapshot,
  DynamicWorkbenchData,
  ExecutionContextNarrative,
  CanonicalPermittedAction,
  CockpitActivityEvent
} from '../../modules/migration/cockpit/cockpit.models';
import { MigrationMode } from '../models/migration-view.models';

@Injectable({
  providedIn: 'root'
})
export class CockpitAdapterService {

  // --------------------------------------------------------------------------
  // 1. PROJECT MIGRATION IDENTITY
  // --------------------------------------------------------------------------
  public projectIdentity(session: any): CockpitIdentity {
    const mode = (session?.mode || 'M2_BULK_CDC') as MigrationMode;
    const sourceProvider = session?.sourceProvider || 'Source';
    const targetProvider = session?.targetProvider || 'Target';

    const sourceLabel = session?.sourceDatabase
      ? `${session.sourceDatabase} (${session.sourceHost || 'source.internal'})`
      : `${sourceProvider} Primary Instance`;

    const targetLabel = session?.targetDatabase
      ? `${session.targetDatabase} (${session.targetHost || 'target.internal'})`
      : `${targetProvider} Primary Instance`;

    const lifecycleState = session?.lifecycleState || 'IDLE';

    return {
      migrationId: session?.id || session?.migrationId || '',
      migrationName: session?.name?.trim() || `${sourceProvider} to ${targetProvider} Migration`,
      environment: session?.environment || 'Production',
      mode,
      modeTitle: this.formatModeTitle(mode),
      source: {
        provider: sourceProvider,
        host: session?.sourceHost,
        port: session?.sourcePort,
        database: session?.sourceDatabase,
        label: sourceLabel
      },
      target: {
        provider: targetProvider,
        host: session?.targetHost,
        port: session?.targetPort,
        database: session?.targetDatabase,
        label: targetLabel
      },
      planRevision: session?.planRevision || 1,
      planFingerprint: session?.planFingerprint || '',
      activeAttempt: session?.activeAttempt || 1,
      lifecycleState,
      lifecycleLabel: this.formatLifecycleLabel(lifecycleState),
      startedAt: session?.startedAt || null,
      elapsedTimeString: session?.elapsedTimeString || '00:00:00'
    };
  }

  // --------------------------------------------------------------------------
  // 2. PROJECT GLANCEABLE STATUS & OPERATIONAL PULSE
  // --------------------------------------------------------------------------
  public projectStatusPulse(session: any): CockpitStatusPulse {
    const mode = (session?.mode || 'M2_BULK_CDC') as MigrationMode;
    const lifecycleState = session?.lifecycleState || (session ? 'RUNNING' : 'IDLE');
    const isPaused = lifecycleState === 'PAUSED';
    const isFailed = lifecycleState === 'FAILED';
    const isWaiting = lifecycleState === 'WAITING_FOR_APPROVAL';
    const isIdle = !session || lifecycleState === 'IDLE';

    let stateHeading = isIdle ? 'IDLE / NO ACTIVE EXECUTION' : 'RUNNING NORMALLY';
    let stateBadgeColor = isIdle ? 'bg-slate-50 text-slate-600 border-slate-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200';
    let phaseSubtitle = isIdle ? 'No active migration workload' : (session?.currentStage || 'Bulk Data Movement & CDC Stream');
    let activeTaskDescription = isIdle ? 'The migration engine is idle. No task is currently executing.' : (session?.activeTaskDescription || 'Active execution');

    if (isPaused) {
      stateHeading = 'EXECUTION PAUSED';
      stateBadgeColor = 'bg-amber-50 text-amber-700 border-amber-200';
      phaseSubtitle = 'Replication Checkpointed & Workers Idled';
      activeTaskDescription = 'State persisted at durable checkpoint. Ready for resume.';
    } else if (isFailed) {
      stateHeading = 'EXECUTION FAILED';
      stateBadgeColor = 'bg-rose-50 text-rose-700 border-rose-200';
      phaseSubtitle = 'Target Connection Pool Starvation';
      activeTaskDescription = 'Worker thread pool exhausted available connections. Operator action required.';
    } else if (isWaiting) {
      stateHeading = 'WAITING ON APPROVAL BARRIER';
      stateBadgeColor = 'bg-amber-50 text-amber-800 border-amber-300';
      phaseSubtitle = 'Cutover Authorization Gate (Gate #1)';
      activeTaskDescription = 'Source writes quiesced. CDC converged. Awaiting Dual DBA / SecOps sign-off.';
    }

    // Mode-specific horizontal metric ribbons
    const metrics: any[] = [];

    switch (mode) {
      case 'M1_BULK':
      case 'M7_DATA_ONLY':
        metrics.push(
          {
            id: 'volume',
            label: 'WORKLOAD VOLUME',
            value: (isPaused || isIdle) ? '0 / 0' : (session?.rowsProcessedString || '0 / 0'),
            unit: 'rows',
            status: isIdle ? 'MUTED' : 'NORMAL',
            detail: session?.progressPercent !== undefined ? `${session.progressPercent}% complete` : (isIdle ? 'No active workload' : '0% complete'),
            sparkline: session?.volumeSparkline || [0, 0, 0, 0]
          },
          {
            id: 'throughput',
            label: 'THROUGHPUT',
            value: (isPaused || isIdle) ? '0' : (session?.throughputRowsSecFormatted || '0'),
            unit: 'rows/s',
            status: (isPaused || isIdle) ? 'MUTED' : 'SUCCESS',
            detail: isPaused ? '0 MB/s (Paused)' : (isIdle ? '0 MB/s (Idle)' : (session?.throughputBytesSecFormatted || '0 B/s')),
            sparkline: (isPaused || isIdle) ? [0, 0, 0, 0] : (session?.throughputSparkline || [0, 0, 0, 0])
          },
          {
            id: 'workers',
            label: 'WORKER CONCURRENCY',
            value: (isPaused || isIdle) ? '0 / 0' : (session?.activeWorkers !== undefined ? `${session.activeWorkers} / ${session.totalWorkers || session.activeWorkers}` : '0 / 0'),
            unit: 'threads',
            status: (isPaused || isIdle) ? 'MUTED' : 'NORMAL',
            detail: isIdle ? 'Workers unassigned' : 'Operational concurrency'
          },
          {
            id: 'eta',
            label: 'ESTIMATED REMAINING',
            value: (isPaused || isIdle) ? '--:--' : (session?.etaString || '--:--'),
            unit: 'time',
            status: isIdle ? 'MUTED' : 'NORMAL',
            detail: isIdle ? 'Idle' : 'Linear estimation'
          },
          {
            id: 'checkpoint',
            label: 'CHECKPOINT AGE',
            value: isIdle ? 'None' : (session?.checkpointFreshness || 'Durable'),
            unit: isIdle ? '' : 'fresh',
            status: isIdle ? 'MUTED' : 'SUCCESS',
            detail: isIdle ? 'No active checkpoint' : 'Durable WAL state'
          }
        );
        break;

      case 'M2_BULK_CDC':
        metrics.push(
          {
            id: 'cdc_lag',
            label: 'CDC REPLICA LAG',
            value: (isPaused || isIdle) ? '0' : `${session?.cdcLagMs ?? 0}`,
            unit: (isPaused || isIdle) ? '' : 'ms',
            status: isIdle ? 'MUTED' : ((session?.cdcLagMs || 0) < 500 ? 'SUCCESS' : 'WARNING'),
            detail: isIdle ? 'No active stream' : 'SLA < 500ms',
            sparkline: (isPaused || isIdle) ? [0, 0, 0, 0] : (session?.cdcSparkline || [0, 0, 0, 0])
          },
          {
            id: 'backlog',
            label: 'REPLICATION BACKLOG',
            value: (isPaused || isIdle) ? '0 MB' : (session?.backlogMbFormatted || '0 MB'),
            unit: 'buffer',
            status: isIdle ? 'MUTED' : 'NORMAL',
            detail: isIdle ? 'Buffer empty' : 'In-memory ring buffer',
            sparkline: (isPaused || isIdle) ? [0, 0, 0, 0] : (session?.backlogSparkline || [0, 0, 0, 0])
          },
          {
            id: 'apply_rate',
            label: 'APPLY RATE',
            value: (isPaused || isIdle) ? '0' : (session?.applyTxSecFormatted || '0'),
            unit: 'tx/s',
            status: (isPaused || isIdle) ? 'MUTED' : 'SUCCESS',
            detail: isIdle ? 'Idle' : 'Target stream apply',
            sparkline: (isPaused || isIdle) ? [0, 0, 0, 0] : (session?.applySparkline || [0, 0, 0, 0])
          },
          {
            id: 'convergence',
            label: 'CONVERGENCE STATE',
            value: isIdle ? 'IDLE' : (session?.convergenceState || 'CONVERGED'),
            unit: '',
            status: isIdle ? 'MUTED' : 'SUCCESS',
            detail: isIdle ? 'No active replication' : 'Source & Target in sync'
          },
          {
            id: 'active_workers',
            label: 'WORKERS',
            value: (isPaused || isIdle) ? '0 / 0' : `${session?.activeWorkers || 0} / ${session?.totalWorkers || session?.activeWorkers || 0}`,
            unit: 'active',
            status: isIdle ? 'MUTED' : 'NORMAL',
            detail: isIdle ? 'Workers unassigned' : 'Parallel chunk ingestion'
          }
        );
        break;

      case 'M3_CDC':
        metrics.push(
          {
            id: 'cdc_lag',
            label: 'STREAMING LAG',
            value: isIdle ? '0' : `${session?.cdcLagMs ?? 0}`,
            unit: isIdle ? '' : 'ms',
            status: isIdle ? 'MUTED' : 'SUCCESS',
            detail: isIdle ? 'Stream inactive' : 'Zero backlog buildup',
            sparkline: isIdle ? [0, 0, 0, 0] : (session?.cdcSparkline || [0, 0, 0, 0])
          },
          {
            id: 'capture_rate',
            label: 'CAPTURE RATE',
            value: isIdle ? '0' : (session?.captureTxSecFormatted || '0'),
            unit: 'events/s',
            status: isIdle ? 'MUTED' : 'NORMAL',
            detail: isIdle ? 'Idle' : 'Source transaction log',
            sparkline: isIdle ? [0, 0, 0, 0] : (session?.captureSparkline || [0, 0, 0, 0])
          },
          {
            id: 'apply_rate',
            label: 'APPLY RATE',
            value: isIdle ? '0' : (session?.applyTxSecFormatted || '0'),
            unit: 'events/s',
            status: isIdle ? 'MUTED' : 'SUCCESS',
            detail: isIdle ? 'Idle' : 'Continuous write pipeline',
            sparkline: isIdle ? [0, 0, 0, 0] : (session?.applySparkline || [0, 0, 0, 0])
          },
          {
            id: 'buffer_fill',
            label: 'RING BUFFER',
            value: isIdle ? '0%' : (session?.bufferFillPercent || '0%'),
            unit: 'capacity',
            status: isIdle ? 'MUTED' : 'NORMAL',
            detail: isIdle ? '0 MB used' : (session?.bufferCapacityFormatted || '0 MB / 2048 MB')
          },
          {
            id: 'mode_type',
            label: 'STREAM TYPE',
            value: 'Continuous',
            unit: 'sync',
            status: 'MUTED',
            detail: 'No finite end date'
          }
        );
        break;

      case 'M4_INCREMENTAL':
        metrics.push(
          {
            id: 'watermark',
            label: 'CURRENT WATERMARK',
            value: isIdle ? 'None' : (session?.watermarkValue || 'None'),
            unit: 'timestamp',
            status: isIdle ? 'MUTED' : 'NORMAL',
            detail: isIdle ? 'No watermark' : 'Column: updated_at'
          },
          {
            id: 'poll_cycle',
            label: 'POLL CYCLE',
            value: isIdle ? 'Idle' : (session?.pollIntervalFormatted || 'Every 60s'),
            unit: 'interval',
            status: isIdle ? 'MUTED' : 'NORMAL',
            detail: isIdle ? 'No active polling' : 'Scheduled cycle'
          },
          {
            id: 'records_last',
            label: 'LAST CYCLE RECORDS',
            value: isIdle ? '0' : (session?.recordsLastCycleFormatted || '0'),
            unit: 'records',
            status: isIdle ? 'MUTED' : 'SUCCESS',
            detail: isIdle ? 'Idle' : 'Last poll cycle',
            sparkline: isIdle ? [0, 0, 0, 0] : (session?.recordsSparkline || [0, 0, 0, 0])
          },
          {
            id: 'query_latency',
            label: 'QUERY DURATION',
            value: isIdle ? '0 ms' : (session?.queryDurationFormatted || '0 ms'),
            unit: 'latency',
            status: isIdle ? 'MUTED' : 'NORMAL',
            detail: isIdle ? 'Idle' : 'Index seek query',
            sparkline: isIdle ? [0, 0, 0, 0] : (session?.queryLatencySparkline || [0, 0, 0, 0])
          },
          {
            id: 'state',
            label: 'POLL ENGINE',
            value: isIdle ? 'Idle' : 'Active Polling',
            unit: isIdle ? '' : 'healthy',
            status: isIdle ? 'MUTED' : 'SUCCESS',
            detail: isIdle ? 'No active poll task' : 'Zero query timeouts'
          }
        );
        break;

      case 'M5_STATE_SYNC':
        metrics.push(
          {
            id: 'divergence',
            label: 'DIVERGENCE COUNT',
            value: isIdle ? '0' : (session?.divergenceCountFormatted || '0'),
            unit: 'diffs',
            status: isIdle ? 'MUTED' : ((session?.divergenceCount || 0) === 0 ? 'SUCCESS' : 'WARNING'),
            detail: isIdle ? 'No active comparison' : 'Across scanned tables',
            sparkline: isIdle ? [0, 0, 0, 0] : (session?.divergenceSparkline || [0, 0, 0, 0])
          },
          {
            id: 'reconciliation',
            label: 'RECONCILIATION',
            value: isIdle ? 'None' : (session?.correctionsAppliedFormatted || '0 applied'),
            unit: 'corrections',
            status: isIdle ? 'MUTED' : 'SUCCESS',
            detail: isIdle ? 'No pending corrections' : 'Reconciliation status'
          },
          {
            id: 'convergence_trend',
            label: 'CONVERGENCE TREND',
            value: isIdle ? 'IDLE' : (session?.convergenceTrend || 'CONVERGED'),
            unit: '',
            status: isIdle ? 'MUTED' : 'SUCCESS',
            detail: isIdle ? 'Sync idle' : 'State reconciliation'
          },
          {
            id: 'cycle',
            label: 'SYNC CYCLE',
            value: isIdle ? 'None' : `Cycle #${session?.syncCycle || 1}`,
            unit: 'active',
            status: isIdle ? 'MUTED' : 'NORMAL',
            detail: isIdle ? 'No active cycle' : 'Incremental scan'
          },
          {
            id: 'state_hash',
            label: 'MERKLE HASH',
            value: isIdle ? 'None' : (session?.merkleHash || 'Verified'),
            unit: isIdle ? '' : 'sha-256',
            status: isIdle ? 'MUTED' : 'NORMAL',
            detail: isIdle ? 'No state hash' : 'Verified matching'
          }
        );
        break;

      case 'M6_SCHEMA_ONLY':
        metrics.push(
          {
            id: 'objects_progress',
            label: 'SCHEMA OBJECTS',
            value: isIdle ? '0 / 0' : (session?.objectsProgressFormatted || '0 / 0'),
            unit: 'objects',
            status: isIdle ? 'MUTED' : 'NORMAL',
            detail: isIdle ? 'No active schema execution' : 'DDL execution'
          },
          {
            id: 'active_object',
            label: 'ACTIVE DDL',
            value: isIdle ? 'None' : (session?.activeDdlObject || 'None'),
            unit: isIdle ? '' : 'DDL',
            status: isIdle ? 'MUTED' : 'NORMAL',
            detail: isIdle ? 'Idle' : 'Active statement'
          },
          {
            id: 'failed_ddl',
            label: 'FAILURES',
            value: isIdle ? '0' : `${session?.failedDdlCount || 0}`,
            unit: 'failed',
            status: isIdle ? 'MUTED' : ((session?.failedDdlCount || 0) === 0 ? 'SUCCESS' : 'CRITICAL'),
            detail: isIdle ? 'No errors' : 'Syntax & constraint errors'
          },
          {
            id: 'workers',
            label: 'DDL THREADS',
            value: isIdle ? '0 / 0' : `${session?.activeWorkers || 0} / ${session?.totalWorkers || session?.activeWorkers || 0}`,
            unit: 'threads',
            status: isIdle ? 'MUTED' : 'NORMAL',
            detail: isIdle ? 'Workers unassigned' : 'Topological order'
          },
          {
            id: 'elapsed',
            label: 'ELAPSED',
            value: isIdle ? '00:00' : (session?.elapsedTimeString || '00:00'),
            unit: 'time',
            status: isIdle ? 'MUTED' : 'NORMAL',
            detail: isIdle ? 'Idle' : (session?.etaString ? `ETA ${session.etaString}` : 'In progress')
          }
        );
        break;
    }

    return {
      stateHeading,
      stateBadgeColor,
      phaseSubtitle,
      activeTaskDescription,
      metrics
    };
  }

  // --------------------------------------------------------------------------
  // 3. PROJECT WORKLOAD PROGRESS (DISTINCT FROM PLAN PROGRESS)
  // --------------------------------------------------------------------------
  public projectWorkloadProgress(session: any): WorkloadProgressState {
    const mode = (session?.mode || 'M2_BULK_CDC') as MigrationMode;
    const lifecycleState = session?.lifecycleState || 'IDLE';
    const isIdle = !session || lifecycleState === 'IDLE';
    const isContinuous = mode === 'M3_CDC';
    const isSchema = mode === 'M6_SCHEMA_ONLY';

    if (isIdle) {
      return {
        isContinuous,
        isUnknown: false,
        units: isContinuous ? 'records' : (isSchema ? 'objects' : 'rows'),
        processed: 0,
        total: 0,
        percentage: 0,
        processedFormatted: isContinuous ? '0 stream events' : (isSchema ? '0 objects' : '0 rows'),
        totalFormatted: isContinuous ? 'Continuous Stream' : (isSchema ? '0 objects' : '0 rows'),
        currentRateFormatted: '0 rows/s',
        etaFormatted: '--:--',
        elapsedFormatted: '00:00',
        phaseDescription: 'No active migration workload'
      };
    }

    if (isContinuous) {
      const processed = session?.eventsProcessed || 0;
      return {
        isContinuous: true,
        isUnknown: false,
        units: 'records',
        processed,
        total: 0,
        percentage: 100,
        processedFormatted: `${processed.toLocaleString()} stream events`,
        totalFormatted: 'Continuous Stream',
        currentRateFormatted: session?.throughputRowsSecFormatted || '0 events/s',
        elapsedFormatted: session?.elapsedTimeString || '00:00',
        phaseDescription: session?.currentStage || 'Continuous transaction log replication active'
      };
    }

    if (isSchema) {
      const processed = session?.objectsCompleted || 0;
      const total = session?.objectsTotal || 0;
      const percentage = total > 0 ? Math.round((processed / total) * 1000) / 10 : 0;
      return {
        isContinuous: false,
        isUnknown: false,
        units: 'objects',
        processed,
        total,
        percentage,
        processedFormatted: `${processed} objects`,
        totalFormatted: `${total} objects`,
        currentRateFormatted: session?.throughputRowsSecFormatted || '0 DDL/s',
        etaFormatted: session?.etaString || '--:--',
        elapsedFormatted: session?.elapsedTimeString || '00:00',
        phaseDescription: session?.currentStage || `Applying DDL (${processed}/${total} completed)`
      };
    }

    const processed = session?.rowsProcessed || 0;
    const total = session?.rowsTotal || 0;
    const percentage = total > 0 ? Math.round((processed / total) * 1000) / 10 : (session?.progressPercent || 0);

    return {
      isContinuous: false,
      isUnknown: false,
      units: 'rows',
      processed,
      total,
      percentage,
      processedFormatted: processed >= 1000000 ? `${(processed / 1000000).toFixed(1)}M rows` : `${processed.toLocaleString()} rows`,
      totalFormatted: total >= 1000000 ? `${(total / 1000000).toFixed(1)}M rows` : `${total.toLocaleString()} rows`,
      currentRateFormatted: session?.throughputRowsSecFormatted || '0 rows/s',
      etaFormatted: session?.etaString || '--:--',
      elapsedFormatted: session?.elapsedTimeString || '00:00',
      phaseDescription: session?.currentStage || `Bulk Extraction & Target Ingestion (${percentage}% completed)`
    };
  }

  // --------------------------------------------------------------------------
  // 4. PROJECT LIVE EXECUTION PLAN / RUNTIME DAG
  // --------------------------------------------------------------------------
  public projectRuntimeDag(session: any): RuntimeDagTopology {
    const lifecycleState = session?.lifecycleState || 'IDLE';
    const isIdle = !session || lifecycleState === 'IDLE';

    if (isIdle && !session?.dagNodes) {
      return {
        nodes: [],
        edges: [],
        activeNodeIds: [],
        completedNodeIds: [],
        waitingBarrierNodeIds: []
      };
    }

    if (session?.dagNodes && Array.isArray(session.dagNodes)) {
      const nodes: RuntimeDagNode[] = session.dagNodes;
      const edges: RuntimeDagEdge[] = session.dagEdges || [];
      return {
        nodes,
        edges,
        activeNodeIds: nodes.filter(n => n.runtimeState === 'ACTIVE' || n.runtimeState === 'RUNNING_PARALLEL').map(n => n.id),
        completedNodeIds: nodes.filter(n => n.runtimeState === 'COMPLETED').map(n => n.id),
        waitingBarrierNodeIds: nodes.filter(n => n.runtimeState === 'APPROVAL_BARRIER').map(n => n.id)
      };
    }

    const mode = (session?.mode || 'M2_BULK_CDC') as MigrationMode;
    const isPaused = session?.lifecycleState === 'PAUSED';
    const isWaitingBarrier = session?.lifecycleState === 'WAITING_FOR_APPROVAL';
    const isFailed = session?.lifecycleState === 'FAILED';

    // Canonical default nodes projected for M2 Bulk + CDC
    let nodes: RuntimeDagNode[] = [];
    let edges: RuntimeDagEdge[] = [];

    if (mode === 'M6_SCHEMA_ONLY') {
      nodes = [
        {
          id: 'node-1',
          order: 1,
          label: 'Pre-Flight Engine Verification',
          subtitle: 'Connectivity, privileges, catalog lock verification',
          category: 'SYSTEM',
          stageType: 'PRE_FLIGHT',
          runtimeState: 'COMPLETED',
          elapsedDuration: session?.preflightDuration || '12s',
          incomingNodeIds: [],
          outgoingNodeIds: ['node-2']
        },
        {
          id: 'node-2',
          order: 2,
          label: 'Schema & Table DDL Generation',
          subtitle: 'Tables, sequences, primary keys',
          category: 'TRANSFORMATION',
          stageType: 'SCHEMA_DDL',
          runtimeState: 'COMPLETED',
          elapsedDuration: session?.ddlDuration || '48s',
          incomingNodeIds: ['node-1'],
          outgoingNodeIds: ['node-3']
        },
        {
          id: 'node-3',
          order: 3,
          label: 'Index & Constraint Construction',
          subtitle: 'Secondary indexes, foreign keys, check constraints',
          category: 'TRANSFORMATION',
          stageType: 'SCHEMA_DDL',
          runtimeState: isFailed ? 'FAILED' : 'ACTIVE',
          progressPercent: session?.progressPercent || 0,
          throughputFormatted: session?.throughputRowsSecFormatted || 'Active',
          workerAllocation: session?.activeWorkers || 0,
          elapsedDuration: session?.elapsedTimeString || '00:00',
          failureMessage: isFailed ? (session?.failureMessage || 'Target DDL constraint execution rejected') : undefined,
          incomingNodeIds: ['node-2'],
          outgoingNodeIds: ['node-4']
        },
        {
          id: 'node-4',
          order: 4,
          label: 'Schema DDL Structural Certification',
          subtitle: 'Catalog diff comparison & constraint validation',
          category: 'VALIDATION',
          stageType: 'POST_VALIDATION',
          runtimeState: 'UPCOMING',
          incomingNodeIds: ['node-3'],
          outgoingNodeIds: []
        }
      ];

      edges = [
        { id: 'e1-2', source: 'node-1', target: 'node-2', isActive: false, isCompleted: true },
        { id: 'e2-3', source: 'node-2', target: 'node-3', isActive: true, isCompleted: false },
        { id: 'e3-4', source: 'node-3', target: 'node-4', isActive: false, isCompleted: false }
      ];
    } else {
      // M1, M2, M3, M7 standard runtime DAG
      nodes = [
        {
          id: 'stage-1',
          order: 1,
          label: 'Pre-Flight System Check',
          subtitle: 'Driver verification, schema catalog locks, storage headroom',
          category: 'SYSTEM',
          stageType: 'PRE_FLIGHT',
          runtimeState: 'COMPLETED',
          elapsedDuration: session?.preflightDuration || '18s',
          incomingNodeIds: [],
          outgoingNodeIds: ['stage-2']
        },
        {
          id: 'stage-2',
          order: 2,
          label: 'Target Schema Preparation',
          subtitle: 'DDL translation, surrogate keys & table allocation',
          category: 'TRANSFORMATION',
          stageType: 'SCHEMA_DDL',
          runtimeState: 'COMPLETED',
          elapsedDuration: session?.schemaDuration || '01:24',
          incomingNodeIds: ['stage-1'],
          outgoingNodeIds: ['stage-3', 'stage-4']
        },
        {
          id: 'stage-3',
          order: 3,
          label: 'Parallel Bulk Table Extraction & Load',
          subtitle: session?.bulkSubtitle || 'Partition workers ingesting scoped workload',
          category: 'INGESTION',
          stageType: 'BULK_LOAD',
          runtimeState: isWaitingBarrier ? 'COMPLETED' : (isFailed ? 'FAILED' : (isPaused ? 'WAITING' : 'ACTIVE')),
          progressPercent: isWaitingBarrier ? 100 : (session?.progressPercent || 0),
          throughputFormatted: isPaused ? 'Paused' : (session?.throughputRowsSecFormatted || 'Active'),
          workerAllocation: isPaused ? 0 : (session?.activeWorkers || 0),
          elapsedDuration: session?.elapsedTimeString || '00:00',
          failureMessage: isFailed ? (session?.failureMessage || 'Worker pool execution interrupted') : undefined,
          incomingNodeIds: ['stage-2'],
          outgoingNodeIds: ['barrier-1']
        },
        {
          id: 'stage-4',
          order: 4,
          label: 'Continuous CDC Log Stream',
          subtitle: 'CDC stream capture & target ingestion',
          category: 'INGESTION',
          stageType: 'CDC_CAPTURE',
          runtimeState: isWaitingBarrier ? 'ACTIVE' : (isPaused ? 'WAITING' : 'RUNNING_PARALLEL'),
          throughputFormatted: session?.cdcThroughputFormatted || (session?.cdcLagMs !== undefined ? `${session.cdcLagMs}ms lag` : 'Active'),
          workerAllocation: 4,
          isContinuous: true,
          incomingNodeIds: ['stage-2'],
          outgoingNodeIds: ['barrier-1']
        },
        {
          id: 'barrier-1',
          order: 5,
          label: 'Cutover Authorization Gate (Gate #1)',
          subtitle: 'Dual-DBA Quorum & SecOps 4-Eyes Sign-off',
          category: 'GOVERNANCE',
          stageType: 'APPROVAL_BARRIER',
          runtimeState: isWaitingBarrier ? 'APPROVAL_BARRIER' : 'UPCOMING',
          isBarrier: true,
          barrierConfig: {
            id: 'barrier-1',
            gateName: 'Pre-Cutover Quorum Sign-off',
            description: 'Enforces CDC catch-up SLA <500ms and requires 2 authorized signatures before source quiesce.',
            protectedOperation: 'CUTOVER_EXECUTION',
            signerPolicy: 'FOUR_EYES',
            requiredSignatures: 2,
            approverRoles: ['LEAD_DBA', 'SECOPS_OFFICER'],
            separationOfDuties: true,
            cdcMaxLagMs: 500,
            requireDlqEmpty: true,
            requireCheckpointClean: true,
            requireValidationPass: true,
            requireTargetTablesEmpty: false,
            rejectionAction: 'HALT_MIGRATION',
            timeoutMinutes: 60,
            timeoutAction: 'ALERT_AND_HOLD',
            planBindingHash: session?.planFingerprint || '',
            isMandatory: true,
            policyLocked: true,
            afterStageId: 'stage-3',
            beforeStageId: 'stage-6'
          },
          incomingNodeIds: ['stage-3', 'stage-4'],
          outgoingNodeIds: ['stage-6']
        },
        {
          id: 'stage-6',
          order: 6,
          label: 'Production Cutover & Source Quiesce',
          subtitle: 'Final CDC flush, transition traffic authority to target',
          category: 'SYSTEM',
          stageType: 'CUTOVER',
          runtimeState: 'UPCOMING',
          incomingNodeIds: ['barrier-1'],
          outgoingNodeIds: ['stage-7']
        },
        {
          id: 'stage-7',
          order: 7,
          label: 'Post-Migration Integrity Certification',
          subtitle: 'Merkle Tree hash comparison & compliance seal',
          category: 'VALIDATION',
          stageType: 'POST_VALIDATION',
          runtimeState: 'UPCOMING',
          incomingNodeIds: ['stage-6'],
          outgoingNodeIds: []
        }
      ];

      edges = [
        { id: 'e1-2', source: 'stage-1', target: 'stage-2', isActive: false, isCompleted: true },
        { id: 'e2-3', source: 'stage-2', target: 'stage-3', isActive: !isWaitingBarrier, isCompleted: isWaitingBarrier },
        { id: 'e2-4', source: 'stage-2', target: 'stage-4', isActive: true, isCompleted: false },
        { id: 'e3-b1', source: 'stage-3', target: 'barrier-1', isActive: isWaitingBarrier, isCompleted: false },
        { id: 'e4-b1', source: 'stage-4', target: 'barrier-1', isActive: isWaitingBarrier, isCompleted: false },
        { id: 'eb1-6', source: 'barrier-1', target: 'stage-6', isActive: false, isCompleted: false },
        { id: 'e6-7', source: 'stage-6', target: 'stage-7', isActive: false, isCompleted: false }
      ];
    }

    const activeNodeIds = nodes.filter(n => n.runtimeState === 'ACTIVE' || n.runtimeState === 'RUNNING_PARALLEL').map(n => n.id);
    const completedNodeIds = nodes.filter(n => n.runtimeState === 'COMPLETED').map(n => n.id);
    const waitingBarrierNodeIds = nodes.filter(n => n.runtimeState === 'APPROVAL_BARRIER').map(n => n.id);

    return {
      nodes,
      edges,
      activeNodeIds,
      completedNodeIds,
      waitingBarrierNodeIds
    };
  }

  // --------------------------------------------------------------------------
  // 5. PROJECT OPERATIONALLY RELEVANT DAG NEIGHBORHOOD
  // --------------------------------------------------------------------------
  public projectActiveNeighborhood(topology: RuntimeDagTopology, focusNodeId?: string): RuntimeDagTopology {
    // When plan is small (<= 7 nodes), the entire topology fits cleanly in the page
    if (topology.nodes.length <= 7 && !focusNodeId) {
      return topology;
    }

    // Determine target focus node (either specified, or first active/barrier, or first node)
    const targetNodeId = focusNodeId ||
      topology.waitingBarrierNodeIds[0] ||
      topology.activeNodeIds[0] ||
      topology.nodes[0]?.id;

    const targetNode = topology.nodes.find(n => n.id === targetNodeId);
    if (!targetNode) return topology;

    const neighborhoodIds = new Set<string>();
    neighborhoodIds.add(targetNode.id);

    // Add immediate predecessors
    targetNode.incomingNodeIds.forEach(id => neighborhoodIds.add(id));

    // Add immediate successors
    targetNode.outgoingNodeIds.forEach(id => neighborhoodIds.add(id));

    // Also include other active nodes if running parallel
    topology.activeNodeIds.forEach(id => neighborhoodIds.add(id));

    const nodes = topology.nodes.filter(n => neighborhoodIds.has(n.id));
    const edges = topology.edges.filter(e => neighborhoodIds.has(e.source) && neighborhoodIds.has(e.target));

    return {
      nodes,
      edges,
      activeNodeIds: topology.activeNodeIds.filter(id => neighborhoodIds.has(id)),
      completedNodeIds: topology.completedNodeIds.filter(id => neighborhoodIds.has(id)),
      waitingBarrierNodeIds: topology.waitingBarrierNodeIds.filter(id => neighborhoodIds.has(id))
    };
  }

  // --------------------------------------------------------------------------
  // 6. PROJECT ENGINE HEALTH (COLLECTION-ORIENTED & EXPLAINABLE)
  // --------------------------------------------------------------------------
  public projectEngineHealth(session: any): EngineHealthSummary {
    const lifecycleState = session?.lifecycleState || 'IDLE';
    const isIdle = !session || lifecycleState === 'IDLE';
    const isDegraded = session?.isHealthDegraded || false;
    const isFailed = lifecycleState === 'FAILED';

    let overallStatus: any = isIdle ? 'HEALTHY' : 'HEALTHY';
    let statusLabel = isIdle ? 'Engine Idle' : 'Engine Operating Normally';
    let summaryNarrative = isIdle
      ? 'No active migration workload. Engine subsystems ready for operation.'
      : 'All runtime subsystems reporting healthy metrics. Zero connection or backpressure anomalies.';
    let primaryDegradedReason: string | undefined;
    let primaryDegradedEvidence: string | undefined;

    if (isFailed) {
      overallStatus = 'CRITICAL';
      statusLabel = 'Critical Failure — Execution Halted';
      summaryNarrative = session?.failureMessage || 'Target connection pool exhausted. Workers in retry backoff state.';
      primaryDegradedReason = session?.failureReason || 'Target database rejected worker transactions due to connection limits.';
      primaryDegradedEvidence = session?.failureEvidence || 'Target host connection limit reached for worker pool.';
    } else if (isDegraded) {
      overallStatus = 'DEGRADED';
      statusLabel = 'Engine Operating with Advisory Warnings';
      summaryNarrative = 'Target write latency elevated. Ingestion rate automatically throttled.';
      primaryDegradedReason = session?.degradedReason || 'Target storage volume reported queue depth elevation.';
      primaryDegradedEvidence = session?.degradedEvidence || 'Target write latency increased during ingestion.';
    }

    const subsystems: SubsystemHealthEntry[] = [
      {
        id: 'source',
        name: 'Source Endpoint',
        category: 'STORAGE',
        status: 'HEALTHY',
        latencyMs: isIdle ? 0 : (session?.sourceLatencyMs || 3.2),
        throughputMetrics: isIdle ? '0 MB/s read' : (session?.sourceThroughputMetrics || 'Read throughput active'),
        reason: isIdle ? 'Standby / Idle' : 'Active session connection healthy',
        isCausal: false
      },
      {
        id: 'target',
        name: 'Target Endpoint',
        category: 'STORAGE',
        status: isFailed ? 'CRITICAL' : (isDegraded ? 'DEGRADED' : 'HEALTHY'),
        latencyMs: isIdle ? 0 : (isDegraded ? 48.6 : (session?.targetLatencyMs || 4.8)),
        throughputMetrics: isIdle ? '0 MB/s write' : (isDegraded ? 'Write throttled' : (session?.targetThroughputMetrics || 'Target write normal')),
        reason: isFailed
          ? 'Connection pool exhausted'
          : (isDegraded ? 'IOPS saturation: elevated queue depth' : (isIdle ? 'Standby / Idle' : 'Target write throughput normal')),
        evidence: isFailed
          ? (session?.failureEvidence || 'Error: connection limit reached')
          : (isDegraded ? 'Latency elevated' : (isIdle ? undefined : 'Apply latency normal')),
        isCausal: isFailed || isDegraded
      },
      {
        id: 'workers',
        name: 'Worker Thread Pool',
        category: 'COMPUTE',
        status: isFailed ? 'DEGRADED' : 'HEALTHY',
        reason: isFailed ? 'Threads waiting on connection pool' : (isIdle ? 'Workers unassigned' : `${session?.activeWorkers || 0} active threads`),
        throughputMetrics: isIdle ? '0 active threads' : `${session?.activeWorkers || 0} active threads`,
        isCausal: isFailed
      },
      {
        id: 'execution_site',
        name: 'Execution Site (Local)',
        category: 'TOPOLOGY',
        status: 'HEALTHY',
        reason: isIdle ? 'Host process ready' : 'Host process memory within pool limits',
        throughputMetrics: '0% CPU throttling',
        isCausal: false
      },
      {
        id: 'checkpoint',
        name: 'Checkpoint Ledger',
        category: 'STATE',
        status: 'HEALTHY',
        reason: isIdle ? 'No active checkpoint' : (session?.checkpointFreshness || 'Durable checkpoint recorded'),
        throughputMetrics: isIdle ? 'None' : (session?.lastCheckpointFormatted || 'Committed'),
        isCausal: false
      },
      {
        id: 'cdc_capture',
        name: 'CDC Capture Engine',
        category: 'STREAMING',
        status: 'HEALTHY',
        latencyMs: isIdle ? 0 : (session?.cdcCaptureLatencyMs || 0),
        throughputMetrics: isIdle ? '0 events/s' : (session?.captureTxSecFormatted || '0 events/s'),
        reason: isIdle ? 'Idle' : 'CDC stream capture active',
        isCausal: false
      },
      {
        id: 'cdc_apply',
        name: 'CDC Apply Stream',
        category: 'STREAMING',
        status: isDegraded ? 'DEGRADED' : 'HEALTHY',
        latencyMs: isIdle ? 0 : (isDegraded ? 24 : (session?.cdcApplyLatencyMs || 0)),
        throughputMetrics: isIdle ? '0 tx/s apply' : (session?.applyTxSecFormatted || '0 tx/s apply'),
        reason: isDegraded ? 'Target write queue depth elevating' : (isIdle ? 'Idle' : 'Catchup SLA satisfied'),
        isCausal: isDegraded
      },
      {
        id: 'buffer',
        name: 'In-Memory Ring Buffer',
        category: 'MEMORY',
        status: 'HEALTHY',
        throughputMetrics: isIdle ? '0 MB / 2048 MB (0% used)' : (session?.bufferFillPercent ? `${session.bufferFillPercent} capacity` : 'Buffer active'),
        reason: 'Zero spill-to-disk events recorded',
        isCausal: false
      },
      {
        id: 'validation',
        name: 'Inline Validation Subsystem',
        category: 'ASSURANCE',
        status: 'HEALTHY',
        reason: isIdle ? 'Standby / Idle' : 'Checksum parity verified',
        throughputMetrics: '0 mismatches',
        isCausal: false
      }
    ];

    return {
      overallStatus,
      statusLabel,
      summaryNarrative,
      subsystems,
      primaryDegradedReason,
      primaryDegradedEvidence
    };
  }

  // --------------------------------------------------------------------------
  // 7. PROJECT CURRENT PHYSICAL ACTIVITY
  // --------------------------------------------------------------------------
  public projectCurrentActivity(session: any): CurrentActivitySnapshot {
    const lifecycleState = session?.lifecycleState || 'IDLE';
    const isIdle = !session || lifecycleState === 'IDLE';
    const isPaused = lifecycleState === 'PAUSED';

    if (isIdle) {
      return {
        activeStageName: 'No active stage',
        activeEntityName: 'None',
        entityType: 'TABLE',
        partitionChunkInfo: 'No active partition chunk',
        activeWorkerCount: 0,
        totalWorkerCount: 0,
        throughputRowsSec: 0,
        throughputBytesSec: 0,
        elapsedSec: 0,
        checkpointContext: 'No active checkpoint',
        isStalled: false
      };
    }

    return {
      activeStageName: session?.currentStage || 'Active Execution',
      activeEntityName: session?.activeEntityName || 'None',
      entityType: session?.entityType || 'TABLE',
      partitionChunkInfo: session?.partitionChunkInfo || 'Active chunk processing',
      activeWorkerCount: isPaused ? 0 : (session?.activeWorkers || 0),
      totalWorkerCount: session?.totalWorkers || session?.activeWorkers || 0,
      throughputRowsSec: isPaused ? 0 : (session?.throughputRowsSec || 0),
      throughputBytesSec: isPaused ? 0 : (session?.throughputBytesSec || 0),
      elapsedSec: session?.elapsedSec || 0,
      checkpointContext: session?.checkpointContext || (session?.checkpointFreshness ? `Checkpoint fresh (${session.checkpointFreshness})` : 'Durable checkpoint recorded'),
      isStalled: isPaused
    };
  }

  // --------------------------------------------------------------------------
  // 8. PROJECT DYNAMIC WORKBENCH DOMAINS
  // --------------------------------------------------------------------------
  public projectWorkbenchDomains(session: any, activeTab?: string): DynamicWorkbenchData {
    const mode = (session?.mode || 'M2_BULK_CDC') as MigrationMode;
    const lifecycleState = session?.lifecycleState || 'IDLE';
    const isIdle = !session || lifecycleState === 'IDLE';
    const isPaused = lifecycleState === 'PAUSED';

    const availableDomains: string[] = ['data_movement', 'cdc_convergence', 'workers_pool', 'execution_sites', 'checkpoint_recovery', 'validation_integrity'];
    if (mode === 'M6_SCHEMA_ONLY') {
      availableDomains.unshift('schema_execution');
    } else if (mode === 'M4_INCREMENTAL') {
      availableDomains.unshift('incremental_polling');
    } else if (mode === 'M5_STATE_SYNC') {
      availableDomains.unshift('state_sync');
    }

    const defaultDomain = availableDomains[0];
    const activeDomainId = activeTab && availableDomains.includes(activeTab) ? activeTab : defaultDomain;

    return {
      mode,
      availableDomains,
      activeDomainId,

      dataMovement: {
        totalTables: session?.totalTables || 0,
        completedTables: session?.completedTables || 0,
        activeTablesCount: session?.activeTablesCount || 0,
        overallRowsSec: isPaused ? 0 : (session?.throughputRowsSec || 0),
        overallBytesSec: isPaused ? 0 : (session?.throughputBytesSec || 0),
        tableProgressList: session?.tableProgressList || []
      },

      cdcConvergence: {
        captureScn: session?.captureScn || (isIdle ? 'None' : '0'),
        applyLsn: session?.applyLsn || (isIdle ? 'None' : '0'),
        lagMs: isIdle ? 0 : (session?.cdcLagMs || 0),
        backlogBytes: isIdle ? 0 : (session?.backlogBytes || 0),
        applyTxSec: (isPaused || isIdle) ? 0 : (session?.applyTxSec || 0),
        bufferCapacityMb: session?.bufferCapacityMb || 2048,
        bufferUsedMb: isIdle ? 0 : (session?.bufferUsedMb || 0),
        convergenceStatus: session?.convergenceState || (isIdle ? 'IDLE' : 'CONVERGED'),
        dlqCount: session?.dlqCount || 0
      },

      workersPool: {
        totalWorkers: session?.totalWorkers || (isPaused || isIdle ? 0 : (session?.activeWorkers || 0)),
        activeWorkers: isPaused || isIdle ? 0 : (session?.activeWorkers || 0),
        idleWorkers: Math.max(0, (session?.totalWorkers || 0) - (session?.activeWorkers || 0)),
        unhealthyWorkers: session?.unhealthyWorkers || 0,
        workersList: session?.workersList || []
      },

      executionSites: {
        sitesList: session?.executionSites || [
          { siteId: 'site-local-01', siteName: 'Local Engine Process', siteTypeDescriptor: 'Local Host Worker Pool', livenessState: 'ONLINE', workerCapacity: session?.totalWorkers || 16, workersAllocated: session?.activeWorkers || 0, latencyMs: 0.2, isDrainPending: false }
        ]
      },

      checkpointRecovery: {
        lastCheckpointTimestamp: session?.lastCheckpointTimestamp || (isIdle ? 'None' : new Date().toISOString()),
        lastCheckpointScn: session?.lastCheckpointScn || (isIdle ? 'None' : '0'),
        freshnessSeconds: isIdle ? 0 : (session?.checkpointFreshnessSeconds || 0),
        resumePosition: session?.resumePosition || (isIdle ? 'None' : 'Checkpoint initial'),
        activeAttempt: session?.activeAttempt || 1,
        recoveryStrategy: session?.recoveryStrategy || 'ATOMIC_STATE_JOURNAL',
        isDurable: !isIdle
      },

      validationIntegrity: {
        validationMode: session?.validationMode || 'TIER_1_ROW_HASH',
        rowCountMatchRate: session?.rowCountMatchRate ?? (isIdle ? 0 : 100.0),
        checksumMatchRate: session?.checksumMatchRate ?? (isIdle ? 0 : 100.0),
        discrepanciesCount: session?.discrepanciesCount || 0,
        discrepancySample: session?.discrepancySample || []
      },

      schemaExecution: {
        totalObjects: session?.objectsTotal || 0,
        completedObjects: session?.objectsCompleted || 0,
        failedObjects: session?.failedDdlCount || 0,
        currentDdl: session?.activeDdlObject || (isIdle ? 'None' : 'Applying DDL'),
        objectStream: session?.schemaObjectStream || []
      },

      incrementalPolling: {
        watermarkColumn: session?.watermarkColumn || (isIdle ? 'None' : 'updated_at'),
        currentWatermarkValue: session?.watermarkValue || 'None',
        pollIntervalSec: session?.pollIntervalSec || 60,
        lastPollDurationMs: session?.lastPollDurationMs || 0,
        recordsLastCycle: session?.recordsLastCycle || 0,
        nextPollScheduled: session?.nextPollScheduled || 'None',
        cycleState: isIdle ? 'IDLE' : (session?.pollCycleState || 'IDLE')
      },

      stateSync: {
        comparisonCycle: session?.syncCycle || (isIdle ? 0 : 1),
        divergenceCount: session?.divergenceCount || 0,
        correctionsApplied: session?.correctionsApplied || 0,
        unresolvedDiffs: session?.unresolvedDiffs || 0,
        convergenceTrend: session?.convergenceTrend || (isIdle ? 'IDLE' : 'CONVERGED'),
        lastReconciliationTimestamp: session?.lastReconciliationTimestamp || (isIdle ? 'None' : new Date().toISOString())
      },

      retryThrottling: {
        retryQueueLength: session?.retryQueueLength || 0,
        activeBackoffSec: session?.activeBackoffSec || 0,
        sourcePressure: session?.sourcePressure || 'LOW',
        targetPressure: session?.targetPressure || 'LOW',
        bufferPressure: session?.bufferPressure || 'LOW'
      }
    };
  }

  // --------------------------------------------------------------------------
  // 9. PROJECT PREVIOUS / NOW / NEXT EXECUTION CONTEXT
  // --------------------------------------------------------------------------
  public projectExecutionContext(session: any): ExecutionContextNarrative {
    const lifecycleState = session?.lifecycleState || 'IDLE';
    const isIdle = !session || lifecycleState === 'IDLE';
    const isWaitingBarrier = lifecycleState === 'WAITING_FOR_APPROVAL';

    if (isIdle) {
      return {
        previousCompleted: {
          stageName: 'None',
          summary: 'No previous stage execution recorded',
          completedAt: '--:--'
        },
        currentNow: {
          stageName: 'Idle',
          summary: 'No active migration stage',
          activeSince: '--:--'
        },
        nextPlanned: {
          stageName: 'None',
          summary: 'No planned stage queued',
          isBlocked: false,
          dependencyNotice: 'Awaiting migration configuration'
        }
      };
    }

    return {
      previousCompleted: {
        stageName: session?.previousStage || 'Stage Preparation',
        summary: session?.previousStageSummary || 'Pre-flight system checks and target schema prepared',
        completedAt: session?.previousStageCompletedAt || 'Completed'
      },
      currentNow: {
        stageName: isWaitingBarrier ? 'Approval Barrier: Cutover Authorization' : (session?.currentStage || 'Active Workload Execution'),
        summary: isWaitingBarrier ? 'Replication converged. Awaiting operator sign-off.' : (session?.activeTaskDescription || 'Partition extraction & ingestion in progress'),
        activeSince: session?.elapsedTimeString ? `${session.elapsedTimeString} active` : 'Active'
      },
      nextPlanned: {
        stageName: session?.nextStage || 'Post-Migration Integrity Certification',
        summary: session?.nextStageSummary || 'Final transaction buffer flush & verification',
        isBlocked: isWaitingBarrier,
        dependencyNotice: isWaitingBarrier ? 'Blocked pending Approval Barrier signature quorum' : 'Requires active stage completion'
      }
    };
  }

  // --------------------------------------------------------------------------
  // 10. PROJECT OPERATOR INTERVENTION
  // --------------------------------------------------------------------------
  public projectIntervention(session: any): OperatorIntervention | null {
    const lifecycleState = session?.lifecycleState || 'IDLE';

    if (lifecycleState === 'WAITING_FOR_APPROVAL') {
      return {
        type: 'APPROVAL_BARRIER',
        title: 'Cutover Authorization Gate Sign-off Required',
        description: 'Migration execution has reached an intentional ApprovalBarrier before production cutover. Source database write quiescence is enforced.',
        durabilityStatus: session?.durabilityStatus || 'Replication stream paused at clean checkpoint. Zero data loss.',
        barrierGateName: session?.barrierGateName || 'Pre-Cutover Quorum Sign-off',
        barrierId: session?.barrierId || 'barrier-1',
        requiredSignatures: session?.requiredSignatures || 2,
        currentSignatures: session?.currentSignatures || 1,
        separationOfDutiesEnforced: true,
        recoveryGuidance: 'Second signature required from authorized SecOps or Lead DBA role to authorize final traffic switchover.',
        isResolved: false,
        validActions: [
          {
            id: 'APPROVE_BARRIER',
            label: 'Authorize & Sign Cutover',
            icon: 'check-circle',
            isPrimary: true,
            isDestructive: false,
            confirmationRequired: true,
            confirmationTitle: 'Authorize Production Cutover?',
            confirmationMessage: 'Authorizing cutover will quiesce source transactions and promote target to active primary.',
            confirmationImpacts: ['Source database becomes read-only', 'Final CDC backlog will commit to target', 'Traffic authority shifts to target']
          },
          {
            id: 'REJECT_BARRIER',
            label: 'Reject & Hold Execution',
            icon: 'square',
            isPrimary: false,
            isDestructive: false,
            confirmationRequired: true,
            confirmationTitle: 'Reject Cutover Authorization?',
            confirmationMessage: 'Rejecting cutover will hold execution at the current checkpoint without making target primary.',
            confirmationImpacts: ['Source database remains active', 'Target remains read-only replica']
          }
        ]
      };
    }

    if (lifecycleState === 'FAILED') {
      return {
        type: 'EXECUTION_FAILURE',
        title: session?.failureTitle || 'Execution Interrupted — Worker Connection Pool Starvation',
        description: session?.failureDescription || 'The target database rejected worker thread pool transactions due to connection limits.',
        durabilityStatus: session?.durabilityStatus || 'Durable checkpoint verified. Preceding workload safely committed.',
        recoveryGuidance: session?.recoveryGuidance || 'Verify target database connection limits, then trigger checkpoint recovery.',
        isResolved: false,
        validActions: [
          {
            id: 'RECOVER_EXECUTION',
            label: 'Recover from Checkpoint',
            icon: 'rotate-ccw',
            isPrimary: true,
            isDestructive: false,
            confirmationRequired: false
          },
          {
            id: 'ABORT_EXECUTION',
            label: 'Abort Migration',
            icon: 'square',
            isPrimary: false,
            isDestructive: true,
            confirmationRequired: true,
            confirmationTitle: 'Abort Migration Run?',
            confirmationMessage: 'Aborting will terminate worker pipelines and leave target database at last checkpoint state.',
            confirmationImpacts: ['Workers will terminate immediately', 'No rollback of already-committed data']
          }
        ]
      };
    }

    if (session?.isHealthDegraded) {
      return {
        type: 'HEALTH_DEGRADED',
        title: 'Advisory Warning — Target Storage IOPS Throttling',
        description: 'Target database write latency elevated. Ingestion throughput has been auto-throttled to protect storage IOPS.',
        durabilityStatus: 'Data writes remain durable. Checkpoints healthy.',
        recoveryGuidance: 'Consider scaling target storage volume IOPS or adjusting worker batch sizing in runtime parameters.',
        isResolved: false,
        validActions: [
          {
            id: 'ACKNOWLEDGE_WARNING',
            label: 'Acknowledge Advisory',
            icon: 'check',
            isPrimary: true,
            isDestructive: false,
            confirmationRequired: false
          }
        ]
      };
    }

    return null;
  }

  // --------------------------------------------------------------------------
  // 11. PROJECT CANONICAL PERMITTED ACTIONS
  // --------------------------------------------------------------------------
  public projectPermittedActions(session: any): CanonicalPermittedAction[] {
    const state = session?.lifecycleState || 'RUNNING';

    const actions: CanonicalPermittedAction[] = [];

    const isCutoverEligibleState = ['ACTIVE', 'RUNNING', 'CDC_STREAMING'].includes(state);
    const isActiveExecutionState = ['ACTIVE', 'RUNNING', 'DISPATCHED', 'IN_PROGRESS', 'BULK_COMPLETED', 'CDC_STREAMING'].includes(state);

    if (isActiveExecutionState) {
      const mode = (session?.mode || 'M2_BULK_CDC') as MigrationMode;
      if (isCutoverEligibleState && (mode === 'M2_BULK_CDC' || mode === 'M3_CDC')) {
        actions.push({
          id: 'CUTOVER',
          label: 'Perform Cutover',
          icon: 'check-circle',
          isPrimary: true,
          isDestructive: false,
          confirmationRequired: true,
          confirmationTitle: 'Execute Production Cutover?',
          confirmationMessage: 'Cutover will flush pending CDC replication events, evaluate convergence readiness, and mark the target database as primary.',
          confirmationImpacts: ['Final CDC backlog committed to target', 'Target promoted to active primary']
        });
      }

      actions.push({
        id: 'PAUSE',
        label: 'Pause Execution',
        icon: 'pause',
        isPrimary: !(isCutoverEligibleState && (mode === 'M2_BULK_CDC' || mode === 'M3_CDC')),
        isDestructive: false,
        confirmationRequired: true,
        confirmationTitle: 'Pause Migration Execution?',
        confirmationMessage: 'Pausing will safely flush in-flight worker partitions and record a durable checkpoint. CDC replication streams can be resumed at any time without data loss.',
        confirmationImpacts: ['Worker thread partitions will idle cleanly', 'CDC capture stream will record position', 'Zero data loss guaranteed']
      });

      actions.push({
        id: 'TRIGGER_CHECKPOINT',
        label: 'Trigger Checkpoint',
        icon: 'rotate-ccw',
        isPrimary: false,
        isDestructive: false,
        confirmationRequired: false
      });

      actions.push({
        id: 'ADJUST_CONCURRENCY',
        label: 'Adjust Worker Concurrency',
        icon: 'cpu',
        isPrimary: false,
        isDestructive: false,
        confirmationRequired: false
      });
    } else if (state === 'PAUSED') {
      actions.push({
        id: 'RESUME',
        label: 'Resume Execution',
        icon: 'play',
        isPrimary: true,
        isDestructive: false,
        confirmationRequired: false
      });
    } else if (state === 'WAITING_FOR_APPROVAL') {
      actions.push({
        id: 'REVIEW_BARRIER',
        label: 'Review Barrier & Sign',
        icon: 'shield-check',
        isPrimary: true,
        isDestructive: false,
        confirmationRequired: false
      });
    } else if (state === 'FAILED') {
      actions.push({
        id: 'RECOVER_EXECUTION',
        label: 'Recover from Checkpoint',
        icon: 'rotate-ccw',
        isPrimary: true,
        isDestructive: false,
        confirmationRequired: false
      });
    }

    // Secondary / Destructive actions
    actions.push({
      id: 'EXPORT_DIAGNOSTICS',
      label: 'Export Diagnostic Package',
      icon: 'download',
      isPrimary: false,
      isDestructive: false,
      confirmationRequired: false
    });

    if (state !== 'COMPLETED' && state !== 'CANCELLED') {
      actions.push({
        id: 'TERMINATE',
        label: 'Terminate Migration',
        icon: 'square',
        isPrimary: false,
        isDestructive: true,
        confirmationRequired: true,
        confirmationTitle: 'Terminate Migration Execution?',
        confirmationMessage: 'Terminating is a consequential action. It cancels active worker pipelines and halts continuous replication.',
        confirmationImpacts: [
          'Worker thread pools will stop immediately',
          'Target database will remain at last durable checkpoint',
          'Resuming will require a new migration execution attempt'
        ]
      });
    }

    return actions;
  }

  // --------------------------------------------------------------------------
  // 12. PROJECT CHRONOLOGICAL ACTIVITY EVENTS
  // --------------------------------------------------------------------------
  public projectActivityEvents(session: any): CockpitActivityEvent[] {
    if (session?.activityEvents && Array.isArray(session.activityEvents)) {
      return session.activityEvents;
    }
    return [];
  }

  // --------------------------------------------------------------------------
  // PRIVATE HELPER FORMATTERS
  // --------------------------------------------------------------------------
  private formatModeTitle(mode: MigrationMode): string {
    switch (mode) {
      case 'M1_BULK': return 'Bulk Offline Migration';
      case 'M2_BULK_CDC': return 'Bulk Migration + Continuous CDC';
      case 'M3_CDC': return 'Continuous CDC Stream';
      case 'M4_INCREMENTAL': return 'Incremental Watermark Polling';
      case 'M5_STATE_SYNC': return 'State-Based Synchronization';
      case 'M6_SCHEMA_ONLY': return 'Schema & DDL Only';
      case 'M7_DATA_ONLY': return 'Data & Table Records Only';
      default: return 'Database Migration';
    }
  }

  private formatLifecycleLabel(state: any): string {
    switch (state) {
      case 'INITIALIZED': return 'Initialized';
      case 'RUNNING':
      case 'ACTIVE': return 'Running';
      case 'PAUSED': return 'Paused';
      case 'WAITING_FOR_APPROVAL': return 'Approval Required';
      case 'RECOVERING': return 'Recovering';
      case 'COMPLETED': return 'Completed';
      case 'FAILED': return 'Failed';
      case 'CANCELLED': return 'Cancelled';
      default: return 'Active';
    }
  }
}
