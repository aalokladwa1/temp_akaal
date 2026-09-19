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

  // 13. Recover Execution
  public async recoverMigration(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'migration.recover', payload);
  }

  // 14. Throttle CDC Rate
  public async throttleCdc(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'migration.throttle_cdc', payload);
  }

  // 15. Trigger Emergency Checkpoint (Northbound Exposure)
  public async triggerCheckpoint(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'migration.checkpoint', payload);
  }

  // 16. Create Schedule
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

  public async getProject(projectId: string): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'project.get', { project_id: projectId });
  }

  public async createProject(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'project.create', payload);
  }

  public async updateProject(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'project.update', payload);
  }

  public async listInitiatives(payload?: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'initiative.list', payload || {});
  }

  public async getInitiative(initiativeId: string): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'initiative.get', { initiative_id: initiativeId });
  }

  public async createInitiative(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'initiative.create', payload);
  }

  public async updateInitiative(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'initiative.update', payload);
  }

  // 22. Connections Vault
  public async listConnections(payload?: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'connection.list', payload || {});
  }

  public async getConnection(connectionId: string): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'connection.get', { connection_id: connectionId });
  }

  public async createConnection(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'connection.create', payload);
  }

  public async updateConnection(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'connection.update', payload);
  }

  public async testConnection(payload: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'connection.test', payload);
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

  public async getValidationMission(missionId: string): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'validation.get_mission', { mission_id: missionId });
  }

  public async listValidationMissions(payload?: any): Promise<IPCResponse> {
    return this.ipc.invoke('pipeline', 'validation.list_missions', payload || {});
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

