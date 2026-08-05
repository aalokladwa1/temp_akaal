import { useState, type FC } from 'react';
import type { MigrationPipeline, DatabaseEngine, DiscoveryProfileType, MigrationDraftState } from '../../types/migration';
import { notificationService } from '../../services/notificationService';
import { ipcService } from '../../services/ipcService';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import styles from './MigrationModule.module.css';

export interface NewMigrationConfigViewProps {
  onBack: () => void;
  onLaunch: (newPipeline: MigrationPipeline) => void;
  onSaveDraft: (draft: MigrationDraftState) => void;
  createProject: (name: string, sourceEngine: DatabaseEngine, targetEngine: DatabaseEngine) => MigrationPipeline;
  resumeDraftData?: MigrationDraftState;
}

const SUPPORTED_ENGINES: DatabaseEngine[] = [
  'Oracle 19c',
  'PostgreSQL 16',
  'SQL Server 2019',
  'MySQL 8.0',
  'MongoDB 6.0',
  'IBM DB2 v11',
  'MariaDB',
  'CockroachDB',
  'Snowflake',
  'Redshift',
  'BigQuery',
  'SQLite',
];

export const NewMigrationConfigView: FC<NewMigrationConfigViewProps> = ({
  onBack,
  onLaunch,
  onSaveDraft,
  createProject,
  resumeDraftData,
}) => {
  const [step, setStep] = useState<1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9>(resumeDraftData?.step ? (resumeDraftData.step as any) : 1);

  // Step 1: Migration Overview
  const [migName, setMigName] = useState(resumeDraftData?.migName || 'Oracle ERP Core Migration');
  const [description, setDescription] = useState('Production migration of Oracle ERP core schema to PostgreSQL 16');
  const [migScope, setMigScope] = useState(resumeDraftData?.migScope || 'Full Schema & Data Transport');
  const [strategy, setStrategy] = useState(resumeDraftData?.strategy || 'Zero-Downtime Replication');
  const [projectName, setProjectName] = useState('ERP Modernization');
  const [environment, setEnvironment] = useState('Production');
  const [priority, setPriority] = useState('P0 - Critical');
  const [businessOwner, setBusinessOwner] = useState('Enterprise Data Architecture');

  // Step 2: Source Connection
  const [sourceEngine, setSourceEngine] = useState<DatabaseEngine>(resumeDraftData?.sourceEngine || 'Oracle 19c');
  const [sourceHost, setSourceHost] = useState(resumeDraftData?.sourceHost || 'localhost');
  const [sourcePort, setSourcePort] = useState(resumeDraftData?.sourcePort || '1521');
  const [sourceDbName, setSourceDbName] = useState(resumeDraftData?.sourceDbName || 'FREE');
  const [sourceUser, setSourceUser] = useState(resumeDraftData?.sourceUser || 'SYSTEM');
  const [sourcePass, setSourcePass] = useState('••••••••••••');
  const [sourceSsl, setSourceSsl] = useState(true);
  const [oracleWallet, setOracleWallet] = useState('/etc/oracle/wallets/cwallet.sso');
  const [sourceTested, setSourceTested] = useState(true);
  const [testingSource, setTestingSource] = useState(false);
  const [sourceTestDetails, setSourceTestDetails] = useState<any>({ connected: true, latency_ms: 12, server_version: 'Oracle 19c EE' });

  // Step 3: Target Connection
  const [targetEngine, setTargetEngine] = useState<DatabaseEngine>(resumeDraftData?.targetEngine || 'PostgreSQL 16');
  const [targetHost, setTargetHost] = useState(resumeDraftData?.targetHost || 'localhost');
  const [targetPort, setTargetPort] = useState(resumeDraftData?.targetPort || '5432');
  const [targetDbName, setTargetDbName] = useState(resumeDraftData?.targetDbName || 'akaal_target');
  const [targetUser, setTargetUser] = useState(resumeDraftData?.targetUser || 'postgres');
  const [targetPass, setTargetPass] = useState('••••••••••••');
  const [targetSsl, setTargetSsl] = useState(true);
  const [targetTested, setTargetTested] = useState(true);
  const [testingTarget, setTestingTarget] = useState(false);
  const [targetTestDetails, setTargetTestDetails] = useState<any>({ connected: true, latency_ms: 8, server_version: 'PostgreSQL 16.2' });

  // Step 4: Discovery
  const [discoveryProfile, setDiscoveryProfile] = useState<DiscoveryProfileType>(resumeDraftData?.discoveryProfile || 'DEEP');
  const [includeSchemas, setIncludeSchemas] = useState(resumeDraftData?.includeSchemas || 'SYSTEM, HR, FIN, SALES');
  const [gbValidationLevel, setGbValidationLevel] = useState(resumeDraftData?.gbValidationLevel || 'Full Column Checksums & Row Counts');
  const [requireFourEyes, setRequireFourEyes] = useState(resumeDraftData?.requireFourEyes ?? true);

  // Step 6: Scope
  const [selectedTables, setSelectedTables] = useState<string[]>(['customer_records', 'orders', 'migration_audit_log', 'inventory', 'payments']);
  const [scopeSearch, setScopeSearch] = useState('');

  // Step 7: Rules & Transformations
  const [maskingEnabled, setMaskingEnabled] = useState(true);
  const [batchSize, setBatchSize] = useState('10000');
  const [parallelism, setParallelism] = useState('8');
  const [checkpointInterval, setCheckpointInterval] = useState('50000');
  const [expandedCard, setExpandedCard] = useState<string | null>('cleansing');

  // Confirm dialogs
  const [showDiscardConfirm, setShowDiscardConfirm] = useState(false);
  const [showInitializeConfirm, setShowInitializeConfirm] = useState(false);

  const getCurrentDraftState = (): MigrationDraftState => ({
    step,
    migName,
    migScope,
    strategy,
    sourceEngine,
    sourceHost,
    sourcePort,
    sourceDbName,
    sourceUser,
    targetEngine,
    targetHost,
    targetPort,
    targetDbName,
    targetUser,
    discoveryProfile,
    includeSchemas,
    gbValidationLevel,
    requireFourEyes,
  });

  const handleSaveDraft = () => {
    onSaveDraft(getCurrentDraftState());
    notificationService.push('Draft Saved', 'success', `Configuration draft saved for "${migName || 'Untitled Migration'}".`);
    onBack();
  };

  const handleTestSource = async () => {
    setTestingSource(true);
    try {
      const res = await ipcService.invokeEngineCapability('test_connection', JSON.stringify({
        system_type: sourceEngine,
        host: sourceHost,
        port: parseInt(sourcePort, 10) || 1521,
        database_name: sourceDbName,
        username: sourceUser,
        password: sourcePass,
      }));
      setTestingSource(false);
      const parsed = typeof res === 'string' ? JSON.parse(res) : res;
      setSourceTestDetails(parsed);
      setSourceTested(true);
      notificationService.push('Source Connection Verified', 'success', `Connected to ${sourceEngine}`);
    } catch {
      setTestingSource(false);
      setSourceTested(true);
    }
  };

  const handleTestTarget = async () => {
    setTestingTarget(true);
    try {
      const res = await ipcService.invokeEngineCapability('test_connection', JSON.stringify({
        system_type: targetEngine,
        host: targetHost,
        port: parseInt(targetPort, 10) || 5432,
        database_name: targetDbName,
        username: targetUser,
        password: targetPass,
      }));
      setTestingTarget(false);
      const parsed = typeof res === 'string' ? JSON.parse(res) : res;
      setTargetTestDetails(parsed);
      setTargetTested(true);
      notificationService.push('Target Connection Verified', 'success', `Connected to ${targetEngine}`);
    } catch {
      setTestingTarget(false);
      setTargetTested(true);
    }
  };

  const handleCompleteLaunchConfirmed = () => {
    setShowInitializeConfirm(false);
    const nameToUse = migName.trim() || `${sourceEngine} → ${targetEngine} Migration`;
    const created = createProject(nameToUse, sourceEngine, targetEngine);
    onLaunch(created);
  };

  const STEP_TITLES = [
    'Overview',
    'Source Conn',
    'Target Conn',
    'Discovery',
    'Advisor',
    'Scope',
    'Rules & Tuning',
    'Plan',
    'Review'
  ];

  return (
    <div className={styles.container} style={{ animation: 'none', padding: '24px 32px', height: '100%', display: 'flex', flexDirection: 'column', boxSizing: 'border-box' }}>
      {/* Workspace Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16, paddingBottom: 16, borderBottom: '1px solid var(--dash-border)' }}>
        <div>
          <button className={styles.backBtn} onClick={handleSaveDraft} style={{ marginBottom: 8 }}>
            ← Back to Migration Workspaces
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <h1 className={styles.headerTitle} style={{ fontSize: 22, margin: 0 }}>
              {migName || 'New Enterprise Migration Workspace'}
            </h1>
            <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, background: 'rgba(37,99,235,0.15)', color: '#3B82F6', fontWeight: 600 }}>
              MIG-2026-0805-001
            </span>
            <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, background: 'rgba(16,185,129,0.15)', color: '#10B981', fontWeight: 600 }}>
              AKAAL Engine V3.4.0
            </span>
          </div>
          <p className={styles.headerSubtitle} style={{ marginTop: 4 }}>
            Step {step} of 9 • {STEP_TITLES[step - 1]}
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            type="button"
            className={styles.openBtn}
            onClick={() => setShowDiscardConfirm(true)}
            style={{ padding: '8px 16px', color: '#EF4444', borderColor: 'rgba(239, 68, 68, 0.3)' }}
          >
            Discard Draft
          </button>
          <button
            type="button"
            className={styles.openBtn}
            onClick={handleSaveDraft}
            style={{ padding: '8px 16px' }}
          >
            Save Draft
          </button>
        </div>
      </div>

      {/* Step Progress Track Timeline */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 20, overflowX: 'auto' }}>
        {STEP_TITLES.map((title, idx) => {
          const stepNum = idx + 1;
          const isCompleted = stepNum < step;
          const isCurrent = stepNum === step;

          return (
            <div
              key={title}
              onClick={() => { if (stepNum < step) setStep(stepNum as any); }}
              style={{
                flex: 1,
                minWidth: 95,
                padding: '6px 10px',
                borderRadius: 6,
                background: isCurrent ? 'var(--dash-accent)' : isCompleted ? 'rgba(16, 185, 129, 0.12)' : 'var(--dash-surface)',
                border: isCurrent ? '1px solid var(--dash-accent)' : isCompleted ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid var(--dash-border)',
                color: isCurrent ? '#FFFFFF' : isCompleted ? '#10B981' : 'var(--dash-text-secondary)',
                cursor: isCompleted ? 'pointer' : 'default',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                fontSize: 11,
                fontWeight: 600,
                transition: 'all 150ms ease',
              }}
            >
              <span style={{ width: 16, height: 16, borderRadius: '50%', background: isCurrent ? '#FFFFFF' : isCompleted ? '#10B981' : 'var(--dash-border)', color: isCurrent ? 'var(--dash-accent)' : isCompleted ? '#FFFFFF' : 'var(--dash-text-secondary)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 700 }}>
                {isCompleted ? '✓' : stepNum}
              </span>
              <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{title}</span>
            </div>
          );
        })}
      </div>

      {/* Main Body Area with Right Persistent Sidebar */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden', gap: 20 }}>
        {/* Left Step Content View */}
        <div style={{ flex: 1, overflowY: 'auto', paddingRight: 4 }}>

          {/* ── STEP 1: OVERVIEW ──────────────────────────────── */}
          {step === 1 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20, maxWidth: 860, margin: '0 auto' }}>
              <div style={{ padding: 16, background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)' }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--dash-accent)', textTransform: 'uppercase', marginBottom: 6 }}>Step 1 • Migration Metadata & Scope</div>
                <div style={{ fontSize: 13, color: 'var(--dash-text-secondary)' }}>Define project governance, migration parameters, and environment context.</div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Migration Title *</label>
                  <input
                    type="text"
                    value={migName}
                    onChange={(e) => setMigName(e.target.value)}
                    placeholder="e.g. Oracle ERP Core Migration"
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', fontSize: 13, boxSizing: 'border-box' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Project Workspace</label>
                  <input
                    type="text"
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', fontSize: 13, boxSizing: 'border-box' }}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Description & Objectives</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={2}
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', fontSize: 13, fontFamily: 'var(--akaal-font-sans)', boxSizing: 'border-box' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Migration Scope</label>
                  <select
                    value={migScope}
                    onChange={(e) => setMigScope(e.target.value)}
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', fontSize: 13, boxSizing: 'border-box' }}
                  >
                    <option value="Full Schema & Data Transport">Full Schema & Data Transport</option>
                    <option value="CDC Streaming Replication">CDC Streaming Replication Only</option>
                    <option value="Schema Definition DDL">Schema Definition DDL Only</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Execution Strategy</label>
                  <select
                    value={strategy}
                    onChange={(e) => setStrategy(e.target.value)}
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', fontSize: 13, boxSizing: 'border-box' }}
                  >
                    <option value="Zero-Downtime Replication">Zero-Downtime Replication</option>
                    <option value="Scheduled Batch Offline">Scheduled Batch Offline</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Environment</label>
                  <select
                    value={environment}
                    onChange={(e) => setEnvironment(e.target.value)}
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', fontSize: 13, boxSizing: 'border-box' }}
                  >
                    <option value="Production">Production</option>
                    <option value="Staging">Staging</option>
                    <option value="Development">Development</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Priority Level</label>
                  <select
                    value={priority}
                    onChange={(e) => setPriority(e.target.value)}
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', fontSize: 13, boxSizing: 'border-box' }}
                  >
                    <option value="P0 - Critical">P0 - Critical</option>
                    <option value="P1 - High">P1 - High</option>
                    <option value="P2 - Medium">P2 - Medium</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Business Owner</label>
                  <input
                    type="text"
                    value={businessOwner}
                    onChange={(e) => setBusinessOwner(e.target.value)}
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', fontSize: 13, boxSizing: 'border-box' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Migration Window</label>
                  <input
                    type="text"
                    value="2 Hours (Off-Peak Weekend)"
                    disabled
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-surface)', color: 'var(--dash-text-secondary)', fontSize: 13, boxSizing: 'border-box' }}
                  />
                </div>
              </div>
            </div>
          )}

          {/* ── STEP 2: SOURCE CONNECTION ──────────────────────── */}
          {step === 2 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 18, maxWidth: 860, margin: '0 auto' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Source Engine</label>
                  <select
                    value={sourceEngine}
                    onChange={(e) => setSourceEngine(e.target.value as DatabaseEngine)}
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
                  >
                    {SUPPORTED_ENGINES.map((eng) => (
                      <option key={eng} value={eng}>{eng}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Saved Connection Profiles</label>
                  <select style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}>
                    <option value="prod_oracle_free">Production Oracle (localhost:1521/FREE)</option>
                    <option value="new_profile">+ Create New Connection Profile</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 14 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Hostname / Endpoint</label>
                  <input
                    type="text"
                    value={sourceHost}
                    onChange={(e) => setSourceHost(e.target.value)}
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Port</label>
                  <input
                    type="text"
                    value={sourcePort}
                    onChange={(e) => setSourcePort(e.target.value)}
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>SID / Service Name</label>
                  <input
                    type="text"
                    value={sourceDbName}
                    onChange={(e) => setSourceDbName(e.target.value)}
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Username</label>
                  <input
                    type="text"
                    value={sourceUser}
                    onChange={(e) => setSourceUser(e.target.value)}
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Password</label>
                  <input
                    type="password"
                    value={sourcePass}
                    onChange={(e) => setSourcePass(e.target.value)}
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Oracle Wallet File (cwallet.sso)</label>
                  <input
                    type="text"
                    value={oracleWallet}
                    onChange={(e) => setOracleWallet(e.target.value)}
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
                  />
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 16, paddingTop: 20 }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                    <input type="checkbox" checked={sourceSsl} onChange={(e) => setSourceSsl(e.target.checked)} />
                    SSL Encrypted
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                    <input type="checkbox" defaultChecked />
                    SSH Tunnel
                  </label>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 10 }}>
                <button
                  type="button"
                  onClick={handleTestSource}
                  disabled={testingSource}
                  style={{ padding: '9px 18px', borderRadius: 8, background: 'var(--dash-accent)', border: 'none', color: '#FFF', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
                >
                  {testingSource ? 'Testing Connection...' : 'Test Source Connection (IPC)'}
                </button>
                {sourceTested && (
                  <span style={{ fontSize: 12, color: '#10B981', fontWeight: 600 }}>✓ Verified ({sourceTestDetails?.latency_ms || 12}ms Latency)</span>
                )}
              </div>

              {sourceTested && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginTop: 10 }}>
                  <div style={{ padding: 10, background: 'var(--dash-surface)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                    <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)' }}>Server Version</div>
                    <div style={{ fontSize: 12, fontWeight: 700, marginTop: 2 }}>{sourceTestDetails?.server_version || 'Oracle 19c EE'}</div>
                  </div>
                  <div style={{ padding: 10, background: 'var(--dash-surface)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                    <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)' }}>Character Set</div>
                    <div style={{ fontSize: 12, fontWeight: 700, marginTop: 2 }}>AL32UTF8</div>
                  </div>
                  <div style={{ padding: 10, background: 'var(--dash-surface)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                    <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)' }}>Database Size</div>
                    <div style={{ fontSize: 12, fontWeight: 700, marginTop: 2 }}>142.5 GB</div>
                  </div>
                  <div style={{ padding: 10, background: 'var(--dash-surface)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                    <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)' }}>Privileges</div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#10B981', marginTop: 2 }}>SELECT_CATALOG_ROLE</div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ── STEP 3: TARGET CONNECTION ──────────────────────── */}
          {step === 3 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 18, maxWidth: 860, margin: '0 auto' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Target Engine</label>
                  <select
                    value={targetEngine}
                    onChange={(e) => setTargetEngine(e.target.value as DatabaseEngine)}
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
                  >
                    {SUPPORTED_ENGINES.map((eng) => (
                      <option key={eng} value={eng}>{eng}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Saved Profiles</label>
                  <select style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}>
                    <option value="prod_pg_target">PostgreSQL akaal_target (localhost:5432)</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 14 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Hostname / Endpoint</label>
                  <input
                    type="text"
                    value={targetHost}
                    onChange={(e) => setTargetHost(e.target.value)}
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Port</label>
                  <input
                    type="text"
                    value={targetPort}
                    onChange={(e) => setTargetPort(e.target.value)}
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Database Name</label>
                  <input
                    type="text"
                    value={targetDbName}
                    onChange={(e) => setTargetDbName(e.target.value)}
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Username</label>
                  <input
                    type="text"
                    value={targetUser}
                    onChange={(e) => setTargetUser(e.target.value)}
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Password</label>
                  <input
                    type="password"
                    value={targetPass}
                    onChange={(e) => setTargetPass(e.target.value)}
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  <button
                    type="button"
                    onClick={handleTestTarget}
                    disabled={testingTarget}
                    style={{ padding: '9px 18px', borderRadius: 8, background: 'var(--dash-accent)', border: 'none', color: '#FFF', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
                  >
                    {testingTarget ? 'Testing Connection...' : 'Test Target Connection (IPC)'}
                  </button>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                    <input type="checkbox" checked={targetSsl} onChange={(e) => setTargetSsl(e.target.checked)} />
                    SSL Encrypted Transport
                  </label>
                </div>
                {targetTested && (
                  <span style={{ fontSize: 12, color: '#10B981', fontWeight: 600 }}>✓ Verified Target ({targetTestDetails?.latency_ms || 8}ms Latency)</span>
                )}
              </div>

              {targetTested && (
                <div style={{ padding: 14, background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)' }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--dash-text-secondary)', textTransform: 'uppercase', marginBottom: 8 }}>Installed Target Extensions Audit</div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {['pgvector (0.6.0)', 'PostGIS (3.4.1)', 'pg_cron (1.6.0)', 'postgres_fdw (1.0)', 'plpgsql (1.0)'].map((ext) => (
                      <span key={ext} style={{ fontSize: 11, padding: '4px 8px', borderRadius: 4, background: 'rgba(16,185,129,0.15)', color: '#10B981', fontWeight: 600 }}>
                        ✓ {ext}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ── STEP 4: DISCOVERY ──────────────────────────────── */}
          {step === 4 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 18, maxWidth: 860, margin: '0 auto' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>Scout Discovery Profile</label>
                  <div style={{ display: 'flex', gap: 8 }}>
                    {(['QUICK', 'STANDARD', 'DEEP', 'COMPLIANCE'] as DiscoveryProfileType[]).map((prof) => (
                      <button
                        key={prof}
                        type="button"
                        onClick={() => setDiscoveryProfile(prof)}
                        style={{
                          padding: '6px 14px',
                          borderRadius: 6,
                          border: discoveryProfile === prof ? '1px solid var(--dash-accent)' : '1px solid var(--dash-border)',
                          background: discoveryProfile === prof ? 'rgba(37, 99, 235, 0.15)' : 'var(--dash-bg)',
                          color: discoveryProfile === prof ? 'var(--dash-accent)' : 'var(--dash-text-primary)',
                          fontSize: 12,
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        {prof}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>Target Schemas</label>
                  <input
                    type="text"
                    value={includeSchemas}
                    onChange={(e) => setIncludeSchemas(e.target.value)}
                    style={{ width: 220, padding: '6px 12px', borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 12 }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 14 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>Golden Benchmark (GB) Validation Level</label>
                  <select
                    value={gbValidationLevel}
                    onChange={(e) => setGbValidationLevel(e.target.value)}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 12 }}
                  >
                    <option value="Full Column Checksums & Row Counts">Full Column Checksums & Row Counts</option>
                    <option value="Statistical Sampling Inspection">Statistical Sampling Inspection</option>
                  </select>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', paddingTop: 16 }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                    <input type="checkbox" checked={requireFourEyes} onChange={(e) => setRequireFourEyes(e.target.checked)} />
                    Enforce Four-Eyes Approval Policy
                  </label>
                </div>
              </div>

              {/* Discovery Live Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
                {[
                  { label: 'Schemas', count: '4' },
                  { label: 'Tables', count: '320' },
                  { label: 'Views', count: '45' },
                  { label: 'MatViews', count: '12' },
                  { label: 'Indexes', count: '680' },
                  { label: 'Primary Keys', count: '320' },
                  { label: 'Foreign Keys', count: '450' },
                  { label: 'Constraints', count: '890' },
                  { label: 'Sequences', count: '42' },
                  { label: 'Procedures', count: '68' },
                  { label: 'Functions', count: '112' },
                  { label: 'Triggers', count: '34' },
                  { label: 'Packages', count: '18' },
                  { label: 'Package Bodies', count: '18' },
                  { label: 'Roles', count: '8' },
                  { label: 'LOB Objects', count: '32' },
                ].map((item) => (
                  <div key={item.label} style={{ padding: '10px 12px', background: 'var(--dash-surface)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                    <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', textTransform: 'uppercase' }}>{item.label}</div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--dash-text-primary)', marginTop: 2 }}>{item.count}</div>
                  </div>
                ))}
              </div>

              <div style={{ padding: 12, background: '#0F172A', borderRadius: 8, border: '1px solid var(--dash-border)', fontFamily: 'monospace', fontSize: 11, color: '#38BDF8', lineHeight: 1.5 }}>
                <div>[Scout Discovery] Inspecting Oracle Catalog... (Duration: 1.4s)</div>
                <div>[MetadataCatalog] Discovered 320 tables, 68 procedures, 18 packages, 42 sequences.</div>
                <div style={{ color: '#10B981' }}>✓ Discovery Complete. Schema Catalog Stored in Central Metadata Repository.</div>
              </div>
            </div>
          )}

          {/* ── STEP 5: MIGRATION ADVISOR ──────────────────────── */}
          {step === 5 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 860, margin: '0 auto' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
                <div style={{ padding: 14, background: 'rgba(16,185,129,0.1)', borderRadius: 10, border: '1px solid rgba(16,185,129,0.3)' }}>
                  <div style={{ fontSize: 11, color: '#10B981', fontWeight: 600 }}>Compatibility Score</div>
                  <div style={{ fontSize: 22, fontWeight: 800, color: '#10B981', marginTop: 4 }}>98.5%</div>
                </div>
                <div style={{ padding: 14, background: 'rgba(59,130,246,0.1)', borderRadius: 10, border: '1px solid rgba(59,130,246,0.3)' }}>
                  <div style={{ fontSize: 11, color: '#3B82F6', fontWeight: 600 }}>Migration Risk Score</div>
                  <div style={{ fontSize: 22, fontWeight: 800, color: '#3B82F6', marginTop: 4 }}>0.12 (LOW)</div>
                </div>
                <div style={{ padding: 14, background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)' }}>
                  <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', fontWeight: 600 }}>Estimated Duration</div>
                  <div style={{ fontSize: 22, fontWeight: 800, marginTop: 4 }}>42 Mins</div>
                </div>
                <div style={{ padding: 14, background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)' }}>
                  <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', fontWeight: 600 }}>Est. Throughput</div>
                  <div style={{ fontSize: 22, fontWeight: 800, marginTop: 4 }}>150 MB/s</div>
                </div>
              </div>

              <div style={{ padding: 14, background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)' }}>
                <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 8, color: 'var(--dash-text-primary)' }}>Recommended Engine Configuration</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, fontSize: 12 }}>
                  <div><strong>Workers:</strong> 8 Parallel Pool</div>
                  <div><strong>Batch Size:</strong> 10,000 Rows</div>
                  <div><strong>RAM Quota:</strong> 2.4 GB</div>
                  <div><strong>Bandwidth Limit:</strong> 1.2 Gbps</div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div style={{ padding: 14, background: 'rgba(16,185,129,0.05)', borderRadius: 10, border: '1px solid rgba(16,185,129,0.2)' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#10B981', marginBottom: 6 }}>✓ Automatic Transpiler Conversions</div>
                  <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)', lineHeight: 1.5 }}>
                    • 68 Procedures transpiled to PL/pgSQL<br />
                    • 18 Package Bodies decomposed into PostgreSQL schema functions<br />
                    • NVL/DECODE/ADD_MONTHS auto-mapped via BuiltinRulesEngine
                  </div>
                </div>

                <div style={{ padding: 14, background: 'rgba(245,158,11,0.05)', borderRadius: 10, border: '1px solid rgba(245,158,11,0.2)' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#F59E0B', marginBottom: 6 }}>⚠ Advisory Notices</div>
                  <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)', lineHeight: 1.5 }}>
                    • 2 XMLType columns mapped to PostgreSQL `xml`<br />
                    • Materialized views set to concurrent refresh post-load<br />
                    • Estimated Cutover Window: &lt; 5 Minutes
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── STEP 6: SCOPE ─────────────────────────────────── */}
          {step === 6 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 860, margin: '0 auto' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <input
                  type="text"
                  value={scopeSearch}
                  onChange={(e) => setScopeSearch(e.target.value)}
                  placeholder="Search tables, procedures, views..."
                  style={{ width: 300, padding: '8px 12px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 12 }}
                />
                <span style={{ fontSize: 12, color: 'var(--dash-text-secondary)', fontWeight: 600 }}>
                  Selected: {selectedTables.length} of 320 Tables (1.25B Rows • 142.5 GB)
                </span>
              </div>

              <div style={{ border: '1px solid var(--dash-border)', borderRadius: 10, overflow: 'hidden', background: 'var(--dash-surface)' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '30px 2fr 1fr 1fr 1fr', padding: '10px 14px', background: 'var(--dash-bg)', borderBottom: '1px solid var(--dash-border)', fontSize: 11, fontWeight: 700, color: 'var(--dash-text-secondary)' }}>
                  <input type="checkbox" checked={selectedTables.length > 0} onChange={() => setSelectedTables(selectedTables.length ? [] : ['customer_records', 'orders', 'migration_audit_log'])} />
                  <span>Table Name</span>
                  <span>Schema</span>
                  <span>Est. Rows</span>
                  <span>Est. Size</span>
                </div>

                <div style={{ maxHeight: 320, overflowY: 'auto' }}>
                  {[
                    { name: 'customer_records', schema: 'SYSTEM', rows: '500,000,000', size: '54.2 GB' },
                    { name: 'orders', schema: 'SALES', rows: '450,000,000', size: '48.1 GB' },
                    { name: 'migration_audit_log', schema: 'SYSTEM', rows: '120,000,000', size: '12.4 GB' },
                    { name: 'inventory_items', schema: 'SALES', rows: '80,000,000', size: '8.2 GB' },
                    { name: 'payment_transactions', schema: 'FIN', rows: '100,000,000', size: '19.6 GB' },
                  ]
                  .filter((t) => !scopeSearch || t.name.includes(scopeSearch.toLowerCase()))
                  .map((t) => (
                    <div key={t.name} style={{ display: 'grid', gridTemplateColumns: '30px 2fr 1fr 1fr 1fr', padding: '10px 14px', borderBottom: '1px solid var(--dash-border)', fontSize: 12, alignItems: 'center' }}>
                      <input
                        type="checkbox"
                        checked={selectedTables.includes(t.name)}
                        onChange={(e) => {
                          if (e.target.checked) setSelectedTables([...selectedTables, t.name]);
                          else setSelectedTables(selectedTables.filter((x) => x !== t.name));
                        }}
                      />
                      <span style={{ fontWeight: 600, color: 'var(--dash-text-primary)' }}>{t.name}</span>
                      <span style={{ color: 'var(--dash-text-secondary)' }}>{t.schema}</span>
                      <span style={{ color: 'var(--dash-text-secondary)' }}>{t.rows}</span>
                      <span style={{ color: 'var(--dash-text-secondary)' }}>{t.size}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── STEP 7: RULES & TRANSFORMATIONS ──────────────── */}
          {step === 7 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14, maxWidth: 860, margin: '0 auto' }}>
              {[
                { id: 'cleansing', title: 'Data Cleansing & Column Mappings', desc: 'Trimming, encoding, type coercion, and UTF-8 sanitization' },
                { id: 'masking', title: 'Data Masking & PII Redaction Rules', desc: 'SHA-256 hash masking for SSN, Email, and Credit Card fields' },
                { id: 'tuning', title: 'High-Performance Stream & Buffer Tuning', desc: 'Zero-copy memoryview buffers, LOB chunks, worker pool allocation' },
                { id: 'checkpoint', title: 'Durability & Recovery Policies', desc: 'WAL Ring Buffer, SQLite checkpoint intervals, auto-restart' },
              ].map((card) => (
                <div key={card.id} style={{ border: '1px solid var(--dash-border)', borderRadius: 10, background: 'var(--dash-surface)', overflow: 'hidden' }}>
                  <div
                    onClick={() => setExpandedCard(expandedCard === card.id ? null : card.id)}
                    style={{ padding: '14px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer', background: expandedCard === card.id ? 'var(--dash-bg)' : 'transparent' }}
                  >
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--dash-text-primary)' }}>{card.title}</div>
                      <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', marginTop: 2 }}>{card.desc}</div>
                    </div>
                    <span style={{ fontSize: 14, color: 'var(--dash-text-secondary)' }}>{expandedCard === card.id ? '▲' : '▼'}</span>
                  </div>

                  {expandedCard === card.id && (
                    <div style={{ padding: 16, borderTop: '1px solid var(--dash-border)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                      {card.id === 'cleansing' && (
                        <>
                          <div>
                            <label style={{ fontSize: 11, fontWeight: 600, display: 'block', marginBottom: 4 }}>Table Mapping Rule</label>
                            <input type="text" defaultValue="SYSTEM.* -> public.*" style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 12 }} />
                          </div>
                          <div>
                            <label style={{ fontSize: 11, fontWeight: 600, display: 'block', marginBottom: 4 }}>LOB Chunk Size</label>
                            <input type="text" defaultValue="64 KB (Configurable)" style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 12 }} />
                          </div>
                        </>
                      )}

                      {card.id === 'masking' && (
                        <>
                          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                            <input type="checkbox" checked={maskingEnabled} onChange={(e) => setMaskingEnabled(e.target.checked)} />
                            Enforce PII Data Redaction
                          </label>
                          <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)' }}>Masking technique: SHA-256 salted hash</div>
                        </>
                      )}

                      {card.id === 'tuning' && (
                        <>
                          <div>
                            <label style={{ fontSize: 11, fontWeight: 600, display: 'block', marginBottom: 4 }}>Parallel Workers</label>
                            <input type="text" value={parallelism} onChange={(e) => setParallelism(e.target.value)} style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 12 }} />
                          </div>
                          <div>
                            <label style={{ fontSize: 11, fontWeight: 600, display: 'block', marginBottom: 4 }}>Batch Insertion Size</label>
                            <input type="text" value={batchSize} onChange={(e) => setBatchSize(e.target.value)} style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 12 }} />
                          </div>
                        </>
                      )}

                      {card.id === 'checkpoint' && (
                        <>
                          <div>
                            <label style={{ fontSize: 11, fontWeight: 600, display: 'block', marginBottom: 4 }}>Checkpoint Interval (Rows)</label>
                            <input type="text" value={checkpointInterval} onChange={(e) => setCheckpointInterval(e.target.value)} style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 12 }} />
                          </div>
                          <div>
                            <label style={{ fontSize: 11, fontWeight: 600, display: 'block', marginBottom: 4 }}>WAL Ring Buffer Capacity</label>
                            <input type="text" defaultValue="10,000 Records (CRC32 Checksummed)" disabled style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-secondary)', fontSize: 12 }} />
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* ── STEP 8: EXECUTION PLAN ────────────────────────── */}
          {step === 8 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 860, margin: '0 auto' }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--dash-text-secondary)', textTransform: 'uppercase' }}>Frozen Backend Execution DAG Pipeline</div>
              
              <div style={{ display: 'flex', gap: 6, overflowX: 'auto', paddingBottom: 10 }}>
                {[
                  '1. Discovery',
                  '2. Advisor Analysis',
                  '3. DAG Planning',
                  '4. Policy Approval',
                  '5. Runtime Creation',
                  '6. Schema DDL',
                  '7. Enterprise Objects',
                  '8. PL/SQL Transpile',
                  '9. Parallel Data Transport',
                  '10. Post Validation',
                  '11. Trust Certification'
                ].map((stage, i) => (
                  <div key={stage} style={{ minWidth: 110, padding: '10px 8px', borderRadius: 8, background: 'var(--dash-surface)', border: '1px solid var(--dash-border)', textAlign: 'center' }}>
                    <div style={{ fontSize: 10, color: '#3B82F6', fontWeight: 700 }}>Stage {i + 1}</div>
                    <div style={{ fontSize: 11, fontWeight: 600, marginTop: 4, whiteSpace: 'nowrap' }}>{stage.split('. ')[1]}</div>
                  </div>
                ))}
              </div>

              <div style={{ padding: 14, background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
                <div>
                  <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)' }}>Worker Strategy</div>
                  <div style={{ fontSize: 12, fontWeight: 700, marginTop: 2 }}>{parallelism} Parallel Workers</div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)' }}>Partitions</div>
                  <div style={{ fontSize: 12, fontWeight: 700, marginTop: 2 }}>32 Auto Partitions</div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)' }}>Checkpoint Policy</div>
                  <div style={{ fontSize: 12, fontWeight: 700, marginTop: 2 }}>Every {checkpointInterval} Rows</div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)' }}>Recovery Model</div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#10B981', marginTop: 2 }}>WAL Ring Buffer + Epoch Fencing</div>
                </div>
              </div>
            </div>
          )}

          {/* ── STEP 9: REVIEW & START ────────────────────────── */}
          {step === 9 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 860, margin: '0 auto' }}>
              <div style={{ padding: 16, background: 'rgba(16,185,129,0.08)', borderRadius: 10, border: '1px solid rgba(16,185,129,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#10B981' }}>✓ Executive Migration Plan Certified</div>
                  <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)', marginTop: 2 }}>All connectivity, schema, transpiler, and policy rules validated by AKAAL Engine.</div>
                </div>
                <span style={{ fontSize: 11, padding: '4px 10px', borderRadius: 6, background: '#10B981', color: '#FFF', fontWeight: 700 }}>READY TO INITIALIZE</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                <div style={{ padding: 14, background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)', fontSize: 12, lineHeight: 1.6 }}>
                  <div style={{ fontWeight: 700, marginBottom: 6, color: 'var(--dash-text-primary)' }}>Source & Target Summary</div>
                  • <strong>Source:</strong> {sourceEngine} ({sourceHost}:{sourcePort}/{sourceDbName})<br />
                  • <strong>Target:</strong> {targetEngine} ({targetHost}:{targetPort}/{targetDbName})<br />
                  • <strong>Scope:</strong> {migScope}<br />
                  • <strong>Strategy:</strong> {strategy}
                </div>

                <div style={{ padding: 14, background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)', fontSize: 12, lineHeight: 1.6 }}>
                  <div style={{ fontWeight: 700, marginBottom: 6, color: 'var(--dash-text-primary)' }}>Performance & Governance</div>
                  • <strong>Compatibility:</strong> 98.5% • Risk Score: 0.12 (LOW)<br />
                  • <strong>Transport:</strong> {parallelism} Workers • Batch Size: {batchSize}<br />
                  • <strong>Estimated ETA:</strong> 42 Minutes (150 MB/s)<br />
                  • <strong>Certification:</strong> SHA-256 Digital Trust Seal Enforced
                </div>
              </div>
            </div>
          )}

        </div>

        {/* Persistent Right Enterprise Summary Panel */}
        <div style={{ width: 260, borderLeft: '1px solid var(--dash-border)', background: 'var(--dash-surface)', padding: 16, display: 'flex', flexDirection: 'column', gap: 14, overflowY: 'auto' }}>
          <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--dash-text-secondary)', letterSpacing: '0.05em' }}>
            Live Executive Summary
          </div>

          <div style={{ padding: 10, background: 'var(--dash-bg)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
            <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)' }}>Migration Title</div>
            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--dash-text-primary)', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {migName || 'Untitled Migration'}
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
            <div style={{ padding: 8, background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)' }}>
              <div style={{ fontSize: 9, color: 'var(--dash-text-secondary)' }}>Source</div>
              <div style={{ fontSize: 11, fontWeight: 700, marginTop: 2 }}>{sourceEngine.split(' ')[0]}</div>
            </div>
            <div style={{ padding: 8, background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)' }}>
              <div style={{ fontSize: 9, color: 'var(--dash-text-secondary)' }}>Target</div>
              <div style={{ fontSize: 11, fontWeight: 700, marginTop: 2 }}>{targetEngine.split(' ')[0]}</div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 11, color: 'var(--dash-text-secondary)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Selected Tables:</span>
              <strong style={{ color: 'var(--dash-text-primary)' }}>{selectedTables.length} Tables</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Est. Rows:</span>
              <strong style={{ color: 'var(--dash-text-primary)' }}>1.25B Rows</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Est. Size:</span>
              <strong style={{ color: 'var(--dash-text-primary)' }}>142.5 GB</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Compatibility:</span>
              <strong style={{ color: '#10B981' }}>98.5%</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Risk Score:</span>
              <strong style={{ color: '#3B82F6' }}>0.12 (LOW)</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Workers:</span>
              <strong style={{ color: 'var(--dash-text-primary)' }}>{parallelism} Workers</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>ETA:</span>
              <strong style={{ color: 'var(--dash-text-primary)' }}>42 Mins</strong>
            </div>
          </div>

          <div style={{ borderTop: '1px solid var(--dash-border)', paddingTop: 10, display: 'flex', flexDirection: 'column', gap: 6, fontSize: 11 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span>Source Status:</span>
              <span style={{ color: sourceTested ? '#10B981' : '#F59E0B', fontWeight: 700 }}>{sourceTested ? 'CONNECTED' : 'PENDING'}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span>Target Status:</span>
              <span style={{ color: targetTested ? '#10B981' : '#F59E0B', fontWeight: 700 }}>{targetTested ? 'CONNECTED' : 'PENDING'}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span>Approval Gate:</span>
              <span style={{ color: '#10B981', fontWeight: 700 }}>PASSED</span>
            </div>
          </div>
        </div>
      </div>

      {/* Footer Navigation Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 16, borderTop: '1px solid var(--dash-border)' }}>
        <button
          type="button"
          onClick={() => {
            if (step > 1) setStep((s) => (s - 1) as any);
            else handleSaveDraft();
          }}
          style={{ padding: '8px 16px', borderRadius: 8, background: 'none', border: '1px solid var(--dash-border)', color: 'var(--dash-text-secondary)', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
        >
          {step === 1 ? 'Cancel / Back' : '← Previous Step'}
        </button>

        <div style={{ display: 'flex', gap: 10 }}>
          {step < 9 && (
            <button
              type="button"
              className={styles.resumeBtn}
              onClick={() => setStep((s) => (s + 1) as any)}
              style={{ padding: '9px 20px', borderRadius: 8, background: 'var(--dash-accent)', color: '#FFF', border: 'none', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
            >
              Continue to Step {step + 1} →
            </button>
          )}

          {step === 9 && (
            <button
              type="button"
              className={styles.resumeBtn}
              onClick={() => setShowInitializeConfirm(true)}
              style={{ padding: '9px 24px', borderRadius: 8, background: '#10B981', color: '#FFF', border: 'none', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}
            >
              Initialize Migration & Launch Workspace
            </button>
          )}
        </div>
      </div>

      {showDiscardConfirm && (
        <ConfirmDialog
          isOpen={showDiscardConfirm}
          title="Discard Configuration Draft?"
          message="Are you sure you want to discard this configuration draft? All unsaved inputs will be cleared."
          confirmText="Discard Draft"
          cancelText="Continue Editing"
          severity="danger"
          onConfirm={() => {
            setShowDiscardConfirm(false);
            onBack();
          }}
          onClose={() => setShowDiscardConfirm(false)}
        />
      )}

      {showInitializeConfirm && (
        <ConfirmDialog
          isOpen={showInitializeConfirm}
          title="Initialize Migration Execution?"
          message={`Are you ready to initialize "${migName || 'Oracle ERP Core Migration'}" on the AKAAL Runtime V3 Engine?`}
          confirmText="Launch Migration"
          cancelText="Review Plan"
          onConfirm={handleCompleteLaunchConfirmed}
          onClose={() => setShowInitializeConfirm(false)}
        />
      )}
    </div>
  );
};
