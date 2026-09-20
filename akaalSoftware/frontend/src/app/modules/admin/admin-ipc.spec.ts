/**
 * admin-ipc.spec.ts
 * ==================
 * Dedicated unit tests for AdministrationIpcService and its integration with Admin domain services.
 * Validates typed IPC calls, schema mapping, reactive state updates, and fail-closed semantics.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AdministrationIpcService } from '../../core/services/ipc/administration.ipc';
import { EnterpriseService } from './services/enterprise.service';
import { PeopleService } from './services/people.service';
import { AuditService } from './services/audit.service';
import { GovernanceService } from './services/governance.service';
import { IpcService } from '../../core/services/ipc.service';

describe('AdministrationIpcService', () => {
  let mockIpcService: IpcService;
  let adminIpc: AdministrationIpcService;

  beforeEach(() => {
    mockIpcService = {
      invoke: vi.fn(),
      connectionState: { set: vi.fn() },
      lastTelemetryTimestamp: { set: vi.fn() },
    } as unknown as IpcService;
    adminIpc = new AdministrationIpcService(mockIpcService);
  });

  describe('Administration queries', () => {
    it('should invoke enterprise.hierarchy query', async () => {
      (mockIpcService.invoke as any).mockResolvedValueOnce({
        status: 'SUCCESS',
        data: { legalEntityName: 'Akaal Global Financial Technologies Inc.', organizations_count: 3 },
      });

      const res = await adminIpc.getEnterpriseHierarchy();
      expect(mockIpcService.invoke).toHaveBeenCalledWith('admin', 'enterprise.hierarchy', {});
      expect(res.status).toBe('SUCCESS');
      expect(res.data?.organizations_count).toBe(3);
    });

    it('should invoke organization.list query', async () => {
      (mockIpcService.invoke as any).mockResolvedValueOnce({
        status: 'SUCCESS',
        data: [{ id: 'org-01', name: 'Akaal Corp' }],
      });

      const res = await adminIpc.listOrganizations();
      expect(mockIpcService.invoke).toHaveBeenCalledWith('admin', 'organization.list', {});
      expect(res.status).toBe('SUCCESS');
      expect(res.data?.length).toBe(1);
    });

    it('should invoke workspace.list query with orgId', async () => {
      (mockIpcService.invoke as any).mockResolvedValueOnce({
        status: 'SUCCESS',
        data: [{ id: 'ws-01', name: 'Core Banking' }],
      });

      const res = await adminIpc.listWorkspaces('org-01');
      expect(mockIpcService.invoke).toHaveBeenCalledWith('admin', 'workspace.list', { org_id: 'org-01' });
      expect(res.status).toBe('SUCCESS');
    });

    it('should invoke user.list query', async () => {
      (mockIpcService.invoke as any).mockResolvedValueOnce({
        status: 'SUCCESS',
        data: [{ id: 'usr-01', name: 'Aalok' }],
      });

      const res = await adminIpc.listUsers();
      expect(mockIpcService.invoke).toHaveBeenCalledWith('admin', 'user.list', {});
      expect(res.status).toBe('SUCCESS');
    });

    it('should invoke audit.ledger query with limit and offset', async () => {
      (mockIpcService.invoke as any).mockResolvedValueOnce({
        status: 'SUCCESS',
        data: { ledger: [], total: 0 },
      });

      const res = await adminIpc.getAuditLedger({ limit: 25, offset: 50 });
      expect(mockIpcService.invoke).toHaveBeenCalledWith('admin', 'audit.ledger', { limit: 25, offset: 50 });
      expect(res.status).toBe('SUCCESS');
    });

    it('should invoke platform.license query', async () => {
      (mockIpcService.invoke as any).mockResolvedValueOnce({
        status: 'SUCCESS',
        data: { licenseTier: 'ENTERPRISE_UNLIMITED', status: 'ACTIVE' },
      });

      const res = await adminIpc.getPlatformLicense();
      expect(mockIpcService.invoke).toHaveBeenCalledWith('admin', 'platform.license', {});
      expect(res.status).toBe('SUCCESS');
      expect(res.data?.status).toBe('ACTIVE');
    });
  });

  describe('Administration commands', () => {
    it('should invoke organization.create command', async () => {
      (mockIpcService.invoke as any).mockResolvedValueOnce({
        status: 'SUCCESS',
        data: { tenant_id: 'org-new-01', name: 'New Org Inc' },
      });

      const res = await adminIpc.createOrganization({ name: 'New Org Inc' });
      expect(mockIpcService.invoke).toHaveBeenCalledWith('admin', 'organization.create', { name: 'New Org Inc' });
      expect(res.status).toBe('SUCCESS');
    });

    it('should invoke user.create command', async () => {
      (mockIpcService.invoke as any).mockResolvedValueOnce({
        status: 'SUCCESS',
        data: { user_id: 'usr-100', name: 'John Doe' },
      });

      const res = await adminIpc.createUser({ name: 'John Doe', email: 'john@akaal.corp' });
      expect(mockIpcService.invoke).toHaveBeenCalledWith('admin', 'user.create', { name: 'John Doe', email: 'john@akaal.corp' });
      expect(res.status).toBe('SUCCESS');
    });

    it('should invoke role.assign command', async () => {
      (mockIpcService.invoke as any).mockResolvedValueOnce({
        status: 'SUCCESS',
        data: { grant_id: 'grant-01', role: 'role-operator' },
      });

      const res = await adminIpc.assignRole({ user_id: 'usr-100', role_id: 'role-operator' });
      expect(mockIpcService.invoke).toHaveBeenCalledWith('admin', 'role.assign', { user_id: 'usr-100', role_id: 'role-operator' });
      expect(res.status).toBe('SUCCESS');
    });

    it('should invoke governance.request_exception command', async () => {
      (mockIpcService.invoke as any).mockResolvedValueOnce({
        status: 'SUCCESS',
        data: { approval_id: 'appr-01', status: 'PENDING' },
      });

      const res = await adminIpc.requestGovernanceException({ policy_id: 'pol-01', reason: 'Emergency fix' });
      expect(mockIpcService.invoke).toHaveBeenCalledWith('admin', 'governance.request_exception', { policy_id: 'pol-01', reason: 'Emergency fix' });
      expect(res.status).toBe('SUCCESS');
    });

    it('should invoke key.rotate command', async () => {
      (mockIpcService.invoke as any).mockResolvedValueOnce({
        status: 'SUCCESS',
        data: { old_key_id: 'k1', new_key_id: 'k2', status: 'ACTIVE' },
      });

      const res = await adminIpc.rotateKey({ key_id: 'k1' });
      expect(mockIpcService.invoke).toHaveBeenCalledWith('admin', 'key.rotate', { key_id: 'k1' });
      expect(res.status).toBe('SUCCESS');
    });
  });

  describe('Fail-Closed & Offline Behavior', () => {
    it('should preserve ERROR status and message when backend rejects command', async () => {
      (mockIpcService.invoke as any).mockResolvedValueOnce({
        status: 'ERROR',
        error: '[FORBIDDEN] Actor lacks SYSTEM_PLATFORM_ADMIN permission',
      });

      const res = await adminIpc.enforceMfa({ user_id: 'global', mfa_policy: 'FIDO2' });
      expect(res.status).toBe('ERROR');
      expect(res.error).toContain('FORBIDDEN');
    });
  });

  describe('Feature Services Integration', () => {
    it('EnterpriseService loads and enriches state from AdministrationIpcService', async () => {
      (mockIpcService.invoke as any).mockResolvedValue({
        status: 'SUCCESS',
        data: [
          {
            id: 'org-test-enrich',
            name: 'Enriched Organization',
            code: 'ORG-ENRICH',
            description: 'Canonical organization from backend',
            tier: 'ENTERPRISE',
            status: 'ACTIVE',
            primaryContactName: 'Test Contact',
            primaryContactEmail: 'test@akaal.corp',
            workspacesCount: 2,
            activeUsersCount: 10,
            defaultRegion: 'us-east-1',
            costCenterCode: 'CC-100',
            createdAt: '2026-01-01',
            updatedAt: '2026-01-02',
          },
        ],
      });

      const enterpriseService = new EnterpriseService(undefined, adminIpc);
      await enterpriseService.loadFromBackend();

      const orgs = enterpriseService.organizations();
      expect(orgs.some(o => o.id === 'org-test-enrich')).toBe(true);
    });

    it('AuditService loads and enriches audit ledger from AdministrationIpcService', async () => {
      (mockIpcService.invoke as any).mockResolvedValue({
        status: 'SUCCESS',
        data: {
          ledger: [
            {
              id: 'audit-evt-real-01',
              audit_id: 'audit-evt-real-01',
              created_at: '2026-03-01T10:00:00Z',
              actor_id: 'admin.operator',
              event_type: 'USER_CREATED',
              resource_type: 'USER',
              resource_id: 'usr-42',
              action: 'CREATE',
              decision: 'ALLOWED',
            },
          ],
        },
      });

      const auditService = new AuditService(adminIpc);
      await auditService.loadFromBackend();

      const events = auditService.auditTrail();
      expect(events.some(e => e.id === 'audit-evt-real-01')).toBe(true);
    });
  });
});
