import React from 'react';
import Header from '@/components/Header';
import Footer from '@/components/Footer';
import HeroDashboard from './components/HeroDashboard';
import PipelineSection from './components/PipelineSection';
import CodeDiffSection from './components/CodeDiffSection';
import MetricsSection from './components/MetricsSection';
import LeadCaptureSection from './components/LeadCaptureSection';
import StickyCTA from './components/StickyCTA';

export default function MigrateDashboardPage() {
  return (
    <div className="noise" style={{ background: 'var(--void)', minHeight: '100vh' }}>
      {/* Scanlines overlay */}
      <div className="scanlines" />

      <Header />

      <main>
        {/* Hero — full viewport migration dashboard */}
        <HeroDashboard />

        {/* Pipeline phases */}
        <PipelineSection />

        {/* Code diffs */}
        <CodeDiffSection />

        {/* Metrics */}
        <MetricsSection />

        {/* Lead capture form */}
        <LeadCaptureSection />
      </main>

      <Footer />

      {/* Sticky bottom CTA */}
      <StickyCTA />
    </div>
  );
}