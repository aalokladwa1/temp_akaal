/**
 * AKAAL Administration — 5.9 Audit Service
 * Authoritative presentation service for Audit Policies, Administrative Audit Trail,
 * Destinations, Retention Policies, Legal Hold, Integrity Verification, and Audit Export.
 */

import { Injectable, signal } from '@angular/core';
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
  public auditTrail = signal<AdministrativeAuditEvent[]>([
    {
      id: 'evt-aud-1001',
      timestamp: '2026-02-19 15:42:10 UTC',
      actor: 'aalok.admin@akaaltech.com',
      actorRole: 'ORGANIZATION_OWNER',
      action: 'AUTHENTICATION_POLICY_UPDATED',
      resourceType: 'AuthPolicy',
      resourceId: 'pol-critical-gov',
      outcome: 'SUCCESS',
      ipAddress: '192.168.1.104',
      correlationId: 'corr-tx-88192a01',
      details: 'Updated min password length to 24 characters and enforced FIDO2 WebAuthn strictly.'
    },
    {
      id: 'evt-aud-1002',
      timestamp: '2026-02-19 14:18:22 UTC',
      actor: 'ciso.officer@akaaltech.com',
      actorRole: 'SECURITY_ADMINISTRATOR',
      action: 'SECRET_ROTATION_TRIGGERED',
      resourceType: 'RotationRule',
      resourceId: 'rot-01',
      outcome: 'SUCCESS',
      ipAddress: '10.200.4.12',
      correlationId: 'corr-tx-88192a02',
      details: 'Automated rotation triggered for Database Migration Ingestion Service Account Key.'
    },
    {
      id: 'evt-aud-1003',
      timestamp: '2026-02-19 11:05:44 UTC',
      actor: 'secops.analyst@akaaltech.com',
      actorRole: 'AUDITOR',
      action: 'BREAK_GLASS_REQUEST_REJECTED',
      resourceType: 'BreakGlassSession',
      resourceId: 'bg-req-99',
      outcome: 'DENIED',
      ipAddress: '172.16.8.90',
      correlationId: 'corr-tx-88192a03',
      details: 'Rejected emergency elevation request due to missing incident ticket reference.'
    },
    {
      id: 'evt-aud-1004',
      timestamp: '2026-02-18 16:30:19 UTC',
      actor: 'system.daemon@akaal.internal',
      actorRole: 'SYSTEM_INTERNAL',
      action: 'MERKLE_TREE_DIGEST_SEALED',
      resourceType: 'AuditLogBatch',
      resourceId: 'batch-2026-02-18',
      outcome: 'SUCCESS',
      ipAddress: '127.0.0.1',
      correlationId: 'corr-tx-88192a04',
      details: 'Computed SHA-256 Merkle root digest over 14,820 audit events.'
    }
  ]);

  // Audit Destinations
  public destinations = signal<AuditDestination[]>([
    {
      id: 'adest-syslog-01',
      name: 'Primary Enterprise RFC-5424 Syslog Collector',
      destinationType: 'SYSLOG',
      endpointUrl: 'syslog-tls.corp.internal:6514',
      format: 'CEF',
      tlsEnforced: true,
      status: 'CONFIGURED',
      createdAt: '2025-08-15'
    },
    {
      id: 'adest-splunk-01',
      name: 'Splunk HEC Enterprise Security Ingestion',
      destinationType: 'SIEM_COLLECTOR',
      endpointUrl: 'https://splunk-hec.corp.internal:8088/services/collector',
      format: 'JSON_STRUCTURED',
      credentialRef: 'vault://secret/siem/splunk-hec-token',
      tlsEnforced: true,
      status: 'CONFIGURED',
      createdAt: '2025-09-20'
    }
  ]);

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
    },
    {
      id: 'ret-02',
      name: 'Transient Validation Sampling Data',
      evidenceClass: 'TEMPORARY_VALIDATION_SAMPLE',
      retentionYears: 1,
      dispositionAction: 'PURGE_CONFIRMED',
      legalHoldExempt: true,
      status: 'ENFORCED'
    }
  ]);

  // Legal Holds
  public legalHolds = signal<LegalHold[]>([
    {
      id: 'hold-01',
      caseId: 'CIV-2026-0819',
      matterName: 'Global Fintech Transaction Audit Investigation',
      custodian: 'Legal & Regulatory Affairs',
      scopeDescription: 'All execution logs, cryptographic hash attestations, and user actions relating to Payment Gateway Workspaces.',
      holdCreatedDate: '2026-01-15',
      heldItemsCount: 1420,
      status: 'ACTIVE'
    }
  ]);

  // Audit Integrity Verifications
  public verifications = signal<AuditIntegrityVerification[]>([
    {
      id: 'vrf-01',
      verificationTimestamp: '2026-02-18 23:59:59 UTC',
      targetPeriod: '2026-02-18 (00:00 - 23:59 UTC)',
      totalEntriesEvaluated: 14820,
      sha256MerkleRootDigest: 'd5b51a5c6893693e5066c06a3501f2f87c10b9f560e29bca5b4512e987c2b3e8',
      verificationResult: 'DIGEST_VERIFIED',
      auditedBy: 'Automated Integrity Daemon (ECDSA Verification)',
      signatureAlgorithm: 'SHA-256 + ECDSA P-384'
    }
  ]);

  // Export Requests
  public exportRequests = signal<AuditExportRequest[]>([
    {
      id: 'exp-01',
      requestedAt: '2026-02-19 12:00:00 UTC',
      requestedBy: 'compliance.lead@akaaltech.com',
      format: 'JSON',
      dateRange: '2026-02-01 to 2026-02-18',
      status: 'COMPLETED',
      downloadSize: '42.8 MB',
      recordCount: 42190
    }
  ]);

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
