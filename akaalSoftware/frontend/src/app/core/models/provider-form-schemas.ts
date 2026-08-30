import { PhysicalProviderId, ProviderCategory } from './migration-view.models';

export type ProviderFormFieldType =
  | 'text'
  | 'number'
  | 'password'
  | 'secret_ref'
  | 'boolean'
  | 'select'
  | 'textarea'
  | 'file_path';

export interface ProviderFormFieldOption {
  label: string;
  value: any;
}

export interface ProviderFormField {
  id: string;
  label: string;
  type: ProviderFormFieldType;
  placeholder?: string;
  defaultValue?: any;
  required?: boolean;
  helpText?: string;
  options?: ProviderFormFieldOption[];
  dependsOn?: string;
  conditionValue?: any;
  group: 'ENDPOINT' | 'AUTH' | 'SECURITY' | 'OPTIONS';
}

export interface ProviderFormSchema {
  providerId: PhysicalProviderId;
  name: string;
  category: ProviderCategory;
  defaultPort?: number;
  icon: string;
  fields: ProviderFormField[];
}

export const ALL_28_PROVIDER_SCHEMAS: Record<PhysicalProviderId, ProviderFormSchema> = {
  // ==========================================================================
  // 1. RELATIONAL DATABASES (7)
  // ==========================================================================
  'SQLite': {
    providerId: 'SQLite',
    name: 'SQLite Database',
    category: 'RELATIONAL',
    icon: 'database',
    fields: [
      { id: 'database_path', label: 'Database File Path *', type: 'file_path', placeholder: '/var/data/app.db or :memory:', required: true, helpText: 'Full filesystem path to the .db file or :memory:', group: 'ENDPOINT' },
      { id: 'lock_timeout', label: 'Lock Timeout (seconds)', type: 'number', defaultValue: 10.0, helpText: 'Timeout when waiting for file locks', group: 'OPTIONS' }
    ]
  },

  'PostgreSQL': {
    providerId: 'PostgreSQL',
    name: 'PostgreSQL Database',
    category: 'RELATIONAL',
    defaultPort: 5432,
    icon: 'database',
    fields: [
      { id: 'host', label: 'Host / IP Address *', type: 'text', placeholder: 'postgres.company.internal', required: true, helpText: 'Database hostname or server IP', group: 'ENDPOINT' },
      { id: 'port', label: 'Port', type: 'number', defaultValue: 5432, helpText: 'TCP port', group: 'ENDPOINT' },
      { id: 'database', label: 'Database Name *', type: 'text', placeholder: 'production_db', required: true, helpText: 'Target database name', group: 'ENDPOINT' },
      { id: 'schema', label: 'Schema Name', type: 'text', defaultValue: 'public', placeholder: 'public', helpText: 'Default schema search path', group: 'ENDPOINT' },
      { id: 'username', label: 'Username *', type: 'text', placeholder: 'postgres', required: true, helpText: 'Database login user', group: 'AUTH' },
      { id: 'secret_ref', label: 'Password / Vault Secret Reference *', type: 'secret_ref', placeholder: 'vault://secret/prod/pg_pass', required: true, helpText: 'Database user password or Vault URI', group: 'AUTH' },
      { id: 'ssl_mode', label: 'SSL / TLS Mode', type: 'select', defaultValue: 'prefer', options: [{ label: 'Prefer (Default)', value: 'prefer' }, { label: 'Disable', value: 'disable' }, { label: 'Require', value: 'require' }, { label: 'Verify-CA', value: 'verify-ca' }, { label: 'Verify-Full', value: 'verify-full' }], helpText: 'Encryption level for connection', group: 'SECURITY' },
      { id: 'connect_timeout', label: 'Connection Timeout (s)', type: 'number', defaultValue: 15, helpText: 'TCP network timeout', group: 'OPTIONS' }
    ]
  },

  'MySQL': {
    providerId: 'MySQL',
    name: 'MySQL Database',
    category: 'RELATIONAL',
    defaultPort: 3306,
    icon: 'database',
    fields: [
      { id: 'host', label: 'Host / IP Address *', type: 'text', placeholder: 'mysql.company.internal', required: true, helpText: 'Database hostname or server IP', group: 'ENDPOINT' },
      { id: 'port', label: 'Port', type: 'number', defaultValue: 3306, helpText: 'MySQL listener port', group: 'ENDPOINT' },
      { id: 'database', label: 'Database Name *', type: 'text', placeholder: 'ecommerce_db', required: true, helpText: 'Target database schema', group: 'ENDPOINT' },
      { id: 'username', label: 'Username *', type: 'text', placeholder: 'root or app_user', required: true, helpText: 'Database login user', group: 'AUTH' },
      { id: 'secret_ref', label: 'Password / Vault Secret Reference *', type: 'secret_ref', placeholder: 'vault://secret/prod/mysql_pass', required: true, helpText: 'Database password or Vault pointer', group: 'AUTH' },
      { id: 'charset', label: 'Character Set', type: 'text', defaultValue: 'utf8mb4', placeholder: 'utf8mb4', helpText: 'Encoding charset', group: 'OPTIONS' },
      { id: 'connect_timeout', label: 'Connection Timeout (s)', type: 'number', defaultValue: 15, helpText: 'TCP network timeout', group: 'OPTIONS' }
    ]
  },

  'MariaDB': {
    providerId: 'MariaDB',
    name: 'MariaDB Database',
    category: 'RELATIONAL',
    defaultPort: 3306,
    icon: 'database',
    fields: [
      { id: 'host', label: 'Host / IP Address *', type: 'text', placeholder: 'mariadb.company.internal', required: true, helpText: 'Server hostname or IP', group: 'ENDPOINT' },
      { id: 'port', label: 'Port', type: 'number', defaultValue: 3306, helpText: 'MariaDB port', group: 'ENDPOINT' },
      { id: 'database', label: 'Database Name *', type: 'text', placeholder: 'app_db', required: true, helpText: 'Target database name', group: 'ENDPOINT' },
      { id: 'username', label: 'Username *', type: 'text', placeholder: 'db_user', required: true, helpText: 'Database login user', group: 'AUTH' },
      { id: 'secret_ref', label: 'Password / Vault Secret Reference *', type: 'secret_ref', placeholder: 'vault://secret/prod/mariadb_pass', required: true, helpText: 'Database password', group: 'AUTH' },
      { id: 'charset', label: 'Character Set', type: 'text', defaultValue: 'utf8mb4', placeholder: 'utf8mb4', helpText: 'Character encoding', group: 'OPTIONS' },
      { id: 'connect_timeout', label: 'Connection Timeout (s)', type: 'number', defaultValue: 15, helpText: 'TCP network timeout', group: 'OPTIONS' }
    ]
  },

  'Oracle': {
    providerId: 'Oracle',
    name: 'Oracle Database',
    category: 'RELATIONAL',
    defaultPort: 1521,
    icon: 'database',
    fields: [
      { id: 'connection_type', label: 'Connection Type *', type: 'select', defaultValue: 'SERVICE_NAME', options: [{ label: 'Service Name', value: 'SERVICE_NAME' }, { label: 'SID (System Identifier)', value: 'SID' }, { label: 'TNS Descriptor / Alias', value: 'TNS_DESCRIPTOR' }, { label: 'Oracle Cloud Wallet', value: 'WALLET' }], required: true, helpText: 'How Oracle resolves the target instance', group: 'ENDPOINT' },
      { id: 'host', label: 'Host / IP Address *', type: 'text', placeholder: 'oracle.company.internal', required: true, dependsOn: 'connection_type', conditionValue: 'SERVICE_NAME', helpText: 'Database listener hostname', group: 'ENDPOINT' },
      { id: 'port', label: 'Port', type: 'number', defaultValue: 1521, dependsOn: 'connection_type', conditionValue: 'SERVICE_NAME', helpText: 'Oracle listener port', group: 'ENDPOINT' },
      { id: 'service_name', label: 'Service Name *', type: 'text', placeholder: 'ORCLPDB1', required: true, dependsOn: 'connection_type', conditionValue: 'SERVICE_NAME', helpText: 'Pluggable Database (PDB) or Service', group: 'ENDPOINT' },
      { id: 'sid', label: 'SID *', type: 'text', placeholder: 'ORCL', required: true, dependsOn: 'connection_type', conditionValue: 'SID', helpText: 'Oracle System Identifier (SID)', group: 'ENDPOINT' },
      { id: 'tns_descriptor', label: 'TNS Descriptor *', type: 'textarea', placeholder: 'MY_ORACLE_TNS', required: true, dependsOn: 'connection_type', conditionValue: 'TNS_DESCRIPTOR', helpText: 'TNS alias from tnsnames.ora', group: 'ENDPOINT' },
      { id: 'wallet_path', label: 'Wallet Directory / Zip *', type: 'file_path', placeholder: '/path/to/wallet or C:\\wallet', required: true, dependsOn: 'connection_type', conditionValue: 'WALLET', helpText: 'Oracle Wallet path (cwallet.sso)', group: 'ENDPOINT' },
      { id: 'wallet_password', label: 'Wallet Password', type: 'password', placeholder: '••••••••••••', dependsOn: 'connection_type', conditionValue: 'WALLET', helpText: 'Password to unlock Oracle Wallet', group: 'AUTH' },
      { id: 'username', label: 'Username *', type: 'text', placeholder: 'SYSTEM or HR', required: true, helpText: 'Oracle database user schema', group: 'AUTH' },
      { id: 'secret_ref', label: 'Password / Vault Secret Reference *', type: 'secret_ref', placeholder: 'vault://secret/prod/oracle_pass', required: true, helpText: 'Oracle user password', group: 'AUTH' },
      { id: 'privilege_mode', label: 'Privilege Mode', type: 'select', defaultValue: 'NORMAL', options: [{ label: 'NORMAL', value: 'NORMAL' }, { label: 'SYSDBA', value: 'SYSDBA' }, { label: 'SYSOPER', value: 'SYSOPER' }], helpText: 'Connection privilege level', group: 'OPTIONS' },
      { id: 'driver_mode', label: 'Driver Mode', type: 'select', defaultValue: 'THIN', options: [{ label: 'THIN (Pure Java / Network Driver)', value: 'THIN' }, { label: 'THICK (OCI Client Library)', value: 'THICK' }], helpText: 'Execution driver mode', group: 'OPTIONS' }
    ]
  },

  'Microsoft SQL Server': {
    providerId: 'Microsoft SQL Server',
    name: 'Microsoft SQL Server (MSSQL)',
    category: 'RELATIONAL',
    defaultPort: 1433,
    icon: 'server',
    fields: [
      { id: 'host', label: 'Host / Server Name *', type: 'text', placeholder: 'sqlserver.company.internal or db-server\\SQLEXPRESS', required: true, helpText: 'Server host, IP, or named instance', group: 'ENDPOINT' },
      { id: 'port', label: 'Port', type: 'number', defaultValue: 1433, helpText: 'SQL Server listener port', group: 'ENDPOINT' },
      { id: 'database', label: 'Database Name *', type: 'text', placeholder: 'master or SalesDB', required: true, helpText: 'Target database name', group: 'ENDPOINT' },
      { id: 'auth_type', label: 'Authentication Type *', type: 'select', defaultValue: 'SQL_AUTH', options: [{ label: 'SQL Server Authentication', value: 'SQL_AUTH' }, { label: 'Windows Integrated (SSPI)', value: 'WINDOWS_SSPI' }], required: true, helpText: 'Authentication method', group: 'AUTH' },
      { id: 'username', label: 'Username *', type: 'text', placeholder: 'sa or app_login', required: true, dependsOn: 'auth_type', conditionValue: 'SQL_AUTH', helpText: 'SQL Server user login', group: 'AUTH' },
      { id: 'secret_ref', label: 'Password / Vault Secret Reference *', type: 'secret_ref', placeholder: 'vault://secret/prod/mssql_pass', required: true, dependsOn: 'auth_type', conditionValue: 'SQL_AUTH', helpText: 'Login password or Vault URI', group: 'AUTH' },
      { id: 'odbc_driver', label: 'ODBC Driver', type: 'text', defaultValue: 'ODBC Driver 17 for SQL Server', placeholder: 'ODBC Driver 17 for SQL Server', helpText: 'Installed system driver', group: 'OPTIONS' }
    ]
  },

  'IBM Db2': {
    providerId: 'IBM Db2',
    name: 'IBM Db2 LUW',
    category: 'RELATIONAL',
    defaultPort: 50000,
    icon: 'hard-drive',
    fields: [
      { id: 'host', label: 'Host / IP Address *', type: 'text', placeholder: 'db2.company.internal', required: true, helpText: 'DB2 server hostname', group: 'ENDPOINT' },
      { id: 'port', label: 'Port', type: 'number', defaultValue: 50000, helpText: 'DB2 port', group: 'ENDPOINT' },
      { id: 'database', label: 'Database Name *', type: 'text', placeholder: 'SAMPLE', required: true, helpText: 'Target database name', group: 'ENDPOINT' },
      { id: 'schema', label: 'Schema Name', type: 'text', defaultValue: 'DB2INST1', placeholder: 'DB2INST1', helpText: 'Default schema path', group: 'ENDPOINT' },
      { id: 'username', label: 'Username *', type: 'text', placeholder: 'db2inst1', required: true, helpText: 'DB2 user account', group: 'AUTH' },
      { id: 'secret_ref', label: 'Password / Vault Secret Reference *', type: 'secret_ref', placeholder: 'vault://secret/prod/db2_pass', required: true, helpText: 'DB2 user password', group: 'AUTH' }
    ]
  },

  // ==========================================================================
  // 2. CLOUD DATA WAREHOUSES & LAKEHOUSES (4)
  // ==========================================================================
  'Snowflake': {
    providerId: 'Snowflake',
    name: 'Snowflake Data Cloud',
    category: 'WAREHOUSE',
    icon: 'snowflake',
    fields: [
      { id: 'account', label: 'Account Identifier *', type: 'text', placeholder: 'xy12345.us-east-1 or orgname-accountname', required: true, helpText: 'Snowflake account locator', group: 'ENDPOINT' },
      { id: 'auth_type', label: 'Authentication Type *', type: 'select', defaultValue: 'PASSWORD', options: [{ label: 'Username & Password', value: 'PASSWORD' }, { label: 'OAuth / PAT Token', value: 'OAUTH' }, { label: 'External Browser SSO', value: 'SSO' }], required: true, helpText: 'Authentication method', group: 'AUTH' },
      { id: 'username', label: 'Username *', type: 'text', placeholder: 'JDOE', required: true, helpText: 'Snowflake login username', group: 'AUTH' },
      { id: 'secret_ref', label: 'Password / Secret Reference *', type: 'secret_ref', placeholder: 'vault://secret/prod/snowflake_pass', required: true, dependsOn: 'auth_type', conditionValue: 'PASSWORD', helpText: 'Snowflake user password', group: 'AUTH' },
      { id: 'oauth_token', label: 'OAuth Access Token *', type: 'password', placeholder: 'eyJhbGci...', required: true, dependsOn: 'auth_type', conditionValue: 'OAUTH', helpText: 'Bearer or OAuth access token', group: 'AUTH' },
      { id: 'warehouse', label: 'Warehouse', type: 'text', placeholder: 'COMPUTE_WH', helpText: 'Default virtual compute warehouse', group: 'OPTIONS' },
      { id: 'database', label: 'Database Name', type: 'text', placeholder: 'ANALYTICS_DB', helpText: 'Target database name', group: 'OPTIONS' },
      { id: 'schema', label: 'Schema Name', type: 'text', placeholder: 'PUBLIC', helpText: 'Default schema name', group: 'OPTIONS' },
      { id: 'role', label: 'Role', type: 'text', placeholder: 'ACCOUNTADMIN or TRANSFORMER', helpText: 'Active user role', group: 'OPTIONS' }
    ]
  },

  'Google BigQuery': {
    providerId: 'Google BigQuery',
    name: 'Google BigQuery',
    category: 'WAREHOUSE',
    icon: 'search',
    fields: [
      { id: 'project_id', label: 'GCP Project ID *', type: 'text', placeholder: 'my-gcp-analytics-prod', required: true, helpText: 'Google Cloud Project ID', group: 'ENDPOINT' },
      { id: 'dataset', label: 'Default Dataset', type: 'text', placeholder: 'analytics_dataset', helpText: 'BigQuery dataset name', group: 'ENDPOINT' },
      { id: 'auth_type', label: 'Authentication Type *', type: 'select', defaultValue: 'SERVICE_ACCOUNT_KEY', options: [{ label: 'Service Account JSON Key', value: 'SERVICE_ACCOUNT_KEY' }, { label: 'Ambient Workload Identity / ADC', value: 'ADC' }], required: true, helpText: 'Authentication method', group: 'AUTH' },
      { id: 'service_account_json', label: 'Service Account JSON *', type: 'textarea', placeholder: 'Paste JSON key contents or vault:// URI', required: true, dependsOn: 'auth_type', conditionValue: 'SERVICE_ACCOUNT_KEY', helpText: 'GCP Service Account credentials', group: 'AUTH' },
      { id: 'location', label: 'Data Processing Location', type: 'text', defaultValue: 'US', placeholder: 'US, EU, asia-south1', helpText: 'Regional or multi-regional location', group: 'OPTIONS' }
    ]
  },

  'Amazon Redshift': {
    providerId: 'Amazon Redshift',
    name: 'Amazon Redshift',
    category: 'WAREHOUSE',
    defaultPort: 5439,
    icon: 'layers',
    fields: [
      { id: 'host', label: 'Cluster Host Endpoint *', type: 'text', placeholder: 'cluster.xxx.us-east-1.redshift.amazonaws.com', required: true, helpText: 'Redshift cluster endpoint', group: 'ENDPOINT' },
      { id: 'port', label: 'Port', type: 'number', defaultValue: 5439, helpText: 'Redshift port', group: 'ENDPOINT' },
      { id: 'database', label: 'Database Name *', type: 'text', placeholder: 'dev or analytics', required: true, helpText: 'Target database name', group: 'ENDPOINT' },
      { id: 'username', label: 'Username *', type: 'text', placeholder: 'awsuser', required: true, helpText: 'Database user', group: 'AUTH' },
      { id: 'secret_ref', label: 'Password / Vault Secret Reference *', type: 'secret_ref', placeholder: 'vault://secret/prod/redshift_pass', required: true, helpText: 'Database user password', group: 'AUTH' },
      { id: 'region', label: 'AWS Region', type: 'text', defaultValue: 'us-east-1', placeholder: 'us-east-1', helpText: 'AWS deployment region', group: 'OPTIONS' },
      { id: 'cluster_identifier', label: 'Cluster Identifier', type: 'text', placeholder: 'redshift-cluster-1', helpText: 'AWS Cluster ID (for IAM auth)', group: 'OPTIONS' }
    ]
  },

  'Databricks / Delta Lake': {
    providerId: 'Databricks / Delta Lake',
    name: 'Databricks Lakehouse SQL',
    category: 'WAREHOUSE',
    icon: 'layers',
    fields: [
      { id: 'server_hostname', label: 'Server Hostname *', type: 'text', placeholder: 'dbc-12345678-abcd.cloud.databricks.com', required: true, helpText: 'Workspace server hostname', group: 'ENDPOINT' },
      { id: 'http_path', label: 'HTTP Path *', type: 'text', placeholder: '/sql/1.0/warehouses/a1b2c3d4e5f6g7h8', required: true, helpText: 'Path to SQL Warehouse / Endpoint', group: 'ENDPOINT' },
      { id: 'secret_ref', label: 'Personal Access Token (PAT) *', type: 'secret_ref', placeholder: 'dapi1234567890abcdef... or vault://...', required: true, helpText: 'Databricks PAT or OAuth Token', group: 'AUTH' },
      { id: 'catalog', label: 'Unity Catalog', type: 'text', defaultValue: 'main', placeholder: 'main', helpText: 'Unity Catalog name', group: 'OPTIONS' },
      { id: 'schema', label: 'Schema / Database', type: 'text', defaultValue: 'default', placeholder: 'default', helpText: 'Default schema name', group: 'OPTIONS' }
    ]
  },

  // ==========================================================================
  // 3. NOSQL, IN-MEMORY, GRAPH, & SEARCH (8)
  // ==========================================================================
  'MongoDB': {
    providerId: 'MongoDB',
    name: 'MongoDB Document Database',
    category: 'NOSQL_GRAPH_SEARCH',
    defaultPort: 27017,
    icon: 'leaf',
    fields: [
      { id: 'connection_mode', label: 'Connection Mode *', type: 'select', defaultValue: 'STANDALONE', options: [{ label: 'Standalone Host', value: 'STANDALONE' }, { label: 'Replica Set / Cluster URLs', value: 'CLUSTER' }], required: true, helpText: 'Single host vs cluster topology', group: 'ENDPOINT' },
      { id: 'host', label: 'Host / IP Address *', type: 'text', placeholder: 'mongo.company.internal', required: true, dependsOn: 'connection_mode', conditionValue: 'STANDALONE', helpText: 'Primary MongoDB host', group: 'ENDPOINT' },
      { id: 'port', label: 'Port', type: 'number', defaultValue: 27017, dependsOn: 'connection_mode', conditionValue: 'STANDALONE', helpText: 'MongoDB port', group: 'ENDPOINT' },
      { id: 'replica_endpoints', label: 'Replica Set Endpoints *', type: 'textarea', placeholder: 'mongo1:27017, mongo2:27017, mongo3:27017', required: true, dependsOn: 'connection_mode', conditionValue: 'CLUSTER', helpText: 'Comma-separated list of nodes', group: 'ENDPOINT' },
      { id: 'replica_set_name', label: 'Replica Set Name', type: 'text', defaultValue: 'rs0', placeholder: 'rs0', helpText: 'Cluster replica set identifier', group: 'ENDPOINT' },
      { id: 'database', label: 'Database Name', type: 'text', placeholder: 'admin or app_db', helpText: 'Target database', group: 'ENDPOINT' },
      { id: 'username', label: 'Username', type: 'text', placeholder: 'mongo_admin', helpText: 'Database username', group: 'AUTH' },
      { id: 'secret_ref', label: 'Password / Vault Secret Reference', type: 'secret_ref', placeholder: 'vault://secret/prod/mongo_pass', helpText: 'Database password', group: 'AUTH' },
      { id: 'auth_source', label: 'Auth Source Database', type: 'text', defaultValue: 'admin', placeholder: 'admin', helpText: 'Database where user credentials live', group: 'AUTH' }
    ]
  },

  'Apache Cassandra': {
    providerId: 'Apache Cassandra',
    name: 'Apache Cassandra',
    category: 'NOSQL_GRAPH_SEARCH',
    defaultPort: 9042,
    icon: 'grid',
    fields: [
      { id: 'contact_points', label: 'Contact Points *', type: 'text', placeholder: 'cassandra1.internal, cassandra2.internal', required: true, helpText: 'Initial cluster node hostnames', group: 'ENDPOINT' },
      { id: 'port', label: 'Port', type: 'number', defaultValue: 9042, helpText: 'CQL native transport port', group: 'ENDPOINT' },
      { id: 'keyspace', label: 'Keyspace Name', type: 'text', placeholder: 'my_keyspace', helpText: 'Default Cassandra keyspace', group: 'ENDPOINT' },
      { id: 'username', label: 'Username', type: 'text', placeholder: 'cassandra', helpText: 'CQL username', group: 'AUTH' },
      { id: 'secret_ref', label: 'Password / Vault Secret Reference', type: 'secret_ref', placeholder: 'vault://secret/prod/cass_pass', helpText: 'CQL password', group: 'AUTH' },
      { id: 'protocol_version', label: 'Protocol Version', type: 'number', defaultValue: 4, helpText: 'CQL binary protocol version', group: 'OPTIONS' }
    ]
  },

  'ScyllaDB': {
    providerId: 'ScyllaDB',
    name: 'ScyllaDB NoSQL',
    category: 'NOSQL_GRAPH_SEARCH',
    defaultPort: 9042,
    icon: 'zap',
    fields: [
      { id: 'contact_points', label: 'Contact Points *', type: 'text', placeholder: 'scylla1.internal, scylla2.internal', required: true, helpText: 'ScyllaDB cluster node addresses', group: 'ENDPOINT' },
      { id: 'port', label: 'Port', type: 'number', defaultValue: 9042, helpText: 'CQL transport port', group: 'ENDPOINT' },
      { id: 'keyspace', label: 'Keyspace Name', type: 'text', placeholder: 'app_keyspace', helpText: 'Default keyspace', group: 'ENDPOINT' },
      { id: 'username', label: 'Username', type: 'text', placeholder: 'scylla', helpText: 'Username', group: 'AUTH' },
      { id: 'secret_ref', label: 'Password / Secret Reference', type: 'secret_ref', placeholder: 'vault://secret/prod/scylla_pass', helpText: 'Password', group: 'AUTH' }
    ]
  },

  'Neo4j': {
    providerId: 'Neo4j',
    name: 'Neo4j Graph Database',
    category: 'NOSQL_GRAPH_SEARCH',
    defaultPort: 7687,
    icon: 'share-2',
    fields: [
      { id: 'host', label: 'Host / IP Address *', type: 'text', placeholder: 'neo4j.company.internal', required: true, helpText: 'Neo4j server hostname', group: 'ENDPOINT' },
      { id: 'port', label: 'Bolt Port', type: 'number', defaultValue: 7687, helpText: 'Bolt protocol port', group: 'ENDPOINT' },
      { id: 'database', label: 'Database Name', type: 'text', defaultValue: 'neo4j', placeholder: 'neo4j', helpText: 'Target graph database name', group: 'ENDPOINT' },
      { id: 'username', label: 'Username *', type: 'text', placeholder: 'neo4j', required: true, helpText: 'Neo4j login user', group: 'AUTH' },
      { id: 'secret_ref', label: 'Password / Secret Reference *', type: 'secret_ref', placeholder: 'vault://secret/prod/neo4j_pass', required: true, helpText: 'Neo4j password', group: 'AUTH' }
    ]
  },

  'Redis': {
    providerId: 'Redis',
    name: 'Redis In-Memory Data Store',
    category: 'NOSQL_GRAPH_SEARCH',
    defaultPort: 6379,
    icon: 'zap',
    fields: [
      { id: 'host', label: 'Host / IP Address *', type: 'text', placeholder: 'redis.company.internal', required: true, helpText: 'Redis server hostname or IP', group: 'ENDPOINT' },
      { id: 'port', label: 'Port', type: 'number', defaultValue: 6379, helpText: 'Redis TCP port', group: 'ENDPOINT' },
      { id: 'db_index', label: 'Database Index', type: 'number', defaultValue: 0, helpText: 'Database index number (0–15)', group: 'ENDPOINT' },
      { id: 'username', label: 'Username', type: 'text', placeholder: 'default', helpText: 'ACL username (Redis 6+)', group: 'AUTH' },
      { id: 'secret_ref', label: 'Password (AUTH) / Secret Reference', type: 'secret_ref', placeholder: 'vault://secret/prod/redis_pass', helpText: 'Redis password / AUTH token', group: 'AUTH' }
    ]
  },

  'KeyDB': {
    providerId: 'KeyDB',
    name: 'KeyDB Multithreaded Store',
    category: 'NOSQL_GRAPH_SEARCH',
    defaultPort: 6379,
    icon: 'key',
    fields: [
      { id: 'host', label: 'Host / IP Address *', type: 'text', placeholder: 'keydb.company.internal', required: true, helpText: 'KeyDB server hostname', group: 'ENDPOINT' },
      { id: 'port', label: 'Port', type: 'number', defaultValue: 6379, helpText: 'KeyDB port', group: 'ENDPOINT' },
      { id: 'db_index', label: 'Database Index', type: 'number', defaultValue: 0, helpText: 'Database index number', group: 'ENDPOINT' },
      { id: 'username', label: 'Username', type: 'text', placeholder: 'default', helpText: 'ACL user account', group: 'AUTH' },
      { id: 'secret_ref', label: 'Password (AUTH) / Secret Reference', type: 'secret_ref', placeholder: 'vault://secret/prod/keydb_pass', helpText: 'AUTH password', group: 'AUTH' }
    ]
  },

  'Elasticsearch': {
    providerId: 'Elasticsearch',
    name: 'Elasticsearch Search Engine',
    category: 'NOSQL_GRAPH_SEARCH',
    defaultPort: 9200,
    icon: 'search',
    fields: [
      { id: 'node_urls', label: 'Node URLs / Hosts *', type: 'textarea', placeholder: 'https://es-node1.internal:9200, https://es-node2.internal:9200', required: true, helpText: 'Cluster endpoints', group: 'ENDPOINT' },
      { id: 'auth_type', label: 'Authentication Type *', type: 'select', defaultValue: 'BASIC', options: [{ label: 'Basic Auth (Username/Password)', value: 'BASIC' }, { label: 'API Key', value: 'API_KEY' }], required: true, helpText: 'Authentication method', group: 'AUTH' },
      { id: 'username', label: 'Username *', type: 'text', placeholder: 'elastic', required: true, dependsOn: 'auth_type', conditionValue: 'BASIC', helpText: 'Elasticsearch user', group: 'AUTH' },
      { id: 'secret_ref', label: 'Password *', type: 'secret_ref', placeholder: 'vault://secret/prod/es_pass', required: true, dependsOn: 'auth_type', conditionValue: 'BASIC', helpText: 'User password', group: 'AUTH' },
      { id: 'api_key', label: 'API Key *', type: 'secret_ref', placeholder: 'VnVhQ2ZHY0JD...', required: true, dependsOn: 'auth_type', conditionValue: 'API_KEY', helpText: 'Base64-encoded API key', group: 'AUTH' }
    ]
  },

  'OpenSearch': {
    providerId: 'OpenSearch',
    name: 'OpenSearch Search Engine',
    category: 'NOSQL_GRAPH_SEARCH',
    defaultPort: 9200,
    icon: 'search',
    fields: [
      { id: 'node_urls', label: 'Cluster Node URLs *', type: 'textarea', placeholder: 'https://opensearch.internal:9200', required: true, helpText: 'OpenSearch endpoints', group: 'ENDPOINT' },
      { id: 'auth_type', label: 'Authentication Type *', type: 'select', defaultValue: 'BASIC', options: [{ label: 'Basic Auth', value: 'BASIC' }, { label: 'API Key', value: 'API_KEY' }], required: true, helpText: 'Authentication method', group: 'AUTH' },
      { id: 'username', label: 'Username *', type: 'text', placeholder: 'admin', required: true, dependsOn: 'auth_type', conditionValue: 'BASIC', helpText: 'OpenSearch user', group: 'AUTH' },
      { id: 'secret_ref', label: 'Password *', type: 'secret_ref', placeholder: 'vault://secret/prod/os_pass', required: true, dependsOn: 'auth_type', conditionValue: 'BASIC', helpText: 'User password', group: 'AUTH' },
      { id: 'api_key', label: 'API Key *', type: 'secret_ref', placeholder: '••••••••••••', required: true, dependsOn: 'auth_type', conditionValue: 'API_KEY', helpText: 'API key token', group: 'AUTH' }
    ]
  },

  // ==========================================================================
  // 4. EVENT STREAMING & MESSAGING (4)
  // ==========================================================================
  'Apache Kafka': {
    providerId: 'Apache Kafka',
    name: 'Apache Kafka Event Streams',
    category: 'STREAMING',
    defaultPort: 9092,
    icon: 'radio',
    fields: [
      { id: 'bootstrap_brokers', label: 'Bootstrap Brokers *', type: 'textarea', placeholder: 'kafka1:9092, kafka2:9092, kafka3:9092', required: true, helpText: 'Comma-separated list of brokers', group: 'ENDPOINT' },
      { id: 'security_protocol', label: 'Security Protocol *', type: 'select', defaultValue: 'PLAINTEXT', options: [{ label: 'PLAINTEXT', value: 'PLAINTEXT' }, { label: 'SSL', value: 'SSL' }, { label: 'SASL_PLAINTEXT', value: 'SASL_PLAINTEXT' }, { label: 'SASL_SSL', value: 'SASL_SSL' }], required: true, helpText: 'Security protocol', group: 'SECURITY' },
      { id: 'sasl_mechanism', label: 'SASL Mechanism *', type: 'select', defaultValue: 'PLAIN', options: [{ label: 'PLAIN', value: 'PLAIN' }, { label: 'SCRAM-SHA-256', value: 'SCRAM-SHA-256' }, { label: 'SCRAM-SHA-512', value: 'SCRAM-SHA-512' }], required: true, dependsOn: 'security_protocol', conditionValue: 'SASL_SSL', helpText: 'SASL mechanism', group: 'AUTH' },
      { id: 'sasl_username', label: 'SASL Username / API Key *', type: 'text', placeholder: 'my_kafka_user', required: true, dependsOn: 'security_protocol', conditionValue: 'SASL_SSL', helpText: 'SASL login or Confluent API key', group: 'AUTH' },
      { id: 'secret_ref', label: 'SASL Password / API Secret *', type: 'secret_ref', placeholder: 'vault://secret/prod/kafka_pass', required: true, dependsOn: 'security_protocol', conditionValue: 'SASL_SSL', helpText: 'SASL password or API secret', group: 'AUTH' },
      { id: 'consumer_group', label: 'Consumer Group ID', type: 'text', defaultValue: 'akaal-consumer-group', placeholder: 'akaal-consumer-group', helpText: 'Kafka consumer group name', group: 'OPTIONS' },
      { id: 'client_id', label: 'Client ID', type: 'text', defaultValue: 'akaal-client', placeholder: 'akaal-client', helpText: 'Client identifier', group: 'OPTIONS' }
    ]
  },

  'Amazon Kinesis': {
    providerId: 'Amazon Kinesis',
    name: 'Amazon Kinesis Data Streams',
    category: 'STREAMING',
    icon: 'activity',
    fields: [
      { id: 'stream_name', label: 'Stream Name *', type: 'text', placeholder: 'telemetry-data-stream', required: true, helpText: 'Target Kinesis Data Stream name', group: 'ENDPOINT' },
      { id: 'region', label: 'AWS Region *', type: 'text', defaultValue: 'us-east-1', placeholder: 'us-east-1', required: true, helpText: 'AWS Region where stream lives', group: 'ENDPOINT' },
      { id: 'auth_type', label: 'Authentication Type *', type: 'select', defaultValue: 'ACCESS_KEYS', options: [{ label: 'Explicit Access Keys', value: 'ACCESS_KEYS' }, { label: 'Ambient IAM Role / EC2 / EKS', value: 'IAM_ROLE' }], required: true, helpText: 'Authentication method', group: 'AUTH' },
      { id: 'aws_access_key_id', label: 'AWS Access Key ID *', type: 'text', placeholder: 'AKIAIOSFODNN7EXAMPLE', required: true, dependsOn: 'auth_type', conditionValue: 'ACCESS_KEYS', helpText: '20-character AWS Access Key', group: 'AUTH' },
      { id: 'secret_ref', label: 'AWS Secret Access Key *', type: 'secret_ref', placeholder: 'vault://secret/prod/aws_secret', required: true, dependsOn: 'auth_type', conditionValue: 'ACCESS_KEYS', helpText: 'AWS Secret Access Key', group: 'AUTH' },
      { id: 'session_token', label: 'Session Token (STS)', type: 'password', placeholder: 'IQoJb3JpZ2luX2VjE...', helpText: 'Required if using temporary STS keys', group: 'AUTH' },
      { id: 'custom_endpoint', label: 'Custom Endpoint URL', type: 'text', placeholder: 'http://localhost:4566', helpText: 'For LocalStack or VPC Endpoints', group: 'OPTIONS' }
    ]
  },

  'Azure Event Hubs': {
    providerId: 'Azure Event Hubs',
    name: 'Azure Event Hubs',
    category: 'STREAMING',
    icon: 'radio',
    fields: [
      { id: 'namespace', label: 'Event Hubs Namespace *', type: 'text', placeholder: 'my-namespace.servicebus.windows.net', required: true, helpText: 'Azure Event Hubs namespace URL', group: 'ENDPOINT' },
      { id: 'secret_ref', label: 'Connection String *', type: 'secret_ref', placeholder: 'Endpoint=sb://my-ns.servicebus.windows.net/;SharedAccessKeyName=...', required: true, helpText: 'Namespace or entity Connection String', group: 'AUTH' },
      { id: 'event_hub_name', label: 'Event Hub Name', type: 'text', placeholder: 'orders-stream', helpText: 'Target Event Hub instance name', group: 'ENDPOINT' }
    ]
  },

  'Google Cloud Pub/Sub': {
    providerId: 'Google Cloud Pub/Sub',
    name: 'Google Cloud Pub/Sub',
    category: 'STREAMING',
    icon: 'send',
    fields: [
      { id: 'project_id', label: 'GCP Project ID *', type: 'text', placeholder: 'my-gcp-project', required: true, helpText: 'Google Cloud Project ID', group: 'ENDPOINT' },
      { id: 'topic_id', label: 'Topic ID', type: 'text', placeholder: 'transactions-topic', helpText: 'Target topic identifier', group: 'ENDPOINT' },
      { id: 'subscription_id', label: 'Subscription ID', type: 'text', placeholder: 'transactions-sub', helpText: 'Source subscription identifier', group: 'ENDPOINT' },
      { id: 'auth_type', label: 'Authentication Type *', type: 'select', defaultValue: 'SERVICE_ACCOUNT_JSON', options: [{ label: 'Service Account JSON', value: 'SERVICE_ACCOUNT_JSON' }, { label: 'Ambient Workload Identity / ADC', value: 'ADC' }], required: true, helpText: 'Authentication method', group: 'AUTH' },
      { id: 'service_account_json', label: 'Service Account JSON *', type: 'textarea', placeholder: 'Paste .json key contents or vault:// URI', required: true, dependsOn: 'auth_type', conditionValue: 'SERVICE_ACCOUNT_JSON', helpText: 'GCP Service Account credentials', group: 'AUTH' }
    ]
  },

  // ==========================================================================
  // 5. CLOUD OBJECT & DISTRIBUTED FILE STORAGE (5)
  // ==========================================================================
  'Amazon S3': {
    providerId: 'Amazon S3',
    name: 'Amazon S3 Storage',
    category: 'STORAGE',
    icon: 'archive',
    fields: [
      { id: 'bucket_name', label: 'Bucket Name *', type: 'text', placeholder: 'my-data-lake-bucket', required: true, helpText: 'S3 bucket name', group: 'ENDPOINT' },
      { id: 'region', label: 'AWS Region *', type: 'text', defaultValue: 'us-east-1', placeholder: 'us-east-1', required: true, helpText: 'AWS S3 region', group: 'ENDPOINT' },
      { id: 'auth_type', label: 'Authentication Type *', type: 'select', defaultValue: 'ACCESS_KEYS', options: [{ label: 'Explicit Access Keys', value: 'ACCESS_KEYS' }, { label: 'Ambient IAM Role / IRSA', value: 'IAM_ROLE' }], required: true, helpText: 'Authentication method', group: 'AUTH' },
      { id: 'aws_access_key_id', label: 'AWS Access Key ID *', type: 'text', placeholder: 'AKIAIOSFODNN7EXAMPLE', required: true, dependsOn: 'auth_type', conditionValue: 'ACCESS_KEYS', helpText: 'AWS Access Key ID', group: 'AUTH' },
      { id: 'secret_ref', label: 'AWS Secret Access Key *', type: 'secret_ref', placeholder: 'vault://secret/prod/s3_key', required: true, dependsOn: 'auth_type', conditionValue: 'ACCESS_KEYS', helpText: 'AWS Secret Access Key', group: 'AUTH' },
      { id: 'session_token', label: 'Session Token (STS)', type: 'password', placeholder: '••••••••••••', helpText: 'Temporary session token', group: 'AUTH' },
      { id: 'custom_endpoint', label: 'Custom Endpoint URL', type: 'text', placeholder: 'https://s3.custom-provider.com', helpText: 'For MinIO, Ceph, or VPC Endpoints', group: 'OPTIONS' }
    ]
  },

  'Google Cloud Storage': {
    providerId: 'Google Cloud Storage',
    name: 'Google Cloud Storage (GCS)',
    category: 'STORAGE',
    icon: 'cloud',
    fields: [
      { id: 'bucket_name', label: 'Bucket Name *', type: 'text', placeholder: 'my-gcs-storage-bucket', required: true, helpText: 'Target GCS bucket name', group: 'ENDPOINT' },
      { id: 'project_id', label: 'GCP Project ID', type: 'text', placeholder: 'my-gcp-project', helpText: 'Google Cloud Project ID', group: 'ENDPOINT' },
      { id: 'auth_type', label: 'Authentication Type *', type: 'select', defaultValue: 'SERVICE_ACCOUNT_JSON', options: [{ label: 'Service Account JSON', value: 'SERVICE_ACCOUNT_JSON' }, { label: 'Ambient Workload Identity / ADC', value: 'ADC' }], required: true, helpText: 'Authentication method', group: 'AUTH' },
      { id: 'service_account_json', label: 'Service Account JSON *', type: 'textarea', placeholder: 'Paste .json file contents or vault:// URI', required: true, dependsOn: 'auth_type', conditionValue: 'SERVICE_ACCOUNT_JSON', helpText: 'GCP Service Account credentials', group: 'AUTH' }
    ]
  },

  'Azure Blob Storage': {
    providerId: 'Azure Blob Storage',
    name: 'Azure Blob Storage',
    category: 'STORAGE',
    icon: 'box',
    fields: [
      { id: 'container_name', label: 'Container Name *', type: 'text', placeholder: 'raw-data-container', required: true, helpText: 'Azure Blob container name', group: 'ENDPOINT' },
      { id: 'auth_type', label: 'Authentication Type *', type: 'select', defaultValue: 'CONN_STRING', options: [{ label: 'Connection String', value: 'CONN_STRING' }, { label: 'Account Key', value: 'ACCOUNT_KEY' }, { label: 'SAS Token', value: 'SAS_TOKEN' }], required: true, helpText: 'Authentication method', group: 'AUTH' },
      { id: 'secret_ref', label: 'Connection String *', type: 'secret_ref', placeholder: 'DefaultEndpointsProtocol=https;AccountName=...', required: true, dependsOn: 'auth_type', conditionValue: 'CONN_STRING', helpText: 'Azure Storage Connection String', group: 'AUTH' },
      { id: 'storage_account_name', label: 'Storage Account Name *', type: 'text', placeholder: 'mystorageaccount', required: true, dependsOn: 'auth_type', conditionValue: 'ACCOUNT_KEY', helpText: 'Azure Storage Account name', group: 'AUTH' },
      { id: 'account_key', label: 'Account Access Key *', type: 'secret_ref', placeholder: 'vault://secret/prod/azure_key', required: true, dependsOn: 'auth_type', conditionValue: 'ACCOUNT_KEY', helpText: 'Storage primary or secondary key', group: 'AUTH' },
      { id: 'sas_token', label: 'SAS Token *', type: 'password', placeholder: '?sv=2020-08-04&ss=b&srt=sco...', required: true, dependsOn: 'auth_type', conditionValue: 'SAS_TOKEN', helpText: 'Shared Access Signature URL token', group: 'AUTH' },
      { id: 'custom_endpoint', label: 'Custom Endpoint URL', type: 'text', placeholder: 'http://127.0.0.1:10000/devstoreaccount1', helpText: 'For Azurite or Private Endpoints', group: 'OPTIONS' }
    ]
  },

  'MinIO': {
    providerId: 'MinIO',
    name: 'MinIO Object Storage',
    category: 'STORAGE',
    defaultPort: 9000,
    icon: 'server',
    fields: [
      { id: 'host', label: 'Server Host / IP *', type: 'text', placeholder: 'localhost or minio.company.internal', required: true, helpText: 'MinIO server address', group: 'ENDPOINT' },
      { id: 'port', label: 'Port', type: 'number', defaultValue: 9000, helpText: 'S3 API port', group: 'ENDPOINT' },
      { id: 'bucket_name', label: 'Bucket Name', type: 'text', placeholder: 'landing-bucket', helpText: 'Target bucket name', group: 'ENDPOINT' },
      { id: 'access_key', label: 'Access Key ID *', type: 'text', defaultValue: 'minioadmin', placeholder: 'minioadmin', required: true, helpText: 'MinIO access key / username', group: 'AUTH' },
      { id: 'secret_ref', label: 'Secret Access Key *', type: 'secret_ref', placeholder: 'vault://secret/prod/minio_pass', required: true, helpText: 'MinIO secret key / password', group: 'AUTH' }
    ]
  },

  'Apache HDFS': {
    providerId: 'Apache HDFS',
    name: 'Apache Hadoop HDFS',
    category: 'STORAGE',
    defaultPort: 9870,
    icon: 'folder-tree',
    fields: [
      { id: 'namenode_host', label: 'NameNode Host / IP *', type: 'text', placeholder: 'namenode.company.internal', required: true, helpText: 'Hadoop NameNode hostname', group: 'ENDPOINT' },
      { id: 'port', label: 'Port', type: 'number', defaultValue: 9870, helpText: 'WebHDFS HTTP port (9870) or RPC (8020)', group: 'ENDPOINT' },
      { id: 'hdfs_user', label: 'HDFS Username', type: 'text', placeholder: 'hdfs', helpText: 'Hadoop user account', group: 'AUTH' },
      { id: 'root_path', label: 'Root Path', type: 'text', defaultValue: '/', placeholder: '/ or /data/warehouse', helpText: 'Root directory path on HDFS', group: 'ENDPOINT' },
      { id: 'access_mode', label: 'Access Mode', type: 'select', defaultValue: 'WEBHDFS', options: [{ label: 'WebHDFS (HTTP/REST)', value: 'WEBHDFS' }, { label: 'Native RPC', value: 'RPC' }], helpText: 'Protocol mode', group: 'OPTIONS' }
    ]
  }
};
