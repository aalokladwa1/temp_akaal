/**
 * AKAAL Administration — 5.6 Connector & Plugin Center Models
 * Governs provider connector implementations, capabilities, compatibility,
 * qualification evidence, and extension plugins.
 */

export type ConnectorCertificationLevel =
  | 'LIVE_PROVEN'
  | 'INTEGRATION_PROVEN'
  | 'UNIT_PROVEN'
  | 'IMPLEMENTED';

export type PluginType =
  | 'TRANSFORMER'
  | 'VALIDATOR'
  | 'REPORTER'
  | 'AUTH_HOOK';

export type PluginStatus =
  | 'ACTIVE'
  | 'DISABLED';

export type PluginSignatureStatus =
  | 'VERIFIED_DIGEST'
  | 'UNSIGNED'
  | 'DIGEST_MISMATCH';

export interface ConnectorCapabilities {
  supportsSource: boolean;
  supportsTarget: boolean;
  supportsCdc: boolean;
  supportsBulk: boolean;
  supportsSchemaIntrospection: boolean;
  supportsValidationSampling: boolean;
  supportsStreaming: boolean;
}

export interface ConnectorDefinition {
  id: string;
  name: string;
  providerId: string;
  category: string;
  version: string;
  driverVersion: string;
  isBuiltIn: boolean;
  applicability: 'SOURCE_AND_TARGET' | 'SOURCE_ONLY' | 'TARGET_ONLY';
  capabilities: ConnectorCapabilities;
  supportedDialects: string[];
  certificationLevel: ConnectorCertificationLevel;
  qualificationNotes: string;
  lastTestedDate: string;
  engineProtocolVersion: string;
}

export interface ExternalConnectorRegistration {
  id: string;
  name: string;
  providerIdentifier: string;
  binaryPath: string;
  protocolVersion: string;
  registeredAt: string;
  sha256Checksum: string;
  certificationLevel: ConnectorCertificationLevel;
  status: 'ACTIVE' | 'DISABLED' | 'PENDING_VALIDATION';
}

export interface PluginDefinition {
  id: string;
  name: string;
  code: string;
  vendor: string;
  version: string;
  pluginType: PluginType;
  status: PluginStatus;
  signatureStatus: PluginSignatureStatus;
  sha256Digest: string;
  permissions: string[];
  description: string;
  installedAt: string;
}

export interface SdkConfiguration {
  sdkVersion: string;
  supportedRuntimes: string[];
  maxExecutionTimeoutSec: number;
  sandboxingEnforced: boolean;
  grpcSocketPath: string;
  wasmRuntimeEngine: string;
}
