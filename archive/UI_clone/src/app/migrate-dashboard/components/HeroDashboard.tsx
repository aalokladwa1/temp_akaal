'use client';
import React, { useEffect, useRef, useState } from 'react';

const MODULES = [
  { name: 'AppModule', from: '14', to: '17', status: 'done', issues: 0 },
  { name: 'SharedModule', from: '14', to: '17', status: 'done', issues: 2 },
  { name: 'AuthModule', from: '14', to: '17', status: 'active', issues: 3 },
  { name: 'DashboardModule', from: '14', to: '17', status: 'active', issues: 1 },
  { name: 'RouterModule', from: '14', to: '17', status: 'pending', issues: 5 },
  { name: 'HttpClientModule', from: '14', to: '17', status: 'pending', issues: 4 },
  { name: 'FormsModule', from: '14', to: '17', status: 'pending', issues: 2 },
];

const RESOLVED = [
  'RouterModule lazy routes migrated',
  'Zone.js signals compatibility patched',
  'NgModule → standalone components',
  'HttpClient injection context fixed',
  'RxJS 6 → 7 operators rewritten',
  'ChangeDetectionStrategy.OnPush enforced',
];

const LOG_LINES = [
  '> ng update @angular/core@17 --force',
  'Fetching package metadata...',
  'Resolving peer dependencies...',
  'UPDATE package.json (3 changes)',
  'UPDATE tsconfig.json (1 change)',
  '✓ @angular/core 14.3.0 → 17.1.0',
  '✓ @angular/cli 14.2.0 → 17.1.0',
  '⚠ @ngrx/store requires manual migration',
  'Running migration schematics...',
  'Migrating lazy routes...',
  '✓ Lazy route syntax updated (4 routes)',
  'Checking standalone components...',
  '⚠ 3 NgModules need conversion',
  '> Running ng build --configuration production',
  'Building... webpack 5.88.0',
  '✓ Browser bundle: 2.1MB (was 4.2MB)',
  'Migration progress: 67% complete',
];

const TYPING_TEXT = "Your Angular migration, visualized.";

export default function HeroDashboard() {
  const [typedText, setTypedText] = useState('');
  const [checkmarks, setCheckmarks] = useState<number[]>([]);
  const [progress, setProgress] = useState(0);
  const [activeModule, setActiveModule] = useState(2);
  const logRef = useRef<HTMLDivElement>(null);

  // Typing effect
  useEffect(() => {
    let i = 0;
    const timer = setInterval(() => {
      if (i < TYPING_TEXT.length) {
        setTypedText(TYPING_TEXT.slice(0, i + 1));
        i++;
      } else {
        clearInterval(timer);
      }
    }, 55);
    return () => clearInterval(timer);
  }, []);

  // Progress bar animation
  useEffect(() => {
    const timer = setTimeout(() => {
      const interval = setInterval(() => {
        setProgress(p => {
          if (p >= 67) { clearInterval(interval); return 67; }
          return p + 1;
        });
      }, 18);
      return () => clearInterval(interval);
    }, 600);
    return () => clearTimeout(timer);
  }, []);

  // Checkmarks appearing one by one
  useEffect(() => {
    RESOLVED.forEach((_, i) => {
      setTimeout(() => {
        setCheckmarks(prev => [...prev, i]);
      }, 800 + i * 400);
    });
  }, []);

  // Cycle active module
  useEffect(() => {
    const interval = setInterval(() => {
      setActiveModule(m => (m === 3 ? 2 : 3));
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="relative w-full" style={{ minHeight: '100vh', paddingTop: '80px' }}>
      {/* Background grid */}
      <div className="absolute inset-0 bg-grid opacity-100 pointer-events-none" />

      {/* Ambient glow */}
      <div className="absolute inset-0 pointer-events-none" style={{
        background: 'radial-gradient(ellipse 80% 60% at 50% 30%, rgba(57,255,20,0.04) 0%, transparent 70%)'
      }} />

      {/* Scrolling log background */}
      <div className="absolute right-0 top-0 bottom-0 w-64 overflow-hidden opacity-[0.04] pointer-events-none select-none">
        <div className="animate-scroll-log">
          {[...LOG_LINES, ...LOG_LINES].map((line, i) => (
            <div key={i} className="font-mono text-xs py-0.5" style={{ color: 'var(--phosphor)' }}>{line}</div>
          ))}
        </div>
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-6 pt-16 pb-12">
        {/* Headline */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 mb-5 px-3 py-1.5 rounded-full font-mono text-xs"
            style={{ background: 'var(--phosphor-dim)', border: '1px solid rgba(57,255,20,0.2)', color: 'var(--phosphor)' }}>
            <span className="w-1.5 h-1.5 rounded-full animate-pulse-dot" style={{ background: 'var(--phosphor)' }} />
            LIVE MIGRATION PREVIEW — ANGULAR 14 → 17
          </div>
          <h1 className="font-sans font-bold tracking-tight" style={{ fontSize: 'clamp(2rem, 5vw, 3.5rem)', lineHeight: 1.1 }}>
            <span className="text-fg">{typedText}</span>
            <span className="animate-blink ml-0.5 inline-block w-0.5 h-[1em] align-middle"
              style={{ background: 'var(--phosphor)', verticalAlign: 'text-bottom' }} />
          </h1>
          <p className="mt-4 text-fg-muted font-sans text-base max-w-xl mx-auto leading-relaxed">
            Stop staring at compiler warnings. Get a systematic breakdown of every breaking change, deprecated API, and migration path — module by module.
          </p>
        </div>

        {/* Main Dashboard Grid */}
        <div className="grid grid-cols-12 gap-3" style={{ minHeight: '420px' }}>

          {/* LEFT: Dependency tree */}
          <div className="col-span-12 md:col-span-3 terminal-chrome flex flex-col">
            <div className="terminal-titlebar">
              <div className="dot dot-red" /><div className="dot dot-yellow" /><div className="dot dot-green" />
              <span className="font-mono text-xs text-fg-muted ml-2">dependencies.json</span>
            </div>
            <div className="flex-1 p-3 overflow-hidden" style={{ background: 'rgba(11,13,15,0.6)' }}>
              <div className="font-mono text-xs text-fg-muted mb-2">// Angular modules</div>
              {MODULES.map((mod, i) => (
                <div key={i}
                  className={`flex items-center justify-between py-1.5 px-2 rounded mb-1 transition-all duration-500 ${
                    i === activeModule ? 'border' : ''
                  }`}
                  style={{
                    background: i === activeModule ? 'rgba(57,255,20,0.05)' : 'transparent',
                    borderColor: i === activeModule ? 'rgba(57,255,20,0.2)' : 'transparent',
                  }}
                >
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                      style={{
                        background: mod.status === 'done' ? 'var(--phosphor)' :
                          mod.status === 'active' ? 'var(--plasma)' : 'var(--fg-dim)',
                        boxShadow: mod.status === 'active' ? '0 0 6px var(--plasma)' :
                          mod.status === 'done' ? '0 0 4px var(--phosphor)' : 'none',
                      }}
                    />
                    <span className="font-mono text-xs truncate"
                      style={{ color: mod.status === 'done' ? 'var(--fg)' : mod.status === 'active' ? 'var(--plasma)' : 'var(--fg-dim)' }}>
                      {mod.name}
                    </span>
                  </div>
                  <span className="font-mono text-xs flex-shrink-0 ml-1"
                    style={{ color: mod.status === 'done' ? 'var(--phosphor)' : mod.status === 'active' ? 'var(--plasma)' : 'var(--fg-dim)' }}>
                    v{mod.from}→{mod.to}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* CENTER: Progress panel */}
          <div className="col-span-12 md:col-span-5 terminal-chrome flex flex-col">
            <div className="terminal-titlebar">
              <div className="dot dot-red" /><div className="dot dot-yellow" /><div className="dot dot-green" />
              <span className="font-mono text-xs text-fg-muted ml-2">migration-progress.ts</span>
              <div className="ml-auto flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full animate-pulse-dot" style={{ background: 'var(--phosphor)' }} />
                <span className="font-mono text-xs" style={{ color: 'var(--phosphor)' }}>LIVE</span>
              </div>
            </div>
            <div className="flex-1 p-4 flex flex-col gap-4" style={{ background: 'rgba(11,13,15,0.6)' }}>
              {/* Big progress number */}
              <div className="flex items-end gap-3">
                <span className="font-mono font-bold text-phosphor" style={{ fontSize: '3.5rem', lineHeight: 1, textShadow: '0 0 20px rgba(57,255,20,0.5)' }}>
                  {progress}%
                </span>
                <div className="pb-2">
                  <div className="font-mono text-xs text-fg-muted">migration complete</div>
                  <div className="font-mono text-xs mt-0.5" style={{ color: 'var(--plasma)' }}>3 modules in progress</div>
                </div>
              </div>

              {/* Progress bar */}
              <div>
                <div className="progress-track w-full" style={{ height: '6px' }}>
                  <div className="progress-fill" style={{ width: `${progress}%` }} />
                </div>
                <div className="flex justify-between mt-1">
                  <span className="font-mono text-xs text-fg-muted">0%</span>
                  <span className="font-mono text-xs text-fg-muted">100%</span>
                </div>
              </div>

              {/* Phase breakdown */}
              <div className="grid grid-cols-4 gap-2 mt-1">
                {[
                  { label: 'Audit', pct: 100, color: 'var(--phosphor)' },
                  { label: 'Compat', pct: 85, color: 'var(--phosphor)' },
                  { label: 'Refactor', pct: 67, color: 'var(--plasma)' },
                  { label: 'Validate', pct: 12, color: 'var(--fg-dim)' },
                ].map(phase => (
                  <div key={phase.label} className="rounded p-2" style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}>
                    <div className="font-mono text-xs text-fg-muted mb-1">{phase.label}</div>
                    <div className="font-mono text-sm font-bold" style={{ color: phase.color }}>{phase.pct}%</div>
                    <div className="progress-track mt-1" style={{ height: '3px' }}>
                      <div className="progress-fill" style={{ width: `${phase.pct}%`, background: phase.color, boxShadow: 'none' }} />
                    </div>
                  </div>
                ))}
              </div>

              {/* Module log */}
              <div className="flex-1 overflow-hidden rounded p-2" style={{ background: 'var(--void)', border: '1px solid var(--border)', minHeight: '80px' }}>
                {['✓ AppModule migrated', '✓ SharedModule migrated', '⟳ AuthModule — 3 issues remaining', '⟳ DashboardModule — checking...', '○ RouterModule — queued'].map((line, i) => (
                  <div key={i} className="font-mono text-xs py-0.5 flex items-center gap-2"
                    style={{
                      color: line.startsWith('✓') ? 'var(--phosphor)' :
                        line.startsWith('⟳') ? 'var(--plasma)' : 'var(--fg-dim)'
                    }}>
                    {line}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* RIGHT: Resolved changes */}
          <div className="col-span-12 md:col-span-4 terminal-chrome flex flex-col">
            <div className="terminal-titlebar">
              <div className="dot dot-red" /><div className="dot dot-yellow" /><div className="dot dot-green" />
              <span className="font-mono text-xs text-fg-muted ml-2">resolved.log</span>
              <span className="ml-auto pill pill-green">{checkmarks.length} fixed</span>
            </div>
            <div className="flex-1 p-3 flex flex-col gap-2" style={{ background: 'rgba(11,13,15,0.6)' }}>
              <div className="font-mono text-xs text-fg-muted mb-1">// Breaking changes resolved</div>
              {RESOLVED.map((item, i) => (
                <div key={i}
                  className={`flex items-center gap-2 py-2 px-2 rounded transition-all duration-500 ${
                    checkmarks.includes(i) ? 'opacity-100' : 'opacity-0'
                  }`}
                  style={{
                    background: checkmarks.includes(i) ? 'rgba(57,255,20,0.05)' : 'transparent',
                    border: `1px solid ${checkmarks.includes(i) ? 'rgba(57,255,20,0.15)' : 'transparent'}`,
                    transitionDelay: `${i * 0.1}s`,
                    transform: checkmarks.includes(i) ? 'translateX(0)' : 'translateX(-8px)',
                  }}
                >
                  <span className={`flex-shrink-0 w-4 h-4 rounded-full flex items-center justify-center ${checkmarks.includes(i) ? 'animate-check-pop' : ''}`}
                    style={{ background: 'var(--phosphor-dim)', border: '1px solid rgba(57,255,20,0.3)' }}>
                    <svg width="8" height="8" viewBox="0 0 12 12" fill="none">
                      <path d="M2 6l3 3 5-5" stroke="#39FF14" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </span>
                  <span className="font-mono text-xs" style={{ color: 'var(--fg)' }}>{item}</span>
                </div>
              ))}

              {/* Issues still open */}
              <div className="mt-2 pt-2" style={{ borderTop: '1px solid var(--border)' }}>
                <div className="font-mono text-xs text-fg-muted mb-2">// Pending issues</div>
                {['Zone.js migration path unclear', 'NgRx effects need manual review'].map((issue, i) => (
                  <div key={i} className="flex items-center gap-2 py-1.5 px-2 rounded mb-1"
                    style={{ background: 'var(--signal-dim)', border: '1px solid rgba(255,53,98,0.15)' }}>
                    <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: 'var(--signal)' }} />
                    <span className="font-mono text-xs" style={{ color: 'var(--signal)' }}>{issue}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* CTA below dashboard */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mt-8">
          <a href="#audit"
            className="font-mono font-bold text-sm uppercase tracking-widest px-8 py-4 rounded transition-all duration-200 hover:scale-105"
            style={{ background: 'var(--phosphor)', color: 'var(--void)', boxShadow: '0 0 25px rgba(57,255,20,0.4)' }}>
            Audit My Angular Project →
          </a>
          <a href="#checklist"
            className="font-mono text-sm text-fg-muted hover:text-fg transition-colors flex items-center gap-2">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M12 15V3m0 12l-4-4m4 4l4-4M2 17l.621 2.485A2 2 0 004.561 21h14.878a2 2 0 001.94-1.515L22 17"/></svg>
            Download Migration Checklist (PDF)
          </a>
        </div>
      </div>
    </div>
  );
}