/**
 * AKAAL Provider Catalog & Dynamic Schemas
 * Full 49 Physical Providers + 4 Cloud Profile Resolvers + File Dataset
 * Reconciled against backend connector registry and canonical contracts.
 */

import { ProviderCatalogItem, ManagedCloudProfile } from './create-connection.models';
import { ProviderFormField } from '../../../core/models/provider-form-schemas';

export interface DynamicFormSchema {
  providerId: string;
  name: string;
  category: string;
  defaultPort?: number;
  icon: string;
  fields: ProviderFormField[];
}

export const MANAGED_CLOUD_PROFILES: ManagedCloudProfile[] = [
  {
    id: 'AWS_MANAGED',
    name: 'AWS Managed Cloud',
    vendorName: 'Amazon Web Services',
    icon: 'cloud',
    supportedResourceTypes: [
      { label: 'Amazon RDS PostgreSQL', value: 'RDS_POSTGRESQL', physicalProviderId: 'postgresql' },
      { label: 'Amazon RDS MySQL', value: 'RDS_MYSQL', physicalProviderId: 'mysql' },
      { label: 'Amazon RDS MariaDB', value: 'RDS_MARIADB', physicalProviderId: 'mariadb' },
      { label: 'Amazon RDS Oracle', value: 'RDS_ORACLE', physicalProviderId: 'oracle' },
      { label: 'Amazon RDS SQL Server', value: 'RDS_MSSQL', physicalProviderId: 'mssql' },
      { label: 'Amazon Aurora PostgreSQL', value: 'AURORA_POSTGRESQL', physicalProviderId: 'postgresql' },
      { label: 'Amazon Aurora MySQL', value: 'AURORA_MYSQL', physicalProviderId: 'mysql' }
    ]
  },
  {
    id: 'AZURE_MANAGED',
    name: 'Azure Managed Cloud',
    vendorName: 'Microsoft Azure',
    icon: 'cloud',
    supportedResourceTypes: [
      { label: 'Azure SQL Database', value: 'AZURE_SQL_DB', physicalProviderId: 'mssql' },
      { label: 'Azure SQL Managed Instance', value: 'AZURE_SQL_MI', physicalProviderId: 'mssql' },
      { label: 'Azure Database for PostgreSQL', value: 'AZURE_PG', physicalProviderId: 'postgresql' },
      { label: 'Azure Database for MySQL', value: 'AZURE_MYSQL', physicalProviderId: 'mysql' }
    ]
  },
  {
    id: 'GCP_MANAGED',
    name: 'Google Cloud Managed',
    vendorName: 'Google Cloud Platform',
    icon: 'cloud',
    supportedResourceTypes: [
      { label: 'Cloud SQL PostgreSQL', value: 'CLOUD_SQL_PG', physicalProviderId: 'postgresql' },
      { label: 'Cloud SQL MySQL', value: 'CLOUD_SQL_MYSQL', physicalProviderId: 'mysql' },
      { label: 'Cloud SQL SQL Server', value: 'CLOUD_SQL_MSSQL', physicalProviderId: 'mssql' },
      { label: 'AlloyDB for PostgreSQL', value: 'ALLOYDB_PG', physicalProviderId: 'postgresql' }
    ]
  },
  {
    id: 'OCI_MANAGED',
    name: 'Oracle Cloud Infrastructure Managed',
    vendorName: 'Oracle Cloud',
    icon: 'cloud',
    supportedResourceTypes: [
      { label: 'Autonomous Database (ATP/ADW)', value: 'OCI_AUTONOMOUS', physicalProviderId: 'oracle' },
      { label: 'Base Database Service', value: 'OCI_BASE_DB', physicalProviderId: 'oracle' },
      { label: 'Exadata Cloud Service', value: 'OCI_EXADATA', physicalProviderId: 'oracle' }
    ]
  }
];

export const ALL_PROVIDER_CATALOG_ITEMS: ProviderCatalogItem[] = [
  // =========================================================================
  // 1. RELATIONAL & DISTRIBUTED SQL (17 Providers)
  // =========================================================================
  {
    id: 'sqlite',
    name: 'SQLite',
    family: 'RELATIONAL',
    categoryLabel: 'Relational Database',
    vendorName: 'SQLite Consortium',
    icon: 'database',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: false,
    supportsMtls: false,
    isCustomExtension: false,
    authMethods: [{ label: 'None (Local File System)', value: 'NONE' }],
    defaultAuthMethod: 'NONE',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Embedded standalone file-based SQL database engine'
  },
  {
    id: 'postgresql',
    name: 'PostgreSQL',
    family: 'RELATIONAL',
    categoryLabel: 'Relational Database',
    vendorName: 'PostgreSQL Global Development Group',
    icon: 'database',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: true,
    defaultPort: 5432,
    isCustomExtension: false,
    authMethods: [
      { label: 'Username / Password', value: 'PASSWORD' },
      { label: 'Client Certificate / mTLS', value: 'MTLS' },
      { label: 'Kerberos / GSSAPI', value: 'KERBEROS' },
      { label: 'Cloud IAM Authentication', value: 'IAM' }
    ],
    defaultAuthMethod: 'PASSWORD',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Enterprise open source object-relational database'
  },
  {
    id: 'mysql',
    name: 'MySQL',
    family: 'RELATIONAL',
    categoryLabel: 'Relational Database',
    vendorName: 'Oracle Corporation',
    icon: 'database',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: true,
    defaultPort: 3306,
    isCustomExtension: false,
    authMethods: [
      { label: 'Username / Password', value: 'PASSWORD' },
      { label: 'Client Certificate / mTLS', value: 'MTLS' },
      { label: 'AWS IAM Database Authentication', value: 'AWS_IAM' }
    ],
    defaultAuthMethod: 'PASSWORD',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Universal relational database management system'
  },
  {
    id: 'mariadb',
    name: 'MariaDB',
    family: 'RELATIONAL',
    categoryLabel: 'Relational Database',
    vendorName: 'MariaDB Foundation',
    icon: 'database',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: true,
    defaultPort: 3306,
    isCustomExtension: false,
    authMethods: [
      { label: 'Username / Password', value: 'PASSWORD' },
      { label: 'Client Certificate / mTLS', value: 'MTLS' }
    ],
    defaultAuthMethod: 'PASSWORD',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'High-performance open-source fork of MySQL'
  },
  {
    id: 'oracle',
    name: 'Oracle Database',
    family: 'RELATIONAL',
    categoryLabel: 'Enterprise RDBMS',
    vendorName: 'Oracle Corporation',
    icon: 'database',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: true,
    defaultPort: 1521,
    isCustomExtension: true,
    customExtensionType: 'ORACLE',
    authMethods: [
      { label: 'Username / Password', value: 'PASSWORD' },
      { label: 'Oracle Wallet / Mutual TLS', value: 'WALLET' },
      { label: 'External / OS Authentication', value: 'EXTERNAL_OS' }
    ],
    defaultAuthMethod: 'PASSWORD',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Enterprise multi-model database management system (11g–23c)'
  },
  {
    id: 'mssql',
    name: 'Microsoft SQL Server',
    family: 'RELATIONAL',
    categoryLabel: 'Enterprise RDBMS',
    vendorName: 'Microsoft Corporation',
    icon: 'database',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: false,
    defaultPort: 1433,
    isCustomExtension: false,
    authMethods: [
      { label: 'SQL Server Username / Password', value: 'SQL_AUTH' },
      { label: 'Windows Integrated / Trusted Connection', value: 'WINDOWS_AUTH' },
      { label: 'Microsoft Entra ID (Azure AD)', value: 'ENTRA_ID' }
    ],
    defaultAuthMethod: 'SQL_AUTH',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Relational database server for mission-critical enterprise workloads'
  },
  {
    id: 'ibm_db2',
    name: 'IBM Db2',
    family: 'RELATIONAL',
    categoryLabel: 'Enterprise RDBMS',
    vendorName: 'IBM Corporation',
    icon: 'database',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: true,
    defaultPort: 50000,
    isCustomExtension: false,
    authMethods: [
      { label: 'Username / Password', value: 'PASSWORD' },
      { label: 'Client Certificate / mTLS', value: 'MTLS' },
      { label: 'Kerberos Authentication', value: 'KERBEROS' }
    ],
    defaultAuthMethod: 'PASSWORD',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'High-volume transaction processing and analytics database'
  },
  {
    id: 'cockroachdb',
    name: 'CockroachDB',
    family: 'RELATIONAL',
    categoryLabel: 'Distributed SQL',
    vendorName: 'Cockroach Labs',
    icon: 'database',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: true,
    defaultPort: 26257,
    isCustomExtension: false,
    authMethods: [
      { label: 'Username / Password', value: 'PASSWORD' },
      { label: 'Client Certificate / mTLS', value: 'MTLS' }
    ],
    defaultAuthMethod: 'PASSWORD',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Cloud-native, distributed SQL database with ACID guarantees'
  },
  {
    id: 'yugabytedb',
    name: 'YugabyteDB',
    family: 'RELATIONAL',
    categoryLabel: 'Distributed SQL',
    vendorName: 'Yugabyte',
    icon: 'database',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: true,
    defaultPort: 5433,
    isCustomExtension: false,
    authMethods: [
      { label: 'Username / Password', value: 'PASSWORD' },
      { label: 'Client Certificate / mTLS', value: 'MTLS' }
    ],
    defaultAuthMethod: 'PASSWORD',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'High-performance distributed SQL database with PostgreSQL compatibility'
  },
  {
    id: 'tidb',
    name: 'TiDB',
    family: 'RELATIONAL',
    categoryLabel: 'Distributed HTAP',
    vendorName: 'PingCAP',
    icon: 'database',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: true,
    defaultPort: 4000,
    isCustomExtension: false,
    authMethods: [
      { label: 'Username / Password', value: 'PASSWORD' },
      { label: 'Client Certificate / mTLS', value: 'MTLS' }
    ],
    defaultAuthMethod: 'PASSWORD',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Open-source distributed NewSQL database supporting hybrid transactional/analytical processing'
  },
  {
    id: 'singlestore',
    name: 'SingleStore',
    family: 'RELATIONAL',
    categoryLabel: 'Distributed SQL',
    vendorName: 'SingleStore Inc.',
    icon: 'database',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: false,
    defaultPort: 3306,
    isCustomExtension: false,
    authMethods: [
      { label: 'Username / Password', value: 'PASSWORD' },
      { label: 'API / JWT Token', value: 'TOKEN' }
    ],
    defaultAuthMethod: 'PASSWORD',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Real-time distributed SQL database combining in-memory and disk storage'
  },
  {
    id: 'teradata',
    name: 'Teradata',
    family: 'RELATIONAL',
    categoryLabel: 'Enterprise Analytics',
    vendorName: 'Teradata Corporation',
    icon: 'database',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: false,
    defaultPort: 1025,
    isCustomExtension: false,
    authMethods: [
      { label: 'TD2 (Native Teradata Auth)', value: 'TD2' },
      { label: 'LDAP Directory Authentication', value: 'LDAP' },
      { label: 'Kerberos (KRB5)', value: 'KRB5' }
    ],
    defaultAuthMethod: 'TD2',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Massively parallel processing (MPP) analytical relational database'
  },
  {
    id: 'vertica',
    name: 'Vertica',
    family: 'RELATIONAL',
    categoryLabel: 'Columnar Analytics',
    vendorName: 'OpenText',
    icon: 'database',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: true,
    defaultPort: 5433,
    isCustomExtension: false,
    authMethods: [
      { label: 'Username / Password', value: 'PASSWORD' },
      { label: 'Client Certificate / mTLS', value: 'MTLS' },
      { label: 'Kerberos / GSSAPI', value: 'KERBEROS' }
    ],
    defaultAuthMethod: 'PASSWORD',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Columnar analytical database engineered for fast query performance'
  },
  {
    id: 'sap_hana',
    name: 'SAP HANA',
    family: 'RELATIONAL',
    categoryLabel: 'In-Memory RDBMS',
    vendorName: 'SAP SE',
    icon: 'database',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: true,
    defaultPort: 39015,
    isCustomExtension: false,
    authMethods: [
      { label: 'Username / Password', value: 'PASSWORD' },
      { label: 'X.509 Client Certificate', value: 'X509' },
      { label: 'Enterprise Token / JWT', value: 'TOKEN' }
    ],
    defaultAuthMethod: 'PASSWORD',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Column-oriented in-memory relational database management system'
  },
  {
    id: 'sap_ase',
    name: 'SAP ASE / Sybase',
    family: 'RELATIONAL',
    categoryLabel: 'Enterprise RDBMS',
    vendorName: 'SAP SE',
    icon: 'database',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: false,
    defaultPort: 5000,
    isCustomExtension: false,
    authMethods: [
      { label: 'Username / Password', value: 'PASSWORD' },
      { label: 'Integrated Authentication', value: 'INTEGRATED' }
    ],
    defaultAuthMethod: 'PASSWORD',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'High-performance transactional database (formerly Sybase SQL Server)'
  },
  {
    id: 'informix',
    name: 'IBM Informix',
    family: 'RELATIONAL',
    categoryLabel: 'Enterprise RDBMS',
    vendorName: 'IBM Corporation',
    icon: 'database',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: false,
    defaultPort: 9088,
    isCustomExtension: false,
    authMethods: [
      { label: 'Username / Password', value: 'PASSWORD' }
    ],
    defaultAuthMethod: 'PASSWORD',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Embeddable high-availability relational and time-series database'
  },
  {
    id: 'spanner',
    name: 'Google Cloud Spanner',
    family: 'RELATIONAL',
    categoryLabel: 'Globally Distributed SQL',
    vendorName: 'Google Cloud',
    icon: 'database',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: false,
    isCustomExtension: true,
    customExtensionType: 'SPANNER',
    authMethods: [
      { label: 'Application Default Credentials (ADC)', value: 'ADC' },
      { label: 'Google Service Account Key', value: 'SERVICE_ACCOUNT' }
    ],
    defaultAuthMethod: 'ADC',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Fully managed, mission-critical relational database with global scale and strong consistency'
  },

  // =========================================================================
  // 2. WAREHOUSE & LAKE (5 Providers)
  // =========================================================================
  {
    id: 'snowflake',
    name: 'Snowflake',
    family: 'WAREHOUSE_LAKE',
    categoryLabel: 'Data Cloud Warehouse',
    vendorName: 'Snowflake Inc.',
    icon: 'layers',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: false,
    defaultPort: 443,
    isCustomExtension: false,
    authMethods: [
      { label: 'Username / Password', value: 'PASSWORD' },
      { label: 'Key Pair Authentication (RSA 2048)', value: 'KEY_PAIR' },
      { label: 'OAuth 2.0 Access Token', value: 'OAUTH' }
    ],
    defaultAuthMethod: 'PASSWORD',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Cloud-native multi-cluster shared data platform and warehouse'
  },
  {
    id: 'bigquery',
    name: 'Google BigQuery',
    family: 'WAREHOUSE_LAKE',
    categoryLabel: 'Serverless Data Warehouse',
    vendorName: 'Google Cloud',
    icon: 'layers',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: false,
    isCustomExtension: true,
    customExtensionType: 'BIGQUERY',
    authMethods: [
      { label: 'Application Default Credentials (ADC)', value: 'ADC' },
      { label: 'Google Service Account Key', value: 'SERVICE_ACCOUNT' }
    ],
    defaultAuthMethod: 'ADC',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Serverless, highly-scalable enterprise data warehouse'
  },
  {
    id: 'redshift',
    name: 'Amazon Redshift',
    family: 'WAREHOUSE_LAKE',
    categoryLabel: 'Cloud Data Warehouse',
    vendorName: 'Amazon Web Services',
    icon: 'layers',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: false,
    defaultPort: 5439,
    isCustomExtension: false,
    authMethods: [
      { label: 'Database Username / Password', value: 'PASSWORD' },
      { label: 'AWS IAM Role / Credential Chain', value: 'AWS_IAM' }
    ],
    defaultAuthMethod: 'PASSWORD',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Fast, fully-managed, petabyte-scale cloud data warehouse'
  },
  {
    id: 'databricks',
    name: 'Databricks',
    family: 'WAREHOUSE_LAKE',
    categoryLabel: 'Lakehouse & Spark',
    vendorName: 'Databricks Inc.',
    icon: 'layers',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: false,
    defaultPort: 443,
    isCustomExtension: false,
    authMethods: [
      { label: 'Personal Access Token (PAT)', value: 'PAT' },
      { label: 'Microsoft Entra ID (Azure)', value: 'ENTRA_ID' },
      { label: 'Cloud / Workload Identity', value: 'WORKLOAD_IDENTITY' }
    ],
    defaultAuthMethod: 'PAT',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Unified lakehouse platform for SQL analytics, BI, and data science'
  },
  {
    id: 'clickhouse',
    name: 'ClickHouse',
    family: 'WAREHOUSE_LAKE',
    categoryLabel: 'Columnar OLAP',
    vendorName: 'ClickHouse Inc.',
    icon: 'layers',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: true,
    defaultPort: 8123,
    isCustomExtension: false,
    authMethods: [
      { label: 'Username / Password', value: 'PASSWORD' },
      { label: 'Client Certificate / mTLS', value: 'MTLS' }
    ],
    defaultAuthMethod: 'PASSWORD',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'High-performance columnar analytics database for real-time reporting'
  },

  // =========================================================================
  // 3. NOSQL, GRAPH, KV & SEARCH (11 Providers)
  // =========================================================================
  {
    id: 'mongodb',
    name: 'MongoDB',
    family: 'NOSQL_GRAPH',
    categoryLabel: 'Document Database',
    vendorName: 'MongoDB Inc.',
    icon: 'box',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: true,
    defaultPort: 27017,
    isCustomExtension: false,
    authMethods: [
      { label: 'SCRAM (Username / Password)', value: 'SCRAM' },
      { label: 'Client Certificate / X.509', value: 'X509' },
      { label: 'AWS IAM Authentication', value: 'AWS_IAM' }
    ],
    defaultAuthMethod: 'SCRAM',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'General-purpose document-based distributed database'
  },
  {
    id: 'cassandra',
    name: 'Apache Cassandra',
    family: 'NOSQL_GRAPH',
    categoryLabel: 'Wide-Column Store',
    vendorName: 'Apache Software Foundation',
    icon: 'box',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: true,
    defaultPort: 9042,
    isCustomExtension: false,
    authMethods: [
      { label: 'Username / Password', value: 'PASSWORD' },
      { label: 'Client Certificate / mTLS', value: 'MTLS' }
    ],
    defaultAuthMethod: 'PASSWORD',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Distributed wide-column NoSQL store designed for high scalability'
  },
  {
    id: 'scylladb',
    name: 'ScyllaDB',
    family: 'NOSQL_GRAPH',
    categoryLabel: 'Wide-Column Store',
    vendorName: 'ScyllaDB Inc.',
    icon: 'box',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: true,
    defaultPort: 9042,
    isCustomExtension: false,
    authMethods: [
      { label: 'Username / Password', value: 'PASSWORD' },
      { label: 'Client Certificate / mTLS', value: 'MTLS' }
    ],
    defaultAuthMethod: 'PASSWORD',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Ultra-fast C++ Cassandra-compatible distributed database'
  },
  {
    id: 'neo4j',
    name: 'Neo4j',
    family: 'NOSQL_GRAPH',
    categoryLabel: 'Graph Database',
    vendorName: 'Neo4j Inc.',
    icon: 'git-branch',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: false,
    defaultPort: 7687,
    isCustomExtension: false,
    authMethods: [
      { label: 'Username / Password', value: 'PASSWORD' },
      { label: 'Bearer Token', value: 'BEARER_TOKEN' }
    ],
    defaultAuthMethod: 'PASSWORD',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Native graph database designed for complex connected data'
  },
  {
    id: 'redis',
    name: 'Redis',
    family: 'NOSQL_GRAPH',
    categoryLabel: 'In-Memory Key-Value',
    vendorName: 'Redis Ltd.',
    icon: 'box',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: true,
    defaultPort: 6379,
    isCustomExtension: false,
    authMethods: [
      { label: 'Password Only', value: 'PASSWORD_ONLY' },
      { label: 'ACL Username + Password', value: 'ACL_PASSWORD' },
      { label: 'Client Certificate / mTLS', value: 'MTLS' },
      { label: 'None (Unauthenticated Local)', value: 'NONE' }
    ],
    defaultAuthMethod: 'ACL_PASSWORD',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'In-memory data structure store used as database, cache, and message broker'
  },
  {
    id: 'keydb',
    name: 'KeyDB',
    family: 'NOSQL_GRAPH',
    categoryLabel: 'Multithreaded Key-Value',
    vendorName: 'Snap Inc.',
    icon: 'box',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: true,
    defaultPort: 6379,
    isCustomExtension: false,
    authMethods: [
      { label: 'Password', value: 'PASSWORD' },
      { label: 'Client Certificate / mTLS', value: 'MTLS' },
      { label: 'None', value: 'NONE' }
    ],
    defaultAuthMethod: 'PASSWORD',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'High-throughput, multithreaded alternative to Redis'
  },
  {
    id: 'elasticsearch',
    name: 'Elasticsearch',
    family: 'NOSQL_GRAPH',
    categoryLabel: 'Distributed Search',
    vendorName: 'Elastic N.V.',
    icon: 'search',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: true,
    defaultPort: 9200,
    isCustomExtension: false,
    authMethods: [
      { label: 'Username / Password', value: 'PASSWORD' },
      { label: 'API Key', value: 'API_KEY' },
      { label: 'Client Certificate / mTLS', value: 'MTLS' }
    ],
    defaultAuthMethod: 'PASSWORD',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Distributed, JSON-based search and analytics engine'
  },
  {
    id: 'opensearch',
    name: 'OpenSearch',
    family: 'NOSQL_GRAPH',
    categoryLabel: 'Distributed Search',
    vendorName: 'OpenSearch Project',
    icon: 'search',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: true,
    defaultPort: 9200,
    isCustomExtension: false,
    authMethods: [
      { label: 'Username / Password', value: 'PASSWORD' },
      { label: 'API Key', value: 'API_KEY' },
      { label: 'AWS SigV4 / IAM', value: 'AWS_SIGV4' }
    ],
    defaultAuthMethod: 'PASSWORD',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Community-driven search and analytics suite derived from Elasticsearch'
  },
  {
    id: 'dynamodb',
    name: 'Amazon DynamoDB',
    family: 'NOSQL_GRAPH',
    categoryLabel: 'Managed NoSQL',
    vendorName: 'Amazon Web Services',
    icon: 'box',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: false,
    defaultPort: 443,
    isCustomExtension: false,
    authMethods: [
      { label: 'Default AWS Credential Chain', value: 'AWS_CHAIN' },
      { label: 'IAM Role ARN (STS AssumeRole)', value: 'IAM_ROLE' },
      { label: 'Access Key ID & Secret Access Key', value: 'ACCESS_KEYS' }
    ],
    defaultAuthMethod: 'AWS_CHAIN',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Fast, flexible, serverless key-value and document database'
  },
  {
    id: 'couchbase',
    name: 'Couchbase',
    family: 'NOSQL_GRAPH',
    categoryLabel: 'Document & KV Store',
    vendorName: 'Couchbase Inc.',
    icon: 'box',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: true,
    defaultPort: 8091,
    isCustomExtension: false,
    authMethods: [
      { label: 'Username / Password', value: 'PASSWORD' },
      { label: 'Client Certificate / mTLS', value: 'MTLS' }
    ],
    defaultAuthMethod: 'PASSWORD',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Distributed multi-model NoSQL document database'
  },
  {
    id: 'cosmosdb',
    name: 'Azure Cosmos DB',
    family: 'NOSQL_GRAPH',
    categoryLabel: 'Multi-Model Distributed NoSQL',
    vendorName: 'Microsoft Azure',
    icon: 'box',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: false,
    defaultPort: 443,
    isCustomExtension: false,
    authMethods: [
      { label: 'Account Primary / Secondary Key', value: 'ACCOUNT_KEY' },
      { label: 'Microsoft Entra ID (Azure AD)', value: 'ENTRA_ID' }
    ],
    defaultAuthMethod: 'ACCOUNT_KEY',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Globally distributed, multi-model database service (SQL/MongoDB/Cassandra APIs)'
  },

  // =========================================================================
  // 4. STREAMING & MESSAGING (6 Providers)
  // =========================================================================
  {
    id: 'kafka',
    name: 'Apache Kafka',
    family: 'STREAMING',
    categoryLabel: 'Distributed Event Streaming',
    vendorName: 'Apache Software Foundation',
    icon: 'radio',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: true,
    defaultPort: 9092,
    isCustomExtension: false,
    authMethods: [
      { label: 'PLAINTEXT (Unauthenticated)', value: 'PLAINTEXT' },
      { label: 'SASL / PLAIN', value: 'SASL_PLAIN' },
      { label: 'SASL / SCRAM-SHA-256', value: 'SASL_SCRAM_256' },
      { label: 'SASL / SCRAM-SHA-512', value: 'SASL_SCRAM_512' },
      { label: 'Kerberos / GSSAPI', value: 'GSSAPI' },
      { label: 'AWS MSK IAM', value: 'AWS_MSK_IAM' }
    ],
    defaultAuthMethod: 'SASL_SCRAM_512',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE'],
    description: 'High-throughput distributed event streaming platform'
  },
  {
    id: 'kinesis',
    name: 'Amazon Kinesis',
    family: 'STREAMING',
    categoryLabel: 'Managed Stream Service',
    vendorName: 'Amazon Web Services',
    icon: 'radio',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: false,
    defaultPort: 443,
    isCustomExtension: false,
    authMethods: [
      { label: 'Default AWS Credential Chain', value: 'AWS_CHAIN' },
      { label: 'IAM Role ARN (STS AssumeRole)', value: 'IAM_ROLE' },
      { label: 'Access Key ID & Secret Access Key', value: 'ACCESS_KEYS' }
    ],
    defaultAuthMethod: 'AWS_CHAIN',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE'],
    description: 'Managed real-time streaming data ingestion and processing'
  },
  {
    id: 'eventhubs',
    name: 'Azure Event Hubs',
    family: 'STREAMING',
    categoryLabel: 'Cloud Event Ingestion',
    vendorName: 'Microsoft Azure',
    icon: 'radio',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: false,
    defaultPort: 443,
    isCustomExtension: false,
    authMethods: [
      { label: 'Shared Access Signature (SAS) Connection String', value: 'SAS_CONN_STRING' },
      { label: 'Microsoft Entra ID (Azure AD)', value: 'ENTRA_ID' },
      { label: 'Azure Managed Identity', value: 'MANAGED_IDENTITY' }
    ],
    defaultAuthMethod: 'SAS_CONN_STRING',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE'],
    description: 'Fully-managed real-time data ingestion service'
  },
  {
    id: 'pubsub',
    name: 'Google Pub/Sub',
    family: 'STREAMING',
    categoryLabel: 'Asynchronous Messaging',
    vendorName: 'Google Cloud',
    icon: 'radio',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: false,
    isCustomExtension: false,
    authMethods: [
      { label: 'Application Default Credentials (ADC)', value: 'ADC' },
      { label: 'Google Service Account Key', value: 'SERVICE_ACCOUNT' }
    ],
    defaultAuthMethod: 'ADC',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE'],
    description: 'Global distributed asynchronous messaging and stream ingestion'
  },
  {
    id: 'rabbitmq',
    name: 'RabbitMQ',
    family: 'STREAMING',
    categoryLabel: 'AMQP Message Broker',
    vendorName: 'VMware Tanzu',
    icon: 'radio',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: true,
    defaultPort: 5672,
    isCustomExtension: false,
    authMethods: [
      { label: 'Username / Password', value: 'PASSWORD' },
      { label: 'Client Certificate / mTLS', value: 'MTLS' }
    ],
    defaultAuthMethod: 'PASSWORD',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE'],
    description: 'Robust, widely-deployed open source message broker (AMQP)'
  },
  {
    id: 'pulsar',
    name: 'Apache Pulsar',
    family: 'STREAMING',
    categoryLabel: 'Multi-Tenant Messaging',
    vendorName: 'Apache Software Foundation',
    icon: 'radio',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: true,
    defaultPort: 6650,
    isCustomExtension: false,
    authMethods: [
      { label: 'JWT Token / Secret', value: 'TOKEN' },
      { label: 'OAuth 2.0 Client Credentials', value: 'OAUTH2' },
      { label: 'Client Certificate / mTLS', value: 'MTLS' },
      { label: 'None (Unauthenticated)', value: 'NONE' }
    ],
    defaultAuthMethod: 'TOKEN',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE'],
    description: 'Cloud-native, distributed messaging and streaming platform'
  },

  // =========================================================================
  // 5. OBJECT & DISTRIBUTED STORAGE (6 Providers)
  // =========================================================================
  {
    id: 's3',
    name: 'Amazon S3',
    family: 'OBJECT_STORAGE',
    categoryLabel: 'Object Storage',
    vendorName: 'Amazon Web Services',
    icon: 'hard-drive',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: false,
    defaultPort: 443,
    isCustomExtension: false,
    authMethods: [
      { label: 'Default AWS Credential Chain', value: 'AWS_CHAIN' },
      { label: 'IAM Role ARN (STS AssumeRole)', value: 'IAM_ROLE' },
      { label: 'Access Key ID & Secret Access Key', value: 'ACCESS_KEYS' }
    ],
    defaultAuthMethod: 'AWS_CHAIN',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Scalable object storage service for data lakes, archives, and bulk transport'
  },
  {
    id: 'gcs',
    name: 'Google Cloud Storage',
    family: 'OBJECT_STORAGE',
    categoryLabel: 'Object Storage',
    vendorName: 'Google Cloud',
    icon: 'hard-drive',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: false,
    isCustomExtension: false,
    authMethods: [
      { label: 'Application Default Credentials (ADC)', value: 'ADC' },
      { label: 'Google Service Account Key', value: 'SERVICE_ACCOUNT' }
    ],
    defaultAuthMethod: 'ADC',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Unified object storage for developers and enterprise enterprises'
  },
  {
    id: 'azure_blob',
    name: 'Azure Blob Storage',
    family: 'OBJECT_STORAGE',
    categoryLabel: 'Object Storage',
    vendorName: 'Microsoft Azure',
    icon: 'hard-drive',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: false,
    defaultPort: 443,
    isCustomExtension: false,
    authMethods: [
      { label: 'Storage Account Key', value: 'ACCOUNT_KEY' },
      { label: 'Shared Access Signature (SAS) Token', value: 'SAS_TOKEN' },
      { label: 'Storage Connection String', value: 'CONN_STRING' },
      { label: 'Microsoft Entra ID', value: 'ENTRA_ID' }
    ],
    defaultAuthMethod: 'ACCOUNT_KEY',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Massively scalable and secure object storage for cloud-native workloads'
  },
  {
    id: 'minio',
    name: 'MinIO',
    family: 'OBJECT_STORAGE',
    categoryLabel: 'S3-Compatible Object Store',
    vendorName: 'MinIO Inc.',
    icon: 'hard-drive',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: true,
    defaultPort: 9000,
    isCustomExtension: false,
    authMethods: [
      { label: 'Access Key & Secret Key', value: 'ACCESS_KEYS' }
    ],
    defaultAuthMethod: 'ACCESS_KEYS',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'High-performance, S3-compatible object storage for private cloud and Kubernetes'
  },
  {
    id: 'hdfs',
    name: 'Apache HDFS',
    family: 'OBJECT_STORAGE',
    categoryLabel: 'Distributed File System',
    vendorName: 'Apache Software Foundation',
    icon: 'hard-drive',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: false,
    defaultPort: 8020,
    isCustomExtension: false,
    authMethods: [
      { label: 'Simple / OS Username', value: 'SIMPLE' },
      { label: 'Kerberos Principal & Keytab', value: 'KERBEROS' }
    ],
    defaultAuthMethod: 'SIMPLE',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Distributed file system designed to run on commodity hardware'
  },
  {
    id: 'oci_object_storage',
    name: 'OCI Object Storage',
    family: 'OBJECT_STORAGE',
    categoryLabel: 'Object Storage',
    vendorName: 'Oracle Cloud',
    icon: 'hard-drive',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: false,
    defaultPort: 443,
    isCustomExtension: false,
    authMethods: [
      { label: 'OCI Config File (API Key + User OCID)', value: 'OCI_CONFIG' },
      { label: 'Instance Principal', value: 'INSTANCE_PRINCIPAL' },
      { label: 'Resource Principal', value: 'RESOURCE_PRINCIPAL' }
    ],
    defaultAuthMethod: 'OCI_CONFIG',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'High-performance internet-scale storage platform in Oracle Cloud'
  },

  // =========================================================================
  // 6. TIME-SERIES (1 Provider)
  // =========================================================================
  {
    id: 'influxdb',
    name: 'InfluxDB',
    family: 'TIME_SERIES',
    categoryLabel: 'Time-Series Database',
    vendorName: 'InfluxData',
    icon: 'activity',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: false,
    defaultPort: 8086,
    isCustomExtension: false,
    authMethods: [
      { label: 'API Token / Secret (v2)', value: 'TOKEN' },
      { label: 'Legacy Username & Password (v1)', value: 'LEGACY_USER_PASS' }
    ],
    defaultAuthMethod: 'TOKEN',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Time-series database designed for high-write-volume operational metrics'
  },

  // =========================================================================
  // 7. ENTERPRISE APPLICATIONS (3 Providers)
  // =========================================================================
  {
    id: 'salesforce',
    name: 'Salesforce',
    family: 'APPLICATION',
    categoryLabel: 'Enterprise CRM / SaaS',
    vendorName: 'Salesforce Inc.',
    icon: 'briefcase',
    roleApplicability: 'SOURCE_ONLY',
    supportsTls: true,
    supportsMtls: false,
    defaultPort: 443,
    isCustomExtension: true,
    customExtensionType: 'SALESFORCE',
    authMethods: [
      { label: 'OAuth 2.0 Client Credentials', value: 'OAUTH' },
      { label: 'JWT Bearer Token Flow', value: 'JWT_BEARER' },
      { label: 'Username / Password + Security Token', value: 'USERNAME_PASSWORD' }
    ],
    defaultAuthMethod: 'OAUTH',
    supportedRoles: ['SOURCE', 'REFERENCE'],
    description: 'Customer relationship management and enterprise SaaS platform'
  },
  {
    id: 'servicenow',
    name: 'ServiceNow',
    family: 'APPLICATION',
    categoryLabel: 'Enterprise ITSM / SaaS',
    vendorName: 'ServiceNow Inc.',
    icon: 'briefcase',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: false,
    defaultPort: 443,
    isCustomExtension: true,
    customExtensionType: 'SERVICENOW',
    authMethods: [
      { label: 'Basic Authentication', value: 'BASIC' },
      { label: 'OAuth 2.0', value: 'OAUTH' }
    ],
    defaultAuthMethod: 'BASIC',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE'],
    description: 'Cloud-based IT service management and digital workflow platform'
  },
  {
    id: 'sap_application',
    name: 'SAP Application',
    family: 'APPLICATION',
    categoryLabel: 'Enterprise ERP Suite',
    vendorName: 'SAP SE',
    icon: 'briefcase',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: true,
    supportsMtls: true,
    defaultPort: 3300,
    isCustomExtension: true,
    customExtensionType: 'SAP_APPLICATION',
    authMethods: [
      { label: 'SAP User / Password', value: 'SAP_USER_PASS' },
      { label: 'SNC (Secure Network Communications)', value: 'SNC' }
    ],
    defaultAuthMethod: 'SAP_USER_PASS',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE'],
    description: 'Enterprise resource planning system (RFC / BAPI / OData endpoints)'
  },

  // =========================================================================
  // 8. FILE DATASET
  // =========================================================================
  {
    id: 'file_dataset',
    name: 'File Dataset',
    family: 'OBJECT_STORAGE',
    categoryLabel: 'File Transport Driver',
    vendorName: 'AKAAL Local / Network FS',
    icon: 'file-text',
    roleApplicability: 'SOURCE_AND_TARGET',
    supportsTls: false,
    supportsMtls: false,
    isCustomExtension: false,
    authMethods: [{ label: 'Local Filesystem Permissions', value: 'LOCAL_PERMS' }],
    defaultAuthMethod: 'LOCAL_PERMS',
    supportedRoles: ['SOURCE', 'TARGET', 'REFERENCE', 'VALIDATION'],
    description: 'Direct tabular file dataset transport (CSV, JSONL, Parquet formats)'
  }
];
