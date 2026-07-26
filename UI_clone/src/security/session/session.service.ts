import { SessionContext, UserIdentity } from '../types/security.types';
import { CryptoService } from '../crypto/crypto.service';
import { defaultSecurityConfig } from '../config/security.config';

export class SessionService {
  private static activeSessions = new Map<string, SessionContext>();

  public static createSession(
    user: UserIdentity,
    deviceInfo: { deviceId: string; userAgent: string; ipAddress: string }
  ): SessionContext {
    const sessionId = `sess_${CryptoService.generateSecureToken(24)}`;
    const now = new Date();
    const expires = new Date(now.getTime() + defaultSecurityConfig.session.idleTimeoutMinutes * 60 * 1000);

    const session: SessionContext = {
      sessionId,
      userId: user.id,
      email: user.email,
      tenantId: user.tenantId,
      organizationId: user.organizationId,
      deviceId: deviceInfo.deviceId,
      userAgent: deviceInfo.userAgent,
      ipAddress: deviceInfo.ipAddress,
      createdAt: now.toISOString(),
      lastActiveAt: now.toISOString(),
      expiresAt: expires.toISOString(),
      isRevoked: false,
    };

    // Enforce max active sessions per user
    const userSessions = Array.from(this.activeSessions.values()).filter(s => s.userId === user.id && !s.isRevoked);
    if (userSessions.length >= defaultSecurityConfig.session.maxActiveSessionsPerUser) {
      // Revoke oldest active session
      const oldest = userSessions.sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime())[0];
      if (oldest) {
        this.revokeSession(oldest.sessionId);
      }
    }

    this.activeSessions.set(sessionId, session);
    return session;
  }

  public static getSession(sessionId: string): SessionContext | null {
    const session = this.activeSessions.get(sessionId);
    if (!session || session.isRevoked) return null;

    // Check sliding expiration
    if (new Date(session.expiresAt).getTime() < Date.now()) {
      session.isRevoked = true;
      return null;
    }

    // Refresh sliding expiration
    const now = new Date();
    session.lastActiveAt = now.toISOString();
    session.expiresAt = new Date(now.getTime() + defaultSecurityConfig.session.idleTimeoutMinutes * 60 * 1000).toISOString();

    return session;
  }

  public static getUserSessions(userId: string): SessionContext[] {
    return Array.from(this.activeSessions.values()).filter(s => s.userId === userId && !s.isRevoked);
  }

  public static revokeSession(sessionId: string): void {
    const session = this.activeSessions.get(sessionId);
    if (session) {
      session.isRevoked = true;
    }
  }

  public static revokeAllUserSessions(userId: string): void {
    for (const session of this.activeSessions.values()) {
      if (session.userId === userId) {
        session.isRevoked = true;
      }
    }
  }
}
