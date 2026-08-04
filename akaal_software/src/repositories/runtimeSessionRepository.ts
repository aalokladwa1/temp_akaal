import type { RuntimeSession, EngineStageId, RuntimeEvent } from '../types/migration';
import { ipcService } from '../services/ipcService';

type RuntimeSessionChangeListener = (sessions: RuntimeSession[]) => void;

class RuntimeSessionRepository {
  private sessions: Map<string, RuntimeSession> = new Map();
  private listeners: Set<RuntimeSessionChangeListener> = new Set();

  public getSessions(): RuntimeSession[] {
    return Array.from(this.sessions.values());
  }

  public getSessionForMigration(migrationId: string): RuntimeSession | undefined {
    return Array.from(this.sessions.values()).find((s) => s.migrationId === migrationId);
  }

  public subscribe(listener: RuntimeSessionChangeListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify(): void {
    const list = Array.from(this.sessions.values());
    this.listeners.forEach((fn) => fn(list));
  }

  public allocateSession(migrationId: string, initialStage: EngineStageId = 'scout'): RuntimeSession {
    const existingCount = Array.from(this.sessions.values()).filter((s) => s.migrationId === migrationId).length;
    const session: RuntimeSession = {
      sessionId: `sess-${Date.now()}`,
      migrationId,
      executionNumber: existingCount + 1,
      status: 'initializing',
      startedAt: new Date().toISOString(),
      currentStage: initialStage,
      progressPercent: 0,
      rowsTransferred: 0,
      bytesTransferred: 0,
      throughputMbps: 0,
      activeWorkers: 0,
      cdcSyncLagMs: 0,
      decisions: [],
      events: [],
      trustScore: 100,
      riskScore: 0.0,
    };

    // Forward start_scout capability invocation to Engine Bridge via IPC
    ipcService.invokeEngineCapability('start_scout', JSON.stringify({
      migration_id: migrationId,
      session_id: session.sessionId,
      initial_stage: initialStage,
    })).catch(() => {});

    this.sessions.set(session.sessionId, session);
    this.notify();
    return session;
  }

  public appendEvent(sessionId: string, event: RuntimeEvent): void {
    const session = this.sessions.get(sessionId);
    if (!session) return;

    const existingEvents = session.events || [];
    // Cap in-memory event buffer at 500 to prevent DOM inflation
    const updatedEvents = [...existingEvents, event].slice(-500);

    const updatedSession: RuntimeSession = {
      ...session,
      events: updatedEvents,
    };

    this.sessions.set(sessionId, updatedSession);
    this.notify();
  }

  public updateTelemetry(
    sessionId: string,
    metrics: Partial<Pick<RuntimeSession, 'throughputMbps' | 'rowsTransferred' | 'bytesTransferred' | 'activeWorkers' | 'cdcSyncLagMs' | 'progressPercent'>>
  ): void {
    const session = this.sessions.get(sessionId);
    if (!session) return;

    const updatedSession: RuntimeSession = {
      ...session,
      ...metrics,
    };

    this.sessions.set(sessionId, updatedSession);
    this.notify();
  }

  public updateStage(sessionId: string, currentStage: EngineStageId): void {
    const session = this.sessions.get(sessionId);
    if (!session) return;

    const updatedSession: RuntimeSession = {
      ...session,
      currentStage,
    };

    this.sessions.set(sessionId, updatedSession);
    this.notify();
  }

  public async invokeEngineCapability(sessionId: string, capability: string, payload: Record<string, any> = {}): Promise<any> {
    const session = this.sessions.get(sessionId);
    const reqPayload = JSON.stringify({
      session_id: sessionId,
      migration_id: session?.migrationId || 'mig-1',
      ...payload,
    });

    try {
      const rawResp = await ipcService.invokeEngineCapability(capability, reqPayload);
      let parsed: any = {};
      try {
        parsed = typeof rawResp === 'string' ? JSON.parse(rawResp) : rawResp;
      } catch {
        parsed = { status: 'success', raw: rawResp };
      }

      let resultObj: any = {};
      if (parsed && parsed.result) {
        try {
          resultObj = typeof parsed.result === 'string' ? JSON.parse(parsed.result) : parsed.result;
        } catch {
          resultObj = parsed.result;
        }
      } else {
        resultObj = parsed;
      }

      // Log engine execution event
      this.appendEvent(sessionId, {
        eventId: `evt-ipc-${Date.now()}`,
        timestamp: new Date().toISOString(),
        sessionId,
        migrationId: session?.migrationId || 'mig-1',
        severity: 'info',
        source: 'bridge',
        stageNumber: 1,
        eventType: `${capability.toUpperCase()}_EXECUTED`,
        payload: resultObj,
      });

      // Update Session Telemetry / Stage from Engine Result
      if (resultObj) {
        const updateObj: Partial<RuntimeSession> = {};
        if (resultObj.stage && ['scout', 'advisor', 'live_intel', 'planner', 'manager', 'schema_exec', 'data_migration', 'validator', 'healing', 'certification'].includes(resultObj.stage)) {
          updateObj.currentStage = resultObj.stage as EngineStageId;
        }
        if (typeof resultObj.throughput_mbps === 'number') {
          updateObj.throughputMbps = resultObj.throughput_mbps;
        }
        if (typeof resultObj.active_partitions === 'number') {
          updateObj.activeWorkers = resultObj.active_partitions;
        }
        if (typeof resultObj.rows_audited === 'number') {
          updateObj.rowsTransferred = resultObj.rows_audited;
        }
        if (Object.keys(updateObj).length > 0) {
          this.updateTelemetry(sessionId, updateObj);
        }
      }

      return resultObj;
    } catch (err: any) {
      this.appendEvent(sessionId, {
        eventId: `evt-err-${Date.now()}`,
        timestamp: new Date().toISOString(),
        sessionId,
        migrationId: session?.migrationId || 'mig-1',
        severity: 'critical',
        source: 'bridge',
        stageNumber: 1,
        eventType: `${capability.toUpperCase()}_FAILED`,
        payload: { error: String(err) },
      });
      throw err;
    }
  }

  public updateSessionFromIPC(updated: RuntimeSession): void {
    this.sessions.set(updated.sessionId, updated);
    this.notify();
  }
}

export const runtimeSessionRepository = new RuntimeSessionRepository();
