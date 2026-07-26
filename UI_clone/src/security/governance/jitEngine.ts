import { CryptoService } from '../crypto/crypto.service';

export interface JITElevationRequest {
  id: string;
  userId: string;
  requestedRole: string;
  durationMinutes: number;
  reason: string;
  status: 'pending' | 'approved' | 'expired' | 'revoked';
  expiresAt: string;
}

export class JITEngine {
  private static requests = new Map<string, JITElevationRequest>();

  public static requestElevation(userId: string, requestedRole: string, durationMinutes: number, reason: string): JITElevationRequest {
    const id = `jit_${CryptoService.generateSecureToken(16)}`;
    const expiresAt = new Date(Date.now() + durationMinutes * 60 * 1000).toISOString();

    const req: JITElevationRequest = {
      id,
      userId,
      requestedRole,
      durationMinutes,
      reason,
      status: 'pending',
      expiresAt,
    };

    this.requests.set(id, req);
    return req;
  }

  public static approveElevation(requestId: string): boolean {
    const req = this.requests.get(requestId);
    if (!req || req.status !== 'pending') return false;
    req.status = 'approved';
    return true;
  }

  public static getActiveElevations(userId: string): JITElevationRequest[] {
    const now = Date.now();
    return Array.from(this.requests.values()).filter(
      r => r.userId === userId && r.status === 'approved' && new Date(r.expiresAt).getTime() > now
    );
  }
}
