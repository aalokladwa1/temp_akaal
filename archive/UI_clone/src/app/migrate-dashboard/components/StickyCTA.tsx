'use client';
import React, { useEffect, useState } from 'react';

export default function StickyCTA() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > window.innerHeight * 0.8);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <div
      className={`sticky-cta fixed bottom-0 left-0 right-0 z-50 ${visible ? 'visible' : ''}`}
      style={{
        background: 'rgba(11,13,15,0.96)',
        backdropFilter: 'blur(20px)',
        borderTop: '1px solid rgba(57,255,20,0.15)',
        boxShadow: '0 -8px 40px rgba(57,255,20,0.08)',
      }}
    >
      <div className="max-w-7xl mx-auto px-6 py-3 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="w-2 h-2 rounded-full animate-pulse-dot" style={{ background: 'var(--signal)' }} />
          <span className="font-mono text-xs text-fg-muted">
            <span style={{ color: 'var(--signal)' }}>34 breaking changes</span> detected in your Angular 14 project. Ready to fix them?
          </span>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          <a href="#checklist"
            className="font-mono text-xs text-fg-muted hover:text-fg transition-colors whitespace-nowrap">
            Download Checklist
          </a>
          <a href="#audit"
            className="font-mono text-xs font-bold uppercase tracking-widest px-5 py-2.5 rounded transition-all whitespace-nowrap"
            style={{ background: 'var(--phosphor)', color: 'var(--void)', boxShadow: '0 0 15px rgba(57,255,20,0.3)' }}>
            Audit My Project →
          </a>
        </div>
      </div>
    </div>
  );
}