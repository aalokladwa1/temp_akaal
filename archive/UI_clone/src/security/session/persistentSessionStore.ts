import { SessionContext } from '../types/security.types';

export class PersistentSessionStore {
  private static STORAGE_KEY = 'akaal_persistent_sessions_v1';

  public static saveSession(session: SessionContext): void {
    if (typeof window === 'undefined') return;
    try {
      const existing = this.getAllSessions();
      const updated = [session, ...existing.filter(s => s.sessionId !== session.sessionId)];
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(updated));
    } catch {
      // Storage unavailable
    }
  }

  public static getAllSessions(): SessionContext[] {
    if (typeof window === 'undefined') return [];
    try {
      const data = localStorage.getItem(this.STORAGE_KEY);
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  }

  public static removeSession(sessionId: string): void {
    if (typeof window === 'undefined') return;
    try {
      const existing = this.getAllSessions();
      const filtered = existing.filter(s => s.sessionId !== sessionId);
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(filtered));
    } catch {
      // Storage error
    }
  }

  public static removeAllUserSessions(userId: string): void {
    if (typeof window === 'undefined') return;
    try {
      const existing = this.getAllSessions();
      const filtered = existing.filter(s => s.userId !== userId);
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(filtered));
    } catch {
      // Storage error
    }
  }
}
