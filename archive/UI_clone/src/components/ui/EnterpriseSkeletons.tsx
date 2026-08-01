'use client';

import React from 'react';

export function SkeletonBlock({
  width = '100%',
  height = '16px',
  className = '',
  style = {},
}: {
  width?: string;
  height?: string;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <div
      className={`rounded animate-pulse ${className}`}
      style={{
        width,
        height,
        background: 'linear-gradient(90deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.03) 100%)',
        backgroundSize: '200% 100%',
        ...style,
      }}
    />
  );
}

export function TableSkeleton({ rows = 5, cols = 6 }: { rows?: number; cols?: number }) {
  return (
    <div className="w-full space-y-3 p-4">
      {/* Table Header Skeleton */}
      <div className="flex items-center gap-4 py-2 border-b" style={{ borderColor: 'var(--akaal-border, #2A3647)' }}>
        {Array.from({ length: cols }).map((_, i) => (
          <SkeletonBlock key={i} width={`${100 / cols}%`} height="12px" />
        ))}
      </div>
      {/* Table Rows Skeleton */}
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex items-center gap-4 py-2.5">
          {Array.from({ length: cols }).map((_, c) => (
            <SkeletonBlock key={c} width={`${100 / cols}%`} height="14px" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function CardSkeleton() {
  return (
    <div
      className="p-4 rounded-lg space-y-3"
      style={{ background: 'var(--akaal-card-bg, #1A2333)', border: '1px solid var(--akaal-card-border, #2A3647)' }}
    >
      <div className="flex items-center justify-between">
        <SkeletonBlock width="32px" height="32px" className="rounded-lg" />
        <SkeletonBlock width="40px" height="12px" />
      </div>
      <SkeletonBlock width="60%" height="24px" />
      <SkeletonBlock width="80%" height="12px" />
    </div>
  );
}

export function InspectorDrawerSkeleton() {
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <SkeletonBlock width="180px" height="20px" />
          <SkeletonBlock width="120px" height="12px" />
        </div>
        <SkeletonBlock width="60px" height="22px" className="rounded-full" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="p-3 rounded space-y-1.5" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid #2A3647' }}>
            <SkeletonBlock width="60px" height="10px" />
            <SkeletonBlock width="100px" height="14px" />
          </div>
        ))}
      </div>
      <div className="space-y-2">
        <SkeletonBlock width="100px" height="14px" />
        <SkeletonBlock width="100%" height="80px" />
      </div>
    </div>
  );
}
