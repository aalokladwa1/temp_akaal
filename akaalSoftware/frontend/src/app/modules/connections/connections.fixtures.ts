import { ConnectionRecord } from './connections.models';

export const FIXTURE_STANDARD_CONNECTIONS: ConnectionRecord[] = [
  // 1. Relational - Oracle RAC (Verified Recent)
  {
    id: 'conn-ora-rac-01',
    name: 'Core Banking Oracle RAC Primary',
    description: 'Production transactional ledger database cluster with active-active Data Guard standby.',
    providerId: 'oracle',
    providerName: 'Oracle RAC',
    family: 'RELATIONAL',
    environment: 'Production',
    workspaceId: 'ws-prod-emea',
    workspaceName: 'EMEA Production Workspace',
    endpointDisplay: 'rac-cluster-01.corp.internal:1521/FINANCE',
    safeRouteInfo: 'Direct DirectConnect / Private Subnet (10.120.4.0/24)',
    tlsMode: 'TLS_1_3',
    authMethodDisplay: 'Vault Managed AppRole + Wallet mTLS',
    roleApplicability: 'SOURCE_AND_TARGET',
    verificationState: 'VERIFIED_RECENT',
    lastVerifiedAt: '2026-09-07T21:45:00Z',
    lastVerifiedDetails: 'Latency 1.2ms · TLS 1.3 Valid · LogMiner CDC & Schema Read Attested',
    usage: {
      referencedProjectCount: 2,
      activeMigrationCount: 3,
      activeValidationCount: 2,
      projectNames: ['Core Banking Ledger Modernization', 'Payments Gateway Real-Time Sync'],
      migrationNames: ['Accounts & General Ledger M2', 'FX Rates Mirror'],
      isUnused: false,
      usageAvailable: true
    },
    fabric: {
      site: 'Frankfurt-DC1',
      locality: 'eu-central-1',
      privateRoute: 'transit-gw-prod-01'
    },
    tags: ['Core Banking', 'Tier 0', 'CDC Active'],
    createdAt: '2026-01-10T08:30:00Z',
    updatedAt: '2026-09-07T21:45:00Z'
  },

  // 2. Relational - AWS Aurora PostgreSQL (Verified Point-in-Time)
  {
    id: 'conn-pg-aurora-01',
    name: 'Cloud Banking Aurora PostgreSQL 16',
    description: 'Target AWS Aurora PostgreSQL multi-AZ cluster for cloud migration workloads.',
    providerId: 'postgresql',
    providerName: 'PostgreSQL (Aurora)',
    family: 'RELATIONAL',
    environment: 'Production',
    workspaceId: 'ws-prod-emea',
    workspaceName: 'EMEA Production Workspace',
    endpointDisplay: 'aurora-pg-cluster.eu-central-1.rds.amazonaws.com:5432/core_banking',
    safeRouteInfo: 'VPC Peering / Private Route Table (172.24.0.0/16)',
    tlsMode: 'TLS_1_3',
    authMethodDisplay: 'AWS IAM Database Authentication',
    roleApplicability: 'SOURCE_AND_TARGET',
    verificationState: 'VERIFIED_POINT_IN_TIME',
    lastVerifiedAt: '2026-09-07T14:20:00Z',
    lastVerifiedDetails: 'Latency 3.8ms · TLS 1.3 · Replication role verified · 18 schema partitions writable',
    usage: {
      referencedProjectCount: 3,
      activeMigrationCount: 4,
      activeValidationCount: 3,
      projectNames: ['Core Banking Ledger Modernization', 'Customer 360 Lakehouse Ingestion'],
      migrationNames: ['Accounts & General Ledger M2', 'Customer Reference & KYC History'],
      isUnused: false,
      usageAvailable: true
    },
    fabric: {
      site: 'AWS-eu-central-1',
      locality: 'eu-central-1a',
      privateRoute: 'vpc-peering-fin-02'
    },
    tags: ['Target Estate', 'Aurora PG 16', 'Tier 1'],
    createdAt: '2026-01-15T11:00:00Z',
    updatedAt: '2026-09-07T14:20:00Z'
  },

  // 3. Warehouse / Lake - Snowflake Enterprise (Verified Recent)
  {
    id: 'conn-snw-lake-01',
    name: 'Enterprise Analytics Snowflake Lakehouse',
    description: 'Central analytical data warehouse for enterprise reporting and data science modeling.',
    providerId: 'snowflake',
    providerName: 'Snowflake',
    family: 'WAREHOUSE_LAKE',
    environment: 'Production',
    workspaceId: 'ws-prod-emea',
    workspaceName: 'EMEA Production Workspace',
    endpointDisplay: 'akaal_enterprise.eu-west-1.privatelink.snowflakecomputing.com',
    safeRouteInfo: 'AWS PrivateLink / Zero Internet Egress',
    tlsMode: 'TLS_1_3',
    authMethodDisplay: 'RSA Keypair Authentication + OAuth 2.0',
    roleApplicability: 'TARGET_ONLY',
    verificationState: 'VERIFIED_RECENT',
    lastVerifiedAt: '2026-09-07T22:10:00Z',
    lastVerifiedDetails: 'PrivateLink established · Warehouse X-LARGE accessible · Stage staging_area/ verified',
    usage: {
      referencedProjectCount: 2,
      activeMigrationCount: 2,
      activeValidationCount: 1,
      projectNames: ['Customer 360 Lakehouse Ingestion', 'Fraud Telemetry Continuous Streaming'],
      migrationNames: ['Customer 360 Raw Ingestion', 'Fraud Event History'],
      isUnused: false,
      usageAvailable: true
    },
    tags: ['Analytics', 'Snowflake', 'PrivateLink'],
    createdAt: '2026-02-01T09:15:00Z',
    updatedAt: '2026-09-07T22:10:00Z'
  },

  // 4. Streaming - Apache Kafka Enterprise Cluster (Verified Recent)
  {
    id: 'conn-kafka-prod-01',
    name: 'Enterprise Event Hub Kafka Cluster',
    description: 'High-throughput transactional event bus with SASL_SSL authentication and schema registry.',
    providerId: 'kafka',
    providerName: 'Apache Kafka',
    family: 'STREAMING',
    environment: 'Production',
    workspaceId: 'ws-prod-emea',
    workspaceName: 'EMEA Production Workspace',
    endpointDisplay: 'kafka-broker-01.corp.internal:9092 [6 Brokers, Schema Registry :8081]',
    safeRouteInfo: 'Encrypted Dedicated Subnet / mTLS Mutual Auth',
    tlsMode: 'MUTUAL_TLS',
    authMethodDisplay: 'SASL_SSL SCRAM-SHA-512 + X.509 Client Cert',
    roleApplicability: 'SOURCE_AND_TARGET',
    verificationState: 'VERIFIED_RECENT',
    lastVerifiedAt: '2026-09-07T20:30:00Z',
    lastVerifiedDetails: 'Cluster metadata OK · 6 brokers alive · Schema Registry compatibility verified',
    usage: {
      referencedProjectCount: 2,
      activeMigrationCount: 2,
      activeValidationCount: 1,
      projectNames: ['Fraud Telemetry Continuous Streaming', 'Payments Gateway Real-Time Sync'],
      migrationNames: ['Fraud Events Stream', 'Payments Gateway Sync'],
      isUnused: false,
      usageAvailable: true
    },
    fabric: {
      site: 'Frankfurt-DC2',
      locality: 'eu-central-1',
      privateRoute: 'ev-backbone-01'
    },
    tags: ['Kafka', 'Event Streaming', 'CDC Source'],
    createdAt: '2026-02-10T14:00:00Z',
    updatedAt: '2026-09-07T20:30:00Z'
  },

  // 5. Object Storage - Amazon S3 Data Lake (Config Changed Since Test)
  {
    id: 'conn-s3-lake-01',
    name: 'Regulatory Archival S3 Bucket',
    description: 'Immutable object storage bucket for regulatory financial archives with WORM retention policy.',
    providerId: 's3',
    providerName: 'Amazon S3',
    family: 'OBJECT_STORAGE',
    environment: 'Production',
    workspaceId: 'ws-prod-emea',
    workspaceName: 'EMEA Production Workspace',
    endpointDisplay: 's3://prod-emea-compliance-archive (eu-central-1)',
    safeRouteInfo: 'VPC Gateway Endpoint s3.eu-central-1.amazonaws.com',
    tlsMode: 'TLS_1_3',
    authMethodDisplay: 'IAM Role Delegation (arn:aws:iam::123456789012:role/akaal-archival-sa)',
    roleApplicability: 'TARGET_ONLY',
    verificationState: 'CONFIG_CHANGED_SINCE_TEST',
    lastVerifiedAt: '2026-09-05T10:00:00Z',
    lastVerifiedDetails: 'Last tested 2d ago · S3 Object Lock PutObject permission verified',
    configChangedSinceTest: true,
    usage: {
      referencedProjectCount: 1,
      activeMigrationCount: 1,
      activeValidationCount: 0,
      projectNames: ['Regulatory Long-Term Archival'],
      migrationNames: ['Cold Ledger Archival M7'],
      isUnused: false,
      usageAvailable: true
    },
    advisory: {
      type: 'REVIEW_RECOMMENDED',
      headline: 'Bucket policy updated in AWS IAM since last probe'
    },
    tags: ['S3', 'Compliance', 'WORM Storage'],
    createdAt: '2026-03-01T09:00:00Z',
    updatedAt: '2026-09-07T16:00:00Z'
  },

  // 6. NoSQL - MongoDB Atlas Sharded Cluster (Partial Verification)
  {
    id: 'conn-mongo-atlas-01',
    name: 'Digital Experience MongoDB Sharded Cluster',
    description: 'Document database cluster for mobile and web customer profiles and session documents.',
    providerId: 'mongodb',
    providerName: 'MongoDB Atlas',
    family: 'NOSQL_GRAPH',
    environment: 'Production',
    workspaceId: 'ws-prod-emea',
    workspaceName: 'EMEA Production Workspace',
    endpointDisplay: 'cluster0.private.mongodb.net [3 Shards, 9 Nodes]',
    safeRouteInfo: 'AWS PrivateLink Endpoint Service',
    tlsMode: 'TLS_1_3',
    authMethodDisplay: 'SCRAM-SHA-256 / AppRole',
    roleApplicability: 'SOURCE_AND_TARGET',
    verificationState: 'PARTIAL_VERIFIED',
    lastVerifiedAt: '2026-09-06T18:00:00Z',
    lastVerifiedDetails: 'Network connectivity & TLS verified · oplog.rs permission probe was skipped',
    usage: {
      referencedProjectCount: 1,
      activeMigrationCount: 1,
      activeValidationCount: 1,
      projectNames: ['Customer 360 Lakehouse Ingestion'],
      migrationNames: ['Customer Profiles Document Sync'],
      isUnused: false,
      usageAvailable: true
    },
    tags: ['MongoDB', 'NoSQL', 'Document Store'],
    createdAt: '2026-02-15T12:00:00Z',
    updatedAt: '2026-09-06T18:00:00Z'
  },

  // 7. Relational - IBM Db2 Mainframe Gateway (Verification Failed)
  {
    id: 'conn-db2-main-01',
    name: 'Mainframe IBM Db2 z/OS Gateway',
    description: 'Legacy core mainframe database gateway for historical general ledger and trade accounting.',
    providerId: 'db2',
    providerName: 'IBM Db2 (z/OS)',
    family: 'RELATIONAL',
    environment: 'Production',
    workspaceId: 'ws-prod-emea',
    workspaceName: 'EMEA Production Workspace',
    endpointDisplay: 'db2-gw-01.corp.internal:50000/GLDB01',
    safeRouteInfo: 'Direct Mainframe Gateway / SNA over IP',
    tlsMode: 'TLS_1_2',
    authMethodDisplay: 'RACF Kerberos Principal + SSL Certificate',
    roleApplicability: 'SOURCE_ONLY',
    verificationState: 'VERIFICATION_FAILED',
    lastVerifiedAt: '2026-09-07T19:40:00Z',
    lastVerifiedDetails: 'Probe failed after 5000ms timeout',
    verificationFailureReason: 'Connection refused: port 50000 unreachable via gateway daemon. Socket reset by peer.',
    usage: {
      referencedProjectCount: 1,
      activeMigrationCount: 1,
      activeValidationCount: 1,
      projectNames: ['Mainframe DB2 Warehouse Retirement'],
      migrationNames: ['Trade History Batch Extraction'],
      isUnused: false,
      usageAvailable: true
    },
    advisory: {
      type: 'ANOMALY',
      headline: 'Mainframe gateway listener dropped TCP connection'
    },
    tags: ['Mainframe', 'Db2', 'Source Only'],
    createdAt: '2026-01-20T10:00:00Z',
    updatedAt: '2026-09-07T19:40:00Z'
  },

  // 8. Relational - Microsoft SQL Server Staging (Verification Stale)
  {
    id: 'conn-mssql-stg-01',
    name: 'Treasury SQL Server AlwaysOn Staging',
    description: 'Staging replica of treasury settlement database for pre-flight validation testing.',
    providerId: 'sqlserver',
    providerName: 'Microsoft SQL Server',
    family: 'RELATIONAL',
    environment: 'Staging',
    workspaceId: 'ws-prod-emea',
    workspaceName: 'EMEA Production Workspace',
    endpointDisplay: 'sql-ao-stg.corp.internal:1433/TreasuryStaging',
    safeRouteInfo: 'Internal Office VPN (10.40.12.0/24)',
    tlsMode: 'TLS_1_2',
    authMethodDisplay: 'Windows Active Directory Kerberos Auth',
    roleApplicability: 'SOURCE_AND_TARGET',
    verificationState: 'VERIFIED_STALE',
    lastVerifiedAt: '2026-08-15T09:00:00Z',
    lastVerifiedDetails: 'Last verified 23 days ago. Recommended freshness threshold is 7 days.',
    usage: {
      referencedProjectCount: 1,
      activeMigrationCount: 0,
      activeValidationCount: 0,
      projectNames: ['Treasury Ledger Modernization'],
      isUnused: false,
      usageAvailable: true
    },
    tags: ['SQL Server', 'Staging', 'Treasury'],
    createdAt: '2026-03-10T15:00:00Z',
    updatedAt: '2026-08-15T09:00:00Z'
  },

  // 9. SaaS / Application - Salesforce Enterprise API (Never Tested)
  {
    id: 'conn-sfdc-crm-01',
    name: 'Salesforce Enterprise CRM Instance',
    description: 'Corporate customer CRM instance connecting via OAuth 2.0 REST and Bulk API v58.0.',
    providerId: 'salesforce',
    providerName: 'Salesforce',
    family: 'APPLICATION',
    environment: 'Production',
    workspaceId: 'ws-prod-emea',
    workspaceName: 'EMEA Production Workspace',
    endpointDisplay: 'enterprise-org.my.salesforce.com [Bulk API v58.0]',
    safeRouteInfo: 'HTTPS REST API Gateway / Cloud Egress IP Whitelist',
    tlsMode: 'TLS_1_3',
    authMethodDisplay: 'OAuth 2.0 JWT Bearer Flow (Connected App)',
    roleApplicability: 'SOURCE_ONLY',
    verificationState: 'NEVER_TESTED',
    lastVerifiedAt: null,
    lastVerifiedDetails: 'Newly configured profile. Initial connectivity and API quota probe has not run.',
    usage: {
      referencedProjectCount: 0,
      activeMigrationCount: 0,
      activeValidationCount: 0,
      isUnused: true,
      usageAvailable: true
    },
    tags: ['SaaS', 'Salesforce', 'CRM', 'Unused'],
    createdAt: '2026-09-07T12:00:00Z',
    updatedAt: '2026-09-07T12:00:00Z'
  },

  // 10. Warehouse - Google BigQuery Analytics (Verified Recent)
  {
    id: 'conn-gbq-analytics-01',
    name: 'Google BigQuery Global Analytics Fleet',
    description: 'GCP BigQuery regional multi-tenant dataset for cross-regional fraud telemetry aggregation.',
    providerId: 'bigquery',
    providerName: 'Google BigQuery',
    family: 'WAREHOUSE_LAKE',
    environment: 'Production',
    workspaceId: 'ws-prod-emea',
    workspaceName: 'EMEA Production Workspace',
    endpointDisplay: 'gcp-project-fin-telemetry.europe-west3 [BigQuery API v2]',
    safeRouteInfo: 'Google Cloud Interconnect / Direct VPC Egress',
    tlsMode: 'TLS_1_3',
    authMethodDisplay: 'GCP Service Account Key via Vault Storage',
    roleApplicability: 'TARGET_ONLY',
    verificationState: 'VERIFIED_RECENT',
    lastVerifiedAt: '2026-09-07T18:15:00Z',
    lastVerifiedDetails: 'Dataset permissions OK · BigQuery Storage Write API quota attested',
    usage: {
      referencedProjectCount: 1,
      activeMigrationCount: 1,
      activeValidationCount: 1,
      projectNames: ['Fraud Telemetry Continuous Streaming'],
      migrationNames: ['Fraud Telemetry Continuous Streaming'],
      isUnused: false,
      usageAvailable: true
    },
    tags: ['BigQuery', 'GCP', 'Analytics'],
    createdAt: '2026-03-20T10:00:00Z',
    updatedAt: '2026-09-07T18:15:00Z'
  },

  // 11. Time-Series - InfluxDB Telemetry Store (Unused, Verified)
  {
    id: 'conn-influx-metrics-01',
    name: 'Industrial IoT InfluxDB Telemetry Fleet',
    description: 'High-precision time series metrics store for operational sensor time-series replication.',
    providerId: 'influxdb',
    providerName: 'InfluxDB',
    family: 'TIME_SERIES',
    environment: 'Staging',
    workspaceId: 'ws-prod-emea',
    workspaceName: 'EMEA Production Workspace',
    endpointDisplay: 'influx-telemetry.corp.internal:8086/telemetry_v2',
    safeRouteInfo: 'Private IoT VLAN (192.168.100.0/24)',
    tlsMode: 'TLS_1_3',
    authMethodDisplay: 'API Token with Org Read Permissions',
    roleApplicability: 'SOURCE_AND_TARGET',
    verificationState: 'VERIFIED_POINT_IN_TIME',
    lastVerifiedAt: '2026-09-06T11:00:00Z',
    lastVerifiedDetails: 'Bucket listing OK · Read/Write write token valid · Latency 0.8ms',
    usage: {
      referencedProjectCount: 0,
      activeMigrationCount: 0,
      activeValidationCount: 0,
      isUnused: true,
      usageAvailable: true
    },
    tags: ['Time-Series', 'InfluxDB', 'IoT'],
    createdAt: '2026-04-01T08:00:00Z',
    updatedAt: '2026-09-06T11:00:00Z'
  },

  // 12. Local / File - SQLite Embedded Seed Store (Verified Point-in-Time, Non-networked)
  {
    id: 'conn-sqlite-seed-01',
    name: 'Edge Master SQLite Seed Store',
    description: 'Local embedded SQLite reference database for standalone seed migrations (non-networked).',
    providerId: 'sqlite',
    providerName: 'SQLite',
    family: 'RELATIONAL',
    environment: 'Development',
    workspaceId: 'ws-prod-emea',
    workspaceName: 'EMEA Production Workspace',
    endpointDisplay: 'file:///var/lib/akaal/seed_store/reference_data.db [Local POSIX File]',
    safeRouteInfo: 'Local Filesystem Storage (Read-Only POSIX Perms)',
    tlsMode: 'DISABLED',
    authMethodDisplay: 'Filesystem DAC Permissions (0640)',
    roleApplicability: 'SOURCE_ONLY',
    verificationState: 'VERIFIED_POINT_IN_TIME',
    lastVerifiedAt: '2026-09-04T12:00:00Z',
    lastVerifiedDetails: 'File integrity verified · SQLite 3.42 header read OK · 24 tables accessible',
    usage: {
      referencedProjectCount: 0,
      activeMigrationCount: 0,
      activeValidationCount: 0,
      isUnused: true,
      usageAvailable: true
    },
    tags: ['SQLite', 'Embedded', 'Reference Data'],
    createdAt: '2026-05-01T10:00:00Z',
    updatedAt: '2026-09-04T12:00:00Z'
  }
];

export const FIXTURE_EMPTY_CONNECTIONS: ConnectionRecord[] = [];
