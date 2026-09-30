import { Injectable } from '@angular/core';
import { IpcService } from '../ipc.service';
import { IPCResponse } from '../../models/ipc.models';

@Injectable({
  providedIn: 'root'
})
export class MigrationIpc {
  constructor(private ipc: IpcService) {}

  // 1. Create Migration
  public async createMigration(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'migration.create', payload);
  }

  // 2. Configure Migration
  public async configureMigration(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'migration.configure', payload);
  }

  // 3. Discover Metadata (Northbound Exposure)
  public async discoverMetadata(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'migration.discover', payload);
  }

  // 4. Compile / Plan Migration
  public async compilePlan(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'migration.plan', payload);
  }

  // 5. Get Plan Details (Northbound Exposure)
  public async getPlan(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'migration.get_plan', payload);
  }

  // 6. Get Readiness Assessment (Northbound Exposure)
  public async getReadiness(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'migration.readiness', payload);
  }

  // 7. Approve Governance Gate
  public async approveMigration(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'migration.approve', payload);
  }

  // 8. Initialize Execution Plan
  public async initializeMigration(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'migration.initialize', payload);
  }

  // 9. Start / Launch Execution
  public async startMigration(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'migration.start', payload);
  }

  // 10. Pause Execution
  public async pauseMigration(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'migration.pause', payload);
  }

  // 11. Resume Execution
  public async resumeMigration(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'migration.resume', payload);
  }

  // 12. Cancel Execution
  public async cancelMigration(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'migration.cancel', payload);
  }

  public async deleteMigration(migrationId: string): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'migration.delete', { migration_id: migrationId });
  }

  public async archiveMigration(migrationId: string): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'migration.archive', { migration_id: migrationId });
  }

  // 13. Recover Execution
  public async recoverMigration(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'migration.recover', payload);
  }

  // 14. Cutover Execution
  public async cutoverMigration(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'migration.cutover', payload);
  }

  // 14b. Failback Execution
  public async failbackMigration(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'migration.failback', payload);
  }

  // 15. CDC Sync
  public async syncCdc(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'migration.cdc_sync', payload);
  }

  // 16. Throttle CDC Rate
  public async throttleCdc(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'migration.throttle_cdc', payload);
  }

  // 17. Trigger Emergency Checkpoint (Northbound Exposure)
  public async triggerCheckpoint(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'migration.checkpoint', payload);
  }

  // 18. Create Schedule
  public async createSchedule(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'schedule.create', payload);
  }

  // 17. List Schedules (Northbound Exposure)
  public async listSchedules(payload?: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'schedule.list', payload || {});
  }

  // 18. Get Migration Details
  public async getMigration(migrationId: string): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'migration.get', { migration_id: migrationId });
  }

  // 19. List Fleet Migrations
  public async listMigrations(payload?: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'migration.list', payload || {});
  }

  // 20. Get Operation Telemetry
  public async getOperation(operationId: string): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'operation.get', { operation_id: operationId });
  }

  // 21. Projects & Initiatives
  public async listProjects(payload?: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'project.list', payload || {});
  }

  public async getProject(projectIdOrPayload: any): Promise<IPCResponse> {
    const payload = typeof projectIdOrPayload === 'string' ? { project_id: projectIdOrPayload } : projectIdOrPayload;
    return this.ipc.invoke('pipeline', 'project.get', payload);
  }

  public async createProject(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'project.create', payload);
  }

  public async updateProject(idOrPayload: any, maybePayload?: any): Promise<IPCResponse> {
    let payload = idOrPayload;
    if (typeof idOrPayload === 'string') {
      payload = { id: idOrPayload, project_id: idOrPayload, ...(maybePayload || {}) };
    } else if (maybePayload) {
      payload = { ...idOrPayload, ...maybePayload };
    }
    return this.ipc.invoke('pipeline', 'project.update', payload);
  }

  public async deleteProject(projectId: string): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'project.delete', { project_id: projectId });
  }

  public async listInitiatives(payload?: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'initiative.list', payload || {});
  }

  public async getInitiative(initiativeIdOrPayload: any): Promise<IPCResponse> {
    const payload = typeof initiativeIdOrPayload === 'string' ? { initiative_id: initiativeIdOrPayload } : initiativeIdOrPayload;
    return this.ipc.invoke('pipeline', 'initiative.get', payload);
  }

  public async createInitiative(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'initiative.create', payload);
  }

  public async updateInitiative(idOrPayload: any, maybePayload?: any): Promise<IPCResponse> {
    let payload = idOrPayload;
    if (typeof idOrPayload === 'string') {
      payload = { id: idOrPayload, initiative_id: idOrPayload, ...(maybePayload || {}) };
    } else if (maybePayload) {
      payload = { ...idOrPayload, ...maybePayload };
    }
    return this.ipc.invoke('pipeline', 'initiative.update', payload);
  }

  public async deleteInitiative(initiativeId: string): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'initiative.delete', { initiative_id: initiativeId });
  }

  // 22. Connections Vault
  public async listConnections(payload?: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'connection.list', payload || {});
  }

  public async getConnection(connectionIdOrPayload: any): Promise<IPCResponse> {
    const payload = typeof connectionIdOrPayload === 'string' ? { connection_id: connectionIdOrPayload } : connectionIdOrPayload;
    return this.ipc.invoke('pipeline', 'connection.get', payload);
  }

  public async createConnection(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'connection.create', payload);
  }

  public async updateConnection(idOrPayload: any, maybePayload?: any): Promise<IPCResponse> {
    let payload = idOrPayload;
    if (typeof idOrPayload === 'string') {
      payload = { id: idOrPayload, connection_id: idOrPayload, ...(maybePayload || {}) };
    } else if (maybePayload) {
      payload = { ...idOrPayload, ...maybePayload };
    }
    return this.ipc.invoke('pipeline', 'connection.update', payload);
  }

  public async testConnection(idOrPayload?: any, maybePayload?: any): Promise<IPCResponse> {
    let payload = idOrPayload || {};
    if (typeof idOrPayload === 'string') {
      payload = { connection_id: idOrPayload, id: idOrPayload, ...(maybePayload || {}) };
    } else if (maybePayload) {
      payload = { ...idOrPayload, ...maybePayload };
    }
    return this.ipc.invoke('pipeline', 'connection.test', payload);
  }

  public async deleteConnection(connectionId: string): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'connection.delete', { connection_id: connectionId });
  }

  public async listConnectionProviders(): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'connection.list_providers', {});
  }

  public async describeConnectionProvider(providerId: string): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'connection.describe_provider', { provider_id: providerId });
  }

  // 23. Templates Store
  public async listTemplates(payload?: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'template.list', payload || {});
  }

  public async getTemplate(templateId: string): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'template.get', { template_id: templateId });
  }

  public async createTemplate(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'template.create', payload);
  }

  public async updateTemplate(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'template.update', payload);
  }

  public async deprecateTemplate(templateId: string): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'template.deprecate', { template_id: templateId });
  }

  public async deleteTemplate(templateId: string): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'template.delete', { template_id: templateId });
  }

  // 24. Audit Trail
  public async getAuditTrail(limit?: number): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'audit.get_trail', { limit: limit || 100 });
  }

  public async verifyAuditTrail(): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'audit.verify', {});
  }

  // 25. Validation Studio
  public async createValidationMission(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'validation.create_mission', payload);
  }

  public async initializeValidationMission(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'validation.initialize_mission', payload);
  }

  public async executeValidationMission(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'validation.execute_mission', payload);
  }

  public async controlContinuousValidation(payload: { mission_id: string; action: string }): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'validation.control_continuous', payload);
  }

  public async establishValidationBaseline(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'validation.establish_baseline', payload);
  }

  public async getValidationBaseline(baselineId: string): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'validation.get_baseline', { baseline_id: baselineId });
  }

  public async resolveValidationCapability(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'validation.resolve_capability', payload);
  }

  public async getValidationMission(missionId: string): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'validation.get_mission', { mission_id: missionId });
  }

  public async listValidationMissions(payload?: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'validation.list_missions', payload || {});
  }

  public async listValidationDiscrepancies(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'validation.list_discrepancies', payload);
  }

  public async getValidationDiscrepancy(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'validation.get_discrepancy', payload);
  }

  public async dispatchValidationRepair(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('validation', 'dispatch_repair', payload);
  }

  // 26. Cockpit Health & Observability
  public async getExplainableHealth(migrationId?: string): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'health.get_explainable', { migration_id: migrationId || '' });
  }

  public async getObservability(migrationId?: string): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'observability.get', { migration_id: migrationId || '' });
  }

  public async getCapacityReport(): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'capacity.report', {});
  }
}

