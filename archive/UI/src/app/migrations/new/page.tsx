'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function NewMigrationRedirect() {
  const router = useRouter();
  useEffect(() => {
    router?.replace('/migration-workspace');
  }, [router]);
  return null;
}
