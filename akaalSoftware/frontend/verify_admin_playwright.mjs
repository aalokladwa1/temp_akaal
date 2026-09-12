import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve('a:/temp_akaal/akaalSoftware/frontend/dist/akaal-software/browser');
const outDir = path.resolve('C:/Users/AALOK/.gemini/antigravity/brain/855a7066-43c2-4fd3-8061-d8f7101ebdc0/admin_playwright_captures');

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
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content, 'utf-8');
    }
  });
});

const PORT = 4349;
server.listen(PORT, async () => {
  console.log(`Verification server running on http://localhost:${PORT}`);

  try {
    const browser = await chromium.launch({ headless: true, channel: 'msedge' });
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 }
    });
    const page = await context.newPage();

    const viewports = [
      { width: 1920, height: 1080, name: '1920x1080' },
      { width: 1440, height: 900, name: '1440x900' },
      { width: 1280, height: 800, name: '1280x800' }
    ];

    // Helper for multi-res capture
    async function captureMultiRes(url, filePrefix) {
      for (const vp of viewports) {
        await page.setViewportSize({ width: vp.width, height: vp.height });
        await page.goto(`http://localhost:${PORT}${url}`, { waitUntil: 'networkidle' });
        await page.waitForTimeout(400);
        await page.screenshot({ path: path.join(outDir, `${filePrefix}_${vp.name}.png`), fullPage: false });
        console.log(`Captured: ${filePrefix}_${vp.name}.png`);
      }
    }

    // 1. Admin Home Overview
    await captureMultiRes('/administration', 'admin_01_home_overview');

    // 2. 5.1 Enterprise - Organizations
    await captureMultiRes('/administration/enterprise?tab=organizations', 'admin_02_enterprise_organizations');

    // 3. 5.1 Enterprise - Workspaces
    await captureMultiRes('/administration/enterprise?tab=workspaces', 'admin_03_enterprise_workspaces');

    // 4. 5.1 Enterprise - Environments
    await captureMultiRes('/administration/enterprise?tab=environments', 'admin_04_enterprise_environments');

    // 5. 5.1 Enterprise - Boundaries
    await captureMultiRes('/administration/enterprise?tab=boundaries', 'admin_05_enterprise_boundaries');

    // 6. 5.1 Enterprise - Ownership
    await captureMultiRes('/administration/enterprise?tab=ownership', 'admin_06_enterprise_ownership');

    // 7. 5.1 Enterprise - Quotas
    await captureMultiRes('/administration/enterprise?tab=quotas', 'admin_07_enterprise_quotas');

    // 8. 5.1 Enterprise - Metadata
    await captureMultiRes('/administration/enterprise?tab=metadata', 'admin_08_enterprise_metadata');

    // 9. 5.1 Enterprise - Setup
    await captureMultiRes('/administration/enterprise?tab=setup', 'admin_09_enterprise_setup');

    // 10. 5.2 People - Users & Principals
    await captureMultiRes('/administration/people?tab=users', 'admin_10_people_users');

    // 11. 5.2 People - Teams
    await captureMultiRes('/administration/people?tab=teams', 'admin_11_people_teams');

    // 12. 5.2 People - Roles & Matrix
    await captureMultiRes('/administration/people?tab=roles', 'admin_12_people_roles');

    // 13. 5.2 People - Permissions
    await captureMultiRes('/administration/people?tab=permissions', 'admin_13_people_permissions');

    // 14. 5.2 People - RBAC
    await captureMultiRes('/administration/people?tab=rbac', 'admin_14_people_rbac');

    // 15. 5.2 People - ABAC
    await captureMultiRes('/administration/people?tab=abac', 'admin_15_people_abac');

    // 16. 5.2 People - JIT Elevation
    await captureMultiRes('/administration/people?tab=jit', 'admin_16_people_jit');

    // 17. 5.2 People - SoD
    await captureMultiRes('/administration/people?tab=sod', 'admin_17_people_sod');

    // 18. 5.2 People - Active Sessions
    await captureMultiRes('/administration/people?tab=sessions', 'admin_18_people_sessions');

    // 19. 5.2 People - Service Accounts
    await captureMultiRes('/administration/people?tab=service-accounts', 'admin_19_people_service_accounts');

    // 20. 5.2 People - Access Reviews
    await captureMultiRes('/administration/people?tab=access-reviews', 'admin_20_people_access_reviews');

    // 21. Modal - Create Organization
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto(`http://localhost:${PORT}/administration/enterprise?tab=organizations`, { waitUntil: 'networkidle' });
    await page.click('button:has-text("Create Organization")');
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, 'admin_21_modal_create_org.png') });

    // 22. Modal - Invite User
    await page.goto(`http://localhost:${PORT}/administration/people?tab=users`, { waitUntil: 'networkidle' });
    await page.click('button:has-text("Invite User")');
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, 'admin_22_modal_invite_user.png') });

    // 23. Modal - Request JIT
    await page.goto(`http://localhost:${PORT}/administration/people?tab=jit`, { waitUntil: 'networkidle' });
    await page.click('button:has-text("Request JIT Elevation")');
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, 'admin_23_modal_request_jit.png') });

    console.log('All Playwright verification captures complete!');
    await browser.close();
  } catch (err) {
    console.error('Playwright capture error:', err);
  } finally {
    server.close();
    process.exit(0);
  }
});
