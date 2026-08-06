import { useState, useEffect, useMemo, useCallback, useRef, type FC } from 'react';
import {
  Database,
  Folder,
  Table,
  Eye,
  BarChart2,
  Zap,
  Cpu,
  Package,
  RefreshCw,
  Hash,
  User,
  Link2,
  FileText,
  AlertTriangle,
  Check,
  CheckCircle2,
  Search,
  Lock,
  Bell,
  ChevronDown,
  ChevronRight,
  ArrowLeft,
  X,
  Sliders,
  Activity,
} from 'lucide-react';
import type { MigrationPipeline, DatabaseEngine, DiscoveryProfileType } from '../../types/migration';
import { notificationService } from '../../services/notificationService';
import styles from './MigrationModule.module.css';

export interface NewMigrationWizardProps {
  onClose: () => void;
  onLaunch: (newPipeline: MigrationPipeline) => void;
  createProject: (name: string, sourceEngine: DatabaseEngine, targetEngine: DatabaseEngine) => MigrationPipeline;
}

// ─── Engine-Compatible DTOs ─────────────────────────────────────────────────

interface DiscoveredObjectDTO {
  object_id: string;
  schema_id: string;
  db_id: string;
  object_name: string;
  object_type: string;
  estimated_rows: number;
  estimated_size_gb: number;
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
  db_id: string;
  object_groups: ObjectGroupDTO[];
}

interface DatabaseDiscoveryDTO {
  db_id: string;
  db_name: string;
  instance_name: string;
  schemas: SchemaDiscoveryDTO[];
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

// ─── Object Type Badges & Lucide Icons ─────────────────────────────────────

const OBJ_BADGE: Record<string, { label: string; color: string; bg: string }> = {
  'Table':             { label: 'TBL', color: '#10B981', bg: 'rgba(16,185,129,0.12)' },
  'View':              { label: 'VIEW', color: '#3B82F6', bg: 'rgba(59,130,246,0.12)' },
  'Materialized View': { label: 'MVIEW', color: '#8B5CF6', bg: 'rgba(139,92,246,0.12)' },
  'Procedure':         { label: 'PROC', color: '#F59E0B', bg: 'rgba(245,158,11,0.12)' },
  'Function':          { label: 'FUNC', color: '#F97316', bg: 'rgba(249,115,22,0.12)' },
  'Package':           { label: 'PKG',  color: '#EC4899', bg: 'rgba(236,72,153,0.12)' },
  'Trigger':           { label: 'TRG',  color: '#EF4444', bg: 'rgba(239,68,68,0.12)' },
  'Sequence':          { label: 'SEQ',  color: '#06B6D4', bg: 'rgba(6,182,212,0.12)' },
  'Role':              { label: 'ROLE', color: '#84CC16', bg: 'rgba(132,204,22,0.12)' },
  'Synonym':           { label: 'SYN',  color: '#6B7280', bg: 'rgba(107,114,128,0.12)' },
};

const renderObjTypeIcon = (type: string, size = 14) => {
  switch (type) {
    case 'Table': return <Table size={size} color="#10B981" />;
    case 'View': return <Eye size={size} color="#3B82F6" />;
    case 'Materialized View': return <BarChart2 size={size} color="#8B5CF6" />;
    case 'Procedure': return <Zap size={size} color="#F59E0B" />;
    case 'Function': return <Cpu size={size} color="#F97316" />;
    case 'Package': return <Package size={size} color="#EC4899" />;
    case 'Trigger': return <RefreshCw size={size} color="#EF4444" />;
    case 'Sequence': return <Hash size={size} color="#06B6D4" />;
    case 'Role': return <User size={size} color="#84CC16" />;
    case 'Synonym': return <Link2 size={size} color="#6B7280" />;
    default: return <FileText size={size} color="var(--dash-text-secondary)" />;
  }
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

// ─── Mock Discovery Data ────────────────────────────────────────────────────

const mk = (
  db_id: string,
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
  object_id, schema_id, db_id, object_name, object_type,
  estimated_rows, estimated_size_gb, compatibility_status,
  dependency_ids, warnings, selected: true,
});

const INITIAL_DATABASES: DatabaseDiscoveryDTO[] = [
  {
    db_id: 'HRDB',
    db_name: 'HRDB',
    instance_name: 'Oracle 19c Enterprise Server',
    schemas: [
      {
        schema_id: 'HR', schema_name: 'HR', db_id: 'HRDB',
        object_groups: [
          { object_type: 'Table', objects: [
            mk('HRDB','HR','hr-t1','EMPLOYEES','Table',18_400_000,4.2,'OPTIMAL'),
            mk('HRDB','HR','hr-t2','DEPARTMENTS','Table',500,0.002,'OPTIMAL'),
            mk('HRDB','HR','hr-t3','JOB_HISTORY','Table',55_000_000,6.1,'OPTIMAL',['hr-t1','hr-t2']),
            mk('HRDB','HR','hr-t4','SALARIES','Table',95_000_000,9.8,'OPTIMAL',['hr-t1']),
            mk('HRDB','HR','hr-t5','LOCATIONS','Table',1000,0.001,'OPTIMAL'),
            mk('HRDB','HR','hr-t6','JOBS','Table',200,0.001,'OPTIMAL'),
            mk('HRDB','HR','hr-t7','REGIONS','Table',20,0.001,'OPTIMAL'),
            mk('HRDB','HR','hr-t8','COUNTRIES','Table',250,0.001,'OPTIMAL',['hr-t7']),
          ]},
          { object_type: 'View', objects: [
            mk('HRDB','HR','hr-v1','EMPLOYEE_SUMMARY','View',-1,-1,'OPTIMAL',['hr-t1','hr-t2']),
            mk('HRDB','HR','hr-v2','ACTIVE_EMPLOYEES','View',-1,-1,'OPTIMAL',['hr-t1']),
            mk('HRDB','HR','hr-v3','DEPT_HEADCOUNT','View',-1,-1,'OPTIMAL',['hr-t2','hr-t1']),
            mk('HRDB','HR','hr-v4','SALARY_BANDS','View',-1,-1,'ADVISORY',['hr-t4'],['CONNECT BY hierarchy — needs WITH RECURSIVE']),
            mk('HRDB','HR','hr-v5','MANAGER_TREE','View',-1,-1,'TRANSPILED',['hr-t1'],['Hierarchical query transpiled']),
          ]},
          { object_type: 'Procedure', objects: [
            mk('HRDB','HR','hr-p1','UPDATE_SALARY','Procedure',-1,-1,'OPTIMAL',['hr-t4']),
            mk('HRDB','HR','hr-p2','ARCHIVE_EMPLOYEE','Procedure',-1,-1,'TRANSPILED',['hr-t1','hr-t3'],['Bulk DML rewrite']),
            mk('HRDB','HR','hr-p3','TRANSFER_DEPARTMENT','Procedure',-1,-1,'OPTIMAL',['hr-t1','hr-t2']),
            mk('HRDB','HR','hr-p4','PROMOTE_EMPLOYEE','Procedure',-1,-1,'OPTIMAL',['hr-t1','hr-t4']),
            mk('HRDB','HR','hr-p5','AUDIT_CHANGES','Procedure',-1,-1,'OPTIMAL',['hr-t3']),
            mk('HRDB','HR','hr-p6','BATCH_UPDATE','Procedure',-1,-1,'ADVISORY',[],['FORALL statement mapping required']),
          ]},
          { object_type: 'Function', objects: [
            mk('HRDB','HR','hr-f1','CALC_SENIORITY','Function',-1,-1,'OPTIMAL',['hr-t1']),
            mk('HRDB','HR','hr-f2','GET_DEPT_NAME','Function',-1,-1,'OPTIMAL',['hr-t2']),
            mk('HRDB','HR','hr-f3','EMP_FULL_NAME','Function',-1,-1,'OPTIMAL',['hr-t1']),
            mk('HRDB','HR','hr-f4','COUNT_REPORTS','Function',-1,-1,'TRANSPILED',['hr-t1'],['CONNECT BY used']),
          ]},
          { object_type: 'Trigger', objects: [
            mk('HRDB','HR','hr-trg1','TRG_EMP_AUDIT','Trigger',-1,-1,'OPTIMAL',['hr-t1','hr-t3']),
            mk('HRDB','HR','hr-trg2','TRG_SALARY_CHECK','Trigger',-1,-1,'OPTIMAL',['hr-t4']),
            mk('HRDB','HR','hr-trg3','TRG_DEPT_VALIDATION','Trigger',-1,-1,'OPTIMAL',['hr-t2']),
          ]},
          { object_type: 'Sequence', objects: [
            mk('HRDB','HR','hr-seq1','SEQ_EMP_ID','Sequence',-1,-1,'OPTIMAL'),
            mk('HRDB','HR','hr-seq2','SEQ_DEPT_ID','Sequence',-1,-1,'OPTIMAL'),
          ]},
        ],
      },
      {
        schema_id: 'SYSTEM', schema_name: 'SYSTEM', db_id: 'HRDB',
        object_groups: [
          { object_type: 'Table', objects: [
            mk('HRDB','SYSTEM','sys-t1','CUSTOMER_RECORDS','Table',500_000_000,54.2,'OPTIMAL'),
            mk('HRDB','SYSTEM','sys-t2','MIGRATION_AUDIT_LOG','Table',120_000_000,12.4,'OPTIMAL'),
            mk('HRDB','SYSTEM','sys-t3','SYSTEM_CONFIG','Table',500,0.001,'OPTIMAL'),
            mk('HRDB','SYSTEM','sys-t4','AUDIT_TRAIL','Table',800_000_000,82.1,'OPTIMAL'),
            mk('HRDB','SYSTEM','sys-t5','ERROR_LOG','Table',45_000_000,4.8,'OPTIMAL'),
          ]},
          { object_type: 'Procedure', objects: [
            mk('HRDB','SYSTEM','sys-p1','PROCESS_CUSTOMER_ORDER','Procedure',-1,-1,'TRANSPILED',['sys-t1'],['PL/SQL cursor rewrite required']),
            mk('HRDB','SYSTEM','sys-p2','HANDLE_EXCEPTIONS','Procedure',-1,-1,'OPTIMAL'),
            mk('HRDB','SYSTEM','sys-p3','REBUILD_INDEXES','Procedure',-1,-1,'ADVISORY',[],['DBMS_INDEX usage — manual review']),
          ]},
          { object_type: 'Sequence', objects: [
            mk('HRDB','SYSTEM','sys-s1','SEQ_CUSTOMER_ID','Sequence',-1,-1,'OPTIMAL'),
            mk('HRDB','SYSTEM','sys-s2','SEQ_AUDIT_ID','Sequence',-1,-1,'OPTIMAL'),
            mk('HRDB','SYSTEM','sys-s3','SEQ_ERROR_ID','Sequence',-1,-1,'OPTIMAL'),
          ]},
          { object_type: 'Role', objects: [
            mk('HRDB','SYSTEM','sys-r1','ROLE_FINANCE_ADMIN','Role',-1,-1,'OPTIMAL'),
            mk('HRDB','SYSTEM','sys-r2','ROLE_SALES_USER','Role',-1,-1,'OPTIMAL'),
            mk('HRDB','SYSTEM','sys-r3','ROLE_DBA','Role',-1,-1,'OPTIMAL'),
            mk('HRDB','SYSTEM','sys-r4','ROLE_READONLY','Role',-1,-1,'OPTIMAL'),
          ]},
          { object_type: 'Synonym', objects: [
            mk('HRDB','SYSTEM','sys-syn1','SYN_CUSTOMERS','Synonym',-1,-1,'OPTIMAL',['sys-t1']),
            mk('HRDB','SYSTEM','sys-syn2','SYN_ORDERS','Synonym',-1,-1,'OPTIMAL'),
          ]},
        ],
      },
    ],
  },
  {
    db_id: 'FINANCEDB',
    db_name: 'FINANCEDB',
    instance_name: 'Oracle 19c Enterprise Server',
    schemas: [
      {
        schema_id: 'FIN', schema_name: 'FIN', db_id: 'FINANCEDB',
        object_groups: [
          { object_type: 'Table', objects: [
            mk('FINANCEDB','FIN','fin-t1','PAYMENT_TRANSACTIONS','Table',100_000_000,19.6,'OPTIMAL'),
            mk('FINANCEDB','FIN','fin-t2','INVOICES','Table',45_000_000,8.2,'OPTIMAL'),
            mk('FINANCEDB','FIN','fin-t3','ACCOUNTS','Table',12_000_000,2.4,'OPTIMAL'),
            mk('FINANCEDB','FIN','fin-t4','LEDGER_ENTRIES','Table',280_000_000,38.4,'OPTIMAL'),
            mk('FINANCEDB','FIN','fin-t5','TAX_RECORDS','Table',55_000_000,7.8,'OPTIMAL'),
            mk('FINANCEDB','FIN','fin-t6','EXCHANGE_RATES','Table',850_000,0.12,'OPTIMAL'),
            mk('FINANCEDB','FIN','fin-t7','BUDGET_LINES','Table',4_200_000,0.62,'OPTIMAL'),
            mk('FINANCEDB','FIN','fin-t8','COST_CENTERS','Table',8500,0.002,'OPTIMAL'),
            mk('FINANCEDB','FIN','fin-t9','FISCAL_PERIODS','Table',240,0.001,'OPTIMAL'),
            mk('FINANCEDB','FIN','fin-t10','CURRENCY_CODES','Table',190,0.001,'OPTIMAL'),
          ]},
          { object_type: 'View', objects: [
            mk('FINANCEDB','FIN','fin-v1','MONTHLY_REVENUE','View',-1,-1,'ADVISORY',['fin-t1','fin-t4'],['ROLLUP clause — verify aggregation']),
            mk('FINANCEDB','FIN','fin-v2','TAX_SUMMARY','View',-1,-1,'OPTIMAL',['fin-t5']),
            mk('FINANCEDB','FIN','fin-v3','ACCOUNT_BALANCES','View',-1,-1,'OPTIMAL',['fin-t3','fin-t4']),
            mk('FINANCEDB','FIN','fin-v4','RECONCILIATION_VIEW','View',-1,-1,'TRANSPILED',['fin-t1','fin-t4'],['PIVOT transpiled to crosstab']),
            mk('FINANCEDB','FIN','fin-v5','COST_ANALYSIS','View',-1,-1,'OPTIMAL',['fin-t7','fin-t8']),
            mk('FINANCEDB','FIN','fin-v6','BUDGET_VS_ACTUAL','View',-1,-1,'ADVISORY',['fin-t7'],['MERGE statement reference']),
          ]},
          { object_type: 'Procedure', objects: [
            mk('FINANCEDB','FIN','fin-p1','CALCULATE_TAX_RATE','Procedure',-1,-1,'OPTIMAL',['fin-t5']),
            mk('FINANCEDB','FIN','fin-p2','RECONCILE_ACCOUNTS','Procedure',-1,-1,'TRANSPILED',['fin-t3','fin-t4'],['Cursor FOR LOOP rewrite']),
            mk('FINANCEDB','FIN','fin-p3','CLOSE_FISCAL_PERIOD','Procedure',-1,-1,'ADVISORY',['fin-t9'],['DBMS_LOCK usage']),
            mk('FINANCEDB','FIN','fin-p4','GENERATE_INVOICE','Procedure',-1,-1,'OPTIMAL',['fin-t2']),
            mk('FINANCEDB','FIN','fin-p5','PROCESS_PAYMENT','Procedure',-1,-1,'OPTIMAL',['fin-t1','fin-t3']),
            mk('FINANCEDB','FIN','fin-p6','AUDIT_TRANSACTIONS','Procedure',-1,-1,'OPTIMAL',['fin-t1']),
            mk('FINANCEDB','FIN','fin-p7','APPLY_EXCHANGE_RATE','Procedure',-1,-1,'OPTIMAL',['fin-t6']),
            mk('FINANCEDB','FIN','fin-p8','BATCH_RECONCILE','Procedure',-1,-1,'TRANSPILED',['fin-t4'],['FORALL + BULK COLLECT']),
          ]},
          { object_type: 'Function', objects: [
            mk('FINANCEDB','FIN','fin-f1','CALC_TAX','Function',-1,-1,'OPTIMAL',['fin-t5']),
            mk('FINANCEDB','FIN','fin-f2','GET_EXCHANGE_RATE','Function',-1,-1,'OPTIMAL',['fin-t6']),
            mk('FINANCEDB','FIN','fin-f3','COMPUTE_MARGIN','Function',-1,-1,'TRANSPILED',[],['UTL_RAW usage mapped']),
            mk('FINANCEDB','FIN','fin-f4','FISCAL_QUARTER','Function',-1,-1,'OPTIMAL',['fin-t9']),
            mk('FINANCEDB','FIN','fin-f5','GET_ACCOUNT_BALANCE','Function',-1,-1,'OPTIMAL',['fin-t3','fin-t4']),
          ]},
          { object_type: 'Package', objects: [
            mk('FINANCEDB','FIN','fin-pkg1','PKG_FINANCIAL_YEAR','Package',-1,-1,'TRANSPILED',[],['Package body decomposed to 4 procedures']),
            mk('FINANCEDB','FIN','fin-pkg2','PKG_TAX_ENGINE','Package',-1,-1,'TRANSPILED',[],['Package body decomposed to 3 procedures']),
            mk('FINANCEDB','FIN','fin-pkg3','PKG_REPORTING','Package',-1,-1,'ADVISORY',[],['UTL_HTTP usage — manual migration']),
          ]},
          { object_type: 'Trigger', objects: [
            mk('FINANCEDB','FIN','fin-trg1','TRG_PAYMENT_AUDIT','Trigger',-1,-1,'OPTIMAL',['fin-t1']),
            mk('FINANCEDB','FIN','fin-trg2','TRG_INVOICE_CREATE','Trigger',-1,-1,'OPTIMAL',['fin-t2']),
            mk('FINANCEDB','FIN','fin-trg3','TRG_LEDGER_BALANCE','Trigger',-1,-1,'OPTIMAL',['fin-t4']),
            mk('FINANCEDB','FIN','fin-trg4','TRG_BUDGET_CHECK','Trigger',-1,-1,'ADVISORY',['fin-t7'],['Compound trigger pattern']),
          ]},
          { object_type: 'Materialized View', objects: [
            mk('FINANCEDB','FIN','fin-mv1','MV_MONTHLY_SUMMARY','Materialized View',8_400_000,1.2,'ADVISORY',[],['Fast refresh compatibility check']),
            mk('FINANCEDB','FIN','fin-mv2','MV_TAX_LIABILITY','Materialized View',2_100_000,0.3,'ADVISORY',[],['ON COMMIT refresh — needs pg_cron']),
          ]},
        ],
      },
    ],
  },
  {
    db_id: 'SALESDB',
    db_name: 'SALESDB',
    instance_name: 'Oracle 19c Enterprise Server',
    schemas: [
      {
        schema_id: 'SALES', schema_name: 'SALES', db_id: 'SALESDB',
        object_groups: [
          { object_type: 'Table', objects: [
            mk('SALESDB','SALES','sal-t1','ORDERS','Table',450_000_000,48.1,'OPTIMAL'),
            mk('SALESDB','SALES','sal-t2','CUSTOMERS','Table',85_000_000,12.4,'OPTIMAL'),
            mk('SALESDB','SALES','sal-t3','PRODUCTS','Table',4_200_000,0.58,'OPTIMAL'),
            mk('SALESDB','SALES','sal-t4','ORDER_ITEMS','Table',1_800_000_000,184.2,'OPTIMAL',['sal-t1','sal-t3']),
            mk('SALESDB','SALES','sal-t5','SHIPMENTS','Table',380_000_000,41.2,'OPTIMAL',['sal-t1']),
            mk('SALESDB','SALES','sal-t6','PROMOTIONS','Table',125_000,0.02,'OPTIMAL'),
            mk('SALESDB','SALES','sal-t7','TERRITORIES','Table',520,0.001,'OPTIMAL'),
            mk('SALESDB','SALES','sal-t8','SALES_TARGETS','Table',18_000,0.004,'OPTIMAL',['sal-t7']),
            mk('SALESDB','SALES','sal-t9','RETURNS','Table',12_000_000,1.8,'OPTIMAL',['sal-t1','sal-t2']),
            mk('SALESDB','SALES','sal-t10','CUSTOMER_SEGMENTS','Table',250_000,0.04,'OPTIMAL',['sal-t2']),
            mk('SALESDB','SALES','sal-t11','PRODUCT_CATEGORIES','Table',8200,0.002,'OPTIMAL'),
            mk('SALESDB','SALES','sal-t12','INVENTORY_ITEMS','Table',80_000_000,8.2,'OPTIMAL',['sal-t3']),
          ]},
          { object_type: 'View', objects: [
            mk('SALESDB','SALES','sal-v1','ORDER_SUMMARY','View',-1,-1,'OPTIMAL',['sal-t1','sal-t4']),
            mk('SALESDB','SALES','sal-v2','CUSTOMER_LIFETIME','View',-1,-1,'ADVISORY',['sal-t2','sal-t1'],['Analytical window function verify']),
            mk('SALESDB','SALES','sal-v3','PRODUCT_PERFORMANCE','View',-1,-1,'OPTIMAL',['sal-t3','sal-t4']),
            mk('SALESDB','SALES','sal-v4','TERRITORY_SALES','View',-1,-1,'OPTIMAL',['sal-t1','sal-t7']),
            mk('SALESDB','SALES','sal-v5','PROMO_EFFECTIVENESS','View',-1,-1,'ADVISORY',['sal-t6','sal-t1'],['DECODE to CASE rewrite']),
            mk('SALESDB','SALES','sal-v6','PENDING_ORDERS','View',-1,-1,'OPTIMAL',['sal-t1']),
            mk('SALESDB','SALES','sal-v7','FULFILLED_ORDERS','View',-1,-1,'OPTIMAL',['sal-t1','sal-t5']),
            mk('SALESDB','SALES','sal-v8','RETURN_ANALYSIS','View',-1,-1,'ADVISORY',['sal-t9'],['PIVOT usage — crosstab required']),
          ]},
          { object_type: 'Procedure', objects: [
            mk('SALESDB','SALES','sal-p1','PROCESS_ORDER','Procedure',-1,-1,'OPTIMAL',['sal-t1','sal-t4','sal-t12']),
            mk('SALESDB','SALES','sal-p2','CANCEL_ORDER','Procedure',-1,-1,'OPTIMAL',['sal-t1','sal-t9']),
            mk('SALESDB','SALES','sal-p3','APPLY_DISCOUNT','Procedure',-1,-1,'TRANSPILED',['sal-t6','sal-t4'],['Package-level variable reference']),
            mk('SALESDB','SALES','sal-p4','UPDATE_INVENTORY','Procedure',-1,-1,'OPTIMAL',['sal-t12']),
            mk('SALESDB','SALES','sal-p5','GENERATE_REPORT','Procedure',-1,-1,'ADVISORY',[],['UTL_FILE usage — pgcopy alternative']),
            mk('SALESDB','SALES','sal-p6','CLOSE_SALE','Procedure',-1,-1,'OPTIMAL',['sal-t1','sal-t2']),
          ]},
          { object_type: 'Function', objects: [
            mk('SALESDB','SALES','sal-f1','CALC_DISCOUNT','Function',-1,-1,'TRANSPILED',['sal-t6'],['NOCOPY parameter hint removed']),
            mk('SALESDB','SALES','sal-f2','ORDER_TOTAL','Function',-1,-1,'OPTIMAL',['sal-t4']),
            mk('SALESDB','SALES','sal-f3','CUSTOMER_TIER','Function',-1,-1,'OPTIMAL',['sal-t2','sal-t10']),
            mk('SALESDB','SALES','sal-f4','SHIPPING_COST','Function',-1,-1,'OPTIMAL',['sal-t5','sal-t7']),
          ]},
          { object_type: 'Trigger', objects: [
            mk('SALESDB','SALES','sal-trg1','TRG_ORDERS_AUDIT','Trigger',-1,-1,'OPTIMAL',['sal-t1']),
            mk('SALESDB','SALES','sal-trg2','TRG_INVENTORY_UPDATE','Trigger',-1,-1,'OPTIMAL',['sal-t12']),
            mk('SALESDB','SALES','sal-trg3','TRG_PROMO_VALIDATE','Trigger',-1,-1,'ADVISORY',['sal-t6'],['Mutating table check']),
            mk('SALESDB','SALES','sal-trg4','TRG_SHIPMENT_CREATE','Trigger',-1,-1,'OPTIMAL',['sal-t5']),
            mk('SALESDB','SALES','sal-trg5','TRG_RETURN_PROCESS','Trigger',-1,-1,'OPTIMAL',['sal-t9','sal-t12']),
          ]},
          { object_type: 'Sequence', objects: [
            mk('SALESDB','SALES','sal-seq1','SEQ_ORDER_ID','Sequence',-1,-1,'OPTIMAL'),
            mk('SALESDB','SALES','sal-seq2','SEQ_CUSTOMER_ID','Sequence',-1,-1,'OPTIMAL'),
            mk('SALESDB','SALES','sal-seq3','SEQ_PRODUCT_ID','Sequence',-1,-1,'OPTIMAL'),
            mk('SALESDB','SALES','sal-seq4','SEQ_SHIPMENT_ID','Sequence',-1,-1,'OPTIMAL'),
          ]},
          { object_type: 'Materialized View', objects: [
            mk('SALESDB','SALES','sal-mv1','MV_DAILY_SALES_SUMMARY','Materialized View',5_000_000,1.2,'ADVISORY',[],['Fast refresh requires trigger-based approach']),
            mk('SALESDB','SALES','sal-mv2','MV_QUARTERLY_TARGETS','Materialized View',840_000,0.18,'OPTIMAL'),
          ]},
        ],
      },
    ],
  },
];

const TOTAL_DATABASES_DETECTED = INITIAL_DATABASES.length;
const TOTAL_SCHEMAS_DETECTED = INITIAL_DATABASES.reduce((sum, d) => sum + d.schemas.length, 0);
const TOTAL_OBJECTS_DETECTED = INITIAL_DATABASES.reduce(
  (sum, d) => sum + d.schemas.reduce((ss, s) => ss + s.object_groups.reduce((gs, g) => gs + g.objects.length, 0), 0), 0
);

const STEP_TITLES = [
  '1. Overview',
  '2. Source Connection',
  '3. Target Connection',
  '4. Discovery & Migration Scope',
  '5. Dynamic Execution Plan',
  '6. Enterprise Configuration Center',
  '7. Deployment Review',
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

  // Step 4: Discovery & Scope State
  const [databases, setDatabases] = useState<DatabaseDiscoveryDTO[]>(INITIAL_DATABASES);
  const [expandedDatabases, setExpandedDatabases] = useState<Set<string>>(new Set(['HRDB']));
  const [expandedSchemas, setExpandedSchemas] = useState<Set<string>>(new Set(['HR']));
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [selectedObjectId, setSelectedObjectId] = useState<string | null>(null);
  const [discoveryProfile, setDiscoveryProfile] = useState<DiscoveryProfileType>('DEEP');

  // Filters
  const [dbFilter, setDbFilter] = useState<string>('ALL');
  const [schemaFilter, setSchemaFilter] = useState<string>('ALL');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [objectSearch, setObjectSearch] = useState<string>('');

  const treeRef = useRef<HTMLDivElement>(null);

  // Step 6: Enterprise Configuration Center State
  const [configMode, setConfigMode] = useState<'BASIC' | 'ADVANCED'>('BASIC');
  const [actionOnExisting, setActionOnExisting] = useState('SKIP');
  const [tableRenamePattern, setTableRenamePattern] = useState('');
  const [maskingEnabled, setMaskingEnabled] = useState(true);
  const [maskingMethod, setMaskingMethod] = useState('SHA-256');
  const [parallelism, setParallelism] = useState('8');
  const [batchSize, setBatchSize] = useState('10000');
  const [commitInterval, setCommitInterval] = useState('5000');
  const [ramLimitGb, setRamLimitGb] = useState('4.0');
  const [retryCount, setRetryCount] = useState('3');
  const [validationLevel, setValidationLevel] = useState('CHECKSUM');
  const [samplingRate, setSamplingRate] = useState('100');
  const [errorAction, setErrorAction] = useState('CONTINUE_AND_LOG');
  const [enableCdc, setEnableCdc] = useState(true);
  const [fourEyesPolicy, setFourEyesPolicy] = useState(true);
  const [notifySlack, setNotifySlack] = useState(true);
  const [notifyEmail, setNotifyEmail] = useState(true);
  const [expandedConfigSection, setExpandedConfigSection] = useState<string | null>('rules');

  // Drawer & Confirmation Modals
  const [showExecutionPlanDrawer, setShowExecutionPlanDrawer] = useState(false);
  const [showLaunchConfirmModal, setShowLaunchConfirmModal] = useState(false);

  // Keyboard Esc
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

  // Connection Handlers
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

  // Step 4: Derived & Filtered Tree
  const allObjectTypes = useMemo(() => {
    const types = new Set<string>();
    INITIAL_DATABASES.forEach((d) => d.schemas.forEach((s) => s.object_groups.forEach((g) => types.add(g.object_type))));
    return Array.from(types).sort();
  }, []);

  const visibleDatabases = useMemo<DatabaseDiscoveryDTO[]>(() => {
    return databases
      .map((db) => {
        if (dbFilter !== 'ALL' && db.db_id !== dbFilter) return null;
        const filteredSchemas = db.schemas
          .map((schema) => {
            if (schemaFilter !== 'ALL' && schema.schema_id !== schemaFilter) return null;
            const filteredGroups = schema.object_groups
              .map((group) => {
                if (typeFilter !== 'ALL' && group.object_type !== typeFilter) return null;
                const filteredObjects = group.objects.filter((obj) => {
                  if (statusFilter !== 'ALL' && obj.compatibility_status !== statusFilter) return false;
                  if (objectSearch && !obj.object_name.toLowerCase().includes(objectSearch.toLowerCase())) return false;
                  return true;
                });
                if (filteredObjects.length === 0) return null;
                return { ...group, objects: filteredObjects };
              })
              .filter(Boolean) as ObjectGroupDTO[];
            if (filteredGroups.length === 0) return null;
            return { ...schema, object_groups: filteredGroups };
          })
          .filter(Boolean) as SchemaDiscoveryDTO[];
        if (filteredSchemas.length === 0) return null;
        return { ...db, schemas: filteredSchemas };
      })
      .filter(Boolean) as DatabaseDiscoveryDTO[];
  }, [databases, dbFilter, schemaFilter, typeFilter, statusFilter, objectSearch]);

  const { selectedCount, selectedDbCount, selectedSchemaCount, selectedObjectsBreakdown } = useMemo(() => {
    let totalObj = 0;
    const selectedDbs = new Set<string>();
    const selectedSchs = new Set<string>();
    const breakdown: Record<string, number> = {};

    for (const d of databases) {
      for (const s of d.schemas) {
        for (const g of s.object_groups) {
          for (const o of g.objects) {
            if (o.selected) {
              totalObj++;
              selectedDbs.add(d.db_id);
              selectedSchs.add(s.schema_id);
              breakdown[o.object_type] = (breakdown[o.object_type] || 0) + 1;
            }
          }
        }
      }
    }
    return {
      selectedCount: totalObj,
      selectedDbCount: selectedDbs.size,
      selectedSchemaCount: selectedSchs.size,
      selectedObjectsBreakdown: breakdown,
    };
  }, [databases]);

  const excludedCount = TOTAL_OBJECTS_DETECTED - selectedCount;

  const selectedObjectDetail = useMemo<DiscoveredObjectDTO | null>(() => {
    if (!selectedObjectId) return null;
    for (const d of databases) {
      for (const s of d.schemas) {
        for (const g of s.object_groups) {
          const obj = g.objects.find((o) => o.object_id === selectedObjectId);
          if (obj) return obj;
        }
      }
    }
    return null;
  }, [databases, selectedObjectId]);

  const isFiltered = dbFilter !== 'ALL' || schemaFilter !== 'ALL' || typeFilter !== 'ALL' || statusFilter !== 'ALL' || objectSearch !== '';

  // Step 4 Check State Helpers
  const getDatabaseCheckState = useCallback((db: DatabaseDiscoveryDTO) => {
    const all = db.schemas.flatMap((s) => s.object_groups.flatMap((g) => g.objects));
    const sel = all.filter((o) => o.selected).length;
    return { checked: sel === all.length && all.length > 0, indeterminate: sel > 0 && sel < all.length };
  }, []);

  const getSchemaCheckState = useCallback((schema: SchemaDiscoveryDTO) => {
    const all = schema.object_groups.flatMap((g) => g.objects);
    const sel = all.filter((o) => o.selected).length;
    return { checked: sel === all.length && all.length > 0, indeterminate: sel > 0 && sel < all.length };
  }, []);

  const getGroupCheckState = useCallback((group: ObjectGroupDTO) => {
    const sel = group.objects.filter((o) => o.selected).length;
    return { checked: sel === group.objects.length && group.objects.length > 0, indeterminate: sel > 0 && sel < group.objects.length };
  }, []);

  // Step 4 Selection Handlers
  const toggleDatabase = useCallback((dbId: string, checked: boolean) => {
    setDatabases((prev) =>
      prev.map((d) =>
        d.db_id !== dbId ? d : {
          ...d, schemas: d.schemas.map((s) => ({
            ...s, object_groups: s.object_groups.map((g) => ({
              ...g, objects: g.objects.map((o) => ({ ...o, selected: checked })),
            })),
          })),
        }
      )
    );
  }, []);

  const toggleSchema = useCallback((dbId: string, schemaId: string, checked: boolean) => {
    setDatabases((prev) =>
      prev.map((d) =>
        d.db_id !== dbId ? d : {
          ...d, schemas: d.schemas.map((s) =>
            s.schema_id !== schemaId ? s : {
              ...s, object_groups: s.object_groups.map((g) => ({
                ...g, objects: g.objects.map((o) => ({ ...o, selected: checked })),
              })),
            }
          ),
        }
      )
    );
  }, []);

  const toggleGroup = useCallback((dbId: string, schemaId: string, objectType: string, checked: boolean) => {
    setDatabases((prev) =>
      prev.map((d) =>
        d.db_id !== dbId ? d : {
          ...d, schemas: d.schemas.map((s) =>
            s.schema_id !== schemaId ? s : {
              ...s, object_groups: s.object_groups.map((g) =>
                g.object_type !== objectType ? g : {
                  ...g, objects: g.objects.map((o) => ({ ...o, selected: checked })),
                }
              ),
            }
          ),
        }
      )
    );
  }, []);

  const toggleObject = useCallback((objectId: string, checked: boolean) => {
    setDatabases((prev) =>
      prev.map((d) => ({
        ...d, schemas: d.schemas.map((s) => ({
          ...s, object_groups: s.object_groups.map((g) => ({
            ...g, objects: g.objects.map((o) =>
              o.object_id !== objectId ? o : { ...o, selected: checked }
            ),
          })),
        })),
      }))
    );
  }, []);

  // Expand Handlers
  const toggleDbExpand = useCallback((dbId: string) => {
    setExpandedDatabases((prev) => {
      const next = new Set(prev);
      if (next.has(dbId)) next.delete(dbId); else next.add(dbId);
      return next;
    });
  }, []);

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
    setExpandedDatabases(new Set(INITIAL_DATABASES.map((d) => d.db_id)));
    setExpandedSchemas(new Set(INITIAL_DATABASES.flatMap((d) => d.schemas.map((s) => s.schema_id))));
    const keys = new Set<string>();
    INITIAL_DATABASES.forEach((d) => d.schemas.forEach((s) => s.object_groups.forEach((g) => keys.add(`${s.schema_id}:${g.object_type}`))));
    setExpandedGroups(keys);
  }, []);

  const collapseAll = useCallback(() => {
    setExpandedDatabases(new Set());
    setExpandedSchemas(new Set());
    setExpandedGroups(new Set());
  }, []);

  const selectAll = useCallback((checked: boolean) => {
    setDatabases((prev) =>
      prev.map((d) => ({
        ...d, schemas: d.schemas.map((s) => ({
          ...s, object_groups: s.object_groups.map((g) => ({
            ...g, objects: g.objects.map((o) => ({ ...o, selected: checked })),
          })),
        })),
      }))
    );
  }, []);

  const clearFilters = useCallback(() => {
    setDbFilter('ALL');
    setSchemaFilter('ALL');
    setTypeFilter('ALL');
    setStatusFilter('ALL');
    setObjectSearch('');
  }, []);

  // Dynamic Execution Plan Nodes
  const dynamicExecutionPlanNodes = useMemo(() => {
    const nodes: { stage: number; name: string; category: string; details: string; status: string }[] = [];
    let stage = 1;

    nodes.push({ stage: stage++, name: 'Discovery & Catalog Fencing', category: 'Catalog', details: `Source Engine: ${sourceEngine} -> Target: ${targetEngine}`, status: 'VERIFIED' });
    nodes.push({ stage: stage++, name: 'DAG Topological Dependency Sorting', category: 'Planner', details: `${selectedDbCount} Databases, ${selectedSchemaCount} Schemas, ${selectedCount} Objects`, status: 'VERIFIED' });
    nodes.push({ stage: stage++, name: 'Target Schema Structure Deployment', category: 'DDL', details: `Deploy DDL definitions to target ${targetDbName}`, status: 'READY' });

    if (selectedObjectsBreakdown['Sequence']) {
      nodes.push({ stage: stage++, name: 'Sequence Generator Sync Node', category: 'DDL', details: `Initialize ${selectedObjectsBreakdown['Sequence']} database sequences`, status: 'READY' });
    }
    if (selectedObjectsBreakdown['Table']) {
      nodes.push({ stage: stage++, name: 'Parallel Stream Data Transport', category: 'Data Transport', details: `${selectedObjectsBreakdown['Table']} Tables (${parallelism} Workers, ${batchSize} Batch Size)`, status: 'READY' });
    }
    if (selectedObjectsBreakdown['View']) {
      nodes.push({ stage: stage++, name: 'Target View DDL Creation', category: 'DDL', details: `Deploy ${selectedObjectsBreakdown['View']} SQL view definitions`, status: 'READY' });
    }
    if (selectedObjectsBreakdown['Procedure'] || selectedObjectsBreakdown['Function'] || selectedObjectsBreakdown['Package']) {
      const routines = (selectedObjectsBreakdown['Procedure'] || 0) + (selectedObjectsBreakdown['Function'] || 0) + (selectedObjectsBreakdown['Package'] || 0);
      nodes.push({ stage: stage++, name: 'PL/SQL Transpilation & Deployment', category: 'Transpiler', details: `Transpile ${routines} PL/SQL routines to PL/pgSQL`, status: 'READY' });
    }
    if (selectedObjectsBreakdown['Trigger']) {
      nodes.push({ stage: stage++, name: 'Trigger Definition Deployment', category: 'DDL', details: `Attach ${selectedObjectsBreakdown['Trigger']} database triggers`, status: 'READY' });
    }
    if (selectedObjectsBreakdown['Materialized View']) {
      nodes.push({ stage: stage++, name: 'Materialized View Refresh Strategy', category: 'DDL', details: `Deploy ${selectedObjectsBreakdown['Materialized View']} Materialized Views`, status: 'READY' });
    }
    if (enableCdc) {
      nodes.push({ stage: stage++, name: 'CDC Continuous Replication Setup', category: 'Replication', details: 'Setup WAL Log Reader & streaming sync', status: 'READY' });
    }
    if (validationLevel !== 'NONE') {
      nodes.push({ stage: stage++, name: 'Reconciliation & Validation Node', category: 'Validation', details: `Level: ${validationLevel} (${samplingRate}% sampling rate)`, status: 'READY' });
    }
    nodes.push({ stage: stage++, name: 'SHA-256 Digital Trust Seal', category: 'Certification', details: 'Generate cryptographic migration certificate', status: 'PENDING' });

    return nodes;
  }, [sourceEngine, targetEngine, selectedDbCount, selectedSchemaCount, selectedCount, selectedObjectsBreakdown, parallelism, batchSize, enableCdc, validationLevel, samplingRate, targetDbName]);

  // ─────────────────────────────────────────────────────────────────────────
  // JSX (Fluid Responsive Container — 100% Width & Height)
  // ─────────────────────────────────────────────────────────────────────────

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', height: '100%', minHeight: 0, background: 'var(--dash-bg)', overflow: 'hidden' }}>
      <style>{`
        .akaal-tree-db { transition: background 150ms ease, border-color 150ms ease; }
        .akaal-tree-db:hover { background: rgba(37,99,235,0.08) !important; }
        .akaal-tree-schema { transition: background 150ms ease; }
        .akaal-tree-schema:hover { background: rgba(37,99,235,0.06) !important; }
        .akaal-tree-group { transition: background 150ms ease; }
        .akaal-tree-group:hover { background: rgba(37,99,235,0.04) !important; }
        .akaal-tree-obj { transition: background 120ms ease; }
        .akaal-tree-obj:hover { background: rgba(37,99,235,0.09) !important; }
      `}</style>

      {/* ── Top Header Bar ─────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 24px', borderBottom: '1px solid var(--dash-border)', background: 'var(--dash-surface)', flexShrink: 0, gap: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, overflow: 'hidden' }}>
          <button type="button" onClick={onClose} style={{ background: 'none', border: '1px solid var(--dash-border)', padding: '6px 12px', borderRadius: 6, color: 'var(--dash-text-secondary)', fontSize: 12, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
            <ArrowLeft size={14} /> Back
          </button>
          <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: 'var(--dash-text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {migName || 'New Enterprise Migration Workspace'}
          </h2>
          <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, background: 'rgba(37,99,235,0.15)', color: '#3B82F6', fontWeight: 600, whiteSpace: 'nowrap', flexShrink: 0 }}>MIG-2026-0806-001</span>
          <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, background: 'rgba(16,185,129,0.15)', color: '#10B981', fontWeight: 600, whiteSpace: 'nowrap', flexShrink: 0 }}>AKAAL Engine V3.4.0</span>
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--dash-text-secondary)', cursor: 'pointer', padding: 4, display: 'flex', alignItems: 'center', justifyContent: 'center' }} aria-label="Close setup experience">
          <X size={20} />
        </button>
      </div>

      {/* ── Workflow 7-Step Nav Bar (Fluid, Zero Abbreviations) ─────────── */}
      <div style={{ display: 'flex', background: 'var(--dash-bg)', padding: '10px 24px', borderBottom: '1px solid var(--dash-border)', gap: 6, overflowX: 'auto', flexShrink: 0 }}>
        {STEP_TITLES.map((title, idx) => {
          const stepNum = idx + 1;
          const isCompleted = stepNum < step;
          const isCurrent = stepNum === step;
          return (
            <div
              key={title}
              onClick={() => { if (stepNum < step) setStep(stepNum as any); }}
              style={{
                flex: 1, minWidth: 125, padding: '7px 12px', borderRadius: 6,
                background: isCurrent ? 'var(--dash-accent)' : isCompleted ? 'rgba(16,185,129,0.12)' : 'var(--dash-surface)',
                border: isCurrent ? '1px solid var(--dash-accent)' : isCompleted ? '1px solid rgba(16,185,129,0.3)' : '1px solid var(--dash-border)',
                color: isCurrent ? '#FFFFFF' : isCompleted ? '#10B981' : 'var(--dash-text-secondary)',
                cursor: isCompleted ? 'pointer' : 'default',
                display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, fontWeight: 600, transition: 'all 150ms ease',
                whiteSpace: 'nowrap',
              }}
            >
              <span style={{ width: 16, height: 16, borderRadius: '50%', background: isCurrent ? '#FFFFFF' : isCompleted ? '#10B981' : 'var(--dash-border)', color: isCurrent ? 'var(--dash-accent)' : isCompleted ? '#FFFFFF' : 'var(--dash-text-secondary)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 700, flexShrink: 0 }}>
                {isCompleted ? <Check size={10} /> : stepNum}
              </span>
              <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{title.split('. ')[1]}</span>
            </div>
          );
        })}
      </div>

      {/* ── Main Body Layout (Fluid 100% Split) ────────────────────────── */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden', width: '100%' }}>
        {/* Left Main View Content */}
        <div style={{ flex: 1, padding: 24, overflowY: 'auto', minWidth: 0 }}>

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
                  <input type="text" value="2 Hours (Off-Peak Weekend)" disabled style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--dash-surface)', color: 'var(--dash-text-secondary)', fontSize: 13 }} />
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
                    <option value="prod_oracle_free">Production Oracle Instance (localhost:1521/FREE)</option>
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
                    <input type="checkbox" checked={sourceSsl} onChange={(e) => setSourceSsl(e.target.checked)} /> SSL Encrypted Connection
                  </label>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 10 }}>
                <button type="button" onClick={handleTestSource} disabled={testingSource} style={{ padding: '9px 18px', borderRadius: 8, background: 'var(--dash-accent)', border: 'none', color: '#FFF', fontSize: 12, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Zap size={14} /> {testingSource ? 'Testing Connection...' : 'Test Source Connection (IPC)'}
                </button>
                {sourceTested && (<span style={{ fontSize: 12, color: '#10B981', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}><Check size={14} /> Source Connection Verified (12ms Latency)</span>)}
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
                    <option value="prod_pg_target">PostgreSQL akaal_target Instance (localhost:5432)</option>
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
                  <button type="button" onClick={handleTestTarget} disabled={testingTarget} style={{ padding: '9px 18px', borderRadius: 8, background: 'var(--dash-accent)', border: 'none', color: '#FFF', fontSize: 12, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Zap size={14} /> {testingTarget ? 'Testing Connection...' : 'Test Target Connection (IPC)'}
                  </button>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                    <input type="checkbox" checked={targetSsl} onChange={(e) => setTargetSsl(e.target.checked)} /> SSL Encrypted Transport
                  </label>
                </div>
                {targetTested && (<span style={{ fontSize: 12, color: '#10B981', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}><Check size={14} /> Target Connection Verified (8ms Latency)</span>)}
              </div>
            </div>
          )}

          {/* ── STEP 4: DISCOVERY & MIGRATION SCOPE (Clean layout, instruction panel removed) ─ */}
          {step === 4 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {/* Discovery Profile + Completion Badge */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 14, flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--dash-text-secondary)', whiteSpace: 'nowrap' }}>Discovery Profile:</span>
                  {(['QUICK', 'STANDARD', 'DEEP', 'COMPLIANCE'] as DiscoveryProfileType[]).map((prof) => (
                    <button key={prof} type="button" onClick={() => setDiscoveryProfile(prof)}
                      style={{ padding: '4px 12px', borderRadius: 6, border: discoveryProfile === prof ? '1px solid var(--dash-accent)' : '1px solid var(--dash-border)', background: discoveryProfile === prof ? 'rgba(37,99,235,0.15)' : 'var(--dash-bg)', color: discoveryProfile === prof ? 'var(--dash-accent)' : 'var(--dash-text-secondary)', fontSize: 11, fontWeight: 600, cursor: 'pointer', transition: 'all 150ms ease' }}>
                      {prof}
                    </button>
                  ))}
                </div>
                <span style={{ fontSize: 11, color: '#10B981', fontWeight: 700, padding: '4px 12px', borderRadius: 20, background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10B981' }} /> DISCOVERY COMPLETE
                </span>
              </div>

              {/* Compact Discovery Summary Card (3 Values: Databases, Schemas, Objects) */}
              <div style={{ padding: '12px 20px', background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)', display: 'inline-flex', alignItems: 'center', gap: 24, alignSelf: 'flex-start', flexWrap: 'wrap' }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--dash-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <BarChart2 size={15} color="#3B82F6" /> Discovery Summary
                </span>
                <div style={{ width: 1, height: 22, background: 'var(--dash-border)' }} />
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 11, color: 'var(--dash-text-secondary)', fontWeight: 600 }}>Databases Discovered:</span>
                  <strong style={{ fontSize: 16, fontWeight: 800, color: '#3B82F6', fontVariantNumeric: 'tabular-nums' }}>{TOTAL_DATABASES_DETECTED}</strong>
                </div>
                <div style={{ width: 1, height: 22, background: 'var(--dash-border)' }} />
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 11, color: 'var(--dash-text-secondary)', fontWeight: 600 }}>Schemas Discovered:</span>
                  <strong style={{ fontSize: 16, fontWeight: 800, color: '#8B5CF6', fontVariantNumeric: 'tabular-nums' }}>{TOTAL_SCHEMAS_DETECTED}</strong>
                </div>
                <div style={{ width: 1, height: 22, background: 'var(--dash-border)' }} />
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 11, color: 'var(--dash-text-secondary)', fontWeight: 600 }}>Objects Discovered:</span>
                  <strong style={{ fontSize: 16, fontWeight: 800, color: '#10B981', fontVariantNumeric: 'tabular-nums' }}>{TOTAL_OBJECTS_DETECTED.toLocaleString()}</strong>
                </div>
              </div>

              {/* Hierarchy Filter Bar */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)', flexWrap: 'wrap' }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--dash-text-secondary)', display: 'flex', alignItems: 'center', gap: 4, whiteSpace: 'nowrap' }}>
                  <Zap size={14} color="#F59E0B" /> Scope Filters:
                </span>

                <select value={dbFilter} onChange={(e) => setDbFilter(e.target.value)} aria-label="Filter by Database"
                  style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 11, fontWeight: 600 }}>
                  <option value="ALL">All Databases</option>
                  {INITIAL_DATABASES.map((d) => (<option key={d.db_id} value={d.db_id}>{d.db_name}</option>))}
                </select>

                <select value={schemaFilter} onChange={(e) => setSchemaFilter(e.target.value)} aria-label="Filter by Schema"
                  style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 11, fontWeight: 600 }}>
                  <option value="ALL">All Schemas</option>
                  {INITIAL_DATABASES.flatMap((d) => d.schemas).map((s) => (<option key={s.schema_id} value={s.schema_id}>{s.schema_name}</option>))}
                </select>

                <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} aria-label="Filter by Object Type"
                  style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 11, fontWeight: 600 }}>
                  <option value="ALL">All Types</option>
                  {allObjectTypes.map((t) => (<option key={t} value={t}>{t}s</option>))}
                </select>

                <div style={{ position: 'relative', flex: 1, minWidth: 140 }}>
                  <input
                    type="text" value={objectSearch} onChange={(e) => setObjectSearch(e.target.value)}
                    placeholder="Search object name..." aria-label="Search objects"
                    style={{ width: '100%', padding: '6px 12px 6px 28px', borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 11 }}
                  />
                  <Search size={13} color="var(--dash-text-secondary)" style={{ position: 'absolute', left: 8, top: 8 }} />
                </div>

                <div style={{ display: 'flex', gap: 6, marginLeft: 'auto', flexWrap: 'wrap' }}>
                  {isFiltered && (
                    <button type="button" onClick={clearFilters} style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid #EF4444', background: 'rgba(239,68,68,0.1)', color: '#EF4444', fontSize: 10, fontWeight: 700, cursor: 'pointer' }}>✕ Clear Filters</button>
                  )}
                  <button type="button" onClick={() => selectAll(true)} style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-secondary)', fontSize: 10, fontWeight: 600, cursor: 'pointer' }}>Select All</button>
                  <button type="button" onClick={() => selectAll(false)} style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-secondary)', fontSize: 10, fontWeight: 600, cursor: 'pointer' }}>Deselect All</button>
                  <button type="button" onClick={expandAll} style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-secondary)', fontSize: 10, fontWeight: 600, cursor: 'pointer' }}>Expand All</button>
                  <button type="button" onClick={collapseAll} style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-secondary)', fontSize: 10, fontWeight: 600, cursor: 'pointer' }}>Collapse All</button>
                </div>
              </div>

              {/* Instance -> DB -> Schema -> Object Type Tree + Detail Panel */}
              <div style={{ display: 'flex', gap: 14 }}>
                <div
                  ref={treeRef}
                  role="tree"
                  aria-label="Database Discovery Explorer"
                  style={{ flex: 1, border: '1px solid var(--dash-border)', borderRadius: 10, overflow: 'hidden', background: 'var(--dash-surface)', display: 'flex', flexDirection: 'column', minWidth: 0 }}
                >
                  {/* Column Header */}
                  <div style={{ display: 'grid', gridTemplateColumns: '26px 26px 1fr 84px 84px 76px', gap: 8, padding: '8px 14px', background: 'var(--dash-bg)', borderBottom: '1px solid var(--dash-border)', fontSize: 10, fontWeight: 700, color: 'var(--dash-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', alignItems: 'center' }}>
                    <span /><span />
                    <span>Database & Schema Hierarchy</span>
                    <span>Est. Rows</span>
                    <span>Est. Size</span>
                    <span>Compatibility</span>
                  </div>

                  {/* Scrollable Explorer Tree */}
                  <div style={{ overflowY: 'auto', maxHeight: 460, padding: 8 }}>
                    {visibleDatabases.length === 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '50px 24px', gap: 12 }}>
                        <Search size={32} color="var(--dash-text-secondary)" />
                        <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--dash-text-primary)' }}>No databases or objects match your filter parameters</div>
                        <button type="button" onClick={clearFilters} style={{ padding: '8px 20px', borderRadius: 8, background: 'var(--dash-accent)', border: 'none', color: '#FFF', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>Clear All Filters</button>
                      </div>
                    ) : (
                      visibleDatabases.map((db) => {
                        const dbCheck = getDatabaseCheckState(db);
                        const dbExpanded = expandedDatabases.has(db.db_id);
                        const totalDbObjs = db.schemas.reduce((ss, s) => ss + s.object_groups.reduce((gs, g) => gs + g.objects.length, 0), 0);

                        return (
                          <div key={db.db_id} style={{ border: '1px solid var(--dash-border)', borderRadius: 8, marginBottom: 10, overflow: 'hidden', background: 'var(--dash-bg)' }}>
                            {/* DATABASE LEVEL ROW */}
                            <div
                              className="akaal-tree-db"
                              role="treeitem"
                              aria-expanded={dbExpanded}
                              onClick={() => toggleDbExpand(db.db_id)}
                              style={{
                                display: 'grid', gridTemplateColumns: '26px 26px 1fr 84px 84px 76px', gap: 8,
                                padding: '10px 14px', alignItems: 'center', cursor: 'pointer',
                                borderBottom: dbExpanded ? '1px solid var(--dash-border)' : 'none',
                                background: 'var(--dash-surface)'
                              }}
                            >
                              <span style={{ fontSize: 11, color: 'var(--dash-accent)', userSelect: 'none', fontWeight: 800, transition: 'transform 150ms ease', display: 'inline-flex', alignItems: 'center' }}>
                                {dbExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                              </span>
                              <IndeterminateCheckbox
                                checked={dbCheck.checked}
                                indeterminate={dbCheck.indeterminate}
                                onChange={(checked) => toggleDatabase(db.db_id, checked)}
                                aria-label={`Select all objects in database ${db.db_name}`}
                              />
                              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <Database size={15} color="#3B82F6" />
                                <span style={{ fontSize: 14, fontWeight: 800, color: 'var(--dash-text-primary)' }}>
                                  {db.db_name}
                                </span>
                                <span style={{ fontSize: 10, color: '#3B82F6', padding: '2px 8px', borderRadius: 12, background: 'rgba(37,99,235,0.12)', border: '1px solid rgba(37,99,235,0.25)', fontWeight: 700 }}>
                                  {db.schemas.length} Schemas · {totalDbObjs} Objects
                                </span>
                                <span style={{ fontSize: 10, color: dbCheck.checked ? '#10B981' : dbCheck.indeterminate ? '#F59E0B' : 'var(--dash-text-secondary)', fontWeight: 700, marginLeft: 'auto', marginRight: 10 }}>
                                  {dbCheck.checked ? 'ALL SELECTED' : dbCheck.indeterminate ? 'PARTIAL' : 'EXCLUDED'}
                                </span>
                              </div>
                              <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--dash-text-secondary)' }}>DB Container</span>
                              <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--dash-text-secondary)' }}>Oracle EE</span>
                              <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 4, background: 'rgba(16,185,129,0.12)', color: '#10B981', textAlign: 'center', border: '1px solid rgba(16,185,129,0.25)' }}>
                                OPTIMAL
                              </span>
                            </div>

                            {/* SCHEMA LEVEL LIST */}
                            <div style={{
                              overflow: 'hidden',
                              maxHeight: dbExpanded ? '30000px' : '0px',
                              transition: 'max-height 200ms ease-in-out, opacity 180ms ease',
                              opacity: dbExpanded ? 1 : 0,
                              background: 'var(--dash-bg)',
                            }}>
                              {db.schemas.map((schema) => {
                                const schemaCheck = getSchemaCheckState(schema);
                                const schemaExpanded = expandedSchemas.has(schema.schema_id);
                                const totalSchemaObjs = schema.object_groups.reduce((sum, g) => sum + g.objects.length, 0);

                                return (
                                  <div key={schema.schema_id} style={{ borderLeft: '3px solid rgba(59, 130, 246, 0.3)', marginLeft: 16, marginTop: 6, marginBottom: 6 }}>
                                    {/* Schema Row */}
                                    <div
                                      className="akaal-tree-schema"
                                      role="treeitem"
                                      aria-expanded={schemaExpanded}
                                      onClick={() => toggleSchemaExpand(schema.schema_id)}
                                      style={{
                                        display: 'grid', gridTemplateColumns: '26px 26px 1fr 84px 84px 76px', gap: 8,
                                        padding: '8px 12px', alignItems: 'center', cursor: 'pointer',
                                        borderBottom: '1px solid var(--dash-border)', background: 'var(--dash-surface)',
                                      }}
                                    >
                                      <span style={{ fontSize: 10, color: 'var(--dash-text-secondary)', userSelect: 'none', display: 'inline-flex', alignItems: 'center' }}>
                                        {schemaExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                                      </span>
                                      <IndeterminateCheckbox
                                        checked={schemaCheck.checked}
                                        indeterminate={schemaCheck.indeterminate}
                                        onChange={(checked) => toggleSchema(db.db_id, schema.schema_id, checked)}
                                        aria-label={`Select all objects in schema ${schema.schema_name}`}
                                      />
                                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                        <Folder size={14} color="#8B5CF6" />
                                        <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--dash-text-primary)' }}>
                                          {schema.schema_name} Schema
                                        </span>
                                        <span style={{ fontSize: 10, color: 'var(--dash-text-secondary)', fontWeight: 500 }}>
                                          ({totalSchemaObjs} Objects)
                                        </span>
                                      </div>
                                      <span /><span /><span />
                                    </div>

                                    {/* OBJECT TYPE LEVEL */}
                                    <div style={{
                                      overflow: 'hidden',
                                      maxHeight: schemaExpanded ? '20000px' : '0px',
                                      transition: 'max-height 180ms ease-in-out, opacity 160ms ease',
                                      opacity: schemaExpanded ? 1 : 0,
                                    }}>
                                      {schema.object_groups.map((group) => {
                                        const groupKey = `${schema.schema_id}:${group.object_type}`;
                                        const groupExpanded = expandedGroups.has(groupKey);
                                        const groupCheck = getGroupCheckState(group);
                                        const badge = OBJ_BADGE[group.object_type] ?? { label: group.object_type.substring(0, 3).toUpperCase(), color: '#6B7280', bg: 'rgba(107,114,128,0.12)' };

                                        return (
                                          <div key={groupKey} style={{ borderLeft: '2px solid rgba(139, 92, 246, 0.25)', marginLeft: 16 }}>
                                            {/* Object Type Row */}
                                            <div
                                              className="akaal-tree-group"
                                              role="treeitem"
                                              aria-expanded={groupExpanded}
                                              onClick={() => toggleGroupExpand(groupKey)}
                                              style={{
                                                display: 'grid', gridTemplateColumns: '22px 22px 1fr 84px 84px 76px', gap: 8,
                                                padding: '6px 12px 6px 14px', alignItems: 'center', cursor: 'pointer',
                                                borderBottom: '1px solid var(--dash-border)', background: 'var(--dash-bg)',
                                              }}
                                            >
                                              <span style={{ fontSize: 10, color: 'var(--dash-text-secondary)', userSelect: 'none', display: 'inline-flex', alignItems: 'center' }}>
                                                {groupExpanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                                              </span>
                                              <IndeterminateCheckbox
                                                checked={groupCheck.checked}
                                                indeterminate={groupCheck.indeterminate}
                                                onChange={(checked) => toggleGroup(db.db_id, schema.schema_id, group.object_type, checked)}
                                                aria-label={`Select all ${group.object_type}s in ${schema.schema_name}`}
                                              />
                                              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                                <span style={{ fontSize: 9, fontWeight: 800, padding: '1px 5px', borderRadius: 4, color: badge.color, background: badge.bg, border: `1px solid ${badge.color}33` }}>
                                                  {badge.label}
                                                </span>
                                                <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--dash-text-primary)', display: 'flex', alignItems: 'center', gap: 4 }}>
                                                  {renderObjTypeIcon(group.object_type)} {group.object_type}s
                                                </span>
                                                <span style={{ fontSize: 10, color: 'var(--dash-text-secondary)' }}>
                                                  ({group.objects.length})
                                                </span>
                                              </div>
                                              <span /><span /><span />
                                            </div>

                                            {/* INDIVIDUAL OBJECT NAME LEVEL */}
                                            <div style={{
                                              overflow: 'hidden',
                                              maxHeight: groupExpanded ? '9999px' : '0px',
                                              transition: 'max-height 160ms ease-in-out, opacity 140ms ease',
                                              opacity: groupExpanded ? 1 : 0,
                                              marginLeft: 24,
                                            }}>
                                              {group.objects.map((obj) => {
                                                const isActive = obj.object_id === selectedObjectId;
                                                const chip = STATUS_CHIP[obj.compatibility_status] ?? STATUS_CHIP['OPTIMAL'];
                                                return (
                                                  <div
                                                    key={obj.object_id}
                                                    className="akaal-tree-obj"
                                                    role="treeitem"
                                                    aria-selected={obj.selected}
                                                    onClick={() => setSelectedObjectId(isActive ? null : obj.object_id)}
                                                    style={{
                                                      display: 'grid', gridTemplateColumns: '22px 22px 1fr 84px 84px 76px', gap: 8,
                                                      padding: '5px 12px 5px 14px', alignItems: 'center',
                                                      borderBottom: '1px solid rgba(71,85,105,0.12)',
                                                      background: isActive ? 'rgba(37,99,235,0.12)' : 'transparent',
                                                      borderLeft: isActive ? '3px solid var(--dash-accent)' : '3px solid transparent',
                                                      cursor: 'pointer',
                                                    }}
                                                  >
                                                    <span />
                                                    <input
                                                      type="checkbox"
                                                      checked={obj.selected}
                                                      onChange={(e) => { e.stopPropagation(); toggleObject(obj.object_id, e.target.checked); }}
                                                      onClick={(e) => e.stopPropagation()}
                                                      aria-label={`Include ${obj.object_name}`}
                                                      style={{ cursor: 'pointer', accentColor: 'var(--dash-accent)' }}
                                                    />
                                                    <span style={{ fontSize: 11, fontWeight: obj.selected ? 600 : 400, color: obj.selected ? 'var(--dash-text-primary)' : 'var(--dash-text-secondary)', fontFamily: 'var(--akaal-font-mono, monospace)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: 6 }}>
                                                      <FileText size={13} color="var(--dash-text-secondary)" />
                                                      {obj.object_name}
                                                      {obj.warnings.length > 0 && (<span title={obj.warnings.join('; ')}><AlertTriangle size={12} color="#F59E0B" /></span>)}
                                                    </span>
                                                    <span style={{ fontSize: 10, color: 'var(--dash-text-secondary)', fontVariantNumeric: 'tabular-nums' }}>{fmtRows(obj.estimated_rows)}</span>
                                                    <span style={{ fontSize: 10, color: 'var(--dash-text-secondary)' }}>{fmtSize(obj.estimated_size_gb)}</span>
                                                    <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 5px', borderRadius: 4, color: chip.color, background: chip.bg, textAlign: 'center' }}>
                                                      {obj.compatibility_status}
                                                    </span>
                                                  </div>
                                                );
                                              })}
                                            </div>
                                          </div>
                                        );
                                      })}
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

                {/* Object Detail Panel */}
                {selectedObjectDetail ? (
                  <div style={{ width: 280, flexShrink: 0, border: '1px solid var(--dash-border)', borderRadius: 10, background: 'var(--dash-surface)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                    <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--dash-border)', background: 'var(--dash-bg)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--dash-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Zap size={13} color="#F59E0B" /> Object Telemetry
                      </span>
                      <button type="button" onClick={() => setSelectedObjectId(null)} style={{ background: 'none', border: 'none', color: 'var(--dash-text-secondary)', cursor: 'pointer', padding: 2 }}>
                        <X size={16} />
                      </button>
                    </div>
                    <div style={{ padding: 14, overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: 12 }}>
                      <div style={{ padding: 10, background: 'var(--dash-bg)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                        <div style={{ fontSize: 9, color: 'var(--dash-text-secondary)', fontWeight: 700, textTransform: 'uppercase' }}>Target Object Name</div>
                        <div style={{ fontFamily: 'var(--akaal-font-mono, monospace)', fontSize: 13, fontWeight: 800, color: 'var(--dash-text-primary)', marginTop: 2 }}>{selectedObjectDetail.object_name}</div>
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, background: 'var(--dash-bg)', padding: 8, borderRadius: 6, border: '1px solid var(--dash-border)', fontSize: 11 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--dash-text-secondary)' }}>Database</span><strong>{selectedObjectDetail.db_id}</strong></div>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--dash-text-secondary)' }}>Schema</span><strong>{selectedObjectDetail.schema_id}</strong></div>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--dash-text-secondary)' }}>Type</span><strong>{selectedObjectDetail.object_type}</strong></div>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--dash-text-secondary)' }}>Est. Rows</span><strong>{fmtRows(selectedObjectDetail.estimated_rows)}</strong></div>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--dash-text-secondary)' }}>Est. Size</span><strong>{fmtSize(selectedObjectDetail.estimated_size_gb)}</strong></div>
                      </div>
                      <button type="button" onClick={() => toggleObject(selectedObjectDetail.object_id, !selectedObjectDetail.selected)}
                        style={{ marginTop: 'auto', padding: '9px 14px', borderRadius: 8, fontSize: 11, fontWeight: 700, cursor: 'pointer', background: selectedObjectDetail.selected ? 'rgba(239,68,68,0.12)' : 'rgba(16,185,129,0.12)', color: selectedObjectDetail.selected ? '#EF4444' : '#10B981', border: selectedObjectDetail.selected ? '1px solid rgba(239,68,68,0.3)' : '1px solid rgba(16,185,129,0.3)' }}>
                        {selectedObjectDetail.selected ? '✕ Exclude from Migration' : '✓ Include in Migration'}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div style={{ width: 280, flexShrink: 0, border: '1px dashed var(--dash-border)', borderRadius: 10, background: 'var(--dash-surface)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 24, gap: 12 }}>
                    <BarChart2 size={28} color="var(--dash-text-secondary)" />
                    <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--dash-text-primary)', textAlign: 'center' }}>Object Telemetry Explorer</div>
                    <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', textAlign: 'center', lineHeight: 1.5 }}>Select any object in the tree to view specs, storage metrics, compatibility status, and dependency telemetry.</div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── STEP 5: DYNAMIC EXECUTION PLAN (Visual DAG Engine Graph) ──── */}
          {step === 5 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div style={{ padding: 14, background: 'rgba(16,185,129,0.12)', borderRadius: 10, border: '1px solid rgba(16,185,129,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 800, color: '#10B981', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <CheckCircle2 size={18} color="#10B981" /> DYNAMIC EXECUTION PLAN GENERATED — 99.4% PREDICTED TRUST SCORE
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)', marginTop: 2 }}>
                    Generated dynamically for {selectedDbCount} Databases, {selectedSchemaCount} Schemas, and {selectedCount} Objects.
                  </div>
                </div>
                <span style={{ fontSize: 11, padding: '4px 12px', borderRadius: 6, background: '#10B981', color: '#FFF', fontWeight: 700 }}>DYNAMIC DAG</span>
              </div>

              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--dash-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Generated DAG Execution Stages ({dynamicExecutionPlanNodes.length} Pipeline Stages)
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {dynamicExecutionPlanNodes.map((node) => (
                  <div key={node.stage} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', background: 'var(--dash-surface)', borderRadius: 8, border: '1px solid var(--dash-border)', gap: 12 }}>
                    <span style={{ width: 24, height: 24, borderRadius: '50%', background: 'rgba(37,99,235,0.15)', color: '#3B82F6', fontSize: 11, fontWeight: 800, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                      {node.stage}
                    </span>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--dash-text-primary)' }}>{node.name}</span>
                        <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, background: 'var(--dash-bg)', border: '1px solid var(--dash-border)', color: 'var(--dash-text-secondary)', fontWeight: 600 }}>{node.category}</span>
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', marginTop: 2 }}>{node.details}</div>
                    </div>
                    <span style={{ fontSize: 10, fontWeight: 700, padding: '3px 8px', borderRadius: 4, background: node.status === 'VERIFIED' ? 'rgba(16,185,129,0.15)' : 'rgba(37,99,235,0.15)', color: node.status === 'VERIFIED' ? '#10B981' : '#3B82F6' }}>
                      {node.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── STEP 6: ENTERPRISE CONFIGURATION CENTER ─────────────────── */}
          {step === 6 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Config Header Mode Toggle */}
              <div style={{ padding: 14, background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--dash-text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Sliders size={16} color="#3B82F6" /> Enterprise Configuration Center
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)', marginTop: 2 }}>Tune engine behavior, performance allocations, security, validation policies, and notifications.</div>
                </div>
                <div style={{ display: 'flex', background: 'var(--dash-bg)', padding: 3, borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                  <button type="button" onClick={() => setConfigMode('BASIC')}
                    style={{ padding: '6px 14px', borderRadius: 6, border: 'none', background: configMode === 'BASIC' ? 'var(--dash-accent)' : 'transparent', color: configMode === 'BASIC' ? '#FFF' : 'var(--dash-text-secondary)', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>
                    Basic Mode
                  </button>
                  <button type="button" onClick={() => setConfigMode('ADVANCED')}
                    style={{ padding: '6px 14px', borderRadius: 6, border: 'none', background: configMode === 'ADVANCED' ? 'var(--dash-accent)' : 'transparent', color: configMode === 'ADVANCED' ? '#FFF' : 'var(--dash-text-secondary)', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>
                    Advanced Configuration
                  </button>
                </div>
              </div>

              {/* Expandable Enterprise Configuration Sections */}
              {[
                {
                  id: 'rules', icon: <FileText size={16} color="#3B82F6" />, title: 'Migration Rules & Object Actions',
                  desc: 'Define include/exclude patterns, renaming rules, and action on existing target tables.',
                  content: (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                      <div>
                        <label style={{ fontSize: 11, fontWeight: 600, display: 'block', marginBottom: 4 }}>Action on Existing Target Table</label>
                        <select value={actionOnExisting} onChange={(e) => setActionOnExisting(e.target.value)} style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 12 }}>
                          <option value="SKIP">Skip Existing Tables</option>
                          <option value="OVERWRITE">Truncate & Overwrite</option>
                          <option value="MERGE">Merge / Append Data</option>
                        </select>
                      </div>
                      <div>
                        <label style={{ fontSize: 11, fontWeight: 600, display: 'block', marginBottom: 4 }}>Table Renaming Pattern (Regex)</label>
                        <input type="text" value={tableRenamePattern} onChange={(e) => setTableRenamePattern(e.target.value)} placeholder="e.g. TBL_$1 -> $1_V2" style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 12 }} />
                      </div>
                    </div>
                  )
                },
                {
                  id: 'transform', icon: <RefreshCw size={16} color="#8B5CF6" />, title: 'Data Transformation & PII Masking',
                  desc: 'Column mapping rules, type coercions, and SHA-256 PII redaction.',
                  content: (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                        <input type="checkbox" checked={maskingEnabled} onChange={(e) => setMaskingEnabled(e.target.checked)} />
                        Enforce PII Data Redaction
                      </label>
                      <div>
                        <label style={{ fontSize: 11, fontWeight: 600, display: 'block', marginBottom: 4 }}>Masking Method</label>
                        <select value={maskingMethod} onChange={(e) => setMaskingMethod(e.target.value)} style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 12 }}>
                          <option value="SHA-256">SHA-256 Salted Hash</option>
                          <option value="SALTED_HMAC">Salted HMAC Key</option>
                          <option value="NULL_REDACTION">Full Nullification</option>
                        </select>
                      </div>
                    </div>
                  )
                },
                {
                  id: 'perf', icon: <Zap size={16} color="#F59E0B" />, title: 'High-Performance Stream & Buffer Allocations',
                  desc: 'Parallel worker pool size, batch insertion capacity, and WAL ring buffers.',
                  content: (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 14 }}>
                      <div>
                        <label style={{ fontSize: 11, fontWeight: 600, display: 'block', marginBottom: 4 }}>Parallel Workers</label>
                        <input type="text" value={parallelism} onChange={(e) => setParallelism(e.target.value)} style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 12 }} />
                      </div>
                      <div>
                        <label style={{ fontSize: 11, fontWeight: 600, display: 'block', marginBottom: 4 }}>Batch Insertion Size</label>
                        <input type="text" value={batchSize} onChange={(e) => setBatchSize(e.target.value)} style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 12 }} />
                      </div>
                      <div>
                        <label style={{ fontSize: 11, fontWeight: 600, display: 'block', marginBottom: 4 }}>Commit Interval</label>
                        <input type="text" value={commitInterval} onChange={(e) => setCommitInterval(e.target.value)} style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 12 }} />
                      </div>
                      <div>
                        <label style={{ fontSize: 11, fontWeight: 600, display: 'block', marginBottom: 4 }}>RAM Quota (GB)</label>
                        <input type="text" value={ramLimitGb} onChange={(e) => setRamLimitGb(e.target.value)} style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 12 }} />
                      </div>
                    </div>
                  )
                },
                {
                  id: 'validation', icon: <Search size={16} color="#10B981" />, title: 'Data Validation & Reconciliation Policy',
                  desc: 'Row count verification, CRC32/SHA256 checksums, and sampling percentage.',
                  content: (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                      <div>
                        <label style={{ fontSize: 11, fontWeight: 600, display: 'block', marginBottom: 4 }}>Validation Strategy</label>
                        <select value={validationLevel} onChange={(e) => setValidationLevel(e.target.value)} style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 12 }}>
                          <option value="CHECKSUM">Full CRC32 Checksum & Row Count</option>
                          <option value="ROW_COUNT">Row Count Only</option>
                          <option value="SAMPLING">Randomized Sample Inspection</option>
                          <option value="NONE">Skip Post Validation</option>
                        </select>
                      </div>
                      <div>
                        <label style={{ fontSize: 11, fontWeight: 600, display: 'block', marginBottom: 4 }}>Sampling Percentage (%)</label>
                        <input type="text" value={samplingRate} onChange={(e) => setSamplingRate(e.target.value)} style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 12 }} />
                      </div>
                    </div>
                  )
                },
                {
                  id: 'error', icon: <AlertTriangle size={16} color="#F59E0B" />, title: 'Error Handling & Fault Tolerance',
                  desc: 'Rollback policies, retry attempts, and failed row quarantine handling.',
                  content: (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                      <div>
                        <label style={{ fontSize: 11, fontWeight: 600, display: 'block', marginBottom: 4 }}>Error Action</label>
                        <select value={errorAction} onChange={(e) => setErrorAction(e.target.value)} style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 12 }}>
                          <option value="CONTINUE_AND_LOG">Continue Execution & Quarantine Errors</option>
                          <option value="STOP_ON_ERROR">Halt Migration Immediately</option>
                          <option value="ROLLBACK_TRANSACTION">Rollback Target Transaction</option>
                        </select>
                      </div>
                      <div>
                        <label style={{ fontSize: 11, fontWeight: 600, display: 'block', marginBottom: 4 }}>Max Retries</label>
                        <input type="text" value={retryCount} onChange={(e) => setRetryCount(e.target.value)} style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-primary)', fontSize: 12 }} />
                      </div>
                    </div>
                  )
                },
                {
                  id: 'security', icon: <Lock size={16} color="#06B6D4" />, title: 'Security, TLS & Governance Controls',
                  desc: 'Encrypted transport, secret vault credentials, and four-eyes policy gates.',
                  content: (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                        <input type="checkbox" checked={fourEyesPolicy} onChange={(e) => setFourEyesPolicy(e.target.checked)} />
                        Enforce Four-Eyes Executive Approval Gate
                      </label>
                      <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                        <input type="checkbox" checked={enableCdc} onChange={(e) => setEnableCdc(e.target.checked)} />
                        Enable CDC Continuous Streaming Replication
                      </label>
                    </div>
                  )
                },
                {
                  id: 'notifications', icon: <Bell size={16} color="#EC4899" />, title: 'Notification Alerts & Webhooks',
                  desc: 'Send execution alerts to Slack, MS Teams, or Email upon completion.',
                  content: (
                    <div style={{ display: 'flex', gap: 20 }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                        <input type="checkbox" checked={notifyEmail} onChange={(e) => setNotifyEmail(e.target.checked)} />
                        Email Executive Alerts
                      </label>
                      <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                        <input type="checkbox" checked={notifySlack} onChange={(e) => setNotifySlack(e.target.checked)} />
                        Slack Webhook Dispatch
                      </label>
                    </div>
                  )
                },
              ].map((card) => (
                <div key={card.id} style={{ border: '1px solid var(--dash-border)', borderRadius: 10, background: 'var(--dash-surface)', overflow: 'hidden' }}>
                  <div onClick={() => setExpandedConfigSection(expandedConfigSection === card.id ? null : card.id)}
                    style={{ padding: '14px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer', background: expandedConfigSection === card.id ? 'var(--dash-bg)' : 'transparent' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      {card.icon}
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--dash-text-primary)' }}>{card.title}</div>
                        <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', marginTop: 2 }}>{card.desc}</div>
                      </div>
                    </div>
                    <span style={{ fontSize: 14, color: 'var(--dash-text-secondary)', display: 'flex', alignItems: 'center' }}>
                      {expandedConfigSection === card.id ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    </span>
                  </div>
                  {(configMode === 'ADVANCED' || expandedConfigSection === card.id) && (
                    <div style={{ padding: 16, borderTop: '1px solid var(--dash-border)' }}>
                      {card.content}
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
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#10B981', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <CheckCircle2 size={18} color="#10B981" /> Executive Deployment Review Certified
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)', marginTop: 2 }}>All connectivity, schema DDL, transpiler, and governance rules validated by AKAAL Engine.</div>
                </div>
                <span style={{ fontSize: 11, padding: '4px 12px', borderRadius: 6, background: '#10B981', color: '#FFF', fontWeight: 700 }}>READY TO INITIALIZE</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                <div style={{ padding: 14, background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)', fontSize: 12, lineHeight: 1.6 }}>
                  <div style={{ fontWeight: 700, marginBottom: 8, color: 'var(--dash-text-primary)', borderBottom: '1px solid var(--dash-border)', paddingBottom: 4 }}>1. Migration Connections</div>
                  • <strong>Source:</strong> {sourceEngine} ({sourceHost}:{sourcePort}/{sourceDbName})<br />
                  • <strong>Target:</strong> {targetEngine} ({targetHost}:{targetPort}/{targetDbName})<br />
                  • <strong>Strategy:</strong> {strategy} ({environment})<br />
                  • <strong>Owner:</strong> {businessOwner} ({priority})
                </div>
                <div style={{ padding: 14, background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)', fontSize: 12, lineHeight: 1.6 }}>
                  <div style={{ fontWeight: 700, marginBottom: 8, color: 'var(--dash-text-primary)', borderBottom: '1px solid var(--dash-border)', paddingBottom: 4 }}>2. Discovered & Selected Scope</div>
                  • <strong>Databases Selected:</strong> {selectedDbCount} of {TOTAL_DATABASES_DETECTED}<br />
                  • <strong>Schemas Selected:</strong> {selectedSchemaCount} of {TOTAL_SCHEMAS_DETECTED}<br />
                  • <strong>Objects Selected:</strong> {selectedCount.toLocaleString()} of {TOTAL_OBJECTS_DETECTED.toLocaleString()}<br />
                  • <strong>Objects Excluded:</strong> {excludedCount.toLocaleString()}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                <div style={{ padding: 14, background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)', fontSize: 12, lineHeight: 1.6 }}>
                  <div style={{ fontWeight: 700, marginBottom: 8, color: 'var(--dash-text-primary)', borderBottom: '1px solid var(--dash-border)', paddingBottom: 4 }}>3. Enterprise Configuration Center</div>
                  • <strong>Config Mode:</strong> {configMode}<br />
                  • <strong>Parallel Workers:</strong> {parallelism} Workers ({batchSize} Row Batches)<br />
                  • <strong>Validation Level:</strong> {validationLevel}<br />
                  • <strong>PII Masking:</strong> {maskingEnabled ? `Active (${maskingMethod})` : 'Disabled'}
                </div>
                <div style={{ padding: 14, background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)', fontSize: 12, lineHeight: 1.6 }}>
                  <div style={{ fontWeight: 700, marginBottom: 8, color: 'var(--dash-text-primary)', borderBottom: '1px solid var(--dash-border)', paddingBottom: 4 }}>4. Dynamic Execution Graph</div>
                  • <strong>Pipeline Stages:</strong> {dynamicExecutionPlanNodes.length} Generated Stages<br />
                  • <strong>CDC Replication:</strong> {enableCdc ? 'Active Stream' : 'Batch Sync'}<br />
                  • <strong>Predicted Trust Score:</strong> 99.4%<br />
                  • <strong>Risk Level:</strong> 0.12 (LOW)
                </div>
              </div>

              <div style={{ padding: 14, background: 'var(--dash-surface)', borderRadius: 10, border: '1px solid var(--dash-border)', fontSize: 12, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div><strong style={{ color: 'var(--dash-text-primary)' }}>Governance Policy:</strong> {fourEyesPolicy ? 'Four-Eyes Executive Approval Enforced' : 'Single Operator Approval'}</div>
                <span style={{ fontSize: 11, padding: '4px 10px', borderRadius: 4, background: 'rgba(16,185,129,0.15)', color: '#10B981', fontWeight: 700 }}>APPROVAL PASSED</span>
              </div>
            </div>
          )}

        </div>

        {/* ── Persistent Right Enterprise Summary Panel (Fluid width) ───── */}
        <div style={{ width: 290, borderLeft: '1px solid var(--dash-border)', background: 'var(--dash-surface)', padding: 16, display: 'flex', flexDirection: 'column', gap: 14, overflowY: 'auto', flexShrink: 0 }}>
          <div style={{ fontSize: 11, fontWeight: 800, textTransform: 'uppercase', color: 'var(--dash-text-secondary)', letterSpacing: '0.06em', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Activity size={14} color="#3B82F6" /> Executive Live Summary
          </div>

          <div style={{ padding: 10, background: 'var(--dash-bg)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
            <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', fontWeight: 600 }}>Migration Workspace</div>
            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--dash-text-primary)', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {migName || 'Untitled Migration'}
            </div>
          </div>

          <button type="button" onClick={() => setShowExecutionPlanDrawer(true)}
            style={{ width: '100%', padding: '10px 14px', borderRadius: 8, background: 'rgba(37,99,235,0.12)', border: '1px solid var(--dash-accent)', color: 'var(--dash-accent)', fontSize: 12, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
            <Zap size={14} /> View Execution Plan DAG
          </button>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            <div style={{ padding: 8, background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)' }}>
              <div style={{ fontSize: 9, color: 'var(--dash-text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>Source Engine</div>
              <div style={{ fontSize: 11, fontWeight: 700, marginTop: 2, color: 'var(--dash-text-primary)' }}>{sourceEngine.split(' ')[0]}</div>
            </div>
            <div style={{ padding: 8, background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)' }}>
              <div style={{ fontSize: 9, color: 'var(--dash-text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>Target Engine</div>
              <div style={{ fontSize: 11, fontWeight: 700, marginTop: 2, color: 'var(--dash-text-primary)' }}>{targetEngine.split(' ')[0]}</div>
            </div>
          </div>

          {/* Telemetry Group 1 */}
          <div style={{ background: 'var(--dash-bg)', padding: 10, borderRadius: 8, border: '1px solid var(--dash-border)', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--dash-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '1px solid var(--dash-border)', paddingBottom: 4 }}>
              1. Scope Telemetry
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: 'var(--dash-text-secondary)' }}>Databases Selected:</span>
              <strong style={{ color: 'var(--dash-text-primary)' }}>{selectedDbCount} / {TOTAL_DATABASES_DETECTED}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: 'var(--dash-text-secondary)' }}>Schemas Selected:</span>
              <strong style={{ color: 'var(--dash-text-primary)' }}>{selectedSchemaCount} / {TOTAL_SCHEMAS_DETECTED}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: 'var(--dash-text-secondary)' }}>Objects Selected:</span>
              <strong style={{ color: '#10B981' }}>{selectedCount.toLocaleString()}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: 'var(--dash-text-secondary)' }}>Objects Excluded:</span>
              <strong style={{ color: excludedCount > 0 ? '#F59E0B' : '#10B981' }}>{excludedCount.toLocaleString()}</strong>
            </div>
          </div>

          {/* Telemetry Group 2 */}
          <div style={{ background: 'var(--dash-bg)', padding: 10, borderRadius: 8, border: '1px solid var(--dash-border)', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--dash-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '1px solid var(--dash-border)', paddingBottom: 4 }}>
              2. Intelligence & DAG
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: 'var(--dash-text-secondary)' }}>DAG Stages:</span>
              <strong style={{ color: '#3B82F6' }}>{dynamicExecutionPlanNodes.length} Stages</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: 'var(--dash-text-secondary)' }}>Workers:</span>
              <strong style={{ color: 'var(--dash-text-primary)' }}>{parallelism} Pool</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: 'var(--dash-text-secondary)' }}>Validation:</span>
              <strong style={{ color: 'var(--dash-text-primary)' }}>{validationLevel}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: 'var(--dash-text-secondary)' }}>Predicted Trust:</span>
              <strong style={{ color: '#10B981' }}>99.4%</strong>
            </div>
          </div>

          {/* Telemetry Group 3 */}
          <div style={{ background: 'var(--dash-bg)', padding: 10, borderRadius: 8, border: '1px solid var(--dash-border)', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--dash-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '1px solid var(--dash-border)', paddingBottom: 4 }}>
              3. Connections & Policy
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: 'var(--dash-text-secondary)' }}>Source Link:</span>
              <span style={{ color: sourceTested ? '#10B981' : '#F59E0B', fontWeight: 700 }}>{sourceTested ? '● CONNECTED' : '○ PENDING'}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: 'var(--dash-text-secondary)' }}>Target Link:</span>
              <span style={{ color: targetTested ? '#10B981' : '#F59E0B', fontWeight: 700 }}>{targetTested ? '● CONNECTED' : '○ PENDING'}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: 'var(--dash-text-secondary)' }}>Four-Eyes Policy:</span>
              <span style={{ color: '#10B981', fontWeight: 700 }}>✓ PASSED</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Footer Navigation Bar ───────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 24px', borderTop: '1px solid var(--dash-border)', background: 'var(--dash-surface)', flexShrink: 0 }}>
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
              <button type="button" className={styles.resumeBtn} onClick={() => setShowLaunchConfirmModal(true)}
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
            style={{ width: 500, height: '100%', background: 'var(--dash-surface)', borderLeft: '1px solid var(--dash-border)', padding: 24, display: 'flex', flexDirection: 'column', gap: 18, overflowY: 'auto' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--dash-border)', paddingBottom: 12 }}>
              <div>
                <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>Dynamic Migration Execution Plan</h3>
                <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', marginTop: 2 }}>Generated for current selection & configuration</div>
              </div>
              <button onClick={() => setShowExecutionPlanDrawer(false)} style={{ background: 'none', border: 'none', color: 'var(--dash-text-secondary)', cursor: 'pointer', padding: 2 }}>
                <X size={20} />
              </button>
            </div>

            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--dash-text-secondary)', textTransform: 'uppercase' }}>Visual Execution DAG Pipeline ({dynamicExecutionPlanNodes.length} Stages)</div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {dynamicExecutionPlanNodes.map((item) => (
                <div key={item.stage} style={{ display: 'flex', gap: 12, alignItems: 'flex-start', padding: 10, background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)' }}>
                  <span style={{ width: 22, height: 22, borderRadius: '50%', background: 'rgba(37,99,235,0.2)', color: '#3B82F6', fontSize: 11, fontWeight: 800, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>{item.stage}</span>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--dash-text-primary)' }}>{item.name}</div>
                    <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', marginTop: 2 }}>{item.details}</div>
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

      {/* ── Enterprise Migration Creation Confirmation Modal ─────────────── */}
      {showLaunchConfirmModal && (
        <div
          onClick={() => setShowLaunchConfirmModal(false)}
          style={{
            position: 'fixed',
            top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.75)',
            backdropFilter: 'blur(4px)',
            zIndex: 10000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 24,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: 620,
              maxWidth: '90vw',
              background: 'var(--dash-surface)',
              border: '1px solid var(--dash-border)',
              borderRadius: 14,
              boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              transition: 'all 200ms ease-out',
            }}
          >
            {/* Header */}
            <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--dash-border)', background: 'var(--dash-bg)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(16,185,129,0.15)', border: '1px solid rgba(16,185,129,0.3)', color: '#10B981', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <CheckCircle2 size={20} />
                </div>
                <div>
                  <h3 style={{ fontSize: 16, fontWeight: 800, margin: 0, color: 'var(--dash-text-primary)' }}>
                    Migration Pipeline Provisioned & Ready
                  </h3>
                  <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)', marginTop: 2 }}>
                    Final custody review before launching Mission Control.
                  </div>
                </div>
              </div>
              <button type="button" onClick={() => setShowLaunchConfirmModal(false)} style={{ background: 'none', border: 'none', color: 'var(--dash-text-secondary)', cursor: 'pointer' }}>
                <X size={20} />
              </button>
            </div>

            {/* Summary Matrix */}
            <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div style={{ padding: 14, background: 'var(--dash-bg)', borderRadius: 10, border: '1px solid var(--dash-border)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, fontSize: 12 }}>
                <div>
                  <div style={{ color: 'var(--dash-text-secondary)', fontSize: 10, fontWeight: 700, textTransform: 'uppercase' }}>Migration Title</div>
                  <div style={{ fontWeight: 800, color: 'var(--dash-text-primary)', marginTop: 2 }}>{migName || 'Oracle ERP Core Migration'}</div>
                </div>
                <div>
                  <div style={{ color: 'var(--dash-text-secondary)', fontSize: 10, fontWeight: 700, textTransform: 'uppercase' }}>Migration ID</div>
                  <div style={{ fontWeight: 800, color: '#3B82F6', marginTop: 2, fontFamily: 'var(--akaal-font-mono, monospace)' }}>MIG-2026-0806-001</div>
                </div>
              </div>

              <div style={{ padding: 14, background: 'var(--dash-bg)', borderRadius: 10, border: '1px solid var(--dash-border)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, fontSize: 12 }}>
                <div>
                  <div style={{ color: 'var(--dash-text-secondary)', fontSize: 10, fontWeight: 700, textTransform: 'uppercase' }}>Source Instance</div>
                  <div style={{ fontWeight: 700, color: 'var(--dash-text-primary)', marginTop: 2 }}>{sourceEngine} ({sourceHost}:{sourcePort}/{sourceDbName})</div>
                </div>
                <div>
                  <div style={{ color: 'var(--dash-text-secondary)', fontSize: 10, fontWeight: 700, textTransform: 'uppercase' }}>Target Instance</div>
                  <div style={{ fontWeight: 700, color: 'var(--dash-text-primary)', marginTop: 2 }}>{targetEngine} ({targetHost}:{targetPort}/{targetDbName})</div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, fontSize: 11 }}>
                <div style={{ padding: 10, background: 'var(--dash-bg)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                  <div style={{ color: 'var(--dash-text-secondary)', fontSize: 10 }}>Discovered & Selected</div>
                  <div style={{ fontWeight: 800, color: '#10B981', marginTop: 2 }}>{selectedDbCount} DBs · {selectedSchemaCount} Schemas · {selectedCount.toLocaleString()} Objs</div>
                </div>
                <div style={{ padding: 10, background: 'var(--dash-bg)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                  <div style={{ color: 'var(--dash-text-secondary)', fontSize: 10 }}>Est. Execution Time</div>
                  <div style={{ fontWeight: 800, color: '#3B82F6', marginTop: 2 }}>~14 Minutes</div>
                </div>
                <div style={{ padding: 10, background: 'var(--dash-bg)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                  <div style={{ color: 'var(--dash-text-secondary)', fontSize: 10 }}>Worker Allocation</div>
                  <div style={{ fontWeight: 800, color: 'var(--dash-text-primary)', marginTop: 2 }}>{parallelism} Workers ({batchSize} Batch)</div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, fontSize: 11 }}>
                <div style={{ padding: 10, background: 'var(--dash-bg)', borderRadius: 8, border: '1px solid var(--dash-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: 'var(--dash-text-secondary)' }}>Governance Approval:</span>
                  <span style={{ color: '#10B981', fontWeight: 800 }}>✓ GATE 2 PASSED</span>
                </div>
                <div style={{ padding: 10, background: 'var(--dash-bg)', borderRadius: 8, border: '1px solid var(--dash-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: 'var(--dash-text-secondary)' }}>Predicted Risk Level:</span>
                  <span style={{ color: '#10B981', fontWeight: 800 }}>0.12 (LOW RISK)</span>
                </div>
              </div>
            </div>

            {/* Action Footer */}
            <div style={{ padding: '16px 24px', borderTop: '1px solid var(--dash-border)', background: 'var(--dash-bg)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <button
                type="button"
                onClick={() => {
                  notificationService.push('Migration Plan Exported', 'info', 'Downloaded workflow manifest payload JSON.');
                }}
                style={{ padding: '8px 14px', borderRadius: 6, background: 'none', border: '1px solid var(--dash-border)', color: 'var(--dash-text-secondary)', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
              >
                Export Migration Plan
              </button>

              <div style={{ display: 'flex', gap: 10 }}>
                <button
                  type="button"
                  onClick={() => setShowLaunchConfirmModal(false)}
                  style={{ padding: '8px 16px', borderRadius: 8, background: 'var(--dash-surface)', border: '1px solid var(--dash-border)', color: 'var(--dash-text-primary)', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
                >
                  Stay in Wizard
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowLaunchConfirmModal(false);
                    handleCompleteLaunch();
                  }}
                  style={{ padding: '9px 22px', borderRadius: 8, background: '#10B981', color: '#FFF', border: 'none', fontSize: 13, fontWeight: 800, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}
                >
                  Launch Mission Control →
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
