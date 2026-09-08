import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { CreateConnectionService } from './create-connection.service';
import { ConnectionsService } from '../connections.service';
import { ALL_PROVIDER_CATALOG_ITEMS, MANAGED_CLOUD_PROFILES } from './create-connection.schemas';

describe('CreateConnectionService & Wizard Flow (Part B)', () => {
  let service: CreateConnectionService;
  let connService: ConnectionsService;
  let routerMock: any;

  beforeEach(() => {
    routerMock = {
      navigate: vi.fn().mockResolvedValue(true)
    };

    connService = new ConnectionsService();
    connService.resetToFixtures();
    service = new CreateConnectionService(routerMock, connService);
    service.resetDraft();
  });

  it('should initialize at Step 1 with default empty draft', () => {
    expect(service.currentStep()).toBe(1);
    expect(service.draft().selectedProviderId).toBeNull();
    expect(service.draft().name).toBe('');
    expect(service.draft().environment).toBe('Production');
    expect(service.isStep1Valid()).toBe(false);
    expect(service.canProceed()).toBe(false);
  });

  it('should load all 49 physical providers + 1 file dataset in catalog', () => {
    const catalog = service.providerCatalog();
    expect(catalog.length).toBe(50); // 49 physical + 1 file dataset
    expect(catalog.some(p => p.id === 'postgresql')).toBe(true);
    expect(catalog.some(p => p.id === 'oracle')).toBe(true);
    expect(catalog.some(p => p.id === 'kafka')).toBe(true);
    expect(catalog.some(p => p.id === 's3')).toBe(true);
    expect(catalog.some(p => p.id === 'bigquery')).toBe(true);
    expect(catalog.some(p => p.id === 'salesforce')).toBe(true);
    expect(catalog.some(p => p.id === 'sqlite')).toBe(true);
  });

  it('should support selecting provider and auto-populate default configuration', () => {
    service.selectProvider('postgresql');
    expect(service.draft().selectedProviderId).toBe('postgresql');
    expect(service.draft().name).toContain('PostgreSQL');
    expect(service.draft().authMethod).toBe('PASSWORD');
    expect(service.draft().tlsMode).toBe('REQUIRED');
    expect(service.isStep1Valid()).toBe(true);
    expect(service.canProceed()).toBe(true);
  });

  it('should reset downstream parameters when switching providers to prevent stale field leakage', () => {
    // Select Oracle
    service.selectProvider('oracle');
    service.draft().oracleServiceName = 'ORCLPDB';
    service.draft().oracleAddressingMode = 'HOST_SERVICE';

    // Switch to Kafka
    service.selectProvider('kafka');
    expect(service.draft().selectedProviderId).toBe('kafka');
    expect(service.draft().authMethod).toBe('SASL_SCRAM_512');
    expect(service.draft().verificationFacts.overallStatus).toBe('UNTESTED');
  });

  it('should validate Step 2 fields correctly for Oracle Extension', () => {
    service.selectProvider('oracle');
    service.currentStep.set(2);
    service.draft.update(d => ({
      ...d,
      name: 'Core Oracle Finance',
      oracleAddressingMode: 'HOST_SERVICE',
      oracleHost: ''
    }));

    expect(service.isStep2Valid()).toBe(false);

    service.draft.update(d => ({
      ...d,
      oracleHost: 'oracle-scan.corp.internal',
      oraclePort: 1521,
      oracleServiceName: 'FINANCE_PDB'
    }));

    expect(service.isStep2Valid()).toBe(true);
    expect(service.canProceed()).toBe(true);
  });

  it('should validate Step 2 fields correctly for Google BigQuery Extension', () => {
    service.selectProvider('bigquery');
    service.currentStep.set(2);
    service.draft.update(d => ({
      ...d,
      name: 'BigQuery Warehouse',
      bigqueryProjectId: ''
    }));

    expect(service.isStep2Valid()).toBe(false);

    service.draft.update(d => ({
      ...d,
      bigqueryProjectId: 'enterprise-analytics-prod'
    }));
    expect(service.isStep2Valid()).toBe(true);
  });

  it('should validate Step 2 fields correctly for SQLite (local file)', () => {
    service.selectProvider('sqlite');
    service.currentStep.set(2);
    service.draft.update(d => ({
      ...d,
      name: 'Local SQLite Cache',
      parameters: { ...d.parameters, database_path: '/var/data/cache.db' }
    }));

    expect(service.isStep2Valid()).toBe(true);
  });

  it('should advance through steps cleanly using nextStep() and prevStep()', () => {
    service.selectProvider('postgresql');
    service.draft.update(d => ({
      ...d,
      name: 'Prod PG DB',
      parameters: { ...d.parameters, host: 'pg.corp.internal', port: 5432, database: 'banking' }
    }));

    expect(service.currentStep()).toBe(1);
    service.nextStep();
    expect(service.currentStep()).toBe(2);

    service.nextStep();
    expect(service.currentStep()).toBe(3);

    service.nextStep();
    expect(service.currentStep()).toBe(4);

    service.prevStep();
    expect(service.currentStep()).toBe(3);
  });

  it('should mark verification as stale when configuration is modified after testing', () => {
    service.selectProvider('postgresql');
    service.draft().verificationFacts.overallStatus = 'PASSED';
    expect(service.draft().isStaleVerification).toBe(false);

    service.markConfigurationMutated();
    expect(service.draft().isStaleVerification).toBe(true);
  });

  it('should simulate point-in-time Test Connection with factual probe facts', async () => {
    service.selectProvider('postgresql');
    service.runTestConnection();
    expect(service.draft().isTesting).toBe(true);

    await new Promise(r => setTimeout(r, 650));

    expect(service.draft().isTesting).toBe(false);
    expect(service.draft().verificationFacts.overallStatus).toBe('PASSED');
    expect(service.draft().verificationFacts.connectivity.length).toBeGreaterThan(0);
    expect(service.draft().verificationFacts.cdcCapability.type).toBe('NATIVE_DATABASE_CDC');
    expect(service.draft().verificationFacts.validationCapability.supported).toBe(true);
  });

  it('should correctly classify Streaming Providers as Stream Offset Consumption instead of fake database CDC', async () => {
    service.selectProvider('kafka');
    service.runTestConnection();

    await new Promise(r => setTimeout(r, 650));

    expect(service.draft().verificationFacts.cdcCapability.type).toBe('STREAM_OFFSET_CONSUMPTION');
    expect(service.draft().verificationFacts.cdcCapability.label).toContain('Stream Offset');
  });

  it('should execute Permission Probe and introspect privileges', async () => {
    service.selectProvider('postgresql');
    service.runPermissionProbe();
    expect(service.draft().isTestingPermissions).toBe(true);

    await new Promise(r => setTimeout(r, 500));

    expect(service.draft().isTestingPermissions).toBe(false);
    expect(service.draft().verificationFacts.permissions.length).toBe(7);
    expect(service.draft().verificationFacts.permissions.some(p => p.privilege.includes('SELECT'))).toBe(true);
  });

  it('should execute Capability Probe and inspect engine prerequisites', async () => {
    service.selectProvider('postgresql');
    service.runCapabilityProbe();
    expect(service.draft().isTestingCapabilities).toBe(true);

    await new Promise(r => setTimeout(r, 500));

    expect(service.draft().isTestingCapabilities).toBe(false);
    expect(service.draft().verificationFacts.capabilities.length).toBe(5);
    expect(service.draft().verificationFacts.capabilities.some(c => c.category === 'CDC')).toBe(true);
  });

  it('should successfully create ConnectionRecord and insert into ConnectionsService store without exposing raw secrets', () => {
    const initialCount = connService.connections().length;
    service.selectProvider('postgresql');
    service.draft().name = 'New Enterprise Postgres';
    service.draft().environment = 'Production';
    service.draft().parameters['host'] = 'pg-aurora.aws.company.internal';
    service.draft().parameters['port'] = 5432;
    service.draft().parameters['database'] = 'ledger';
    service.draft().authUsername = 'app_user';
    service.draft().authSecretRef = 'vault://secret/prod/ledger_pass';

    service.createConnection();

    expect(connService.connections().length).toBe(initialCount + 1);
    const created = connService.connections()[0];
    expect(created.name).toBe('New Enterprise Postgres');
    expect(created.providerId).toBe('postgresql');
    expect(created.endpointDisplay).toContain('pg-aurora.aws.company.internal:5432/ledger');
    expect(created.authMethodDisplay).toBeDefined();
    // Verify secret is NOT stored in plain representation
    expect((created as any).authSecretValue).toBeUndefined();
    expect(routerMock.navigate).toHaveBeenCalledWith(['/connections']);
  });
});
