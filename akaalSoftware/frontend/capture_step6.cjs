const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('@playwright/test');

const DIST_DIR = path.join(__dirname, 'dist', 'akaal-software', 'browser');
const OUT_DIR = 'C:/Users/AALOK/.gemini/antigravity/brain/f8de0286-7b06-4fcc-be55-80e48d218a00';
const PORT = 4328;

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
  console.log(`Step 6 Capture Server listening on http://localhost:${PORT}`);

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
    console.log(`Capturing Step 6 for viewport: ${vp.name}...`);
    console.log(`========================================\n`);

    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height }
    });
    const page = await context.newPage();

    // Navigate to Create Validation
    await page.goto(`http://localhost:${PORT}/migration/validation/new`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);

    // Setup base draft state for Step 6
    const baseSetup = async (extraDraft = {}, extraComp = null) => {
      await page.evaluate(({ extraDraft, extraComp }) => {
        const wizardEl = document.querySelector('app-new-validation-wizard');
        // @ts-ignore
        const comp = window.ng?.getComponent(wizardEl);
        if (comp && comp.vs) {
          comp.vs.updateDraft({
            name: 'Core Financials Migration Assurance Mission',
            validationContext: 'EXISTING_PROJECT',
            projectId: 'proj-01',
            projectName: 'Cloud Modernization 2026',
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
            currentStep: 6,
            baselineIntent: 'INHERITED_MIGRATION',
            assuranceLevel: 'PARTITION_FINGERPRINT',
            temporalCadence: 'CONSISTENT_STATE',
            coveragePolicy: 'EXHAUSTIVE',
            assuranceExceptions: [],
            ...extraDraft
          });
        }
        if (extraComp) {
          const step6El = document.querySelector('app-step6-strategy');
          // @ts-ignore
          const step6Comp = window.ng?.getComponent(step6El);
          if (step6Comp) {
            if (extraComp.isAdvancedCoverageOpen !== undefined) {
              step6Comp.isAdvancedCoverageOpen.set(extraComp.isAdvancedCoverageOpen);
            }
            if (extraComp.showExceptionModal !== undefined) {
              step6Comp.showExceptionModal.set(extraComp.showExceptionModal);
              if (extraComp.showExceptionModal && typeof step6Comp.attachModalToBody === 'function') {
                step6Comp.attachModalToBody();
              }
            }
            if (extraComp.contextualFinding !== undefined) {
              step6Comp.contextualFinding.set(extraComp.contextualFinding);
            }
            if (extraComp.draftExceptionType !== undefined) {
              step6Comp.draftExceptionType.set(extraComp.draftExceptionType);
            }
            if (extraComp.draftReason !== undefined) {
              step6Comp.draftReason.set(extraComp.draftReason);
            }
            if (extraComp.draftSelectedObjectIds !== undefined) {
              step6Comp.draftSelectedObjectIds.set(extraComp.draftSelectedObjectIds);
            }
          }
        }
      }, { extraDraft, extraComp });
      await page.waitForTimeout(350);
    };

    // -------------------------------------------------------------------------
    // Shot 60: State A — Default Partition Fingerprint (Level 3, Exhaustive, Consistent-State)
    // -------------------------------------------------------------------------
    await baseSetup();
    const shot60 = path.join(OUT_DIR, `validation_create_60_step6_default_fingerprint_${vp.name}.png`);
    await page.screenshot({ path: shot60, fullPage: false });
    console.log(`Captured: ${shot60}`);

    // -------------------------------------------------------------------------
    // Shot 61: State B — Complete Attribute Assurance (Level 4, Highest Assurance)
    // -------------------------------------------------------------------------
    await baseSetup({ assuranceLevel: 'COMPLETE_ATTRIBUTE' });
    const shot61 = path.join(OUT_DIR, `validation_create_61_step6_complete_attribute_${vp.name}.png`);
    await page.screenshot({ path: shot61, fullPage: false });
    console.log(`Captured: ${shot61}`);

    // -------------------------------------------------------------------------
    // Shot 62: State C — Cardinality Assurance (Level 2)
    // -------------------------------------------------------------------------
    await baseSetup({ assuranceLevel: 'CARDINALITY' });
    const shot62 = path.join(OUT_DIR, `validation_create_62_step6_cardinality_${vp.name}.png`);
    await page.screenshot({ path: shot62, fullPage: false });
    console.log(`Captured: ${shot62}`);

    // -------------------------------------------------------------------------
    // Shot 63: State D — Mixed Assurance Exceptions (Escalated + Reduced Scopes)
    // -------------------------------------------------------------------------
    await baseSetup({
      assuranceLevel: 'PARTITION_FINGERPRINT',
      assuranceExceptions: [
        {
          id: 'exc-escalated-ledger',
          type: 'ESCALATED',
          targetAssuranceLevel: 'COMPLETE_ATTRIBUTE',
          reason: 'Financial critical general ledger tables requiring row-level logical value equivalence for SOX compliance',
          objectIds: ['tbl_gl_balances', 'tbl_payments'],
          objectNames: ['GL_BALANCES', 'PAYMENTS']
        },
        {
          id: 'exc-reduced-session',
          type: 'REDUCED',
          targetAssuranceLevel: 'CARDINALITY',
          reason: 'High-volume ephemeral session logs exempt from cryptographic partition verification',
          objectIds: ['tbl_sessions'],
          objectNames: ['SESSIONS_ARCHIVE']
        }
      ]
    });
    // Scroll down to showcase Zone 4 Assurance Exceptions
    await page.evaluate(() => {
      const scrollableCanvas = document.querySelector('section[aria-label="Active Step Workspace Canvas"]');
      if (scrollableCanvas) {
        scrollableCanvas.scrollTo({ top: 620, behavior: 'instant' });
      }
    });
    await page.waitForTimeout(300);

    const shot63 = path.join(OUT_DIR, `validation_create_63_step6_mixed_assurance_exceptions_${vp.name}.png`);
    await page.screenshot({ path: shot63, fullPage: false });
    console.log(`Captured: ${shot63}`);

    // -------------------------------------------------------------------------
    // Shot 64: State E — Large-Estate Object Picker Modal Open
    // -------------------------------------------------------------------------
    // Reset scroll to top before opening modal
    await page.evaluate(() => {
      const scrollableCanvas = document.querySelector('section[aria-label="Active Step Workspace Canvas"]');
      if (scrollableCanvas) {
        scrollableCanvas.scrollTo({ top: 0, behavior: 'instant' });
      }
    });
    await page.waitForTimeout(200);

    await baseSetup({}, {
      showExceptionModal: true,
      draftExceptionType: 'ESCALATED',
      draftReason: 'High-consequence payment records requiring exhaustive attribute-level verification',
      draftSelectedObjectIds: ['tbl_payments', 'tbl_transactions']
    });
    const shot64 = path.join(OUT_DIR, `validation_create_64_step6_exception_modal_${vp.name}.png`);
    await page.screenshot({ path: shot64, fullPage: false });
    console.log(`Captured: ${shot64}`);

    // Close modal
    await baseSetup({}, { showExceptionModal: false });

    // -------------------------------------------------------------------------
    // Shot 65: State F — Continuous Cadence (Capability Unavailable Notice + Fail-Closed)
    // -------------------------------------------------------------------------
    await baseSetup({
      temporalCadence: 'CONTINUOUS'
    });
    // Scroll down to reveal temporal cards and capability unavailable box
    await page.evaluate(() => {
      const scrollableCanvas = document.querySelector('section[aria-label="Active Step Workspace Canvas"]');
      if (scrollableCanvas) {
        scrollableCanvas.scrollTo({ top: 480, behavior: 'instant' });
      }
    });
    await page.waitForTimeout(300);

    const shot65 = path.join(OUT_DIR, `validation_create_65_step6_continuous_unavailable_${vp.name}.png`);
    await page.screenshot({ path: shot65, fullPage: false });
    console.log(`Captured: ${shot65}`);

    // -------------------------------------------------------------------------
    // Shot 66: State G — Advanced Coverage & Sampling Progressively Disclosed
    // -------------------------------------------------------------------------
    await baseSetup({
      coveragePolicy: 'LIMITED_SAMPLE',
      advancedCoverage: {
        mode: 'STATISTICAL_SAMPLE',
        samplePercentage: 5,
        deterministicSeed: 42,
        disclaimer: 'Statistical sampling proves only the inspected subset and will not satisfy the cutover certification gate.'
      }
    }, {
      isAdvancedCoverageOpen: true
    });
    // Scroll down to reveal advanced coverage section
    await page.evaluate(() => {
      const scrollableCanvas = document.querySelector('section[aria-label="Active Step Workspace Canvas"]');
      if (scrollableCanvas) {
        scrollableCanvas.scrollTo({ top: scrollableCanvas.scrollHeight, behavior: 'instant' });
      }
    });
    await page.waitForTimeout(300);

    const shot66 = path.join(OUT_DIR, `validation_create_66_step6_advanced_coverage_sampling_${vp.name}.png`);
    await page.screenshot({ path: shot66, fullPage: false });
    console.log(`Captured: ${shot66}`);

    // -------------------------------------------------------------------------
    // Shot 67: State H — P7C Contextual Intelligence Advisory Finding
    // -------------------------------------------------------------------------
    await baseSetup({}, {
      isAdvancedCoverageOpen: false,
      contextualFinding: {
        id: 'cif-high-churn',
        severity: 'ADVISORY',
        title: 'Elevated Write Churn Detected on Scoped Financial Entities',
        body: 'Source telemetry indicates frequent concurrent updates on GL_BALANCES and PAYMENTS. Partition fingerprinting will capture point-in-time divergence quickly, but Complete Attribute validation or scoped escalation is recommended for audit defensibility.',
        recommendedAssuranceLevel: 'COMPLETE_ATTRIBUTE',
        isDismissed: false
      }
    });
    // Reset scroll to top
    await page.evaluate(() => {
      const scrollableCanvas = document.querySelector('section[aria-label="Active Step Workspace Canvas"]');
      if (scrollableCanvas) {
        scrollableCanvas.scrollTo({ top: 0, behavior: 'instant' });
      }
    });
    await page.waitForTimeout(300);

    const shot67 = path.join(OUT_DIR, `validation_create_67_step6_p7c_recommendation_${vp.name}.png`);
    await page.screenshot({ path: shot67, fullPage: false });
    console.log(`Captured: ${shot67}`);

    await context.close();
  }

  await browser.close();
  server.close(() => {
    console.log('Capture server closed. All Step 6 screenshots generated successfully.');
    process.exit(0);
  });
});
