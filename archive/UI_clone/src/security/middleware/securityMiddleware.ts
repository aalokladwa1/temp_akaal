import { SessionService } from '../session/session.service';
import { PermissionEvaluator } from '../authz/permissionEvaluator';
import { UserIdentity } from '../types/security.types';

export interface MiddlewareResult {
  allowed: boolean;
  reason?: string;
  statusCode: number;
}

export class SecurityMiddleware {
  public static validateSession(sessionId: string): MiddlewareResult {
    const session = SessionService.getSession(sessionId);
    if (!session) {
      return { allowed: false, reason: 'Session expired or revoked', statusCode: 401 };
    }
    return { allowed: true, statusCode: 200 };
  }

  public static authorizeRequest(user: UserIdentity, resource: string, action: string): MiddlewareResult {
    const hasAccess = PermissionEvaluator.hasPermission(user, resource, action);
    if (!hasAccess) {
      return { allowed: false, reason: `Insufficient permissions for ${action} on ${resource}`, statusCode: 403 };
    }
    return { allowed: true, statusCode: 200 };
  }
}
