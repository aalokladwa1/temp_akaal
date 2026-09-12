/**
 * AKAAL Administration — 5.6 Connector & Plugin Center Service
 * Authoritative presentation service backed by canonical provider catalog and extension registry.
 */

import { Injectable, signal, computed } from '@angular/core';
import {
  ConnectorDefinition,
  ExternalConnectorRegistration,
  PluginDefinition,
  SdkConfiguration
} from '../models/connectors-plugins.models';

@Injectable({
  providedIn: 'root'
})
export class ConnectorsPluginsService {
  // Built-in Connectors (Sample populated from canonical 49-provider catalog)
  public connectors = signal<ConnectorDefinition[]>([
    {
      id: 'conn-pg-01',
      name: 'PostgreSQL Enterprise Connector',
      providerId: 'postgresql',
      category: 'Relational & Distributed SQL',
      version: '3.8.2',
      driverVersion: 'pgjdbc-42.7.2',
      isBuiltIn: true,
      applicability: 'SOURCE_AND_TARGET',
      capabilities: {
        supportsSource: true,
        supportsTarget: true,
        supportsCdc: true,
        supportsBulk: true,
        supportsSchemaIntrospection: true,
        supportsValidationSampling: true,
        supportsStreaming: false
      },
      supportedDialects: ['PostgreSQL 12-16', 'TimescaleDB', 'Amazon Aurora PG', 'Azure Flexible PG'],
      certificationLevel: 'LIVE_PROVEN',
      qualificationNotes: 'Passed comprehensive end-to-end integration test suites across full transactional CDC boundaries.',
      lastTestedDate: '2026-02-15',
      engineProtocolVersion: 'v2.4'
    },
    {
      id: 'conn-ora-01',
      name: 'Oracle Database Enterprise Connector',
      providerId: 'oracle',
      category: 'Relational & Distributed SQL',
      version: '4.1.0',
      driverVersion: 'ojdbc11-23.3.0',
      isBuiltIn: true,
      applicability: 'SOURCE_AND_TARGET',
      capabilities: {
        supportsSource: true,
        supportsTarget: true,
        supportsCdc: true,
        supportsBulk: true,
        supportsSchemaIntrospection: true,
        supportsValidationSampling: true,
        supportsStreaming: false
      },
      supportedDialects: ['Oracle 19c', 'Oracle 21c', 'Oracle 23c Free', 'Exadata Cloud'],
      certificationLevel: 'LIVE_PROVEN',
      qualificationNotes: 'Validated with LogMiner & XStream CDC replication buffers.',
      lastTestedDate: '2026-02-12',
      engineProtocolVersion: 'v2.4'
    },
    {
      id: 'conn-sf-01',
      name: 'Snowflake Cloud Data Warehouse Connector',
      providerId: 'snowflake',
      category: 'Warehouse & Lakehouse',
      version: '3.5.1',
      driverVersion: 'snowflake-jdbc-3.14.4',
      isBuiltIn: true,
      applicability: 'SOURCE_AND_TARGET',
      capabilities: {
        supportsSource: true,
        supportsTarget: true,
        supportsCdc: false,
        supportsBulk: true,
        supportsSchemaIntrospection: true,
        supportsValidationSampling: true,
        supportsStreaming: true
      },
      supportedDialects: ['Snowflake Standard', 'Snowflake Enterprise', 'Snowflake VPS'],
      certificationLevel: 'LIVE_PROVEN',
      qualificationNotes: 'Snowpipe streaming and high-throughput multi-file COPY ingestion verified.',
      lastTestedDate: '2026-02-18',
      engineProtocolVersion: 'v2.4'
    },
    {
      id: 'conn-bq-01',
      name: 'Google BigQuery High-Throughput Connector',
      providerId: 'bigquery',
      category: 'Warehouse & Lakehouse',
      version: '2.9.0',
      driverVersion: 'google-cloud-bigquery-2.35.0',
      isBuiltIn: true,
      applicability: 'SOURCE_AND_TARGET',
      capabilities: {
        supportsSource: true,
        supportsTarget: true,
        supportsCdc: false,
        supportsBulk: true,
        supportsSchemaIntrospection: true,
        supportsValidationSampling: true,
        supportsStreaming: true
      },
      supportedDialects: ['Google BigQuery Standard SQL', 'BigQuery Omni'],
      certificationLevel: 'INTEGRATION_PROVEN',
      qualificationNotes: 'BigQuery Storage Write API and Storage Read API streaming qualified.',
      lastTestedDate: '2026-01-29',
      engineProtocolVersion: 'v2.3'
    },
    {
      id: 'conn-kafka-01',
      name: 'Apache Kafka Event Streaming Connector',
      providerId: 'kafka',
      category: 'Streaming & Event Broker',
      version: '3.4.0',
      driverVersion: 'kafka-clients-3.7.0',
      isBuiltIn: true,
      applicability: 'SOURCE_AND_TARGET',
      capabilities: {
        supportsSource: true,
        supportsTarget: true,
        supportsCdc: false,
        supportsBulk: false,
        supportsSchemaIntrospection: true,
        supportsValidationSampling: true,
        supportsStreaming: true
      },
      supportedDialects: ['Apache Kafka 3.x', 'Confluent Cloud', 'AWS MSK', 'Redpanda'],
      certificationLevel: 'LIVE_PROVEN',
      qualificationNotes: 'Exact-once semantics (EOS) and Schema Registry Avro/Protobuf bindings proven.',
      lastTestedDate: '2026-02-14',
      engineProtocolVersion: 'v2.4'
    },
    {
      id: 'conn-mongo-01',
      name: 'MongoDB Document Connector',
      providerId: 'mongodb',
      category: 'NoSQL & Document Store',
      version: '3.2.1',
      driverVersion: 'mongodb-driver-sync-5.0.0',
      isBuiltIn: true,
      applicability: 'SOURCE_AND_TARGET',
      capabilities: {
        supportsSource: true,
        supportsTarget: true,
        supportsCdc: true,
        supportsBulk: true,
        supportsSchemaIntrospection: true,
        supportsValidationSampling: true,
        supportsStreaming: false
      },
      supportedDialects: ['MongoDB 5.0 - 7.0', 'MongoDB Atlas', 'Amazon DocumentDB'],
      certificationLevel: 'INTEGRATION_PROVEN',
      qualificationNotes: 'Change Streams CDC listening and bulk upsert operations verified.',
      lastTestedDate: '2026-02-04',
      engineProtocolVersion: 'v2.3'
    },
    {
      id: 'conn-s3-01',
      name: 'Amazon S3 Parquet / Delta Object Connector',
      providerId: 's3',
      category: 'Object Storage & Lake',
      version: '2.8.4',
      driverVersion: 'aws-sdk-s3-2.25.10',
      isBuiltIn: true,
      applicability: 'SOURCE_AND_TARGET',
      capabilities: {
        supportsSource: true,
        supportsTarget: true,
        supportsCdc: false,
        supportsBulk: true,
        supportsSchemaIntrospection: true,
        supportsValidationSampling: true,
        supportsStreaming: true
      },
      supportedDialects: ['AWS S3', 'MinIO', 'Ceph S3', 'Cloudflare R2'],
      certificationLevel: 'LIVE_PROVEN',
      qualificationNotes: 'Multipart parallel upload and Apache Parquet column predicate pushdown tested.',
      lastTestedDate: '2026-02-10',
      engineProtocolVersion: 'v2.4'
    },
    {
      id: 'conn-redis-01',
      name: 'Redis In-Memory Key-Value Connector',
      providerId: 'redis',
      category: 'In-Memory & Cache',
      version: '2.1.0',
      driverVersion: 'jedis-5.1.0',
      isBuiltIn: true,
      applicability: 'TARGET_ONLY',
      capabilities: {
        supportsSource: false,
        supportsTarget: true,
        supportsCdc: false,
        supportsBulk: true,
        supportsSchemaIntrospection: false,
        supportsValidationSampling: true,
        supportsStreaming: false
      },
      supportedDialects: ['Redis 6.2 - 7.2', 'Redis Enterprise', 'AWS ElastiCache'],
      certificationLevel: 'UNIT_PROVEN',
      qualificationNotes: 'Pipelined writes and cluster hash-slot sharding unit proven.',
      lastTestedDate: '2026-01-20',
      engineProtocolVersion: 'v2.2'
    }
  ]);

  // External Connectors
  public externalConnectors = signal<ExternalConnectorRegistration[]>([
    {
      id: 'ext-conn-01',
      name: 'Custom SAP HANA Egress Connector',
      providerIdentifier: 'sap_hana_custom',
      binaryPath: '/opt/akaal/connectors/ext/sap-hana-x64.so',
      protocolVersion: 'v2.4',
      registeredAt: '2026-01-14',
      sha256Checksum: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      certificationLevel: 'UNIT_PROVEN',
      status: 'ACTIVE'
    },
    {
      id: 'ext-conn-02',
      name: 'Teradata Enterprise FastExport Extension',
      providerIdentifier: 'teradata_fastexport',
      binaryPath: '/opt/akaal/connectors/ext/teradata-fastexport.bin',
      protocolVersion: 'v2.3',
      registeredAt: '2026-02-02',
      sha256Checksum: '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
      certificationLevel: 'UNIT_PROVEN',
      status: 'ACTIVE'
    }
  ]);

  // Extension Plugins
  public plugins = signal<PluginDefinition[]>([
    {
      id: 'plg-01',
      name: 'FF3-1 Format-Preserving Encryption Tokenizer',
      code: 'FPE_FF3_TOKENIZER',
      vendor: 'Akaal Security Labs',
      version: '1.4.2',
      pluginType: 'TRANSFORMER',
      status: 'ACTIVE',
      signatureStatus: 'VERIFIED_DIGEST',
      sha256Digest: '7b52009b64fd0a2a49e6d8a939753077792b0554ca5a6e8b4e76a666e5f8f8f2',
      permissions: ['TRANSFORM_ROW', 'READ_SCHEMA_METADATA'],
      description: 'NIST SP 800-38G Rev 1 compliant format-preserving encryption plugin for card numbers and SSNs.',
      installedAt: '2025-11-10'
    },
    {
      id: 'plg-02',
      name: 'Great Expectations Rule Evaluator',
      code: 'GX_RULE_EVALUATOR',
      vendor: 'Data Integrity Consortium',
      version: '0.9.5',
      pluginType: 'VALIDATOR',
      status: 'ACTIVE',
      signatureStatus: 'VERIFIED_DIGEST',
      sha256Digest: '8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4',
      permissions: ['READ_ROW_STREAM', 'EMIT_VALIDATION_EVENT'],
      description: 'Executes Great Expectations assertions during in-flight migration stages.',
      installedAt: '2025-12-05'
    },
    {
      id: 'plg-03',
      name: 'PagerDuty Incident Dispatch Hook',
      code: 'PAGERDUTY_DISPATCH',
      vendor: 'Ops Integrations Corp',
      version: '1.1.0',
      pluginType: 'REPORTER',
      status: 'ACTIVE',
      signatureStatus: 'VERIFIED_DIGEST',
      sha256Digest: 'ec74723049b251a37c95a25ebef9170fc8e8436eb10065e1eb2c64b58b4f1778',
      permissions: ['NETWORK_EGRESS', 'EMIT_ALERT'],
      description: 'Dispatches high-severity schema drift and migration abort alerts directly to PagerDuty services.',
      installedAt: '2026-01-18'
    }
  ]);

  // SDK Configuration
  public sdkConfig = signal<SdkConfiguration>({
    sdkVersion: '2.4.1',
    supportedRuntimes: ['Go 1.23+', 'Rust 1.80+ (WASM)', 'Node.js 22 LTS', 'Python 3.12'],
    maxExecutionTimeoutSec: 120,
    sandboxingEnforced: true,
    grpcSocketPath: '/run/akaal/extension-ipc.sock',
    wasmRuntimeEngine: 'Wasmtime 24.0.0'
  });

  public getConnectorById(id: string): ConnectorDefinition | undefined {
    return this.connectors().find(c => c.id === id);
  }

  public getPluginById(id: string): PluginDefinition | undefined {
    return this.plugins().find(p => p.id === id);
  }

  public registerExternalConnector(entry: Omit<ExternalConnectorRegistration, 'id' | 'registeredAt' | 'certificationLevel' | 'status'>): void {
    const newRecord: ExternalConnectorRegistration = {
      ...entry,
      id: `ext-conn-${Date.now()}`,
      registeredAt: new Date().toISOString().split('T')[0],
      certificationLevel: 'UNIT_PROVEN',
      status: 'ACTIVE'
    };
    this.externalConnectors.update(list => [newRecord, ...list]);
  }

  public togglePluginStatus(id: string): void {
    this.plugins.update(list =>
      list.map(p => {
        if (p.id === id) {
          return {
            ...p,
            status: p.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE'
          };
        }
        return p;
      })
    );
  }
}
