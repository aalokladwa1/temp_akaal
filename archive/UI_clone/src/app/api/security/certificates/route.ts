import { NextResponse } from 'next/server';
import { CertificateManager } from '@/security/certificates/certificateManager';

export async function GET() {
  try {
    const certs = CertificateManager.list();
    return NextResponse.json({ success: true, count: certs.length, certificates: certs });
  } catch (err: any) {
    return NextResponse.json({ success: false, error: err.message }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const cert = await CertificateManager.importCert(body, 'api_user');
    return NextResponse.json({ success: true, certificate: cert }, { status: 201 });
  } catch (err: any) {
    return NextResponse.json({ success: false, error: err.message }, { status: 400 });
  }
}

export async function PUT(request: Request) {
  try {
    const body = await request.json();
    const { action, id, reason } = body;

    if (action === 'renew') {
      const cert = CertificateManager.renew(id, 'api_user');
      return NextResponse.json({ success: true, certificate: cert });
    }

    if (action === 'revoke') {
      const cert = CertificateManager.revoke(id, reason || 'API Revocation', 'api_user');
      return NextResponse.json({ success: true, certificate: cert });
    }

    return NextResponse.json({ success: false, error: 'Invalid action' }, { status: 400 });
  } catch (err: any) {
    return NextResponse.json({ success: false, error: err.message }, { status: 400 });
  }
}
