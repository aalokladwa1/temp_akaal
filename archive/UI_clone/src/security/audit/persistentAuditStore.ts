import { AuditEvent } from '../types/security.types';
import { CryptoService } from '../crypto/crypto.service';

export class PersistentAuditStore {
  private static STORAGE_KEY = 'akaal_persistent_audit_trail';

  public static append(event: Omit<AuditEvent, 'id' | 'timestamp'>): AuditEvent {
    const fullEvent: AuditEvent = {
      ...event,
      id: `audit_${CryptoService.generateSecureToken(16)}`,
      timestamp: new Date().toISOString(),
    };

    if (typeof window !== 'undefined') {
      try {
        const existing = this.getAuditEvents();
        const updated = [fullEvent, ...existing];
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(updated));
      } catch {
        // Fallback silently if storage unavailable
      }
    }
    return fullEvent;
  }

  public static getAuditEvents(): AuditEvent[] {
    if (typeof window === 'undefined') return [];
    try {
      const data = localStorage.getItem(this.STORAGE_KEY);
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  }

  public static exportToCSV(): string {
    const events = this.getAuditEvents();
    const headers = ['ID', 'Timestamp', 'EventType', 'UserEmail', 'TenantID', 'IPAddress', 'Resource', 'Action', 'Status'];
    const rows = events.map(e => [
      e.id,
      e.timestamp,
      e.eventType,
      e.userEmail,
      e.tenantId,
      e.ipAddress,
      e.resource,
      e.action,
      e.status,
    ]);

    return [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  }
}
