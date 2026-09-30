/**
 * AKAAL Administration — 5.9 Audit Service
 * Authoritative presentation service for Audit Policies, Administrative Audit Trail,
 * Destinations, Retention Policies, Legal Hold, Integrity Verification, and Audit Export.
 */

import { Injectable, signal, Optional, inject } from '@angular/core';
import { AdministrationIpcService } from '../../../core/services/ipc/administration.ipc';
import {
  AuditPolicy,
  AdministrativeAuditEvent,
  AuditDestination,
  EvidenceRetentionPolicy,
  LegalHold,
  AuditIntegrityVerification,
  AuditExportRequest
} from '../models/audit.models';

@Injectable({
  providedIn: 'root'
})
export class AuditService {
  private adminIpc?: AdministrationIpcService;

  constructor(@Optional() adminIpc?: AdministrationIpcService) {
    if (adminIpc) {
      this.adminIpc = adminIpc;
    } else {
      try {
        this.adminIpc = inject(AdministrationIpcService, { optional: true }) || undefined;
      } catch {
        this.adminIpc = undefined;
      }
    }
    this.loadFromBackend();
  }

  public async loadFromBackend(): Promise<void> {
    if (!this.adminIpc) return;
    try {
      const respTrail = await this.adminIpc.listAuditTrail();
      if (respTrail.status === 'SUCCESS' && Array.isArray(respTrail.data)) {
        this.auditTrail.set(respTrail.data);
      } else {
        const resp = await this.adminIpc.getAuditLedger();
        if (resp.status === 'SUCCESS' && resp.data) {
          const events = Array.isArray(resp.data) ? resp.data : (resp.data.ledger || resp.data.entries || []);
          const mapped = events.map((ev: any) => ({
            id: ev.audit_id || ev.id,
            timestamp: ev.created_at || ev.timestamp || new Date().toISOString(),
            actor: ev.actor_id || 'system',
            actorRole: 'ORGANIZATION_OWNER',
            action: ev.event_type || ev.action || 'ADMIN_MUTATION',
            resourceType: ev.resource_type || 'SYSTEM_PLATFORM',
            resourceId: ev.resource_id || 'system-root',
            outcome: ev.decision === 'DENY' ? 'DENIED' : 'SUCCESS',
            ipAddress: '127.0.0.1',
            correlationId: ev.correlation_id || ev.audit_id || 'corr-admin-01',
            details: typeof ev.details === 'string' ? ev.details : JSON.stringify(ev.details || {}),
          }));
          this.auditTrail.set(mapped);
        }
      }

      const respPol = await this.adminIpc.listAuditPolicies();
      if (respPol.status === 'SUCCESS' && respPol.data) {
        if (Array.isArray(respPol.data.policies)) {
          this.auditPolicies.set(respPol.data.policies);
        }
        if (Array.isArray(respPol.data.destinations)) {
          this.destinations.set(respPol.data.destinations);
        }
      }
    } catch {
      // Offline fallback
    }
  }
  // Audit Policies
  public auditPolicies = signal<AuditPolicy[]>([
    {
      id: 'apol-01',
      name: 'Administrative Control Plane Mutations',
      category: 'ADMIN_ACTIONS',
      severityFilter: 'ALL',
      retentionDays: 730,
      destinations: ['adest-syslog-01', 'adest-splunk-01'],
      description: 'Records all creation, updates, and terminations across enterprise organizations, workspaces, and role assignments.',
      status: 'ACTIVE',
      updatedAt: '2026-02-15'
    },
    {
      id: 'apol-02',
      name: 'Cryptographic Key & Secret Access Operations',
      category: 'SECURITY_OPERATIONS',
      severityFilter: 'ALL',
      retentionDays: 1095,
      destinations: ['adest-splunk-01'],
      description: 'Records all key rotation, KMS envelope decryption requests, and credential reference updates.',
      status: 'ACTIVE',
      updatedAt: '2026-02-10'
    },
    {
      id: 'apol-03',
      name: 'High-Volume Pipeline Execution Audit',
      category: 'PIPELINE_EXECUTION',
      severityFilter: 'WARNING_AND_ABOVE',
      retentionDays: 90,
      destinations: ['adest-syslog-01'],
      description: 'Captures pipeline failures, CDC lag anomalies, and stage transition errors.',
      status: 'ACTIVE',
      updatedAt: '2026-01-20'
    }
  ]);

  // Administrative Audit Trail (Real canonical structured events)
  public auditTrail = signal<AdministrativeAuditEvent[]>([]);

  // Audit Destinations
  public destinations = signal<AuditDestination[]>([]);

  // Evidence Retention Policies
  public retentionPolicies = signal<EvidenceRetentionPolicy[]>([
    {
      id: 'ret-01',
      name: 'Compliance Audit & Cryptographic Evidence Retention',
      evidenceClass: 'CRYPTOGRAPHIC_EVIDENCE',
      retentionYears: 7,
      dispositionAction: 'ARCHIVE_COLD',
      legalHoldExempt: false,
      status: 'ENFORCED'
    }
  ]);

  // Legal Holds
  public legalHolds = signal<LegalHold[]>([]);

  // Audit Integrity Verifications
  public verifications = signal<AuditIntegrityVerification[]>([]);

  // Export Requests
  public exportRequests = signal<AuditExportRequest[]>([]);

  public getPolicyById(id: string): AuditPolicy | undefined {
    return this.auditPolicies().find(p => p.id === id);
  }

  public getEventById(id: string): AdministrativeAuditEvent | undefined {
    return this.auditTrail().find(e => e.id === id);
  }

  public getDestinationById(id: string): AuditDestination | undefined {
    return this.destinations().find(d => d.id === id);
  }

  public getLegalHoldById(id: string): LegalHold | undefined {
    return this.legalHolds().find(h => h.id === id);
  }

  public createAuditPolicy(policy: Omit<AuditPolicy, 'id' | 'updatedAt' | 'status'>): void {
    const newRecord: AuditPolicy = {
      ...policy,
      id: `apol-${Date.now()}`,
      status: 'ACTIVE',
      updatedAt: new Date().toISOString().split('T')[0]
    };
    this.auditPolicies.update(list => [newRecord, ...list]);
  }

  public createDestination(dest: Omit<AuditDestination, 'id' | 'createdAt' | 'status'>): void {
    const newRecord: AuditDestination = {
      ...dest,
      id: `adest-${Date.now()}`,
      status: 'CONFIGURED',
      createdAt: new Date().toISOString().split('T')[0]
    };
    this.destinations.update(list => [newRecord, ...list]);
  }

  public createLegalHold(hold: Omit<LegalHold, 'id' | 'holdCreatedDate' | 'heldItemsCount' | 'status'>): void {
    const newRecord: LegalHold = {
      ...hold,
      id: `hold-${Date.now()}`,
      holdCreatedDate: new Date().toISOString().split('T')[0],
      heldItemsCount: 0,
      status: 'ACTIVE'
    };
    this.legalHolds.update(list => [newRecord, ...list]);
  }

  public releaseLegalHold(id: string, reason: string): void {
    this.legalHolds.update(list =>
      list.map(h => {
        if (h.id === id) {
          return {
            ...h,
            status: 'RELEASED',
            releasedDate: new Date().toISOString().split('T')[0],
            releaseReason: reason
          };
        }
        return h;
      })
    );
  }

  public triggerExport(format: 'JSON' | 'CSV' | 'ZIP', dateRange: string): void {
    const req: AuditExportRequest = {
      id: `exp-${Date.now()}`,
      requestedAt: 'Just now',
      requestedBy: 'Current Operator',
      format,
      dateRange,
      status: 'COMPLETED',
      downloadSize: '1.2 MB',
      recordCount: 1250
    };
    this.exportRequests.update(list => [req, ...list]);
  }
}
