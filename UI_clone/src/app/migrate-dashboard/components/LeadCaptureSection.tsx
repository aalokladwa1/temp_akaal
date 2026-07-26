'use client';
import React, { useState } from 'react';

const ANGULAR_VERSIONS = ['v8', 'v9', 'v10', 'v11', 'v12', 'v13', 'v14', 'v15', 'v16'];
const MODULE_RANGES = [
  { label: '< 10 modules', value: 'lt10' },
  { label: '10 – 50 modules', value: '10to50' },
  { label: '50+ modules', value: 'gt50' },
];

export default function LeadCaptureSection() {
  const [step, setStep] = useState(1);
  const [version, setVersion] = useState('');
  const [moduleRange, setModuleRange] = useState('');
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [checklistEmail, setChecklistEmail] = useState('');
  const [checklistDone, setChecklistDone] = useState(false);

  const handleAuditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Backend integration point — connect to audit API here
    setSubmitted(true);
  };

  const handleChecklistSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Backend integration point — send checklist PDF here
    setChecklistDone(true);
  };

  return (
    <section id="audit" className="relative py-28 overflow-hidden" style={{ borderTop: '1px solid var(--border)' }}>
      {/* Ambient */}
      <div className="absolute inset-0 pointer-events-none"
        style={{ background: 'radial-gradient(ellipse 60% 50% at 50% 50%, rgba(57,255,20,0.04) 0%, transparent 70%)' }} />

      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">

          {/* Left: Copy */}
          <div>
            <span className="font-mono text-xs tracking-widest uppercase mb-4 block" style={{ color: 'var(--phosphor)' }}>
              04 // Start Now
            </span>
            <h2 className="font-sans font-bold tracking-tight mb-4" style={{ fontSize: 'clamp(1.8rem, 4vw, 2.8rem)' }}>
              Get your migration roadmap in 24 hours.
            </h2>
            <p className="text-fg-muted text-base leading-relaxed mb-8 max-w-md">
              Tell us your current Angular version and project scale. We run a static analysis audit and return a prioritized migration plan — no sales call required.
            </p>

            {/* What you get */}
            <div className="space-y-3 mb-8">
              {[
                'Full breaking change inventory, version-specific',
                'Auto-fixable vs. manual effort breakdown',
                'Sprint-by-sprint migration timeline estimate',
                'CI/CD impact assessment across your pipeline',
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-3">
                  <span className="w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0"
                    style={{ background: 'var(--phosphor-dim)', border: '1px solid rgba(57,255,20,0.3)' }}>
                    <svg width="8" height="8" viewBox="0 0 12 12" fill="none">
                      <path d="M2 6l3 3 5-5" stroke="#39FF14" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </span>
                  <span className="font-mono text-sm" style={{ color: 'var(--fg)' }}>{item}</span>
                </div>
              ))}
            </div>

            {/* Checklist download */}
            <div id="checklist" className="rounded-lg p-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
              <div className="flex items-center gap-2 mb-3">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"
                  style={{ color: 'var(--plasma)' }}>
                  <path d="M12 15V3m0 12l-4-4m4 4l4-4M2 17l.621 2.485A2 2 0 004.561 21h14.878a2 2 0 001.94-1.515L22 17"/>
                </svg>
                <span className="font-mono text-xs font-bold" style={{ color: 'var(--plasma)' }}>FREE DOWNLOAD</span>
              </div>
              <div className="font-sans font-semibold text-sm mb-1">Angular Migration Checklist (PDF)</div>
              <p className="font-mono text-xs text-fg-muted mb-3">87-point checklist covering every breaking change from v8 → v17.</p>
              {checklistDone ? (
                <div className="flex items-center gap-2 font-mono text-xs" style={{ color: 'var(--phosphor)' }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M9 11l3 3L22 4"/>
                  </svg>
                  Check your inbox — checklist sent!
                </div>
              ) : (
                <form onSubmit={handleChecklistSubmit} className="flex gap-2">
                  <input
                    type="email"
                    placeholder="work@company.com"
                    value={checklistEmail}
                    onChange={e => setChecklistEmail(e.target.value)}
                    required
                    className="form-input flex-1"
                    style={{ fontSize: '12px', padding: '8px 12px' }}
                  />
                  <button type="submit"
                    className="font-mono text-xs font-bold px-4 py-2 rounded transition-all"
                    style={{ background: 'var(--plasma)', color: 'var(--void)' }}>
                    Send
                  </button>
                </form>
              )}
            </div>
          </div>

          {/* Right: Form */}
          <div className="terminal-chrome">
            <div className="terminal-titlebar justify-between">
              <div className="flex items-center gap-2">
                <div className="dot dot-red" /><div className="dot dot-yellow" /><div className="dot dot-green" />
              </div>
              <span className="font-mono text-xs text-fg-muted">audit-request.sh</span>
              <span className="pill pill-green">secure</span>
            </div>

            <div className="p-6" style={{ background: 'rgba(11,13,15,0.8)' }}>
              {submitted ? (
                <div className="text-center py-8">
                  <div className="w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-4 animate-check-pop"
                    style={{ background: 'var(--phosphor-dim)', border: '2px solid var(--phosphor)' }}>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#39FF14" strokeWidth="2">
                      <path d="M9 11l3 3L22 4"/>
                    </svg>
                  </div>
                  <h3 className="font-sans font-bold text-lg mb-2" style={{ color: 'var(--phosphor)' }}>Audit request received.</h3>
                  <p className="font-mono text-xs text-fg-muted">We&apos;ll have your migration roadmap in your inbox within 24 hours.</p>
                  <div className="mt-4 p-3 rounded" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                    <div className="font-mono text-xs text-fg-muted">// Audit queued for:</div>
                    <div className="font-mono text-xs mt-1" style={{ color: 'var(--phosphor)' }}>Angular {version} → 17 · {moduleRange} modules · {email}</div>
                  </div>
                </div>
              ) : (
                <>
                  {/* Step indicator */}
                  <div className="flex items-center gap-2 mb-6">
                    {[1,2,3].map(s => (
                      <React.Fragment key={s}>
                        <div className="flex items-center gap-1.5">
                          <div className="w-5 h-5 rounded-full flex items-center justify-center font-mono text-xs font-bold transition-all duration-300"
                            style={{
                              background: step >= s ? 'var(--phosphor)' : 'var(--surface-2)',
                              color: step >= s ? 'var(--void)' : 'var(--fg-muted)',
                              border: `1px solid ${step >= s ? 'var(--phosphor)' : 'var(--border)'}`,
                            }}>
                            {step > s ? '✓' : s}
                          </div>
                          <span className="font-mono text-xs hidden sm:inline"
                            style={{ color: step === s ? 'var(--fg)' : 'var(--fg-muted)' }}>
                            {s === 1 ? 'Version' : s === 2 ? 'Scale' : 'Contact'}
                          </span>
                        </div>
                        {s < 3 && <div className="flex-1 h-px" style={{ background: step > s ? 'var(--phosphor)' : 'var(--border)', transition: 'background 0.3s' }} />}
                      </React.Fragment>
                    ))}
                  </div>

                  <form onSubmit={handleAuditSubmit}>
                    {/* Step 1 */}
                    {step === 1 && (
                      <div className="space-y-4">
                        <div>
                          <label className="font-mono text-xs text-fg-muted block mb-2">Current Angular version</label>
                          <select
                            value={version}
                            onChange={e => setVersion(e.target.value)}
                            className="form-input"
                            required
                          >
                            <option value="">-- select version --</option>
                            {ANGULAR_VERSIONS.map(v => (
                              <option key={v} value={v}>{v}</option>
                            ))}
                          </select>
                        </div>
                        {version && (
                          <div className="rounded p-3" style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}>
                            <div className="font-mono text-xs text-fg-muted mb-1">Estimated breaking changes:</div>
                            <div className="font-mono text-lg font-bold" style={{ color: 'var(--signal)' }}>
                              {version === 'v8' ? '47' : version === 'v9' ? '41' : version === 'v10' ? '38' :
                               version === 'v11' ? '33' : version === 'v12' ? '28' : version === 'v13' ? '22' :
                               version === 'v14' ? '17' : version === 'v15' ? '11' : '6'}
                            </div>
                            <div className="font-mono text-xs" style={{ color: 'var(--phosphor)' }}>
                              {version === 'v8' ? '~71%' : version === 'v9' ? '~73%' : '~82%'} auto-fixable
                            </div>
                          </div>
                        )}
                        <button
                          type="button"
                          disabled={!version}
                          onClick={() => setStep(2)}
                          className="w-full font-mono text-sm font-bold py-3 rounded transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
                          style={{ background: 'var(--phosphor)', color: 'var(--void)' }}>
                          Next: Project scale →
                        </button>
                      </div>
                    )}

                    {/* Step 2 */}
                    {step === 2 && (
                      <div className="space-y-4">
                        <div>
                          <label className="font-mono text-xs text-fg-muted block mb-3">Approximate number of Angular modules</label>
                          <div className="space-y-2">
                            {MODULE_RANGES.map(range => (
                              <label key={range.value}
                                className="flex items-center gap-3 p-3 rounded cursor-pointer transition-all duration-200"
                                style={{
                                  background: moduleRange === range.value ? 'var(--phosphor-dim)' : 'var(--surface-2)',
                                  border: `1px solid ${moduleRange === range.value ? 'rgba(57,255,20,0.3)' : 'var(--border)'}`,
                                }}>
                                <input
                                  type="radio"
                                  name="modules"
                                  value={range.value}
                                  checked={moduleRange === range.value}
                                  onChange={() => setModuleRange(range.value)}
                                  className="sr-only"
                                />
                                <div className="w-4 h-4 rounded-full border flex items-center justify-center flex-shrink-0 transition-all"
                                  style={{
                                    borderColor: moduleRange === range.value ? 'var(--phosphor)' : 'var(--fg-dim)',
                                    background: moduleRange === range.value ? 'var(--phosphor)' : 'transparent',
                                  }}>
                                  {moduleRange === range.value && <div className="w-1.5 h-1.5 rounded-full" style={{ background: 'var(--void)' }} />}
                                </div>
                                <span className="font-mono text-sm" style={{ color: moduleRange === range.value ? 'var(--phosphor)' : 'var(--fg)' }}>
                                  {range.label}
                                </span>
                              </label>
                            ))}
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <button type="button" onClick={() => setStep(1)}
                            className="flex-1 font-mono text-sm py-3 rounded transition-all"
                            style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--fg-muted)' }}>
                            ← Back
                          </button>
                          <button type="button" disabled={!moduleRange} onClick={() => setStep(3)}
                            className="flex-1 font-mono text-sm font-bold py-3 rounded transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                            style={{ background: 'var(--phosphor)', color: 'var(--void)' }}>
                            Next: Contact →
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Step 3 */}
                    {step === 3 && (
                      <div className="space-y-4">
                        <div>
                          <label className="font-mono text-xs text-fg-muted block mb-2">Work email</label>
                          <input
                            type="email"
                            placeholder="you@company.com"
                            value={email}
                            onChange={e => setEmail(e.target.value)}
                            className="form-input"
                            required
                          />
                          <p className="font-mono text-xs text-fg-muted mt-2">Your audit report lands here within 24 hours.</p>
                        </div>
                        {/* Summary */}
                        <div className="rounded p-3" style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}>
                          <div className="font-mono text-xs text-fg-muted mb-2">// Audit parameters</div>
                          <div className="space-y-1">
                            <div className="flex justify-between font-mono text-xs">
                              <span className="text-fg-muted">From version</span>
                              <span style={{ color: 'var(--plasma)' }}>{version}</span>
                            </div>
                            <div className="flex justify-between font-mono text-xs">
                              <span className="text-fg-muted">Target version</span>
                              <span style={{ color: 'var(--phosphor)' }}>v17</span>
                            </div>
                            <div className="flex justify-between font-mono text-xs">
                              <span className="text-fg-muted">Module scale</span>
                              <span style={{ color: 'var(--fg)' }}>{MODULE_RANGES.find(r => r.value === moduleRange)?.label}</span>
                            </div>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <button type="button" onClick={() => setStep(2)}
                            className="font-mono text-sm py-3 px-4 rounded transition-all"
                            style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--fg-muted)' }}>
                            ←
                          </button>
                          <button type="submit" disabled={!email}
                            className="flex-1 font-mono text-sm font-bold py-3 rounded transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                            style={{ background: 'var(--phosphor)', color: 'var(--void)', boxShadow: '0 0 20px rgba(57,255,20,0.3)' }}>
                            Audit My Angular Project →
                          </button>
                        </div>
                      </div>
                    )}
                  </form>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}