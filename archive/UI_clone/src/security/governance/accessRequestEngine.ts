import { CryptoService } from '../crypto/crypto.service';

export interface AccessRequest {
  id: string;
  requesterEmail: string;
  targetRole: string;
  resource: string;
  justification: string;
  status: 'pending' | 'approved' | 'rejected' | 'expired';
  requestedAt: string;
  approverEmail?: string;
}

export class AccessRequestEngine {
  private static requests: AccessRequest[] = [
    {
      id: 'req_84920',
      requesterEmail: 'david.miller@acme.com',
      targetRole: 'migration_operator',
      resource: 'prj_mig_oracle',
      justification: 'Required for Oracle 19c to PostgreSQL 16 cutover execution window',
      status: 'pending',
      requestedAt: new Date().toISOString(),
    },
  ];

  public static createRequest(requesterEmail: string, targetRole: string, resource: string, justification: string): AccessRequest {
    const req: AccessRequest = {
      id: `req_${CryptoService.generateSecureToken(12)}`,
      requesterEmail,
      targetRole,
      resource,
      justification,
      status: 'pending',
      requestedAt: new Date().toISOString(),
    };
    this.requests.unshift(req);
    return req;
  }

  public static processRequest(requestId: string, status: 'approved' | 'rejected', approverEmail: string): boolean {
    const req = this.requests.find(r => r.id === requestId);
    if (!req || req.status !== 'pending') return false;
    req.status = status;
    req.approverEmail = approverEmail;
    return true;
  }

  public static getRequests(): readonly AccessRequest[] {
    return this.requests;
  }
}
