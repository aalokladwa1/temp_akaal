import { AuditEvent } from '../types/security.types';
import { CryptoService } from '../crypto/crypto.service';

export class AuditPipeline {
  private static auditLogs: AuditEvent[] = [];

  public static log(event: Omit<AuditEvent, 'id' | 'timestamp'>): AuditEvent {
    const fullEvent: AuditEvent = {
      ...event,
      id: `evt_${CryptoService.generateSecureToken(16)}`,
      timestamp: new Date().toISOString(),
    };

    // Immutable append-only record
    Object.freeze(fullEvent);
    this.auditLogs.push(fullEvent);
    return fullEvent;
  }

  public static getEvents(): readonly AuditEvent[] {
    return Object.freeze([...this.auditLogs]);
  }
}
