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

  it('should handle Test Connection with truthful unexposed backend notice (B-2.2-05)', async () => {
    service.selectProvider('postgresql');
    service.runTestConnection();
    expect(service.draft().isTesting).toBe(true);
    await new Promise(r => setTimeout(r, 250));
    expect(service.draft().isTesting).toBe(false);
    expect(service.draft().verificationFacts.warnings[0]).toContain('Live connection testing is unavailable');
  });

  it('should handle Permission Probe with truthful notice', async () => {
    service.selectProvider('postgresql');
    service.runPermissionProbe();
    expect(service.draft().isTestingPermissions).toBe(true);
    await new Promise(r => setTimeout(r, 250));
    expect(service.draft().isTestingPermissions).toBe(false);
    expect(service.draft().verificationFacts.warnings).toContain('Live permission introspection is unavailable while connection service is disconnected.');
  });

  it('should handle Capability Probe with truthful notice', async () => {
    service.selectProvider('postgresql');
    service.runCapabilityProbe();
    expect(service.draft().isTestingCapabilities).toBe(true);
    await new Promise(r => setTimeout(r, 250));
    expect(service.draft().isTestingCapabilities).toBe(false);
    expect(service.draft().verificationFacts.warnings).toContain('Live capability attestation is unavailable while connection service is disconnected.');
  });

  it('should fail closed on createConnection and display truthful notice without inserting fake record into signal (B-2.2-07)', () => {
    connService.availabilityState.set('NOT_CONNECTED');
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

    // Must NOT insert fake records into production signals before live backend RPC is wired
    expect(connService.connections().length).toBe(initialCount);
    expect(service.draft().name).toBe('New Enterprise Postgres');
    expect(routerMock.navigate).not.toHaveBeenCalled();
    expect(service.creationNotice()).toBe('Connection saving is unavailable while connection service is disconnected.');
  });

  it('should fail closed when provider is missing and never fabricate PostgreSQL defaults', () => {
    service.draft.update(d => ({
      ...d,
      selectedProviderId: null,
      name: 'Unspecified Provider',
      parameters: {}
    }));

    service.createConnection();

    expect(service.creationNotice()).toBe('Cannot create connection: No provider selected.');
  });

  it('should truthfully derive connection parameters without fabricated defaults when connected', () => {
    vi.spyOn(connService, 'availabilityState').mockReturnValue('READY');
    let capturedConn: any = null;
    service.onSuccessHandler = (c) => { capturedConn = c; };

    service.selectProvider('sqlite');
    service.draft().name = 'Truthful SQLite DB';
    service.draft().environment = 'Development';
    service.draft().parameters = { database_path: '/opt/data/test.db' };
    service.draft().authMethod = 'NONE';
    service.draft().authUsername = '';

    service.createConnection();

    expect(capturedConn).not.toBeNull();
    expect(capturedConn.providerId).toBe('sqlite');
    expect(capturedConn.providerName).toBe('SQLite');
    expect(capturedConn.endpointDisplay).toBe('/opt/data/test.db');
    expect(capturedConn.endpointDisplay).not.toContain('db.prod.corp.internal');
    expect(capturedConn.endpointDisplay).not.toContain('5432');
    expect(capturedConn.authMethodDisplay).toBe('NONE');
    expect(capturedConn.authMethodDisplay).not.toContain('Password / Vault Secret');
    expect(capturedConn.workspaceId).toBe('ws-enterprise-default');
    expect(capturedConn.environment).toBe('Development');
  });
});
