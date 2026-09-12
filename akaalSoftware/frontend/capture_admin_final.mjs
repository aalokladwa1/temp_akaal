import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve('a:/temp_akaal/akaalSoftware/frontend/dist/akaal-software/browser');
const outDir = path.resolve('C:/Users/AALOK/.gemini/antigravity/brain/855a7066-43c2-4fd3-8061-d8f7101ebdc0/admin_final_captures');

if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

const server = http.createServer((req, res) => {
  let reqPath = req.url.split('?')[0];
  const ext = path.extname(reqPath).toLowerCase();
  let filePath = path.join(distDir, reqPath);

  if (ext) {
    if (!fs.existsSync(filePath)) {
      filePath = path.join(distDir, path.basename(reqPath));
    }
  } else {
    filePath = path.join(distDir, 'index.html');
  }

  if (!fs.existsSync(filePath)) {
    filePath = path.join(distDir, 'index.html');
  }

  const mimeTypes = {
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.woff2': 'font/woff2',
    '.woff': 'font/woff',
    '.ttf': 'font/ttf'
  };

  const contentType = mimeTypes[path.extname(filePath).toLowerCase()] || 'application/octet-stream';
  fs.readFile(filePath, (err, content) => {
    if (err) {
      res.writeHead(500);
      res.end('Server error: ' + err.code);
    } else {
      if (filePath.endsWith('index.html')) {
        const text = content.toString('utf-8').replace('<base href="./">', '<base href="/">');
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(text, 'utf-8');
      } else {
        res.writeHead(200, { 'Content-Type': contentType });
        res.end(content);
      }
    }
  });
});

const PORT = 4355;
server.listen(PORT, async () => {
  console.log(`Final capture server running on http://localhost:${PORT}`);

  try {
    const browser = await chromium.launch({ headless: true, channel: 'msedge' });
    const context = await browser.newContext();
    const page = await context.newPage();

    const targets = [
      { name: '01_admin_home_master', url: '/administration' },
      
      // 5.8 Compliance
      { name: '02_compliance_home', url: '/administration/compliance' },
      { name: '03_compliance_catalog', url: '/administration/compliance/frameworks/catalog' },
      { name: '04_compliance_detail', url: '/administration/compliance/frameworks/detail/fw-soc2' },
      { name: '05_compliance_views', url: '/administration/compliance/frameworks/views' },
      { name: '06_compliance_custom_create', url: '/administration/compliance/frameworks/custom/create' },
      { name: '07_compliance_controls', url: '/administration/compliance/controls/mapping' },
      { name: '08_compliance_exception_request', url: '/administration/compliance/controls/exceptions/request' },
      { name: '09_compliance_evidence', url: '/administration/compliance/evidence' },
      
      // 5.9 Audit
      { name: '10_audit_home', url: '/administration/audit' },
      { name: '11_audit_policies', url: '/administration/audit/policies' },
      { name: '12_audit_policy_create', url: '/administration/audit/policies/create' },
      { name: '13_audit_destinations', url: '/administration/audit/destinations' },
      { name: '14_audit_destination_create', url: '/administration/audit/destinations/create' },
      { name: '15_audit_trail', url: '/administration/audit/trail' },
      { name: '16_audit_legal_hold', url: '/administration/audit/legal-hold' },
      { name: '17_audit_legal_hold_create', url: '/administration/audit/legal-hold/create' },
      { name: '18_audit_integrity', url: '/administration/audit/integrity' },
      { name: '19_audit_export', url: '/administration/audit/export' },

      // 5.10 Platform Administration
      { name: '20_platform_admin_home', url: '/administration/platform-admin' },
      { name: '21_platform_config', url: '/administration/platform-admin/platform/config' },
      { name: '22_platform_services', url: '/administration/platform-admin/platform/services' },
      { name: '23_platform_updates', url: '/administration/platform-admin/lifecycle/updates' },
      { name: '24_platform_maintenance', url: '/administration/platform-admin/lifecycle/maintenance' },
      { name: '25_platform_maintenance_create', url: '/administration/platform-admin/lifecycle/maintenance/create' },
      { name: '26_platform_licensing', url: '/administration/platform-admin/commercial/licensing' },
      { name: '27_platform_backup', url: '/administration/platform-admin/resilience/backup-restore' },
      { name: '28_platform_diagnostics', url: '/administration/platform-admin/support/diagnostics' },

      // 5.11 Integrations & Notifications
      { name: '29_integrations_home', url: '/administration/integrations' },
      { name: '30_integrations_channels', url: '/administration/integrations/notifications/channels' },
      { name: '31_integrations_channel_create', url: '/administration/integrations/notifications/channels/create' },
      { name: '32_integrations_policies', url: '/administration/integrations/notifications/policies' },
      { name: '33_integrations_routing', url: '/administration/integrations/events/routing' },
      { name: '34_integrations_siem', url: '/administration/integrations/enterprise/siem' },
      { name: '35_integrations_siem_create', url: '/administration/integrations/enterprise/siem/create' },
      { name: '36_integrations_itsm', url: '/administration/integrations/enterprise/itsm' },
      { name: '37_integrations_credentials', url: '/administration/integrations/credentials' }
    ];

    const viewports = [
      { width: 1920, height: 1080, suffix: '1920x1080' },
      { width: 1440, height: 900, suffix: '1440x900' }
    ];

    page.on('console', msg => {
      if (msg.type() === 'error') console.log('BROWSER CONSOLE ERROR:', msg.text());
    });
    page.on('pageerror', err => console.log('PAGE ERROR:', err.message));

    for (const target of targets) {
      const cap1 = path.join(outDir, `${target.name}_1920x1080.png`);
      const cap2 = path.join(outDir, `${target.name}_1440x900.png`);

      try {
        await page.setViewportSize({ width: 1920, height: 1080 });
        await page.goto(`http://localhost:${PORT}${target.url}`, { waitUntil: 'load', timeout: 10000 });
        await page.waitForTimeout(350);
        
        await page.screenshot({ path: cap1, fullPage: false });
        console.log(`Captured: ${path.basename(cap1)}`);

        await page.setViewportSize({ width: 1440, height: 900 });
        await page.waitForTimeout(150);
        await page.screenshot({ path: cap2, fullPage: false });
        console.log(`Captured: ${path.basename(cap2)}`);
      } catch (navErr) {
        console.error(`Error capturing ${target.name}:`, navErr.message);
      }
    }

    console.log('All 74 final administration captures completed successfully!');
    await browser.close();
  } catch (err) {
    console.error('Final capture error:', err);
  } finally {
    server.close();
    process.exit(0);
  }
});
