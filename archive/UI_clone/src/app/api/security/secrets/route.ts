import { NextResponse } from 'next/server';
import { SecretManager } from '@/security/secrets/secretManager';
import { SecretRotationEngine } from '@/security/secrets/secretRotationEngine';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const type = searchParams.get('type') as any;
    const status = searchParams.get('status') as any;
    const provider = searchParams.get('provider') as any;
    const search = searchParams.get('search') ?? undefined;

    const secrets = SecretManager.list({ type, status, provider, search });
    return NextResponse.json({ success: true, count: secrets.length, secrets });
  } catch (err: any) {
    return NextResponse.json({ success: false, error: err.message }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const record = await SecretManager.create(body, 'api_user');
    return NextResponse.json({ success: true, secret: record }, { status: 201 });
  } catch (err: any) {
    return NextResponse.json({ success: false, error: err.message }, { status: 400 });
  }
}

export async function PUT(request: Request) {
  try {
    const body = await request.json();
    const { action, id, newValue, requestedBy } = body;

    if (action === 'rotate') {
      const rotation = await SecretRotationEngine.rotateManual(id, newValue, requestedBy || 'api_user');
      return NextResponse.json({ success: true, rotation });
    }

    if (action === 'emergency_rotate') {
      const rotation = await SecretRotationEngine.rotateEmergency(id, newValue, requestedBy || 'api_user');
      return NextResponse.json({ success: true, rotation });
    }

    const updated = SecretManager.update(body, requestedBy || 'api_user');
    return NextResponse.json({ success: true, secret: updated });
  } catch (err: any) {
    return NextResponse.json({ success: false, error: err.message }, { status: 400 });
  }
}
