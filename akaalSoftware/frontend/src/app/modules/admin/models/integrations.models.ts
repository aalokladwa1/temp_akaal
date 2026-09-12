/**
 * AKAAL Administration — 5.11 Integrations & Notifications Models
 * Models for Notification Channels, Notification Policies, Event Routing,
 * SIEM Integrations, ITSM / Ticketing, and Integration Credential References.
 */

export type ChannelType = 'EMAIL_SMTP' | 'WEBHOOK' | 'SLACK' | 'TEAMS' | 'PAGERDUTY';

export interface NotificationChannel {
  id: string;
  name: string;
  channelType: ChannelType;
  targetEndpointOrAddress: string;
  credentialRef?: string;
  isEnabled: boolean;
  description: string;
  createdAt: string;
}

export interface NotificationPolicy {
  id: string;
  name: string;
  severityLevels: ('CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW')[];
  channelIds: string[];
  quietHoursStart?: string;
  quietHoursEnd?: string;
  escalationDelayMinutes?: number;
  status: 'ACTIVE' | 'PAUSED';
}

export interface EventRoutingRule {
  id: string;
  eventFamily: 'ADMINISTRATIVE' | 'SECURITY' | 'GOVERNANCE' | 'MIGRATION' | 'MONITORING';
  filterPattern: string;
  targetChannelIds: string[];
  description: string;
  status: 'ENABLED' | 'DISABLED';
}

export interface SiemIntegration {
  id: string;
  name: string;
  siemType: 'SPLUNK' | 'DATADOG' | 'GENERIC_SYSLOG' | 'ELASTICSEARCH';
  endpointUrl: string;
  protocol: 'TLS_TCP' | 'HTTPS_POST';
  credentialRef?: string;
  status: 'CONFIGURED' | 'DISABLED';
}

export interface ItsmIntegration {
  id: string;
  name: string;
  provider: 'SERVICENOW' | 'JIRA';
  instanceUrl: string;
  defaultProjectOrQueue: string;
  credentialRef: string;
  issueTypeMapping: string;
  status: 'CONFIGURED' | 'DISABLED';
}

export interface IntegrationCredentialRef {
  id: string;
  name: string;
  providerType: string;
  vaultUri: string;
  associatedIntegrationsCount: number;
  lastRotatedAt: string;
  status: 'VALID' | 'ROTATION_REQUIRED';
}
