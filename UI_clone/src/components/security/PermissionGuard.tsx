'use client';

import React from 'react';
import { PermissionEvaluator } from '@/security/authz/permissionEvaluator';
import { UserIdentity } from '@/security/types/security.types';

interface PermissionGuardProps {
  user: UserIdentity | null;
  resource: string;
  action: string;
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

export function PermissionGuard({
  user,
  resource,
  action,
  fallback = null,
  children,
}: PermissionGuardProps) {
  if (!user || !PermissionEvaluator.hasPermission(user, resource, action)) {
    return <>{fallback}</>;
  }
  return <>{children}</>;
}
