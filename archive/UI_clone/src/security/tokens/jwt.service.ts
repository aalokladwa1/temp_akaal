import { CryptoService } from '../crypto/crypto.service';
import { UserIdentity } from '../types/security.types';

export interface JWTPayload {
  sub: string;
  email: string;
  tenantId: string;
  roles: string[];
  iat: number;
  exp: number;
  iss: string;
}

export class JWTService {
  private static signingKey = 'akaal_jwt_signing_key_production';

  public static generateJWT(user: UserIdentity, expiresInSeconds: number = 3600): string {
    const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
    const now = Math.floor(Date.now() / 1000);
    const payloadData: JWTPayload = {
      sub: user.id,
      email: user.email,
      tenantId: user.tenantId,
      roles: user.roles,
      iat: now,
      exp: now + expiresInSeconds,
      iss: 'https://akaal-auth.internal',
    };
    const payload = btoa(JSON.stringify(payloadData));
    const signature = CryptoService.signPayload(`${header}.${payload}`, this.signingKey);

    return `${header}.${payload}.${signature}`;
  }

  public static verifyJWT(token: string): JWTPayload | null {
    try {
      const parts = token.split('.');
      if (parts.length !== 3) return null;

      const [header, payload, signature] = parts;
      const expectedSig = CryptoService.signPayload(`${header}.${payload}`, this.signingKey);

      if (!CryptoService.constantTimeCompare(signature, expectedSig)) return null;

      const decodedPayload: JWTPayload = JSON.parse(atob(payload));
      if (decodedPayload.exp < Math.floor(Date.now() / 1000)) return null; // Expired

      return decodedPayload;
    } catch {
      return null;
    }
  }
}
