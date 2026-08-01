'use client';
import React, { useEffect, useRef, useState } from 'react';

const PHASES = [
  {
    id: 'audit',
    label: '01 // Audit',
    title: 'Dependency Audit',
    color: 'var(--phosphor)',
    colorDim: 'var(--phosphor-dim)',
    tasks: ['Scan ng update output', 'Map deprecated APIs', 'Flag lazy route syntax', 'Check peer dependencies'],
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
      </svg>
    ),
  },
  {
    id: 'compat',
    label: '02 // Compat',
    title: 'Compatibility Layer',
    color: 'var(--plasma)',
    colorDim: 'var(--plasma-dim)',
    tasks: ['Install bridge packages', 'Add compatibility shims', 'Test existing tests', 'Patch RxJS operators'],
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M18 20V10M12 20V4M6 20v-6"/>
      </svg>
    ),
  },
  {
    id: 'refactor',
    label: '03 // Refactor',
    title: 'Module Refactor',
    color: 'var(--plasma)',
    colorDim: 'var(--plasma-dim)',
    tasks: ['Convert NgModules → standalone', 'Migrate lazy routes', 'Adopt new inject() API', 'Update template syntax'],
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
      </svg>
    ),
  },
  {
    id: 'validate',
    label: '04 // Validate',
    title: 'CI Validation',
    color: 'var(--phosphor)',
    colorDim: 'var(--phosphor-dim)',
    tasks: ['Run full test suite', 'Lighthouse performance check', 'Bundle size comparison', 'Deploy to staging'],
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/>
      </svg>
    ),
  },
];

export default function PipelineSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const [visible, setVisible] = useState(false);
  const [activePhase, setActivePhase] = useState(0);

  useEffect(() => {
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { setVisible(true); obs.disconnect(); }
    }, { threshold: 0.2 });
    if (sectionRef?.current) obs?.observe(sectionRef?.current);
    return () => obs?.disconnect();
  }, []);

  useEffect(() => {
    if (!visible) return;
    const interval = setInterval(() => {
      setActivePhase(p => (p + 1) % PHASES?.length);
    }, 2200);
    return () => clearInterval(interval);
  }, [visible]);

  return (
    <section ref={sectionRef} className="relative py-28 overflow-hidden" style={{ borderTop: '1px solid var(--border)' }}>
      {/* Background accent */}
      <div className="absolute inset-0 pointer-events-none"
        style={{ background: 'radial-gradient(ellipse 60% 40% at 50% 50%, rgba(57,255,20,0.02) 0%, transparent 70%)' }} />
      <div className="max-w-7xl mx-auto px-6">
        {/* Header */}
        <div className={`reveal ${visible ? 'visible' : ''} mb-16`}>
          <span className="font-mono text-xs tracking-widest uppercase mb-3 block" style={{ color: 'var(--phosphor)' }}>
            01 // Methodology
          </span>
          <h2 className="font-sans font-bold tracking-tight" style={{ fontSize: 'clamp(1.8rem, 4vw, 3rem)' }}>
            Four phases. Zero guesswork.
          </h2>
          <p className="mt-3 text-fg-muted text-base max-w-lg leading-relaxed">
            Every Angular migration follows the same battle-tested pipeline. No surprises, no "we'll figure it out" moments.
          </p>
        </div>

        {/* Pipeline visual */}
        <div className="relative">
          {/* Connector line */}
          <div className="hidden md:block absolute top-[52px] left-0 right-0 h-px" style={{ background: 'var(--border-bright)' }}>
            <div className="pipeline-connector absolute inset-0" />
          </div>

          <div className={`grid grid-cols-1 md:grid-cols-4 gap-4 stagger ${visible ? '' : ''}`}>
            {PHASES?.map((phase, i) => (
              <div
                key={phase?.id}
                className={`reveal card-hover rounded-lg p-5 cursor-pointer transition-all duration-500 ${visible ? 'visible' : ''}`}
                style={{
                  transitionDelay: `${i * 0.1}s`,
                  background: activePhase === i ? 'var(--surface-2)' : 'var(--surface)',
                  border: `1px solid ${activePhase === i ? phase?.color : 'var(--border)'}`,
                  boxShadow: activePhase === i ? `0 0 20px rgba(${phase?.color === 'var(--phosphor)' ? '57,255,20' : '255,230,0'},0.08)` : 'none',
                }}
                onClick={() => setActivePhase(i)}
              >
                {/* Phase icon */}
                <div className="w-10 h-10 rounded-lg flex items-center justify-center mb-4 relative z-10"
                  style={{
                    background: activePhase === i ? phase?.colorDim : 'rgba(255,255,255,0.04)',
                    border: `1px solid ${activePhase === i ? phase?.color : 'var(--border)'}`,
                    color: activePhase === i ? phase?.color : 'var(--fg-muted)',
                  }}>
                  {phase?.icon}
                </div>

                <div className="font-mono text-xs mb-1" style={{ color: 'var(--fg-muted)' }}>{phase?.label}</div>
                <h3 className="font-sans font-semibold text-base mb-3" style={{ color: activePhase === i ? phase?.color : 'var(--fg)' }}>
                  {phase?.title}
                </h3>

                <ul className="space-y-1.5">
                  {phase?.tasks?.map((task, j) => (
                    <li key={j} className="flex items-center gap-2 font-mono text-xs" style={{ color: 'var(--fg-muted)' }}>
                      <span className="w-1 h-1 rounded-full flex-shrink-0"
                        style={{ background: activePhase === i ? phase?.color : 'var(--fg-dim)' }} />
                      {task}
                    </li>
                  ))}
                </ul>

                {/* Active indicator */}
                {activePhase === i && (
                  <div className="mt-4 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full animate-pulse-dot" style={{ background: phase?.color }} />
                    <span className="font-mono text-xs" style={{ color: phase?.color }}>RUNNING</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Data flow visual below */}
        <div className={`reveal mt-10 rounded-lg p-4 ${visible ? 'visible' : ''}`}
          style={{ background: 'var(--surface)', border: '1px solid var(--border)', transitionDelay: '0.4s' }}>
          <div className="flex items-center gap-2 mb-3">
            <span className="w-1.5 h-1.5 rounded-full animate-pulse-dot" style={{ background: 'var(--phosphor)' }} />
            <span className="font-mono text-xs" style={{ color: 'var(--phosphor)' }}>ng migrate --dry-run --verbose</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {[
              { label: 'Files scanned', value: '2,847', color: 'var(--fg)' },
              { label: 'Breaking changes', value: '34 found', color: 'var(--signal)' },
              { label: 'Auto-fixable', value: '28 (82%)', color: 'var(--phosphor)' },
            ]?.map(stat => (
              <div key={stat?.label} className="rounded p-3" style={{ background: 'var(--void)', border: '1px solid var(--border)' }}>
                <div className="font-mono text-xs text-fg-muted mb-1">{stat?.label}</div>
                <div className="font-mono font-bold text-lg" style={{ color: stat?.color }}>{stat?.value}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}