/**
 * AKAAL Administration — 5.2 People & Access and 5.3 Governance Centre Unit Tests
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { PeopleService } from './services/people.service';
import { GovernanceService } from './services/governance.service';

describe('5.2 People & Access Service & Workflows', () => {
  let peopleService: PeopleService;

  beforeEach(() => {
    peopleService = new PeopleService();
  });

  it('should initialize with standard seed users, teams, and service accounts', () => {
    expect(peopleService.users().length).toBeGreaterThanOrEqual(3);
    expect(peopleService.teams().length).toBeGreaterThanOrEqual(2);
    expect(peopleService.serviceAccounts().length).toBeGreaterThanOrEqual(2);
  });

  it('should create and update a user principal', () => {
    const newUser = peopleService.createUser({
      name: 'Test Engineer',
      email: 'test.eng@akaaltech.corp',
      title: 'DevOps Lead',
      department: 'Infrastructure',
      type: 'EMPLOYEE',
      status: 'ACTIVE'
    });

    expect(newUser.id).toBeDefined();
    expect(peopleService.users().find(u => u.id === newUser.id)).toBeDefined();

    peopleService.updateUser(newUser.id, { status: 'SUSPENDED' });
    const updated = peopleService.users().find(u => u.id === newUser.id);
    expect(updated?.status).toBe('SUSPENDED');
  });

  it('should create and update teams', () => {
    const newTeam = peopleService.createTeam({
      name: 'Observability Squad',
      code: 'TEAM-OBS',
      description: 'Platform Telemetry',
      leadOwnerName: 'Aalok Ladwa',
      leadOwnerEmail: 'aalok.ladwa@akaaltech.internal'
    });

    expect(newTeam.id).toBeDefined();
    expect(peopleService.teams().find(t => t.id === newTeam.id)).toBeDefined();

    peopleService.updateTeam(newTeam.id, { description: 'Updated Telemetry Squad' });
    expect(peopleService.teams().find(t => t.id === newTeam.id)?.description).toBe('Updated Telemetry Squad');
  });

  it('should create, update and list machine service accounts', () => {
    const sa = peopleService.createServiceAccount({
      name: 'Prometheus Scraper Agent',
      ownerEmail: 'metrics@akaaltech.corp',
      targetScope: 'Global Monitoring'
    });

    expect(sa.id).toBeDefined();
    expect(sa.clientId).toContain('akaal-sa-');

    peopleService.updateServiceAccount(sa.id, { tokenExpiryDays: 180 });
    expect(peopleService.serviceAccounts().find(s => s.id === sa.id)?.tokenExpiryDays).toBe(180);
  });

  it('should manage roles and access assignments', () => {
    const role = peopleService.createRole({
      name: 'Custom Auditor',
      code: 'ROLE-CUSTOM-AUDITOR',
      domainScope: 'GLOBAL',
      permissions: ['akaal:audit:read']
    });

    expect(role.id).toBeDefined();

    const asg = peopleService.assignAccess({
      principalId: 'usr-aalok-01',
      principalName: 'Aalok Ladwa',
      roleId: role.id,
      roleName: role.name
    });

    expect(asg.id).toBeDefined();
    expect(peopleService.assignments().find(a => a.id === asg.id)).toBeDefined();
  });

  it('should handle JIT access request workflow', () => {
    const req = peopleService.requestJit({
      requesterName: 'Aalok Ladwa',
      requesterEmail: 'aalok.ladwa@akaaltech.internal',
      targetRoleName: 'Enterprise Platform Administrator',
      durationHours: 3,
      justification: 'Emergency DB Schema Migration'
    });

    expect(req.id).toBeDefined();
    expect(req.status).toBe('PENDING_APPROVAL');
    expect(peopleService.jitRequests().find(j => j.id === req.id)).toBeDefined();
  });

  it('should terminate active sessions', () => {
    const activeSession = peopleService.sessions()[0];
    expect(activeSession).toBeDefined();

    peopleService.terminateSession(activeSession.id);
    expect(peopleService.sessions().find(s => s.id === activeSession.id)?.status).toBe('TERMINATED');
  });

  it('should create access review campaigns', () => {
    const rev = peopleService.createAccessReview({
      name: 'Q3 Privileged Access Attestation',
      scopeType: 'ROLE_TIER',
      scopeName: 'All Privileged Roles'
    });

    expect(rev.id).toBeDefined();
    expect(rev.status).toBe('IN_PROGRESS');
  });
});

describe('5.3 Governance Centre Service & Workflows', () => {
  let govService: GovernanceService;

  beforeEach(() => {
    govService = new GovernanceService();
  });

  it('should initialize with default governance policies, approval chains, and SoD rules', () => {
    expect(govService.policies().length).toBeGreaterThanOrEqual(3);
    expect(govService.approvalChains().length).toBeGreaterThanOrEqual(2);
    expect(govService.approverGroups().length).toBeGreaterThanOrEqual(2);
    expect(govService.sodRules().length).toBeGreaterThanOrEqual(2);
    expect(govService.privilegedOps().length).toBeGreaterThanOrEqual(3);
    expect(govService.waivers().length).toBeGreaterThanOrEqual(1);
    expect(govService.breakGlass().status).toBe('ESCROW_ARMED');
  });

  it('should create and update governance policies', () => {
    const policy = govService.createPolicy({
      name: 'Row-Level Security Enforcement',
      code: 'POL-RLS-MANDATORY',
      category: 'DATA_CLASSIFICATION',
      enforcementLevel: 'MANDATORY_BLOCKING'
    });

    expect(policy.id).toBeDefined();
    expect(govService.policies().find(p => p.id === policy.id)).toBeDefined();

    govService.updatePolicy(policy.id, { enforcementLevel: 'AUDIT_WARNING' });
    expect(govService.policies().find(p => p.id === policy.id)?.enforcementLevel).toBe('AUDIT_WARNING');
  });

  it('should simulate policy evaluation against hypothetical targets', () => {
    const sim = govService.simulatePolicy('POL-MASK-001', 'arn:akaal:pg:database/prod_analytics', 'akaal:db:execute');
    expect(sim.evaluationDecision).toBe('PERMITTED');
    expect(sim.reasons.length).toBeGreaterThan(0);
  });

  it('should manage multi-stage approval chains and approver groups', () => {
    const chain = govService.createApprovalChain({
      name: 'Hotfix Deployment Quorum',
      code: 'CHAIN-HOTFIX',
      quorumApproversRequired: 2
    });

    expect(chain.id).toBeDefined();

    const grp = govService.createApproverGroup({
      name: 'Emergency Hotfix Signers',
      code: 'GRP-HOTFIX-SIGNERS',
      quorumThreshold: 2
    });

    expect(grp.id).toBeDefined();
  });

  it('should enforce Separation of Duties rules', () => {
    const sod = govService.createSodRule({
      name: 'DBA vs Financial Signer Conflict',
      code: 'SOD-DBA-FINANCE',
      incompatibleRoleA: 'ROLE-LEAD-DBA',
      incompatibleRoleB: 'ROLE-FINANCIAL-SIGNER'
    });

    expect(sod.id).toBeDefined();
    expect(sod.enforcementMode).toBe('PREVENTATIVE_BLOCKING');
  });

  it('should create and track governance waivers', () => {
    const waiver = govService.createWaiver({
      targetPolicy: 'POL-MASK-001',
      targetResource: 'Benchmark Cluster',
      justification: 'Quarterly load testing'
    });

    expect(waiver.id).toBeDefined();
    expect(waiver.status).toBe('ACTIVE');
    expect(govService.waivers().find(w => w.id === waiver.id)).toBeDefined();
  });
});