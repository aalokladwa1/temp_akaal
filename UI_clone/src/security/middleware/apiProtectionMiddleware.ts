import { UserIdentity } from '../types/security.types';
import { SessionService } from '../session/session.service';
import { PermissionEvaluator } from '../authz/permissionEvaluator';
import { PersistentAuditStore } from '../audit/persistentAuditStore';

export interface ProtectedApiContext {
  user: UserIdentity;
  sessionId: string;
  tenantId: string;
  resource: string;
  action: string;
}

export class ApiProtectionMiddleware {
  public static validateApiRequest(ctx: ProtectedApiContext): { allowed: boolean; statusCode: number; error?: string } {
    // 1. Session check
    const session = SessionService.getSession(ctx.sessionId);
    if (!session || session.isRevoked) {
      PersistentAuditStore.append({
        eventType: 'AUTH_FAILURE',
        userId: ctx.user.id,
        userEmail: ctx.user.email,
        tenantId: ctx.tenantId,
        ipAddress: '127.0.0.1',
        userAgent: 'API-Client',
        resource: ctx.resource,
        action: ctx.action,
        status: 'FAILURE',
        details: { reason: 'Invalid or revoked session' },
      });
      return { allowed: false, statusCode: 401, error: 'Unauthorized: Invalid or expired session' };
    }

    // 2. Permission check
    const hasPerm = PermissionEvaluator.hasPermission(ctx.user, ctx.resource, ctx.action);
    if (!hasPerm) {
      PersistentAuditStore.append({
        eventType: 'PERMISSION_DENIED',
        userId: ctx.user.id,
        userEmail: ctx.user.email,
        tenantId: ctx.tenantId,
        ipAddress: '127.0.0.1',
        userAgent: 'API-Client',
        resource: ctx.resource,
        action: ctx.action,
        status: 'FAILURE',
        details: { reason: 'Forbidden: Insufficient RBAC privileges' },
      });
      return { allowed: false, statusCode: 403, error: 'Forbidden: Insufficient RBAC privileges' };
    }

    return { allowed: true, statusCode: 200 };
  }
}
