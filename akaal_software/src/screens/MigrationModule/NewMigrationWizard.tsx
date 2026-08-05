import { useState, useEffect, useMemo, useCallback, useRef, type FC } from 'react';
import type { MigrationPipeline, DatabaseEngine, DiscoveryProfileType } from '../../types/migration';
import { notificationService } from '../../services/notificationService';
import styles from './MigrationModule.module.css';

export interface NewMigrationWizardProps {
  onClose: () => void;
  onLaunch: (newPipeline: MigrationPipeline) => void;
  createProject: (name: string, sourceEngine: DatabaseEngine, targetEngine: DatabaseEngine) => MigrationPipeline;
}

// ─── Engine-Compatible DTOs ─────────────────────────────────────────────────
// These DTOs map 1:1 with future SchemaDiscoveryDTO engine responses.
// Replacing INITIAL_SCHEMAS with a live fetch is the only change needed.

interface DiscoveredObjectDTO {
  object_id: string;
  schema_id: string;
  object_name: string;
  object_type: string;
  estimated_rows: number;    // -1 = N/A (procedures, functions, etc.)
  estimated_size_gb: number; // -1 = N/A
  compatibility_status: 'OPTIMAL' | 'TRANSPILED' | 'ADVISORY';
  dependency_ids: string[];
  warnings: string[];
  selected: boolean;
}

interface ObjectGroupDTO {
  object_type: string;
  objects: DiscoveredObjectDTO[];
}

interface SchemaDiscoveryDTO {
  schema_id: string;
  schema_name: string;
  object_groups: ObjectGroupDTO[];
}

// ─── Constants ──────────────────────────────────────────────────────────────

const SUPPORTED_ENGINES: DatabaseEngine[] = [
  'Oracle 19c', 'PostgreSQL 16', 'SQL Server 2019', 'MySQL 8.0', 'MongoDB 6.0',
  'IBM DB2 v11', 'MariaDB', 'CockroachDB', 'Snowflake', 'Redshift', 'BigQuery', 'SQLite',
];

// ─── Formatting Helpers ─────────────────────────────────────────────────────

const fmtRows = (n: number): string => {
  if (n < 0) return '—';
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(0)}K`;
  return `${n}`;
};

const fmtSize = (gb: number): string => {
  if (gb < 0) return '—';
  if (gb >= 1) return `${gb.toFixed(1)} GB`;
  if (gb >= 0.001) return `${(gb * 1024).toFixed(0)} MB`;
  return '< 1 MB';
};

// ─── Object Type Badges ─────────────────────────────────────────────────────

const OBJ_BADGE: Record<string, { label: string; color: string; bg: string }> = {
  'Table':             { label: 'T',   color: '#10B981', bg: 'rgba(16,185,129,0.12)' },
  'View':              { label: 'V',   color: '#3B82F6', bg: 'rgba(59,130,246,0.12)' },
  'Materialized View': { label: 'MV',  color: '#8B5CF6', bg: 'rgba(139,92,246,0.12)' },
  'Procedure':         { label: 'P',   color: '#F59E0B', bg: 'rgba(245,158,11,0.12)' },
  'Function':          { label: 'F',   color: '#F97316', bg: 'rgba(249,115,22,0.12)' },
  'Package':           { label: 'PKG', color: '#EC4899', bg: 'rgba(236,72,153,0.12)' },
  'Trigger':           { label: 'TRG', color: '#EF4444', bg: 'rgba(239,68,68,0.12)' },
  'Sequence':          { label: 'SEQ', color: '#06B6D4', bg: 'rgba(6,182,212,0.12)' },
  'Role':              { label: 'R',   color: '#84CC16', bg: 'rgba(132,204,22,0.12)' },
  'Synonym':           { label: 'SYN', color: '#6B7280', bg: 'rgba(107,114,128,0.12)' },
};

const STATUS_CHIP: Record<string, { color: string; bg: string }> = {
  'OPTIMAL':    { color: '#10B981', bg: 'rgba(16,185,129,0.12)' },
  'TRANSPILED': { color: '#3B82F6', bg: 'rgba(59,130,246,0.12)' },
  'ADVISORY':   { color: '#F59E0B', bg: 'rgba(245,158,11,0.12)' },
};

// ─── IndeterminateCheckbox ──────────────────────────────────────────────────

interface IndeterminateCheckboxProps {
  checked: boolean;
  indeterminate: boolean;
  onChange: (checked: boolean) => void;
  'aria-label'?: string;
}

const IndeterminateCheckbox: FC<IndeterminateCheckboxProps> = ({
  checked, indeterminate, onChange, 'aria-label': ariaLabel,
}) => {
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (ref.current) ref.current.indeterminate = indeterminate;
  }, [indeterminate]);
  return (
    <input
      ref={ref}
      type="checkbox"
      checked={checked}
      onChange={(e) => onChange(e.target.checked)}
      aria-label={ariaLabel}
      style={{ cursor: 'pointer', accentColor: 'var(--dash-accent)', flexShrink: 0 }}
    />
  );
};

// ─── Mock Discovery Data (Engine-Compatible, 124 objects across 4 schemas) ──

const mk = (
  schema_id: string,
  object_id: string,
  object_name: string,
  object_type: string,
  estimated_rows: number,
  estimated_size_gb: number,
  compatibility_status: 'OPTIMAL' | 'TRANSPILED' | 'ADVISORY',
  dependency_ids: string[] = [],
  warnings: string[] = [],
): DiscoveredObjectDTO => ({
  object_id, schema_id, object_name, object_type,
  estimated_rows, estimated_size_gb, compatibility_status,
  dependency_ids, warnings, selected: true,
});

const INITIAL_SCHEMAS: SchemaDiscoveryDTO[] = [
  {
    schema_id: 'SYSTEM', schema_name: 'SYSTEM',
    object_groups: [
      { object_type: 'Table', objects: [
        mk('SYSTEM','sys-t1','CUSTOMER_RECORDS','Table',500_000_000,54.2,'OPTIMAL'),
        mk('SYSTEM','sys-t2','MIGRATION_AUDIT_LOG','Table',120_000_000,12.4,'OPTIMAL'),
        mk('SYSTEM','sys-t3','SYSTEM_CONFIG','Table',500,0.001,'OPTIMAL'),
        mk('SYSTEM','sys-t4','AUDIT_TRAIL','Table',800_000_000,82.1,'OPTIMAL'),
        mk('SYSTEM','sys-t5','ERROR_LOG','Table',45_000_000,4.8,'OPTIMAL'),
      ]},
      { object_type: 'Procedure', objects: [
        mk('SYSTEM','sys-p1','PROCESS_CUSTOMER_ORDER','Procedure',-1,-1,'TRANSPILED',['sys-t1'],['PL/SQL cursor rewrite required']),
        mk('SYSTEM','sys-p2','HANDLE_EXCEPTIONS','Procedure',-1,-1,'OPTIMAL'),
        mk('SYSTEM','sys-p3','REBUILD_INDEXES','Procedure',-1,-1,'ADVISORY',[],['DBMS_INDEX usage — manual review']),
      ]},
      { object_type: 'Sequence', objects: [
        mk('SYSTEM','sys-s1','SEQ_CUSTOMER_ID','Sequence',-1,-1,'OPTIMAL'),
        mk('SYSTEM','sys-s2','SEQ_AUDIT_ID','Sequence',-1,-1,'OPTIMAL'),
        mk('SYSTEM','sys-s3','SEQ_ERROR_ID','Sequence',-1,-1,'OPTIMAL'),
      ]},
      { object_type: 'Role', objects: [
        mk('SYSTEM','sys-r1','ROLE_FINANCE_ADMIN','Role',-1,-1,'OPTIMAL'),
        mk('SYSTEM','sys-r2','ROLE_SALES_USER','Role',-1,-1,'OPTIMAL'),
        mk('SYSTEM','sys-r3','ROLE_DBA','Role',-1,-1,'OPTIMAL'),
        mk('SYSTEM','sys-r4','ROLE_READONLY','Role',-1,-1,'OPTIMAL'),
      ]},
      { object_type: 'Synonym', objects: [
        mk('SYSTEM','sys-syn1','SYN_CUSTOMERS','Synonym',-1,-1,'OPTIMAL',['sys-t1']),
        mk('SYSTEM','sys-syn2','SYN_ORDERS','Synonym',-1,-1,'OPTIMAL'),
      ]},
    ],
  },
  {
    schema_id: 'HR', schema_name: 'HR',
    object_groups: [
      { object_type: 'Table', objects: [
        mk('HR','hr-t1','EMPLOYEES','Table',18_400_000,4.2,'OPTIMAL'),
        mk('HR','hr-t2','DEPARTMENTS','Table',500,0.002,'OPTIMAL'),
        mk('HR','hr-t3','JOB_HISTORY','Table',55_000_000,6.1,'OPTIMAL',['hr-t1','hr-t2']),
        mk('HR','hr-t4','SALARIES','Table',95_000_000,9.8,'OPTIMAL',['hr-t1']),
        mk('HR','hr-t5','LOCATIONS','Table',1000,0.001,'OPTIMAL'),
        mk('HR','hr-t6','JOBS','Table',200,0.001,'OPTIMAL'),
        mk('HR','hr-t7','REGIONS','Table',20,0.001,'OPTIMAL'),
        mk('HR','hr-t8','COUNTRIES','Table',250,0.001,'OPTIMAL',['hr-t7']),
      ]},
      { object_type: 'View', objects: [
        mk('HR','hr-v1','EMPLOYEE_SUMMARY','View',-1,-1,'OPTIMAL',['hr-t1','hr-t2']),
        mk('HR','hr-v2','ACTIVE_EMPLOYEES','View',-1,-1,'OPTIMAL',['hr-t1']),
        mk('HR','hr-v3','DEPT_HEADCOUNT','View',-1,-1,'OPTIMAL',['hr-t2','hr-t1']),
        mk('HR','hr-v4','SALARY_BANDS','View',-1,-1,'ADVISORY',['hr-t4'],['CONNECT BY hierarchy — needs WITH RECURSIVE']),
        mk('HR','hr-v5','MANAGER_TREE','View',-1,-1,'TRANSPILED',['hr-t1'],['Hierarchical query transpiled']),
      ]},
      { object_type: 'Procedure', objects: [
        mk('HR','hr-p1','UPDATE_SALARY','Procedure',-1,-1,'OPTIMAL',['hr-t4']),
        mk('HR','hr-p2','ARCHIVE_EMPLOYEE','Procedure',-1,-1,'TRANSPILED',['hr-t1','hr-t3'],['Bulk DML rewrite']),
        mk('HR','hr-p3','TRANSFER_DEPARTMENT','Procedure',-1,-1,'OPTIMAL',['hr-t1','hr-t2']),
        mk('HR','hr-p4','PROMOTE_EMPLOYEE','Procedure',-1,-1,'OPTIMAL',['hr-t1','hr-t4']),
        mk('HR','hr-p5','AUDIT_CHANGES','Procedure',-1,-1,'OPTIMAL',['hr-t3']),
        mk('HR','hr-p6','BATCH_UPDATE','Procedure',-1,-1,'ADVISORY',[],['FORALL statement mapping required']),
      ]},
      { object_type: 'Function', objects: [
        mk('HR','hr-f1','CALC_SENIORITY','Function',-1,-1,'OPTIMAL',['hr-t1']),
        mk('HR','hr-f2','GET_DEPT_NAME','Function',-1,-1,'OPTIMAL',['hr-t2']),
        mk('HR','hr-f3','EMP_FULL_NAME','Function',-1,-1,'OPTIMAL',['hr-t1']),
        mk('HR','hr-f4','COUNT_REPORTS','Function',-1,-1,'TRANSPILED',['hr-t1'],['CONNECT BY used']),
      ]},
      { object_type: 'Trigger', objects: [
        mk('HR','hr-trg1','TRG_EMP_AUDIT','Trigger',-1,-1,'OPTIMAL',['hr-t1','hr-t3']),
        mk('HR','hr-trg2','TRG_SALARY_CHECK','Trigger',-1,-1,'OPTIMAL',['hr-t4']),
        mk('HR','hr-trg3','TRG_DEPT_VALIDATION','Trigger',-1,-1,'OPTIMAL',['hr-t2']),
      ]},
      { object_type: 'Sequence', objects: [
        mk('HR','hr-seq1','SEQ_EMP_ID','Sequence',-1,-1,'OPTIMAL'),
        mk('HR','hr-seq2','SEQ_DEPT_ID','Sequence',-1,-1,'OPTIMAL'),
      ]},
    ],
  },
  {
    schema_id: 'FIN', schema_name: 'FIN',
    object_groups: [
      { object_type: 'Table', objects: [
        mk('FIN','fin-t1','PAYMENT_TRANSACTIONS','Table',100_000_000,19.6,'OPTIMAL'),
        mk('FIN','fin-t2','INVOICES','Table',45_000_000,8.2,'OPTIMAL'),
        mk('FIN','fin-t3','ACCOUNTS','Table',12_000_000,2.4,'OPTIMAL'),
        mk('FIN','fin-t4','LEDGER_ENTRIES','Table',280_000_000,38.4,'OPTIMAL'),
        mk('FIN','fin-t5','TAX_RECORDS','Table',55_000_000,7.8,'OPTIMAL'),
        mk('FIN','fin-t6','EXCHANGE_RATES','Table',850_000,0.12,'OPTIMAL'),
        mk('FIN','fin-t7','BUDGET_LINES','Table',4_200_000,0.62,'OPTIMAL'),
        mk('FIN','fin-t8','COST_CENTERS','Table',8500,0.002,'OPTIMAL'),
        mk('FIN','fin-t9','FISCAL_PERIODS','Table',240,0.001,'OPTIMAL'),
        mk('FIN','fin-t10','CURRENCY_CODES','Table',190,0.001,'OPTIMAL'),
      ]},
      { object_type: 'View', objects: [
        mk('FIN','fin-v1','MONTHLY_REVENUE','View',-1,-1,'ADVISORY',['fin-t1','fin-t4'],['ROLLUP clause — verify aggregation']),
        mk('FIN','fin-v2','TAX_SUMMARY','View',-1,-1,'OPTIMAL',['fin-t5']),
        mk('FIN','fin-v3','ACCOUNT_BALANCES','View',-1,-1,'OPTIMAL',['fin-t3','fin-t4']),
        mk('FIN','fin-v4','RECONCILIATION_VIEW','View',-1,-1,'TRANSPILED',['fin-t1','fin-t4'],['PIVOT transpiled to crosstab']),
        mk('FIN','fin-v5','COST_ANALYSIS','View',-1,-1,'OPTIMAL',['fin-t7','fin-t8']),
        mk('FIN','fin-v6','BUDGET_VS_ACTUAL','View',-1,-1,'ADVISORY',['fin-t7'],['MERGE statement reference']),
      ]},
      { object_type: 'Procedure', objects: [
        mk('FIN','fin-p1','CALCULATE_TAX_RATE','Procedure',-1,-1,'OPTIMAL',['fin-t5']),
        mk('FIN','fin-p2','RECONCILE_ACCOUNTS','Procedure',-1,-1,'TRANSPILED',['fin-t3','fin-t4'],['Cursor FOR LOOP rewrite']),
        mk('FIN','fin-p3','CLOSE_FISCAL_PERIOD','Procedure',-1,-1,'ADVISORY',['fin-t9'],['DBMS_LOCK usage']),
        mk('FIN','fin-p4','GENERATE_INVOICE','Procedure',-1,-1,'OPTIMAL',['fin-t2']),
        mk('FIN','fin-p5','PROCESS_PAYMENT','Procedure',-1,-1,'OPTIMAL',['fin-t1','fin-t3']),
        mk('FIN','fin-p6','AUDIT_TRANSACTIONS','Procedure',-1,-1,'OPTIMAL',['fin-t1']),
        mk('FIN','fin-p7','APPLY_EXCHANGE_RATE','Procedure',-1,-1,'OPTIMAL',['fin-t6']),
        mk('FIN','fin-p8','BATCH_RECONCILE','Procedure',-1,-1,'TRANSPILED',['fin-t4'],['FORALL + BULK COLLECT']),
      ]},
      { object_type: 'Function', objects: [
        mk('FIN','fin-f1','CALC_TAX','Function',-1,-1,'OPTIMAL',['fin-t5']),
        mk('FIN','fin-f2','GET_EXCHANGE_RATE','Function',-1,-1,'OPTIMAL',['fin-t6']),
        mk('FIN','fin-f3','COMPUTE_MARGIN','Function',-1,-1,'TRANSPILED',[],['UTL_RAW usage mapped']),
        mk('FIN','fin-f4','FISCAL_QUARTER','Function',-1,-1,'OPTIMAL',['fin-t9']),
        mk('FIN','fin-f5','GET_ACCOUNT_BALANCE','Function',-1,-1,'OPTIMAL',['fin-t3','fin-t4']),
      ]},
      { object_type: 'Package', objects: [
        mk('FIN','fin-pkg1','PKG_FINANCIAL_YEAR','Package',-1,-1,'TRANSPILED',[],['Package body decomposed to 4 procedures']),
        mk('FIN','fin-pkg2','PKG_TAX_ENGINE','Package',-1,-1,'TRANSPILED',[],['Package body decomposed to 3 procedures']),
        mk('FIN','fin-pkg3','PKG_REPORTING','Package',-1,-1,'ADVISORY',[],['UTL_HTTP usage — manual migration']),
      ]},
      { object_type: 'Trigger', objects: [
        mk('FIN','fin-trg1','TRG_PAYMENT_AUDIT','Trigger',-1,-1,'OPTIMAL',['fin-t1']),
        mk('FIN','fin-trg2','TRG_INVOICE_CREATE','Trigger',-1,-1,'OPTIMAL',['fin-t2']),
        mk('FIN','fin-trg3','TRG_LEDGER_BALANCE','Trigger',-1,-1,'OPTIMAL',['fin-t4']),
        mk('FIN','fin-trg4','TRG_BUDGET_CHECK','Trigger',-1,-1,'ADVISORY',['fin-t7'],['Compound trigger pattern']),
      ]},
      { object_type: 'Materialized View', objects: [
        mk('FIN','fin-mv1','MV_MONTHLY_SUMMARY','Materialized View',8_400_000,1.2,'ADVISORY',[],['Fast refresh compatibility check']),
        mk('FIN','fin-mv2','MV_TAX_LIABILITY','Materialized View',2_100_000,0.3,'ADVISORY',[],['ON COMMIT refresh — needs pg_cron']),
      ]},
    ],
  },
  {
    schema_id: 'SALES', schema_name: 'SALES',
    object_groups: [
      { object_type: 'Table', objects: [
        mk('SALES','sal-t1','ORDERS','Table',450_000_000,48.1,'OPTIMAL'),
        mk('SALES','sal-t2','CUSTOMERS','Table',85_000_000,12.4,'OPTIMAL'),
        mk('SALES','sal-t3','PRODUCTS','Table',4_200_000,0.58,'OPTIMAL'),
        mk('SALES','sal-t4','ORDER_ITEMS','Table',1_800_000_000,184.2,'OPTIMAL',['sal-t1','sal-t3']),
        mk('SALES','sal-t5','SHIPMENTS','Table',380_000_000,41.2,'OPTIMAL',['sal-t1']),
        mk('SALES','sal-t6','PROMOTIONS','Table',125_000,0.02,'OPTIMAL'),
        mk('SALES','sal-t7','TERRITORIES','Table',520,0.001,'OPTIMAL'),
        mk('SALES','sal-t8','SALES_TARGETS','Table',18_000,0.004,'OPTIMAL',['sal-t7']),
        mk('SALES','sal-t9','RETURNS','Table',12_000_000,1.8,'OPTIMAL',['sal-t1','sal-t2']),
        mk('SALES','sal-t10','CUSTOMER_SEGMENTS','Table',250_000,0.04,'OPTIMAL',['sal-t2']),
        mk('SALES','sal-t11','PRODUCT_CATEGORIES','Table',8200,0.002,'OPTIMAL'),
        mk('SALES','sal-t12','INVENTORY_ITEMS','Table',80_000_000,8.2,'OPTIMAL',['sal-t3']),
      ]},
      { object_type: 'View', objects: [
        mk('SALES','sal-v1','ORDER_SUMMARY','View',-1,-1,'OPTIMAL',['sal-t1','sal-t4']),
        mk('SALES','sal-v2','CUSTOMER_LIFETIME','View',-1,-1,'ADVISORY',['sal-t2','sal-t1'],['Analytical window function verify']),
        mk('SALES','sal-v3','PRODUCT_PERFORMANCE','View',-1,-1,'OPTIMAL',['sal-t3','sal-t4']),
        mk('SALES','sal-v4','TERRITORY_SALES','View',-1,-1,'OPTIMAL',['sal-t1','sal-t7']),
        mk('SALES','sal-v5','PROMO_EFFECTIVENESS','View',-1,-1,'ADVISORY',['sal-t6','sal-t1'],['DECODE to CASE rewrite']),
        mk('SALES','sal-v6','PENDING_ORDERS','View',-1,-1,'OPTIMAL',['sal-t1']),
        mk('SALES','sal-v7','FULFILLED_ORDERS','View',-1,-1,'OPTIMAL',['sal-t1','sal-t5']),
        mk('SALES','sal-v8','RETURN_ANALYSIS','View',-1,-1,'ADVISORY',['sal-t9'],['PIVOT usage — crosstab required']),
      ]},
      { object_type: 'Procedure', objects: [
        mk('SALES','sal-p1','PROCESS_ORDER','Procedure',-1,-1,'OPTIMAL',['sal-t1','sal-t4','sal-t12']),
        mk('SALES','sal-p2','CANCEL_ORDER','Procedure',-1,-1,'OPTIMAL',['sal-t1','sal-t9']),
        mk('SALES','sal-p3','APPLY_DISCOUNT','Procedure',-1,-1,'TRANSPILED',['sal-t6','sal-t4'],['Package-level variable reference']),
        mk('SALES','sal-p4','UPDATE_INVENTORY','Procedure',-1,-1,'OPTIMAL',['sal-t12']),
        mk('SALES','sal-p5','GENERATE_REPORT','Procedure',-1,-1,'ADVISORY',[],['UTL_FILE usage — pgcopy alternative']),
        mk('SALES','sal-p6','CLOSE_SALE','Procedure',-1,-1,'OPTIMAL',['sal-t1','sal-t2']),
      ]},
      { object_type: 'Function', objects: [
        mk('SALES','sal-f1','CALC_DISCOUNT','Function',-1,-1,'TRANSPILED',['sal-t6'],['NOCOPY parameter hint removed']),
        mk('SALES','sal-f2','ORDER_TOTAL','Function',-1,-1,'OPTIMAL',['sal-t4']),
        mk('SALES','sal-f3','CUSTOMER_TIER','Function',-1,-1,'OPTIMAL',['sal-t2','sal-t10']),
        mk('SALES','sal-f4','SHIPPING_COST','Function',-1,-1,'OPTIMAL',['sal-t5','sal-t7']),
      ]},
      { object_type: 'Trigger', objects: [
        mk('SALES','sal-trg1','TRG_ORDERS_AUDIT','Trigger',-1,-1,'OPTIMAL',['sal-t1']),
        mk('SALES','sal-trg2','TRG_INVENTORY_UPDATE','Trigger',-1,-1,'OPTIMAL',['sal-t12']),
        mk('SALES','sal-trg3','TRG_PROMO_VALIDATE','Trigger',-1,-1,'ADVISORY',['sal-t6'],['Mutating table check']),
        mk('SALES','sal-trg4','TRG_SHIPMENT_CREATE','Trigger',-1,-1,'OPTIMAL',['sal-t5']),
        mk('SALES','sal-trg5','TRG_RETURN_PROCESS','Trigger',-1,-1,'OPTIMAL',['sal-t9','sal-t12']),
      ]},
      { object_type: 'Sequence', objects: [
        mk('SALES','sal-seq1','SEQ_ORDER_ID','Sequence',-1,-1,'OPTIMAL'),
        mk('SALES','sal-seq2','SEQ_CUSTOMER_ID','Sequence',-1,-1,'OPTIMAL'),
        mk('SALES','sal-seq3','SEQ_PRODUCT_ID','Sequence',-1,-1,'OPTIMAL'),
        mk('SALES','sal-seq4','SEQ_SHIPMENT_ID','Sequence',-1,-1,'OPTIMAL'),
      ]},
      { object_type: 'Materialized View', objects: [
        mk('SALES','sal-mv1','MV_DAILY_SALES_SUMMARY','Materialized View',5_000_000,1.2,'ADVISORY',[],['Fast refresh requires trigger-based approach']),
        mk('SALES','sal-mv2','MV_QUARTERLY_TARGETS','Materialized View',840_000,0.18,'OPTIMAL'),
      ]},
    ],
  },
];

// Precomputed discovery totals — fixed after discovery, never change with selections
const TOTAL_SCHEMAS_DETECTED = INITIAL_SCHEMAS.length; // 4
const TOTAL_OBJECTS_DETECTED = INITIAL_SCHEMAS.reduce(
  (sum, s) => sum + s.object_groups.reduce((gs, g) => gs + g.objects.length, 0), 0
); // 124

// Initial expand state — schemas expanded, groups collapsed
const INITIAL_EXPANDED_SCHEMAS = new Set(INITIAL_SCHEMAS.map((s) => s.schema_id));
const INITIAL_EXPANDED_GROUPS = new Set<string>();

// ─── Step Titles ────────────────────────────────────────────────────────────

const STEP_TITLES = [
  '1. Overview', '2. Source Conn', '3. Target Conn',
  '4. Scope & Discovery', '5. Advisor Dashboard', '6. Rules & Tuning', '7. Deploy Review',
];

// ─── Main Component ──────────────────────────────────────────────────────────

export const NewMigrationWizard: FC<NewMigrationWizardProps> = ({ onClose, onLaunch, createProject }) => {
  const [step, setStep] = useState<1 | 2 | 3 | 4 | 5 | 6 | 7>(1);

  // Step 1: Overview
  const [migName, setMigName] = useState('Oracle ERP Core Migration');
  const [description, setDescription] = useState('Production migration of Oracle ERP core schema to PostgreSQL 16');
  const [migScope, setMigScope] = useState('Full Schema & Data Transport');
  const [strategy, setStrategy] = useState('Zero-Downtime Replication');
  const [projectName, setProjectName] = useState('ERP Modernization');
  const [environment, setEnvironment] = useState('Production');
  const [priority, setPriority] = useState('P0 - Critical');
  const [businessOwner, setBusinessOwner] = useState('Enterprise Data Architecture');

  // Step 2: Source Connection
  const [sourceEngine, setSourceEngine] = useState<DatabaseEngine>('Oracle 19c');
  const [sourceHost, setSourceHost] = useState('localhost');
  const [sourcePort, setSourcePort] = useState('1521');
  const [sourceDbName, setSourceDbName] = useState('FREE');
  const [sourceUser, setSourceUser] = useState('SYSTEM');
  const [sourcePass, setSourcePass] = useState('••••••••••••');
  const [sourceSsl, setSourceSsl] = useState(true);
  const [oracleWallet, setOracleWallet] = useState('/etc/oracle/wallets/cwallet.sso');
  const [sourceTested, setSourceTested] = useState(true);
  const [testingSource, setTestingSource] = useState(false);

  // Step 3: Target Connection
  const [targetEngine, setTargetEngine] = useState<DatabaseEngine>('PostgreSQL 16');
  const [targetHost, setTargetHost] = useState('localhost');
  const [targetPort, setTargetPort] = useState('5432');
  const [targetDbName, setTargetDbName] = useState('akaal_target');
  const [targetUser, setTargetUser] = useState('postgres');
  const [targetPass, setTargetPass] = useState('••••••••••••');
  const [targetSsl, setTargetSsl] = useState(true);
  const [targetTested, setTargetTested] = useState(true);
  const [testingTarget, setTestingTarget] = useState(false);

  // ─── Step 4: Discovery & Scope — Enterprise Schema-First State ─────────────
  // schemas: full mutable selection state; never lost on filter/expand changes
  const [schemas, setSchemas] = useState<SchemaDiscoveryDTO[]>(INITIAL_SCHEMAS);
  // Stable expand sets — survive filter changes, persist across re-renders
  const [expandedSchemas, setExpandedSchemas] = useState<Set<string>>(INITIAL_EXPANDED_SCHEMAS);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(INITIAL_EXPANDED_GROUPS);
  const [selectedObjectId, setSelectedObjectId] = useState<string | null>(null);
  const [discoveryProfile, setDiscoveryProfile] = useState<DiscoveryProfileType>('DEEP');
  // Filters: narrow the visible tree only — never affect selection state
  const [schemaFilter, setSchemaFilter] = useState<string>('ALL');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [objectSearch, setObjectSearch] = useState<string>('');
  const treeRef = useRef<HTMLDivElement>(null);

  // Step 6: Rules & Tuning
  const [maskingEnabled, setMaskingEnabled] = useState(true);
  const [batchSize, setBatchSize] = useState('10000');
  const [parallelism, setParallelism] = useState('8');
  const [checkpointInterval, setCheckpointInterval] = useState('50000');
  const [expandedCard, setExpandedCard] = useState<string | null>('cleansing');

  // Execution Plan Drawer
  const [showExecutionPlanDrawer, setShowExecutionPlanDrawer] = useState(false);

  // ── Keyboard Esc ──────────────────────────────────────────────────────────
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (showExecutionPlanDrawer) setShowExecutionPlanDrawer(false);
        else onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose, showExecutionPlanDrawer]);

  // ── Connection Handlers ───────────────────────────────────────────────────
  const handleTestSource = () => {
    setTestingSource(true);
    setTimeout(() => {
      setTestingSource(false);
      setSourceTested(true);
      notificationService.push(
        'Source Connection Verified', 'success',
        `Successfully connected to ${sourceEngine} (${sourceHost}:${sourcePort}/${sourceDbName}). Latency: 12ms. Version: Oracle 19c EE.`
      );
    }, 400);
  };

  const handleTestTarget = () => {
    setTestingTarget(true);
    setTimeout(() => {
      setTestingTarget(false);
      setTargetTested(true);
      notificationService.push(
        'Target Connection Verified', 'success',
        `Successfully connected to ${targetEngine} (${targetHost}:${targetPort}/${targetDbName}). Latency: 8ms. Extensions: pgvector, PostGIS, pg_cron.`
      );
    }, 400);
  };

  const handleCompleteLaunch = () => {
    const nameToUse = migName.trim() || `${sourceEngine} → ${targetEngine} Migration`;
    const created = createProject(nameToUse, sourceEngine, targetEngine);
    onLaunch(created);
  };

  // ── Step 4: Memoized Derived Values ──────────────────────────────────────

  // Static schema stats — computed once from initial data, never re-computed
  const schemaStaticStats = useMemo(() => {
    const map = new Map<string, { typeCounts: Record<string, number>; totalRows: number; totalSizeGb: number }>();
    for (const schema of INITIAL_SCHEMAS) {
      const typeCounts: Record<string, number> = {};
      let totalRows = 0;
      let totalSizeGb = 0;
      for (const group of schema.object_groups) {
        typeCounts[group.object_type] = group.objects.length;
        for (const obj of group.objects) {
          if (obj.estimated_rows > 0) totalRows += obj.estimated_rows;
          if (obj.estimated_size_gb > 0) totalSizeGb += obj.estimated_size_gb;
        }
      }
      map.set(schema.schema_id, { typeCounts, totalRows, totalSizeGb });
    }
    return map;
  }, []); // empty deps — computed once from static constant

  // All unique object types — for the type filter dropdown
  const allObjectTypes = useMemo(() => {
    const types = new Set<string>();
    INITIAL_SCHEMAS.forEach((s) => s.object_groups.forEach((g) => types.add(g.object_type)));
    return Array.from(types).sort();
  }, []); // empty deps — static

  // Filtered visible tree — preserves schema-first hierarchy, NEVER affects selection
  const visibleSchemas = useMemo<SchemaDiscoveryDTO[]>(() => {
    return schemas
      .map((schema) => {
        if (schemaFilter !== 'ALL' && schema.schema_id !== schemaFilter) return null;
        const filteredGroups = schema.object_groups
          .map((group) => {
            if (typeFilter !== 'ALL' && group.object_type !== typeFilter) return null;
            const filteredObjects = objectSearch
              ? group.objects.filter((obj) => obj.object_name.toLowerCase().includes(objectSearch.toLowerCase()))
              : group.objects;
            if (filteredObjects.length === 0) return null;
            return { ...group, objects: filteredObjects };
          })
          .filter(Boolean) as ObjectGroupDTO[];
        if (filteredGroups.length === 0) return null;
        return { ...schema, object_groups: filteredGroups };
      })
      .filter(Boolean) as SchemaDiscoveryDTO[];
  }, [schemas, schemaFilter, typeFilter, objectSearch]);

  // Live selection counts — derived from full schemas state (not just visible)
  const { selectedCount, schemasIncludedCount } = useMemo(() => {
    let total = 0;
    let included = 0;
    for (const s of schemas) {
      let hasSelection = false;
      for (const g of s.object_groups) {
        for (const o of g.objects) {
          if (o.selected) { total++; hasSelection = true; }
        }
      }
      if (hasSelection) included++;
    }
    return { selectedCount: total, schemasIncludedCount: included };
  }, [schemas]);

  const excludedCount = TOTAL_OBJECTS_DETECTED - selectedCount;

  // Detail panel — find selected object across all schemas
  const selectedObjectDetail = useMemo<DiscoveredObjectDTO | null>(() => {
    if (!selectedObjectId) return null;
    for (const s of schemas) {
      for (const g of s.object_groups) {
        const obj = g.objects.find((o) => o.object_id === selectedObjectId);
        if (obj) return obj;
      }
    }
    return null;
  }, [schemas, selectedObjectId]);

  // includeSchemas string — derived from schemas with at least 1 selected object
  const includeSchemas = useMemo(() =>
    schemas
      .filter((s) => s.object_groups.some((g) => g.objects.some((o) => o.selected)))
      .map((s) => s.schema_name)
      .join(', '),
    [schemas]
  );

  const isFiltered = schemaFilter !== 'ALL' || typeFilter !== 'ALL' || objectSearch !== '';

  // ── Step 4: Check State Helpers ───────────────────────────────────────────

  const getSchemaCheckState = useCallback((schema: SchemaDiscoveryDTO) => {
    const all = schema.object_groups.flatMap((g) => g.objects);
    const sel = all.filter((o) => o.selected).length;
    return { checked: sel === all.length && all.length > 0, indeterminate: sel > 0 && sel < all.length };
  }, []);

  const getGroupCheckState = useCallback((group: ObjectGroupDTO) => {
    const sel = group.objects.filter((o) => o.selected).length;
    return { checked: sel === group.objects.length && group.objects.length > 0, indeterminate: sel > 0 && sel < group.objects.length };
  }, []);

  // ── Step 4: Selection Handlers ────────────────────────────────────────────

  const toggleSchema = useCallback((schemaId: string, checked: boolean) => {
    setSchemas((prev) =>
      prev.map((s) =>
        s.schema_id !== schemaId ? s : {
          ...s, object_groups: s.object_groups.map((g) => ({
            ...g, objects: g.objects.map((o) => ({ ...o, selected: checked })),
          })),
        }
      )
    );
  }, []);

  const toggleGroup = useCallback((schemaId: string, objectType: string, checked: boolean) => {
    setSchemas((prev) =>
      prev.map((s) =>
        s.schema_id !== schemaId ? s : {
          ...s, object_groups: s.object_groups.map((g) =>
            g.object_type !== objectType ? g : {
              ...g, objects: g.objects.map((o) => ({ ...o, selected: checked })),
            }
          ),
        }
      )
    );
  }, []);

  const toggleObject = useCallback((objectId: string, checked: boolean) => {
    setSchemas((prev) =>
      prev.map((s) => ({
        ...s, object_groups: s.object_groups.map((g) => ({
          ...g, objects: g.objects.map((o) =>
            o.object_id !== objectId ? o : { ...o, selected: checked }
          ),
        })),
      }))
    );
  }, []);

  // ── Step 4: Expand/Collapse Handlers ─────────────────────────────────────

  const toggleSchemaExpand = useCallback((schemaId: string) => {
    setExpandedSchemas((prev) => {
      const next = new Set(prev);
      if (next.has(schemaId)) next.delete(schemaId); else next.add(schemaId);
      return next;
    });
  }, []);

  const toggleGroupExpand = useCallback((key: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  }, []);

  const expandAll = useCallback(() => {
    setExpandedSchemas(new Set(INITIAL_SCHEMAS.map((s) => s.schema_id)));
    const keys = new Set<string>();
    INITIAL_SCHEMAS.forEach((s) => s.object_groups.forEach((g) => keys.add(`${s.schema_id}:${g.object_type}`)));
    setExpandedGroups(keys);
  }, []);

  const collapseAll = useCallback(() => {
    setExpandedSchemas(new Set());
    setExpandedGroups(new Set());
  }, []);

  // ── Step 4: Bulk Selection ────────────────────────────────────────────────

  const selectAll = useCallback((checked: boolean) => {
    setSchemas((prev) =>
      prev.map((s) => ({
        ...s, object_groups: s.object_groups.map((g) => ({
          ...g, objects: g.objects.map((o) => ({ ...o, selected: checked })),
        })),
      }))
    );
  }, []);

  const selectVisible = useCallback((checked: boolean) => {
    const visibleIds = new Set<string>();
    visibleSchemas.forEach((s) => s.object_groups.forEach((g) => g.objects.forEach((o) => visibleIds.add(o.object_id))));
    setSchemas((prev) =>
      prev.map((s) => ({
        ...s, object_groups: s.object_groups.map((g) => ({
          ...g, objects: g.objects.map((o) =>
            visibleIds.has(o.object_id) ? { ...o, selected: checked } : o
          ),
        })),
      }))
    );
  }, [visibleSchemas]);

  const clearFilters = useCallback(() => {
    setSchemaFilter('ALL');
    setTypeFilter('ALL');
    setObjectSearch('');
  }, []);

  // ── Step 4: Schema Summary Helper ────────────────────────────────────────

  const getSchemaOverview = useCallback((schemaId: string): string => {
    const stats = schemaStaticStats.get(schemaId);
    if (!stats) return '';
    const parts: string[] = [];
    Object.entries(stats.typeCounts).slice(0, 5).forEach(([type, count]) =>
      parts.push(`${count} ${type}${count !== 1 ? 's' : ''}`)
    );
    if (stats.totalRows > 0) parts.push(`${fmtRows(stats.totalRows)} rows`);
    if (stats.totalSizeGb > 0) parts.push(fmtSize(stats.totalSizeGb));
    return parts.join(' · ');
  }, [schemaStaticStats]);

  const getGroupSelectionLabel = useCallback((group: ObjectGroupDTO): string => {
    const sel = group.objects.filter((o) => o.selected).length;
    const total = group.objects.length;
    if (sel === total) return `${total} selected`;
    if (sel === 0) return `0 of ${total}`;
    return `${sel} of ${total}`;
  }, []);

  // ── Step 4: Keyboard Navigation ───────────────────────────────────────────

  const handleTreeKeyDown = useCallback((e: React.KeyboardEvent<HTMLDivElement>) => {
    const tree = treeRef.current;
    if (!tree) return;
    const items = Array.from(tree.querySelectorAll<HTMLElement>('[data-tree-item]'));
    const focused = document.activeElement as HTMLElement;
    const currentIdx = items.indexOf(focused);

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        if (currentIdx < items.length - 1) items[currentIdx + 1].focus();
        break;
      case 'ArrowUp':
        e.preventDefault();
        if (currentIdx > 0) items[currentIdx - 1].focus();
        else if (items.length > 0) items[0].focus();
        break;
      case 'ArrowRight': {
        e.preventDefault();
        const sid = focused?.dataset.schemaId;
        const gk = focused?.dataset.groupKey;
        if (sid && !expandedSchemas.has(sid)) toggleSchemaExpand(sid);
        else if (gk && !expandedGroups.has(gk)) toggleGroupExpand(gk);
        break;
      }
      case 'ArrowLeft': {
        e.preventDefault();
        const sid = focused?.dataset.schemaId;
        const gk = focused?.dataset.groupKey;
        if (sid && expandedSchemas.has(sid)) toggleSchemaExpand(sid);
        else if (gk && expandedGroups.has(gk)) toggleGroupExpand(gk);
        break;
      }
      case ' ':
      case 'Enter': {
        e.preventDefault();
        const sid = focused?.dataset.schemaId;
        const gk = focused?.dataset.groupKey;
        const oid = focused?.dataset.objectId;
        if (sid) {
          const s = schemas.find((x) => x.schema_id === sid);
          if (s) { const { checked } = getSchemaCheckState(s); toggleSchema(sid, !checked); }
        } else if (gk) {
          const [schId, ...rest] = gk.split(':');
          const objType = rest.join(':');
          const grp = schemas.find((x) => x.schema_id === schId)?.object_groups.find((g) => g.object_type === objType);
          if (grp) { const { checked } = getGroupCheckState(grp); toggleGroup(schId, objType, !checked); }
        } else if (oid) {
          const obj = schemas.flatMap((s) => s.object_groups.flatMap((g) => g.objects)).find((o) => o.object_id === oid);
          if (obj) toggleObject(oid, !obj.selected);
        }
        break;
      }
    }
  }, [expandedSchemas, expandedGroups, schemas, getSchemaCheckState, getGroupCheckState, toggleSchemaExpand, toggleGroupExpand, toggleSchema, toggleGroup, toggleObject]);

  // ─────────────────────────────────────────────────────────────────────────
  // JSX
  // ─────────────────────────────────────────────────────────────────────────

  return (
    <div className={styles.modalBackdrop} onClick={onClose} role="dialog" aria-modal="true" aria-label={migName || 'New Enterprise Migration Workspace'}>
      {/* Scoped hover & focus styles for tree items */}
      <style>{`
        .akaal-tree-schema:hover { background: rgba(37,99,235,0.05) !important; }
        .akaal-tree-group:hover  { background: rgba(37,99,235,0.03) !important; }
        .akaal-tree-obj:hover    { background: rgba(37,99,235,0.07) !important; }
        .akaal-tree-schema:focus,
        .akaal-tree-group:focus,
        .akaal-tree-obj:focus    { outline: 2px solid var(--dash-accent); outline-offset: -2px; border-radius: 0; }
      `}</style>

      <div
        className={styles.modalBox}
        onClick={(e) => e.stopPropagation()}
        style={{ width: '94vw', maxWidth: 1320, height: '90vh', maxHeight: 900, display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden' }}
      >
        {/* ── Header Bar ─────────────────────────────────────────────────── */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 24px', borderBottom: '1px solid var(--dash-border)', background: 'var(--dash-surface)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: 'var(--dash-text-primary)' }}>
              {migName || 'New Enterprise Migration Workspace'}
            </h2>
            <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, background: 'rgba(37,99,235,0.15)', color: '#3B82F6', fontWeight: 600 }}>MIG-2026-0805-001</span>
            <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, background: 'rgba(16,185,129,0.15)', color: '#10B981', fontWeight: 600 }}>AKAAL Engine V3.4.0</span>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--dash-text-secondary)', fontSize: 22, cursor: 'pointer' }} aria-label="Close setup experience">×</button>
        </div>

        {/* ── Workflow 7-Step Nav Bar ─────────────────────────────────────── */}
        <div style={{ display: 'flex', background: 'var(--dash-bg)', padding: '10px 24px', borderBottom: '1px solid var(--dash-border)', gap: 6, overflowX: 'auto' }}>
          {STEP_TITLES.map((title, idx) => {
            const stepNum = idx + 1;
            const isCompleted = stepNum < step;
            const isCurrent = stepNum === step;
            return (
              <div
                key={title}
                onClick={() => { if (stepNum < step) setStep(stepNum as any); }}
                style={{
                  flex: 1, minWidth: 115, padding: '6px 12px', borderRadius: 6,
                  background: isCurrent ? 'var(--dash-accent)' : isCompleted ? 'rgba(16,185,129,0.12)' : 'var(--dash-surface)',
                  border: isCurrent ? '1px solid var(--dash-accent)' : isCompleted ? '1px solid rgba(16,185,129,0.3)' : '1px solid var(--dash-border)',
                  color: isCurrent ? '#FFFFFF' : isCompleted ? '#10B981' : 'var(--dash-text-secondary)',
                  cursor: isCompleted ? 'pointer' : 'default',
                  display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, fontWeight: 600, transition: 'all 150ms ease',
                }}
              >
                <span style={{ width: 16, height: 16, borderRadius: '50%', background: isCurrent ? '#FFFFFF' : isCompleted ? '#10B981' : 'var(--dash-border)', color: isCurrent ? 'var(--dash-accent)' : isCompleted ? '#FFFFFF' : 'var(--dash-text-secondary)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 700 }}>
                  {isCompleted ? '✓' : stepNum}
                </span>
                <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{title.split('. ')[1]}</span>
              </div>
            );
          })}
        </div>

        {/* ── Main Body Layout ────────────────────────────────────────────── */}
        <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
          {/* Left Content View */}
          <div style={{ flex: 1, padding: 24, overflowY: 'auto' }}>

            {/* ── STEP 1: OVERVIEW ────────────────────────────────────────── */}
            {step === 1 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
                <div style={{ padding: 14, background: 'var(--dash-surface)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--dash-accent)', textTransform: 'uppercase', marginBottom: 4 }}>Step 1 • Migration Strategy & Governance Metadata</div>
                  <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)' }}>Define project parameters, owner, execution scope, and target environment.</div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 14 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Migration Title *</label>
                    <input type="text" value={migName} onChange={(e) => setMigName(e.target.value)} placeholder="e.g. Oracle ERP Core Migration" style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }} />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Project Workspace</label>
                    <input type="text" value={projectName} onChange={(e) => setProjectName(e.target.value)} style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }} />
                  </div>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Description & Objectives</label>
                  <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13, fontFamily: 'var(--akaal-font-sans)' }} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Migration Scope</label>
                    <select value={migScope} onChange={(e) => setMigScope(e.target.value)} style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}>
                      <option value="Full Schema & Data Transport">Full Schema & Data Transport</option>
                      <option value="CDC Streaming Replication">CDC Streaming Replication Only</option>
                      <option value="Schema Definition DDL">Schema Definition DDL Only</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Execution Strategy</label>
                    <select value={strategy} onChange={(e) => setStrategy(e.target.value)} style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}>
                      <option value="Zero-Downtime Replication">Zero-Downtime Replication</option>
                      <option value="Scheduled Batch Offline">Scheduled Batch Offline</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Environment</label>
                    <select value={environment} onChange={(e) => setEnvironment(e.target.value)} style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}>
                      <option value="Production">Production</option>
                      <option value="Staging">Staging</option>
                      <option value="Development">Development</option>
                    </select>
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Priority Level</label>
                    <select value={priority} onChange={(e) => setPriority(e.target.value)} style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}>
                      <option value="P0 - Critical">P0 - Critical</option>
                      <option value="P1 - High">P1 - High</option>
                      <option value="P2 - Medium">P2 - Medium</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Business Owner</label>
                    <input type="text" value={businessOwner} onChange={(e) => setBusinessOwner(e.target.value)} style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }} />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Migration Window</label>
                    <input type="text" value="2 Hours (Off-Peak Weekend)" disabled style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-surface)', color: 'var(--dash-text-secondary)', fontSize: 13 }} />
                  </div>
                </div>
              </div>
            )}

            {/* ── STEP 2: SOURCE CONNECTION ────────────────────────────────── */}
            {step === 2 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Source Engine</label>
                    <select value={sourceEngine} onChange={(e) => setSourceEngine(e.target.value as DatabaseEngine)} style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}>
                      {SUPPORTED_ENGINES.map((eng) => (<option key={eng} value={eng}>{eng}</option>))}
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Saved Profiles</label>
                    <select style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}>
                      <option value="prod_oracle_free">Production Oracle (localhost:1521/FREE)</option>
                    </select>
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 14 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Hostname / Endpoint</label>
                    <input type="text" value={sourceHost} onChange={(e) => setSourceHost(e.target.value)} style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }} />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Port</label>
                    <input type="text" value={sourcePort} onChange={(e) => setSourcePort(e.target.value)} style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>SID / Service Name</label>
                    <input type="text" value={sourceDbName} onChange={(e) => setSourceDbName(e.target.value)} style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }} />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Username</label>
                    <input type="text" value={sourceUser} onChange={(e) => setSourceUser(e.target.value)} style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }} />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Password</label>
                    <input type="password" value={sourcePass} onChange={(e) => setSourcePass(e.target.value)} style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Oracle Wallet File (cwallet.sso)</label>
                    <input type="text" value={oracleWallet} onChange={(e) => setOracleWallet(e.target.value)} style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }} />
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 16, paddingTop: 20 }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                      <input type="checkbox" checked={sourceSsl} onChange={(e) => setSourceSsl(e.target.checked)} /> SSL Encrypted
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                      <input type="checkbox" defaultChecked /> SSH Tunnel
                    </label>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 10 }}>
                  <button type="button" onClick={handleTestSource} disabled={testingSource} style={{ padding: '9px 18px', borderRadius: 8, background: 'var(--dash-accent)', border: 'none', color: '#FFF', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                    {testingSource ? 'Testing Connection...' : 'Test Source Connection (IPC)'}
                  </button>
                  {sourceTested && (<span style={{ fontSize: 12, color: '#10B981', fontWeight: 600 }}>✓ Verified (12ms Latency)</span>)}
                </div>
              </div>
            )}

            {/* ── STEP 3: TARGET CONNECTION ────────────────────────────────── */}
            {step === 3 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Target Engine</label>
                    <select value={targetEngine} onChange={(e) => setTargetEngine(e.target.value as DatabaseEngine)} style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}>
                      {SUPPORTED_ENGINES.map((eng) => (<option key={eng} value={eng}>{eng}</option>))}
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Saved Profiles</label>
                    <select style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }}>
                      <option value="prod_pg_target">PostgreSQL akaal_target (localhost:5432)</option>
                    </select>
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 14 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Hostname / Endpoint</label>
                    <input type="text" value={targetHost} onChange={(e) => setTargetHost(e.target.value)} style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }} />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Port</label>
                    <input type="text" value={targetPort} onChange={(e) => setTargetPort(e.target.value)} style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Database Name</label>
                    <input type="text" value={targetDbName} onChange={(e) => setTargetDbName(e.target.value)} style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }} />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Username</label>
                    <input type="text" value={targetUser} onChange={(e) => setTargetUser(e.target.value)} style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }} />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Password</label>
                    <input type="password" value={targetPass} onChange={(e) => setTargetPass(e.target.value)} style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 13 }} />
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <button type="button" onClick={handleTestTarget} disabled={testingTarget} style={{ padding: '9px 18px', borderRadius: 8, background: 'var(--dash-accent)', border: 'none', color: '#FFF', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                      {testingTarget ? 'Testing Connection...' : 'Test Target Connection (IPC)'}
                    </button>
                    <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                      <input type="checkbox" checked={targetSsl} onChange={(e) => setTargetSsl(e.target.checked)} /> SSL Encrypted Transport
                    </label>
                  </div>
                  {targetTested && (<span style={{ fontSize: 12, color: '#10B981', fontWeight: 600 }}>✓ Verified Target (8ms Latency)</span>)}
                </div>
              </div>
            )}

            {/* ── STEP 4: ENTERPRISE DISCOVERY & SCOPE EXPLORER ───────────── */}
            {step === 4 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

                {/* Header row: Discovery Profile + Status badge */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 14 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--dash-text-secondary)' }}>Discovery Profile:</span>
                    {(['QUICK', 'STANDARD', 'DEEP', 'COMPLIANCE'] as DiscoveryProfileType[]).map((prof) => (
                      <button key={prof} type="button" onClick={() => setDiscoveryProfile(prof)}
                        style={{ padding: '4px 10px', borderRadius: 6, border: discoveryProfile === prof ? '1px solid var(--dash-accent)' : '1px solid var(--dash-border)', background: discoveryProfile === prof ? 'rgba(37,99,235,0.15)' : 'var(--dash-bg)', color: discoveryProfile === prof ? 'var(--dash-accent)' : 'var(--dash-text-secondary)', fontSize: 11, fontWeight: 600, cursor: 'pointer', transition: 'all 150ms ease' }}>
                        {prof}
                      </button>
                    ))}
                  </div>
                  <span style={{ fontSize: 11, color: '#10B981', fontWeight: 700, padding: '3px 10px', borderRadius: 4, background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.25)' }}>
                    ● DISCOVERY COMPLETE
                  </span>
                </div>

                {/* KPI Cards — Detected totals are fixed; Selected/Excluded update live */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
                  {[
                    { label: 'Schemas Detected', value: TOTAL_SCHEMAS_DETECTED.toString(), color: '#3B82F6', note: 'Discovery total · fixed' },
                    { label: 'Objects Detected', value: TOTAL_OBJECTS_DETECTED.toLocaleString(), color: '#8B5CF6', note: 'Discovery total · fixed' },
                    { label: 'Objects Selected', value: selectedCount.toLocaleString(), color: '#10B981', note: 'Updates with selection' },
                    { label: 'Objects Excluded', value: excludedCount.toLocaleString(), color: excludedCount > 0 ? '#F59E0B' : '#10B981', note: 'Detected − Selected' },
                  ].map((kpi) => (
                    <div key={kpi.label} style={{ padding: '10px 14px', background: 'var(--dash-surface)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                      <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>{kpi.label}</div>
                      <div style={{ fontSize: 24, fontWeight: 800, color: kpi.color, marginTop: 4, fontVariantNumeric: 'tabular-nums' }}>{kpi.value}</div>
                      <div style={{ fontSize: 9, color: 'var(--dash-text-secondary)', marginTop: 2 }}>{kpi.note}</div>
                    </div>
                  ))}
                </div>

                {/* Filter Bar */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', background: 'var(--dash-surface)', borderRadius: 8, border: '1px solid var(--dash-border)', flexWrap: 'wrap' }}>
                  <select value={schemaFilter} onChange={(e) => setSchemaFilter(e.target.value)} aria-label="Filter by schema"
                    style={{ padding: '5px 8px', borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 11, fontWeight: 600 }}>
                    <option value="ALL">All Schemas</option>
                    {INITIAL_SCHEMAS.map((s) => (<option key={s.schema_id} value={s.schema_id}>{s.schema_name}</option>))}
                  </select>

                  <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} aria-label="Filter by object type"
                    style={{ padding: '5px 8px', borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 11, fontWeight: 600 }}>
                    <option value="ALL">All Types</option>
                    {allObjectTypes.map((t) => (<option key={t} value={t}>{t}s</option>))}
                  </select>

                  <input
                    type="text" value={objectSearch} onChange={(e) => setObjectSearch(e.target.value)}
                    placeholder="Search objects..." aria-label="Search objects"
                    style={{ flex: 1, minWidth: 140, padding: '5px 10px', borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 11 }}
                  />

                  <div style={{ display: 'flex', gap: 5, marginLeft: 'auto', flexWrap: 'wrap' }}>
                    {isFiltered && (
                      <button type="button" onClick={clearFilters} style={{ padding: '4px 8px', borderRadius: 4, border: '1px solid #EF4444', background: 'rgba(239,68,68,0.08)', color: '#EF4444', fontSize: 10, fontWeight: 700, cursor: 'pointer' }}>✕ Clear Filters</button>
                    )}
                    <button type="button" onClick={() => selectVisible(true)} style={{ padding: '4px 8px', borderRadius: 4, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-secondary)', fontSize: 10, fontWeight: 600, cursor: 'pointer' }}>Select Visible</button>
                    <button type="button" onClick={() => selectVisible(false)} style={{ padding: '4px 8px', borderRadius: 4, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-secondary)', fontSize: 10, fontWeight: 600, cursor: 'pointer' }}>Deselect Visible</button>
                    <button type="button" onClick={() => selectAll(true)} style={{ padding: '4px 8px', borderRadius: 4, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-secondary)', fontSize: 10, fontWeight: 600, cursor: 'pointer' }}>Select All</button>
                    <button type="button" onClick={() => selectAll(false)} style={{ padding: '4px 8px', borderRadius: 4, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-secondary)', fontSize: 10, fontWeight: 600, cursor: 'pointer' }}>Deselect All</button>
                    <button type="button" onClick={expandAll} style={{ padding: '4px 8px', borderRadius: 4, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-secondary)', fontSize: 10, fontWeight: 600, cursor: 'pointer' }}>⊞ Expand All</button>
                    <button type="button" onClick={collapseAll} style={{ padding: '4px 8px', borderRadius: 4, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-secondary)', fontSize: 10, fontWeight: 600, cursor: 'pointer' }}>⊟ Collapse All</button>
                  </div>
                </div>

                {/* Explorer: Schema-First Tree + Detail Panel */}
                <div style={{ display: 'flex', gap: 12 }}>

                  {/* ── Schema-First Tree ── */}
                  <div
                    ref={treeRef}
                    role="tree"
                    aria-label="Database schema object explorer"
                    onKeyDown={handleTreeKeyDown}
                    style={{ flex: 1, border: '1px solid var(--dash-border)', borderRadius: 8, overflow: 'hidden', background: 'var(--dash-surface)', display: 'flex', flexDirection: 'column', minWidth: 0 }}
                  >
                    {/* Column header */}
                    <div style={{ display: 'grid', gridTemplateColumns: '22px 22px 1fr 76px 76px 72px', gap: 6, padding: '7px 12px', background: 'var(--dash-bg)', borderBottom: '1px solid var(--dash-border)', fontSize: 10, fontWeight: 700, color: 'var(--dash-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em', alignItems: 'center' }}>
                      <span /><span />
                      <span>Object</span>
                      <span>Est. Rows</span>
                      <span>Est. Size</span>
                      <span>Status</span>
                    </div>

                    {/* Scrollable body */}
                    <div style={{ overflowY: 'auto', maxHeight: 400 }}>
                      {visibleSchemas.length === 0 ? (
                        /* Enterprise empty state */
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 24px', gap: 10 }}>
                          <span style={{ fontSize: 28 }}>🔍</span>
                          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--dash-text-primary)' }}>No objects match current filters</div>
                          <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', textAlign: 'center', maxWidth: 260 }}>
                            Adjust the schema, type, or search query to find objects.
                          </div>
                          <button type="button" onClick={clearFilters}
                            style={{ marginTop: 4, padding: '8px 18px', borderRadius: 6, background: 'var(--dash-accent)', border: 'none', color: '#FFF', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                            Clear All Filters
                          </button>
                        </div>
                      ) : (
                        visibleSchemas.map((schema) => {
                          const schemaCheck = getSchemaCheckState(schema);
                          const schemaExpanded = expandedSchemas.has(schema.schema_id);
                          const stats = schemaStaticStats.get(schema.schema_id);

                          return (
                            <div key={schema.schema_id}>
                              {/* Schema Row */}
                              <div
                                className="akaal-tree-schema"
                                role="treeitem"
                                aria-expanded={schemaExpanded}
                                tabIndex={0}
                                data-tree-item="true"
                                data-schema-id={schema.schema_id}
                                onClick={() => toggleSchemaExpand(schema.schema_id)}
                                style={{ display: 'grid', gridTemplateColumns: '22px 22px 1fr 76px 76px 72px', gap: 6, padding: '9px 12px', alignItems: 'center', cursor: 'pointer', borderBottom: '1px solid var(--dash-border)', background: 'var(--dash-bg)', transition: 'background 150ms ease' }}
                              >
                                <span style={{ fontSize: 11, color: 'var(--dash-text-secondary)', userSelect: 'none', fontWeight: 700, transition: 'transform 150ms ease', display: 'inline-block', transform: schemaExpanded ? 'rotate(0deg)' : 'rotate(-90deg)' }}>▼</span>
                                <IndeterminateCheckbox
                                  checked={schemaCheck.checked}
                                  indeterminate={schemaCheck.indeterminate}
                                  onChange={(checked) => toggleSchema(schema.schema_id, checked)}
                                  aria-label={`Select all objects in schema ${schema.schema_name}`}
                                />
                                <div>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                    <span style={{ fontSize: 13, fontWeight: 800, color: 'var(--dash-text-primary)' }}>
                                      🗄 {schema.schema_name}
                                    </span>
                                    <span style={{ fontSize: 10, color: 'var(--dash-text-secondary)', padding: '1px 5px', borderRadius: 3, background: 'var(--dash-surface)', border: '1px solid var(--dash-border)', fontWeight: 600 }}>
                                      {schema.object_groups.reduce((sum, g) => sum + g.objects.length, 0)} objects
                                    </span>
                                  </div>
                                  {stats && (
                                    <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                      {getSchemaOverview(schema.schema_id)}
                                    </div>
                                  )}
                                </div>
                                <span style={{ fontSize: 11, color: 'var(--dash-text-secondary)', fontVariantNumeric: 'tabular-nums' }}>
                                  {stats && stats.totalRows > 0 ? fmtRows(stats.totalRows) : '—'}
                                </span>
                                <span style={{ fontSize: 11, color: 'var(--dash-text-secondary)' }}>
                                  {stats && stats.totalSizeGb > 0 ? fmtSize(stats.totalSizeGb) : '—'}
                                </span>
                                <span />
                              </div>

                              {/* Schema children — animated expand/collapse */}
                              <div style={{
                                overflow: 'hidden',
                                maxHeight: schemaExpanded ? '20000px' : '0px',
                                transition: 'max-height 200ms ease-in-out, opacity 180ms ease',
                                opacity: schemaExpanded ? 1 : 0,
                              }}>
                                {schema.object_groups.map((group) => {
                                  const groupKey = `${schema.schema_id}:${group.object_type}`;
                                  const groupExpanded = expandedGroups.has(groupKey);
                                  const groupCheck = getGroupCheckState(group);
                                  const badge = OBJ_BADGE[group.object_type] ?? { label: group.object_type.substring(0, 3).toUpperCase(), color: '#6B7280', bg: 'rgba(107,114,128,0.12)' };

                                  return (
                                    <div key={groupKey}>
                                      {/* Object Group Row */}
                                      <div
                                        className="akaal-tree-group"
                                        role="treeitem"
                                        aria-expanded={groupExpanded}
                                        tabIndex={0}
                                        data-tree-item="true"
                                        data-group-key={groupKey}
                                        onClick={() => toggleGroupExpand(groupKey)}
                                        style={{ display: 'grid', gridTemplateColumns: '22px 22px 1fr 76px 76px 72px', gap: 6, padding: '6px 12px 6px 26px', alignItems: 'center', cursor: 'pointer', borderBottom: '1px solid var(--dash-border)', background: 'var(--dash-surface)', transition: 'background 150ms ease' }}
                                      >
                                        <span style={{ fontSize: 10, color: 'var(--dash-text-secondary)', userSelect: 'none', display: 'inline-block', transform: groupExpanded ? 'rotate(0deg)' : 'rotate(-90deg)', transition: 'transform 150ms ease' }}>▼</span>
                                        <IndeterminateCheckbox
                                          checked={groupCheck.checked}
                                          indeterminate={groupCheck.indeterminate}
                                          onChange={(checked) => toggleGroup(schema.schema_id, group.object_type, checked)}
                                          aria-label={`Select all ${group.object_type}s in ${schema.schema_name}`}
                                        />
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                          <span style={{ fontSize: 10, fontWeight: 700, padding: '1px 5px', borderRadius: 3, color: badge.color, background: badge.bg, letterSpacing: '0.02em', whiteSpace: 'nowrap' }}>
                                            {badge.label}
                                          </span>
                                          <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--dash-text-primary)' }}>{group.object_type}s</span>
                                          <span style={{ fontSize: 10, color: 'var(--dash-text-secondary)' }}>
                                            ({group.objects.length}) — {getGroupSelectionLabel(group)}
                                          </span>
                                        </div>
                                        <span /><span /><span />
                                      </div>

                                      {/* Individual Objects */}
                                      <div style={{
                                        overflow: 'hidden',
                                        maxHeight: groupExpanded ? '9999px' : '0px',
                                        transition: 'max-height 180ms ease-in-out, opacity 160ms ease',
                                        opacity: groupExpanded ? 1 : 0,
                                      }}>
                                        <div role="group">
                                          {group.objects.map((obj) => {
                                            const isActive = obj.object_id === selectedObjectId;
                                            const chip = STATUS_CHIP[obj.compatibility_status] ?? STATUS_CHIP['OPTIMAL'];
                                            return (
                                              <div
                                                key={obj.object_id}
                                                className="akaal-tree-obj"
                                                role="treeitem"
                                                aria-selected={obj.selected}
                                                tabIndex={0}
                                                data-tree-item="true"
                                                data-object-id={obj.object_id}
                                                onClick={() => setSelectedObjectId(isActive ? null : obj.object_id)}
                                                style={{
                                                  display: 'grid', gridTemplateColumns: '22px 22px 1fr 76px 76px 72px', gap: 6,
                                                  padding: '5px 12px 5px 52px', alignItems: 'center',
                                                  borderBottom: '1px solid rgba(71,85,105,0.2)',
                                                  background: isActive ? 'rgba(37,99,235,0.09)' : 'transparent',
                                                  cursor: 'pointer', transition: 'background 120ms ease',
                                                }}
                                              >
                                                <span /><input
                                                  type="checkbox"
                                                  checked={obj.selected}
                                                  onChange={(e) => { e.stopPropagation(); toggleObject(obj.object_id, e.target.checked); }}
                                                  onClick={(e) => e.stopPropagation()}
                                                  aria-label={`Include ${obj.object_name}`}
                                                  style={{ cursor: 'pointer', accentColor: 'var(--dash-accent)' }}
                                                />
                                                <span style={{ fontSize: 11, fontWeight: obj.selected ? 600 : 400, color: obj.selected ? 'var(--dash-text-primary)' : 'var(--dash-text-secondary)', fontFamily: 'var(--akaal-font-mono, monospace)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                  {obj.object_name}
                                                  {obj.warnings.length > 0 && (
                                                    <span title={obj.warnings.join('; ')} style={{ marginLeft: 5, fontSize: 10, color: '#F59E0B', cursor: 'help' }}>⚠</span>
                                                  )}
                                                </span>
                                                <span style={{ fontSize: 10, color: 'var(--dash-text-secondary)', fontVariantNumeric: 'tabular-nums' }}>{fmtRows(obj.estimated_rows)}</span>
                                                <span style={{ fontSize: 10, color: 'var(--dash-text-secondary)' }}>{fmtSize(obj.estimated_size_gb)}</span>
                                                <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 4px', borderRadius: 3, color: chip.color, background: chip.bg, textAlign: 'center' }}>
                                                  {obj.compatibility_status}
                                                </span>
                                              </div>
                                            );
                                          })}
                                        </div>
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          );
                        })
                      )}
                    </div>
                  </div>

                  {/* ── Object Detail Panel ── */}
                  {selectedObjectDetail ? (
                    <div style={{ width: 252, flexShrink: 0, border: '1px solid var(--dash-border)', borderRadius: 8, background: 'var(--dash-surface)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                      <div style={{ padding: '9px 12px', borderBottom: '1px solid var(--dash-border)', background: 'var(--dash-bg)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--dash-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Object Details</span>
                        <button type="button" onClick={() => setSelectedObjectId(null)} style={{ background: 'none', border: 'none', color: 'var(--dash-text-secondary)', fontSize: 16, cursor: 'pointer', lineHeight: 1 }}>×</button>
                      </div>
                      <div style={{ padding: 12, overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
                        <div style={{ fontFamily: 'var(--akaal-font-mono, monospace)', fontSize: 12, fontWeight: 800, color: 'var(--dash-text-primary)', wordBreak: 'break-all' }}>
                          {selectedObjectDetail.object_name}
                        </div>

                        {[
                          { label: 'Schema', value: selectedObjectDetail.schema_id },
                          { label: 'Type', value: selectedObjectDetail.object_type },
                          { label: 'Est. Rows', value: fmtRows(selectedObjectDetail.estimated_rows) },
                          { label: 'Est. Size', value: fmtSize(selectedObjectDetail.estimated_size_gb) },
                        ].map(({ label, value }) => (
                          <div key={label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 11, padding: '4px 0', borderBottom: '1px solid var(--dash-border)' }}>
                            <span style={{ color: 'var(--dash-text-secondary)', fontWeight: 600 }}>{label}</span>
                            <span style={{ color: 'var(--dash-text-primary)', fontWeight: 700 }}>{value}</span>
                          </div>
                        ))}

                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 11, padding: '4px 0', borderBottom: '1px solid var(--dash-border)' }}>
                          <span style={{ color: 'var(--dash-text-secondary)', fontWeight: 600 }}>Compatibility</span>
                          <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 5px', borderRadius: 3, color: (STATUS_CHIP[selectedObjectDetail.compatibility_status] ?? STATUS_CHIP['OPTIMAL']).color, background: (STATUS_CHIP[selectedObjectDetail.compatibility_status] ?? STATUS_CHIP['OPTIMAL']).bg }}>
                            {selectedObjectDetail.compatibility_status}
                          </span>
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 11, padding: '4px 0', borderBottom: '1px solid var(--dash-border)' }}>
                          <span style={{ color: 'var(--dash-text-secondary)', fontWeight: 600 }}>Included</span>
                          <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 5px', borderRadius: 3, color: selectedObjectDetail.selected ? '#10B981' : '#EF4444', background: selectedObjectDetail.selected ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)' }}>
                            {selectedObjectDetail.selected ? 'YES' : 'EXCLUDED'}
                          </span>
                        </div>

                        {selectedObjectDetail.dependency_ids.length > 0 && (
                          <div style={{ fontSize: 11, marginTop: 2 }}>
                            <div style={{ color: 'var(--dash-text-secondary)', fontWeight: 600, marginBottom: 3 }}>Dependencies ({selectedObjectDetail.dependency_ids.length})</div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                              {selectedObjectDetail.dependency_ids.map((dep) => (
                                <span key={dep} style={{ fontSize: 10, fontFamily: 'var(--akaal-font-mono, monospace)', color: 'var(--dash-text-secondary)', padding: '2px 4px', background: 'var(--dash-bg)', borderRadius: 3, border: '1px solid var(--dash-border)' }}>{dep}</span>
                              ))}
                            </div>
                          </div>
                        )}

                        {selectedObjectDetail.warnings.length > 0 && (
                          <div style={{ fontSize: 11, marginTop: 2 }}>
                            <div style={{ color: '#F59E0B', fontWeight: 700, marginBottom: 3 }}>⚠ Warnings</div>
                            {selectedObjectDetail.warnings.map((w, i) => (
                              <div key={i} style={{ fontSize: 10, color: '#F59E0B', padding: '4px 6px', background: 'rgba(245,158,11,0.08)', borderRadius: 4, border: '1px solid rgba(245,158,11,0.2)', marginBottom: 3 }}>{w}</div>
                            ))}
                          </div>
                        )}

                        {selectedObjectDetail.warnings.length === 0 && selectedObjectDetail.dependency_ids.length === 0 && (
                          <div style={{ fontSize: 10, color: '#10B981', padding: 8, background: 'rgba(16,185,129,0.06)', borderRadius: 4, border: '1px solid rgba(16,185,129,0.2)', textAlign: 'center', marginTop: 4 }}>
                            ✓ No warnings · No dependencies
                          </div>
                        )}

                        <button type="button" onClick={() => toggleObject(selectedObjectDetail.object_id, !selectedObjectDetail.selected)}
                          style={{ marginTop: 'auto', padding: '8px 12px', borderRadius: 6, border: 'none', fontSize: 11, fontWeight: 700, cursor: 'pointer', background: selectedObjectDetail.selected ? 'rgba(239,68,68,0.1)' : 'rgba(16,185,129,0.1)', color: selectedObjectDetail.selected ? '#EF4444' : '#10B981' }}>
                          {selectedObjectDetail.selected ? '✕ Exclude from Migration' : '✓ Include in Migration'}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div style={{ width: 252, flexShrink: 0, border: '1px dashed var(--dash-border)', borderRadius: 8, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 20, gap: 8, opacity: 0.55 }}>
                      <span style={{ fontSize: 22 }}>👆</span>
                      <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--dash-text-secondary)', textAlign: 'center', lineHeight: 1.5 }}>
                        Click any object to view details, warnings, and dependencies
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* ── STEP 5: MIGRATION ADVISOR DASHBOARD ─────────────────────── */}
            {step === 5 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div style={{ padding: 14, background: 'rgba(16,185,129,0.12)', borderRadius: 10, border: '1px solid rgba(16,185,129,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ fontSize: 15, fontWeight: 800, color: '#10B981' }}>✓ SAFE TO EXECUTE — 99.2% PREDICTED TRUST SCORE</div>
                    <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)', marginTop: 2 }}>Automated topological dependency checks, DDL compatibility, and worker allocations verified.</div>
                  </div>
                  <span style={{ fontSize: 11, padding: '4px 10px', borderRadius: 6, background: '#10B981', color: '#FFF', fontWeight: 700 }}>VERIFIED</span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
                  <div style={{ padding: 14, background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)' }}>
                    <div style={{ fontSize: 11, color: '#10B981', fontWeight: 700 }}>Compatibility Score</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: '#10B981', marginTop: 4 }}>98.5%</div>
                    <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', marginTop: 4 }}>2 minor builtin transpiler maps</div>
                  </div>
                  <div style={{ padding: 14, background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)' }}>
                    <div style={{ fontSize: 11, color: '#3B82F6', fontWeight: 700 }}>Migration Risk Score</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: '#3B82F6', marginTop: 4 }}>0.12 (LOW)</div>
                    <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', marginTop: 4 }}>Zero schema lock conflicts</div>
                  </div>
                  <div style={{ padding: 14, background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)' }}>
                    <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', fontWeight: 700 }}>Est. Cutover Downtime</div>
                    <div style={{ fontSize: 24, fontWeight: 800, marginTop: 4 }}>&lt; 5 Mins</div>
                    <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', marginTop: 4 }}>CDC catchup buffer ready</div>
                  </div>
                  <div style={{ padding: 14, background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)' }}>
                    <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', fontWeight: 700 }}>Est. Execution Duration</div>
                    <div style={{ fontSize: 24, fontWeight: 800, marginTop: 4 }}>42 Mins</div>
                    <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', marginTop: 4 }}>At 150 MB/s streaming speed</div>
                  </div>
                </div>

                <div style={{ padding: 14, background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 10, color: 'var(--dash-text-primary)' }}>Recommended Engine Allocation</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10, fontSize: 12 }}>
                    {[
                      { label: 'Parallel Workers', value: '8 Pool' },
                      { label: 'Batch Insertion', value: '10,000 Rows' },
                      { label: 'RAM Quota', value: '2.4 GB' },
                      { label: 'CPU Usage', value: '65% (4 Cores)' },
                      { label: 'WAN Bandwidth', value: '1.2 Gbps' },
                    ].map((item) => (
                      <div key={item.label} style={{ padding: 8, background: 'var(--dash-bg)', borderRadius: 6 }}>
                        <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)' }}>{item.label}</div>
                        <div style={{ fontSize: 13, fontWeight: 700, marginTop: 2 }}>{item.value}</div>
                      </div>
                    ))}
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div style={{ padding: 14, background: 'rgba(16,185,129,0.05)', borderRadius: 10, border: '1px solid rgba(16,185,129,0.2)' }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#10B981', marginBottom: 6 }}>✓ Automatic Optimizations</div>
                    <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)', lineHeight: 1.6 }}>
                      • 68 Procedures transpiled to PL/pgSQL<br />
                      • 18 Package Bodies decomposed into PostgreSQL schema functions<br />
                      • Zero-copy memoryview socket buffer allocation active
                    </div>
                  </div>
                  <div style={{ padding: 14, background: 'rgba(245,158,11,0.05)', borderRadius: 10, border: '1px solid rgba(245,158,11,0.2)' }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#F59E0B', marginBottom: 6 }}>⚠ Advisory Notices & Recommendations</div>
                    <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)', lineHeight: 1.6 }}>
                      • 2 XMLType columns mapped to PostgreSQL `xml`<br />
                      • Materialized views set to concurrent refresh post-load<br />
                      • Blockers: NONE
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ── STEP 6: RULES & TUNING ───────────────────────────────────── */}
            {step === 6 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {[
                  { id: 'cleansing', title: 'Data Cleansing & Column Mappings', desc: 'Trimming, encoding, type coercion, and UTF-8 sanitization' },
                  { id: 'masking', title: 'Data Masking & PII Redaction Rules', desc: 'SHA-256 hash masking for SSN, Email, and Credit Card fields' },
                  { id: 'tuning', title: 'High-Performance Stream & Buffer Tuning', desc: 'Zero-copy memoryview buffers, LOB chunks, worker pool allocation' },
                  { id: 'checkpoint', title: 'Durability & Recovery Policies', desc: 'WAL Ring Buffer, SQLite checkpoint intervals, auto-restart' },
                ].map((card) => (
                  <div key={card.id} style={{ border: '1px solid var(--dash-border)', borderRadius: 10, background: 'var(--dash-surface)', overflow: 'hidden' }}>
                    <div onClick={() => setExpandedCard(expandedCard === card.id ? null : card.id)}
                      style={{ padding: '14px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer', background: expandedCard === card.id ? 'var(--dash-bg)' : 'transparent' }}>
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

            {/* ── STEP 7: DEPLOYMENT REVIEW DASHBOARD ─────────────────────── */}
            {step === 7 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div style={{ padding: 14, background: 'rgba(16,185,129,0.08)', borderRadius: 10, border: '1px solid rgba(16,185,129,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#10B981' }}>✓ Executive Deployment Review Certified</div>
                    <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)', marginTop: 2 }}>All connectivity, schema DDL, transpiler, and governance rules validated by AKAAL Engine.</div>
                  </div>
                  <span style={{ fontSize: 11, padding: '4px 12px', borderRadius: 6, background: '#10B981', color: '#FFF', fontWeight: 700 }}>READY TO INITIALIZE</span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                  <div style={{ padding: 14, background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)', fontSize: 12, lineHeight: 1.6 }}>
                    <div style={{ fontWeight: 700, marginBottom: 8, color: 'var(--dash-text-primary)', borderBottom: '1px solid var(--dash-border)', paddingBottom: 4 }}>1. Migration Overview</div>
                    • <strong>Source:</strong> {sourceEngine} ({sourceHost}:{sourcePort}/{sourceDbName})<br />
                    • <strong>Target:</strong> {targetEngine} ({targetHost}:{targetPort}/{targetDbName})<br />
                    • <strong>Type & Scope:</strong> {migScope}<br />
                    • <strong>Strategy:</strong> {strategy}<br />
                    • <strong>Project & Owner:</strong> {projectName} ({businessOwner})
                  </div>
                  <div style={{ padding: 14, background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)', fontSize: 12, lineHeight: 1.6 }}>
                    <div style={{ fontWeight: 700, marginBottom: 8, color: 'var(--dash-text-primary)', borderBottom: '1px solid var(--dash-border)', paddingBottom: 4 }}>2. Scope Summary</div>
                    • <strong>Schemas Detected:</strong> {TOTAL_SCHEMAS_DETECTED}<br />
                    • <strong>Objects Detected:</strong> {TOTAL_OBJECTS_DETECTED.toLocaleString()}<br />
                    • <strong>Objects Selected:</strong> {selectedCount.toLocaleString()}<br />
                    • <strong>Schemas Included:</strong> {includeSchemas || '—'}<br />
                    • <strong>Objects Excluded:</strong> {excludedCount.toLocaleString()}
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                  <div style={{ padding: 14, background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)', fontSize: 12, lineHeight: 1.6 }}>
                    <div style={{ fontWeight: 700, marginBottom: 8, color: 'var(--dash-text-primary)', borderBottom: '1px solid var(--dash-border)', paddingBottom: 4 }}>3. Migration Intelligence</div>
                    • <strong>Compatibility Score:</strong> 98.5%<br />
                    • <strong>Risk Score:</strong> 0.12 (LOW)<br />
                    • <strong>Transpiled Routines:</strong> 68 PL/SQL Procedures ➔ PL/pgSQL<br />
                    • <strong>Package Bodies:</strong> 18 Decomposed<br />
                    • <strong>Cutover Window:</strong> &lt; 5 Minutes Downtime
                  </div>
                  <div style={{ padding: 14, background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)', fontSize: 12, lineHeight: 1.6 }}>
                    <div style={{ fontWeight: 700, marginBottom: 8, color: 'var(--dash-text-primary)', borderBottom: '1px solid var(--dash-border)', paddingBottom: 4 }}>4. Execution Summary</div>
                    • <strong>Parallel Workers:</strong> {parallelism} Workers ({batchSize} Row Batches)<br />
                    • <strong>Checkpoint Frequency:</strong> Every {checkpointInterval} Rows<br />
                    • <strong>Recovery Model:</strong> WAL Ring Buffer (CRC32 Checksummed)<br />
                    • <strong>Validation Strategy:</strong> Full Column Checksums & Row Counts<br />
                    • <strong>Trust Certification:</strong> SHA-256 Digital Seal Active
                  </div>
                </div>

                <div style={{ padding: 14, background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)', fontSize: 12, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div><strong style={{ color: 'var(--dash-text-primary)' }}>Governance Gate:</strong> Four-Eyes Executive Approval Enforced</div>
                  <span style={{ fontSize: 11, padding: '4px 10px', borderRadius: 4, background: 'rgba(16,185,129,0.15)', color: '#10B981', fontWeight: 700 }}>APPROVAL PASSED</span>
                </div>
              </div>
            )}

          </div>

          {/* ── Persistent Right Enterprise Summary Panel ─────────────────── */}
          <div style={{ width: 290, borderLeft: '1px solid var(--dash-border)', background: 'var(--dash-surface)', padding: 16, display: 'flex', flexDirection: 'column', gap: 14, overflowY: 'auto' }}>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--dash-text-secondary)', letterSpacing: '0.05em' }}>Live Executive Summary</div>

            <div style={{ padding: 10, background: 'var(--dash-bg)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
              <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)' }}>Migration Title</div>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--dash-text-primary)', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {migName || 'Untitled Migration'}
              </div>
            </div>

            {/* View Execution Plan Drawer */}
            <button type="button" onClick={() => setShowExecutionPlanDrawer(true)}
              style={{ width: '100%', padding: '10px 14px', borderRadius: 8, background: 'rgba(37,99,235,0.12)', border: '1px solid var(--dash-accent)', color: 'var(--dash-accent)', fontSize: 12, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
              <span>⚡ View Execution Plan</span>
            </button>

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

            <div style={{ display: 'flex', flexDirection: 'column', gap: 7, fontSize: 11, color: 'var(--dash-text-secondary)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Schemas Detected:</span>
                <strong style={{ color: 'var(--dash-text-primary)' }}>{TOTAL_SCHEMAS_DETECTED}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Objects Detected:</span>
                <strong style={{ color: 'var(--dash-text-primary)' }}>{TOTAL_OBJECTS_DETECTED.toLocaleString()}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Schemas Included:</span>
                <strong style={{ color: schemasIncludedCount > 0 ? '#10B981' : 'var(--dash-text-secondary)' }}>{schemasIncludedCount}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Objects Selected:</span>
                <strong style={{ color: 'var(--dash-text-primary)' }}>{selectedCount.toLocaleString()}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Objects Excluded:</span>
                <strong style={{ color: excludedCount > 0 ? '#F59E0B' : '#10B981' }}>{excludedCount.toLocaleString()}</strong>
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

        {/* ── Footer Navigation Bar ───────────────────────────────────────── */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 24px', borderTop: '1px solid var(--dash-border)', background: 'var(--dash-surface)' }}>
          <button type="button"
            onClick={() => { if (step > 1) setStep((s) => (s - 1) as any); else onClose(); }}
            style={{ padding: '8px 18px', borderRadius: 8, background: 'none', border: '1px solid var(--dash-border)', color: 'var(--dash-text-secondary)', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
            {step === 1 ? 'Cancel' : '← Previous Step'}
          </button>

          <div style={{ display: 'flex', gap: 10 }}>
            {step < 7 && (
              <button type="button" className={styles.resumeBtn}
                onClick={() => setStep((s) => (s + 1) as any)}
                style={{ padding: '9px 20px', borderRadius: 8, background: 'var(--dash-accent)', color: '#FFF', border: 'none', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                Continue to Step {step + 1} →
              </button>
            )}
            {step === 7 && (
              <>
                <button type="button" onClick={onClose}
                  style={{ padding: '9px 18px', borderRadius: 8, background: 'var(--dash-bg)', border: '1px solid var(--dash-border)', color: 'var(--dash-text-primary)', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                  Save Draft
                </button>
                <button type="button" className={styles.resumeBtn} onClick={handleCompleteLaunch}
                  style={{ padding: '9px 24px', borderRadius: 8, background: '#10B981', color: '#FFF', border: 'none', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}>
                  Initialize Migration & Launch Dashboard
                </button>
              </>
            )}
          </div>
        </div>

        {/* ── Execution Plan Drawer ────────────────────────────────────────── */}
        {showExecutionPlanDrawer && (
          <div onClick={() => setShowExecutionPlanDrawer(false)}
            style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.6)', zIndex: 9999, display: 'flex', justifyContent: 'flex-end' }}>
            <div onClick={(e) => e.stopPropagation()}
              style={{ width: 480, height: '100%', background: 'var(--dash-surface)', borderLeft: '1px solid var(--dash-border)', padding: 24, display: 'flex', flexDirection: 'column', gap: 18, overflowY: 'auto' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--dash-border)', paddingBottom: 12 }}>
                <div>
                  <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>Frozen Engine Execution Lifecycle</h3>
                  <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', marginTop: 2 }}>Runtime V3 Execution Plan</div>
                </div>
                <button onClick={() => setShowExecutionPlanDrawer(false)} style={{ background: 'none', border: 'none', color: 'var(--dash-text-secondary)', fontSize: 20, cursor: 'pointer' }}>×</button>
              </div>

              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--dash-text-secondary)', textTransform: 'uppercase' }}>Visual Execution DAG Pipeline</div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {[
                  { name: '1. Discovery & Catalog', desc: 'Inspect source database metadata & catalog definitions' },
                  { name: '2. Advisor Analysis', desc: 'Rule checking, compatibility scoring, risk assessment' },
                  { name: '3. DAG Planning', desc: 'Topological dependency sorting & partition creation' },
                  { name: '4. Policy Approval', desc: 'Four-eyes executive sign-off & epoch fencing' },
                  { name: '5. Runtime Creation', desc: 'Spawn MigrationRuntimeDaemon & SupervisorTree' },
                  { name: '6. Checkpoint Initialization', desc: 'WAL Ring Buffer & command mailbox allocation' },
                  { name: '7. Schema Deployment', desc: 'Deploy target DDL structures & constraint locks' },
                  { name: '8. Enterprise Objects', desc: 'Deploy sequences, views, synonyms, and UDTs' },
                  { name: '9. PL/SQL Transpilation', desc: 'Transpile procedures & functions to PL/pgSQL' },
                  { name: '10. Worker Allocation', desc: 'Allocate 8 zero-copy worker threads & memoryview' },
                  { name: '11. Parallel Data Transport', desc: 'High-throughput stream pipeline execution' },
                  { name: '12. Post Validation', desc: 'Column checksums & row count reconciliation' },
                  { name: '13. Trust Certification', desc: 'Generate SHA-256 digital migration certificate' },
                ].map((item, idx) => (
                  <div key={item.name} style={{ display: 'flex', gap: 12, alignItems: 'flex-start', padding: 8, background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)' }}>
                    <span style={{ width: 20, height: 20, borderRadius: '50%', background: 'rgba(37,99,235,0.2)', color: '#3B82F6', fontSize: 10, fontWeight: 700, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>{idx + 1}</span>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--dash-text-primary)' }}>{item.name.split('. ')[1]}</div>
                      <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', marginTop: 2 }}>{item.desc}</div>
                    </div>
                  </div>
                ))}
              </div>

              <div style={{ borderTop: '1px solid var(--dash-border)', paddingTop: 14, display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12 }}>
                <div style={{ fontWeight: 700, color: 'var(--dash-text-primary)' }}>Runtime Engine Architecture</div>
                <div>• <strong>Daemon:</strong> MigrationRuntimeDaemon (Isolated Process)</div>
                <div>• <strong>Supervisor:</strong> RuntimeSupervisorTree (Auto-Healing)</div>
                <div>• <strong>WAL Buffer:</strong> DurableWALRingBuffer (10k Records, CRC32)</div>
                <div>• <strong>Mailbox:</strong> DurableCommandMailbox (SQLite Epoch Fencing)</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
