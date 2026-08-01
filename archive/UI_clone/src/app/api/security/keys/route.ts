import { NextResponse } from 'next/server';
import { KeyManagementService } from '@/security/keys/keyManagementService';

export async function GET() {
  try {
    const keys = KeyManagementService.list();
    return NextResponse.json({ success: true, count: keys.length, keys });
  } catch (err: any) {
    return NextResponse.json({ success: false, error: err.message }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const key = await KeyManagementService.create(body, 'api_user');
    return NextResponse.json({ success: true, key }, { status: 201 });
  } catch (err: any) {
    return NextResponse.json({ success: false, error: err.message }, { status: 400 });
  }
}

export async function PUT(request: Request) {
  try {
    const body = await request.json();
    const { action, id, reason } = body;

    if (action === 'rotate') {
      const result = await KeyManagementService.rotate(id, 'api_user');
      return NextResponse.json({ success: true, result });
    }

    if (action === 'revoke') {
      const result = KeyManagementService.revoke(id, reason || 'API Revocation', 'api_user');
      return NextResponse.json({ success: true, result });
    }

    return NextResponse.json({ success: false, error: 'Invalid action' }, { status: 400 });
  } catch (err: any) {
    return NextResponse.json({ success: false, error: err.message }, { status: 400 });
  }
}
