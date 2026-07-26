import { CryptoService } from '../crypto/crypto.service';

export interface SecureCookieOptions {
  httpOnly: boolean;
  secure: boolean;
  sameSite: 'Strict' | 'Lax' | 'None';
  path: string;
  maxAge: number;
}

export class CookieService {
  public static defaultOptions: SecureCookieOptions = {
    httpOnly: true,
    secure: true,
    sameSite: 'Strict',
    path: '/',
    maxAge: 86400,
  };

  public static generateCSRFToken(): string {
    return `csrf_${CryptoService.generateSecureToken(24)}`;
  }

  public static validateCSRFToken(clientToken: string, serverToken: string): boolean {
    return CryptoService.constantTimeCompare(clientToken, serverToken);
  }
}
