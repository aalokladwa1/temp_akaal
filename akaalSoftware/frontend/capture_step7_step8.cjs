const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('@playwright/test');

const DIST_DIR = path.join(__dirname, 'dist', 'akaal-software', 'browser');
const OUT_DIR = 'C:/Users/AALOK/.gemini/antigravity/brain/f8de0286-7b06-4fcc-be55-80e48d218a00';
const PORT = 4332;

// MIME types
const MIME = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2',
  '.woff': 'font/woff',
  '.ttf': 'font/ttf'
};

// Static file server with SPA routing fallback to index.html
const server = http.createServer((req, res) => {
  let reqPath = req.url.split('?')[0];
  let filePath = path.join(DIST_DIR, reqPath);

  if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
    const ext = path.extname(filePath);
    res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
    fs.createReadStream(filePath).pipe(res);
  } else {
    const indexPath = path.join(DIST_DIR, 'index.html');
    res.writeHead(200, { 'Content-Type': 'text/html' });
    fs.createReadStream(indexPath).pipe(res);
  }
});

server.listen(PORT, async () => {
  console.log(`Step 7 & 8 Capture Server listening on http://localhost:${PORT}`);

  let browser;
  try {
    browser = await chromium.launch({ headless: true, channel: 'chrome' });
  } catch (e) {
    try {
      browser = await chromium.launch({ headless: true, channel: 'msedge' });
    } catch (e2) {
      browser = await chromium.launch({ headless: true });
    }
  }

  const viewports = [
    { name: '1920x1080', width: 1920, height: 1080 },
    { name: '1440x900', width: 1440, height: 900 }
  ];

  for (const vp of viewports) {
    console.log(`\n========================================`);
    console.log(`Capturing Steps 7 & 8 for viewport: ${vp.name}...`);
    console.log(`========================================\n`);

    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height }
    });
    const page = await context.newPage();

    // Navigate to Create Validation
    await page.goto(`http://localhost:${PORT}/migration/validation/new`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);

    // Setup base draft state
    const setupDraft = async (step, extraDraft = {}) => {
      await page.evaluate(({ step, extraDraft }) => {
        const wizardEl = document.querySelector('app-new-validation-wizard');
        // @ts-ignore
        const comp = window.ng?.getComponent(wizardEl);
        if (comp && comp.vs) {
          comp.vs.updateDraft({
            name: 'Core Financials Settlement Assurance',
            environment: 'Production',
            validationContext: 'INDEPENDENT',
            sourceConnectionMode: 'SAVED',
            sourceConnectionId: 'conn-01',
            sourceProvider: 'Oracle',
            sourceHost: 'prod-oracle-rac.internal',
            sourcePort: 1521,
            sourceDatabase: 'FINANCE',
            sourceVerified: true,
            targetConnectionMode: 'SAVED',
            targetConnectionId: 'conn-02',
            targetProvider: 'PostgreSQL',
            targetHost: 'aurora-pg-cluster.aws.internal',
            targetPort: 5432,
            targetDatabase: 'public',
            targetVerified: true,
            step4Pathway: 'DEFINE',
            comparisonUnits: [
              {
                id: 'unit-01',
                sourceId: 'tbl_gl_balances',
                sourceName: 'GL_BALANCES',
                targetId: 'tbl_gl_balances',
                targetName: 'gl_balances',
                targetStatus: 'CONFIRMED',
                disposition: 'INCLUDED'
              },
              {
                id: 'unit-02',
                sourceId: 'tbl_journal_entries',
                sourceName: 'JOURNAL_ENTRIES',
                targetId: 'tbl_journal_entries',
                targetName: 'journal_entries',
                targetStatus: 'CONFIRMED',
                disposition: 'INCLUDED'
              },
              {
                id: 'unit-03',
                sourceId: 'tbl_payments',
                sourceName: 'PAYMENTS',
                targetId: 'tbl_payments',
                targetName: 'payments',
                targetStatus: 'CONFIRMED',
                disposition: 'INCLUDED'
              }
            ],
            baselineIntent: 'CURRENT_OPERATIONAL',
            assuranceLevel: 'PARTITION_FINGERPRINT',
            temporalCadence: 'CONSISTENT_STATE',
            coveragePolicy: 'EXHAUSTIVE',
            currentStep: step,
            ...extraDraft
          });
          // @ts-ignore
          window.ng?.applyChanges(wizardEl);
        }
      }, { step, extraDraft });
      await page.waitForTimeout(400);
    };

    const scrollCanvas = async (top) => {
      await page.evaluate((top) => {
        const canvas = document.querySelector('section[aria-label="Active Step Workspace Canvas"]');
        if (canvas) canvas.scrollTo({ top, behavior: 'instant' });
      }, top);
      await page.waitForTimeout(200);
    };

    // ------------------------------------------------------------------------
    // STEP 7 — STATE 1: Production Default (NOT_EVALUATED / READINESS_NOT_CONNECTED)
    // ------------------------------------------------------------------------
    console.log(`[${vp.name}] Capturing Step 7 State 1: Production Default...`);
    await setupDraft(7);
    await scrollCanvas(0);
    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_70_step7_default_not_evaluated_${vp.name}.png`),
      fullPage: false
    });

    // ------------------------------------------------------------------------
    // STEP 7 — STATE 2: Visual Fixture READY
    // ------------------------------------------------------------------------
    console.log(`[${vp.name}] Capturing Step 7 State 2: Fixture READY...`);
    await page.evaluate(() => {
      const step7El = document.querySelector('app-step7-readiness');
      // @ts-ignore
      const comp = window.ng?.getComponent(step7El);
      if (comp) {
        comp.visualFixture = {
          status: 'READY',
          statusLabel: 'Ready for Execution',
          summaryText: 'All 5 readiness domains evaluated and certified. Pre-execution checks passed.',
          isEvaluationConnected: true,
          domains: [
            {
              id: 'CONNECTIVITY_ACCESS',
              title: '1. Connectivity & Access Rights',
              description: 'Physical transport, endpoint reachability, TLS verification, and authentication credentials.',
              passedCount: 4,
              totalCount: 4,
              hasBlockers: false,
              hasWarnings: false,
              isExpanded: true,
              checks: [
                { id: 'c1', domain: 'CONNECTIVITY_ACCESS', name: 'Source Endpoint Reachability', status: 'READY', observation: 'Latency 1.8ms via Direct TCP', affectedResources: ['Oracle RAC'] },
                { id: 'c2', domain: 'CONNECTIVITY_ACCESS', name: 'Target Endpoint Reachability', status: 'READY', observation: 'Latency 0.9ms via Direct TCP', affectedResources: ['PostgreSQL Aurora'] },
                { id: 'c3', domain: 'CONNECTIVITY_ACCESS', name: 'TLS Handshake Attestation', status: 'READY', observation: 'TLS 1.3 negotiated with verify-full', affectedResources: ['TLS Layer'] },
                { id: 'c4', domain: 'CONNECTIVITY_ACCESS', name: 'Read-Only Privileges', status: 'READY', observation: 'SELECT privileges confirmed, zero mutation rights', affectedResources: ['Role: akaal_reader'] }
              ]
            },
            {
              id: 'SCOPE_CORRESPONDENCE',
              title: '2. Scope Correspondence & Entity Mapping',
              description: 'Target counterpart discovery and resolution of operator correspondence decisions.',
              passedCount: 2,
              totalCount: 2,
              hasBlockers: false,
              hasWarnings: false,
              isExpanded: false,
              checks: []
            },
            {
              id: 'BASELINE_LEGITIMACY',
              title: '3. Comparison Baseline Legitimacy',
              description: 'Baseline consistency conditions and transaction boundary stability.',
              passedCount: 1,
              totalCount: 1,
              hasBlockers: false,
              hasWarnings: false,
              isExpanded: false,
              checks: []
            },
            {
              id: 'ASSURANCE_COMPATIBILITY',
              title: '4. Assurance Strategy & Engine Capability',
              description: 'Assurance algorithm requirements, physical provider support, and exception contracts.',
              passedCount: 1,
              totalCount: 1,
              hasBlockers: false,
              hasWarnings: false,
              isExpanded: false,
              checks: []
            },
            {
              id: 'GOVERNANCE_OPERATIONAL',
              title: '5. Governance & Operational Conditions',
              description: 'Platform invariants and operator-declared maintenance coordination.',
              passedCount: 2,
              totalCount: 2,
              hasBlockers: false,
              hasWarnings: false,
              isExpanded: false,
              checks: []
            }
          ],
          actions: [],
          acknowledgements: []
        };
        // @ts-ignore
        window.ng?.applyChanges(step7El);
      }
    });
    await page.waitForTimeout(300);
    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_71_step7_fixture_ready_${vp.name}.png`),
      fullPage: false
    });

    // ------------------------------------------------------------------------
    // STEP 7 — STATE 3: Visual Fixture BLOCKED
    // ------------------------------------------------------------------------
    console.log(`[${vp.name}] Capturing Step 7 State 3: Fixture BLOCKED...`);
    await page.evaluate(() => {
      const step7El = document.querySelector('app-step7-readiness');
      // @ts-ignore
      const comp = window.ng?.getComponent(step7El);
      if (comp) {
        comp.visualFixture = {
          status: 'BLOCKED',
          statusLabel: 'Validation Blocked',
          summaryText: '1 blocking issue prevents validation execution. Remediate in upstream wizard step.',
          isEvaluationConnected: true,
          domains: [
            {
              id: 'SCOPE_CORRESPONDENCE',
              title: '2. Scope Correspondence & Entity Mapping',
              description: 'Target counterpart discovery and resolution of operator correspondence decisions.',
              passedCount: 1,
              totalCount: 2,
              hasBlockers: true,
              hasWarnings: false,
              isExpanded: true,
              checks: [
                {
                  id: 'c-blocker',
                  domain: 'SCOPE_CORRESPONDENCE',
                  name: 'Target Counterpart Unresolved',
                  status: 'BLOCKER',
                  observation: 'Entity AUDIT_LOG_2025 has no confirmed counterpart in target database.',
                  affectedResources: ['AUDIT_LOG_2025']
                }
              ]
            }
          ],
          actions: [
            {
              id: 'act-1',
              severity: 'BLOCKER',
              title: 'Unresolved Target Correspondence',
              description: 'One or more included comparison units have unresolved target mappings.',
              actionLabel: 'Resolve in Step 4',
              upstreamStep: 4
            }
          ],
          acknowledgements: []
        };
        // @ts-ignore
        window.ng?.applyChanges(step7El);
      }
    });
    await page.waitForTimeout(300);
    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_72_step7_fixture_blocked_${vp.name}.png`),
      fullPage: false
    });

    // ------------------------------------------------------------------------
    // STEP 7 — STATE 4: Operational Conditions & Acknowledgements
    // ------------------------------------------------------------------------
    console.log(`[${vp.name}] Capturing Step 7 State 4: Operational Conditions...`);
    await setupDraft(7, {
      baselineIntent: 'MAINTENANCE_COORDINATED',
      maintenanceCondition: 'WRITES_STOPPED_DECLARED'
    });
    await page.evaluate(() => {
      const step7El = document.querySelector('app-step7-readiness');
      // @ts-ignore
      const comp = window.ng?.getComponent(step7El);
      if (comp) {
        comp.visualFixture = undefined;
        // @ts-ignore
        window.ng?.applyChanges(step7El);
      }
    });
    try {
      await page.locator('text=Operational Conditions & Maintenance Coordination').scrollIntoViewIfNeeded({ timeout: 1000 });
    } catch {
      await scrollCanvas(500);
    }
    await page.waitForTimeout(300);
    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_73_step7_operational_conditions_${vp.name}.png`),
      fullPage: false
    });

    // ------------------------------------------------------------------------
    // STEP 7 — STATE 5: Inspect Drawer Open
    // ------------------------------------------------------------------------
    console.log(`[${vp.name}] Capturing Step 7 State 5: Inspect Drawer Open...`);
    await scrollCanvas(0);
    await page.evaluate(() => {
      const step7El = document.querySelector('app-step7-readiness');
      // @ts-ignore
      const comp = window.ng?.getComponent(step7El);
      if (comp) {
        comp.openInspectDrawer({
          id: 'conn-src-reach',
          domain: 'CONNECTIVITY_ACCESS',
          name: 'Source Endpoint Reachability & Handshake',
          status: 'NOT_EVALUATED',
          observation: 'Endpoint host prod-oracle-rac.internal:1521 specified. Live TCP socket handshake and TLS ALPN negotiation will execute during engine initialization.',
          affectedResources: ['prod-oracle-rac.internal:1521 (Oracle RAC 19c)'],
          technicalDetail: 'Socket Probe: Deferred to engine runner\nProtocol: Oracle TNS over TCP\nTLS Cipher: TLS_AES_256_GCM_SHA384 (enforced)',
          remediationGuidance: 'Ensure firewall allows ingress on port 1521 from the AKAAL engine host and TLS certificate chains are valid.'
        });
        // @ts-ignore
        window.ng?.applyChanges(step7El);
      }
    });
    await page.waitForTimeout(350);
    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_74_step7_inspect_drawer_${vp.name}.png`),
      fullPage: false
    });

    // Close drawer
    await page.evaluate(() => {
      const step7El = document.querySelector('app-step7-readiness');
      // @ts-ignore
      const comp = window.ng?.getComponent(step7El);
      if (comp) {
        comp.closeInspectDrawer();
        // @ts-ignore
        window.ng?.applyChanges(step7El);
      }
    });
    await page.waitForTimeout(200);

    // ------------------------------------------------------------------------
    // STEP 8 — STATE 6: Review - Top Section (Identity & Groups 1-2)
    // ------------------------------------------------------------------------
    console.log(`[${vp.name}] Capturing Step 8 State 6: Identity & Top Groups...`);
    await setupDraft(8);
    await scrollCanvas(0);
    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_80_step8_timing_initialization_${vp.name}.png`),
      fullPage: false
    });

    // ------------------------------------------------------------------------
    // STEP 8 — STATE 7: Review - Execution Timing (SCHEDULE_LATER)
    // ------------------------------------------------------------------------
    console.log(`[${vp.name}] Capturing Step 8 State 7: Timing SCHEDULE_LATER (Scrolled)...`);
    await page.evaluate(() => {
      const step8El = document.querySelector('app-step8-review');
      // @ts-ignore
      const comp = window.ng?.getComponent(step8El);
      if (comp) {
        comp.setTimingChoice('SCHEDULE_LATER');
        comp.setScheduledDate('2026-10-15');
        comp.setScheduledTime('02:30');
        // @ts-ignore
        window.ng?.applyChanges(step8El);
      }
    });
    try {
      await page.locator('text=When should this validation run?').scrollIntoViewIfNeeded({ timeout: 1000 });
    } catch {
      await scrollCanvas(800);
    }
    await page.waitForTimeout(300);
    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_81_step8_timing_schedule_later_${vp.name}.png`),
      fullPage: false
    });

    // ------------------------------------------------------------------------
    // STEP 8 — STATE 8: Review - Execution Timing (RECURRING)
    // ------------------------------------------------------------------------
    console.log(`[${vp.name}] Capturing Step 8 State 8: Timing RECURRING (Scrolled)...`);
    await page.evaluate(() => {
      const step8El = document.querySelector('app-step8-review');
      // @ts-ignore
      const comp = window.ng?.getComponent(step8El);
      if (comp) {
        comp.setTimingChoice('RECURRING');
        comp.setRecurrenceFrequency('DAILY');
        // @ts-ignore
        window.ng?.applyChanges(step8El);
      }
    });
    try {
      await page.locator('text=When should this validation run?').scrollIntoViewIfNeeded({ timeout: 1000 });
    } catch {
      await scrollCanvas(800);
    }
    await page.waitForTimeout(300);
    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_82_step8_timing_recurring_${vp.name}.png`),
      fullPage: false
    });

    // Capture with Recurrence Custom Dropdown Open
    console.log(`[${vp.name}] Capturing Step 8 State 8C: Recurrence Dropdown Open...`);
    try {
      const selectBtn = page.locator('app-custom-select button').first();
      if (await selectBtn.count() > 0) {
        await selectBtn.click();
        await page.waitForTimeout(300);
        await page.screenshot({
          path: path.join(OUT_DIR, `validation_create_82c_step8_timing_recurring_dropdown_open_${vp.name}.png`),
          fullPage: false
        });
        await selectBtn.click();
        await page.waitForTimeout(150);
      }
    } catch (e) {
      console.warn('Could not capture open dropdown:', e);
    }

    // ------------------------------------------------------------------------
    // STEP 8 — STATE 8B: Operational Considerations / Consequence Explainer
    // ------------------------------------------------------------------------
    console.log(`[${vp.name}] Capturing Step 8 State 8B: Operational Considerations...`);
    try {
      await page.locator('text=Operational Considerations').scrollIntoViewIfNeeded({ timeout: 1000 });
    } catch {
      await scrollCanvas(1200);
    }
    await page.waitForTimeout(300);
    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_82b_step8_consequence_${vp.name}.png`),
      fullPage: false
    });

    // ------------------------------------------------------------------------
    // STEP 8 — STATE 9: Technical Configuration Modal Open
    // ------------------------------------------------------------------------
    console.log(`[${vp.name}] Capturing Step 8 State 9: Technical Modal Open...`);
    await scrollCanvas(0);
    await page.evaluate(() => {
      const step8El = document.querySelector('app-step8-review');
      // @ts-ignore
      const comp = window.ng?.getComponent(step8El);
      if (comp) {
        comp.openTechnicalModal();
        // @ts-ignore
        window.ng?.applyChanges(step8El);
      }
    });
    await page.waitForTimeout(350);
    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_83_step8_technical_modal_${vp.name}.png`),
      fullPage: false
    });

    await context.close();
  }

  await browser.close();
  server.close(() => {
    console.log('Capture Server closed. All Step 7 & 8 screenshots captured successfully!');
    process.exit(0);
  });
});
