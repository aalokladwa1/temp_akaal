'use client';
import React, { useEffect, useState } from 'react';
import AppLogo from '@/components/ui/AppLogo';

export default function Header() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 80);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <>
      {/* Main nav */}
      <nav
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          scrolled ? 'opacity-0 pointer-events-none' : 'opacity-100'
        }`}
        style={{ background: 'rgba(11,13,15,0.7)', backdropFilter: 'blur(16px)', borderBottom: '1px solid rgba(255,255,255,0.04)' }}
      >
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <AppLogo size={28} text="Migrate" />
          <div className="hidden md:flex items-center gap-8">
            {['Methodology','Case Studies','Pricing','Docs']?.map(item => (
              <a key={item} href="#" className="font-mono text-xs text-fg-muted hover:text-fg transition-colors tracking-widest uppercase">
                {item}
              </a>
            ))}
          </div>
          <a
            href="#audit"
            className="font-mono text-xs font-bold uppercase tracking-widest px-5 py-2.5 rounded border transition-all duration-200"
            style={{ background: 'var(--phosphor)', color: 'var(--void)', border: '1px solid var(--phosphor)', boxShadow: '0 0 15px rgba(57,255,20,0.3)' }}
          >
            Audit My Project
          </a>
        </div>
      </nav>
      {/* Mini compressed bar */}
      <div
        className={`mini-bar fixed top-0 left-0 right-0 z-50 ${scrolled ? 'visible' : ''}`}
        style={{ background: 'rgba(11,13,15,0.95)', backdropFilter: 'blur(20px)', borderBottom: '1px solid rgba(57,255,20,0.1)' }}
      >
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="w-2 h-2 rounded-full animate-pulse-dot" style={{ background: 'var(--phosphor)', boxShadow: '0 0 6px var(--phosphor)' }} />
            <span className="font-mono text-xs" style={{ color: 'var(--phosphor)' }}>migrate</span>
            <span className="font-mono text-xs text-fg-muted ml-2 hidden md:inline">Angular 14 → 17 migration in progress...</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="hidden md:flex items-center gap-2">
              <div className="progress-track w-32"><div className="progress-fill" style={{ width: '67%' }} /></div>
              <span className="font-mono text-xs text-fg-muted">67%</span>
            </div>
            <a
              href="#audit"
              className="font-mono text-xs font-bold uppercase tracking-wider px-4 py-2 rounded transition-all"
              style={{ background: 'var(--phosphor)', color: 'var(--void)' }}
            >
              Audit
            </a>
          </div>
        </div>
      </div>
    </>
  );
}