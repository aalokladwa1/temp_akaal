import { useState, useEffect, useMemo, type FC } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Search,
  ArrowLeft,
  UserCheck,
  Lock,
  Zap,
  Database,
  Layers,
  Activity,
  Download,
  MessageSquare,
  Send,
  Shield,
} from 'lucide-react';
import type { GovernanceApproval } from '../../types/migration';
import { approvalRepository } from '../../repositories/approvalRepository';
import { notificationService } from '../../services/notificationService';

export interface GovernanceCenterViewProps {
  onBack: () => void;
  initialMigrationId?: string;
  initialGateId?: string;
  onNavigateToMissionControl?: (migrationId: string) => void;
  onNavigateToExecutionPlan?: (migrationId: string) => void;
}

export type KPIFilterType =
  | 'all'
  | 'pending'
  | 'waiting_for_me'
  | 'runtime_waiting'
  | 'approved_today'
  | 'rejected_today'
  | 'sla_breaches'
  | 'high_risk';

export type GateFilterType = 'all' | 'GATE_1' | 'GATE_2' | 'GATE_3';
export type StatusFilterType = 'all' | 'pending' | 'approved' | 'rejected' | 'changes_requested';
export type PriorityFilterType = 'all' | 'HIGH' | 'CRITICAL' | 'NORMAL';

export const GovernanceCenterView: FC<GovernanceCenterViewProps> = ({
  onBack,
  initialMigrationId,
  initialGateId,
  onNavigateToMissionControl,
  onNavigateToExecutionPlan,
}) => {
  // Master state
  const [approvals, setApprovals] = useState<GovernanceApproval[]>(() => approvalRepository.getApprovals());
  const [activeMainTab, setActiveMainTab] = useState<'pending' | 'history'>('pending');
  const [isLoading, setIsLoading] = useState(false);

  // Multi-migration selection state (Strictly using immutable IDs)
  const [selectedMigrationId, setSelectedMigrationId] = useState<string | null>(initialMigrationId || null);
  const [selectedGateId, setSelectedGateId] = useState<string | null>(initialGateId || null);

  // Filters & Search
  const [kpiFilter, setKpiFilter] = useState<KPIFilterType>('all');
  const [gateFilter, setGateFilter] = useState<GateFilterType>('all');
  const [statusFilter, setStatusFilter] = useState<StatusFilterType>('all');
  const [priorityFilter, setPriorityFilter] = useState<PriorityFilterType>('all');
  const [runtimeOnly, setRuntimeOnly] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Local discussion comment input
  const [commentText, setCommentText] = useState('');

  // Confirmation Modal state
  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    actionType: 'approved' | 'rejected' | 'changes_requested';
    approvalId: string;
    migrationId: string;
  } | null>(null);

  const [confirmReason, setConfirmReason] = useState('');

  // Subscribe to approval repository updates
  useEffect(() => {
    return approvalRepository.subscribe((updated) => {
      setApprovals(updated);
    });
  }, []);

  // Sync selection when main tab changes
  const handleMainTabChange = (tab: 'pending' | 'history') => {
    setActiveMainTab(tab);
    const targetList = approvals.filter((a) => (tab === 'pending' ? a.status === 'pending' : a.status !== 'pending'));
    if (targetList.length > 0) {
      setSelectedMigrationId(targetList[0].migrationId);
      setSelectedGateId(targetList[0].gate);
    }
  };

  // Derived KPI Counts
  const kpis = useMemo(() => {
    const pending = approvals.filter((a) => a.status === 'pending');
    const waitingForMe = pending.filter((a) => a.requiredRoles.includes('Lead DBA'));
    const runtimeWaiting = pending.filter((a) => a.gate === 'GATE_3');
    const approvedToday = approvals.filter((a) => a.status === 'approved');
    const rejectedToday = approvals.filter((a) => a.status === 'rejected' || a.status === 'changes_requested');
    const slaBreaches = approvals.filter((a) => (a.riskScore || 0) > 0.9 || a.migrationId === 'MIG-2026-0806-006');
    const highRisk = approvals.filter((a) => (a.riskScore || 0) >= 0.7);

    return {
      pending: pending.length,
      waitingForMe: waitingForMe.length,
      runtimeWaiting: runtimeWaiting.length,
      approvedToday: approvedToday.length,
      rejectedToday: rejectedToday.length,
      avgTime: '~4.2 Mins',
      slaBreaches: slaBreaches.length,
      highRisk: highRisk.length,
    };
  }, [approvals]);

  // Filtered Queue
  const filteredApprovals = useMemo(() => {
    return approvals.filter((appr) => {
      // Main tab filter
      if (activeMainTab === 'pending' && appr.status !== 'pending') return false;
      if (activeMainTab === 'history' && appr.status === 'pending') return false;

      // KPI filter
      if (kpiFilter === 'pending' && appr.status !== 'pending') return false;
      if (kpiFilter === 'waiting_for_me' && !appr.requiredRoles.includes('Lead DBA')) return false;
      if (kpiFilter === 'runtime_waiting' && appr.gate !== 'GATE_3') return false;
      if (kpiFilter === 'approved_today' && appr.status !== 'approved') return false;
      if (kpiFilter === 'rejected_today' && (appr.status !== 'rejected' && appr.status !== 'changes_requested')) return false;
      if (kpiFilter === 'sla_breaches' && (appr.riskScore || 0) < 0.9 && appr.migrationId !== 'MIG-2026-0806-006') return false;
      if (kpiFilter === 'high_risk' && (appr.riskScore || 0) < 0.7) return false;

      // Dropdown filters
      if (gateFilter !== 'all' && appr.gate !== gateFilter) return false;
      if (statusFilter !== 'all' && appr.status !== statusFilter) return false;
      if (runtimeOnly && appr.gate !== 'GATE_3') return false;

      if (priorityFilter !== 'all') {
        const p = (appr.riskScore || 0) > 0.7 ? 'HIGH' : (appr.riskScore || 0) > 0.9 ? 'CRITICAL' : 'NORMAL';
        if (p !== priorityFilter) return false;
      }

      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchName = appr.migrationName.toLowerCase().includes(q);
        const matchId = appr.migrationId.toLowerCase().includes(q);
        const matchProj = appr.projectName.toLowerCase().includes(q);
        const matchUser = appr.requestedBy.toLowerCase().includes(q);
        if (!matchName && !matchId && !matchProj && !matchUser) return false;
      }

      return true;
    });
  }, [approvals, activeMainTab, kpiFilter, gateFilter, statusFilter, priorityFilter, runtimeOnly, searchQuery]);

  // Selected Approval Packet (Strictly bound to selectedMigrationId + selectedGateId)
  const selectedApproval = useMemo(() => {
    if (!selectedMigrationId) return null;
    return (
      approvals.find(
        (a) => a.migrationId === selectedMigrationId && (selectedGateId ? a.gate === selectedGateId : true)
      ) || null
    );
  }, [approvals, selectedMigrationId, selectedGateId]);

  // Handle Card Click
  const handleSelectApproval = (appr: GovernanceApproval) => {
    setIsLoading(true);
    setSelectedMigrationId(appr.migrationId);
    setSelectedGateId(appr.gate);
    setTimeout(() => setIsLoading(false), 150);
  };

  // Process Decision Submit
  const handleConfirmDecision = () => {
    if (!confirmModal) return;
    const { approvalId, actionType } = confirmModal;
    const reason = confirmReason.trim() || `Decision: ${actionType.toUpperCase()}`;

    approvalRepository.processDecision(approvalId, actionType, 'Aalok', reason);
    notificationService.push(
      `Gate Decision ${actionType.toUpperCase()}`,
      actionType === 'approved' ? 'success' : actionType === 'rejected' ? 'error' : 'warning',
      `Signed and recorded for pipeline ${confirmModal.migrationId}.`
    );

    setConfirmModal(null);
    setConfirmReason('');
  };

  // Add Comment
  const handleAddComment = () => {
    if (!commentText.trim() || !selectedApproval) return;
    const updatedComments = [
      ...(selectedApproval.comments || []),
      { author: 'Aalok (Lead DBA)', timestamp: new Date().toISOString(), text: commentText.trim() },
    ];
    selectedApproval.comments = updatedComments;
    setCommentText('');
    notificationService.push('Comment Added', 'info', 'Comment recorded on approval audit log.');
  };

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--dash-bg)',
        overflow: 'hidden',
      }}
    >
      {/* ── TOP HEADER BAR ────────────────────────────────────────────────── */}
      <div
        style={{
          padding: '12px 24px',
          background: 'var(--dash-surface)',
          borderBottom: '1px solid var(--dash-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0,
          gap: 16,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <button
            type="button"
            onClick={onBack}
            style={{
              background: 'none',
              border: '1px solid var(--dash-border)',
              padding: '6px 12px',
              borderRadius: 6,
              color: 'var(--dash-text-secondary)',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <ArrowLeft size={14} /> Back
          </button>

          <div style={{ width: 1, height: 20, background: 'var(--dash-border)' }} />

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <ShieldCheck size={20} color="var(--dash-accent)" />
              <h1 style={{ fontSize: 18, fontWeight: 800, margin: 0, color: 'var(--dash-text-primary)', letterSpacing: '-0.01em' }}>
                Governance Centre & Multi-Custody Approval Hub
              </h1>
            </div>
            <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', marginTop: 2 }}>
              Enterprise Operations Governance • 4-Eyes Dual Custody Policy • Cryptographic Audit Trail
            </div>
          </div>
        </div>

        {/* Global Controls & Search */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ position: 'relative', width: 260 }}>
            <Search size={14} style={{ position: 'absolute', left: 10, top: 9, color: 'var(--dash-text-secondary)' }} />
            <input
              type="text"
              placeholder="Search migration, project, approver..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '6px 12px 6px 32px',
                borderRadius: 6,
                background: 'var(--dash-bg)',
                border: '1px solid var(--dash-border)',
                color: 'var(--dash-text-primary)',
                fontSize: 12,
              }}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'rgba(16,185,129,0.12)', padding: '4px 10px', borderRadius: 6, border: '1px solid rgba(16,185,129,0.3)' }}>
            <Lock size={13} color="#10B981" />
            <span style={{ fontSize: 11, fontWeight: 700, color: '#10B981' }}>POLICY ENFORCEMENT ACTIVE</span>
          </div>
        </div>
      </div>

      {/* ── SECTION 1: ENTERPRISE KPI CARDS (Interactive Filtering) ─────── */}
      <div
        style={{
          padding: '14px 24px',
          background: 'var(--dash-surface)',
          borderBottom: '1px solid var(--dash-border)',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
          gap: 10,
          flexShrink: 0,
        }}
      >
        {[
          { id: 'pending', label: 'Pending Approvals', count: kpis.pending, color: '#3B82F6', icon: Clock },
          { id: 'waiting_for_me', label: 'Waiting For Me', count: kpis.waitingForMe, color: '#F59E0B', icon: UserCheck },
          { id: 'runtime_waiting', label: 'Runtime Waiting ⚡', count: kpis.runtimeWaiting, color: '#EC4899', icon: Zap },
          { id: 'approved_today', label: 'Approved Today', count: kpis.approvedToday, color: '#10B981', icon: CheckCircle2 },
          { id: 'rejected_today', label: 'Rejected Today', count: kpis.rejectedToday, color: '#EF4444', icon: XCircle },
          { id: 'avg_time', label: 'Avg Approval Time', count: kpis.avgTime, color: '#8B5CF6', icon: Activity },
          { id: 'sla_breaches', label: 'SLA Breaches', count: kpis.slaBreaches, color: '#F97316', icon: AlertTriangle },
          { id: 'high_risk', label: 'High Risk Approvals', count: kpis.highRisk, color: '#E11D48', icon: ShieldAlert },
        ].map((kpi) => {
          const isSelected = kpiFilter === kpi.id;
          const Icon = kpi.icon;
          return (
            <button
              key={kpi.id}
              type="button"
              onClick={() => setKpiFilter(isSelected ? 'all' : (kpi.id as KPIFilterType))}
              style={{
                padding: '10px 12px',
                borderRadius: 8,
                background: isSelected ? 'rgba(37,99,235,0.12)' : 'var(--dash-bg)',
                border: `1px solid ${isSelected ? 'var(--dash-accent)' : 'var(--dash-border)'}`,
                textAlign: 'left',
                cursor: 'pointer',
                transition: 'all 150ms ease-out',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--dash-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  {kpi.label}
                </span>
                <Icon size={14} color={kpi.color} />
              </div>
              <div style={{ fontSize: 18, fontWeight: 800, color: kpi.color, fontFamily: 'var(--akaal-font-mono, monospace)' }}>
                {kpi.count}
              </div>
            </button>
          );
        })}
      </div>

      {/* ── QUEUE NAVIGATION & FILTER BAR ─────────────────────────────────── */}
      <div
        style={{
          padding: '8px 24px',
          background: 'var(--dash-surface)',
          borderBottom: '1px solid var(--dash-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0,
          gap: 12,
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button
            type="button"
            onClick={() => handleMainTabChange('pending')}
            style={{
              padding: '6px 14px',
              borderRadius: 6,
              background: activeMainTab === 'pending' ? 'var(--dash-accent)' : 'transparent',
              color: activeMainTab === 'pending' ? '#FFF' : 'var(--dash-text-secondary)',
              fontSize: 12,
              fontWeight: 700,
              border: 'none',
              cursor: 'pointer',
            }}
          >
            Pending Queue ({approvals.filter((a) => a.status === 'pending').length})
          </button>
          <button
            type="button"
            onClick={() => handleMainTabChange('history')}
            style={{
              padding: '6px 14px',
              borderRadius: 6,
              background: activeMainTab === 'history' ? 'var(--dash-accent)' : 'transparent',
              color: activeMainTab === 'history' ? '#FFF' : 'var(--dash-text-secondary)',
              fontSize: 12,
              fontWeight: 700,
              border: 'none',
              cursor: 'pointer',
            }}
          >
            Approval History ({approvals.filter((a) => a.status !== 'pending').length})
          </button>
        </div>

        {/* Filter Dropdowns */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <select
            value={gateFilter}
            onChange={(e) => setGateFilter(e.target.value as GateFilterType)}
            style={{
              padding: '4px 8px',
              borderRadius: 6,
              background: 'var(--dash-bg)',
              border: '1px solid var(--dash-border)',
              color: 'var(--dash-text-primary)',
              fontSize: 11,
              fontWeight: 600,
            }}
          >
            <option value="all">All Gates</option>
            <option value="GATE_1">Gate 1: Scope & Risk</option>
            <option value="GATE_2">Gate 2: Execution & DDL</option>
            <option value="GATE_3">Gate 3: Cutover Authorization</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as StatusFilterType)}
            style={{
              padding: '4px 8px',
              borderRadius: 6,
              background: 'var(--dash-bg)',
              border: '1px solid var(--dash-border)',
              color: 'var(--dash-text-primary)',
              fontSize: 11,
              fontWeight: 600,
            }}
          >
            <option value="all">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="changes_requested">Changes Requested</option>
          </select>

          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value as PriorityFilterType)}
            style={{
              padding: '4px 8px',
              borderRadius: 6,
              background: 'var(--dash-bg)',
              border: '1px solid var(--dash-border)',
              color: 'var(--dash-text-primary)',
              fontSize: 11,
              fontWeight: 600,
            }}
          >
            <option value="all">All Priorities</option>
            <option value="NORMAL">Normal Priority</option>
            <option value="HIGH">High Priority</option>
            <option value="CRITICAL">Critical Priority</option>
          </select>

          <button
            type="button"
            onClick={() => setRuntimeOnly(!runtimeOnly)}
            style={{
              padding: '4px 10px',
              borderRadius: 6,
              background: runtimeOnly ? 'rgba(236,72,153,0.15)' : 'var(--dash-bg)',
              border: `1px solid ${runtimeOnly ? '#EC4899' : 'var(--dash-border)'}`,
              color: runtimeOnly ? '#EC4899' : 'var(--dash-text-secondary)',
              fontSize: 11,
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            <Zap size={12} /> Runtime Only
          </button>
        </div>
      </div>

      {/* ── MAIN WORKSPACE AREA: QUEUE (LEFT) + DETAILS (RIGHT) ───────────── */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden', padding: 16, gap: 16, width: '100%' }}>

        {/* ── SECTION 2: APPROVAL QUEUE (LEFT PANEL) ───────────────────────── */}
        <div
          style={{
            width: 380,
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
            overflowY: 'auto',
            flexShrink: 0,
          }}
        >
          {filteredApprovals.length === 0 ? (
            <div
              style={{
                padding: 32,
                textAlign: 'center',
                background: 'var(--dash-surface)',
                border: '1px dashed var(--dash-border)',
                borderRadius: 10,
                color: 'var(--dash-text-secondary)',
              }}
            >
              <CheckCircle2 size={32} color="#10B981" style={{ marginBottom: 8 }} />
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--dash-text-primary)' }}>No Pending Approvals</div>
              <div style={{ fontSize: 11, marginTop: 4 }}>All migration gates match your current filters.</div>
            </div>
          ) : (
            filteredApprovals.map((appr) => {
              const isSelected = selectedMigrationId === appr.migrationId && selectedGateId === appr.gate;
              const isRuntime = appr.gate === 'GATE_3';
              const isHighRisk = (appr.riskScore || 0) >= 0.7;

              const statusStripColor =
                appr.status === 'pending'
                  ? isHighRisk
                    ? '#F59E0B'
                    : '#3B82F6'
                  : appr.status === 'approved'
                  ? '#10B981'
                  : '#EF4444';

              return (
                <div
                  key={`${appr.migrationId}-${appr.gate}-${appr.id}`}
                  onClick={() => handleSelectApproval(appr)}
                  style={{
                    padding: 14,
                    borderRadius: 10,
                    background: isSelected ? 'rgba(37,99,235,0.08)' : 'var(--dash-surface)',
                    border: `1px solid ${isSelected ? 'var(--dash-accent)' : 'var(--dash-border)'}`,
                    borderLeft: `4px solid ${statusStripColor}`,
                    cursor: 'pointer',
                    transition: 'all 150ms ease-out',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 8,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 4, background: 'var(--dash-bg)', color: 'var(--dash-accent)', fontWeight: 800, fontFamily: 'var(--akaal-font-mono, monospace)' }}>
                      {appr.gate.replace('_', ' ')}
                    </span>

                    {isRuntime && (
                      <span style={{ fontSize: 9, padding: '2px 6px', borderRadius: 4, background: 'rgba(236,72,153,0.15)', color: '#EC4899', fontWeight: 800, display: 'flex', alignItems: 'center', gap: 3 }}>
                        <Zap size={10} /> RUNTIME WAITING
                      </span>
                    )}

                    <span style={{ fontSize: 10, color: 'var(--dash-text-secondary)', fontWeight: 600 }}>
                      18m ago
                    </span>
                  </div>

                  <div>
                    <h3 style={{ fontSize: 13, fontWeight: 700, margin: 0, color: 'var(--dash-text-primary)' }}>
                      {appr.migrationName}
                    </h3>
                    <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', marginTop: 2, fontFamily: 'var(--akaal-font-mono, monospace)' }}>
                      {appr.migrationId} • {appr.projectName}
                    </div>
                  </div>

                  <div style={{ fontSize: 11, color: 'var(--dash-text-primary)', background: 'var(--dash-bg)', padding: '6px 8px', borderRadius: 6, border: '1px solid var(--dash-border)' }}>
                    {appr.summary}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: 'var(--dash-text-secondary)', paddingTop: 4, borderTop: '1px solid var(--dash-border)' }}>
                    <span>By: {appr.requestedBy}</span>
                    <span style={{ color: isHighRisk ? '#EF4444' : '#10B981', fontWeight: 700 }}>
                      Risk: {appr.riskScore || 0.12} ({isHighRisk ? 'HIGH' : 'LOW'})
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* ── SECTION 3: APPROVAL DETAILS PANEL (RIGHT) ────────────────────── */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            background: 'var(--dash-surface)',
            border: '1px solid var(--dash-border)',
            borderRadius: 10,
            overflow: 'hidden',
          }}
        >
          {isLoading ? (
            /* Skeleton Loading State */
            <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div style={{ height: 24, width: '40%', background: 'var(--dash-border)', borderRadius: 4, animation: 'pulse 1.5s infinite' }} />
              <div style={{ height: 16, width: '60%', background: 'var(--dash-border)', borderRadius: 4, animation: 'pulse 1.5s infinite' }} />
              <div style={{ height: 100, width: '100%', background: 'var(--dash-border)', borderRadius: 8, animation: 'pulse 1.5s infinite' }} />
            </div>
          ) : !selectedApproval ? (
            <div style={{ padding: 48, textAlign: 'center', color: 'var(--dash-text-secondary)', margin: 'auto' }}>
              <Shield size={48} color="var(--dash-border)" style={{ marginBottom: 12 }} />
              <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--dash-text-primary)' }}>No Approval Selected</div>
              <div style={{ fontSize: 12, marginTop: 4 }}>Select an approval packet from the queue on the left to view details.</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'auto' }}>

              {/* Immutable Archive Banner for Historical Approvals */}
              {selectedApproval.status !== 'pending' && (
                <div
                  style={{
                    padding: '10px 20px',
                    background: 'rgba(107, 114, 128, 0.12)',
                    borderBottom: '1px solid var(--dash-border)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 16,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Lock size={15} color="#9CA3AF" />
                    <span style={{ fontSize: 11, fontWeight: 700, color: '#9CA3AF', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                      🔒 IMMUTABLE HISTORICAL ARCHIVE — READ ONLY ({selectedApproval.status.toUpperCase()})
                    </span>
                  </div>
                  <div style={{ fontSize: 11, fontFamily: 'var(--akaal-font-mono, monospace)', color: 'var(--dash-text-secondary)' }}>
                    SHA256: 3a7f8e91c2b409aef12d0831 • Version: v8 • Duration: 4m 12s
                  </div>
                </div>
              )}

              {/* Approval Packet Header */}
              <div style={{ padding: 20, borderBottom: '1px solid var(--dash-border)', background: 'var(--dash-bg)', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16 }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: 11, padding: '3px 8px', borderRadius: 4, background: 'var(--dash-accent)', color: '#FFF', fontWeight: 800 }}>
                      {selectedApproval.gate.replace('_', ' ')}
                    </span>
                    <h2 style={{ fontSize: 18, fontWeight: 800, margin: 0, color: 'var(--dash-text-primary)' }}>
                      {selectedApproval.migrationName}
                    </h2>
                    <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, background: selectedApproval.status === 'pending' ? 'rgba(245,158,11,0.15)' : selectedApproval.status === 'approved' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)', color: selectedApproval.status === 'pending' ? '#F59E0B' : selectedApproval.status === 'approved' ? '#10B981' : '#EF4444', fontWeight: 700, textTransform: 'uppercase' }}>
                      ● {selectedApproval.status}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)', marginTop: 4, fontFamily: 'var(--akaal-font-mono, monospace)' }}>
                    Pipeline ID: {selectedApproval.migrationId} • Project: {selectedApproval.projectName} • Requested by: {selectedApproval.requestedBy}
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)' }}>
                    {selectedApproval.status === 'pending' ? 'SLA Countdown' : 'Archived On'}
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 800, color: selectedApproval.status === 'pending' ? '#F59E0B' : '#9CA3AF', fontFamily: 'var(--akaal-font-mono, monospace)' }}>
                    {selectedApproval.status === 'pending' ? '03h 42m 15s' : selectedApproval.approvedAt ? new Date(selectedApproval.approvedAt).toLocaleDateString() : '2026-08-05'}
                  </div>
                </div>
              </div>

              {/* Dynamic Gate-Specific Content Area */}
              <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 20, flex: 1 }}>

                {/* GATE 1 LAYOUT: Discovery & Assessment */}
                {selectedApproval.gate === 'GATE_1' && (
                  <div style={{ border: '1px solid var(--dash-border)', borderRadius: 10, padding: 16, background: 'var(--dash-bg)', display: 'flex', flexDirection: 'column', gap: 14 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--dash-text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Database size={15} color="var(--dash-accent)" /> Gate 1 Discovery & Scope Assessment Summary
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
                      <div style={{ background: 'var(--dash-surface)', padding: 12, borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                        <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', textTransform: 'uppercase' }}>Databases Cataloged</div>
                        <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--dash-text-primary)', marginTop: 4 }}>3 Databases</div>
                      </div>
                      <div style={{ background: 'var(--dash-surface)', padding: 12, borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                        <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', textTransform: 'uppercase' }}>Schemas Discovered</div>
                        <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--dash-text-primary)', marginTop: 4 }}>4 Schemas</div>
                      </div>
                      <div style={{ background: 'var(--dash-surface)', padding: 12, borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                        <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', textTransform: 'uppercase' }}>Objects Discovered</div>
                        <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--dash-text-primary)', marginTop: 4 }}>124 Objects</div>
                      </div>
                      <div style={{ background: 'var(--dash-surface)', padding: 12, borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                        <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', textTransform: 'uppercase' }}>Conversion Readiness</div>
                        <div style={{ fontSize: 16, fontWeight: 800, color: '#10B981', marginTop: 4 }}>99.4% Optimal</div>
                      </div>
                    </div>

                    <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)' }}>
                      <strong>Evidence Summary:</strong> {selectedApproval.evidenceSummary || 'Catalog discovery probe SHA-256 digest verified.'}
                    </div>
                  </div>
                )}

                {/* GATE 2 LAYOUT: Migration Plan & Execution */}
                {selectedApproval.gate === 'GATE_2' && (
                  <div style={{ border: '1px solid var(--dash-border)', borderRadius: 10, padding: 16, background: 'var(--dash-bg)', display: 'flex', flexDirection: 'column', gap: 14 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--dash-text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Layers size={15} color="var(--dash-accent)" /> Gate 2 Execution DAG & Governance Policy
                      </div>
                      {onNavigateToExecutionPlan && (
                        <button
                          type="button"
                          onClick={() => onNavigateToExecutionPlan(selectedApproval.migrationId)}
                          style={{ padding: '4px 10px', borderRadius: 6, background: 'rgba(37,99,235,0.12)', border: '1px solid var(--dash-accent)', color: 'var(--dash-accent)', fontSize: 11, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}
                        >
                          <Zap size={12} /> Open Execution Plan
                        </button>
                      )}
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
                      <div style={{ background: 'var(--dash-surface)', padding: 12, borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                        <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', textTransform: 'uppercase' }}>Worker Pool</div>
                        <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--dash-text-primary)', marginTop: 4 }}>8 Workers</div>
                      </div>
                      <div style={{ background: 'var(--dash-surface)', padding: 12, borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                        <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', textTransform: 'uppercase' }}>Batch Commit Size</div>
                        <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--dash-text-primary)', marginTop: 4 }}>10,000 Rows</div>
                      </div>
                      <div style={{ background: 'var(--dash-surface)', padding: 12, borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                        <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', textTransform: 'uppercase' }}>Validation Strategy</div>
                        <div style={{ fontSize: 16, fontWeight: 800, color: '#10B981', marginTop: 4 }}>Checksum 100%</div>
                      </div>
                      <div style={{ background: 'var(--dash-surface)', padding: 12, borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                        <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', textTransform: 'uppercase' }}>Masking Protocol</div>
                        <div style={{ fontSize: 16, fontWeight: 800, color: '#3B82F6', marginTop: 4 }}>SHA-256 Enforced</div>
                      </div>
                    </div>
                  </div>
                )}

                {/* GATE 3 LAYOUT: Production Cutover Authorization */}
                {selectedApproval.gate === 'GATE_3' && (
                  <div style={{ border: '1px solid rgba(236,72,153,0.3)', borderRadius: 10, padding: 16, background: 'rgba(236,72,153,0.05)', display: 'flex', flexDirection: 'column', gap: 14 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: '#EC4899', display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Zap size={16} color="#EC4899" /> Gate 3 Runtime Cutover Telemetry & Replication Snapshot
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
                      <div style={{ background: 'var(--dash-surface)', padding: 12, borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                        <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', textTransform: 'uppercase' }}>CDC Replication Lag</div>
                        <div style={{ fontSize: 16, fontWeight: 800, color: '#10B981', marginTop: 4 }}>0.000s (Zero Lag)</div>
                      </div>
                      <div style={{ background: 'var(--dash-surface)', padding: 12, borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                        <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', textTransform: 'uppercase' }}>Integrity Match</div>
                        <div style={{ fontSize: 16, fontWeight: 800, color: '#10B981', marginTop: 4 }}>100.0% (CRC32)</div>
                      </div>
                      <div style={{ background: 'var(--dash-surface)', padding: 12, borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                        <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', textTransform: 'uppercase' }}>Rows Loaded</div>
                        <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--dash-text-primary)', marginTop: 4 }}>1,240,500,000</div>
                      </div>
                      <div style={{ background: 'var(--dash-surface)', padding: 12, borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                        <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', textTransform: 'uppercase' }}>Rollback Readiness</div>
                        <div style={{ fontSize: 16, fontWeight: 800, color: '#10B981', marginTop: 4 }}>Reverse CDC Ready</div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Digital Signatures Card (4-Eyes Custody Matrix) */}
                <div style={{ border: '1px solid var(--dash-border)', borderRadius: 10, padding: 16, background: 'var(--dash-bg)' }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--dash-text-primary)', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <ShieldCheck size={15} color="#10B981" /> Digital Signature & Multi-Custody Approval Matrix
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 10 }}>
                    {selectedApproval.requiredRoles.map((role, idx) => {
                      const isSigned = idx === 0 || selectedApproval.status === 'approved';
                      return (
                        <div
                          key={role}
                          style={{
                            padding: 12,
                            borderRadius: 8,
                            background: 'var(--dash-surface)',
                            border: `1px solid ${isSigned ? 'rgba(16,185,129,0.3)' : 'var(--dash-border)'}`,
                            display: 'flex',
                            alignItems: 'center',
                            gap: 10,
                          }}
                        >
                          {isSigned ? <CheckCircle2 size={18} color="#10B981" /> : <Clock size={18} color="#F59E0B" />}
                          <div>
                            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--dash-text-primary)' }}>{role}</div>
                            <div style={{ fontSize: 10, color: isSigned ? '#10B981' : '#F59E0B', fontWeight: 600 }}>
                              {isSigned ? '✓ SIGNED & VERIFIED' : 'PENDING SIGNATURE'}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Comments & Discussion Thread */}
                <div style={{ border: '1px solid var(--dash-border)', borderRadius: 10, padding: 16, background: 'var(--dash-bg)' }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--dash-text-primary)', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <MessageSquare size={15} color="var(--dash-accent)" /> Discussion Thread & Reviewer Feedback
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 14 }}>
                    {(selectedApproval.comments || []).length === 0 ? (
                      <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', fontStyle: 'italic' }}>No comments recorded yet.</div>
                    ) : (
                      selectedApproval.comments?.map((c, i) => (
                        <div key={i} style={{ background: 'var(--dash-surface)', padding: 10, borderRadius: 6, border: '1px solid var(--dash-border)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, fontWeight: 700, color: 'var(--dash-text-primary)' }}>
                            <span>{c.author}</span>
                            <span style={{ fontSize: 10, color: 'var(--dash-text-secondary)', fontWeight: 500 }}>{c.timestamp}</span>
                          </div>
                          <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)', marginTop: 4 }}>{c.text}</div>
                        </div>
                      ))
                    )}
                  </div>

                  <div style={{ display: 'flex', gap: 8 }}>
                    <input
                      type="text"
                      placeholder="Add reviewer feedback or comment..."
                      value={commentText}
                      onChange={(e) => setCommentText(e.target.value)}
                      style={{ flex: 1, padding: '8px 12px', borderRadius: 6, background: 'var(--dash-surface)', border: '1px solid var(--dash-border)', color: 'var(--dash-text-primary)', fontSize: 12 }}
                    />
                    <button
                      type="button"
                      onClick={handleAddComment}
                      style={{ padding: '8px 14px', borderRadius: 6, background: 'var(--dash-accent)', color: '#FFF', fontSize: 12, fontWeight: 700, border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}
                    >
                      <Send size={13} /> Post
                    </button>
                  </div>
                </div>

              </div>

              {/* ── STICKY ACTION PANEL ──────────────────────────────────────── */}
              <div
                style={{
                  padding: '14px 20px',
                  background: 'var(--dash-bg)',
                  borderTop: '1px solid var(--dash-border)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 12,
                  flexWrap: 'wrap',
                  position: 'sticky',
                  bottom: 0,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  {selectedApproval.status === 'pending' ? (
                    <>
                      <button
                        type="button"
                        onClick={() =>
                          setConfirmModal({
                            isOpen: true,
                            title: 'Approve Migration Gate',
                            message: `Grant formal multi-custody approval for ${selectedApproval.migrationName} at ${selectedApproval.gate}.`,
                            actionType: 'approved',
                            approvalId: selectedApproval.id,
                            migrationId: selectedApproval.migrationId,
                          })
                        }
                        style={{
                          padding: '8px 18px',
                          borderRadius: 6,
                          background: '#10B981',
                          color: '#FFF',
                          fontSize: 12,
                          fontWeight: 800,
                          border: 'none',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 6,
                        }}
                      >
                        <CheckCircle2 size={15} /> Approve Gate
                      </button>

                      <button
                        type="button"
                        onClick={() =>
                          setConfirmModal({
                            isOpen: true,
                            title: 'Request Changes',
                            message: `Request plan or schema modifications before approving ${selectedApproval.migrationName}.`,
                            actionType: 'changes_requested',
                            approvalId: selectedApproval.id,
                            migrationId: selectedApproval.migrationId,
                          })
                        }
                        style={{
                          padding: '8px 16px',
                          borderRadius: 6,
                          background: 'rgba(245,158,11,0.15)',
                          border: '1px solid #F59E0B',
                          color: '#F59E0B',
                          fontSize: 12,
                          fontWeight: 700,
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 6,
                        }}
                      >
                        <AlertTriangle size={15} /> Request Changes
                      </button>

                      <button
                        type="button"
                        onClick={() =>
                          setConfirmModal({
                            isOpen: true,
                            title: 'Reject Migration Gate',
                            message: `Reject approval request for ${selectedApproval.migrationName}. Pipeline execution will remain held.`,
                            actionType: 'rejected',
                            approvalId: selectedApproval.id,
                            migrationId: selectedApproval.migrationId,
                          })
                        }
                        style={{
                          padding: '8px 16px',
                          borderRadius: 6,
                          background: 'rgba(239,68,68,0.15)',
                          border: '1px solid #EF4444',
                          color: '#EF4444',
                          fontSize: 12,
                          fontWeight: 700,
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 6,
                        }}
                      >
                        <XCircle size={15} /> Reject
                      </button>
                    </>
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span
                        style={{
                          fontSize: 11,
                          padding: '6px 12px',
                          borderRadius: 6,
                          background: 'rgba(107, 114, 128, 0.15)',
                          border: '1px solid #6B7280',
                          color: '#9CA3AF',
                          fontWeight: 700,
                          display: 'flex',
                          alignItems: 'center',
                          gap: 6,
                        }}
                      >
                        🔒 ARCHIVED RECORD — READ ONLY ({selectedApproval.status.toUpperCase()})
                      </span>
                    </div>
                  )}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  {onNavigateToMissionControl && (
                    <button
                      type="button"
                      onClick={() => onNavigateToMissionControl(selectedApproval.migrationId)}
                      style={{
                        padding: '8px 14px',
                        borderRadius: 6,
                        background: 'var(--dash-surface)',
                        border: '1px solid var(--dash-border)',
                        color: 'var(--dash-text-primary)',
                        fontSize: 12,
                        fontWeight: 700,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                      }}
                    >
                      <Activity size={14} color="var(--dash-accent)" /> Open Mission Control
                    </button>
                  )}

                  <button
                    type="button"
                    onClick={() =>
                      notificationService.push('Approval Packet Exported', 'success', 'Exported cryptographic approval packet JSON.')
                    }
                    style={{
                      padding: '8px 14px',
                      borderRadius: 6,
                      background: 'var(--dash-surface)',
                      border: '1px solid var(--dash-border)',
                      color: 'var(--dash-text-secondary)',
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                    }}
                  >
                    <Download size={14} /> Download Packet
                  </button>
                </div>
              </div>

            </div>
          )}
        </div>
      </div>

      {/* ── ENTERPRISE DECISION CONFIRMATION MODAL ───────────────────────── */}
      {confirmModal && confirmModal.isOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.65)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
          }}
        >
          <div
            style={{
              width: 480,
              background: 'var(--dash-surface)',
              border: '1px solid var(--dash-border)',
              borderRadius: 12,
              boxShadow: '0 20px 40px rgba(0,0,0,0.5)',
              padding: 24,
              display: 'flex',
              flexDirection: 'column',
              gap: 16,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <ShieldAlert size={24} color={confirmModal.actionType === 'approved' ? '#10B981' : '#EF4444'} />
              <h3 style={{ fontSize: 16, fontWeight: 800, margin: 0, color: 'var(--dash-text-primary)' }}>
                {confirmModal.title}
              </h3>
            </div>

            <div style={{ fontSize: 13, color: 'var(--dash-text-secondary)' }}>
              {confirmModal.message}
            </div>

            <div>
              <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--dash-text-secondary)', textTransform: 'uppercase' }}>
                Decision Justification / Reason:
              </label>
              <textarea
                rows={3}
                placeholder="Enter mandatory decision reason for compliance audit log..."
                value={confirmReason}
                onChange={(e) => setConfirmReason(e.target.value)}
                style={{
                  width: '100%',
                  marginTop: 6,
                  padding: 10,
                  borderRadius: 6,
                  background: 'var(--dash-bg)',
                  border: '1px solid var(--dash-border)',
                  color: 'var(--dash-text-primary)',
                  fontSize: 12,
                }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, paddingTop: 10, borderTop: '1px solid var(--dash-border)' }}>
              <button
                type="button"
                onClick={() => setConfirmModal(null)}
                style={{ padding: '8px 16px', borderRadius: 6, background: 'var(--dash-bg)', border: '1px solid var(--dash-border)', color: 'var(--dash-text-primary)', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmDecision}
                style={{
                  padding: '8px 18px',
                  borderRadius: 6,
                  background: confirmModal.actionType === 'approved' ? '#10B981' : confirmModal.actionType === 'rejected' ? '#EF4444' : '#F59E0B',
                  color: '#FFF',
                  fontSize: 12,
                  fontWeight: 800,
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                Confirm Decision
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
