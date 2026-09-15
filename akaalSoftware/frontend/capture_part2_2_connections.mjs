import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve('a:/temp_akaal/akaalSoftware/frontend/dist/akaal-software/browser');
const outDir = path.resolve('C:/Users/AALOK/.gemini/antigravity/brain/bff7a30e-4864-4520-934b-ab0cddc46aeb/part2_2_connections_captures');

if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

// Static HTTP server for Angular SPA with base-href rewrite
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
      if (path.extname(filePath).toLowerCase() === '.html') {
        let html = content.toString('utf-8');
        html = html.replace('<base href="./">', '<base href="/">');
        res.writeHead(200, { 'Content-Type': contentType });
        res.end(html, 'utf-8');
      } else {
        res.writeHead(200, { 'Content-Type': contentType });
        res.end(content);
      }
    }
  });
});

const PORT = 4370;
server.listen(PORT, async () => {
  console.log(`Static server listening on http://localhost:${PORT}`);

  const browser = await chromium.launch({ headless: true, channel: 'msedge' });

  const viewports = [
    { name: '1920x1080', width: 1920, height: 1080 },
    { name: '1440x900', width: 1440, height: 900 },
    { name: '1280x800', width: 1280, height: 800 },
    { name: '1024x768', width: 1024, height: 768 }
  ];

  for (const vp of viewports) {
    console.log(`\n========================================`);
    console.log(`Capturing at resolution ${vp.name}...`);
    console.log(`========================================`);

    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
      deviceScaleFactor: 1
    });
    const page = await context.newPage();

    // 1. CONNECTIONS HOME — DISCONNECTED / NEUTRAL STARTUP STATE
    await page.goto(`http://localhost:${PORT}/connections`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.screenshot({
      path: path.join(outDir, `01_conn_home_disconnected_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Captured 01_conn_home_disconnected_${vp.name}.png`);

    // 2. CONNECTIONS HOME — POPULATED STATE (via loadFixturesForTesting)
    await page.evaluate(() => {
      if (window.__CONNECTIONS_SERVICE__) {
        window.__CONNECTIONS_SERVICE__.loadFixturesForTesting();
      }
    });
    await page.waitForTimeout(600);
    await page.screenshot({
      path: path.join(outDir, `02_conn_home_populated_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Captured 02_conn_home_populated_${vp.name}.png`);

    // 3. CONNECTIONS HOME — FILTER: NEEDS ATTENTION
    const attentionCard = page.locator('text=Needs Attention').first();
    if (await attentionCard.isVisible()) {
      await attentionCard.click();
      await page.waitForTimeout(400);
      await page.screenshot({
        path: path.join(outDir, `03_conn_home_filter_needs_attention_${vp.name}.png`),
        fullPage: false
      });
      console.log(`Captured 03_conn_home_filter_needs_attention_${vp.name}.png`);
      // Reset filter
      const totalCard = page.locator('text=Total Inventory').first();
      if (await totalCard.isVisible()) {
        await totalCard.click();
        await page.waitForTimeout(300);
      }
    }

    // 4. CONNECTIONS HOME — SLIDE-OVER INSPECT DRAWER
    await page.evaluate(() => {
      if (window.__CONNECTIONS_SERVICE__) {
        const firstConn = window.__CONNECTIONS_SERVICE__.connections()[0];
        if (firstConn) {
          window.__CONNECTIONS_SERVICE__.openInspectDrawer(firstConn);
        }
      }
    });
    await page.waitForTimeout(600);
    await page.screenshot({
      path: path.join(outDir, `04_conn_home_inspect_drawer_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Captured 04_conn_home_inspect_drawer_${vp.name}.png`);

    // Close drawer
    await page.evaluate(() => {
      if (window.__CONNECTIONS_SERVICE__) {
        window.__CONNECTIONS_SERVICE__.closeInspectDrawer();
      }
    });
    await page.waitForTimeout(300);

    // 5. CREATE CONNECTION WIZARD — STEP 1: PROVIDER SELECTION
    await page.goto(`http://localhost:${PORT}/connections/new`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(700);
    await page.screenshot({
      path: path.join(outDir, `05_wizard_step1_provider_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Captured 05_wizard_step1_provider_${vp.name}.png`);

    // 6. CREATE CONNECTION WIZARD — STEP 2: CONNECTION PARAMETERS
    await page.evaluate(() => {
      if (window.__CREATE_CONN_SERVICE__) {
        window.__CREATE_CONN_SERVICE__.selectProvider('postgresql');
        window.__CREATE_CONN_SERVICE__.goToStep(2);
      }
    });
    await page.waitForTimeout(500);
    await page.screenshot({
      path: path.join(outDir, `06_wizard_step2_connection_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Captured 06_wizard_step2_connection_${vp.name}.png`);

    // 7. CREATE CONNECTION WIZARD — STEP 3: SECURITY & NETWORK
    await page.evaluate(() => {
      if (window.__CREATE_CONN_SERVICE__) {
        window.__CREATE_CONN_SERVICE__.goToStep(3);
      }
    });
    await page.waitForTimeout(500);
    await page.screenshot({
      path: path.join(outDir, `07_wizard_step3_security_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Captured 07_wizard_step3_security_${vp.name}.png`);

    // 8. CREATE CONNECTION WIZARD — STEP 4: CAPABILITIES & VERIFICATION PROBES (Truthful Notice)
    await page.evaluate(() => {
      if (window.__CREATE_CONN_SERVICE__) {
        window.__CREATE_CONN_SERVICE__.goToStep(4);
      }
    });
    await page.waitForTimeout(500);
    const testProbeBtn = page.locator('button:has-text("Test Connection")').first();
    if (await testProbeBtn.isVisible()) {
      await testProbeBtn.click();
      await page.waitForTimeout(400);
    }
    await page.screenshot({
      path: path.join(outDir, `08_wizard_step4_capabilities_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Captured 08_wizard_step4_capabilities_${vp.name}.png`);

    // 9. CREATE CONNECTION WIZARD — STEP 5: REVIEW & CREATE (Truthful Notice)
    await page.evaluate(() => {
      if (window.__CREATE_CONN_SERVICE__) {
        window.__CREATE_CONN_SERVICE__.goToStep(5);
      }
    });
    await page.waitForTimeout(500);
    const submitBtn = page.locator('button:has-text("Create Connection Profile")').first();
    if (await submitBtn.isVisible()) {
      await submitBtn.click();
      await page.waitForTimeout(400);
    }
    await page.screenshot({
      path: path.join(outDir, `09_wizard_step5_review_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Captured 09_wizard_step5_review_${vp.name}.png`);

    // 10. WORKSPACE — TAB 1: OVERVIEW
    await page.goto(`http://localhost:${PORT}/connections/conn-ora-rac-01/overview`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(700);
    await page.screenshot({
      path: path.join(outDir, `10_workspace_tab1_overview_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Captured 10_workspace_tab1_overview_${vp.name}.png`);

    // 11. WORKSPACE — TAB 2: CONFIGURATION (READ MODE)
    await page.evaluate(() => {
      if (window.__WORKSPACE_SERVICE__) {
        window.__WORKSPACE_SERVICE__.setActiveTab('configuration');
      }
    });
    await page.waitForTimeout(500);
    await page.screenshot({
      path: path.join(outDir, `11_workspace_tab2_config_read_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Captured 11_workspace_tab2_config_read_${vp.name}.png`);

    // 12. WORKSPACE — TAB 2: CONFIGURATION (EDIT MODE)
    await page.evaluate(() => {
      if (window.__WORKSPACE_SERVICE__) {
        window.__WORKSPACE_SERVICE__.startEditingConfig();
      }
    });
    await page.waitForTimeout(500);
    await page.screenshot({
      path: path.join(outDir, `12_workspace_tab2_config_edit_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Captured 12_workspace_tab2_config_edit_${vp.name}.png`);

    // Cancel edit
    await page.evaluate(() => {
      if (window.__WORKSPACE_SERVICE__) {
        window.__WORKSPACE_SERVICE__.cancelEditingConfig();
      }
    });
    await page.waitForTimeout(200);

    // 13. WORKSPACE — TAB 3: CAPABILITIES
    await page.evaluate(() => {
      if (window.__WORKSPACE_SERVICE__) {
        window.__WORKSPACE_SERVICE__.setActiveTab('capabilities');
      }
    });
    await page.waitForTimeout(500);
    await page.screenshot({
      path: path.join(outDir, `13_workspace_tab3_capabilities_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Captured 13_workspace_tab3_capabilities_${vp.name}.png`);

    // 14. WORKSPACE — TAB 4: USAGE & DEPENDENCY GOVERNANCE
    await page.evaluate(() => {
      if (window.__WORKSPACE_SERVICE__) {
        window.__WORKSPACE_SERVICE__.setActiveTab('usage');
      }
    });
    await page.waitForTimeout(500);
    await page.screenshot({
      path: path.join(outDir, `14_workspace_tab4_usage_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Captured 14_workspace_tab4_usage_${vp.name}.png`);

    // 15. WORKSPACE — TAB 5: ACTIVITY AUDIT LOG
    await page.evaluate(() => {
      if (window.__WORKSPACE_SERVICE__) {
        window.__WORKSPACE_SERVICE__.setActiveTab('activity');
      }
    });
    await page.waitForTimeout(500);
    await page.screenshot({
      path: path.join(outDir, `15_workspace_tab5_activity_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Captured 15_workspace_tab5_activity_${vp.name}.png`);

    // 16. WORKSPACE — TAB 6: SETTINGS & GOVERNED LIFECYCLE
    await page.evaluate(() => {
      if (window.__WORKSPACE_SERVICE__) {
        window.__WORKSPACE_SERVICE__.setActiveTab('settings');
      }
    });
    await page.waitForTimeout(500);
    await page.screenshot({
      path: path.join(outDir, `16_workspace_tab6_settings_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Captured 16_workspace_tab6_settings_${vp.name}.png`);

    // 17. WORKSPACE — NOT_FOUND STATE (Truthful Zero-Fallback B-2.2-02)
    await page.goto(`http://localhost:${PORT}/connections/unknown-nonexistent-id/overview`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(700);
    await page.screenshot({
      path: path.join(outDir, `17_workspace_not_found_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Captured 17_workspace_not_found_${vp.name}.png`);

    await context.close();
  }

  await browser.close();
  server.close(() => {
    console.log('\nAll captures successfully completed across 4 viewports!');
    process.exit(0);
  });
});
