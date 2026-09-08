/**
 * AKAAL Connection Workspace Detailed Fixtures (Part C)
 * Covers all 6 tabs and heterogeneous provider families:
 * Oracle RAC, PostgreSQL Aurora, Snowflake, Kafka, S3, BigQuery, Salesforce, SQLite, Unused, and Failed.
 */

import { DetailedConnectionRecord } from './connection-workspace.models';

export const DETAILED_CONNECTION_FIXTURES: Record<string, DetailedConnectionRecord> = {
  // =========================================================================
  // 1. ORACLE RAC PRIMARY (Enterprise Relational & CDC LogMiner)
  // =========================================================================
  'conn-ora-rac-01': {
    id: 'conn-ora-rac-01',
    name: 'Core Banking Oracle RAC Primary',
    description: 'Production transactional ledger database cluster with active-active Data Guard standby.',
    providerId: 'oracle',
    providerName: 'Oracle RAC',
    family: 'RELATIONAL',
    environment: 'Production',
    workspaceId: 'ws-prod-emea',
    workspaceName: 'EMEA Production Workspace',
    organizationId: 'org-enterprise-emea',
    organizationName: 'Enterprise Banking EMEA',
    endpointDisplay: 'rac-cluster-01.corp.internal:1521/FINANCE',
    safeRouteInfo: 'Direct DirectConnect / Private Subnet (10.120.4.0/24)',
    authMethodDisplay: 'Vault Managed AppRole + Wallet mTLS',
    roleApplicability: 'SOURCE_AND_TARGET',
    verificationState: 'VERIFIED_RECENT',
    lastVerifiedAt: '2026-09-07T21:45:00Z',
    lastVerifiedDetails: 'Latency 1.2ms · TLS 1.3 Valid · LogMiner CDC & Schema Read Attested',
    configChangedSinceTest: false,
    lifecycleState: 'ACTIVE',
    fabric: {
      site: 'Frankfurt-DC1',
      locality: 'eu-central-1',
      privateRoute: 'transit-gw-prod-01',
      transitVpc: 'vpc-transit-prod-emea',
      datacenterZone: 'Zone-A1'
    },
    advisory: {
      type: 'REVIEW_RECOMMENDED',
      headline: 'Optimal Throughput: Recommended 8 parallel extractor workers for partitioned transaction tables.',
      description: 'Partition hash distribution indicates 16 physical shards on Oracle RAC Node 1 & Node 2.'
    },
    tags: ['Core Banking', 'Tier 0', 'CDC Active', 'LogMiner'],
    createdAt: '2026-01-10T08:30:00Z',
    updatedAt: '2026-09-07T21:45:00Z',

    endpointConfig: {
      host: 'rac-cluster-01.corp.internal',
      port: 1521,
      serviceName: 'FINANCE_PRD.CORP',
      driverMode: 'THIN',
      schema: 'CORE_BANKING',
      customParams: {
        connectionPoolSize: 32,
        fetchArraySize: 5000,
        enableTaf: true
      }
    },
    authConfig: {
      authMethod: 'PASSWORD',
      username: 'c##akaal_sync_agent',
      secretRef: 'kv/data/production/oracle/core-banking',
      secretSource: 'Vault',
      isConfigured: true
    },
    tlsConfig: {
      mode: 'VERIFY_FULL',
      minVersion: 'TLS_1_3',
      caCertRef: 'pki/ca/corp-root-ca-2026.crt',
      serverNameOverride: 'rac-cluster-01.corp.internal',
      clientCertRef: 'pki/certs/akaal-oracle-client.crt',
      isMtlsEnabled: true
    },
    routeConfig: {
      type: 'DIRECT',
      fabricSite: 'Frankfurt-DC1',
      fabricTransitVpc: 'vpc-transit-prod-emea'
    },
    advancedSettings: {
      dnsTimeoutMs: 3000,
      connectTimeoutMs: 10000,
      socketTimeoutMs: 30000,
      tcpKeepaliveEnabled: true,
      keepaliveIdleSec: 45,
      keepaliveIntervalSec: 10,
      sessionParams: {
        'NLS_DATE_FORMAT': 'YYYY-MM-DD HH24:MI:SS',
        'NLS_TIMESTAMP_TZ_FORMAT': 'YYYY-MM-DD HH24:MI:SS.FF TZR',
        'ALTER SESSION SET TIME_ZONE': 'UTC'
      }
    },
    capabilities: {
      connectivityProbes: [
        { step: 'DNS_RESOLUTION', name: 'DNS Host Resolution', status: 'VERIFIED', latencyMs: 0.4, details: 'Resolved rac-cluster-01.corp.internal to 10.120.4.12, 10.120.4.13' },
        { step: 'TCP_TRANSPORT', name: 'TCP Port Handshake (1521)', status: 'VERIFIED', latencyMs: 0.8, details: 'DirectConnect private wire reached in 0.8ms' },
        { step: 'TLS_HANDSHAKE', name: 'TLS 1.3 & Server Certificate', status: 'VERIFIED', latencyMs: 1.2, details: 'CN=rac-cluster-01.corp.internal, Issuer=Corp Root CA, Cipher=TLS_AES_256_GCM_SHA384' },
        { step: 'AUTHENTICATION', name: 'Credential & AppRole Attestation', status: 'VERIFIED', latencyMs: 2.1, details: 'Authenticated as C##AKAAL_SYNC_AGENT via HashiCorp Vault dynamic lease' },
        { step: 'SERVER_IDENTITY', name: 'Engine Version & Cluster Topology', status: 'VERIFIED', latencyMs: 1.5, details: 'Oracle Database 19c Enterprise Edition Release 19.18.0.0.0 - 2-Node RAC' }
      ],
      permissionChecks: [
        { permission: 'CREATE SESSION', scope: 'Instance', status: 'VERIFIED', details: 'Session establishment authorized' },
        { permission: 'SELECT ANY TABLE', scope: 'Schema: CORE_BANKING, FX_RATES', status: 'VERIFIED', details: 'Read access verified across 314 tables' },
        { permission: 'SELECT_CATALOG_ROLE', scope: 'Data Dictionary', status: 'VERIFIED', details: 'Metadata dictionary dictionary views accessible (DBA_OBJECTS, DBA_TAB_COLS)' },
        { permission: 'EXECUTE ON DBMS_LOGMNR', scope: 'CDC Engine', status: 'VERIFIED', details: 'LogMiner package execution privileges verified' },
        { permission: 'LOGMINING', scope: 'Transaction Redo Logs', status: 'VERIFIED', details: 'Supplemental logging enabled for primary & foreign key columns' }
      ],
      sourceCapability: {
        supported: true,
        status: 'VERIFIED',
        throughputRating: 'High (~180k rows/sec parallel)',
        details: 'Native OCI bulk array extraction with multi-threaded table slicing.'
      },
      targetCapability: {
        supported: true,
        status: 'VERIFIED',
        acidCompliant: true,
        details: 'Direct path load / multi-row batch insert with transactional commit intervals.'
      },
      discoveryCapability: {
        supported: true,
        status: 'VERIFIED',
        supportedObjectTypes: ['Tables', 'Columns', 'Primary Keys', 'Foreign Keys', 'Indexes', 'Partitions', 'Sequences', 'Triggers', 'Views', 'Packages', 'Synonyms'],
        details: 'Full dictionary inspection of Oracle 19c DDL catalog.'
      },
      cdcCapability: {
        type: 'LOGMINER',
        label: 'Oracle LogMiner / XStream CDC',
        status: 'VERIFIED',
        details: 'Continuously captures row-level INSERT, UPDATE, DELETE and DDL alterations from redo/archive logs.'
      },
      validationCapability: {
        supported: true,
        status: 'VERIFIED',
        supportedLevels: ['L1 Row Count', 'L2 Schema Parity', 'L3 Partition Hash Fingerprint', 'L4 Cell Reconciliation'],
        details: 'M8 Validation engine supports parallel block-level CRC32/SHA256 checksum queries.'
      },
      providerLimitations: [
        'Uncommitted transactions in active undo segments are not visible to LogMiner until commit.',
        'LOB columns (>4KB) require inline retrieval mode which limits parallel CDC extraction speed.'
      ],
      proofLevel: 'INTEGRATION_PROVEN',
      lastCheckedAt: '2026-09-07T21:45:00Z',
      configChangedSinceTest: false
    },
    usage: {
      projects: [
        { id: 'proj-banking-01', key: 'CBM', name: 'Core Banking Ledger Modernization', environment: 'Production', status: 'ACTIVE', associatedAt: '2026-01-15T10:00:00Z' },
        { id: 'proj-payments-02', key: 'PGR', name: 'Payments Gateway Real-Time Sync', environment: 'Production', status: 'ACTIVE', associatedAt: '2026-02-01T14:30:00Z' }
      ],
      migrations: [
        { id: 'mig-accounts-gl', name: 'Accounts & General Ledger M2', projectKey: 'CBM', role: 'Source', mode: 'M2 Bulk+CDC', state: 'EXECUTING', lastRunAt: '2026-09-08T18:30:00Z' },
        { id: 'mig-fx-rates', name: 'FX Rates Mirror', projectKey: 'PGR', role: 'Source', mode: 'M3 CDC Continuous', state: 'EXECUTING', lastRunAt: '2026-09-08T20:00:00Z' },
        { id: 'mig-hist-ledger', name: 'Historical Archive 2020-2025', projectKey: 'CBM', role: 'Source', mode: 'M1 Bulk', state: 'COMPLETED', lastRunAt: '2026-08-20T12:00:00Z' }
      ],
      validations: [
        { id: 'val-accounts-parity', name: 'Accounts 10M Row Reconciliation', projectKey: 'CBM', role: 'Source Reference', verdict: 'PASSED', state: 'COMPLETED', lastRunAt: '2026-09-07T22:00:00Z' },
        { id: 'val-fx-audit', name: 'FX Spot Rates Dual Parity', projectKey: 'PGR', role: 'Source Reference', verdict: 'PASSED', state: 'COMPLETED', lastRunAt: '2026-09-08T15:00:00Z' }
      ],
      activeStreamsCount: 2,
      scheduledExecutionsCount: 1,
      referenceProtection: {
        canDelete: false,
        blockReason: 'Connection is referenced by 2 Projects, 3 Migrations (2 executing), and 2 Validation missions. Archive connection instead.',
        isReferenced: true
      }
    },
    activities: [
      {
        id: 'act-01',
        timestamp: '2026-09-07T21:45:00Z',
        category: 'TEST',
        title: 'Point-in-Time Connection Test Succeeded',
        description: 'Automated health probe verified TLS 1.3 handshake, Vault authentication, and LogMiner redo access.',
        actor: 'system-probe-scheduler',
        icon: 'shield-check',
        stateBadge: { label: 'Verified', type: 'success' }
      },
      {
        id: 'act-02',
        timestamp: '2026-09-01T14:20:00Z',
        category: 'SECURITY',
        title: 'Secret Lease Renewed',
        description: 'HashiCorp Vault dynamic AppRole token rotated smoothly without connection disruption.',
        actor: 'vault-agent@corp.internal',
        icon: 'lock',
        stateBadge: { label: 'Rotated', type: 'info' }
      },
      {
        id: 'act-03',
        timestamp: '2026-08-15T09:10:00Z',
        category: 'CONFIG',
        title: 'Connection Pool Increased',
        description: 'Connection pool size adjusted from 16 to 32 for multi-worker parallel extraction.',
        actor: 'admin-aalok@corp.internal',
        icon: 'sliders',
        stateBadge: { label: 'Updated', type: 'neutral' }
      },
      {
        id: 'act-04',
        timestamp: '2026-01-10T08:30:00Z',
        category: 'LIFECYCLE',
        title: 'Connection Profile Authored',
        description: 'Initial creation of Core Banking Oracle RAC connection profile in EMEA Production Workspace.',
        actor: 'admin-aalok@corp.internal',
        icon: 'plus-circle',
        stateBadge: { label: 'Created', type: 'info' }
      }
    ]
  },

  // =========================================================================
  // 2. AWS AURORA POSTGRESQL 16 (Relational & Logical Decoding)
  // =========================================================================
  'conn-pg-aurora-01': {
    id: 'conn-pg-aurora-01',
    name: 'Cloud Banking Aurora PostgreSQL 16',
    description: 'Target AWS Aurora PostgreSQL multi-AZ cluster for cloud migration workloads.',
    providerId: 'postgresql',
    providerName: 'PostgreSQL (Aurora)',
    family: 'RELATIONAL',
    environment: 'Production',
    workspaceId: 'ws-prod-emea',
    workspaceName: 'EMEA Production Workspace',
    organizationId: 'org-enterprise-emea',
    organizationName: 'Enterprise Banking EMEA',
    managedCloudId: 'AWS_MANAGED',
    managedCloudName: 'Amazon Web Services',
    managedResourceType: 'Amazon Aurora PostgreSQL',
    endpointDisplay: 'aurora-pg-cluster.eu-central-1.rds.amazonaws.com:5432/core_banking',
    safeRouteInfo: 'VPC Peering / Private Route Table (172.24.0.0/16)',
    authMethodDisplay: 'AWS IAM Database Authentication',
    roleApplicability: 'SOURCE_AND_TARGET',
    verificationState: 'VERIFIED_POINT_IN_TIME',
    lastVerifiedAt: '2026-09-07T14:20:00Z',
    lastVerifiedDetails: 'Latency 3.8ms · TLS 1.3 · Replication role verified · 18 schema partitions writable',
    configChangedSinceTest: false,
    lifecycleState: 'ACTIVE',
    fabric: {
      site: 'AWS-eu-central-1',
      locality: 'eu-central-1a',
      privateRoute: 'vpc-peering-fin-02',
      transitVpc: 'vpc-cloud-banking-prod',
      datacenterZone: 'eu-central-1a'
    },
    tags: ['Target Estate', 'Aurora PG 16', 'Tier 1', 'AWS Managed'],
    createdAt: '2026-01-15T11:00:00Z',
    updatedAt: '2026-09-07T14:20:00Z',

    endpointConfig: {
      host: 'aurora-pg-cluster.eu-central-1.rds.amazonaws.com',
      port: 5432,
      database: 'core_banking',
      schema: 'public, ledger_2026',
      customParams: {
        sslMode: 'verify-full',
        applicationName: 'akaal-migration-pipeline'
      }
    },
    authConfig: {
      authMethod: 'AWS_IAM',
      username: 'akaal_aurora_writer',
      roleArn: 'arn:aws:iam::123456789012:role/akaal-aurora-db-sync',
      secretSource: 'AWS Secrets Manager',
      isConfigured: true
    },
    tlsConfig: {
      mode: 'VERIFY_FULL',
      minVersion: 'TLS_1_3',
      caCertRef: 'certs/aws-global-bundle.pem',
      serverNameOverride: 'aurora-pg-cluster.eu-central-1.rds.amazonaws.com',
      isMtlsEnabled: false
    },
    routeConfig: {
      type: 'PRIVATE_ENDPOINT',
      privateEndpointUrl: 'vpce-0a1b2c3d4e5f6g7h8.rds.eu-central-1.vpce.amazonaws.com',
      fabricSite: 'AWS-eu-central-1'
    },
    advancedSettings: {
      dnsTimeoutMs: 5000,
      connectTimeoutMs: 15000,
      socketTimeoutMs: 30000,
      tcpKeepaliveEnabled: true,
      keepaliveIdleSec: 60,
      keepaliveIntervalSec: 15,
      sessionParams: {
        'timezone': 'UTC',
        'synchronous_commit': 'off',
        'work_mem': '64MB'
      }
    },
    capabilities: {
      connectivityProbes: [
        { step: 'DNS_RESOLUTION', name: 'AWS Private DNS Resolution', status: 'VERIFIED', latencyMs: 1.1, details: 'Resolved Aurora cluster endpoint via Route 53 Private Hosted Zone' },
        { step: 'TCP_TRANSPORT', name: 'TCP Port Handshake (5432)', status: 'VERIFIED', latencyMs: 2.3, details: 'VPC peering direct route reached in 2.3ms' },
        { step: 'TLS_HANDSHAKE', name: 'TLS 1.3 Encryption', status: 'VERIFIED', latencyMs: 3.8, details: 'Verified with Amazon RDS Global Root CA bundle' },
        { step: 'AUTHENTICATION', name: 'AWS IAM Database Token Exchange', status: 'VERIFIED', latencyMs: 4.2, details: 'Generated temporary 15-minute IAM auth token' },
        { step: 'SERVER_IDENTITY', name: 'Engine Version Check', status: 'VERIFIED', latencyMs: 1.9, details: 'PostgreSQL 16.2 on aarch64-unknown-linux-gnu, compiled by gcc (GCC) 11.4.1' }
      ],
      permissionChecks: [
        { permission: 'CONNECT', scope: 'Database: core_banking', status: 'VERIFIED', details: 'Connection granted' },
        { permission: 'CREATE, USAGE', scope: 'Schema: public, ledger_2026', status: 'VERIFIED', details: 'DDL table & index creation permitted' },
        { permission: 'INSERT, UPDATE, DELETE', scope: 'All Target Tables', status: 'VERIFIED', details: 'Full DML write operations authorized' },
        { permission: 'rds_replication', scope: 'Logical Decoding Slot', status: 'VERIFIED', details: 'Aurora logical replication slot creation permitted' }
      ],
      sourceCapability: {
        supported: true,
        status: 'VERIFIED',
        throughputRating: 'High (~150k rows/sec)',
        details: 'Supports binary COPY OUT and parallel table slice streaming.'
      },
      targetCapability: {
        supported: true,
        status: 'VERIFIED',
        acidCompliant: true,
        details: 'High-speed binary COPY IN format with batch size 100,000 rows.'
      },
      discoveryCapability: {
        supported: true,
        status: 'VERIFIED',
        supportedObjectTypes: ['Tables', 'Columns', 'Primary Keys', 'Foreign Keys', 'Indexes', 'Unique Constraints', 'Check Constraints', 'Partitions', 'Enums', 'Sequences', 'Views'],
        details: 'Deep introspection of information_schema and pg_catalog.'
      },
      cdcCapability: {
        type: 'LOGICAL_DECODING',
        label: 'PostgreSQL Logical Decoding (pgoutput)',
        status: 'VERIFIED',
        details: 'Native publication / logical replication slot stream with pgoutput plugin.'
      },
      validationCapability: {
        supported: true,
        status: 'VERIFIED',
        supportedLevels: ['L1 Row Count', 'L2 Schema Parity', 'L3 MD5/SHA256 Fingerprint', 'L4 Direct Cell Parity'],
        details: 'Fully integrated with M8 Validation Engine.'
      },
      providerLimitations: [
        'Large JSONB objects require strict UTF-8 sanitization during high-speed COPY.',
        'Foreign keys should be temporarily deferred during initial bulk load for maximum throughput.'
      ],
      proofLevel: 'LIVE_PROVEN',
      lastCheckedAt: '2026-09-07T14:20:00Z',
      configChangedSinceTest: false
    },
    usage: {
      projects: [
        { id: 'proj-banking-01', key: 'CBM', name: 'Core Banking Ledger Modernization', environment: 'Production', status: 'ACTIVE', associatedAt: '2026-01-16T12:00:00Z' },
        { id: 'proj-lakehouse-03', key: 'C360', name: 'Customer 360 Lakehouse Ingestion', environment: 'Production', status: 'ACTIVE', associatedAt: '2026-02-10T16:00:00Z' }
      ],
      migrations: [
        { id: 'mig-accounts-gl', name: 'Accounts & General Ledger M2', projectKey: 'CBM', role: 'Target', mode: 'M2 Bulk+CDC', state: 'EXECUTING', lastRunAt: '2026-09-08T18:30:00Z' },
        { id: 'mig-cust-ref', name: 'Customer Reference & KYC History', projectKey: 'C360', role: 'Target', mode: 'M1 Bulk', state: 'COMPLETED', lastRunAt: '2026-09-01T10:00:00Z' }
      ],
      validations: [
        { id: 'val-accounts-parity', name: 'Accounts 10M Row Reconciliation', projectKey: 'CBM', role: 'Target Assertion', verdict: 'PASSED', state: 'COMPLETED', lastRunAt: '2026-09-07T22:00:00Z' }
      ],
      activeStreamsCount: 1,
      scheduledExecutionsCount: 0,
      referenceProtection: {
        canDelete: false,
        blockReason: 'Connection is referenced by 2 Projects, 2 Migrations (1 executing), and 1 Validation mission. Cannot be permanently deleted.',
        isReferenced: true
      }
    },
    activities: [
      {
        id: 'act-pg-01',
        timestamp: '2026-09-07T14:20:00Z',
        category: 'TEST',
        title: 'Connection Test Passed',
        description: 'Automated verification validated IAM token exchange, SSL handshake, and table write permissions.',
        actor: 'system-probe-scheduler',
        icon: 'shield-check',
        stateBadge: { label: 'Verified', type: 'success' }
      },
      {
        id: 'act-pg-02',
        timestamp: '2026-08-20T11:00:00Z',
        category: 'SECURITY',
        title: 'IAM Role Policy Updated',
        description: 'Extended rds-db:connect permission to include standby replica endpoint.',
        actor: 'cloud-infra-team@corp.internal',
        icon: 'shield',
        stateBadge: { label: 'Security', type: 'info' }
      }
    ]
  },

  // =========================================================================
  // 3. APACHE KAFKA (Streaming Engine - No Fake Database CDC!)
  // =========================================================================
  'conn-kafka-prod-01': {
    id: 'conn-kafka-prod-01',
    name: 'Enterprise Event Hub Kafka Cluster',
    description: 'High-throughput transactional event bus with SASL_SSL authentication and schema registry.',
    providerId: 'kafka',
    providerName: 'Apache Kafka',
    family: 'STREAMING',
    environment: 'Production',
    workspaceId: 'ws-prod-emea',
    workspaceName: 'EMEA Production Workspace',
    organizationId: 'org-enterprise-emea',
    organizationName: 'Enterprise Banking EMEA',
    endpointDisplay: 'kafka-broker-01.corp.internal:9092 [6 Brokers, Schema Registry :8081]',
    safeRouteInfo: 'Encrypted Dedicated Subnet / mTLS Mutual Auth',
    authMethodDisplay: 'SASL_SSL SCRAM-SHA-512 + X.509 Client Cert',
    roleApplicability: 'SOURCE_AND_TARGET',
    verificationState: 'VERIFIED_RECENT',
    lastVerifiedAt: '2026-09-07T20:30:00Z',
    lastVerifiedDetails: 'Cluster metadata OK · 6 brokers alive · Schema Registry compatibility verified',
    configChangedSinceTest: false,
    lifecycleState: 'ACTIVE',
    fabric: {
      site: 'Frankfurt-DC2',
      locality: 'eu-central-1',
      privateRoute: 'ev-backbone-01',
      transitVpc: 'vpc-streaming-prod'
    },
    tags: ['Kafka', 'Event Streaming', 'Stream Consumer', 'mTLS'],
    createdAt: '2026-02-10T14:00:00Z',
    updatedAt: '2026-09-07T20:30:00Z',

    endpointConfig: {
      bootstrapServers: 'kafka-broker-01.corp.internal:9092,kafka-broker-02.corp.internal:9092,kafka-broker-03.corp.internal:9092',
      securityProtocol: 'SASL_SSL',
      customParams: {
        schemaRegistryUrl: 'https://schema-registry.corp.internal:8081',
        compressionType: 'zstd',
        acks: 'all',
        maxInFlightRequestsPerConnection: 1
      }
    },
    authConfig: {
      authMethod: 'SASL_SCRAM_512',
      username: 'akaal-pipeline-consumer',
      secretRef: 'secrets/kafka/scram-creds',
      secretSource: 'Vault',
      isConfigured: true
    },
    tlsConfig: {
      mode: 'VERIFY_FULL',
      minVersion: 'TLS_1_3',
      caCertRef: 'certs/kafka-ca.pem',
      clientCertRef: 'certs/akaal-kafka-client.crt',
      isMtlsEnabled: true
    },
    routeConfig: {
      type: 'DIRECT',
      fabricSite: 'Frankfurt-DC2'
    },
    advancedSettings: {
      dnsTimeoutMs: 3000,
      connectTimeoutMs: 10000,
      socketTimeoutMs: 30000,
      tcpKeepaliveEnabled: true,
      keepaliveIdleSec: 30,
      keepaliveIntervalSec: 10,
      sessionParams: {
        'session.timeout.ms': '45000',
        'heartbeat.interval.ms': '3000',
        'auto.offset.reset': 'earliest'
      }
    },
    capabilities: {
      connectivityProbes: [
        { step: 'DNS_RESOLUTION', name: 'Bootstrap Brokers DNS', status: 'VERIFIED', latencyMs: 0.6, details: 'Resolved 3 broker addresses' },
        { step: 'TCP_TRANSPORT', name: 'TCP Port Reachability (9092)', status: 'VERIFIED', latencyMs: 1.1, details: 'Brokers reached across internal backbone' },
        { step: 'TLS_HANDSHAKE', name: 'mTLS Client Certificate Handshake', status: 'VERIFIED', latencyMs: 1.8, details: 'Mutual TLS established with client identity: CN=akaal-pipeline-consumer' },
        { step: 'SASL_AUTH', name: 'SASL/SCRAM-SHA-512 Authentication', status: 'VERIFIED', latencyMs: 2.4, details: 'Principal: User:akaal-pipeline-consumer' },
        { step: 'CLUSTER_METADATA', name: 'Cluster Introspection & Schema Registry', status: 'VERIFIED', latencyMs: 3.1, details: 'Cluster ID: kfk-prod-emea-99, 6 brokers online, Schema Registry 7.5.0 reachable' }
      ],
      permissionChecks: [
        { permission: 'DescribeCluster', scope: 'Cluster', status: 'VERIFIED', details: 'Cluster metadata access allowed' },
        { permission: 'Read', scope: 'Topic: corp.banking.ledger.*', status: 'VERIFIED', details: 'Consume messages from 24 ledger topics' },
        { permission: 'Write', scope: 'Topic: corp.events.outbound.*', status: 'VERIFIED', details: 'Produce messages with idempotence' },
        { permission: 'DescribeConfigs', scope: 'Topics & Brokers', status: 'VERIFIED', details: 'Topic partition configuration inspection permitted' }
      ],
      sourceCapability: {
        supported: true,
        status: 'VERIFIED',
        throughputRating: 'High (>300k msgs/sec)',
        details: 'Partitioned consumer group extraction with offset commit coordination.'
      },
      targetCapability: {
        supported: true,
        status: 'VERIFIED',
        acidCompliant: false,
        details: 'Producer with idempotence (enable.idempotence=true) and Schema Registry Avro/JSON serialization.'
      },
      discoveryCapability: {
        supported: true,
        status: 'VERIFIED',
        supportedObjectTypes: ['Topics', 'Partitions', 'Consumer Groups', 'Avro Schemas', 'JSON Schemas', 'Protobuf Schemas'],
        details: 'Inspects topic topology and Schema Registry subject versions.'
      },
      cdcCapability: {
        type: 'STREAM_OFFSET',
        label: 'Stream Offset Consumption (Not Database CDC)',
        status: 'VERIFIED',
        details: 'Continuous stream consumption via high-watermark Kafka offset commits. (Truthful stream processing, not relational table CDC).'
      },
      validationCapability: {
        supported: true,
        status: 'VERIFIED',
        supportedLevels: ['L1 Event Count Parity', 'L3 Message Payload Hash', 'L4 Schema Evolution Check'],
        details: 'Validation engine compares stream offset ranges against sink ledger tables.'
      },
      providerLimitations: [
        'Kafka does not have relational rollback transactions; compensating events or Dead Letter Queues (DLQ) are used for failures.',
        'Stream Offset consumption is not database row-level CDC.'
      ],
      proofLevel: 'INTEGRATION_PROVEN',
      lastCheckedAt: '2026-09-07T20:30:00Z',
      configChangedSinceTest: false
    },
    usage: {
      projects: [
        { id: 'proj-fraud-04', key: 'FTCS', name: 'Fraud Telemetry Continuous Streaming', environment: 'Production', status: 'ACTIVE', associatedAt: '2026-02-12T09:00:00Z' },
        { id: 'proj-payments-02', key: 'PGR', name: 'Payments Gateway Real-Time Sync', environment: 'Production', status: 'ACTIVE', associatedAt: '2026-02-15T11:00:00Z' }
      ],
      migrations: [
        { id: 'mig-fraud-stream', name: 'Fraud Events Stream', projectKey: 'FTCS', role: 'Source', mode: 'M3 CDC Continuous', state: 'EXECUTING', lastRunAt: '2026-09-08T20:45:00Z' },
        { id: 'mig-payments-sync', name: 'Payments Gateway Sync', projectKey: 'PGR', role: 'Target', mode: 'M3 CDC Continuous', state: 'EXECUTING', lastRunAt: '2026-09-08T20:45:00Z' }
      ],
      validations: [
        { id: 'val-stream-offsets', name: 'Stream Offset Parity Check', projectKey: 'FTCS', role: 'Source Reference', verdict: 'PASSED', state: 'COMPLETED', lastRunAt: '2026-09-07T20:00:00Z' }
      ],
      activeStreamsCount: 2,
      scheduledExecutionsCount: 0,
      referenceProtection: {
        canDelete: false,
        blockReason: 'Active real-time streams are currently reading from this Kafka cluster. Cannot delete.',
        isReferenced: true
      }
    },
    activities: [
      {
        id: 'act-kf-01',
        timestamp: '2026-09-07T20:30:00Z',
        category: 'TEST',
        title: 'Kafka Cluster Probe Verified',
        description: 'Verified SASL_SSL authentication across 6 brokers and Schema Registry endpoint.',
        actor: 'system-probe-scheduler',
        icon: 'shield-check',
        stateBadge: { label: 'Verified', type: 'success' }
      }
    ]
  },

  // =========================================================================
  // 4. AMAZON S3 ARCHIVE (Object Storage - Config Changed / Stale State)
  // =========================================================================
  'conn-s3-lake-01': {
    id: 'conn-s3-lake-01',
    name: 'Regulatory Archival S3 Bucket',
    description: 'Immutable object storage bucket for regulatory financial archives with WORM retention policy.',
    providerId: 's3',
    providerName: 'Amazon S3',
    family: 'OBJECT_STORAGE',
    environment: 'Production',
    workspaceId: 'ws-prod-emea',
    workspaceName: 'EMEA Production Workspace',
    organizationId: 'org-enterprise-emea',
    organizationName: 'Enterprise Banking EMEA',
    endpointDisplay: 's3://prod-emea-compliance-archive (eu-central-1)',
    safeRouteInfo: 'VPC Gateway Endpoint s3.eu-central-1.amazonaws.com',
    authMethodDisplay: 'IAM Role Delegation (arn:aws:iam::123456789012:role/akaal-archival-sa)',
    roleApplicability: 'TARGET_ONLY',
    verificationState: 'CONFIG_CHANGED_SINCE_TEST',
    lastVerifiedAt: '2026-09-05T10:00:00Z',
    lastVerifiedDetails: 'Last tested 2d ago · S3 Object Lock PutObject permission verified',
    configChangedSinceTest: true,
    lifecycleState: 'ACTIVE',
    fabric: {
      site: 'AWS-eu-central-1',
      locality: 'eu-central-1',
      privateRoute: 's3-gateway-endpoint'
    },
    advisory: {
      type: 'REVIEW_RECOMMENDED',
      headline: 'Verification Stale: Bucket prefix configuration was updated after the last point-in-time test.',
      description: 'Retest connection to verify that the newer prefix permissions and S3 Object Lock rules are active.'
    },
    tags: ['S3', 'Object Storage', 'Archival', 'Compliance'],
    createdAt: '2026-01-20T10:00:00Z',
    updatedAt: '2026-09-08T09:30:00Z',

    endpointConfig: {
      bucketName: 'prod-emea-compliance-archive',
      region: 'eu-central-1',
      endpointUrl: 'https://s3.eu-central-1.amazonaws.com',
      prefix: 'finance/ledger_archive_2026/',
      customParams: {
        storageClass: 'INTELLIGENT_TIERING',
        serverSideEncryption: 'aws:kms',
        kmsKeyId: 'arn:aws:kms:eu-central-1:123456789012:key/mrk-compliance'
      }
    },
    authConfig: {
      authMethod: 'AWS_IAM',
      roleArn: 'arn:aws:iam::123456789012:role/akaal-archival-sa',
      secretSource: 'AWS Secrets Manager',
      isConfigured: true
    },
    tlsConfig: {
      mode: 'REQUIRED',
      minVersion: 'TLS_1_3',
      isMtlsEnabled: false
    },
    routeConfig: {
      type: 'DIRECT',
      fabricSite: 'AWS-eu-central-1'
    },
    advancedSettings: {
      dnsTimeoutMs: 5000,
      connectTimeoutMs: 15000,
      socketTimeoutMs: 30000,
      tcpKeepaliveEnabled: true,
      keepaliveIdleSec: 60,
      keepaliveIntervalSec: 15
    },
    capabilities: {
      connectivityProbes: [
        { step: 'DNS_RESOLUTION', name: 'S3 Regional Endpoint DNS', status: 'VERIFIED', latencyMs: 0.9, details: 'Resolved s3.eu-central-1.amazonaws.com' },
        { step: 'HTTPS_HANDSHAKE', name: 'TLS 1.3 Transport', status: 'VERIFIED', latencyMs: 1.5, details: 'Amazon Trust Services Root CA certificate valid' },
        { step: 'IAM_AUTHENTICATION', name: 'IAM Role AssumeRole / STS Exchange', status: 'VERIFIED', latencyMs: 3.2, details: 'STS AssumeRole succeeded for akaal-archival-sa' }
      ],
      permissionChecks: [
        { permission: 's3:ListBucket', scope: 'Bucket: prod-emea-compliance-archive', status: 'VERIFIED', details: 'Listing objects under prefix permitted' },
        { permission: 's3:PutObject', scope: 'Prefix: finance/ledger_archive_2026/*', status: 'VERIFIED', details: 'Multipart upload permitted with KMS encryption' },
        { permission: 's3:GetObject', scope: 'Prefix: finance/ledger_archive_2026/*', status: 'VERIFIED', details: 'Read verification permitted' },
        { permission: 's3:PutObjectLegalHold', scope: 'Object Lock', status: 'NOT_CHECKED', details: 'WORM Legal Hold governance policy unverified in latest probe' }
      ],
      sourceCapability: {
        supported: false,
        status: 'UNSUPPORTED',
        throughputRating: 'N/A',
        details: 'Configured as Target-Only for archival dumps.'
      },
      targetCapability: {
        supported: true,
        status: 'VERIFIED',
        acidCompliant: false,
        details: 'High-throughput parallel multipart upload with SHA-256 integrity checksum headers.'
      },
      discoveryCapability: {
        supported: true,
        status: 'VERIFIED',
        supportedObjectTypes: ['Buckets', 'Prefix Hierarchy', 'Parquet Files', 'ORC Files', 'CSV Partitions'],
        details: 'Inspects prefix objects and metadata tags.'
      },
      cdcCapability: {
        type: 'NONE',
        label: 'Not Applicable (Object Storage)',
        status: 'UNSUPPORTED',
        details: 'Object Storage does not support database CDC. Supports batch Parquet dump writes.'
      },
      validationCapability: {
        supported: true,
        status: 'VERIFIED',
        supportedLevels: ['L1 Object Count', 'L3 S3 ETag / SHA256 Checksum'],
        details: 'M8 Validation engine compares manifest checksums against database source tables.'
      },
      providerLimitations: [
        'Object Storage has eventual consistency characteristics on some prefix operations.',
        'CDC row-level streaming is not supported on raw object storage buckets.'
      ],
      proofLevel: 'UNIT_PROVEN',
      lastCheckedAt: '2026-09-05T10:00:00Z',
      configChangedSinceTest: true
    },
    usage: {
      projects: [
        { id: 'proj-archival-05', key: 'RLTA', name: 'Regulatory Long-Term Archival', environment: 'Production', status: 'ACTIVE', associatedAt: '2026-01-22T08:00:00Z' }
      ],
      migrations: [
        { id: 'mig-cold-ledger', name: 'Cold Ledger Archival M7', projectKey: 'RLTA', role: 'Target', mode: 'M7 Data Only', state: 'COMPLETED', lastRunAt: '2026-09-04T16:00:00Z' }
      ],
      validations: [],
      activeStreamsCount: 0,
      scheduledExecutionsCount: 1,
      referenceProtection: {
        canDelete: false,
        blockReason: 'Connection has completed historical compliance runs and is referenced by Project RLTA. Archive connection instead.',
        isReferenced: true
      }
    },
    activities: [
      {
        id: 'act-s3-01',
        timestamp: '2026-09-08T09:30:00Z',
        category: 'CONFIG',
        title: 'Bucket Prefix Modified',
        description: 'Prefix updated to "finance/ledger_archive_2026/". Previous verification transitioned to STALE.',
        actor: 'admin-aalok@corp.internal',
        icon: 'sliders',
        stateBadge: { label: 'Needs Retest', type: 'warning' }
      },
      {
        id: 'act-s3-02',
        timestamp: '2026-09-05T10:00:00Z',
        category: 'TEST',
        title: 'Connection Test Passed',
        description: 'Point-in-time probe verified STS role delegation and PutObject permission.',
        actor: 'admin-aalok@corp.internal',
        icon: 'shield-check',
        stateBadge: { label: 'Verified', type: 'success' }
      }
    ]
  },

  // =========================================================================
  // 5. UNUSED CONNECTION (Permits Deletion)
  // =========================================================================
  'conn-unused-test-01': {
    id: 'conn-unused-test-01',
    name: 'Dev MySQL Sandbox Staging',
    description: 'Temporary developer test sandbox for initial schema conversions.',
    providerId: 'mysql',
    providerName: 'MySQL Community',
    family: 'RELATIONAL',
    environment: 'Development',
    workspaceId: 'ws-dev-sandbox',
    workspaceName: 'Developer Sandbox Workspace',
    organizationId: 'org-enterprise-emea',
    organizationName: 'Enterprise Banking EMEA',
    endpointDisplay: 'mysql-dev.sandbox.internal:3306/dev_test',
    safeRouteInfo: 'Direct Subnet (10.99.1.0/24)',
    authMethodDisplay: 'Standard Password (Direct Configured)',
    roleApplicability: 'SOURCE_AND_TARGET',
    verificationState: 'VERIFIED_POINT_IN_TIME',
    lastVerifiedAt: '2026-09-06T12:00:00Z',
    lastVerifiedDetails: 'Latency 0.9ms · MySQL 8.0.36 Community Server',
    configChangedSinceTest: false,
    lifecycleState: 'ACTIVE',
    fabric: {
      site: 'LocalDev-Lab',
      locality: 'internal-lab'
    },
    tags: ['Sandbox', 'Unused', 'Disposable'],
    createdAt: '2026-09-01T10:00:00Z',
    updatedAt: '2026-09-06T12:00:00Z',

    endpointConfig: {
      host: 'mysql-dev.sandbox.internal',
      port: 3306,
      database: 'dev_test',
      customParams: {}
    },
    authConfig: {
      authMethod: 'PASSWORD',
      username: 'dev_user',
      secretRef: 'kv/data/dev/mysql',
      secretSource: 'Direct Configured',
      isConfigured: true
    },
    tlsConfig: {
      mode: 'PREFERRED',
      minVersion: 'TLS_1_2',
      isMtlsEnabled: false
    },
    routeConfig: {
      type: 'DIRECT'
    },
    advancedSettings: {
      dnsTimeoutMs: 5000,
      connectTimeoutMs: 10000,
      socketTimeoutMs: 30000,
      tcpKeepaliveEnabled: true,
      keepaliveIdleSec: 60,
      keepaliveIntervalSec: 15
    },
    capabilities: {
      connectivityProbes: [
        { step: 'DNS_RESOLUTION', name: 'DNS Resolution', status: 'VERIFIED', latencyMs: 0.3, details: 'Resolved mysql-dev.sandbox.internal' },
        { step: 'TCP_TRANSPORT', name: 'TCP Port (3306)', status: 'VERIFIED', latencyMs: 0.6, details: 'Port reached' },
        { step: 'AUTHENTICATION', name: 'MySQL Native Password', status: 'VERIFIED', latencyMs: 0.9, details: 'Authenticated as dev_user' }
      ],
      permissionChecks: [
        { permission: 'ALL PRIVILEGES', scope: 'Database: dev_test', status: 'VERIFIED', details: 'Full privileges granted' }
      ],
      sourceCapability: { supported: true, status: 'VERIFIED', throughputRating: 'Standard', details: 'MySQL mysqldump / table scan supported.' },
      targetCapability: { supported: true, status: 'VERIFIED', acidCompliant: true, details: 'Standard InnoDB transactions.' },
      discoveryCapability: { supported: true, status: 'VERIFIED', supportedObjectTypes: ['Tables', 'Columns', 'Indexes'], details: 'Schema introspection.' },
      cdcCapability: { type: 'BINLOG', label: 'MySQL Binlog (Row-based)', status: 'VERIFIED', details: 'Binlog replication.' },
      validationCapability: { supported: true, status: 'VERIFIED', supportedLevels: ['L1 Row Count'], details: 'Validation supported.' },
      providerLimitations: [],
      proofLevel: 'UNIT_PROVEN',
      lastCheckedAt: '2026-09-06T12:00:00Z',
      configChangedSinceTest: false
    },
    usage: {
      projects: [],
      migrations: [],
      validations: [],
      activeStreamsCount: 0,
      scheduledExecutionsCount: 0,
      referenceProtection: {
        canDelete: true,
        isReferenced: false
      }
    },
    activities: [
      {
        id: 'act-un-01',
        timestamp: '2026-09-06T12:00:00Z',
        category: 'TEST',
        title: 'Connection Test Succeeded',
        description: 'Point-in-time test reached sandbox MySQL server.',
        actor: 'dev-operator',
        icon: 'shield-check',
        stateBadge: { label: 'Verified', type: 'success' }
      },
      {
        id: 'act-un-02',
        timestamp: '2026-09-01T10:00:00Z',
        category: 'LIFECYCLE',
        title: 'Connection Created',
        description: 'Created for temporary schema experimentation.',
        actor: 'dev-operator',
        icon: 'plus-circle',
        stateBadge: { label: 'Created', type: 'info' }
      }
    ]
  },

  // =========================================================================
  // 6. FAILED VERIFICATION CONNECTION
  // =========================================================================
  'conn-failed-test-01': {
    id: 'conn-failed-test-01',
    name: 'Legacy Sybase ASE Datacenter Standby',
    description: 'Decommissioned legacy Sybase instance failing network DNS resolution.',
    providerId: 'sybase',
    providerName: 'SAP ASE (Sybase)',
    family: 'RELATIONAL',
    environment: 'Disaster Recovery',
    workspaceId: 'ws-legacy-dr',
    workspaceName: 'Legacy Systems Workspace',
    organizationId: 'org-enterprise-emea',
    organizationName: 'Enterprise Banking EMEA',
    endpointDisplay: 'sybase-dr-01.legacy.corp:5000/MASTER',
    safeRouteInfo: 'Direct Subnet (10.200.1.0/24)',
    authMethodDisplay: 'Sybase Native Login',
    roleApplicability: 'SOURCE_ONLY',
    verificationState: 'VERIFICATION_FAILED',
    lastVerifiedAt: '2026-09-08T08:00:00Z',
    lastVerifiedDetails: 'Probe failed: Connection refused (TCP 5000 unreachable) · Host offline',
    verificationFailureReason: 'Network connection refused on port 5000. Remote host is unreachable or Sybase ASE service is stopped.',
    configChangedSinceTest: false,
    lifecycleState: 'ACTIVE',
    fabric: {
      site: 'London-DR-Facility',
      locality: 'uk-south-dr'
    },
    tags: ['Legacy', 'Decommissioned', 'Failed Probe'],
    createdAt: '2025-11-01T10:00:00Z',
    updatedAt: '2026-09-08T08:00:00Z',

    endpointConfig: {
      host: 'sybase-dr-01.legacy.corp',
      port: 5000,
      database: 'MASTER'
    },
    authConfig: {
      authMethod: 'PASSWORD',
      username: 'sa_akaal_probe',
      isConfigured: true
    },
    tlsConfig: {
      mode: 'DISABLED',
      minVersion: 'TLS_1_2',
      isMtlsEnabled: false
    },
    routeConfig: {
      type: 'DIRECT'
    },
    advancedSettings: {
      dnsTimeoutMs: 5000,
      connectTimeoutMs: 5000,
      socketTimeoutMs: 10000,
      tcpKeepaliveEnabled: false,
      keepaliveIdleSec: 60,
      keepaliveIntervalSec: 15
    },
    capabilities: {
      connectivityProbes: [
        { step: 'DNS_RESOLUTION', name: 'Host Resolution', status: 'VERIFIED', latencyMs: 1.2, details: 'Resolved sybase-dr-01.legacy.corp to 10.200.1.45' },
        { step: 'TCP_TRANSPORT', name: 'TCP Port (5000)', status: 'FAILED', latencyMs: 5001, details: 'Connection timed out after 5000ms. Host refused packet.' },
        { step: 'TLS_HANDSHAKE', name: 'TLS Encryption', status: 'NOT_CHECKED', details: 'Skipped due to transport failure' },
        { step: 'AUTHENTICATION', name: 'Sybase Login', status: 'NOT_CHECKED', details: 'Skipped due to transport failure' }
      ],
      permissionChecks: [],
      sourceCapability: { supported: true, status: 'UNVERIFIED', throughputRating: 'Unknown', details: 'Unverified due to offline host.' },
      targetCapability: { supported: false, status: 'UNSUPPORTED', acidCompliant: false, details: 'Source-only connection.' },
      discoveryCapability: { supported: false, status: 'UNVERIFIED', supportedObjectTypes: [], details: 'Metadata unreachable.' },
      cdcCapability: { type: 'NONE', label: 'None', status: 'UNSUPPORTED', details: 'Not configured.' },
      validationCapability: { supported: false, status: 'UNVERIFIED', supportedLevels: [], details: 'Unverified.' },
      providerLimitations: ['Server is currently unreachable.'],
      proofLevel: 'EXTERNAL_DEFERRED',
      lastCheckedAt: '2026-09-08T08:00:00Z',
      configChangedSinceTest: false
    },
    usage: {
      projects: [],
      migrations: [],
      validations: [],
      activeStreamsCount: 0,
      scheduledExecutionsCount: 0,
      referenceProtection: {
        canDelete: true,
        isReferenced: false
      }
    },
    activities: [
      {
        id: 'act-fl-01',
        timestamp: '2026-09-08T08:00:00Z',
        category: 'TEST',
        title: 'Connection Probe Failed',
        description: 'TCP Port 5000 connection timed out. Host sybase-dr-01.legacy.corp unreachable.',
        actor: 'system-probe-scheduler',
        icon: 'alert-triangle',
        stateBadge: { label: 'Failed', type: 'danger' }
      }
    ]
  }
};
