/**
 * AKAAL Shared Domain Models & Type Definitions
 */

export type EnvironmentTier = 'production' | 'staging' | 'development' | 'testing';

export interface DatabaseModel {
  id: string;
  name: string;
  vendor: 'postgresql' | 'mysql' | 'oracle' | 'mssql' | 'mongodb' | 'mariadb';
  environment: EnvironmentTier;
  host: string;
  port: number;
  database: string;
  status: 'connected' | 'disconnected' | 'warning' | 'error' | 'unknown';
  health: 'healthy' | 'warning' | 'critical' | 'unknown';
  latencyMs: number | null;
  owner: string;
  createdAt: string;
  lastChecked: string;
  isFavorite: boolean;
}

export interface MigrationModel {
  id: string;
  name: string;
  sourceDbId: string;
  targetDbId: string;
  sourceEngine: string;
  targetEngine: string;
  status: 'draft' | 'validated' | 'running' | 'paused' | 'completed' | 'failed';
  totalRows: number;
  migratedRows: number;
  progressPercent: number;
  throughputRowsSec: number;
  cdcLagSeconds: number;
  owner: string;
  createdAt: string;
}

export interface ExecutionJobModel {
  id: string;
  migrationId: string;
  migrationName: string;
  source: string;
  target: string;
  status: 'queued' | 'validating' | 'running' | 'paused' | 'retrying' | 'completed' | 'failed';
  progress: number;
  currentStage: string;
  rowsMigrated: number;
  throughput: number;
  elapsedTime: string;
  eta: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  owner: string;
}

export interface AgentNodeModel {
  id: string;
  name: string;
  host: string;
  status: 'online' | 'offline' | 'degraded' | 'paused';
  cpuPercent: number;
  memoryPercent: number;
  activeJobs: number;
  uptime: string;
}
