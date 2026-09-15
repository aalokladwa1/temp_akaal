/**
 * AKAAL Administration — 5.11 Integrations & Notifications Service
 * Authoritative presentation service for Notification Channels, Notification Policies,
 * Event Routing, SIEM Integrations, ITSM Ticketing, and Integration Credential References.
 */

import { Injectable, signal } from '@angular/core';
import {
  NotificationChannel,
  NotificationPolicy,
  EventRoutingRule,
  SiemIntegration,
  ItsmIntegration,
  IntegrationCredentialRef
} from '../models/integrations.models';

@Injectable({
  providedIn: 'root'
})
export class IntegrationsService {
  // Notification Channels
  public channels = signal<NotificationChannel[]>([
    {
      id: 'chan-email-01',
      name: 'Enterprise SecOps Alert Mailing List',
      channelType: 'EMAIL_SMTP',
      targetEndpointOrAddress: 'secops-alerts@akaaltech.com',
      credentialRef: 'vault://secret/smtp/corporate-relay-creds',
      isEnabled: true,
      description: 'Dispatches high-severity platform security and authorization events to SecOps team.',
      createdAt: '2025-08-10'
    },
    {
      id: 'chan-slack-01',
      name: 'Migration Critical Incident Webhook',
      channelType: 'SLACK',
      targetEndpointOrAddress: 'https://hooks.slack.com/services/T00/B00/XXXX',
      credentialRef: 'vault://secret/slack/migration-webhook-token',
      isEnabled: true,
      description: 'Real-time alert dispatch to #migration-incidents Slack channel.',
      createdAt: '2025-09-12'
    },
    {
      id: 'chan-pagerduty-01',
      name: 'P1 Infrastructure On-Call Escalation Service',
      channelType: 'PAGERDUTY',
      targetEndpointOrAddress: 'events.pagerduty.com/v2/enqueue',
      credentialRef: 'vault://secret/pagerduty/routing-key-prod',
      isEnabled: true,
      description: 'Triggers automated on-call engineer paging for cluster and engine failures.',
      createdAt: '2025-10-01'
    }
  ]);

  // Notification Policies
  public policies = signal<NotificationPolicy[]>([
    {
      id: 'npol-01',
      name: 'Urgent Critical Security & Failure Broadcast',
      severityLevels: ['CRITICAL'],
      channelIds: ['chan-email-01', 'chan-pagerduty-01', 'chan-slack-01'],
      escalationDelayMinutes: 5,
      status: 'ACTIVE'
    },
    {
      id: 'npol-02',
      name: 'Standard Operational Health Warnings',
      severityLevels: ['HIGH', 'MEDIUM'],
      channelIds: ['chan-slack-01'],
      quietHoursStart: '22:00',
      quietHoursEnd: '06:00',
      status: 'ACTIVE'
    }
  ]);

  // Event Routing Rules
  public eventRoutingRules = signal<EventRoutingRule[]>([
    {
      id: 'erule-01',
      eventFamily: 'SECURITY',
      filterPattern: 'security.auth.* | security.kms.*',
      targetChannelIds: ['chan-email-01', 'chan-pagerduty-01'],
      description: 'Routes all authentication failures, key rotations, and break-glass overrides.',
      status: 'ENABLED'
    },
    {
      id: 'erule-02',
      eventFamily: 'MIGRATION',
      filterPattern: 'migration.pipeline.aborted | migration.cdc.lag_critical',
      targetChannelIds: ['chan-slack-01', 'chan-pagerduty-01'],
      description: 'Routes pipeline fatal halts and CDC replication buffer overflows.',
      status: 'ENABLED'
    },
    {
      id: 'erule-03',
      eventFamily: 'ADMINISTRATIVE',
      filterPattern: 'admin.organization.* | admin.user.role_assigned',
      targetChannelIds: ['chan-email-01'],
      description: 'Routes tenancy mutations and privileged role delegations.',
      status: 'ENABLED'
    }
  ]);

  // SIEM Integrations
  public siemIntegrations = signal<SiemIntegration[]>([
    {
      id: 'siem-01',
      name: 'Corporate Splunk Enterprise Cloud HEC',
      siemType: 'SPLUNK',
      endpointUrl: 'https://http-inputs-akaal.splunkcloud.com:8088/services/collector/raw',
      protocol: 'HTTPS_POST',
      credentialRef: 'vault://secret/siem/splunk-hec-token',
      status: 'CONFIGURED'
    },
    {
      id: 'siem-02',
      name: 'On-Prem Datadog Agent Syslog Forwarder',
      siemType: 'DATADOG',
      endpointUrl: 'datadog-intake.internal:10516',
      protocol: 'TLS_TCP',
      credentialRef: 'vault://secret/siem/datadog-api-key',
      status: 'CONFIGURED'
    }
  ]);

  // ITSM / Ticketing Integrations
  public itsmIntegrations = signal<ItsmIntegration[]>([
    {
      id: 'itsm-01',
      name: 'Enterprise ServiceNow Incident Management',
      provider: 'SERVICENOW',
      instanceUrl: 'https://akaalcorp.service-now.com',
      defaultProjectOrQueue: 'INC_DATA_PLATFORM',
      credentialRef: 'vault://secret/itsm/servicenow-oauth-client',
      issueTypeMapping: 'Incident (Urgency: High)',
      status: 'CONFIGURED'
    },
    {
      id: 'itsm-02',
      name: 'Jira Software Data Platform Support Project',
      provider: 'JIRA',
      instanceUrl: 'https://jira.corp.akaaltech.com',
      defaultProjectOrQueue: 'AKAAL_OPS',
      credentialRef: 'vault://secret/itsm/jira-pat-token',
      issueTypeMapping: 'Task / Bug',
      status: 'CONFIGURED'
    }
  ]);

  // Integration Credential References (Zero plaintext secrets)
  public credentialRefs = signal<IntegrationCredentialRef[]>([
    {
      id: 'cref-01',
      name: 'Splunk HEC Production Ingestion Token',
      providerType: 'SPLUNK_HEC',
      vaultUri: 'vault://secret/siem/splunk-hec-token',
      associatedIntegrationsCount: 2,
      lastRotatedAt: '2026-02-10',
      status: 'VALID'
    },
    {
      id: 'cref-02',
      name: 'ServiceNow OAuth2 Client Grant',
      providerType: 'SERVICENOW_OAUTH',
      vaultUri: 'vault://secret/itsm/servicenow-oauth-client',
      associatedIntegrationsCount: 1,
      lastRotatedAt: '2026-01-18',
      status: 'VALID'
    },
    {
      id: 'cref-03',
      name: 'PagerDuty Events API v2 Routing Key',
      providerType: 'PAGERDUTY_V2',
      vaultUri: 'vault://secret/pagerduty/routing-key-prod',
      associatedIntegrationsCount: 1,
      lastRotatedAt: '2026-02-01',
      status: 'VALID'
    }
  ]);

  public getChannelById(id: string): NotificationChannel | undefined {
    return this.channels().find(c => c.id === id);
  }

  public getPolicyById(id: string): NotificationPolicy | undefined {
    return this.policies().find(p => p.id === id);
  }

  public createChannel(channel: Omit<NotificationChannel, 'id' | 'createdAt'>): void {
    const newRecord: NotificationChannel = {
      ...channel,
      id: `chan-${Date.now()}`,
      createdAt: new Date().toISOString().split('T')[0]
    };
    this.channels.update(list => [newRecord, ...list]);
  }

  public createPolicy(policy: Omit<NotificationPolicy, 'id' | 'status'>): void {
    const newRecord: NotificationPolicy = {
      ...policy,
      id: `npol-${Date.now()}`,
      status: 'ACTIVE'
    };
    this.policies.update(list => [newRecord, ...list]);
  }

  public createEventRule(rule: Omit<EventRoutingRule, 'id' | 'status'>): void {
    const newRecord: EventRoutingRule = {
      ...rule,
      id: `erule-${Date.now()}`,
      status: 'ENABLED'
    };
    this.eventRoutingRules.update(list => [newRecord, ...list]);
  }

  public createSiemIntegration(siem: Omit<SiemIntegration, 'id' | 'status'>): void {
    const newRecord: SiemIntegration = {
      ...siem,
      id: `siem-${Date.now()}`,
      status: 'CONFIGURED'
    };
    this.siemIntegrations.update(list => [newRecord, ...list]);
  }

  public createItsmIntegration(itsm: Omit<ItsmIntegration, 'id' | 'status'>): void {
    const newRecord: ItsmIntegration = {
      ...itsm,
      id: `itsm-${Date.now()}`,
      status: 'CONFIGURED'
    };
    this.itsmIntegrations.update(list => [newRecord, ...list]);
  }
}
