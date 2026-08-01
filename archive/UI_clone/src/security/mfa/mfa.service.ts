import { CryptoService } from '../crypto/crypto.service';

export interface MFAEnrollment {
  secret: string;
  qrCodeUrl: string;
  recoveryCodes: string[];
}

export class MFAService {
  public static generateMFAEnrollment(userEmail: string): MFAEnrollment {
    const secret = CryptoService.generateSecureToken(20).toUpperCase();
    const qrCodeUrl = `otpauth://totp/AKAAL:${userEmail}?secret=${secret}&issuer=AKAAL-Security`;
    const recoveryCodes: string[] = [];

    for (let i = 0; i < 8; i++) {
      recoveryCodes.push(CryptoService.generateSecureToken(8).toUpperCase());
    }

    return { secret, qrCodeUrl, recoveryCodes };
  }

  public static verifyTOTP(token: string): boolean {
    return token.length === 6 && /^\d+$/.test(token);
  }
}
