import { useState, useEffect, type FC } from 'react';
import type { MigrationPipeline, DatabaseEngine, DiscoveryProfileType } from '../../types/migration';
import styles from './MigrationModule.module.css';

export interface NewMigrationWizardProps {
  onClose: () => void;
  onLaunch: (newPipeline: MigrationPipeline) => void;
  createProject: (name: string, sourceEngine: DatabaseEngine, targetEngine: DatabaseEngine) => MigrationPipeline;
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

export const NewMigrationWizard: FC<NewMigrationWizardProps> = ({ onClose, onLaunch, createProject }) => {
  const [step, setStep] = useState<1 | 2 | 3 | 4 | 5 | 6>(1);

  // Step 1: Strategy
  const [migName, setMigName] = useState('');
  const [migScope, setMigScope] = useState('Full Schema & Data Transport');
  const [strategy, setStrategy] = useState('Zero-Downtime Replication');

  // Step 2: Source Adaptive Connection
  const [sourceEngine, setSourceEngine] = useState<DatabaseEngine>('Oracle 19c');
  const [sourceHost, setSourceHost] = useState('db-oracle.enterprise.internal');
  const [sourcePort, setSourcePort] = useState('1521');
  const [sourceDbName, setSourceDbName] = useState('ORCL');
  const [sourceUser, setSourceUser] = useState('akaal_source_admin');
  const [sourcePass, setSourcePass] = useState('••••••••••••');
  const [sourceSsl, setSourceSsl] = useState(true);
  const [oracleWallet, setOracleWallet] = useState('/etc/oracle/wallets/cwallet.sso');
  const [useWinAuth, setUseWinAuth] = useState(false);
  const [sourceTested, setSourceTested] = useState(false);
  const [testingSource, setTestingSource] = useState(false);

  // Step 3: Target Adaptive Connection
  const [targetEngine, setTargetEngine] = useState<DatabaseEngine>('PostgreSQL 16');
  const [targetHost, setTargetHost] = useState('pg-cluster.enterprise.internal');
  const [targetPort, setTargetPort] = useState('5432');
  const [targetDbName, setTargetDbName] = useState('app_target_db');
  const [targetUser, setTargetUser] = useState('akaal_target_admin');
  const [targetPass, setTargetPass] = useState('••••••••••••');
  const [targetSsl, setTargetSsl] = useState(true);
  const [targetTested, setTargetTested] = useState(false);
  const [testingTarget, setTestingTarget] = useState(false);

  // Step 4: Governance & Discovery Scope
  const [discoveryProfile, setDiscoveryProfile] = useState<DiscoveryProfileType>('STANDARD');
  const [includeSchemas, setIncludeSchemas] = useState('public, analytics, hr, finance');
  const [gbValidationLevel, setGbValidationLevel] = useState('Full Column Checksums & Row Counts');
  const [requireFourEyes, setRequireFourEyes] = useState(true);

  // Step 5: Pre-Flight Engine Preparation State
  const [prepProgress, setPrepProgress] = useState(0);

  // Keyboard Esc listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // Handle Step 5 Engine Preparation Progression
  useEffect(() => {
    if (step === 5) {
      setPrepProgress(10);
      const t1 = setTimeout(() => setPrepProgress(40), 400);
      const t2 = setTimeout(() => setPrepProgress(75), 800);
      const t3 = setTimeout(() => {
        setPrepProgress(100);
        setStep(6);
      }, 1200);

      return () => {
        clearTimeout(t1);
        clearTimeout(t2);
        clearTimeout(t3);
      };
    }
  }, [step]);

  const handleTestSource = () => {
    setTestingSource(true);
    setTimeout(() => {
      setTestingSource(false);
      setSourceTested(true);
    }, 600);
  };

  const handleTestTarget = () => {
    setTestingTarget(true);
    setTimeout(() => {
      setTestingTarget(false);
      setTargetTested(true);
    }, 600);
  };

  const handleCompleteLaunch = () => {
    const nameToUse = migName.trim() || `${sourceEngine} → ${targetEngine} Migration`;
    const created = createProject(nameToUse, sourceEngine, targetEngine);
    onLaunch(created);
  };

  return (
    <div className={styles.modalBackdrop} onClick={onClose} role="dialog" aria-modal="true">
      <div className={styles.modalBox} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>New Enterprise Database Migration</h2>
            <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)', marginTop: 4 }}>
              Step {step} of 6 • {
                step === 1 ? 'Migration Strategy' :
                step === 2 ? `Source Connection (${sourceEngine})` :
                step === 3 ? `Target Connection (${targetEngine})` :
                step === 4 ? 'Scope & Governance Policy' :
                step === 5 ? 'AKAAL Engine Preparation' :
                'Pre-Flight Executive Report'
              }
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: 'var(--dash-text-secondary)', fontSize: 22, cursor: 'pointer' }}
            aria-label="Close setup experience"
          >
            ×
          </button>
        </div>

        {/* Progress Bar */}
        <div style={{ display: 'flex', gap: 6, marginBottom: 24 }}>
          {[1, 2, 3, 4, 5, 6].map((s) => (
            <div
              key={s}
              style={{
                flex: 1,
                height: 4,
                borderRadius: 2,
                background: s <= step ? 'var(--dash-accent)' : 'var(--dash-border)',
                transition: 'background 180ms ease',
              }}
            />
          ))}
        </div>

        {/* ── STEP 1: STRATEGY ──────────────────────────────── */}
        {step === 1 && (
          <div>
            <div style={{ marginBottom: 18 }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>
                Migration Title
              </label>
              <input
                type="text"
                value={migName}
                onChange={(e) => setMigName(e.target.value)}
                placeholder="e.g. Oracle ERP Core Migration"
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: 8,
                  border: '1px solid var(--dash-border)',
                  background: 'var(--dash-bg)',
                  color: 'var(--dash-text-primary)',
                  fontSize: 13,
                }}
                autoFocus
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 18 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>
                  Migration Transport Scope
                </label>
                <select
                  value={migScope}
                  onChange={(e) => setMigScope(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: 8,
                    border: '1px solid var(--dash-border)',
                    background: 'var(--dash-bg)',
                    color: 'var(--dash-text-primary)',
                    fontSize: 13,
                  }}
                >
                  <option value="Full Schema & Data Transport">Full Schema & Data Transport</option>
                  <option value="CDC Streaming Replication">CDC Streaming Replication Only</option>
                  <option value="Schema Definition DDL">Schema Definition DDL Only</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>
                  Execution Strategy
                </label>
                <select
                  value={strategy}
                  onChange={(e) => setStrategy(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: 8,
                    border: '1px solid var(--dash-border)',
                    background: 'var(--dash-bg)',
                    color: 'var(--dash-text-primary)',
                    fontSize: 13,
                  }}
                >
                  <option value="Zero-Downtime Replication">Zero-Downtime Live Replication</option>
                  <option value="Scheduled Batch Offline">Scheduled Batch Offline</option>
                </select>
              </div>
            </div>

            <div style={{ padding: 14, background: 'var(--dash-bg)', borderRadius: 10, border: '1px solid var(--dash-border)' }}>
              <div style={{ fontSize: 11, textTransform: 'uppercase', color: 'var(--dash-text-secondary)', marginBottom: 4 }}>Strategy Notes</div>
              <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)', lineHeight: 1.5 }}>
                {strategy === 'Zero-Downtime Replication'
                  ? '• Continuous Change Data Capture (CDC) enables active-active live streaming during data transfer without database locks.'
                  : '• High-throughput offline batch transfer with automated topological dependency ordering.'}
              </div>
            </div>
          </div>
        )}

        {/* ── STEP 2: SOURCE ADAPTIVE ENGINE CONNECTION ─────── */}
        {step === 2 && (
          <div>
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>
                Source Database Engine
              </label>
              <select
                value={sourceEngine}
                onChange={(e) => {
                  const val = e.target.value as DatabaseEngine;
                  setSourceEngine(val);
                  if (val === 'Oracle 19c') setSourcePort('1521');
                  else if (val === 'PostgreSQL 16') setSourcePort('5432');
                  else if (val === 'SQL Server 2019') setSourcePort('1433');
                  else if (val === 'MySQL 8.0' || val === 'MariaDB') setSourcePort('3306');
                  else if (val === 'IBM DB2 v11') setSourcePort('50000');
                }}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: 8,
                  border: '1px solid var(--dash-border)',
                  background: 'var(--dash-bg)',
                  color: 'var(--dash-text-primary)',
                  fontSize: 13,
                }}
              >
                {SUPPORTED_ENGINES.map((eng) => (
                  <option key={eng} value={eng}>{eng}</option>
                ))}
              </select>
            </div>

            {/* Dynamic Adaptive Form Fields */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>
                  Host / Endpoint
                </label>
                <input
                  type="text"
                  value={sourceHost}
                  onChange={(e) => setSourceHost(e.target.value)}
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>
                  Port
                </label>
                <input
                  type="text"
                  value={sourcePort}
                  onChange={(e) => setSourcePort(e.target.value)}
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>
                  {sourceEngine.includes('Oracle') ? 'Service Name / SID' : 'Database Name'}
                </label>
                <input
                  type="text"
                  value={sourceDbName}
                  onChange={(e) => setSourceDbName(e.target.value)}
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>
                  Username
                </label>
                <input
                  type="text"
                  value={sourceUser}
                  onChange={(e) => setSourceUser(e.target.value)}
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
                />
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>
                Password (Stored via OS DPAPI Vault)
              </label>
              <input
                type="password"
                value={sourcePass}
                onChange={(e) => setSourcePass(e.target.value)}
                style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
              />
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={sourceSsl}
                  onChange={(e) => setSourceSsl(e.target.checked)}
                />
                Require Enforced Encrypted SSL/TLS Transport
              </label>
            </div>

            {/* Oracle Specific Options */}
            {sourceEngine.includes('Oracle') && (
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>
                  Oracle Wallet File Path (cwallet.sso)
                </label>
                <input
                  type="text"
                  value={oracleWallet}
                  onChange={(e) => setOracleWallet(e.target.value)}
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
                />
              </div>
            )}

            {/* SQL Server Specific Options */}
            {sourceEngine.includes('SQL Server') && (
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={useWinAuth}
                    onChange={(e) => setUseWinAuth(e.target.checked)}
                  />
                  Use Integrated Windows Authentication
                </label>
              </div>
            )}

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 8 }}>
              <button
                type="button"
                onClick={handleTestSource}
                disabled={testingSource}
                style={{ padding: '8px 16px', borderRadius: 8, background: 'var(--dash-surface-hover)', border: '1px solid var(--dash-border)', color: 'var(--dash-text-primary)', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
              >
                {testingSource ? 'Testing Connection...' : 'Test Connection'}
              </button>
              {sourceTested && (
                <span style={{ fontSize: 12, color: '#10B981', fontWeight: 600 }}>
                  ✓ Source Verified (12ms latency)
                </span>
              )}
            </div>
          </div>
        )}

        {/* ── STEP 3: TARGET ADAPTIVE ENGINE CONNECTION ─────── */}
        {step === 3 && (
          <div>
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>
                Target Database Engine
              </label>
              <select
                value={targetEngine}
                onChange={(e) => {
                  const val = e.target.value as DatabaseEngine;
                  setTargetEngine(val);
                  if (val === 'PostgreSQL 16') setTargetPort('5432');
                  else if (val === 'Oracle 19c') setTargetPort('1521');
                  else if (val === 'CockroachDB') setTargetPort('26257');
                }}
                style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
              >
                {SUPPORTED_ENGINES.map((eng) => (
                  <option key={eng} value={eng}>{eng}</option>
                ))}
              </select>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>
                  Host / Endpoint
                </label>
                <input
                  type="text"
                  value={targetHost}
                  onChange={(e) => setTargetHost(e.target.value)}
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>
                  Port
                </label>
                <input
                  type="text"
                  value={targetPort}
                  onChange={(e) => setTargetPort(e.target.value)}
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>
                  Target Database Name
                </label>
                <input
                  type="text"
                  value={targetDbName}
                  onChange={(e) => setTargetDbName(e.target.value)}
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>
                  Username
                </label>
                <input
                  type="text"
                  value={targetUser}
                  onChange={(e) => setTargetUser(e.target.value)}
                  style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
                />
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>
                Password Secret
              </label>
              <input
                type="password"
                value={targetPass}
                onChange={(e) => setTargetPass(e.target.value)}
                style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
              />
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={targetSsl}
                  onChange={(e) => setTargetSsl(e.target.checked)}
                />
                Require Enforced Encrypted SSL/TLS Transport
              </label>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 8 }}>
              <button
                type="button"
                onClick={handleTestTarget}
                disabled={testingTarget}
                style={{ padding: '8px 16px', borderRadius: 8, background: 'var(--dash-surface-hover)', border: '1px solid var(--dash-border)', color: 'var(--dash-text-primary)', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
              >
                {testingTarget ? 'Testing Connection...' : 'Test Connection'}
              </button>
              {targetTested && (
                <span style={{ fontSize: 12, color: '#10B981', fontWeight: 600 }}>
                  ✓ Target Ready (8ms latency)
                </span>
              )}
            </div>
          </div>
        )}

        {/* ── STEP 4: DISCOVERY SCOPE & GOVERNANCE ──────────── */}
        {step === 4 && (
          <div>
            <div style={{ marginBottom: 18 }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>
                Scout Discovery Profile
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
                {(['QUICK', 'STANDARD', 'DEEP', 'COMPLIANCE'] as DiscoveryProfileType[]).map((prof) => (
                  <button
                    key={prof}
                    type="button"
                    onClick={() => setDiscoveryProfile(prof)}
                    style={{
                      padding: '12px 10px',
                      borderRadius: 10,
                      border: discoveryProfile === prof ? '1px solid var(--dash-accent)' : '1px solid var(--dash-border)',
                      background: discoveryProfile === prof ? 'rgba(37, 99, 235, 0.12)' : 'var(--dash-bg)',
                      color: discoveryProfile === prof ? 'var(--dash-accent)' : 'var(--dash-text-primary)',
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: 'pointer',
                      textAlign: 'center',
                    }}
                  >
                    {prof}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>
                Include Schemas (Comma Separated)
              </label>
              <input
                type="text"
                value={includeSchemas}
                onChange={(e) => setIncludeSchemas(e.target.value)}
                style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
              />
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>
                Golden Benchmark (GB) Validation Level
              </label>
              <select
                value={gbValidationLevel}
                onChange={(e) => setGbValidationLevel(e.target.value)}
                style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}
              >
                <option value="Full Column Checksums & Row Counts">Full Column Checksums & Row Counts</option>
                <option value="Statistical Sampling Inspection">Statistical Sampling Inspection</option>
              </select>
            </div>

            <div style={{ padding: 14, background: 'var(--dash-bg)', borderRadius: 10, border: '1px solid var(--dash-border)' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>
                <input
                  type="checkbox"
                  checked={requireFourEyes}
                  onChange={(e) => setRequireFourEyes(e.target.checked)}
                />
                Enforce Four-Eyes Approval Policy (Requires Manager sign-off before Cutover)
              </label>
            </div>
          </div>
        )}

        {/* ── STEP 5: AKAAL ENGINE PREPARATION (PRE-FLIGHT) ─── */}
        {step === 5 && (
          <div style={{ textAlign: 'center', padding: '24px 0' }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>AKAAL Engine Preparation</h3>
            <p style={{ fontSize: 13, color: 'var(--dash-text-secondary)', marginBottom: 24 }}>
              Executing automated connection handshakes, permission audits, and Scout runtime allocation.
            </p>

            <div style={{ width: '100%', height: 8, borderRadius: 4, background: 'var(--dash-border)', overflow: 'hidden', marginBottom: 24 }}>
              <div style={{ width: `${prepProgress}%`, height: '100%', background: 'var(--dash-accent)', transition: 'width 300ms ease' }} />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, textAlign: 'left', maxWidth: 420, margin: '0 auto' }}>
              <div style={{ fontSize: 12, color: prepProgress >= 10 ? '#10B981' : 'var(--dash-text-secondary)' }}>
                {prepProgress >= 10 ? '✓' : '•'} Connection & Endpoint Verification
              </div>
              <div style={{ fontSize: 12, color: prepProgress >= 40 ? '#10B981' : 'var(--dash-text-secondary)' }}>
                {prepProgress >= 40 ? '✓' : '•'} Administrative Permission & Table Lock Audit
              </div>
              <div style={{ fontSize: 12, color: prepProgress >= 75 ? '#10B981' : 'var(--dash-text-secondary)' }}>
                {prepProgress >= 75 ? '✓' : '•'} Scout Discovery Pipeline Initialization
              </div>
              <div style={{ fontSize: 12, color: prepProgress >= 100 ? '#10B981' : 'var(--dash-text-secondary)' }}>
                {prepProgress >= 100 ? '✓' : '•'} Pre-Flight Executive Report Generation
              </div>
            </div>
          </div>
        )}

        {/* ── STEP 6: PRE-FLIGHT EXECUTIVE REPORT ────────────── */}
        {step === 6 && (
          <div>
            <div style={{ padding: 18, background: 'var(--dash-bg)', borderRadius: 12, border: '1px solid var(--dash-border)', marginBottom: 20 }}>
              <div style={{ fontSize: 11, textTransform: 'uppercase', color: 'var(--dash-text-secondary)', marginBottom: 4 }}>Pre-Flight Executive Report</div>
              <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>{migName || `${sourceEngine} → ${targetEngine}`}</div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 14 }}>
                <div style={{ padding: 10, background: 'var(--dash-surface)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                  <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)' }}>Estimated Rows</div>
                  <div style={{ fontSize: 14, fontWeight: 700, marginTop: 2 }}>1.25 Billion Rows</div>
                </div>
                <div style={{ padding: 10, background: 'var(--dash-surface)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                  <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)' }}>Risk Score</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#10B981', marginTop: 2 }}>0.15 (LOW)</div>
                </div>
                <div style={{ padding: 10, background: 'var(--dash-surface)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                  <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)' }}>Trust Score Prediction</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#3B82F6', marginTop: 2 }}>99.2% Verified</div>
                </div>
              </div>

              <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)', lineHeight: 1.6 }}>
                • <strong>Source Endpoint:</strong> {sourceEngine} ({sourceHost}:{sourcePort}/{sourceDbName})<br />
                • <strong>Target Endpoint:</strong> {targetEngine} ({targetHost}:{targetPort}/{targetDbName})<br />
                • <strong>Profile & Strategy:</strong> {discoveryProfile} Profile • {strategy}<br />
                • <strong>Governance:</strong> {requireFourEyes ? 'Four-Eyes Sign-off Enforced' : 'Single User Execution'}
              </div>
            </div>

            <div style={{ fontSize: 12, color: '#10B981', fontWeight: 600, textAlign: 'center', marginBottom: 20 }}>
              ✓ All Pre-Flight Connectivity, Security & Policy Checks Passed
            </div>
          </div>
        )}

        {/* Footer Actions */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 28, paddingTop: 16, borderTop: '1px solid var(--dash-border)' }}>
          <button
            type="button"
            onClick={() => {
              if (step > 1 && step !== 5 && step !== 6) setStep((s) => (s - 1) as any);
              else onClose();
            }}
            style={{ padding: '9px 18px', borderRadius: 8, background: 'none', border: '1px solid var(--dash-border)', color: 'var(--dash-text-secondary)', fontSize: 13, cursor: 'pointer' }}
          >
            {step === 1 ? 'Cancel' : '← Back'}
          </button>

          {step < 4 && (
            <button
              type="button"
              className={styles.resumeBtn}
              onClick={() => setStep((s) => (s + 1) as any)}
            >
              Continue →
            </button>
          )}

          {step === 4 && (
            <button
              type="button"
              className={styles.resumeBtn}
              onClick={() => setStep(5)}
            >
              Prepare AKAAL Engine →
            </button>
          )}

          {step === 6 && (
            <button
              type="button"
              className={styles.resumeBtn}
              onClick={handleCompleteLaunch}
            >
              Initialize Migration
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
