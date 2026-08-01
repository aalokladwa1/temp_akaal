import { SecurityContextState, UserIdentity, SessionContext } from '../types/security.types';
import { CryptoService } from '../crypto/crypto.service';

export class SecurityContext {
  private static currentContext: SecurityContextState | null = null;

  public static initialize(user: UserIdentity, session: SessionContext): SecurityContextState {
    const context: SecurityContextState = {
      user,
      session,
      correlationId: `corr_${CryptoService.generateSecureToken(16)}`,
      auditId: `audit_${CryptoService.generateSecureToken(16)}`,
      permissions: new Set(user.roles),
    };
    this.currentContext = context;
    return context;
  }

  public static getContext(): SecurityContextState | null {
    return this.currentContext;
  }

  public static clear(): void {
    this.currentContext = null;
  }
}
