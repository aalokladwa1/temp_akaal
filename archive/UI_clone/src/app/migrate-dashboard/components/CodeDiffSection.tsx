'use client';
import React, { useEffect, useRef, useState } from 'react';

const DIFFS = [
  {
    title: 'NgModule → Standalone Component',
    before: [
      { type: 'neutral', code: '// app.module.ts' },
      { type: 'deleted', code: 'import { NgModule } from \'@angular/core\';' },
      { type: 'deleted', code: 'import { BrowserModule } from \'@angular/platform-browser\';' },
      { type: 'deleted', code: '' },
      { type: 'deleted', code: '@NgModule({' },
      { type: 'deleted', code: '  declarations: [AppComponent],' },
      { type: 'deleted', code: '  imports: [BrowserModule],' },
      { type: 'deleted', code: '  bootstrap: [AppComponent]' },
      { type: 'deleted', code: '})' },
      { type: 'deleted', code: 'export class AppModule {}' },
    ],
    after: [
      { type: 'neutral', code: '// main.ts' },
      { type: 'added', code: 'import { bootstrapApplication } from \'@angular/platform-browser\';' },
      { type: 'added', code: 'import { AppComponent } from \'./app/app.component\';' },
      { type: 'added', code: '' },
      { type: 'added', code: 'bootstrapApplication(AppComponent, {' },
      { type: 'added', code: '  providers: [provideRouter(routes)]' },
      { type: 'added', code: '}).catch(err => console.error(err));' },
    ],
  },
  {
    title: 'HttpClientModule → provideHttpClient()',
    before: [
      { type: 'neutral', code: '// app.module.ts (legacy)' },
      { type: 'deleted', code: 'import { HttpClientModule } from \'@angular/common/http\';' },
      { type: 'deleted', code: '' },
      { type: 'deleted', code: '@NgModule({' },
      { type: 'deleted', code: '  imports: [HttpClientModule]' },
      { type: 'deleted', code: '})' },
    ],
    after: [
      { type: 'neutral', code: '// app.config.ts (standalone)' },
      { type: 'added', code: 'import { provideHttpClient,' },
      { type: 'added', code: '         withInterceptorsFromDi' },
      { type: 'added', code: '} from \'@angular/common/http\';' },
      { type: 'added', code: '' },
      { type: 'added', code: 'export const appConfig: ApplicationConfig = {' },
      { type: 'added', code: '  providers: [provideHttpClient()]' },
      { type: 'added', code: '};' },
    ],
  },
];

function CodeLine({ line, delay }: { line: { type: string; code: string }; delay: number }) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setVisible(true), delay);
    return () => clearTimeout(t);
  }, [delay]);

  return (
    <div
      className={`code-block px-3 py-0.5 transition-all duration-300 ${
        line.type === 'deleted' ? 'diff-deleted' :
        line.type === 'added' ? 'diff-added' : 'diff-neutral'
      }`}
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateX(0)' : 'translateX(-4px)',
      }}
    >
      <span className="mr-2 select-none font-mono text-xs"
        style={{ color: line.type === 'deleted' ? 'var(--signal)' : line.type === 'added' ? 'var(--phosphor)' : 'var(--fg-dim)' }}>
        {line.type === 'deleted' ? '−' : line.type === 'added' ? '+' : ' '}
      </span>
      <span className={`font-mono text-xs ${line.type === 'deleted' ? 'tok-deleted' : line.type === 'added' ? 'tok-added' : ''}`}
        style={{ color: line.type === 'neutral' ? 'var(--fg-muted)' : undefined }}>
        {line.code || '\u00a0'}
      </span>
    </div>
  );
}

export default function CodeDiffSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const [visible, setVisible] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  const [animKey, setAnimKey] = useState(0);

  useEffect(() => {
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { setVisible(true); obs.disconnect(); }
    }, { threshold: 0.15 });
    if (sectionRef.current) obs.observe(sectionRef.current);
    return () => obs.disconnect();
  }, []);

  const handleTab = (i: number) => {
    setActiveTab(i);
    setAnimKey(k => k + 1);
  };

  const diff = DIFFS[activeTab];

  return (
    <section ref={sectionRef} className="relative py-28 overflow-hidden" style={{ borderTop: '1px solid var(--border)' }}>
      <div className="absolute inset-0 pointer-events-none"
        style={{ background: 'radial-gradient(ellipse 50% 40% at 30% 50%, rgba(255,53,98,0.02) 0%, transparent 70%)' }} />

      <div className="max-w-7xl mx-auto px-6">
        <div className={`reveal ${visible ? 'visible' : ''} mb-12`}>
          <span className="font-mono text-xs tracking-widest uppercase mb-3 block" style={{ color: 'var(--signal)' }}>
            02 // Breaking Changes
          </span>
          <h2 className="font-sans font-bold tracking-tight" style={{ fontSize: 'clamp(1.8rem, 4vw, 3rem)' }}>
            See exactly what changes.
          </h2>
          <p className="mt-3 text-fg-muted text-base max-w-lg leading-relaxed">
            Every deprecated API mapped to its modern replacement. Syntax-highlighted diffs, not vague release notes.
          </p>
        </div>

        {/* Tab selector */}
        <div className={`reveal ${visible ? 'visible' : ''} flex gap-2 mb-6`} style={{ transitionDelay: '0.1s' }}>
          {DIFFS.map((d, i) => (
            <button key={i} onClick={() => handleTab(i)}
              className="font-mono text-xs px-4 py-2 rounded transition-all duration-200"
              style={{
                background: activeTab === i ? 'var(--surface-2)' : 'transparent',
                border: `1px solid ${activeTab === i ? 'rgba(255,53,98,0.3)' : 'var(--border)'}`,
                color: activeTab === i ? 'var(--signal)' : 'var(--fg-muted)',
              }}>
              {d.title.split('→')[0].trim()}
            </button>
          ))}
        </div>

        {/* Diff viewer */}
        <div className={`reveal ${visible ? 'visible' : ''}`} style={{ transitionDelay: '0.2s' }}>
          <div className="terminal-chrome">
            <div className="terminal-titlebar justify-between">
              <div className="flex items-center gap-2">
                <div className="dot dot-red" /><div className="dot dot-yellow" /><div className="dot dot-green" />
              </div>
              <span className="font-mono text-xs text-fg-muted">{diff.title}</span>
              <span className="pill pill-red font-mono text-xs">deprecated</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2" style={{ background: 'var(--void)' }}>
              {/* Before */}
              <div style={{ borderRight: '1px solid var(--border)' }}>
                <div className="px-3 py-2 flex items-center gap-2" style={{ borderBottom: '1px solid var(--border)', background: 'rgba(255,53,98,0.05)' }}>
                  <span className="w-2 h-2 rounded-full" style={{ background: 'var(--signal)' }} />
                  <span className="font-mono text-xs" style={{ color: 'var(--signal)' }}>BEFORE — Angular 14</span>
                </div>
                <div className="py-2 overflow-x-auto">
                  {diff.before.map((line, i) => (
                    <CodeLine key={`${animKey}-before-${i}`} line={line} delay={visible ? i * 60 : 9999} />
                  ))}
                </div>
              </div>

              {/* After */}
              <div>
                <div className="px-3 py-2 flex items-center gap-2" style={{ borderBottom: '1px solid var(--border)', background: 'rgba(57,255,20,0.04)' }}>
                  <span className="w-2 h-2 rounded-full" style={{ background: 'var(--phosphor)' }} />
                  <span className="font-mono text-xs" style={{ color: 'var(--phosphor)' }}>AFTER — Angular 17</span>
                </div>
                <div className="py-2 overflow-x-auto">
                  {diff.after.map((line, i) => (
                    <CodeLine key={`${animKey}-after-${i}`} line={line} delay={visible ? 400 + i * 60 : 9999} />
                  ))}
                </div>
              </div>
            </div>

            {/* Footer bar */}
            <div className="px-4 py-2 flex items-center gap-4" style={{ borderTop: '1px solid var(--border)', background: 'var(--surface-2)' }}>
              <span className="font-mono text-xs" style={{ color: 'var(--signal)' }}>−{diff.before.filter(l => l.type === 'deleted').length} removed</span>
              <span className="font-mono text-xs" style={{ color: 'var(--phosphor)' }}>+{diff.after.filter(l => l.type === 'added').length} added</span>
              <span className="font-mono text-xs text-fg-muted ml-auto">auto-migrated by schematic</span>
              <span className="pill pill-green">✓ schematic available</span>
            </div>
          </div>
        </div>

        {/* Breaking change catalog */}
        <div className={`reveal ${visible ? 'visible' : ''} mt-6 grid grid-cols-1 md:grid-cols-3 gap-3`} style={{ transitionDelay: '0.3s' }}>
          {[
            { label: 'Deprecated APIs', count: 34, auto: 28, color: 'var(--signal)' },
            { label: 'RxJS operators', count: 12, auto: 12, color: 'var(--plasma)' },
            { label: 'Route syntax changes', count: 8, auto: 6, color: 'var(--phosphor)' },
          ].map(item => (
            <div key={item.label} className="rounded-lg p-4 card-hover" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
              <div className="font-mono text-xs text-fg-muted mb-2">{item.label}</div>
              <div className="flex items-end gap-2">
                <span className="font-mono font-bold text-2xl" style={{ color: item.color }}>{item.count}</span>
                <span className="font-mono text-xs text-fg-muted mb-1">found</span>
              </div>
              <div className="mt-2">
                <div className="progress-track" style={{ height: '3px' }}>
                  <div className="progress-fill" style={{ width: `${(item.auto / item.count) * 100}%`, background: item.color, boxShadow: 'none' }} />
                </div>
                <span className="font-mono text-xs mt-1 block" style={{ color: item.color }}>{item.auto}/{item.count} auto-fixable</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}