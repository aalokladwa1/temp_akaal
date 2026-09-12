const http = require('http');
const fs = require('fs');
const path = require('path');

const playwrightPath = path.resolve(__dirname, '../../../frontend/node_modules/playwright');
const { chromium } = require(playwrightPath);

const distDir = path.resolve(__dirname, '../../../frontend/dist/akaal-software/browser');
const evidenceDir = path.resolve(__dirname, 'evidence');
const manifestsDir = path.resolve(__dirname, 'manifests');

if (!fs.existsSync(evidenceDir)) fs.mkdirSync(evidenceDir, { recursive: true });
if (!fs.existsSync(manifestsDir)) fs.mkdirSync(manifestsDir, { recursive: true });

const mimeTypes = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.mjs': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2'
};

const server = http.createServer((req, res) => {
  let reqPath = req.url.split('?')[0];
  let filePath = path.join(distDir, reqPath);
  if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    filePath = path.join(distDir, 'index.html');
  }
  const ext = path.extname(filePath).toLowerCase();
  const ctype = mimeTypes[ext] || 'application/octet-stream';
  res.writeHead(200, { 'Content-Type': ctype });
  fs.createReadStream(filePath).pipe(res);
});

const PORT = 4399;

const testCases = [
  { id: 'TC-DASH-001', module: 'Dashboard', url: '/dashboard', label: 'Executive Dashboard', requiredSelector: 'app-dashboard' },
  { id: 'TC-MIGR-001', module: 'Migration', url: '/migration', label: 'Migration Portfolio', requiredSelector: 'p-portfolio-home, app-portfolio-home' },
  { id: 'TC-MIGR-002', module: 'Migration', url: '/migration/new', label: '9-Step Wizard Step 1', requiredSelector: 'app-create-migration-wizard' },
  { id: 'TC-MIGR-003', module: 'Migration', url: '/cockpit/MIG-DEMO-001', label: 'Mission Control Cockpit', requiredSelector: 'app-cockpit' },
  { id: 'TC-MIGR-004', module: 'Migration', url: '/connections', label: 'Connections Portfolio', requiredSelector: 'app-connections' },
  { id: 'TC-MIGR-005', module: 'Migration', url: '/connections/new', label: 'Create Connection', requiredSelector: 'app-create-connection' },
  { id: 'TC-MIGR-006', module: 'Migration', url: '/connections/CONN-PG-PROD', label: 'Connection Details & Probes', requiredSelector: 'app-connection-workspace' },
  { id: 'TC-MIGR-007', module: 'Migration', url: '/validation', label: 'Validation Operations Portfolio', requiredSelector: 'app-validation-portfolio' },
  { id: 'TC-MIGR-008', module: 'Migration', url: '/validation/new', label: 'New Validation Wizard', requiredSelector: 'app-new-validation-wizard' },
  { id: 'TC-MIGR-009', module: 'Migration', url: '/validation/VAL-SUITE-001', label: 'Validation Workstation', requiredSelector: 'app-validation-workstation' },
  { id: 'TC-MIGR-010', module: 'Migration', url: '/migration/history', label: 'Migration History', requiredSelector: 'app-history-home' },
  { id: 'TC-MON-001', module: 'Monitoring', url: '/monitoring', label: 'Monitoring Overview', requiredSelector: 'app-monitoring' },
  { id: 'TC-MON-002', module: 'Monitoring', url: '/monitoring/migrations', label: 'Migration Telemetry', requiredSelector: 'app-migration-monitoring' },
  { id: 'TC-MON-003', module: 'Monitoring', url: '/monitoring/platform', label: 'Platform Telemetry', requiredSelector: 'app-platform-monitoring' },
  { id: 'TC-MON-004', module: 'Monitoring', url: '/monitoring/alerts', label: 'Alerts & Incidents', requiredSelector: 'app-alerts' },
  { id: 'TC-REP-001', module: 'Reports', url: '/reports', label: 'Reports Catalog (14 Types)', requiredSelector: 'app-reports' },
  { id: 'TC-REP-002', module: 'Reports', url: '/reports/certification', label: 'Trust Certification', requiredSelector: 'app-reports' },
  { id: 'TC-REP-003', module: 'Reports', url: '/reports/evidence', label: 'Evidence Portal', requiredSelector: 'app-reports' },
  { id: 'TC-ADM-001', module: 'Administration', url: '/administration/enterprise', label: 'Enterprise Management', requiredSelector: 'app-admin' },
  { id: 'TC-ADM-002', module: 'Administration', url: '/administration/enterprise/workspaces', label: 'Enterprise Workspaces', requiredSelector: 'app-admin' },
  { id: 'TC-ADM-003', module: 'Administration', url: '/administration/people-access', label: 'People & Access', requiredSelector: 'app-admin' },
  { id: 'TC-ADM-004', module: 'Administration', url: '/administration/governance-centre/approval-chains', label: 'Approval Chains & Governance', requiredSelector: 'app-admin' },
  { id: 'TC-ADM-005', module: 'Administration', url: '/administration/security/kms', label: 'Security KMS & Keys', requiredSelector: 'app-admin' },
  { id: 'TC-ADM-006', module: 'Administration', url: '/administration/templates/migration', label: 'Migration Templates Library', requiredSelector: 'app-admin' },
  { id: 'TC-ADM-007', module: 'Administration', url: '/administration/connectors-plugins', label: 'Connector Center', requiredSelector: 'app-admin' },
  { id: 'TC-ADM-008', module: 'Administration', url: '/administration/infrastructure', label: 'Cloud & Infrastructure', requiredSelector: 'app-admin' },
  { id: 'TC-ADM-009', module: 'Administration', url: '/administration/compliance', label: 'Compliance Frameworks', requiredSelector: 'app-admin' },
  { id: 'TC-ADM-010', module: 'Administration', url: '/administration/audit', label: 'Audit Trail', requiredSelector: 'app-admin' },
  { id: 'TC-ADM-011', module: 'Administration', url: '/administration/platform', label: 'Platform Administration', requiredSelector: 'app-admin' },
  { id: 'TC-SET-001', module: 'Settings', url: '/settings/general', label: 'Settings General', requiredSelector: 'app-settings' },
  { id: 'TC-SET-002', module: 'Settings', url: '/settings/appearance', label: 'Settings Appearance', requiredSelector: 'app-settings' },
  { id: 'TC-SET-003', module: 'Settings', url: '/settings/runtime', label: 'Settings Runtime Defaults', requiredSelector: 'app-settings' },
  { id: 'TC-SET-004', module: 'Settings', url: '/settings/notifications', label: 'Settings Notifications Routing', requiredSelector: 'app-settings' },
  { id: 'TC-SET-005', module: 'Settings', url: '/settings/ai', label: 'Settings AI Governance', requiredSelector: 'app-settings' },
  { id: 'TC-SET-006', module: 'Settings', url: '/settings/advanced', label: 'Settings Advanced Options', requiredSelector: 'app-settings' }
];

server.listen(PORT, async () => {
  console.log('Deep Re-Audit Sweep Server running on port ' + PORT);

  const sweepOutput = {
    auditTimestamp: new Date().toISOString(),
    serverPort: PORT,
    totalTestCases: testCases.length,
    testCasesPassed: 0,
    testCasesFailed: 0,
    crossCuttingVerifications: {},
    consoleErrorsCaught: [],
    caseResults: []
  };

  let browser;
  try {
    browser = await chromium.launch({ headless: true, channel: 'msedge' });
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();

    page.on('console', msg => {
      if (msg.type() === 'error') {
        sweepOutput.consoleErrorsCaught.push({ text: msg.text(), location: msg.location() });
      }
    });

    await page.goto('http://localhost:' + PORT + '/dashboard', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    const orgSelector = await page.button:has-text(Acme Global), button:has-text(Acme), div:has-text(Acme);
    const envBadge = await page.span:has-text(PROD), div:has-text(PROD);
    sweepOutput.crossCuttingVerifications.contextSwitcher = {
      orgSelectorFound: !!orgSelector,
      envBadgeFound: !!envBadge,
      status: orgSelector || envBadge ? 'VERIFIED' : 'NOT_FOUND'
    };

    await page.keyboard.press('Control+KeyK');
    await page.waitForTimeout(300);
    const cmdPalette = await page.input[placeholder*=command], div[role=dialog];
    sweepOutput.crossCuttingVerifications.commandPalette = {
      modalTriggeredByCtrlK: !!cmdPalette,
      status: cmdPalette ? 'VERIFIED_EXACT' : 'TRIGGER_FAILED'
    };
    if (cmdPalette) {
      await page.keyboard.press('Escape');
      await page.waitForTimeout(200);
    }

    const bellBtn = await page.button:has([data-icon=bell]), button svg.lucide-bell;
    sweepOutput.crossCuttingVerifications.notificationCenter = {
      headerBellFound: !!bellBtn,
      status: bellBtn ? 'VERIFIED_COMPACT_POPOVER' : 'HEADER_BELL_NOT_FOUND'
    };

    const assistantDrawer = await page.aside#assistant-drawer, div#assistant-drawer, button:has-text(Assistant), button:has-text(AKAAL Assistant);
    sweepOutput.crossCuttingVerifications.assistantDrawer = {
      floatingDrawerFound: !!assistantDrawer,
      governingStatus: assistantDrawer ? 'BUILT' : 'SURFACE_MISSING_CONFIG_UNDER_SETTINGS_AI'
    };

    const approvalInboxHeader = await page.button#approval-inbox, button:has-text(Approvals ();
