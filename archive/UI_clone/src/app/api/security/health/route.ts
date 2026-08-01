import { NextResponse } from 'next/server';
import { SecretHealthMonitor } from '@/security/health/secretHealthMonitor';

export async function GET() {
  try {
    const health = await SecretHealthMonitor.getAggregateHealth();
    return NextResponse.json({ success: true, health });
  } catch (err: any) {
    return NextResponse.json({ success: false, error: err.message }, { status: 500 });
  }
}
