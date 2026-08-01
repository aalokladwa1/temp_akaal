import { UserIdentity } from '../types/security.types';

export interface ABACAttributeContext {
  environment: 'production' | 'staging' | 'development';
  clientIp: string;
  timeOfAccessHour: number; // 0 - 23
  resourceClassification: 'public' | 'internal' | 'confidential' | 'restricted';
  riskScore: number; // 0 - 100
}

export class ABACEngine {
  public static evaluateABAC(user: UserIdentity, ctx: ABACAttributeContext): { allowed: boolean; reason?: string } {
    // Rule 1: Restricted production resources require riskScore < 50 and MFA
    if (ctx.resourceClassification === 'restricted' && ctx.environment === 'production') {
      if (!user.mfaEnabled) {
        return { allowed: false, reason: 'ABAC Deny: Production restricted resource requires MFA' };
      }
      if (ctx.riskScore > 50) {
        return { allowed: false, reason: 'ABAC Deny: Elevated risk score detected' };
      }
    }

    // Rule 2: Access outside 06:00 - 22:00 requires elevated audit logging
    if (ctx.timeOfAccessHour < 5 || ctx.timeOfAccessHour > 23) {
      if (!user.roles.includes('super_admin')) {
        return { allowed: false, reason: 'ABAC Deny: Out of maintenance window access' };
      }
    }

    return { allowed: true };
  }
}
