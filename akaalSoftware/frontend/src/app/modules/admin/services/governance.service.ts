/**
 * AKAAL Administration — 5.3 Governance Centre Reactive Signals Store
 */

import { Injectable, signal } from '@angular/core';
import {
  GovernancePolicy,
  PolicySimulationResult,
  ApprovalChain,
  ApproverGroup,
  MakerCheckerPolicy,
  SodRule,
  PrivilegedOperationConfig,
  GovernanceWaiver,
  BreakGlassConfig,
  GovernanceAuditRecord
} from '../models/governance.models';

@Injectable({
  providedIn: 'root'
})
export class GovernanceService {
  // 1. Policies
  public policies = signal<GovernancePolicy[]>([
    {
      id: 'pol-data-masking',
      name: 'Mandatory Non-Production Data Masking Policy',
      code: 'POL-MASK-001',
      description: 'Enforces irreversible pseudonymization and tokenization on all non-production database targets prior to pipeline execution.',
      category: 'DATA_CLASSIFICATION',
      enforcementLevel: 'MANDATORY_BLOCKING',
      targetScope: 'GLOBAL',
      boundResourcesCount: 4,
      updatedAt: '2026-03-01T00:00:00Z',
      updatedBy: 'SecOps Governance Authority'
    },
    {
      id: 'pol-schema-freeze',
      name: 'Fiscal Quarter-End Schema Alteration Freeze',
      code: 'POL-FREEZE-Q1',
      description: 'Blocks DDL mutation and schema remapping during fiscal close periods unless granted an approved governance waiver.',
      category: 'SCHEMA_FREEZE',
      enforcementLevel: 'MANDATORY_BLOCKING',
      targetScope: 'ORGANIZATION',
      boundResourcesCount: 1,
      updatedAt: '2026-03-05T00:00:00Z',
      updatedBy: 'Chief Risk Officer'
    },
    {
      id: 'pol-kms-baseline',
      name: 'KMS HSM Customer-Managed Key Mandate',
      code: 'POL-KMS-HSM',
      description: 'Mandates customer-managed AWS KMS HSM keys with automatic annual envelope key rotation for all encrypted replication volumes.',
      category: 'ENCRYPTION_KEY',
      enforcementLevel: 'MANDATORY_BLOCKING',
      targetScope: 'GLOBAL',
      boundResourcesCount: 8,
      updatedAt: '2026-01-10T00:00:00Z',
      updatedBy: 'SecOps Governance Authority'
    }
  ]);

  // 2. Approval Chains
  public approvalChains = signal<ApprovalChain[]>([
    {
      id: 'chain-prod-cutover',
      name: 'Production Migration Cutover Quorum Chain',
      code: 'CHAIN-PROD-CUTOVER',
      description: 'Multi-stage approval workflow requiring sign-off from Migration Lead, Lead DBA, and SecOps Incident Commander.',
      targetOperation: 'Live Production Cutover',
      stagesCount: 3,
      quorumApproversRequired: 3,
      timeoutHours: 12,
      status: 'ACTIVE',
      createdAt: '2026-01-10T00:00:00Z'
    },
    {
      id: 'chain-schema-destructive',
      name: 'Destructive DDL Drop / Truncate Approval',
      code: 'CHAIN-DESTRUCTIVE-DDL',
      description: 'Two-person dual control approval chain for table drop, column drop, or irreversible index reconstruction.',
      targetOperation: 'Destructive Schema Execution',
      stagesCount: 2,
      quorumApproversRequired: 2,
      timeoutHours: 6,
      status: 'ACTIVE',
      createdAt: '2026-01-20T00:00:00Z'
    }
  ]);

  // 3. Approver Groups
  public approverGroups = signal<ApproverGroup[]>([
    {
      id: 'grp-secops-signoff',
      name: 'SecOps Incident Commanders',
      code: 'GRP-SECOPS-COMMANDERS',
      description: 'Designated incident commanders authorized to approve emergency elevation, break-glass escrow, and production cutover.',
      eligibleApprovers: [
        { name: 'Sarah Jenkins', email: 's.jenkins@akaaltech.corp', title: 'Staff Security Engineer' },
        { name: 'Marcus Vance', email: 'm.vance@akaaltech.corp', title: 'Director of Cyber Defense' }
      ],
      quorumThreshold: 1,
      status: 'ACTIVE',
      createdAt: '2026-01-05T00:00:00Z'
    },
    {
      id: 'grp-dba-leads',
      name: 'Database Principal Stewards',
      code: 'GRP-DBA-STEWARDS',
      description: 'Principal database architects authorized to approve schema migration plans and irreversible DDL alters.',
      eligibleApprovers: [
        { name: 'Aalok Ladwa', email: 'aalok.ladwa@akaaltech.internal', title: 'Principal Lead Architect' },
        { name: 'Devon Vance', email: 'd.vance@akaaltech.corp', title: 'Senior Migration Specialist' }
      ],
      quorumThreshold: 1,
      status: 'ACTIVE',
      createdAt: '2026-01-10T00:00:00Z'
    }
  ]);

  // 4. Maker / Checker Controls
  public makerCheckerPolicies = signal<MakerCheckerPolicy[]>([
    {
      id: 'mc-migration-exec',
      entityType: 'MIGRATION_EXECUTION',
      dualControlEnforced: true,
      selfApprovalProhibited: true,
      quorumRequirement: 2,
      auditAttestationRequired: true,
      updatedAt: '2026-03-01T00:00:00Z',
      updatedBy: 'Platform Administrator'
    },
    {
      id: 'mc-schema-alter',
      entityType: 'SCHEMA_ALTERATION',
      dualControlEnforced: true,
      selfApprovalProhibited: true,
      quorumRequirement: 2,
      auditAttestationRequired: true,
      updatedAt: '2026-03-01T00:00:00Z',
      updatedBy: 'Platform Administrator'
    },
    {
      id: 'mc-secret-rotate',
      entityType: 'SECRET_ROTATION',
      dualControlEnforced: true,
      selfApprovalProhibited: true,
      quorumRequirement: 2,
      auditAttestationRequired: true,
      updatedAt: '2026-03-01T00:00:00Z',
      updatedBy: 'Platform Administrator'
    }
  ]);

  // 5. Separation of Duties (SoD) Rules
  public sodRules = signal<SodRule[]>([
    {
      id: 'sod-rule-01',
      code: 'SOD-DEV-PROD-SPLIT',
      name: 'Development Authoring vs. Production Execution',
      description: 'Principals authoring migration configuration mapping cannot unilaterally trigger live production data cutover.',
      incompatibleRoleA: 'ROLE-MIGRATION-ARCHITECT',
      incompatibleRoleB: 'ROLE-PLATFORM-ADMIN',
      enforcementMode: 'PREVENTATIVE_BLOCKING',
      activeViolationsCount: 1,
      createdAt: '2026-01-10T00:00:00Z'
    },
    {
      id: 'sod-rule-02',
      code: 'SOD-AUDIT-OPERATOR',
      name: 'Assurance Auditor vs. Operational Admin',
      description: 'Independent auditors cannot possess administrative mutation rights across governance rules or policy definitions.',
      incompatibleRoleA: 'ROLE-COMPLIANCE-AUDITOR',
      incompatibleRoleB: 'ROLE-PLATFORM-ADMIN',
      enforcementMode: 'PREVENTATIVE_BLOCKING',
      activeViolationsCount: 0,
      createdAt: '2026-01-15T00:00:00Z'
    }
  ]);

  // 6. Privileged Operations
  public privilegedOperations = signal<PrivilegedOperationConfig[]>([
    {
      id: 'priv-op-01',
      operationCode: 'HSM_MASTER_KEY_DESTRUCTION',
      operationName: 'Cryptographic HSM Key Decommission',
      riskTier: 'CRITICAL_HSM',
      approvalChainName: 'Production Migration Cutover Quorum Chain',
      fourEyesRequired: true,
      breakGlassEligible: false,
      status: 'PROTECTED'
    },
    {
      id: 'priv-op-02',
      operationCode: 'DATABASE_LIVE_CUTOVER',
      operationName: 'Live Transactional Ledger Switchover',
      riskTier: 'HIGH_TRANSACTIONAL',
      approvalChainName: 'Production Migration Cutover Quorum Chain',
      fourEyesRequired: true,
      breakGlassEligible: true,
      status: 'PROTECTED'
    },
    {
      id: 'priv-op-03',
      operationCode: 'SCHEMA_ALTER_DROP_COLUMN',
      operationName: 'Destructive Column Deletion',
      riskTier: 'ELEVATED_SCHEMA',
      approvalChainName: 'Destructive DDL Drop / Truncate Approval',
      fourEyesRequired: true,
      breakGlassEligible: false,
      status: 'RESTRICTED'
    }
  ]);

  // 7. Exceptions & Waivers
  public waivers = signal<GovernanceWaiver[]>([
    {
      id: 'waiver-2026-01',
      waiverCode: 'WAIVER-MASK-TEMP-01',
      justification: 'Staging benchmark performance testing requiring representative synthetic cardinality dataset.',
      targetPolicy: 'POL-MASK-001 (Mandatory Non-Production Data Masking Policy)',
      targetResource: 'Development Tier Cluster (ws-core-banking)',
      beneficiaryPrincipal: 'Devon Vance',
      approvedBy: 'Sarah Jenkins (SecOps)',
      validFrom: '2026-03-01T00:00:00Z',
      validUntil: '2026-03-31T23:59:59Z',
      status: 'ACTIVE'
    }
  ]);

  // 8. Break-Glass Configuration
  public breakGlass = signal<BreakGlassConfig>({
    id: 'bg-config-root',
    status: 'ESCROW_ARMED',
    emergencyEscrowKeyId: 'CYBER-VAULT-ESCROW-ALPHA-01',
    primaryIncidentCommander: 'SecOps Incident Commander (Sarah Jenkins)',
    secondaryIncidentCommander: 'Chief Security Officer',
    autoRevokeHours: 4,
    lastDrillDate: '2026-02-15T09:00:00Z',
    totalHistoricalActivations: 0
  });

  // 9. Governance Audit History
  public governanceAudit = signal<GovernanceAuditRecord[]>([
    {
      id: 'gov-aud-01',
      eventType: 'POLICY_EVALUATION',
      principalName: 'Devon Vance',
      principalEmail: 'd.vance@akaaltech.corp',
      targetResource: 'POL-MASK-001 / Staging Cluster',
      decision: 'WAIVED',
      timestamp: '2026-03-01T00:00:00Z',
      details: 'Active waiver WAIVER-MASK-TEMP-01 applied by SecOps authority.'
    },
    {
      id: 'gov-aud-02',
      eventType: 'SOD_ENFORCEMENT',
      principalName: 'Devon Vance',
      principalEmail: 'd.vance@akaaltech.corp',
      targetResource: 'ROLE-PLATFORM-ADMIN assignment attempt',
      decision: 'ENFORCED',
      timestamp: '2026-03-01T11:20:00Z',
      details: 'Preventative block: Principal already possesses incompatible ROLE-MIGRATION-ARCHITECT.'
    },
    {
      id: 'gov-aud-03',
      eventType: 'MAKER_CHECKER_QUORUM',
      principalName: 'Aalok Ladwa',
      principalEmail: 'aalok.ladwa@akaaltech.internal',
      targetResource: 'Production Cutover Barrier #409',
      decision: 'APPROVED',
      timestamp: '2026-03-05T16:45:00Z',
      details: 'Quorum reached: 2 of 2 required signatures validated.'
    }
  ]);

  // Aliases for component convenience
  public privilegedOps = this.privilegedOperations;
  public auditHistory = this.governanceAudit;

  // ==========================================================================
  // MUTATION METHODS
  // ==========================================================================

  public simulatePolicy(policyCode: string, targetResource: string, action: string): PolicySimulationResult {
    return {
      policyCode,
      targetResource,
      action,
      evaluationDecision: 'PERMITTED',
      reasons: [
        `Target resource '${targetResource}' complies with encryption baseline.`,
        `Principal action '${action}' validated under authorized security scope.`,
        `No conflicting Separation of Duties (SoD) violations triggered.`
      ],
      evaluatedAt: new Date().toISOString()
    };
  }

  public createPolicy(data: Partial<GovernancePolicy>): GovernancePolicy {
    const newPolicy: GovernancePolicy = {
      id: 'pol-' + Date.now().toString().slice(-6),
      name: data.name || '',
      code: data.code || 'POL-CUSTOM',
      description: data.description || '',
      category: data.category || 'DATA_CLASSIFICATION',
      enforcementLevel: data.enforcementLevel || 'MANDATORY_BLOCKING',
      targetScope: data.targetScope || 'GLOBAL',
      boundResourcesCount: 1,
      updatedAt: new Date().toISOString(),
      updatedBy: 'Platform Administrator'
    };
    this.policies.update(list => [newPolicy, ...list]);
    return newPolicy;
  }

  public updatePolicy(id: string, updates: Partial<GovernancePolicy>): void {
    this.policies.update(list => list.map(p => p.id === id ? { ...p, ...updates, updatedAt: new Date().toISOString() } : p));
  }

  public createApprovalChain(data: Partial<ApprovalChain>): ApprovalChain {
    const newChain: ApprovalChain = {
      id: 'chain-' + Date.now().toString().slice(-6),
      name: data.name || '',
      code: data.code || 'CHAIN-CUSTOM',
      description: data.description || '',
      targetOperation: data.targetOperation || 'Production Cutover',
      stagesCount: data.stagesCount || 2,
      quorumApproversRequired: data.quorumApproversRequired || 2,
      timeoutHours: data.timeoutHours || 8,
      status: 'ACTIVE',
      createdAt: new Date().toISOString()
    };
    this.approvalChains.update(list => [newChain, ...list]);
    return newChain;
  }

  public updateApprovalChain(id: string, updates: Partial<ApprovalChain>): void {
    this.approvalChains.update(list => list.map(c => c.id === id ? { ...c, ...updates } : c));
  }

  public createApproverGroup(data: Partial<ApproverGroup>): ApproverGroup {
    const newGroup: ApproverGroup = {
      id: 'grp-' + Date.now().toString().slice(-6),
      name: data.name || '',
      code: data.code || 'GRP-CUSTOM',
      description: data.description || '',
      eligibleApprovers: data.eligibleApprovers || [{ name: 'Aalok Ladwa', email: 'aalok.ladwa@akaaltech.internal', title: 'Principal Architect' }],
      quorumThreshold: data.quorumThreshold || 1,
      status: 'ACTIVE',
      createdAt: new Date().toISOString()
    };
    this.approverGroups.update(list => [newGroup, ...list]);
    return newGroup;
  }

  public updateApproverGroup(id: string, updates: Partial<ApproverGroup>): void {
    this.approverGroups.update(list => list.map(g => g.id === id ? { ...g, ...updates } : g));
  }

  public updateMakerCheckerPolicy(id: string, updates: Partial<MakerCheckerPolicy>): void {
    this.makerCheckerPolicies.update(list => list.map(m => m.id === id ? { ...m, ...updates, updatedAt: new Date().toISOString() } : m));
  }

  public createSodRule(data: Partial<SodRule>): SodRule {
    const newRule: SodRule = {
      id: 'sod-' + Date.now().toString().slice(-6),
      code: data.code || 'SOD-CUSTOM',
      name: data.name || '',
      description: data.description || '',
      incompatibleRoleA: data.incompatibleRoleA || 'ROLE-MIGRATION-ARCHITECT',
      incompatibleRoleB: data.incompatibleRoleB || 'ROLE-PLATFORM-ADMIN',
      enforcementMode: data.enforcementMode || 'PREVENTATIVE_BLOCKING',
      activeViolationsCount: 0,
      createdAt: new Date().toISOString()
    };
    this.sodRules.update(list => [newRule, ...list]);
    return newRule;
  }

  public updateSodRule(id: string, updates: Partial<SodRule>): void {
    this.sodRules.update(list => list.map(r => r.id === id ? { ...r, ...updates } : r));
  }

  public createWaiver(data: Partial<GovernanceWaiver>): GovernanceWaiver {
    const newWaiver: GovernanceWaiver = {
      id: 'waiver-' + Date.now().toString().slice(-6),
      waiverCode: 'WAIVER-' + Date.now().toString().slice(-4),
      justification: data.justification || '',
      targetPolicy: data.targetPolicy || 'POL-MASK-001',
      targetResource: data.targetResource || 'Global Scope',
      beneficiaryPrincipal: data.beneficiaryPrincipal || 'Operator',
      approvedBy: 'Sarah Jenkins (SecOps)',
      validFrom: new Date().toISOString(),
      validUntil: data.validUntil || '2026-06-30T23:59:59Z',
      status: 'ACTIVE'
    };
    this.waivers.update(list => [newWaiver, ...list]);
    return newWaiver;
  }

  public updateBreakGlassConfig(updates: Partial<BreakGlassConfig>): void {
    this.breakGlass.update(current => ({ ...current, ...updates }));
  }
}
