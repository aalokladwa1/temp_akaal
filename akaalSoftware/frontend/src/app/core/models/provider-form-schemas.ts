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
  desc?: string;
}

export interface IngestionEngineOption {
  label: string;
  value: string;
  desc?: string;
  recommended?: boolean;
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
  ingestionEngines?: IngestionEngineOption[];
}

export const ALL_48_PROVIDER_SCHEMAS: Record<PhysicalProviderId, ProviderFormSchema> = {
  'SQLite': {
    "providerId": "SQLite",
    "name": "SQLite",
    "category": "RELATIONAL",
    "icon": "database",
    "fields": [
        {
            "id": "database_path",
            "label": "Database Path",
            "type": "file_path",
            "required": true,
            "placeholder": "/var/data/app.db or :memory:",
            "group": "ENDPOINT"
        },
        {
            "id": "lock_timeout",
            "label": "Lock Timeout (seconds)",
            "type": "number",
            "defaultValue": 10.0,
            "placeholder": "10.0",
            "group": "OPTIONS"
        }
    ],
    "ingestionEngines": [
        {
            "label": "PRAGMA synchronous=OFF/WAL & Multi-Row Batches",
            "value": "SQLITE_WAL_BATCH",
            "desc": "Write-Ahead Log multi-statement transactions",
            "recommended": true
        },
        {
            "label": "Standard Atomic Insert",
            "value": "STANDARD_INSERT",
            "desc": "Single row atomic transactional write"
        }
    ]
} as any,
  'PostgreSQL': {
    "providerId": "PostgreSQL",
    "name": "PostgreSQL",
    "category": "RELATIONAL",
    "defaultPort": 5432,
    "icon": "database",
    "fields": [
        {
            "id": "host",
            "label": "Host",
            "type": "text",
            "required": true,
            "placeholder": "postgres.company.internal",
            "group": "ENDPOINT"
        },
        {
            "id": "port",
            "label": "Port",
            "type": "number",
            "defaultValue": 5432,
            "placeholder": "5432",
            "group": "ENDPOINT"
        },
        {
            "id": "database",
            "label": "Database",
            "type": "text",
            "required": true,
            "placeholder": "banking_ledger",
            "group": "ENDPOINT"
        },
        {
            "id": "schema",
            "label": "Schema",
            "type": "text",
            "defaultValue": "public",
            "placeholder": "public",
            "group": "ENDPOINT"
        },
        {
            "id": "username",
            "label": "Username",
            "type": "text",
            "required": true,
            "placeholder": "postgres_admin",
            "group": "AUTH"
        },
        {
            "id": "secret_ref",
            "label": "Secret Ref / Password",
            "type": "secret_ref",
            "required": true,
            "placeholder": "vault://secret/prod/pg_pass",
            "group": "AUTH"
        },
        {
            "id": "ssl_mode",
            "label": "SSL Mode",
            "type": "select",
            "defaultValue": "prefer",
            "options": [
                {
                    "label": "prefer (Default Non-Prod)",
                    "value": "prefer"
                },
                {
                    "label": "require",
                    "value": "require"
                },
                {
                    "label": "verify-ca",
                    "value": "verify-ca"
                },
                {
                    "label": "verify-full (Production Enforced)",
                    "value": "verify-full"
                }
            ],
            "group": "SECURITY"
        },
        {
            "id": "slot_name",
            "label": "Replication Slot Name",
            "type": "text",
            "placeholder": "akaal_cdc_slot (for M2/M3)",
            "group": "OPTIONS"
        },
        {
            "id": "publication_name",
            "label": "Publication Name",
            "type": "text",
            "placeholder": "akaal_pub (for M2/M3)",
            "group": "OPTIONS"
        }
    ],
    "ingestionEngines": [
        {
            "label": "Binary COPY FROM STDIN Protocol",
            "value": "POSTGRES_BINARY_COPY",
            "desc": "High-speed streaming bypassing SQL parser (Direct binary)",
            "recommended": true
        },
        {
            "label": "Multi-Row Prepared Insert Batches",
            "value": "MULTI_ROW_INSERT",
            "desc": "Standard parameterized bulk insert statements"
        }
    ]
} as any,
  'MySQL': {
    "providerId": "MySQL",
    "name": "MySQL",
    "category": "RELATIONAL",
    "defaultPort": 3306,
    "icon": "database",
    "fields": [
        {
            "id": "host",
            "label": "Host",
            "type": "text",
            "required": true,
            "placeholder": "mysql.company.internal",
            "group": "ENDPOINT"
        },
        {
            "id": "port",
            "label": "Port",
            "type": "number",
            "defaultValue": 3306,
            "placeholder": "3306",
            "group": "ENDPOINT"
        },
        {
            "id": "database",
            "label": "Database",
            "type": "text",
            "required": true,
            "placeholder": "ecommerce_db",
            "group": "ENDPOINT"
        },
        {
            "id": "username",
            "label": "Username",
            "type": "text",
            "required": true,
            "placeholder": "mysql_user",
            "group": "AUTH"
        },
        {
            "id": "secret_ref",
            "label": "Secret Ref / Password",
            "type": "secret_ref",
            "required": true,
            "placeholder": "vault://secret/prod/mysql_pass",
            "group": "AUTH"
        },
        {
            "id": "charset",
            "label": "Charset",
            "type": "text",
            "defaultValue": "utf8mb4",
            "placeholder": "utf8mb4",
            "group": "OPTIONS"
        },
        {
            "id": "server_id",
            "label": "Server ID",
            "type": "number",
            "placeholder": "1001 (CDC register ID)",
            "group": "OPTIONS"
        }
    ],
    "ingestionEngines": [
        {
            "label": "LOAD DATA LOCAL INFILE Buffer Streaming",
            "value": "LOAD_DATA_LOCAL_INFILE",
            "desc": "Direct file buffer streaming into InnoDB engine",
            "recommended": true
        },
        {
            "label": "Multi-Row Bulk Inserts",
            "value": "MULTI_ROW_INSERT",
            "desc": "Extended INSERT INTO ... VALUES (...) batches"
        }
    ]
} as any,
  'MariaDB': {
    "providerId": "MariaDB",
    "name": "MariaDB",
    "category": "RELATIONAL",
    "defaultPort": 3306,
    "icon": "database",
    "fields": [
        {
            "id": "host",
            "label": "Host",
            "type": "text",
            "required": true,
            "placeholder": "mariadb.company.internal",
            "group": "ENDPOINT"
        },
        {
            "id": "port",
            "label": "Port",
            "type": "number",
            "defaultValue": 3306,
            "placeholder": "3306",
            "group": "ENDPOINT"
        },
        {
            "id": "database",
            "label": "Database",
            "type": "text",
            "required": true,
            "placeholder": "mariadb_db",
            "group": "ENDPOINT"
        },
        {
            "id": "username",
            "label": "Username",
            "type": "text",
            "required": true,
            "placeholder": "maria_user",
            "group": "AUTH"
        },
        {
            "id": "secret_ref",
            "label": "Secret Ref / Password",
            "type": "secret_ref",
            "required": true,
            "placeholder": "vault://secret/prod/maria_pass",
            "group": "AUTH"
        },
        {
            "id": "charset",
            "label": "Charset",
            "type": "text",
            "defaultValue": "utf8mb4",
            "placeholder": "utf8mb4",
            "group": "OPTIONS"
        }
    ],
    "ingestionEngines": [
        {
            "label": "LOAD DATA LOCAL INFILE Buffer Streaming",
            "value": "LOAD_DATA_LOCAL_INFILE",
            "desc": "Streaming binary table loader",
            "recommended": true
        },
        {
            "label": "Bulk Parameter Array Execution",
            "value": "BULK_ARRAY_EXEC",
            "desc": "CLI prepared array parameter injection"
        }
    ]
} as any,
  'Oracle Database': {
    "providerId": "Oracle Database",
    "name": "Oracle Database",
    "category": "RELATIONAL",
    "defaultPort": 1521,
    "icon": "database",
    "fields": [
        {
            "id": "connection_type",
            "label": "Connection Type",
            "type": "select",
            "required": true,
            "defaultValue": "SERVICE_NAME",
            "options": [
                {
                    "label": "Service Name (PDB / RAC)",
                    "value": "SERVICE_NAME",
                    "desc": "Connect via logical database service name"
                },
                {
                    "label": "SID (Oracle System ID)",
                    "value": "SID",
                    "desc": "Connect via physical instance SID"
                },
                {
                    "label": "TNS Descriptor (tnsnames.ora)",
                    "value": "TNS_DESCRIPTOR",
                    "desc": "Raw TNS alias descriptor string"
                },
                {
                    "label": "Oracle Wallet (cwallet.sso / mTLS)",
                    "value": "WALLET",
                    "desc": "Encrypted client credentials directory"
                }
            ],
            "group": "ENDPOINT"
        },
        {
            "id": "host",
            "label": "Host / SCAN IP",
            "type": "text",
            "placeholder": "ora-rac.prod.internal",
            "group": "ENDPOINT"
        },
        {
            "id": "port",
            "label": "Port",
            "type": "number",
            "defaultValue": 1521,
            "placeholder": "1521",
            "group": "ENDPOINT"
        },
        {
            "id": "service_name",
            "label": "Service Name (PDB)",
            "type": "text",
            "placeholder": "ORCLPDB1",
            "group": "ENDPOINT"
        },
        {
            "id": "sid",
            "label": "SID",
            "type": "text",
            "placeholder": "ORCL",
            "group": "ENDPOINT"
        },
        {
            "id": "tns_descriptor",
            "label": "TNS Descriptor",
            "type": "textarea",
            "placeholder": "(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=...)(PORT=1521))(CONNECT_DATA=(SERVICE_NAME=...)))",
            "group": "ENDPOINT"
        },
        {
            "id": "wallet_path",
            "label": "Wallet Path",
            "type": "file_path",
            "placeholder": "/opt/oracle/wallets/client_wallet.zip",
            "group": "ENDPOINT"
        },
        {
            "id": "wallet_password",
            "label": "Wallet Password",
            "type": "password",
            "placeholder": "Wallet decryption password",
            "group": "AUTH"
        },
        {
            "id": "tns_alias",
            "label": "TNS Alias",
            "type": "text",
            "placeholder": "db_high_wallet",
            "group": "ENDPOINT"
        },
        {
            "id": "username",
            "label": "Username",
            "type": "text",
            "required": true,
            "placeholder": "SYSTEM or HR",
            "group": "AUTH"
        },
        {
            "id": "secret_ref",
            "label": "Secret Ref / Password",
            "type": "secret_ref",
            "required": true,
            "placeholder": "vault://secret/prod/oracle",
            "group": "AUTH"
        },
        {
            "id": "privilege_mode",
            "label": "Privilege Mode",
            "type": "select",
            "defaultValue": "NORMAL",
            "options": [
                {
                    "label": "NORMAL (Standard schema session)",
                    "value": "NORMAL"
                },
                {
                    "label": "SYSDBA (Required for LogMiner CDC)",
                    "value": "SYSDBA"
                },
                {
                    "label": "SYSOPER (Operator administrative access)",
                    "value": "SYSOPER"
                }
            ],
            "group": "OPTIONS"
        },
        {
            "id": "driver_mode",
            "label": "Driver Mode",
            "type": "select",
            "defaultValue": "THIN",
            "options": [
                {
                    "label": "THIN (Zero-Client Pure Go/Java)",
                    "value": "THIN",
                    "desc": "Default zero-dependency client"
                },
                {
                    "label": "THICK (OCI Native Client)",
                    "value": "THICK",
                    "desc": "Native C OCI libraries for Direct-Path & TNS"
                }
            ],
            "group": "OPTIONS"
        }
    ],
    "ingestionEngines": [
        {
            "label": "OCI Direct-Path Load API",
            "value": "OCI_DIRECT_PATH",
            "desc": "Direct blocks write bypassing buffer cache and undo logs",
            "recommended": true
        },
        {
            "label": "FORALL Bulk Array Insert",
            "value": "BULK_ARRAY_INSERT",
            "desc": "PL/SQL array bind bulk inserts"
        }
    ]
} as any,
  'Microsoft SQL Server (MSSQL)': {
    "providerId": "Microsoft SQL Server (MSSQL)",
    "name": "Microsoft SQL Server (MSSQL)",
    "category": "RELATIONAL",
    "defaultPort": 1433,
    "icon": "database",
    "fields": [
        {
            "id": "host",
            "label": "Host / Named Instance",
            "type": "text",
            "required": true,
            "placeholder": "sql-server.corp.internal or db\\\\SQLEXPRESS",
            "group": "ENDPOINT"
        },
        {
            "id": "port",
            "label": "Port",
            "type": "number",
            "defaultValue": 1433,
            "placeholder": "1433",
            "group": "ENDPOINT"
        },
        {
            "id": "database",
            "label": "Database",
            "type": "text",
            "required": true,
            "placeholder": "master or erp_db",
            "group": "ENDPOINT"
        },
        {
            "id": "auth_type",
            "label": "Authentication Mode",
            "type": "select",
            "required": true,
            "defaultValue": "SQL_AUTH",
            "options": [
                {
                    "label": "SQL Server Authentication",
                    "value": "SQL_AUTH",
                    "desc": "Standard database username and password"
                },
                {
                    "label": "Windows Authentication (SSPI / AD)",
                    "value": "WINDOWS_SSPI",
                    "desc": "Integrated Kerberos/Active Directory token"
                }
            ],
            "group": "AUTH"
        },
        {
            "id": "username",
            "label": "Username",
            "type": "text",
            "placeholder": "sa or db_owner",
            "group": "AUTH"
        },
        {
            "id": "secret_ref",
            "label": "Secret Ref / Password",
            "type": "secret_ref",
            "placeholder": "vault://secret/prod/mssql",
            "group": "AUTH"
        },
        {
            "id": "encrypt",
            "label": "Encrypt Connection (TLS)",
            "type": "boolean",
            "defaultValue": true,
            "group": "SECURITY"
        },
        {
            "id": "trust_server_cert",
            "label": "Trust Server Certificate",
            "type": "boolean",
            "defaultValue": false,
            "group": "SECURITY"
        }
    ],
    "ingestionEngines": [
        {
            "label": "SqlBulkCopy with TABLOCK Streaming",
            "value": "SQL_BULK_COPY_TABLOCK",
            "desc": "Direct TDS bulk streaming with minimal transaction logging",
            "recommended": true
        },
        {
            "label": "Prepared Parameterized Batch Insert",
            "value": "PREPARED_BATCH",
            "desc": "Standard multi-row batches with RPC protocol"
        }
    ]
} as any,
  'IBM Db2 LUW': {
    "providerId": "IBM Db2 LUW",
    "name": "IBM Db2 LUW",
    "category": "RELATIONAL",
    "defaultPort": 50000,
    "icon": "database",
    "fields": [
        {
            "id": "host",
            "label": "Host",
            "type": "text",
            "required": true,
            "placeholder": "db2.corp.internal",
            "group": "ENDPOINT"
        },
        {
            "id": "port",
            "label": "Port",
            "type": "number",
            "defaultValue": 50000,
            "placeholder": "50000",
            "group": "ENDPOINT"
        },
        {
            "id": "database",
            "label": "Database",
            "type": "text",
            "required": true,
            "placeholder": "SAMPLE",
            "group": "ENDPOINT"
        },
        {
            "id": "schema",
            "label": "Schema",
            "type": "text",
            "defaultValue": "DB2INST1",
            "placeholder": "DB2INST1",
            "group": "ENDPOINT"
        },
        {
            "id": "username",
            "label": "Username",
            "type": "text",
            "required": true,
            "placeholder": "db2admin",
            "group": "AUTH"
        },
        {
            "id": "secret_ref",
            "label": "Secret Ref / Password",
            "type": "secret_ref",
            "required": true,
            "placeholder": "vault://secret/prod/db2",
            "group": "AUTH"
        }
    ],
    "ingestionEngines": [
        {
            "label": "db2Load Utility API",
            "value": "DB2_LOAD_API",
            "desc": "High-throughput kernel block loader bypassing transaction log",
            "recommended": true
        },
        {
            "label": "CLI Bulk Array Insertion",
            "value": "CLI_ARRAY_INSERT",
            "desc": "Array binding with parameterized insert buffer"
        }
    ]
} as any,
  'Snowflake Data Cloud': {
    "providerId": "Snowflake Data Cloud",
    "name": "Snowflake Data Cloud",
    "category": "WAREHOUSE",
    "defaultPort": 443,
    "icon": "layers",
    "fields": [
        {
            "id": "account",
            "label": "Account Identifier",
            "type": "text",
            "required": true,
            "placeholder": "xy12345.us-east-1 or org-account",
            "group": "ENDPOINT"
        },
        {
            "id": "auth_type",
            "label": "Authentication Type",
            "type": "select",
            "required": true,
            "defaultValue": "PASSWORD",
            "options": [
                {
                    "label": "Password Authentication",
                    "value": "PASSWORD"
                },
                {
                    "label": "Key Pair (RSA 2048/4096)",
                    "value": "KEY_PAIR"
                },
                {
                    "label": "OAuth 2.0 Token",
                    "value": "OAUTH"
                },
                {
                    "label": "External Browser SSO",
                    "value": "SSO"
                }
            ],
            "group": "AUTH"
        },
        {
            "id": "username",
            "label": "Username",
            "type": "text",
            "placeholder": "akaal_loader",
            "group": "AUTH"
        },
        {
            "id": "secret_ref",
            "label": "Secret Ref / Password",
            "type": "secret_ref",
            "placeholder": "vault://secret/prod/snowflake",
            "group": "AUTH"
        },
        {
            "id": "private_key_path",
            "label": "Private Key Path",
            "type": "file_path",
            "placeholder": "/etc/ssl/rsa_key.p8",
            "group": "AUTH"
        },
        {
            "id": "passphrase",
            "label": "Key Passphrase",
            "type": "password",
            "placeholder": "Passphrase for private key",
            "group": "AUTH"
        },
        {
            "id": "oauth_token",
            "label": "OAuth Token",
            "type": "secret_ref",
            "placeholder": "vault://secret/snowflake_token",
            "group": "AUTH"
        },
        {
            "id": "warehouse",
            "label": "Virtual Warehouse",
            "type": "text",
            "defaultValue": "COMPUTE_WH",
            "placeholder": "COMPUTE_WH",
            "group": "ENDPOINT"
        },
        {
            "id": "database",
            "label": "Database",
            "type": "text",
            "placeholder": "ANALYTICS_PROD",
            "group": "ENDPOINT"
        },
        {
            "id": "schema",
            "label": "Schema",
            "type": "text",
            "defaultValue": "PUBLIC",
            "placeholder": "PUBLIC",
            "group": "ENDPOINT"
        },
        {
            "id": "role",
            "label": "Role",
            "type": "text",
            "defaultValue": "ACCOUNTADMIN",
            "placeholder": "ACCOUNTADMIN",
            "group": "OPTIONS"
        }
    ],
    "ingestionEngines": [
        {
            "label": "Snowpipe Streaming SDK",
            "value": "SNOWPIPE_STREAMING",
            "desc": "Real-time sub-second low-latency streaming load API",
            "recommended": true
        },
        {
            "label": "Parquet STAGE COPY INTO",
            "value": "STAGE_COPY_INTO",
            "desc": "Micro-partition batch load from cloud stage"
        }
    ]
} as any,
  'Google BigQuery': {
    "providerId": "Google BigQuery",
    "name": "Google BigQuery",
    "category": "WAREHOUSE",
    "defaultPort": 443,
    "icon": "layers",
    "fields": [
        {
            "id": "project_id",
            "label": "GCP Project ID",
            "type": "text",
            "required": true,
            "placeholder": "my-gcp-analytics-prod",
            "group": "ENDPOINT"
        },
        {
            "id": "dataset",
            "label": "BigQuery Dataset",
            "type": "text",
            "placeholder": "analytics_dw",
            "group": "ENDPOINT"
        },
        {
            "id": "auth_type",
            "label": "Authentication Method",
            "type": "select",
            "required": true,
            "defaultValue": "SERVICE_ACCOUNT_KEY",
            "options": [
                {
                    "label": "Service Account Key (JSON)",
                    "value": "SERVICE_ACCOUNT_KEY",
                    "desc": "Explicit service account key JSON payload"
                },
                {
                    "label": "Application Default Credentials (ADC)",
                    "value": "ADC",
                    "desc": "Ambient GCP Workload Identity / Metadata"
                }
            ],
            "group": "AUTH"
        },
        {
            "id": "service_account_json",
            "label": "Service Account JSON Key",
            "type": "textarea",
            "placeholder": "{'type': 'service_account', ...} or vault://secret/...",
            "group": "AUTH"
        },
        {
            "id": "location",
            "label": "Dataset Location",
            "type": "text",
            "defaultValue": "US",
            "placeholder": "US, EU, or asia-south1",
            "group": "OPTIONS"
        }
    ],
    "ingestionEngines": [
        {
            "label": "gRPC BigQuery Storage Write API",
            "value": "STORAGE_WRITE_API",
            "desc": "Streaming Proto3 serialization with exactly-once delivery",
            "recommended": true
        },
        {
            "label": "Batch Load Jobs API",
            "value": "BATCH_LOAD_JOBS",
            "desc": "Asynchronous bulk load jobs"
        }
    ]
} as any,
  'Amazon Redshift': {
    "providerId": "Amazon Redshift",
    "name": "Amazon Redshift",
    "category": "WAREHOUSE",
    "defaultPort": 5439,
    "icon": "layers",
    "fields": [
        {
            "id": "host",
            "label": "Cluster Host Endpoint",
            "type": "text",
            "required": true,
            "placeholder": "cluster.xxx.redshift.amazonaws.com",
            "group": "ENDPOINT"
        },
        {
            "id": "port",
            "label": "Port",
            "type": "number",
            "defaultValue": 5439,
            "placeholder": "5439",
            "group": "ENDPOINT"
        },
        {
            "id": "database",
            "label": "Database",
            "type": "text",
            "required": true,
            "placeholder": "dev or warehouse",
            "group": "ENDPOINT"
        },
        {
            "id": "username",
            "label": "Username",
            "type": "text",
            "required": true,
            "placeholder": "awsuser",
            "group": "AUTH"
        },
        {
            "id": "secret_ref",
            "label": "Secret Ref / Password",
            "type": "secret_ref",
            "required": true,
            "placeholder": "vault://secret/prod/redshift",
            "group": "AUTH"
        },
        {
            "id": "region",
            "label": "AWS Region",
            "type": "text",
            "defaultValue": "us-east-1",
            "placeholder": "us-east-1",
            "group": "OPTIONS"
        },
        {
            "id": "cluster_identifier",
            "label": "Cluster Identifier",
            "type": "text",
            "placeholder": "my-redshift-cluster",
            "group": "OPTIONS"
        }
    ],
    "ingestionEngines": [
        {
            "label": "S3 Manifest Parallel Cluster COPY",
            "value": "REDSHIFT_S3_COPY",
            "desc": "Massively parallel slice loading from S3 buckets",
            "recommended": true
        },
        {
            "label": "Direct Multi-Row Insert",
            "value": "DIRECT_INSERT",
            "desc": "Standard SQL insert batches"
        }
    ]
} as any,
  'Databricks': {
    "providerId": "Databricks",
    "name": "Databricks",
    "category": "WAREHOUSE",
    "defaultPort": 443,
    "icon": "layers",
    "fields": [
        {
            "id": "server_hostname",
            "label": "Server Hostname",
            "type": "text",
            "required": true,
            "placeholder": "dbc-12345678-abcd.cloud.databricks.com",
            "group": "ENDPOINT"
        },
        {
            "id": "http_path",
            "label": "HTTP Path",
            "type": "text",
            "required": true,
            "placeholder": "/sql/1.0/warehouses/a1b2c3d4e5f6g7h8",
            "group": "ENDPOINT"
        },
        {
            "id": "secret_ref",
            "label": "Personal Access Token / OAuth",
            "type": "secret_ref",
            "required": true,
            "placeholder": "dapi... or vault://secret/...",
            "group": "AUTH"
        },
        {
            "id": "catalog",
            "label": "Unity Catalog",
            "type": "text",
            "defaultValue": "main",
            "placeholder": "main",
            "group": "OPTIONS"
        },
        {
            "id": "schema",
            "label": "Schema",
            "type": "text",
            "defaultValue": "default",
            "placeholder": "default",
            "group": "OPTIONS"
        }
    ],
    "ingestionEngines": [
        {
            "label": "Delta Lake Native Engine & Auto Loader",
            "value": "DELTA_NATIVE_AUTOLOADER",
            "desc": "Direct Parquet ACID micro-batch streaming",
            "recommended": true
        },
        {
            "label": "JDBC Spark Micro-Batch",
            "value": "JDBC_MICRO_BATCH",
            "desc": "Standard JDBC worker partition load"
        }
    ]
} as any,
  'MongoDB': {
    "providerId": "MongoDB",
    "name": "MongoDB",
    "category": "NOSQL",
    "defaultPort": 27017,
    "icon": "boxes",
    "fields": [
        {
            "id": "connection_mode",
            "label": "Topology Mode",
            "type": "select",
            "required": true,
            "defaultValue": "STANDALONE",
            "options": [
                {
                    "label": "Standalone Host:Port",
                    "value": "STANDALONE"
                },
                {
                    "label": "Replica Set / Sharded Cluster",
                    "value": "CLUSTER"
                }
            ],
            "group": "ENDPOINT"
        },
        {
            "id": "host",
            "label": "Host",
            "type": "text",
            "placeholder": "cluster0.mongodb.net",
            "group": "ENDPOINT"
        },
        {
            "id": "port",
            "label": "Port",
            "type": "number",
            "defaultValue": 27017,
            "placeholder": "27017",
            "group": "ENDPOINT"
        },
        {
            "id": "replica_endpoints",
            "label": "Replica Endpoints",
            "type": "textarea",
            "placeholder": "m1.internal:27017, m2.internal:27017",
            "group": "ENDPOINT"
        },
        {
            "id": "replica_set_name",
            "label": "Replica Set Name",
            "type": "text",
            "defaultValue": "rs0",
            "placeholder": "rs0",
            "group": "ENDPOINT"
        },
        {
            "id": "database",
            "label": "Database",
            "type": "text",
            "placeholder": "catalog_prod",
            "group": "ENDPOINT"
        },
        {
            "id": "username",
            "label": "Username",
            "type": "text",
            "placeholder": "admin",
            "group": "AUTH"
        },
        {
            "id": "secret_ref",
            "label": "Secret Ref / Password",
            "type": "secret_ref",
            "placeholder": "vault://secret/prod/mongo",
            "group": "AUTH"
        },
        {
            "id": "auth_source",
            "label": "Auth Source",
            "type": "text",
            "defaultValue": "admin",
            "placeholder": "admin",
            "group": "AUTH"
        }
    ],
    "ingestionEngines": [
        {
            "label": "bulkWrite API (Unordered Chunked Batches)",
            "value": "MONGO_BULK_WRITE",
            "desc": "High-throughput parallel document batches",
            "recommended": true
        },
        {
            "label": "Single Document Insert Stream",
            "value": "SINGLE_INSERT_STREAM",
            "desc": "Standard sequential document insertion"
        }
    ]
} as any,
  'Apache Cassandra': {
    "providerId": "Apache Cassandra",
    "name": "Apache Cassandra",
    "category": "NOSQL",
    "defaultPort": 9042,
    "icon": "boxes",
    "fields": [
        {
            "id": "contact_points",
            "label": "Contact Points",
            "type": "text",
            "required": true,
            "placeholder": "cas1.internal, cas2.internal",
            "group": "ENDPOINT"
        },
        {
            "id": "port",
            "label": "Port",
            "type": "number",
            "defaultValue": 9042,
            "placeholder": "9042",
            "group": "ENDPOINT"
        },
        {
            "id": "keyspace",
            "label": "Keyspace",
            "type": "text",
            "placeholder": "banking_ks",
            "group": "ENDPOINT"
        },
        {
            "id": "username",
            "label": "Username",
            "type": "text",
            "placeholder": "cassandra",
            "group": "AUTH"
        },
        {
            "id": "secret_ref",
            "label": "Secret Ref / Password",
            "type": "secret_ref",
            "placeholder": "vault://secret/prod/cassandra",
            "group": "AUTH"
        },
        {
            "id": "protocol_version",
            "label": "CQL Protocol Version",
            "type": "number",
            "defaultValue": 4,
            "placeholder": "4",
            "group": "OPTIONS"
        }
    ],
    "ingestionEngines": [
        {
            "label": "CQL UNLOGGED BATCH & SSTable Loader",
            "value": "CASSANDRA_SSTABLE_LOADER",
            "desc": "Direct token-aware partition streaming",
            "recommended": true
        },
        {
            "label": "Standard CQL Batch",
            "value": "CQL_BATCH",
            "desc": "Standard logged batches"
        }
    ]
} as any,
  'ScyllaDB': {
    "providerId": "ScyllaDB",
    "name": "ScyllaDB",
    "category": "NOSQL",
    "defaultPort": 9042,
    "icon": "boxes",
    "fields": [
        {
            "id": "contact_points",
            "label": "Contact Points",
            "type": "text",
            "required": true,
            "placeholder": "scylla1.internal, scylla2.internal",
            "group": "ENDPOINT"
        },
        {
            "id": "port",
            "label": "Port",
            "type": "number",
            "defaultValue": 9042,
            "placeholder": "9042",
            "group": "ENDPOINT"
        },
        {
            "id": "keyspace",
            "label": "Keyspace",
            "type": "text",
            "placeholder": "telemetry_ks",
            "group": "ENDPOINT"
        },
        {
            "id": "username",
            "label": "Username",
            "type": "text",
            "placeholder": "scylla",
            "group": "AUTH"
        },
        {
            "id": "secret_ref",
            "label": "Secret Ref / Password",
            "type": "secret_ref",
            "placeholder": "vault://secret/prod/scylla",
            "group": "AUTH"
        }
    ],
    "ingestionEngines": [
        {
            "label": "Shard-Aware Direct Core Ingestion",
            "value": "SCYLLA_SHARD_AWARE",
            "desc": "CPU-core affinity routing bypassing thread cross-locks",
            "recommended": true
        },
        {
            "label": "CQL Batching",
            "value": "CQL_BATCH",
            "desc": "Standard CQL prepared batches"
        }
    ]
} as any,
  'Neo4j': {
    "providerId": "Neo4j",
    "name": "Neo4j",
    "category": "NOSQL",
    "defaultPort": 7687,
    "icon": "boxes",
    "fields": [
        {
            "id": "host",
            "label": "Host",
            "type": "text",
            "required": true,
            "placeholder": "neo4j.prod.internal",
            "group": "ENDPOINT"
        },
        {
            "id": "port",
            "label": "Port",
            "type": "number",
            "defaultValue": 7687,
            "placeholder": "7687",
            "group": "ENDPOINT"
        },
        {
            "id": "database",
            "label": "Database",
            "type": "text",
            "defaultValue": "neo4j",
            "placeholder": "neo4j",
            "group": "ENDPOINT"
        },
        {
            "id": "username",
            "label": "Username",
            "type": "text",
            "required": true,
            "placeholder": "neo4j",
            "group": "AUTH"
        },
        {
            "id": "secret_ref",
            "label": "Secret Ref / Password",
            "type": "secret_ref",
            "required": true,
            "placeholder": "vault://secret/prod/neo4j",
            "group": "AUTH"
        }
    ],
    "ingestionEngines": [
        {
            "label": "UNWIND Cypher Batch Streams & Reactive Bolt",
            "value": "NEO4J_UNWIND_BOLT",
            "desc": "Batch array parameterization in Cypher transactions",
            "recommended": true
        },
        {
            "label": "Transactional Node Writes",
            "value": "SINGLE_NODE_WRITE",
            "desc": "Standard single-statement graph creation"
        }
    ]
} as any,
  'Redis': {
    "providerId": "Redis",
    "name": "Redis",
    "category": "NOSQL",
    "defaultPort": 6379,
    "icon": "boxes",
    "fields": [
        {
            "id": "host",
            "label": "Host",
            "type": "text",
            "required": true,
            "placeholder": "redis.prod.internal",
            "group": "ENDPOINT"
        },
        {
            "id": "port",
            "label": "Port",
            "type": "number",
            "defaultValue": 6379,
            "placeholder": "6379",
            "group": "ENDPOINT"
        },
        {
            "id": "db_index",
            "label": "Database Index (0-15)",
            "type": "number",
            "defaultValue": 0,
            "placeholder": "0",
            "group": "ENDPOINT"
        },
        {
            "id": "username",
            "label": "Username (ACL)",
            "type": "text",
            "defaultValue": "default",
            "placeholder": "default",
            "group": "AUTH"
        },
        {
            "id": "secret_ref",
            "label": "Secret Ref / AUTH Password",
            "type": "secret_ref",
            "placeholder": "vault://secret/prod/redis",
            "group": "AUTH"
        }
    ],
    "ingestionEngines": [
        {
            "label": "Multi-Bulk RESP Pipeline Streaming Buffer",
            "value": "REDIS_RESP_PIPELINE",
            "desc": "Pipelined non-blocking socket buffer streaming",
            "recommended": true
        },
        {
            "label": "Synchronous Key-Value SET",
            "value": "SYNC_SET",
            "desc": "Individual round-trip SET calls"
        }
    ]
} as any,
  'KeyDB': {
    "providerId": "KeyDB",
    "name": "KeyDB",
    "category": "NOSQL",
    "defaultPort": 6379,
    "icon": "boxes",
    "fields": [
        {
            "id": "host",
            "label": "Host",
            "type": "text",
            "required": true,
            "placeholder": "keydb.prod.internal",
            "group": "ENDPOINT"
        },
        {
            "id": "port",
            "label": "Port",
            "type": "number",
            "defaultValue": 6379,
            "placeholder": "6379",
            "group": "ENDPOINT"
        },
        {
            "id": "db_index",
            "label": "Database Index (0-15)",
            "type": "number",
            "defaultValue": 0,
            "placeholder": "0",
            "group": "ENDPOINT"
        },
        {
            "id": "username",
            "label": "Username",
            "type": "text",
            "defaultValue": "default",
            "placeholder": "default",
            "group": "AUTH"
        },
        {
            "id": "secret_ref",
            "label": "Secret Ref / AUTH Password",
            "type": "secret_ref",
            "placeholder": "vault://secret/prod/keydb",
            "group": "AUTH"
        }
    ],
    "ingestionEngines": [
        {
            "label": "Multithreaded Pipelining Engine",
            "value": "KEYDB_MULTI_PIPELINE",
            "desc": "Multi-core concurrent pipelined socket execution",
            "recommended": true
        },
        {
            "label": "Standard SET",
            "value": "STANDARD_SET",
            "desc": "Standard command execution"
        }
    ]
} as any,
  'Elasticsearch': {
    "providerId": "Elasticsearch",
    "name": "Elasticsearch",
    "category": "NOSQL",
    "defaultPort": 9200,
    "icon": "boxes",
    "fields": [
        {
            "id": "node_urls",
            "label": "Node URLs",
            "type": "textarea",
            "required": true,
            "placeholder": "https://es1:9200, https://es2:9200",
            "group": "ENDPOINT"
        },
        {
            "id": "auth_type",
            "label": "Authentication Type",
            "type": "select",
            "required": true,
            "defaultValue": "BASIC",
            "options": [
                {
                    "label": "Basic Authentication (Username/Password)",
                    "value": "BASIC"
                },
                {
                    "label": "API Key",
                    "value": "API_KEY"
                }
            ],
            "group": "AUTH"
        },
        {
            "id": "username",
            "label": "Username",
            "type": "text",
            "placeholder": "elastic",
            "group": "AUTH"
        },
        {
            "id": "secret_ref",
            "label": "Secret Ref / Password",
            "type": "secret_ref",
            "placeholder": "vault://secret/prod/es_pass",
            "group": "AUTH"
        },
        {
            "id": "api_key",
            "label": "API Key",
            "type": "secret_ref",
            "placeholder": "vault://secret/prod/es_api_key",
            "group": "AUTH"
        }
    ],
    "ingestionEngines": [
        {
            "label": "Native _bulk API (Chunked NDJSON Multi-Worker)",
            "value": "ES_BULK_API",
            "desc": "Parallel worker threads with NDJSON chunk streaming",
            "recommended": true
        },
        {
            "label": "Single Document Index API",
            "value": "SINGLE_INDEX",
            "desc": "Standard document index endpoint"
        }
    ]
} as any,
  'OpenSearch': {
    "providerId": "OpenSearch",
    "name": "OpenSearch",
    "category": "NOSQL",
    "defaultPort": 9200,
    "icon": "boxes",
    "fields": [
        {
            "id": "node_urls",
            "label": "Node URLs",
            "type": "textarea",
            "required": true,
            "placeholder": "https://opensearch:9200",
            "group": "ENDPOINT"
        },
        {
            "id": "auth_type",
            "label": "Authentication Type",
            "type": "select",
            "required": true,
            "defaultValue": "BASIC",
            "options": [
                {
                    "label": "Basic Authentication (Username/Password)",
                    "value": "BASIC"
                },
                {
                    "label": "API Key / SigV4",
                    "value": "API_KEY"
                }
            ],
            "group": "AUTH"
        },
        {
            "id": "username",
            "label": "Username",
            "type": "text",
            "placeholder": "admin",
            "group": "AUTH"
        },
        {
            "id": "secret_ref",
            "label": "Secret Ref / Password",
            "type": "secret_ref",
            "placeholder": "vault://secret/prod/os_pass",
            "group": "AUTH"
        },
        {
            "id": "api_key",
            "label": "API Key",
            "type": "secret_ref",
            "placeholder": "vault://secret/prod/os_api_key",
            "group": "AUTH"
        }
    ],
    "ingestionEngines": [
        {
            "label": "Native _bulk API with Concurrent Queues",
            "value": "OPENSEARCH_BULK_API",
            "desc": "Async bulk indexing queues with SigV4 support",
            "recommended": true
        },
        {
            "label": "Standard Index API",
            "value": "STANDARD_INDEX",
            "desc": "Standard index endpoint"
        }
    ]
} as any,
  'Apache Kafka': {
    "providerId": "Apache Kafka",
    "name": "Apache Kafka",
    "category": "STREAMING",
    "defaultPort": 9092,
    "icon": "radio",
    "fields": [
        {
            "id": "bootstrap_brokers",
            "label": "Bootstrap Brokers",
            "type": "textarea",
            "required": true,
            "placeholder": "kafka1:9092, kafka2:9092",
            "group": "ENDPOINT"
        },
        {
            "id": "security_protocol",
            "label": "Security Protocol",
            "type": "select",
            "required": true,
            "defaultValue": "PLAINTEXT",
            "options": [
                {
                    "label": "PLAINTEXT (Unencrypted)",
                    "value": "PLAINTEXT"
                },
                {
                    "label": "SSL",
                    "value": "SSL"
                },
                {
                    "label": "SASL_PLAINTEXT",
                    "value": "SASL_PLAINTEXT"
                },
                {
                    "label": "SASL_SSL",
                    "value": "SASL_SSL"
                }
            ],
            "group": "SECURITY"
        },
        {
            "id": "sasl_mechanism",
            "label": "SASL Mechanism",
            "type": "select",
            "defaultValue": "PLAIN",
            "options": [
                {
                    "label": "PLAIN",
                    "value": "PLAIN"
                },
                {
                    "label": "SCRAM-SHA-256",
                    "value": "SCRAM-SHA-256"
                },
                {
                    "label": "SCRAM-SHA-512",
                    "value": "SCRAM-SHA-512"
                }
            ],
            "group": "AUTH"
        },
        {
            "id": "sasl_username",
            "label": "SASL Username",
            "type": "text",
            "placeholder": "akaal_user",
            "group": "AUTH"
        },
        {
            "id": "secret_ref",
            "label": "Secret Ref / SASL Password",
            "type": "secret_ref",
            "placeholder": "vault://secret/prod/kafka",
            "group": "AUTH"
        },
        {
            "id": "consumer_group",
            "label": "Consumer Group",
            "type": "text",
            "defaultValue": "akaal-consumer-group",
            "placeholder": "akaal-consumer-group",
            "group": "OPTIONS"
        },
        {
            "id": "schema_registry_url",
            "label": "Schema Registry URL",
            "type": "text",
            "placeholder": "http://schema-registry:8081",
            "group": "OPTIONS"
        }
    ],
    "ingestionEngines": [
        {
            "label": "High-Throughput Producer Record Batching",
            "value": "KAFKA_BATCH_PRODUCER",
            "desc": "Buffered records with LZ4/Snappy compression and batching",
            "recommended": true
        },
        {
            "label": "Synchronous Single Record Send",
            "value": "SYNC_SEND",
            "desc": "Per-message individual ack delivery"
        }
    ]
} as any,
  'Amazon Kinesis Data Streams': {
    "providerId": "Amazon Kinesis Data Streams",
    "name": "Amazon Kinesis Data Streams",
    "category": "STREAMING",
    "defaultPort": 443,
    "icon": "radio",
    "fields": [
        {
            "id": "stream_name",
            "label": "Stream Name",
            "type": "text",
            "required": true,
            "placeholder": "telemetry-stream",
            "group": "ENDPOINT"
        },
        {
            "id": "region",
            "label": "AWS Region",
            "type": "text",
            "required": true,
            "defaultValue": "us-east-1",
            "placeholder": "us-east-1",
            "group": "ENDPOINT"
        },
        {
            "id": "auth_type",
            "label": "Authentication Method",
            "type": "select",
            "required": true,
            "defaultValue": "ACCESS_KEYS",
            "options": [
                {
                    "label": "AWS Access Key & Secret",
                    "value": "ACCESS_KEYS"
                },
                {
                    "label": "Ambient IAM Role / IRSA",
                    "value": "IAM_ROLE"
                }
            ],
            "group": "AUTH"
        },
        {
            "id": "aws_access_key_id",
            "label": "AWS Access Key ID",
            "type": "text",
            "placeholder": "AKIAIOSFODNN7EXAMPLE",
            "group": "AUTH"
        },
        {
            "id": "secret_ref",
            "label": "Secret Ref / Secret Access Key",
            "type": "secret_ref",
            "placeholder": "vault://secret/prod/kinesis_key",
            "group": "AUTH"
        }
    ],
    "ingestionEngines": [
        {
            "label": "PutRecords Batch API (500 records / 5MB burst)",
            "value": "KINESIS_PUT_RECORDS",
            "desc": "Burst record bundle ingest with partition hash key",
            "recommended": true
        },
        {
            "label": "Single Record PutRecord",
            "value": "PUT_RECORD",
            "desc": "Individual item ingestion"
        }
    ]
} as any,
  'Azure Event Hubs': {
    "providerId": "Azure Event Hubs",
    "name": "Azure Event Hubs",
    "category": "STREAMING",
    "defaultPort": 443,
    "icon": "radio",
    "fields": [
        {
            "id": "namespace",
            "label": "Namespace FQDN",
            "type": "text",
            "required": true,
            "placeholder": "my-namespace.servicebus.windows.net",
            "group": "ENDPOINT"
        },
        {
            "id": "event_hub_name",
            "label": "Event Hub Entity Name",
            "type": "text",
            "placeholder": "ingest-hub",
            "group": "ENDPOINT"
        },
        {
            "id": "secret_ref",
            "label": "Secret Ref / SharedAccessKey Connection String",
            "type": "secret_ref",
            "required": true,
            "placeholder": "Endpoint=sb://...;SharedAccessKey=...",
            "group": "AUTH"
        }
    ],
    "ingestionEngines": [
        {
            "label": "AMQP EventDataBatch Pipeline Streaming",
            "value": "EVENT_DATA_BATCH",
            "desc": "Binary AMQP packet stream batching",
            "recommended": true
        },
        {
            "label": "Single Event Send",
            "value": "SINGLE_EVENT",
            "desc": "Standard single event dispatch"
        }
    ]
} as any,
  'Google Cloud Pub/Sub': {
    "providerId": "Google Cloud Pub/Sub",
    "name": "Google Cloud Pub/Sub",
    "category": "STREAMING",
    "defaultPort": 443,
    "icon": "radio",
    "fields": [
        {
            "id": "project_id",
            "label": "GCP Project ID",
            "type": "text",
            "required": true,
            "placeholder": "my-pubsub-project",
            "group": "ENDPOINT"
        },
        {
            "id": "topic_id",
            "label": "Topic ID",
            "type": "text",
            "placeholder": "cdc-events-topic",
            "group": "ENDPOINT"
        },
        {
            "id": "subscription_id",
            "label": "Subscription ID",
            "type": "text",
            "placeholder": "sub-akaal-read",
            "group": "ENDPOINT"
        },
        {
            "id": "auth_type",
            "label": "Authentication Method",
            "type": "select",
            "required": true,
            "defaultValue": "SERVICE_ACCOUNT_JSON",
            "options": [
                {
                    "label": "Service Account Key (JSON)",
                    "value": "SERVICE_ACCOUNT_JSON"
                },
                {
                    "label": "Application Default Credentials (ADC)",
                    "value": "ADC"
                }
            ],
            "group": "AUTH"
        }
    ],
    "ingestionEngines": [
        {
            "label": "gRPC PublishBatch Bundle Streaming",
            "value": "PUBSUB_PUBLISH_BATCH",
            "desc": "High-volume gRPC batch publishing",
            "recommended": true
        },
        {
            "label": "Single Publish",
            "value": "SINGLE_PUBLISH",
            "desc": "Single message publish"
        }
    ]
} as any,
  'Amazon S3': {
    "providerId": "Amazon S3",
    "name": "Amazon S3",
    "category": "STORAGE",
    "defaultPort": 443,
    "icon": "hard-drive",
    "fields": [
        {
            "id": "bucket_name",
            "label": "Bucket Name",
            "type": "text",
            "required": true,
            "placeholder": "company-data-lake-prod",
            "group": "ENDPOINT"
        },
        {
            "id": "region",
            "label": "AWS Region",
            "type": "text",
            "required": true,
            "defaultValue": "us-east-1",
            "placeholder": "us-east-1",
            "group": "ENDPOINT"
        },
        {
            "id": "prefix",
            "label": "Folder Prefix",
            "type": "text",
            "placeholder": "exports/2026/",
            "group": "ENDPOINT"
        },
        {
            "id": "auth_type",
            "label": "Authentication Method",
            "type": "select",
            "required": true,
            "defaultValue": "ACCESS_KEYS",
            "options": [
                {
                    "label": "AWS Access Key & Secret",
                    "value": "ACCESS_KEYS"
                },
                {
                    "label": "Ambient IAM Role / IRSA",
                    "value": "IAM_ROLE"
                }
            ],
            "group": "AUTH"
        },
        {
            "id": "aws_access_key_id",
            "label": "AWS Access Key ID",
            "type": "text",
            "placeholder": "AKIA...",
            "group": "AUTH"
        },
        {
            "id": "secret_ref",
            "label": "Secret Ref / Secret Access Key",
            "type": "secret_ref",
            "placeholder": "vault://secret/prod/s3_key",
            "group": "AUTH"
        },
        {
            "id": "custom_endpoint",
            "label": "Custom S3 Endpoint (MinIO / Wasabi)",
            "type": "text",
            "placeholder": "https://s3.custom.internal",
            "group": "OPTIONS"
        }
    ],
    "ingestionEngines": [
        {
            "label": "S3 Multipart Upload API + Parquet Stream",
            "value": "S3_MULTIPART_PARQUET",
            "desc": "Parallel multipart part streaming with columnar encoding",
            "recommended": true
        },
        {
            "label": "Direct PutObject Single Part",
            "value": "DIRECT_PUT_OBJECT",
            "desc": "Standard S3 object write"
        }
    ]
} as any,
  'Google Cloud Storage': {
    "providerId": "Google Cloud Storage",
    "name": "Google Cloud Storage",
    "category": "STORAGE",
    "defaultPort": 443,
    "icon": "hard-drive",
    "fields": [
        {
            "id": "bucket_name",
            "label": "GCS Bucket Name",
            "type": "text",
            "required": true,
            "placeholder": "gcp-analytics-lake",
            "group": "ENDPOINT"
        },
        {
            "id": "project_id",
            "label": "GCP Project ID",
            "type": "text",
            "placeholder": "my-gcp-project",
            "group": "ENDPOINT"
        },
        {
            "id": "prefix",
            "label": "Prefix",
            "type": "text",
            "placeholder": "lakehouse/data/",
            "group": "ENDPOINT"
        },
        {
            "id": "auth_type",
            "label": "Authentication Method",
            "type": "select",
            "required": true,
            "defaultValue": "SERVICE_ACCOUNT_JSON",
            "options": [
                {
                    "label": "Service Account Key (JSON)",
                    "value": "SERVICE_ACCOUNT_JSON"
                },
                {
                    "label": "Application Default Credentials (ADC)",
                    "value": "ADC"
                }
            ],
            "group": "AUTH"
        }
    ],
    "ingestionEngines": [
        {
            "label": "GCS Parallel Composite & Resumable Multipart",
            "value": "GCS_RESUMABLE_MULTIPART",
            "desc": "Chunked parallel composite stream",
            "recommended": true
        },
        {
            "label": "Standard Object Insert",
            "value": "STANDARD_OBJECT_INSERT",
            "desc": "Single-part media upload"
        }
    ]
} as any,
  'Azure Blob Storage': {
    "providerId": "Azure Blob Storage",
    "name": "Azure Blob Storage",
    "category": "STORAGE",
    "defaultPort": 443,
    "icon": "hard-drive",
    "fields": [
        {
            "id": "container_name",
            "label": "Container Name",
            "type": "text",
            "required": true,
            "placeholder": "raw-archives",
            "group": "ENDPOINT"
        },
        {
            "id": "prefix",
            "label": "Blob Virtual Prefix",
            "type": "text",
            "placeholder": "incoming/",
            "group": "ENDPOINT"
        },
        {
            "id": "auth_type",
            "label": "Authentication Type",
            "type": "select",
            "required": true,
            "defaultValue": "CONN_STRING",
            "options": [
                {
                    "label": "Connection String",
                    "value": "CONN_STRING"
                },
                {
                    "label": "Storage Account Key",
                    "value": "ACCOUNT_KEY"
                },
                {
                    "label": "SAS Token",
                    "value": "SAS_TOKEN"
                }
            ],
            "group": "AUTH"
        },
        {
            "id": "secret_ref",
            "label": "Connection String",
            "type": "secret_ref",
            "placeholder": "DefaultEndpointsProtocol=https;...",
            "group": "AUTH"
        },
        {
            "id": "storage_account_name",
            "label": "Storage Account Name",
            "type": "text",
            "placeholder": "mystorageacc",
            "group": "AUTH"
        },
        {
            "id": "account_key",
            "label": "Account Key",
            "type": "secret_ref",
            "placeholder": "vault://secret/prod/blob_key",
            "group": "AUTH"
        },
        {
            "id": "sas_token",
            "label": "SAS Token",
            "type": "secret_ref",
            "placeholder": "?sv=2020-08-04&ss=b&...",
            "group": "AUTH"
        }
    ],
    "ingestionEngines": [
        {
            "label": "PutBlock & PutBlockList Parallel Chunking",
            "value": "BLOB_PUT_BLOCK_LIST",
            "desc": "Block chunk streaming with parallel commit",
            "recommended": true
        },
        {
            "label": "Direct PutBlob",
            "value": "DIRECT_PUT_BLOB",
            "desc": "Single blob write"
        }
    ]
} as any,
  'MinIO': {
    "providerId": "MinIO",
    "name": "MinIO",
    "category": "STORAGE",
    "defaultPort": 9000,
    "icon": "hard-drive",
    "fields": [
        {
            "id": "host",
            "label": "Host",
            "type": "text",
            "required": true,
            "placeholder": "minio.internal",
            "group": "ENDPOINT"
        },
        {
            "id": "port",
            "label": "Port",
            "type": "number",
            "defaultValue": 9000,
            "placeholder": "9000",
            "group": "ENDPOINT"
        },
        {
            "id": "bucket_name",
            "label": "Bucket Name",
            "type": "text",
            "placeholder": "akaal-minio-bucket",
            "group": "ENDPOINT"
        },
        {
            "id": "access_key",
            "label": "Access Key",
            "type": "text",
            "required": true,
            "defaultValue": "minioadmin",
            "placeholder": "minioadmin",
            "group": "AUTH"
        },
        {
            "id": "secret_ref",
            "label": "Secret Ref / Secret Key",
            "type": "secret_ref",
            "required": true,
            "placeholder": "vault://secret/prod/minio",
            "group": "AUTH"
        }
    ],
    "ingestionEngines": [
        {
            "label": "S3-Compatible Parallel Multipart Chunking",
            "value": "MINIO_MULTIPART_ENGINE",
            "desc": "Parallel high-speed chunk pipeline",
            "recommended": true
        },
        {
            "label": "Single Part Upload",
            "value": "SINGLE_PART_UPLOAD",
            "desc": "Standard object write"
        }
    ]
} as any,
  'Apache HDFS': {
    "providerId": "Apache HDFS",
    "name": "Apache HDFS",
    "category": "STORAGE",
    "defaultPort": 9870,
    "icon": "hard-drive",
    "fields": [
        {
            "id": "namenode_host",
            "label": "Namenode Host",
            "type": "text",
            "required": true,
            "placeholder": "hdfs-nn.corp.internal",
            "group": "ENDPOINT"
        },
        {
            "id": "port",
            "label": "Port",
            "type": "number",
            "defaultValue": 9870,
            "placeholder": "9870",
            "group": "ENDPOINT"
        },
        {
            "id": "root_path",
            "label": "Root Path",
            "type": "text",
            "defaultValue": "/",
            "placeholder": "/data/migration",
            "group": "ENDPOINT"
        },
        {
            "id": "hdfs_user",
            "label": "HDFS User",
            "type": "text",
            "defaultValue": "hdfs",
            "placeholder": "hdfs",
            "group": "AUTH"
        },
        {
            "id": "access_mode",
            "label": "Access Mode",
            "type": "select",
            "defaultValue": "WEBHDFS",
            "options": [
                {
                    "label": "WebHDFS (HTTP REST)",
                    "value": "WEBHDFS"
                },
                {
                    "label": "RPC (Binary IPC)",
                    "value": "RPC"
                }
            ],
            "group": "OPTIONS"
        }
    ],
    "ingestionEngines": [
        {
            "label": "WebHDFS Chunked Append & DFSOutputStream RPC",
            "value": "HDFS_DFS_STREAM_RPC",
            "desc": "Direct namenode/datanode RPC block streaming",
            "recommended": true
        },
        {
            "label": "Single Block Write",
            "value": "SINGLE_BLOCK_WRITE",
            "desc": "Standard REST WebHDFS write"
        }
    ]
} as any,
} as any;

export const ALL_28_PROVIDER_SCHEMAS = ALL_48_PROVIDER_SCHEMAS;
ALL_48_PROVIDER_SCHEMAS['Oracle'] = { ...ALL_48_PROVIDER_SCHEMAS['Oracle Database'], providerId: 'Oracle' };
ALL_48_PROVIDER_SCHEMAS['Microsoft SQL Server'] = { ...ALL_48_PROVIDER_SCHEMAS['Microsoft SQL Server (MSSQL)'], providerId: 'Microsoft SQL Server' };
ALL_48_PROVIDER_SCHEMAS['IBM Db2'] = { ...ALL_48_PROVIDER_SCHEMAS['IBM Db2 LUW'], providerId: 'IBM Db2' };
ALL_48_PROVIDER_SCHEMAS['Snowflake'] = { ...ALL_48_PROVIDER_SCHEMAS['Snowflake Data Cloud'], providerId: 'Snowflake' };
ALL_48_PROVIDER_SCHEMAS['Neo4j Graph Database'] = { ...ALL_48_PROVIDER_SCHEMAS['Neo4j'], providerId: 'Neo4j Graph Database' };
ALL_48_PROVIDER_SCHEMAS['Databricks / Delta Lake'] = { ...ALL_48_PROVIDER_SCHEMAS['Databricks'], providerId: 'Databricks / Delta Lake' };
ALL_48_PROVIDER_SCHEMAS['Amazon Kinesis'] = { ...ALL_48_PROVIDER_SCHEMAS['Amazon Kinesis Data Streams'], providerId: 'Amazon Kinesis' };
