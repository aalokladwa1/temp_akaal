'use client';
import React, { useEffect, useRef, useState } from 'react';

interface MetricConfig {
  label: string;
  value: number;
  suffix: string;
  prefix: string;
  description: string;
  company: string;
  color: string;
  icon: React.ReactNode;
}

const METRICS: MetricConfig[] = [
  {
    label: 'Build time reduction',
    value: 43,
    suffix: '%',
    prefix: '',
    description: 'Production build went from 4m 12s to 2m 24s after standalone migration',
    company: 'FinOps Platform — 47 microfrontends',
    color: 'var(--phosphor)',
    icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>,
  },
  {
    label: 'Bundle size saved',
    value: 2.1,
    suffix: 'MB',
    prefix: '',
    description: 'Tree-shaking improvements after removing NgModule overhead',
    company: 'Enterprise HR Suite — Angular 12 → 17',
    color: 'var(--plasma)',
    icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/></svg>,
  },
  {
    label: 'Test pass rate restored',
    value: 94,
    suffix: '%',
    prefix: '',
    description: 'From 61% failing after ng update to 94% green in 3 sprints',
    company: 'Logistics Dashboard — 340 test files',
    color: 'var(--phosphor)',
    icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/></svg>,
  },
  {
    label: 'Feature velocity restored',
    value: 6,
    suffix: ' wks',
    prefix: '',
    description: 'Time from red CI to full feature velocity — not two quarters',
    company: 'InsureTech Platform — 12-person team',
    color: 'var(--plasma)',
    icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>,
  },
];

function CountUp({ target, suffix, prefix, color, active }: { target: number; suffix: string; prefix: string; color: string; active: boolean }) {
  const [current, setCurrent] = useState(0);
  const isDecimal = target % 1 !== 0;

  useEffect(() => {
    if (!active) return;
    let start = 0;
    const step = target / 60;
    const timer = setInterval(() => {
      start += step;
      if (start >= target) { setCurrent(target); clearInterval(timer); }
      else setCurrent(start);
    }, 16);
    return () => clearInterval(timer);
  }, [active, target]);

  return (
    <span className="font-mono font-bold" style={{ fontSize: '2.8rem', lineHeight: 1, color, textShadow: `0 0 20px ${color}40` }}>
      {prefix}{isDecimal ? current.toFixed(1) : Math.floor(current)}{suffix}
    </span>
  );
}

export default function MetricsSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { setVisible(true); obs.disconnect(); }
    }, { threshold: 0.15 });
    if (sectionRef.current) obs.observe(sectionRef.current);
    return () => obs.disconnect();
  }, []);

  return (
    <section ref={sectionRef} className="relative py-28 overflow-hidden" style={{ borderTop: '1px solid var(--border)' }}>
      <div className="absolute inset-0 pointer-events-none"
        style={{ background: 'radial-gradient(ellipse 60% 40% at 70% 50%, rgba(255,230,0,0.02) 0%, transparent 70%)' }} />

      <div className="max-w-7xl mx-auto px-6">
        <div className={`reveal ${visible ? 'visible' : ''} mb-16`}>
          <span className="font-mono text-xs tracking-widest uppercase mb-3 block" style={{ color: 'var(--plasma)' }}>
            03 // Outcomes
          </span>
          <h2 className="font-sans font-bold tracking-tight" style={{ fontSize: 'clamp(1.8rem, 4vw, 3rem)' }}>
            Numbers from real migrations.
          </h2>
          <p className="mt-3 text-fg-muted text-base max-w-lg leading-relaxed">
            Not estimates. Actual measurements from enterprise teams who ran the full pipeline.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {METRICS.map((metric, i) => (
            <div
              key={i}
              className={`reveal card-hover rounded-lg p-6 ${visible ? 'visible' : ''}`}
              style={{
                transitionDelay: `${i * 0.1}s`,
                background: 'var(--surface)',
                border: '1px solid var(--border)',
              }}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="w-9 h-9 rounded-lg flex items-center justify-center"
                  style={{ background: `${metric.color}15`, border: `1px solid ${metric.color}30`, color: metric.color }}>
                  {metric.icon}
                </div>
                <span className="pill pill-muted">{metric.company.split('—')[0].trim()}</span>
              </div>

              <div className="mb-2">
                <CountUp
                  target={metric.value}
                  suffix={metric.suffix}
                  prefix={metric.prefix}
                  color={metric.color}
                  active={visible}
                />
              </div>

              <div className="font-sans font-semibold text-base mb-2" style={{ color: 'var(--fg)' }}>{metric.label}</div>
              <p className="font-mono text-xs text-fg-muted leading-relaxed mb-3">{metric.description}</p>

              <div className="pt-3 flex items-center gap-2" style={{ borderTop: '1px solid var(--border)' }}>
                <span className="w-1 h-1 rounded-full" style={{ background: metric.color }} />
                <span className="font-mono text-xs text-fg-muted">{metric.company}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Social proof strip */}
        <div className={`reveal ${visible ? 'visible' : ''} mt-8 rounded-lg p-5`}
          style={{ transitionDelay: '0.4s', background: 'var(--surface)', border: '1px solid var(--border)' }}>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { quote: '"We went from 40 red pipelines to all-green in 4 weeks. The phase breakdown made it manageable."', name: 'Priya Nair', role: 'Engineering Lead, Mumbai', initials: 'PN' },
              { quote: '"The code diff previews alone saved us 3 sprint cycles of archaeology. We knew exactly what to touch."', name: 'Marcus Webb', role: 'Frontend Architect, Austin TX', initials: 'MW' },
              { quote: '"CTO approved the roadmap in one meeting because the migration was visualized, not described."', name: 'Yuki Tanaka', role: 'VP Engineering, Tokyo', initials: 'YT' },
            ].map((t, i) => (
              <div key={i} className="flex flex-col gap-3">
                <p className="font-sans text-sm text-fg-muted leading-relaxed italic">"{t.quote}"</p>
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-full flex items-center justify-center font-mono text-xs font-bold"
                    style={{ background: 'var(--phosphor-dim)', color: 'var(--phosphor)', border: '1px solid rgba(57,255,20,0.2)' }}>
                    {t.initials}
                  </div>
                  <div>
                    <div className="font-sans text-xs font-semibold" style={{ color: 'var(--fg)' }}>{t.name}</div>
                    <div className="font-mono text-xs text-fg-muted">{t.role}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}