import { Injectable } from '@angular/core';
import {
  PhysicalProviderId,
  PhysicalProviderMeta,
  MigrationMode,
  MigrationModeDefinition,
  PortfolioSummaryCounters,
  MigrationAttentionItem,
  MigrationPortfolioItem,
  ActivityEventItem,
  ConnectionItem,
  RouteCompatibilityMatrix,
  ProjectItem,
  ProjectCoordinationNode,
  ProjectCoordinationEdge,
  ProjectMember,
  TopologyNode,
  TableMappingItem,
  CodeTranspilerItem,
  ConfigDomainGroup,
  ExecutionPlanViewModel,
  ReadinessCheckItem,
  ValidationItem,
  DifferenceFunnelLevel,
  SchemaDiffItem,
  PartitionHeatmapCell,
  MerkleNodeItem,
  DisputedRowItem,
  GovernedRepairPlan,
  HistoryLedgerItem,
  MultiRunComparisonMetric,
  MigrationTemplateItem
} from '../models/migration-view.models';

@Injectable({
  providedIn: 'root'
})
export class MigrationDevFixturesAdapter {

  // --------------------------------------------------------------------------
  // 1. 28 PHYSICAL PROVIDERS CATALOG
  // --------------------------------------------------------------------------
  public getPhysicalProviders(): PhysicalProviderMeta[] {
    return [
      // Relational (7)
      { id: 'Oracle', name: 'Oracle Database', category: 'RELATIONAL', defaultPort: 1521, icon: 'database', description: 'Enterprise RDBMS with LogMiner CDC and TNS descriptors.', supportedModes: ['M1_BULK', 'M2_BULK_CDC', 'M3_CDC', 'M4_INCREMENTAL', 'M5_STATE_SYNC', 'M6_SCHEMA_ONLY', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['LOGMINER_CDC', 'DIRECT_PATH_LOAD', 'TABLE_PARTITIONING', 'LOB_CHUNKING'] },
      { id: 'PostgreSQL', name: 'PostgreSQL', category: 'RELATIONAL', defaultPort: 5432, icon: 'database', description: 'Advanced open-source relational database with logical replication.', supportedModes: ['M1_BULK', 'M2_BULK_CDC', 'M3_CDC', 'M4_INCREMENTAL', 'M5_STATE_SYNC', 'M6_SCHEMA_ONLY', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['WAL_LOGICAL_REPLICATION', 'COPY_BINARY_STREAM', 'PARTITION_ROUTING', 'JSONB_OPTIMIZATION'] },
      { id: 'MySQL', name: 'MySQL', category: 'RELATIONAL', defaultPort: 3306, icon: 'database', description: 'Web-scale open-source relational engine with binlog CDC.', supportedModes: ['M1_BULK', 'M2_BULK_CDC', 'M3_CDC', 'M4_INCREMENTAL', 'M5_STATE_SYNC', 'M6_SCHEMA_ONLY', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['BINLOG_ROW_CAPTURE', 'LOAD_DATA_LOCAL', 'INVISIBLE_INDEXES'] },
      { id: 'Microsoft SQL Server', name: 'Microsoft SQL Server', category: 'RELATIONAL', defaultPort: 1433, icon: 'server', description: 'Enterprise relational engine with SQL Server CDC and BCP.', supportedModes: ['M1_BULK', 'M2_BULK_CDC', 'M3_CDC', 'M4_INCREMENTAL', 'M5_STATE_SYNC', 'M6_SCHEMA_ONLY', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['MSSQL_CDC_CAPTURE', 'BCP_FAST_LOAD', 'CHANGE_TRACKING'] },
      { id: 'MariaDB', name: 'MariaDB', category: 'RELATIONAL', defaultPort: 3306, icon: 'database', description: 'Community-developed fork of MySQL with Galera cluster support.', supportedModes: ['M1_BULK', 'M2_BULK_CDC', 'M3_CDC', 'M4_INCREMENTAL', 'M5_STATE_SYNC', 'M6_SCHEMA_ONLY', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['BINLOG_ROW_CAPTURE', 'LOAD_DATA_LOCAL', 'SEQUENCE_OBJECTS'] },
      { id: 'SQLite', name: 'SQLite', category: 'RELATIONAL', icon: 'database', description: 'Self-contained zero-configuration transactional SQL database engine.', supportedModes: ['M1_BULK', 'M4_INCREMENTAL', 'M6_SCHEMA_ONLY', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['DIRECT_FILE_ATTACH', 'TRANSACTIONAL_LOCKING'] },
      { id: 'IBM Db2', name: 'IBM Db2 LUW', category: 'RELATIONAL', defaultPort: 50000, icon: 'hard-drive', description: 'Enterprise multi-workload database management system with DATA CAPTURE CHANGES.', supportedModes: ['M1_BULK', 'M2_BULK_CDC', 'M3_CDC', 'M4_INCREMENTAL', 'M5_STATE_SYNC', 'M6_SCHEMA_ONLY', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['DATA_CAPTURE_CHANGES', 'LOAD_CLIENT_STREAM', 'RANGE_PARTITIONS'] },
      
      // Warehouses / Lakehouses (4)
      { id: 'Snowflake', name: 'Snowflake Data Cloud', category: 'WAREHOUSE', defaultPort: 443, icon: 'snowflake', description: 'Elastic cloud data platform with Snowpipe streaming.', supportedModes: ['M1_BULK', 'M2_BULK_CDC', 'M3_CDC', 'M4_INCREMENTAL', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['STAGE_BULK_COPY', 'SNOWPIPE_STREAMING', 'MICRO_PARTITIONING', 'TIME_TRAVEL'] },
      { id: 'Google BigQuery', name: 'Google BigQuery', category: 'WAREHOUSE', defaultPort: 443, icon: 'search', description: 'Serverless enterprise data warehouse with Storage Write API.', supportedModes: ['M1_BULK', 'M2_BULK_CDC', 'M3_CDC', 'M4_INCREMENTAL', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['STORAGE_WRITE_API', 'AVRO_BATCH_LOAD', 'PARTITION_EXPIRATION'] },
      { id: 'Amazon Redshift', name: 'Amazon Redshift', category: 'WAREHOUSE', defaultPort: 5439, icon: 'layers', description: 'Fast, petabyte-scale cloud data warehouse.', supportedModes: ['M1_BULK', 'M2_BULK_CDC', 'M4_INCREMENTAL', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['S3_MANIFEST_COPY', 'SORTKEY_DISTKEY_DDL', 'AUTO_VACUUM'] },
      { id: 'Databricks / Delta Lake', name: 'Databricks / Delta Lake', category: 'WAREHOUSE', defaultPort: 443, icon: 'layers', description: 'Open-source storage framework with ACID transactions on Apache Spark.', supportedModes: ['M1_BULK', 'M2_BULK_CDC', 'M3_CDC', 'M4_INCREMENTAL', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['DELTA_TABLE_STREAM', 'CHANGE_DATA_FEED', 'PARQUET_COMPACTION'] },

      // NoSQL / Graph / Search (8)
      { id: 'MongoDB', name: 'MongoDB', category: 'NOSQL_GRAPH_SEARCH', defaultPort: 27017, icon: 'leaf', description: 'Document-oriented database with Change Streams via replica set oplog.', supportedModes: ['M1_BULK', 'M2_BULK_CDC', 'M3_CDC', 'M4_INCREMENTAL', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['CHANGE_STREAMS_OPLOG', 'BULK_WRITE_OPS', 'SHARDED_CLUSTER_CURSOR'] },
      { id: 'Apache Cassandra', name: 'Apache Cassandra', category: 'NOSQL_GRAPH_SEARCH', defaultPort: 9042, icon: 'grid', description: 'Distributed wide-column store designed for massive scalability.', supportedModes: ['M1_BULK', 'M4_INCREMENTAL', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['SSTABLE_DIRECT_STREAM', 'CQL_PAGINATION', 'CONSISTENCY_LEVELS'] },
      { id: 'ScyllaDB', name: 'ScyllaDB', category: 'NOSQL_GRAPH_SEARCH', defaultPort: 9042, icon: 'zap', description: 'C++ rewrite of Cassandra with shard-per-core architecture.', supportedModes: ['M1_BULK', 'M2_BULK_CDC', 'M3_CDC', 'M4_INCREMENTAL', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['SCYLLA_CDC_LOG', 'LOW_LATENCY_STREAM', 'CQL_PAGINATION'] },
      { id: 'Neo4j', name: 'Neo4j Graph Database', category: 'NOSQL_GRAPH_SEARCH', defaultPort: 7687, icon: 'share-2', description: 'Native graph database with Cypher query language.', supportedModes: ['M1_BULK', 'M4_INCREMENTAL', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['BOLT_PROTOCOL', 'GRAPH_IMPORT_TOOL', 'CYPHER_PARAMETER_UNWIND'] },
      { id: 'Redis', name: 'Redis', category: 'NOSQL_GRAPH_SEARCH', defaultPort: 6379, icon: 'zap', description: 'In-memory data structure store with keyspace notifications.', supportedModes: ['M1_BULK', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['PIPELINE_EXEC', 'RDB_RESTORE', 'KEYSPACE_EVENTS'] },
      { id: 'KeyDB', name: 'KeyDB', category: 'NOSQL_GRAPH_SEARCH', defaultPort: 6379, icon: 'key', description: 'Multithreaded drop-in alternative to Redis with active replication.', supportedModes: ['M1_BULK', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['MULTI_THREAD_PIPELINE', 'FLASH_STORAGE'] },
      { id: 'Elasticsearch', name: 'Elasticsearch', category: 'NOSQL_GRAPH_SEARCH', defaultPort: 9200, icon: 'search', description: 'Distributed search and analytics engine.', supportedModes: ['M1_BULK', 'M4_INCREMENTAL', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['BULK_INDEX_API', 'SCROLL_SEARCH', 'INDEX_ALIASES'] },
      { id: 'OpenSearch', name: 'OpenSearch', category: 'NOSQL_GRAPH_SEARCH', defaultPort: 9200, icon: 'search', description: 'Community-driven search and analytics suite.', supportedModes: ['M1_BULK', 'M4_INCREMENTAL', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['BULK_INDEX_API', 'POINT_IN_TIME_SEARCH'] },

      // Streaming (4)
      { id: 'Apache Kafka', name: 'Apache Kafka', category: 'STREAMING', defaultPort: 9092, icon: 'radio', description: 'Distributed event streaming platform with partition-level ordering.', supportedModes: ['M3_CDC', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['EXACTLY_ONCE_PRODUCER', 'SCHEMA_REGISTRY_AVRO', 'CONSUMER_GROUPS'] },
      { id: 'Amazon Kinesis', name: 'Amazon Kinesis Data Streams', category: 'STREAMING', defaultPort: 443, icon: 'activity', description: 'Scalable and durable real-time data streaming service.', supportedModes: ['M3_CDC', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['ENHANCED_FAN_OUT', 'SHARD_ITERATOR'] },
      { id: 'Azure Event Hubs', name: 'Azure Event Hubs', category: 'STREAMING', defaultPort: 5671, icon: 'radio', description: 'Fully managed real-time data ingestion service.', supportedModes: ['M3_CDC', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['KAFKA_COMPATIBILITY', 'CAPTURE_TO_BLOB'] },
      { id: 'Google Cloud Pub/Sub', name: 'Google Cloud Pub/Sub', category: 'STREAMING', defaultPort: 443, icon: 'send', description: 'Asynchronous global messaging service.', supportedModes: ['M3_CDC', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['ORDERING_KEYS', 'EXACTLY_ONCE_DELIVERY'] },

      // Storage (5)
      { id: 'Amazon S3', name: 'Amazon S3 Object Storage', category: 'STORAGE', defaultPort: 443, icon: 'archive', description: 'Scalable cloud object storage with multipart uploads.', supportedModes: ['M1_BULK', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['MULTIPART_PARALLEL', 'PARQUET_ORC_AVRO', 'S3_SELECT'] },
      { id: 'Google Cloud Storage', name: 'Google Cloud Storage', category: 'STORAGE', defaultPort: 443, icon: 'cloud', description: 'Unified object storage for developers and enterprises.', supportedModes: ['M1_BULK', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['RESUMABLE_UPLOAD', 'COMPOSITE_OBJECTS'] },
      { id: 'Azure Blob Storage', name: 'Azure Blob Storage', category: 'STORAGE', defaultPort: 443, icon: 'box', description: 'Massively scalable object storage for unstructured data.', supportedModes: ['M1_BULK', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['BLOCK_BLOB_COMMIT', 'IMMUTABLE_STORAGE'] },
      { id: 'MinIO', name: 'MinIO Object Storage', category: 'STORAGE', defaultPort: 9000, icon: 'server', description: 'High-performance S3-compatible enterprise object storage.', supportedModes: ['M1_BULK', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['S3_API_V4', 'MULTIPART_STREAM'] },
      { id: 'Apache HDFS', name: 'Hadoop Distributed File System', category: 'STORAGE', defaultPort: 9000, icon: 'folder-tree', description: 'Distributed file system designed to run on commodity hardware.', supportedModes: ['M1_BULK', 'M7_DATA_ONLY'], isSourceSupported: true, isTargetSupported: true, capabilities: ['WEBHDFS_REST', 'BLOCK_APPEND', 'KERBEROS_AUTH'] }
    ];
  }

  // --------------------------------------------------------------------------
  // 2. 7 CREATION EXECUTION MODES
  // --------------------------------------------------------------------------
  public getExecutionModes(): MigrationModeDefinition[] {
    return [
      {
        id: 'M1_BULK',
        code: 'M1',
        title: 'Bulk Migration',
        badge: 'Bulk Snapshot',
        shortDesc: 'Parallel table snapshot extraction and streaming. Optimized for initial seeds and static operational tables without CDC.',
        detailedImpact: 'High throughput parallel worker pipelines. No transaction log tailing. Best for offline windows, read-only data, and cold migrations.',
        scopeTag: 'Snapshot Only',
        slaExpectation: 'Scheduled Window',
        requiredCapabilities: ['TABLE_PARTITIONING', 'DIRECT_PATH_LOAD']
      },
      {
        id: 'M2_BULK_CDC',
        code: 'M2',
        title: 'Bulk + CDC',
        badge: 'Zero-Downtime',
        shortDesc: 'Complete zero-downtime standard enterprise migration. Takes initial snapshot while tailing transaction logs, then streams delta.',
        detailedImpact: 'Captures full baseline while spooling ongoing transactions into memory ring buffers. Catches up delta stream until cutover barrier.',
        scopeTag: 'Full + Stream',
        slaExpectation: 'Zero Downtime (<1s lag)',
        requiredCapabilities: ['LOGMINER_CDC', 'WAL_LOGICAL_REPLICATION', 'BINLOG_ROW_CAPTURE']
      },
      {
        id: 'M3_CDC',
        code: 'M3',
        title: 'CDC Only',
        badge: 'Continuous Replication',
        shortDesc: 'Continuous Change Data Capture stream ingestion from active transaction logs. Assumes target is already initialized.',
        detailedImpact: 'No initial snapshot phase. Immediately hooks into SCN/LSN bookmarks and streams row mutations directly to target tables or topics.',
        scopeTag: 'Stream Only',
        slaExpectation: 'Sub-second Continuous Lag',
        requiredCapabilities: ['LOGMINER_CDC', 'WAL_LOGICAL_REPLICATION']
      },
      {
        id: 'M4_INCREMENTAL',
        code: 'M4',
        title: 'Incremental Query',
        badge: 'Watermark Polling',
        shortDesc: 'Periodic delta extraction driven by high-watermark columns (timestamp or sequential identity) with lookback overlap.',
        detailedImpact: 'Polls source using indexed watermark expressions. Does not require database superuser log-tailing privileges. Handles soft deletes via predicates.',
        scopeTag: 'Watermark Sync',
        slaExpectation: 'Micro-batch (seconds to minutes)',
        requiredCapabilities: ['INDEXED_QUERIES', 'TIMEZONE_COERCION']
      },
      {
        id: 'M5_STATE_SYNC',
        code: 'M5',
        title: 'State Synchronization',
        badge: 'Merkle Differential',
        shortDesc: 'Differential comparison using hierarchical XXHash64 Merkle trees to detect and reconcile silent drift without full scans.',
        detailedImpact: 'Generates partitioned state fingerprints on both engines, localizes mismatch boundaries, and applies delta repairs without re-streaming unchanged rows.',
        scopeTag: 'Differential Sync',
        slaExpectation: 'On-Demand Drift Reconciliation',
        requiredCapabilities: ['HASH_AGGREGATION', 'MERKLE_TREE_CALC']
      },
      {
        id: 'M6_SCHEMA_ONLY',
        code: 'M6',
        title: 'Schema Only',
        badge: 'DDL Evolution',
        shortDesc: 'Topological extraction, translation, and transactional execution of schemas, constraints, indexes, views, and stored procedures with zero rows.',
        detailedImpact: 'Resolves cyclic foreign key dependencies, defers non-unique indexes, and prepares target database schema structures cleanly.',
        scopeTag: 'DDL Objects Only',
        slaExpectation: 'Immediate Schema Prep',
        requiredCapabilities: ['METADATA_DISCOVERY', 'DDL_TRANSPILATION']
      },
      {
        id: 'M7_DATA_ONLY',
        code: 'M7',
        title: 'Data Only',
        badge: 'Direct Transport',
        shortDesc: 'High-throughput binary row movement into existing matching target schemas with table structures pre-created.',
        detailedImpact: 'Bypasses DDL creation and foreign key overhead. Focuses strictly on maximum network IOPS and zero-copy binary streaming.',
        scopeTag: 'Raw Data Movement',
        slaExpectation: 'Maximum Network IOPS',
        requiredCapabilities: ['COPY_BINARY_STREAM', 'BULK_WRITE_OPS']
      }
    ];
  }

  // --------------------------------------------------------------------------
  // 3. PORTFOLIO DEMO PRESENTATION FIXTURES
  // --------------------------------------------------------------------------
  public getSummaryCounters(): PortfolioSummaryCounters {
    return {
      total: 5,
      active: 2,
      scheduled: 1,
      attentionRequired: 1,
      completed: 1,
      failedInterrupted: 0,
      archived: 0
    };
  }

  public getAttentionItems(): MigrationAttentionItem[] {
    return [
      {
        id: 'att-1',
        migrationId: 'mig-002',
        migrationName: 'Core Banking Ledger (Oracle → PostgreSQL)',
        severity: 'ACTION_REQUIRED',
        title: 'Cutover Approval Barrier Reached',
        description: 'CDC replication lag is 12ms (within SLA). Cutover barrier requires 2 L4 operator sign-offs before source quiesce.',
        actionLabel: 'Review & Authorize',
        actionType: 'APPROVE',
        targetTab: 'governance',
        timestamp: '4 min ago'
      }
    ];
  }

  public getPortfolioMigrations(): MigrationPortfolioItem[] {
    return [
      {
        id: 'mig-001',
        name: 'Enterprise Customer Data Hub',
        projectId: 'proj-01',
        projectName: 'Cloud Modernization 2026',
        sourceEngine: 'Oracle',
        sourceInstance: 'ora-cluster-01.prod:1521',
        targetEngine: 'PostgreSQL',
        targetInstance: 'aurora-pg-01.aws:5432',
        mode: 'M1_BULK',
        environment: 'Production',
        lifecycleState: 'RUNNING',
        currentStage: 'Streaming Partition Batch 42/64',
        progressPercent: 62,
        throughputRowsSec: 88400,
        etaString: '14m remaining',
        health: 'HEALTHY',
        attentionCount: 0,
        requiresApproval: false,
        planVersion: 'v1.4.0',
        planFingerprint: 'sha256:7f9a2b8e3c1d4a5f',
        updatedAt: 'Just now'
      },
      {
        id: 'mig-002',
        name: 'Core Banking Ledger & Settlements',
        projectId: 'proj-01',
        projectName: 'Cloud Modernization 2026',
        sourceEngine: 'Oracle',
        sourceInstance: 'ora-rac-core.corp:1521',
        targetEngine: 'PostgreSQL',
        targetInstance: 'aurora-pg-core.aws:5432',
        mode: 'M2_BULK_CDC',
        environment: 'Production',
        lifecycleState: 'GOVERNANCE_PENDING',
        currentStage: 'CDC Steady-State Lag 12ms',
        progressPercent: 94,
        throughputRowsSec: 12400,
        cdcLagMs: 12,
        etaString: 'Ready for cutover',
        health: 'WARNING',
        attentionCount: 1,
        requiresApproval: true,
        activeBarrierId: 'barr-cutover-01',
        planVersion: 'v2.1.0',
        planFingerprint: 'sha256:3d1e9f8a7b6c5d4e',
        updatedAt: '2 min ago'
      },
      {
        id: 'mig-003',
        name: 'Real-Time Fraud Telemetry Stream',
        sourceEngine: 'MySQL',
        sourceInstance: 'mysql-fraud-rw.internal:3306',
        targetEngine: 'Apache Kafka',
        targetInstance: 'kafka-cluster.prod:9092',
        mode: 'M3_CDC',
        environment: 'Production',
        lifecycleState: 'ACTIVE',
        currentStage: 'Tailing Binlog Stream',
        progressPercent: 100,
        cdcLagMs: 4,
        etaString: 'Continuous',
        health: 'HEALTHY',
        attentionCount: 0,
        requiresApproval: false,
        planVersion: 'v1.0.2',
        planFingerprint: 'sha256:1a2b3c4d5e6f7a8b',
        updatedAt: 'Just now'
      },
      {
        id: 'mig-004',
        name: 'Merchant Settlement Watermark Sync',
        projectId: 'proj-02',
        projectName: 'Payments Analytics Pipeline',
        sourceEngine: 'Microsoft SQL Server',
        sourceInstance: 'mssql-settle.prod:1433',
        targetEngine: 'Snowflake',
        targetInstance: 'org-xy12345.snowflakecomputing.com',
        mode: 'M4_INCREMENTAL',
        environment: 'Staging',
        lifecycleState: 'INITIALIZED',
        currentStage: 'Waiting for scheduled window',
        progressPercent: 0,
        watermarkTimestamp: '2026-08-28 12:00:00 UTC',
        etaString: 'Starts at 02:00 UTC',
        health: 'HEALTHY',
        attentionCount: 0,
        requiresApproval: false,
        planVersion: 'v1.1.0',
        planFingerprint: 'sha256:9f8e7d6c5b4a3a2b',
        updatedAt: '1 hour ago'
      },
      {
        id: 'mig-005',
        name: 'Legacy Product Catalog DDL Schema',
        sourceEngine: 'IBM Db2',
        sourceInstance: 'db2-catalog.internal:50000',
        targetEngine: 'PostgreSQL',
        targetInstance: 'pg-catalog.aws:5432',
        mode: 'M6_SCHEMA_ONLY',
        environment: 'Development',
        lifecycleState: 'COMPLETED',
        currentStage: 'All 248 DDL objects executed',
        progressPercent: 100,
        objectsCompletedCount: 248,
        objectsTotalCount: 248,
        etaString: 'Complete',
        health: 'HEALTHY',
        attentionCount: 0,
        requiresApproval: false,
        planVersion: 'v1.0.0',
        planFingerprint: 'sha256:4a5b6c7d8e9f0a1b',
        updatedAt: '3 hours ago'
      }
    ];
  }

  public getActivityEvents(): ActivityEventItem[] {
    return [
      {
        id: 'act-1',
        timestamp: '12 min ago',
        type: 'APPROVAL_GRANTED',
        title: 'Cutover Barrier Approved by SecOps',
        description: 'Operator M. Vance (SecOps Lead) authorized cutover barrier for Core Banking Ledger.',
        migrationId: 'mig-002',
        migrationName: 'Core Banking Ledger',
        operator: 'M. Vance (L4)',
        severity: 'SUCCESS'
      },
      {
        id: 'act-2',
        timestamp: '1 hour ago',
        type: 'CERTIFIED',
        title: 'Validation Certification Issued',
        description: 'Post-migration verification run for Settlement Batches certified with 0 cell differences.',
        migrationId: 'mig-001',
        migrationName: 'Enterprise Customer Data Hub',
        operator: 'Automated Gate',
        severity: 'SUCCESS'
      }
    ];
  }

  // --------------------------------------------------------------------------
  // 4. CONNECTIONS VAULT PRESENTATION FIXTURES
  // --------------------------------------------------------------------------
  public getConnections(): ConnectionItem[] {
    return [
      {
        id: 'conn-01',
        name: 'Oracle 19c Enterprise RAC',
        provider: 'Oracle',
        category: 'RELATIONAL',
        environment: 'Production',
        host: 'ora-rac-cluster.prod.internal',
        port: 1521,
        databaseName: 'ORCLPDB',
        username: 'akaal_repl_user',
        secretRef: 'vault://secret/prod/oracle/akaal_repl',
        tlsEnabled: true,
        networkRoute: 'SSH_BASTION',
        bastionHost: 'bastion-ap-south.corp.internal',
        status: 'CONNECTED',
        verificationFreshness: 'Verified 4 min ago',
        latencyMs: 2.1,
        capabilities: ['LOGMINER_CDC', 'TABLE_PARTITIONING', 'DIRECT_PATH_LOAD', 'LOB_CHUNKING'],
        assignedMigrationCount: 3,
        assignedProjectCount: 2,
        createdAt: '2026-08-01T10:00:00Z',
        updatedAt: '2026-08-28T09:00:00Z',
        probeStages: [
          { stage: 'NETWORK', label: 'TCP Network Route', status: 'PASSED', detail: 'Connected via SSH Bastion at bastion-ap-south (2.1ms RTT)', latencyMs: 2.1 },
          { stage: 'TLS', label: 'TLS 1.3 Cryptographic Handshake', status: 'PASSED', detail: 'Cipher suite TLS_AES_256_GCM_SHA384 verified' },
          { stage: 'AUTHENTICATION', label: 'Vault Secret Authentication', status: 'PASSED', detail: 'Authenticated as akaal_repl_user' },
          { stage: 'IDENTITY', label: 'Instance Identity & Version', status: 'PASSED', detail: 'Oracle Database 19c Enterprise Edition Release 19.18.0.0.0' },
          { stage: 'PERMISSIONS', label: 'Privilege Authorization Matrix', status: 'PASSED', detail: 'SELECT ANY TABLE, EXECUTE ON DBMS_LOGMNR, LOGSTDBY' },
          { stage: 'PREREQUISITES', label: 'Supplemental Logging', status: 'PASSED', detail: 'Database supplemental logging active (ALL COLUMNS)' },
          { stage: 'CAPABILITIES', label: 'Engine Capabilities', status: 'PASSED', detail: 'Verified 4 native capabilities' }
        ]
      },
      {
        id: 'conn-02',
        name: 'AWS Aurora PostgreSQL Cluster',
        provider: 'PostgreSQL',
        category: 'RELATIONAL',
        environment: 'Production',
        host: 'aurora-pg-cluster.aws.internal',
        port: 5432,
        databaseName: 'banking_ledger',
        username: 'akaal_applier',
        secretRef: 'vault://secret/prod/postgres/applier',
        tlsEnabled: true,
        networkRoute: 'PRIVATE_ENDPOINT',
        privateEndpointId: 'vpce-0a1b2c3d4e5f6g7h8',
        status: 'CONNECTED',
        verificationFreshness: 'Verified 8 min ago',
        latencyMs: 1.4,
        capabilities: ['WAL_LOGICAL_REPLICATION', 'COPY_BINARY_STREAM', 'DEFERRED_CONSTRAINTS', 'JSONB_STORAGE'],
        assignedMigrationCount: 4,
        assignedProjectCount: 2,
        createdAt: '2026-08-01T11:00:00Z',
        updatedAt: '2026-08-28T09:00:00Z',
        probeStages: [
          { stage: 'NETWORK', label: 'AWS VPC Endpoint Handshake', status: 'PASSED', detail: 'Connected via vpce-0a1b2c3d4e5f6g7h8 (1.4ms RTT)', latencyMs: 1.4 },
          { stage: 'TLS', label: 'mTLS Handshake', status: 'PASSED', detail: 'Client certificate valid (Issuer: Corp Internal CA)' },
          { stage: 'AUTHENTICATION', label: 'Vault Secret Authentication', status: 'PASSED', detail: 'Authenticated as akaal_applier' },
          { stage: 'IDENTITY', label: 'PostgreSQL Version', status: 'PASSED', detail: 'PostgreSQL 16.2 (Aurora 16.2.0)' },
          { stage: 'PERMISSIONS', label: 'Superuser / RDS Replication Role', status: 'PASSED', detail: 'rds_replication, rds_superuser active' },
          { stage: 'PREREQUISITES', label: 'WAL Level Verification', status: 'PASSED', detail: 'wal_level = logical, max_replication_slots = 32' },
          { stage: 'CAPABILITIES', label: 'Engine Capabilities', status: 'PASSED', detail: 'Verified 4 native capabilities' }
        ]
      },
      {
        id: 'conn-03',
        name: 'Snowflake Enterprise Data Lake',
        provider: 'Snowflake',
        category: 'WAREHOUSE',
        environment: 'Production',
        host: 'org-xy12345.snowflakecomputing.com',
        port: 443,
        databaseName: 'ANALYTICS_PROD',
        username: 'akaal_loader',
        secretRef: 'vault://secret/prod/snowflake/loader',
        tlsEnabled: true,
        networkRoute: 'DIRECT',
        status: 'CONNECTED',
        verificationFreshness: 'Verified 15 min ago',
        latencyMs: 18.5,
        capabilities: ['STAGE_BULK_COPY', 'SNOWPIPE_STREAMING', 'MICRO_PARTITIONING'],
        assignedMigrationCount: 2,
        assignedProjectCount: 1,
        createdAt: '2026-08-10T14:00:00Z',
        updatedAt: '2026-08-28T08:00:00Z'
      },
      {
        id: 'conn-04',
        name: 'Kafka Event Bus (Core Stream)',
        provider: 'Apache Kafka',
        category: 'STREAMING',
        environment: 'Production',
        host: 'kafka-broker-01.prod.internal',
        port: 9092,
        username: 'akaal_producer',
        secretRef: 'vault://secret/prod/kafka/producer',
        tlsEnabled: true,
        networkRoute: 'PRIVATE_ENDPOINT',
        status: 'CONNECTED',
        verificationFreshness: 'Verified 30 min ago',
        latencyMs: 3.2,
        capabilities: ['EXACTLY_ONCE_PRODUCER', 'SCHEMA_REGISTRY_AVRO'],
        assignedMigrationCount: 1,
        assignedProjectCount: 1,
        createdAt: '2026-08-15T09:00:00Z',
        updatedAt: '2026-08-28T07:00:00Z'
      }
    ];
  }

  // --------------------------------------------------------------------------
  // 5. PROJECTS & WORKSPACES FIXTURES
  // --------------------------------------------------------------------------
  public getProjects(): ProjectItem[] {
    return [
      {
        id: 'proj-01',
        key: 'MOD-2026',
        name: 'Cloud Modernization 2026',
        description: 'Core banking and customer database migration from on-prem Oracle RAC to AWS Aurora PostgreSQL.',
        defaultEnvironment: 'Production',
        owner: 'Aalok Ladwa',
        targetMilestone: 'Q3 2026 — Final Cutover',
        health: 'HEALTHY',
        migrationIds: ['mig-001', 'mig-002'],
        activeMigrationsCount: 2,
        attentionCount: 1,
        scheduledCount: 0,
        membersCount: 8,
        progressPercent: 78,
        createdAt: '2026-07-01T00:00:00Z',
        updatedAt: '2026-08-28T10:00:00Z'
      },
      {
        id: 'proj-02',
        key: 'ANALYTICS',
        name: 'Payments Analytics Pipeline',
        description: 'Continuous ingestion and incremental sync from transactional SQL Server to Snowflake Lakehouse.',
        defaultEnvironment: 'Production',
        owner: 'Sarah Chen (Data Platform)',
        targetMilestone: 'Q4 2026 — Analytics Go-Live',
        health: 'HEALTHY',
        migrationIds: ['mig-004'],
        activeMigrationsCount: 0,
        attentionCount: 0,
        scheduledCount: 1,
        membersCount: 5,
        progressPercent: 30,
        createdAt: '2026-08-01T00:00:00Z',
        updatedAt: '2026-08-28T08:00:00Z'
      }
    ];
  }

  public getProjectCoordination(projectId: string): { nodes: ProjectCoordinationNode[]; edges: ProjectCoordinationEdge[] } {
    return {
      nodes: [
        { id: 'mig-001', migrationId: 'mig-001', name: 'Enterprise Customer Data Hub', mode: 'M1_BULK', status: 'RUNNING', progress: 62 },
        { id: 'mig-002', migrationId: 'mig-002', name: 'Core Banking Ledger & Settlements', mode: 'M2_BULK_CDC', status: 'GOVERNANCE_PENDING', progress: 94 }
      ],
      edges: [
        { id: 'e1', source: 'mig-001', target: 'mig-002', relationship: 'MUST_COMPLETE_BEFORE', isSatisfied: false }
      ]
    };
  }

  public getProjectMembers(projectId: string): ProjectMember[] {
    return [
      { id: 'usr-1', name: 'Aalok Ladwa', email: 'aalok@corp.internal', principalType: 'USER', roles: ['Project Lead', 'Migration Author'], effectiveGrants: ['MIGRATION_CREATE', 'CONFIG_OVERRIDE', 'CUTOVER_REQUEST'], soDConflicts: [] },
      { id: 'usr-2', name: 'M. Vance', email: 'm.vance@corp.internal', principalType: 'USER', roles: ['SecOps Lead', 'L4 Approver'], effectiveGrants: ['CUTOVER_APPROVE', 'GOVERNED_REPAIR_AUTHORIZE'], soDConflicts: [] },
      { id: 'grp-1', name: 'DBA Platform Operations', email: 'dba-team@corp.internal', principalType: 'DIRECTORY_GROUP', roles: ['Operator Tier 3'], effectiveGrants: ['WORKER_SCALE', 'PAUSE_RESUME', 'RECOVERY_TRIGGER'], soDConflicts: [] }
    ];
  }

  // --------------------------------------------------------------------------
  // 6. STEP 4 — DISCOVERY TOPOLOGY FIXTURES
  // --------------------------------------------------------------------------
  public getTopologyTree(provider: PhysicalProviderId): TopologyNode[] {
    if (provider === 'Oracle') {
      return [
        {
          id: 'schema-sct',
          label: 'SCT_DEMO',
          type: 'SCHEMA',
          objectCount: 24,
          estimatedRows: 52400000,
          estimatedSizeBytes: 42949672960,
          isSelected: true,
          children: [
            {
              id: 'grp-tables',
              label: 'Tables (18)',
              type: 'OBJECT_GROUP',
              objectCount: 18,
              isSelected: true,
              children: [
                { id: 'tbl-cust', label: 'CUSTOMERS', type: 'TABLE', estimatedRows: 14200000, estimatedSizeBytes: 8589934592, isSelected: true },
                { id: 'tbl-acc', label: 'ACCOUNTS', type: 'TABLE', estimatedRows: 18600000, estimatedSizeBytes: 12884901888, isSelected: true },
                { id: 'tbl-tx', label: 'TRANSACTIONS', type: 'TABLE', estimatedRows: 16800000, estimatedSizeBytes: 17179869184, isSelected: true },
                { id: 'tbl-audit', label: 'AUDIT_LOGS', type: 'TABLE', estimatedRows: 2800000, estimatedSizeBytes: 4294967296, isSelected: true }
              ]
            },
            {
              id: 'grp-procs',
              label: 'Stored Procedures & Functions (6)',
              type: 'OBJECT_GROUP',
              objectCount: 6,
              isSelected: true,
              children: [
                { id: 'proc-settle', label: 'P_SETTLE_ACCOUNTS', type: 'OBJECT_GROUP', isSelected: true },
                { id: 'proc-sub', label: 'P_SUBTYPE_003', type: 'OBJECT_GROUP', isSelected: true },
                { id: 'fn-calc', label: 'FN_CALCULATE_FEE', type: 'OBJECT_GROUP', isSelected: true }
              ]
            }
          ]
        }
      ];
    }
    return [
      {
        id: 'db-public',
        label: 'public',
        type: 'SCHEMA',
        objectCount: 12,
        isSelected: true,
        children: [
          { id: 'tbl-users', label: 'users', type: 'TABLE', estimatedRows: 500000, isSelected: true },
          { id: 'tbl-orders', label: 'orders', type: 'TABLE', estimatedRows: 2500000, isSelected: true }
        ]
      }
    ];
  }

  // --------------------------------------------------------------------------
  // 7. STEP 5 — TABLE & COLUMN MAPPING & SCT WORKBENCH FIXTURES
  // --------------------------------------------------------------------------
  public getTableMapping(): TableMappingItem {
    return {
      id: 'map-acc',
      sourceSchema: 'SCT_DEMO',
      sourceTable: 'ACCOUNTS',
      targetSchema: 'public',
      targetTable: 'accounts',
      columnsCount: 5,
      mappedColumnsCount: 5,
      isComplete: true,
      piiRulesCount: 1,
      dedupEnabled: true,
      dedupCandidateKeys: ['account_id'],
      dedupSurvivorRule: 'LATEST_TIMESTAMP',
      preOperationHookSql: '-- Prepare partition index\nSET maintenance_work_mem = "4GB";',
      postOperationHookSql: 'VACUUM ANALYZE public.accounts;',
      conflictPolicy: 'OVERWRITE',
      columns: [
        { id: 'col-1', sourceColumn: 'ACCOUNT_ID', sourceType: 'NUMBER(18)', targetColumn: 'account_id', targetType: 'BIGINT', isPrimaryKey: true, isForeignKey: false, isNullable: false, status: 'MAPPED' },
        { id: 'col-2', sourceColumn: 'CUSTOMER_ID', sourceType: 'NUMBER(18)', targetColumn: 'customer_id', targetType: 'BIGINT', isPrimaryKey: false, isForeignKey: true, isNullable: false, status: 'MAPPED' },
        { id: 'col-3', sourceColumn: 'SSN_NO', sourceType: 'VARCHAR2(11)', targetColumn: 'ssn_masked', targetType: 'TEXT', isPrimaryKey: false, isForeignKey: false, isNullable: true, piiSensitivity: 'SSN', piiMaskingPolicy: 'FORMAT_PRESERVING_REDACT', status: 'MAPPED' },
        { id: 'col-4', sourceColumn: 'BALANCE', sourceType: 'NUMBER(12,2)', targetColumn: 'balance', targetType: 'NUMERIC(12,2)', isPrimaryKey: false, isForeignKey: false, isNullable: false, status: 'MAPPED' },
        { id: 'col-5', sourceColumn: 'UPDATED_AT', sourceType: 'TIMESTAMP(6)', targetColumn: 'updated_at', targetType: 'TIMESTAMPTZ', isPrimaryKey: false, isForeignKey: false, isNullable: false, status: 'MAPPED' }
      ]
    };
  }

  public getCodeTranspilerItems(): CodeTranspilerItem[] {
    return [
      {
        id: 'sct-1',
        schema: 'SCT_DEMO',
        name: 'P_SUBTYPE_003',
        objectType: 'PROCEDURE',
        sourceLanguage: 'Oracle PL/SQL',
        targetLanguage: 'PostgreSQL PL/pgSQL',
        conversionStatus: 'CONVERSION_PROPOSED',
        parametersCount: 3,
        complexityScore: 4,
        sourceSql: `CREATE OR REPLACE PROCEDURE P_SUBTYPE_003 (
    p_account_id IN NUMBER,
    p_amount     IN NUMBER,
    p_status     OUT VARCHAR2
) AS
    v_balance NUMBER(12,2);
BEGIN
    SELECT balance INTO v_balance FROM accounts 
    WHERE account_id = p_account_id FOR UPDATE;
    
    IF v_balance >= p_amount THEN
        UPDATE accounts SET balance = balance - p_amount, updated_at = SYSTIMESTAMP 
        WHERE account_id = p_account_id;
        p_status := 'SUCCESS';
    ELSE
        p_status := 'INSUFFICIENT_FUNDS';
    END IF;
    COMMIT;
EXCEPTION
    WHEN OTHERS THEN
        ROLLBACK;
        p_status := 'ERROR: ' || SQLERRM;
END P_SUBTYPE_003;`,
        targetSql: `CREATE OR REPLACE PROCEDURE public.p_subtype_003 (
    IN p_account_id BIGINT,
    IN p_amount NUMERIC(12,2),
    OUT p_status TEXT
) LANGUAGE plpgsql AS $$
DECLARE
    v_balance NUMERIC(12,2);
BEGIN
    SELECT balance INTO v_balance FROM public.accounts 
    WHERE account_id = p_account_id FOR UPDATE;
    
    IF v_balance >= p_amount THEN
        UPDATE public.accounts SET balance = balance - p_amount, updated_at = clock_timestamp() 
        WHERE account_id = p_account_id;
        p_status := 'SUCCESS';
    ELSE
        p_status := 'INSUFFICIENT_FUNDS';
    END IF;
    -- Note: Transaction commit in Postgres procedure is handled by caller
EXCEPTION
    WHEN OTHERS THEN
        p_status := 'ERROR: ' || SQLERRM;
END;
$$;`,
        findings: [
          { line: 15, severity: 'INFO', code: 'TRANSPILER_NOTE', message: 'SYSTIMESTAMP mapped to clock_timestamp() for transaction-level freshness.', suggestedFix: 'Verified compatible' },
          { line: 20, severity: 'WARNING', code: 'COMMIT_SEMANTICS', message: 'Explicit COMMIT inside procedure has different scope in PostgreSQL. Caller handles outer transaction block.' }
        ]
      }
    ];
  }

  // --------------------------------------------------------------------------
  // 8. STEP 6 — ENTERPRISE CONFIGURATION TAXONOMY (DOMAINS A..AC)
  // --------------------------------------------------------------------------
  public getDynamicConfigDomains(mode: MigrationMode): ConfigDomainGroup[] {
    const allDomains: ConfigDomainGroup[] = [
      {
        id: 'A',
        name: 'Connection & Session Tuning',
        description: 'Connection pool bounds, statement timeouts, and keepalive configurations.',
        applicableModes: ['M1_BULK', 'M2_BULK_CDC', 'M3_CDC', 'M4_INCREMENTAL', 'M5_STATE_SYNC', 'M6_SCHEMA_ONLY', 'M7_DATA_ONLY'],
        fields: [
          { id: 'max_pool_size', label: 'Max Connection Pool Size', description: 'Concurrent worker database sessions allocated.', domainId: 'A', type: 'number', defaultValue: 16, effectiveValue: 16, recommendation: '16 for standard core count', scope: 'CONNECTOR', isOverridden: false, isBasicVisible: true, risk: 'LOW', restartRequired: false },
          { id: 'stmt_timeout_sec', label: 'Statement Timeout (sec)', description: 'Query execution cancel boundary.', domainId: 'A', type: 'number', defaultValue: 300, effectiveValue: 300, scope: 'CONNECTOR', isOverridden: false, isBasicVisible: false, risk: 'LOW', restartRequired: false }
        ]
      },
      {
        id: 'C',
        name: 'Work Partitioning Strategy',
        description: 'Primary key range chunking, partition boundary estimation, and worker dispatch.',
        applicableModes: ['M1_BULK', 'M2_BULK_CDC', 'M5_STATE_SYNC', 'M7_DATA_ONLY'],
        fields: [
          { id: 'partition_strategy', label: 'Partition Split Algorithm', description: 'Method used to calculate chunk boundaries.', domainId: 'C', type: 'select', options: [{ label: 'Adaptive Key-Range Splitting', value: 'ADAPTIVE_RANGE' }, { label: 'Even Modulo Hash', value: 'MODULO_HASH' }, { label: 'Physical Table Partition Bound', value: 'PHYSICAL_BOUND' }], defaultValue: 'ADAPTIVE_RANGE', effectiveValue: 'ADAPTIVE_RANGE', recommendation: 'Adaptive range for uneven indexes', scope: 'MIGRATION', isOverridden: false, isBasicVisible: true, risk: 'MEDIUM', restartRequired: true },
          { id: 'chunk_row_target', label: 'Target Rows Per Chunk', description: 'Optimum partition granularity.', domainId: 'C', type: 'number', defaultValue: 100000, effectiveValue: 100000, scope: 'MIGRATION', isOverridden: false, isBasicVisible: true, risk: 'LOW', restartRequired: false }
        ]
      },
      {
        id: 'D',
        name: 'Workers & Parallelism',
        description: 'Active thread execution limits and CPU core quotas.',
        applicableModes: ['M1_BULK', 'M2_BULK_CDC', 'M4_INCREMENTAL', 'M5_STATE_SYNC', 'M7_DATA_ONLY'],
        fields: [
          { id: 'min_workers', label: 'Minimum Worker Threads', description: 'Base concurrent worker threads.', domainId: 'D', type: 'number', defaultValue: 4, effectiveValue: 4, scope: 'MIGRATION', isOverridden: false, isBasicVisible: true, risk: 'LOW', restartRequired: false },
          { id: 'max_workers', label: 'Maximum Worker Threads', description: 'Burst cap for parallel partitions.', domainId: 'D', type: 'number', defaultValue: 16, effectiveValue: 16, scope: 'MIGRATION', isOverridden: false, isBasicVisible: true, risk: 'MEDIUM', restartRequired: false }
        ]
      },
      {
        id: 'H',
        name: 'Bulk Transport Engine',
        description: 'Direct binary streaming, zero-copy buffer pools, and bulk load optimizations.',
        applicableModes: ['M1_BULK', 'M2_BULK_CDC', 'M7_DATA_ONLY'],
        fields: [
          { id: 'direct_stream_buffer_mb', label: 'Direct Stream Buffer (MB)', description: 'In-memory off-heap ring buffer size.', domainId: 'H', type: 'number', defaultValue: 512, effectiveValue: 512, scope: 'MIGRATION', isOverridden: false, isBasicVisible: true, risk: 'MEDIUM', restartRequired: true },
          { id: 'bulk_commit_interval_rows', label: 'Commit Batch Interval (Rows)', description: 'Transaction size written to target per atomic flush.', domainId: 'H', type: 'number', defaultValue: 25000, effectiveValue: 25000, scope: 'MIGRATION', isOverridden: false, isBasicVisible: true, risk: 'LOW', restartRequired: false }
        ]
      },
      {
        id: 'M',
        name: 'CDC Log Capture Engine',
        description: 'Transaction log reading, SCN/LSN bookmarks, and connector-specific replication slots.',
        applicableModes: ['M2_BULK_CDC', 'M3_CDC'],
        fields: [
          { id: 'cdc_start_boundary', label: 'CDC Starting Boundary Mode', description: 'Position from which change logs are tailed.', domainId: 'M', type: 'select', options: [{ label: 'Automatic Snapshot Boundary', value: 'SNAPSHOT_BOUNDARY' }, { label: 'Earliest Available Log Entry', value: 'EARLIEST' }, { label: 'Current Transaction Wall Time', value: 'CURRENT_TIME' }], defaultValue: 'SNAPSHOT_BOUNDARY', effectiveValue: 'SNAPSHOT_BOUNDARY', scope: 'MIGRATION', isOverridden: false, isBasicVisible: true, risk: 'HIGH', restartRequired: true },
          { id: 'cdc_poll_interval_ms', label: 'Log Poll Frequency (ms)', description: 'Delay between transaction log read cycles.', domainId: 'M', type: 'number', defaultValue: 50, effectiveValue: 50, scope: 'MIGRATION', isOverridden: false, isBasicVisible: true, risk: 'LOW', restartRequired: false }
        ]
      },
      {
        id: 'N',
        name: 'CDC Backlog & Buffer Management',
        description: 'Memory ring buffer limits, spill-to-disk thresholds, and backpressure policies.',
        applicableModes: ['M2_BULK_CDC', 'M3_CDC'],
        fields: [
          { id: 'cdc_max_memory_mb', label: 'Max In-Memory Queue (MB)', description: 'Buffer cap before spooling changes to disk.', domainId: 'N', type: 'number', defaultValue: 2048, effectiveValue: 2048, scope: 'MIGRATION', isOverridden: false, isBasicVisible: true, risk: 'MEDIUM', restartRequired: false },
          { id: 'backpressure_throttle_percent', label: 'Source Throttling Threshold (%)', description: 'Queue capacity level that triggers source extract slowdown.', domainId: 'N', type: 'number', defaultValue: 90, effectiveValue: 90, scope: 'MIGRATION', isOverridden: false, isBasicVisible: false, risk: 'HIGH', restartRequired: false }
        ]
      },
      {
        id: 'Q',
        name: 'Incremental Query & Watermark Strategy',
        description: 'High-watermark tracking, overlap lookback windows, and late data handling.',
        applicableModes: ['M4_INCREMENTAL'],
        fields: [
          { id: 'watermark_column', label: 'High-Watermark Tracking Column', description: 'Monotonically increasing timestamp or sequential ID.', domainId: 'Q', type: 'string', defaultValue: 'updated_at', effectiveValue: 'updated_at', scope: 'OBJECT', isOverridden: false, isBasicVisible: true, risk: 'HIGH', restartRequired: true },
          { id: 'lookback_window_sec', label: 'Overlap Lookback Window (sec)', description: 'Safety window re-polled to catch out-of-order commits.', domainId: 'Q', type: 'number', defaultValue: 120, effectiveValue: 120, scope: 'MIGRATION', isOverridden: false, isBasicVisible: true, risk: 'MEDIUM', restartRequired: false }
        ]
      },
      {
        id: 'R',
        name: 'State-Based Merkle Synchronization',
        description: 'Hierarchical hash comparisons, delta computation, and repair boundaries.',
        applicableModes: ['M5_STATE_SYNC'],
        fields: [
          { id: 'merkle_depth', label: 'Merkle Tree Precision Depth', description: 'Subdivision level for granular mismatch localization.', domainId: 'R', type: 'number', defaultValue: 8, effectiveValue: 8, scope: 'MIGRATION', isOverridden: false, isBasicVisible: true, risk: 'LOW', restartRequired: false },
          { id: 'hash_algorithm', label: 'State Fingerprint Hash Function', description: 'Cryptographic hash used for record aggregation.', domainId: 'R', type: 'select', options: [{ label: 'XXHash64 (High Performance)', value: 'XXHASH64' }, { label: 'SHA-256 (Strict Audit Proof)', value: 'SHA256' }], defaultValue: 'XXHASH64', effectiveValue: 'XXHASH64', scope: 'MIGRATION', isOverridden: false, isBasicVisible: true, risk: 'LOW', restartRequired: false }
        ]
      },
      {
        id: 'U',
        name: 'Schema Execution & DDL Ordering',
        description: 'Topological sort, constraint deferred validation, and transaction rollback rules.',
        applicableModes: ['M1_BULK', 'M2_BULK_CDC', 'M6_SCHEMA_ONLY'],
        fields: [
          { id: 'foreign_key_mode', label: 'Foreign Key Constraint Handling', description: 'Timing of foreign key creation and validation.', domainId: 'U', type: 'select', options: [{ label: 'Drop / Defer & Rebuild at Cutover', value: 'DEFER_REBUILD' }, { label: 'Enforce Online During Stream', value: 'ONLINE_ENFORCE' }], defaultValue: 'DEFER_REBUILD', effectiveValue: 'DEFER_REBUILD', scope: 'MIGRATION', isOverridden: false, isBasicVisible: true, risk: 'HIGH', restartRequired: true },
          { id: 'unsupported_type_action', label: 'Unsupported Data Type Policy', description: 'Action taken when column type has no native 1:1 map.', domainId: 'U', type: 'select', options: [{ label: 'Convert to JSON / String Representation', value: 'CONVERT_TEXT' }, { label: 'Block Plan Compilation with Error', value: 'BLOCK_ERROR' }], defaultValue: 'CONVERT_TEXT', effectiveValue: 'CONVERT_TEXT', scope: 'MIGRATION', isOverridden: false, isBasicVisible: true, risk: 'MEDIUM', restartRequired: false }
        ]
      },
      {
        id: 'AB',
        name: 'Governance & Approval Barriers',
        description: 'Mandatory human-in-the-loop checkpoints, four-eyes quorum, and timeout escalations.',
        applicableModes: ['M1_BULK', 'M2_BULK_CDC', 'M3_CDC', 'M4_INCREMENTAL', 'M5_STATE_SYNC', 'M6_SCHEMA_ONLY', 'M7_DATA_ONLY'],
        fields: [
          { id: 'four_eyes_enforced', label: 'Enforce Maker-Checker (Four-Eyes)', description: 'Author of migration cannot self-approve cutover.', domainId: 'AB', type: 'boolean', defaultValue: true, effectiveValue: true, scope: 'MIGRATION', isOverridden: false, isBasicVisible: true, risk: 'HIGH', restartRequired: false },
          { id: 'barrier_timeout_hours', label: 'Approval Expiry Window (hours)', description: 'Time before waiting barrier auto-cancels execution.', domainId: 'AB', type: 'number', defaultValue: 24, effectiveValue: 24, scope: 'MIGRATION', isOverridden: false, isBasicVisible: false, risk: 'LOW', restartRequired: false }
        ]
      }
    ];

    return allDomains.filter(d => d.applicableModes.includes(mode));
  }

  // --------------------------------------------------------------------------
  // 9. STEP 7 — DYNAMIC PLAN & CYTOSCAPE DAG FIXTURES
  // --------------------------------------------------------------------------
  // --------------------------------------------------------------------------
  // 9. STEP 7 — DYNAMIC PLAN & CYTOSCAPE DAG FIXTURES (7 CANONICAL MODES)
  // --------------------------------------------------------------------------
  public getExecutionPlanForMode(mode: MigrationMode): ExecutionPlanViewModel {
    switch (mode) {
      case 'M1_BULK':
        return {
          planId: 'plan-m1',
          migrationId: 'mig-m1',
          version: 1,
          fingerprint: 'Pending canonical compilation',
          mode: 'M1_BULK',
          isStale: false,
          estimatedDurationMin: 35,
          totalWorkItems: 48,
          risks: ['Heavy I/O read load on source tables'],
          warnings: ['Rebuilding target secondary indexes scheduled post-load'],
          nodes: [
            { id: 'm1_n1', label: '1. Runtime Initialization', type: 'DISCOVERY', state: 'COMPLETED', progressPercent: 100 },
            { id: 'm1_n2', label: '2. Target Schema DDL Execution', type: 'SCHEMA', state: 'COMPLETED', progressPercent: 100 },
            { id: 'm1_n3', label: '3. Disable Target FKs & Indexes', type: 'SCHEMA', state: 'COMPLETED', progressPercent: 100 },
            { id: 'm1_n4', label: '4. Partition Slicing (48 Tasks)', type: 'STAGE', state: 'RUNNING', progressPercent: 80, workerCount: 8 },
            { id: 'm1_n5', label: '5. Parallel Direct-Path Bulk Stream', type: 'BULK_TRANSFER', state: 'RUNNING', progressPercent: 65, workerCount: 16, throughput: '92k r/s' },
            { id: 'm1_n6', label: '6. Re-enable Constraints & Indexes', type: 'SCHEMA', state: 'QUEUED', progressPercent: 0 },
            { id: 'm1_n7', label: '7. Checksum & Row-Count Validation', type: 'VALIDATION', state: 'QUEUED', progressPercent: 0 },
            { id: 'm1_n8', label: '8. Target Finalize & Trust Seal', type: 'STAGE', state: 'QUEUED', progressPercent: 0 }
          ],
          edges: [
            { id: 'm1_e1', source: 'm1_n1', target: 'm1_n2', canInsertBarrier: true },
            { id: 'm1_e2', source: 'm1_n2', target: 'm1_n3', canInsertBarrier: true },
            { id: 'm1_e3', source: 'm1_n3', target: 'm1_n4', canInsertBarrier: true },
            { id: 'm1_e4', source: 'm1_n4', target: 'm1_n5', canInsertBarrier: true },
            { id: 'm1_e5', source: 'm1_n5', target: 'm1_n6', canInsertBarrier: true },
            { id: 'm1_e6', source: 'm1_n6', target: 'm1_n7', canInsertBarrier: true },
            { id: 'm1_e7', source: 'm1_n7', target: 'm1_n8', canInsertBarrier: true }
          ]
        };

      case 'M2_BULK_CDC':
        return {
          planId: 'plan-m2',
          migrationId: 'mig-m2',
          version: 2,
          fingerprint: 'Pending canonical compilation',
          mode: 'M2_BULK_CDC',
          isStale: false,
          estimatedDurationMin: 45,
          totalWorkItems: 64,
          risks: ['Cutover requires source write quiescence', 'Large LOB column in TRANSACTIONS table'],
          warnings: ['PostgreSQL target autovacuum recommended after initial bulk stream'],
          nodes: [
            { id: 'm2_n1', label: '1. Runtime Initialization', type: 'DISCOVERY', state: 'COMPLETED', progressPercent: 100 },
            { id: 'm2_n2', label: '2. Target Schema DDL Execution', type: 'SCHEMA', state: 'COMPLETED', progressPercent: 100 },
            { id: 'm2_n3', label: '3. Establish SCN / LSN Boundary', type: 'STAGE', state: 'COMPLETED', progressPercent: 100 },
            { id: 'm2_n4', label: '4. Initialize CDC LogMiner Stream', type: 'CDC_CATCHUP', state: 'RUNNING', progressPercent: 100, throughput: '12ms lag' },
            { id: 'm2_n5', label: '5. Parallel Bulk Snapshot Stream (64 Tasks)', type: 'BULK_TRANSFER', state: 'COMPLETED', progressPercent: 100, workerCount: 16, throughput: '88k r/s' },
            { id: 'm2_n6', label: '6. Continuous CDC Synchronization', type: 'CDC_CATCHUP', state: 'RUNNING', progressPercent: 95, throughput: '12ms lag' },
            { id: 'm2_n7', label: '7. Replication Lag & Backlog Monitor', type: 'VALIDATION', state: 'RUNNING', progressPercent: 98 },
            {
              id: 'm2_n8',
              label: 'Gate 2: Production Cutover Sign-Off',
              type: 'APPROVAL_BARRIER',
              state: 'BARRIER_WAITING',
              progressPercent: 0,
              isBarrier: true,
              barrierType: 'MANDATORY_FOUR_EYES',
              approverRoles: ['Lead DBA', 'Security Officer'],
              requiredSignatures: 2,
              currentSignatures: 0,
              isApproved: false
            },
            { id: 'm2_n9', label: '8. Target Quiescence & Drain In-Flight', type: 'STAGE', state: 'QUEUED', progressPercent: 0 },
            { id: 'm2_n10', label: '9. Final Target Cutover & Authority Flip', type: 'CUTOVER', state: 'QUEUED', progressPercent: 0 },
            { id: 'm2_n11', label: '10. Post-Cutover Validation & Seal', type: 'VALIDATION', state: 'QUEUED', progressPercent: 0 }
          ],
          edges: [
            { id: 'm2_e1', source: 'm2_n1', target: 'm2_n2', canInsertBarrier: true },
            { id: 'm2_e2', source: 'm2_n2', target: 'm2_n3', canInsertBarrier: true },
            { id: 'm2_e3', source: 'm2_n3', target: 'm2_n4', canInsertBarrier: true },
            { id: 'm2_e4', source: 'm2_n3', target: 'm2_n5', canInsertBarrier: true },
            { id: 'm2_e5', source: 'm2_n5', target: 'm2_n6', canInsertBarrier: true },
            { id: 'm2_e6', source: 'm2_n4', target: 'm2_n6', canInsertBarrier: true },
            { id: 'm2_e7', source: 'm2_n6', target: 'm2_n7', canInsertBarrier: true },
            { id: 'm2_e8', source: 'm2_n7', target: 'm2_n8', canInsertBarrier: false },
            { id: 'm2_e9', source: 'm2_n8', target: 'm2_n9', canInsertBarrier: true },
            { id: 'm2_e10', source: 'm2_n9', target: 'm2_n10', canInsertBarrier: true },
            { id: 'm2_e11', source: 'm2_n10', target: 'm2_n11', canInsertBarrier: true }
          ]
        };

      case 'M3_CDC':
        return {
          planId: 'plan-m3',
          migrationId: 'mig-m3',
          version: 1,
          fingerprint: 'Pending canonical compilation',
          mode: 'M3_CDC',
          isStale: false,
          estimatedDurationMin: 60,
          totalWorkItems: 12,
          risks: ['Requires active transaction log retention on source'],
          warnings: ['Ensure CDC publisher queue headroom remains above 20%'],
          nodes: [
            { id: 'm3_n1', label: '1. Runtime Initialization', type: 'DISCOVERY', state: 'COMPLETED', progressPercent: 100 },
            { id: 'm3_n2', label: '2. Establish CDC Starting Frontier', type: 'STAGE', state: 'COMPLETED', progressPercent: 100 },
            { id: 'm3_n3', label: '3. Transaction Capture Stream', type: 'CDC_CATCHUP', state: 'RUNNING', progressPercent: 88, throughput: '14k tx/s' },
            { id: 'm3_n4', label: '4. Persistent Spill Buffer & Ring Queue', type: 'STAGE', state: 'RUNNING', progressPercent: 88 },
            { id: 'm3_n5', label: '5. Transaction-Aware Apply Pipeline', type: 'STAGE', state: 'RUNNING', progressPercent: 85 },
            { id: 'm3_n6', label: '6. Lag & SLA Health Telemetry', type: 'VALIDATION', state: 'RUNNING', progressPercent: 90 },
            {
              id: 'm3_n7',
              label: 'Gate 2: Production Cutover Sign-Off',
              type: 'APPROVAL_BARRIER',
              state: 'BARRIER_WAITING',
              progressPercent: 0,
              isBarrier: true,
              barrierType: 'MANDATORY_FOUR_EYES',
              approverRoles: ['Lead DBA', 'Security Officer'],
              requiredSignatures: 2,
              currentSignatures: 0,
              isApproved: false
            },
            { id: 'm3_n8', label: '7. Cutover & Fencing Execution', type: 'CUTOVER', state: 'QUEUED', progressPercent: 0 }
          ],
          edges: [
            { id: 'm3_e1', source: 'm3_n1', target: 'm3_n2', canInsertBarrier: true },
            { id: 'm3_e2', source: 'm3_n2', target: 'm3_n3', canInsertBarrier: true },
            { id: 'm3_e3', source: 'm3_n3', target: 'm3_n4', canInsertBarrier: true },
            { id: 'm3_e4', source: 'm3_n4', target: 'm3_n5', canInsertBarrier: true },
            { id: 'm3_e5', source: 'm3_n5', target: 'm3_n6', canInsertBarrier: true },
            { id: 'm3_e6', source: 'm3_n6', target: 'm3_n7', canInsertBarrier: false },
            { id: 'm3_e7', source: 'm3_n7', target: 'm3_n8', canInsertBarrier: true }
          ]
        };

      case 'M4_INCREMENTAL':
        return {
          planId: 'plan-m4',
          migrationId: 'mig-m4',
          version: 1,
          fingerprint: 'Pending canonical compilation',
          mode: 'M4_INCREMENTAL',
          isStale: false,
          estimatedDurationMin: 20,
          totalWorkItems: 16,
          risks: [],
          warnings: ['Watermark must not advance prior to target commit'],
          nodes: [
            { id: 'm4_n1', label: '1. Runtime Initialization', type: 'DISCOVERY', state: 'COMPLETED', progressPercent: 100 },
            { id: 'm4_n2', label: '2. Acquire Watermark Cursor Position', type: 'STAGE', state: 'COMPLETED', progressPercent: 100 },
            { id: 'm4_n3', label: '3. Bounded Query Window Extraction', type: 'BULK_TRANSFER', state: 'RUNNING', progressPercent: 75, throughput: '32k r/s' },
            { id: 'm4_n4', label: '4. In-Flight Transform & Cleansing', type: 'STAGE', state: 'RUNNING', progressPercent: 75 },
            { id: 'm4_n5', label: '5. Target Upsert & Transaction Commit', type: 'STAGE', state: 'RUNNING', progressPercent: 70 },
            { id: 'm4_n6', label: '6. Advance Watermark Frontier', type: 'STAGE', state: 'QUEUED', progressPercent: 0 },
            { id: 'm4_n7', label: '7. Window Checksum Validation', type: 'VALIDATION', state: 'QUEUED', progressPercent: 0 }
          ],
          edges: [
            { id: 'm4_e1', source: 'm4_n1', target: 'm4_n2', canInsertBarrier: true },
            { id: 'm4_e2', source: 'm4_n2', target: 'm4_n3', canInsertBarrier: true },
            { id: 'm4_e3', source: 'm4_n3', target: 'm4_n4', canInsertBarrier: true },
            { id: 'm4_e4', source: 'm4_n4', target: 'm4_n5', canInsertBarrier: true },
            { id: 'm4_e5', source: 'm4_n5', target: 'm4_n6', canInsertBarrier: true },
            { id: 'm4_e6', source: 'm4_n6', target: 'm4_n7', canInsertBarrier: true }
          ]
        };

      case 'M5_STATE_SYNC':
        return {
          planId: 'plan-m5',
          migrationId: 'mig-m5',
          version: 1,
          fingerprint: 'Pending canonical compilation',
          mode: 'M5_STATE_SYNC',
          isStale: false,
          estimatedDurationMin: 30,
          totalWorkItems: 24,
          risks: [],
          warnings: ['Merkle verification requires hash calculation across target'],
          nodes: [
            { id: 'm5_n1', label: '1. Runtime Initialization', type: 'DISCOVERY', state: 'COMPLETED', progressPercent: 100 },
            { id: 'm5_n2', label: '2. Source & Target Boundary Slicing', type: 'STAGE', state: 'COMPLETED', progressPercent: 100 },
            { id: 'm5_n3', label: '3. Merkle Tree Checksum Computation', type: 'VALIDATION', state: 'RUNNING', progressPercent: 60 },
            { id: 'm5_n4', label: '4. Divergence & Delta Identification', type: 'VALIDATION', state: 'RUNNING', progressPercent: 50 },
            { id: 'm5_n5', label: '5. Conflict Resolution & Fenced Repair', type: 'STAGE', state: 'QUEUED', progressPercent: 0 },
            { id: 'm5_n6', label: '6. Target Delta Ingestion', type: 'BULK_TRANSFER', state: 'QUEUED', progressPercent: 0 },
            { id: 'm5_n7', label: '7. Final State Verification', type: 'VALIDATION', state: 'QUEUED', progressPercent: 0 }
          ],
          edges: [
            { id: 'm5_e1', source: 'm5_n1', target: 'm5_n2', canInsertBarrier: true },
            { id: 'm5_e2', source: 'm5_n2', target: 'm5_n3', canInsertBarrier: true },
            { id: 'm5_e3', source: 'm5_n3', target: 'm5_n4', canInsertBarrier: true },
            { id: 'm5_e4', source: 'm5_n4', target: 'm5_n5', canInsertBarrier: true },
            { id: 'm5_e5', source: 'm5_n5', target: 'm5_n6', canInsertBarrier: true },
            { id: 'm5_e6', source: 'm5_n6', target: 'm5_n7', canInsertBarrier: true }
          ]
        };

      case 'M6_SCHEMA_ONLY':
        return {
          planId: 'plan-m6',
          migrationId: 'mig-m6',
          version: 1,
          fingerprint: 'Pending canonical compilation',
          mode: 'M6_SCHEMA_ONLY',
          isStale: false,
          estimatedDurationMin: 15,
          totalWorkItems: 8,
          risks: [],
          warnings: ['Procedures with proprietary built-ins require transpile validation'],
          nodes: [
            { id: 'm6_n1', label: '1. Runtime Initialization', type: 'DISCOVERY', state: 'COMPLETED', progressPercent: 100 },
            { id: 'm6_n2', label: '2. Extract Source DDL & Abstract Syntax', type: 'DISCOVERY', state: 'COMPLETED', progressPercent: 100 },
            { id: 'm6_n3', label: '3. Dependency Graph Sorter & Parser', type: 'STAGE', state: 'COMPLETED', progressPercent: 100 },
            { id: 'm6_n4', label: '4. Transpile DDL & Stored Procedures', type: 'SCHEMA', state: 'RUNNING', progressPercent: 90 },
            { id: 'm6_n5', label: '5. Create Target Tables & Sequences', type: 'SCHEMA', state: 'RUNNING', progressPercent: 80 },
            { id: 'm6_n6', label: '6. Create FKs & Secondary Indexes', type: 'SCHEMA', state: 'QUEUED', progressPercent: 0 },
            { id: 'm6_n7', label: '7. Compile Functions, Procs & Triggers', type: 'SCHEMA', state: 'QUEUED', progressPercent: 0 },
            { id: 'm6_n8', label: '8. Schema Object Integrity Audit', type: 'VALIDATION', state: 'QUEUED', progressPercent: 0 }
          ],
          edges: [
            { id: 'm6_e1', source: 'm6_n1', target: 'm6_n2', canInsertBarrier: true },
            { id: 'm6_e2', source: 'm6_n2', target: 'm6_n3', canInsertBarrier: true },
            { id: 'm6_e3', source: 'm6_n3', target: 'm6_n4', canInsertBarrier: true },
            { id: 'm6_e4', source: 'm6_n4', target: 'm6_n5', canInsertBarrier: true },
            { id: 'm6_e5', source: 'm6_n5', target: 'm6_n6', canInsertBarrier: true },
            { id: 'm6_e6', source: 'm6_n6', target: 'm6_n7', canInsertBarrier: true },
            { id: 'm6_e7', source: 'm6_n7', target: 'm6_n8', canInsertBarrier: true }
          ]
        };

      case 'M7_DATA_ONLY':
        return {
          planId: 'plan-m7',
          migrationId: 'mig-m7',
          version: 1,
          fingerprint: 'Pending canonical compilation',
          mode: 'M7_DATA_ONLY',
          isStale: false,
          estimatedDurationMin: 25,
          totalWorkItems: 32,
          risks: ['Target tables must pre-exist and match source column definitions'],
          warnings: ['Constraints temporarily disabled during transport to maximize ingest rate'],
          nodes: [
            { id: 'm7_n1', label: '1. Runtime Initialization', type: 'DISCOVERY', state: 'COMPLETED', progressPercent: 100 },
            { id: 'm7_n2', label: '2. Verify Target Tables & Capacity', type: 'DISCOVERY', state: 'COMPLETED', progressPercent: 100 },
            { id: 'm7_n3', label: '3. Disable Target Constraints & Triggers', type: 'SCHEMA', state: 'COMPLETED', progressPercent: 100 },
            { id: 'm7_n4', label: '4. Parallel Bulk Data Transport', type: 'BULK_TRANSFER', state: 'RUNNING', progressPercent: 70, workerCount: 16, throughput: '96k r/s' },
            { id: 'm7_n5', label: '5. Re-enable & Validate Constraints', type: 'SCHEMA', state: 'QUEUED', progressPercent: 0 },
            { id: 'm7_n6', label: '6. Row-Count & Checksum Integrity Audit', type: 'VALIDATION', state: 'QUEUED', progressPercent: 0 }
          ],
          edges: [
            { id: 'm7_e1', source: 'm7_n1', target: 'm7_n2', canInsertBarrier: true },
            { id: 'm7_e2', source: 'm7_n2', target: 'm7_n3', canInsertBarrier: true },
            { id: 'm7_e3', source: 'm7_n3', target: 'm7_n4', canInsertBarrier: true },
            { id: 'm7_e4', source: 'm7_n4', target: 'm7_n5', canInsertBarrier: true },
            { id: 'm7_e5', source: 'm7_n5', target: 'm7_n6', canInsertBarrier: true }
          ]
        };
    }
  }

  // --------------------------------------------------------------------------
  // 10. STEP 8 — GOVERNANCE & READINESS CHECKLIST
  // --------------------------------------------------------------------------
  public getReadinessChecks(): ReadinessCheckItem[] {
    return [
      { id: 'chk-1', category: 'CONNECTION', title: 'Source & Target Connection Handshake', status: 'PASSED', detail: 'Both Oracle and PostgreSQL endpoints verified via mTLS and SSH Bastion.' },
      { id: 'chk-2', category: 'PREREQUISITES', title: 'Oracle Supplemental Logging', status: 'PASSED', detail: 'Database supplemental logging active with ALL COLUMNS enabled.' },
      { id: 'chk-3', category: 'STORAGE', title: 'Target Disk & WAL Spool Headroom', status: 'PASSED', detail: '148 GB free headroom on target EBS volume (threshold: 50 GB).' },
      { id: 'chk-4', category: 'GOVERNANCE', title: 'Maker-Checker Policy Enforcement', status: 'PASSED', detail: 'Author Aalok Ladwa cannot self-approve cutover. 2 L4 sign-offs configured.' }
    ];
  }

  // --------------------------------------------------------------------------
  // 11. VALIDATION OPERATIONS (2.6) FIXTURES
  // --------------------------------------------------------------------------
  public getValidationItems(): ValidationItem[] {
    return [
      {
        id: 'val-001',
        name: 'Enterprise Customer Data Post-Migration Check',
        purpose: 'POST_MIGRATION_VERIFICATION',
        migrationId: 'mig-001',
        migrationName: 'Enterprise Customer Data Hub',
        sourceEngine: 'Oracle',
        sourceInstance: 'ora-cluster-01.prod:1521',
        targetEngine: 'PostgreSQL',
        targetInstance: 'aurora-pg-01.aws:5432',
        verdict: 'SYNCED_CERTIFIED',
        profile: 'FULL_CERTIFICATION',
        scopeType: 'FULL',
        objectsExpected: 18,
        objectsValidated: 18,
        objectsDivergent: 0,
        rowsExpected: 52400000,
        rowsValidated: 52400000,
        rowsMatched: 52400000,
        rowsMismatched: 0,
        rowsMissingInTarget: 0,
        rowsExtraInTarget: 0,
        cellDifferencesCount: 0,
        durationSec: 342,
        isRepairEligible: false,
        isCertified: true,
        runFingerprint: 'sha256:5a6b7c8d9e0f1a2b3c4d5e6f',
        startedAt: '2026-08-28T07:00:00Z',
        completedAt: '2026-08-28T07:05:42Z'
      },
      {
        id: 'val-002',
        name: 'Core Banking Ledger Pre-Cutover Verification',
        purpose: 'CONTINUOUS_SYNCHRONIZATION_ASSURANCE',
        migrationId: 'mig-002',
        migrationName: 'Core Banking Ledger',
        sourceEngine: 'Oracle',
        sourceInstance: 'ora-rac-core.corp:1521',
        targetEngine: 'PostgreSQL',
        targetInstance: 'aurora-pg-core.aws:5432',
        verdict: 'NOT_SYNCED',
        profile: 'DEEP',
        scopeType: 'PARTITIONED',
        objectsExpected: 24,
        objectsValidated: 24,
        objectsDivergent: 2,
        rowsExpected: 18600000,
        rowsValidated: 18600000,
        rowsMatched: 18599982,
        rowsMismatched: 18,
        rowsMissingInTarget: 14,
        rowsExtraInTarget: 4,
        cellDifferencesCount: 34,
        durationSec: 128,
        isRepairEligible: true,
        isCertified: false,
        runFingerprint: 'sha256:9a8b7c6d5e4f3a2b1c0d9e8f',
        startedAt: '2026-08-28T09:30:00Z',
        completedAt: '2026-08-28T09:32:08Z'
      }
    ];
  }

  public getDifferenceFunnel(validationId: string): DifferenceFunnelLevel[] {
    return [
      { label: 'Total Rows Evaluated', totalCount: 18600000, matchedCount: 18599982, mismatchedCount: 18, unit: 'Rows', percentMatched: 99.9999 },
      { label: 'Objects in Scope', totalCount: 24, matchedCount: 22, mismatchedCount: 2, unit: 'Tables', percentMatched: 91.66 },
      { label: 'Partitions Compared', totalCount: 8, matchedCount: 6, mismatchedCount: 2, unit: 'Partitions', percentMatched: 75.0 },
      { label: 'Disputed Rows', totalCount: 18, matchedCount: 0, mismatchedCount: 18, unit: 'Rows', percentMatched: 0.0 },
      { label: 'Differing Cells', totalCount: 34, matchedCount: 0, mismatchedCount: 34, unit: 'Cells', percentMatched: 0.0 }
    ];
  }

  public getSchemaDiff(validationId: string): SchemaDiffItem[] {
    return [
      { objectName: 'ACCOUNTS.account_id', sourceType: 'NUMBER(18)', targetType: 'BIGINT', status: 'MATCH', detail: 'Native integer width match' },
      { objectName: 'ACCOUNTS.balance', sourceType: 'NUMBER(12,2)', targetType: 'NUMERIC(12,2)', status: 'MATCH', detail: 'Exact precision match' },
      { objectName: 'ACCOUNTS.ssn_no', sourceType: 'VARCHAR2(11)', targetType: 'TEXT', status: 'TYPE_COERCION', detail: 'PII format-preserving masking applied' }
    ];
  }

  public getPartitionHeatmap(validationId: string): PartitionHeatmapCell[] {
    return [
      { partitionId: 'P01', keyRange: '1..2500000', status: 'IDENTICAL', divergentRows: 0, totalRows: 2500000 },
      { partitionId: 'P02', keyRange: '2500001..5000000', status: 'IDENTICAL', divergentRows: 0, totalRows: 2500000 },
      { partitionId: 'P03', keyRange: '5000001..7500000', status: 'LOW_DIFF', divergentRows: 8, totalRows: 2500000 },
      { partitionId: 'P04', keyRange: '7500001..10000000', status: 'LOW_DIFF', divergentRows: 10, totalRows: 2500000 },
      { partitionId: 'P05', keyRange: '10000001..12500000', status: 'IDENTICAL', divergentRows: 0, totalRows: 2500000 },
      { partitionId: 'P06', keyRange: '12500001..15000000', status: 'IDENTICAL', divergentRows: 0, totalRows: 2500000 },
      { partitionId: 'P07', keyRange: '15000001..17500000', status: 'IDENTICAL', divergentRows: 0, totalRows: 2500000 },
      { partitionId: 'P08', keyRange: '17500001..18600000', status: 'IDENTICAL', divergentRows: 0, totalRows: 1100000 }
    ];
  }

  public getMerkleTree(validationId: string): MerkleNodeItem {
    return {
      id: 'root',
      range: 'ACCOUNTS (1..18600000)',
      sourceHash: '0x7F9A2B8E3C1D4A5F',
      targetHash: '0x7F9A2B8E3C1D4A00',
      isMatched: false,
      children: [
        {
          id: 'branch-left',
          range: '1..10000000',
          sourceHash: '0x3D1E9F8A7B6C5D4E',
          targetHash: '0x3D1E9F8A7B6C5D00',
          isMatched: false,
          children: [
            { id: 'leaf-p3', range: '5000001..7500000', sourceHash: '0xAA11BB22CC33DD44', targetHash: '0xAA11BB22CC33DD00', isMatched: false },
            { id: 'leaf-p4', range: '7500001..10000000', sourceHash: '0xEE55FF6600112233', targetHash: '0xEE55FF6600112200', isMatched: false }
          ]
        },
        {
          id: 'branch-right',
          range: '10000001..18600000',
          sourceHash: '0x5C4B3A291807FE6D',
          targetHash: '0x5C4B3A291807FE6D',
          isMatched: true
        }
      ]
    };
  }

  public getDisputedRows(validationId: string): DisputedRowItem[] {
    return [
      {
        primaryKey: '948201',
        tableName: 'ACCOUNTS',
        differenceType: 'VALUE_MISMATCH',
        sourceFields: { account_id: 948201, customer_id: 42109, balance: 14250.00, updated_at: '2026-08-28 09:28:14' },
        targetFields: { account_id: 948201, customer_id: 42109, balance: 14000.00, updated_at: '2026-08-28 09:25:00' },
        disputedColumns: ['balance', 'updated_at']
      },
      {
        primaryKey: '948204',
        tableName: 'ACCOUNTS',
        differenceType: 'MISSING_IN_TARGET',
        sourceFields: { account_id: 948204, customer_id: 88120, balance: 250.00, updated_at: '2026-08-28 09:29:40' },
        targetFields: {},
        disputedColumns: ['account_id', 'customer_id', 'balance']
      }
    ];
  }

  public getGovernedRepairPlan(validationId: string): GovernedRepairPlan {
    return {
      repairPlanId: 'rep-002',
      validationRunId: validationId,
      fingerprint: 'sha256:2b3c4d5e6f7a8b9c0d1e2f3a',
      proposedInserts: 14,
      proposedUpdates: 4,
      proposedDeletes: 0,
      affectedObjects: ['ACCOUNTS'],
      safetyClassification: 'TARGET_MUTATION_REVERSIBLE',
      approvalRequired: true,
      approvalStatus: 'PENDING',
      approverRoles: ['Lead DBA', 'SecOps Approver'],
      requiresMandatoryRevalidation: true,
      executionState: 'IDLE'
    };
  }

  // --------------------------------------------------------------------------
  // 12. HISTORY & EVIDENCE LEDGER FIXTURES
  // --------------------------------------------------------------------------
  public getHistoryLedger(): HistoryLedgerItem[] {
    return [
      {
        executionId: 'exec-20260828-001',
        migrationId: 'mig-001',
        migrationName: 'Enterprise Customer Data Hub',
        sourceEngine: 'Oracle',
        targetEngine: 'PostgreSQL',
        mode: 'M1_BULK',
        environment: 'Production',
        startedAt: '2026-08-28 06:30:00 UTC',
        completedAt: '2026-08-28 07:05:42 UTC',
        durationString: '35m 42s',
        lifecycleState: 'COMPLETED',
        validationVerdict: 'SYNCED_CERTIFIED',
        evidenceState: 'SEALED',
        operator: 'Aalok Ladwa',
        planVersion: 'v1.4.0',
        planFingerprint: 'sha256:7f9a2b8e3c1d4a5f',
        rowsTransferred: 52400000,
        throughputAvg: 88400
      },
      {
        executionId: 'exec-20260827-003',
        migrationId: 'mig-005',
        migrationName: 'Legacy Product Catalog DDL Schema',
        sourceEngine: 'IBM Db2',
        targetEngine: 'PostgreSQL',
        mode: 'M6_SCHEMA_ONLY',
        environment: 'Development',
        startedAt: '2026-08-27 14:00:00 UTC',
        completedAt: '2026-08-27 14:04:12 UTC',
        durationString: '4m 12s',
        lifecycleState: 'COMPLETED',
        validationVerdict: 'SYNCED',
        evidenceState: 'SEALED',
        operator: 'Sarah Chen',
        planVersion: 'v1.0.0',
        planFingerprint: 'sha256:4a5b6c7d8e9f0a1b',
        rowsTransferred: 0,
        throughputAvg: 0
      }
    ];
  }

  public getMultiRunComparison(): MultiRunComparisonMetric[] {
    return [
      { dimension: 'Execution Duration', runValues: { 'exec-20260828-001': '35m 42s', 'exec-20260827-003': '4m 12s' }, hasVariance: true },
      { dimension: 'Rows Transferred', runValues: { 'exec-20260828-001': '52.4M rows', 'exec-20260827-003': '0 rows (Schema Only)' }, hasVariance: true },
      { dimension: 'Validation Verdict', runValues: { 'exec-20260828-001': 'SYNCED · CERTIFIED', 'exec-20260827-003': 'SYNCED' }, hasVariance: true },
      { dimension: 'Evidence Status', runValues: { 'exec-20260828-001': 'SEALED (SHA-256)', 'exec-20260827-003': 'SEALED (SHA-256)' }, hasVariance: false }
    ];
  }

  // --------------------------------------------------------------------------
  // 13. MIGRATION TEMPLATES FIXTURES
  // --------------------------------------------------------------------------
  public getTemplates(): MigrationTemplateItem[] {
    return [
      {
        id: 'tmpl-01',
        title: 'Oracle 19c to Aurora PostgreSQL Zero-Downtime Blueprint',
        version: 'v3.2.0',
        category: 'ORGANIZATION_STANDARD',
        description: 'Certified enterprise configuration for mission-critical core banking Oracle to AWS Aurora PostgreSQL migrations with parallel bulk and LogMiner CDC.',
        sourceTypes: ['Oracle'],
        targetTypes: ['PostgreSQL'],
        compatibleModes: ['M2_BULK_CDC', 'M1_BULK', 'M3_CDC'],
        strength: 'ENFORCED_POLICY',
        defaultConfigPreset: 'BALANCED',
        recommendedWorkers: 16,
        provenance: 'Derived from 14 completed enterprise banking migrations',
        tags: ['Zero-Downtime', 'LogMiner', 'Four-Eyes-Required', 'PCI-Masking'],
        usageCount: 18,
        lastUpdated: '2026-08-20',
        author: 'Platform Architecture Board'
      },
      {
        id: 'tmpl-02',
        title: 'SQL Server to Snowflake Lakehouse Ingestion Profile',
        version: 'v2.0.1',
        category: 'RECOMMENDED',
        description: 'Optimized batch and watermark micro-batch stream configuration for replicating transactional tables into Snowflake analytical schemas.',
        sourceTypes: ['Microsoft SQL Server'],
        targetTypes: ['Snowflake'],
        compatibleModes: ['M4_INCREMENTAL', 'M1_BULK', 'M7_DATA_ONLY'],
        strength: 'RECOMMENDATION',
        defaultConfigPreset: 'HIGH_THROUGHPUT',
        recommendedWorkers: 8,
        provenance: 'Created manually by Data Platform Team',
        tags: ['Snowflake', 'Stage-Copy', 'Incremental-Watermark'],
        usageCount: 7,
        lastUpdated: '2026-08-15',
        author: 'Sarah Chen'
      }
    ];
  }
}
