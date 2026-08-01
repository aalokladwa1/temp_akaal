'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function ConnectDatabaseRedirect() {
  const router = useRouter();
  useEffect(() => {
    router?.replace('/databases');
  }, [router]);
  return null;
}
