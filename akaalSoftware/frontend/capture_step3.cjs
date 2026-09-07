const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('@playwright/test');

const DIST_DIR = path.join(__dirname, 'dist', 'akaal-software', 'browser');
const OUT_DIR = 'C:/Users/AALOK/.gemini/antigravity/brain/f8de0286-7b06-4fcc-be55-80e48d218a00';
const PORT = 4310;

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
    // SPA fallback
    const indexPath = path.join(DIST_DIR, 'index.html');
    res.writeHead(200, { 'Content-Type': 'text/html' });
    fs.createReadStream(indexPath).pipe(res);
  }
});

server.listen(PORT, async () => {
  console.log(`Server listening on http://localhost:${PORT}`);

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
    console.log(`Capturing Step 3 for viewport: ${vp.name}...`);
    console.log(`========================================\n`);

    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height }
    });
    const page = await context.newPage();

    // 1. Navigate to Create Validation
    await page.goto(`http://localhost:${PORT}/migration/validation/new`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);

    // Step 1: Fill name
    const nameInput = page.locator('#step1-validation-name');
    await nameInput.fill('Core Banking Ledger Parity');
    await page.waitForTimeout(200);

    // Click Continue to Source (Step 2)
    const continueToSourceBtn = page.locator('button:has-text("Continue to Source")');
    await continueToSourceBtn.click();
    await page.waitForTimeout(400);

    // Step 2: Select Oracle saved connection (conn-01)
    const savedCard = page.locator('button:has-text("Saved Connection")').first();
    await savedCard.click();
    await page.waitForTimeout(300);

    const oracleConnCard = page.locator('div:has-text("Oracle 19c Enterprise RAC")').last();
    await oracleConnCard.click();
    await page.waitForTimeout(300);

    // Continue to Target (Step 3)
    const continueToTargetBtn = page.locator('button:has-text("Continue to Target")');
    await continueToTargetBtn.click();
    await page.waitForTimeout(600);

    // -------------------------------------------------------------------------
    // Screenshot 1: Step 3 Hero Selection Opening (Saved vs New)
    // -------------------------------------------------------------------------
    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_15_step3_hero_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_15_step3_hero_${vp.name}.png`);

    // -------------------------------------------------------------------------
    // Screenshot 2: Step 3 Saved Grid
    // -------------------------------------------------------------------------
    const step3SavedCard = page.locator('button:has-text("Saved Connection")').first();
    await step3SavedCard.click();
    await page.waitForTimeout(500);

    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_16_step3_saved_grid_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_16_step3_saved_grid_${vp.name}.png`);

    // -------------------------------------------------------------------------
    // Screenshot 3: Step 3 Filter Popover Open
    // -------------------------------------------------------------------------
    const filterBtn = page.locator('button:has-text("Filter")').first();
    await filterBtn.click();
    await page.waitForTimeout(400);

    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_17_step3_filter_popover_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_17_step3_filter_popover_${vp.name}.png`);

    // Close filter popover
    await filterBtn.click();
    await page.waitForTimeout(200);

    // -------------------------------------------------------------------------
    // Screenshot 4: Same Endpoint Guard Alert (Select Oracle conn-01 for Target too)
    // -------------------------------------------------------------------------
    const oracleTargetCard = page.locator('div:has-text("Oracle 19c Enterprise RAC")').last();
    await oracleTargetCard.click();
    await page.waitForTimeout(400);

    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_18_step3_same_endpoint_alert_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_18_step3_same_endpoint_alert_${vp.name}.png`);

    // -------------------------------------------------------------------------
    // Screenshot 5: Saved Selected Banner (Select Aurora Postgres conn-02)
    // -------------------------------------------------------------------------
    const auroraPgCard = page.locator('div:has-text("AWS Aurora PostgreSQL Cluster")').last();
    await auroraPgCard.click();
    await page.waitForTimeout(400);

    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_19_step3_saved_selected_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_19_step3_saved_selected_${vp.name}.png`);

    // -------------------------------------------------------------------------
    // Screenshot 6: New Connection Catalog Grid (48 Engines across 7 Categories)
    // -------------------------------------------------------------------------
    const newModeToggle = page.locator('button:has-text("New Connection")').first();
    await newModeToggle.click();
    await page.waitForTimeout(500);

    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_20_step3_catalog_48_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_20_step3_catalog_48_${vp.name}.png`);

    // -------------------------------------------------------------------------
    // Screenshot 7: Selected Target PostgreSQL Dynamic Schema Form
    // -------------------------------------------------------------------------
    const pgEngineCard = page.locator('button:has-text("PostgreSQL")').first();
    await pgEngineCard.click();
    await page.waitForTimeout(500);

    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_21_step3_postgres_form_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_21_step3_postgres_form_${vp.name}.png`);

    // -------------------------------------------------------------------------
    // Screenshot 8: Accordions Expanded (Network Route & TLS)
    // -------------------------------------------------------------------------
    const routeAccordion = page.locator('button:has-text("Network Route & Bastion Configuration")');
    await routeAccordion.click();
    await page.waitForTimeout(200);

    const tlsAccordion = page.locator('button:has-text("Transport Layer Security (TLS) & Certificates")');
    await tlsAccordion.click();
    await page.waitForTimeout(300);

    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_22_step3_accordions_open_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_22_step3_accordions_open_${vp.name}.png`);

    // -------------------------------------------------------------------------
    // Screenshot 9: Live Target Read Probe Verified (Passed with 6 Read Chips)
    // -------------------------------------------------------------------------
    // Fill required PostgreSQL form fields
    const hostInput = page.locator('input[placeholder*="postgres.company.internal"]').first();
    await hostInput.fill('aurora-pg-target.aws.internal');

    const dbInput = page.locator('input[placeholder*="banking_ledger"]').first();
    await dbInput.fill('banking_ledger_target');

    const userInput = page.locator('input[placeholder*="postgres_admin"]').first();
    await userInput.fill('akaal_val_reader');

    const pwdInput = page.locator('input[placeholder*="vault://secret/prod/pg_pass"]').first();
    await pwdInput.fill('vault://secret/prod/target/pg_reader');
    await page.waitForTimeout(300);

    // Scroll the read probe section into view
    const probeBtn = page.locator('button:has-text("Run Target Read Probe")');
    await probeBtn.scrollIntoViewIfNeeded();
    await page.waitForTimeout(300);

    // Click Run Target Read Probe
    await probeBtn.click();

    // Wait for probe to complete (6 phases * 180ms ~ 1.2s)
    await page.waitForTimeout(1600);

    // Check "Save this target connection to the Enterprise Vault"
    const vaultCheckbox = page.locator('input[type="checkbox"]').last();
    await vaultCheckbox.click();
    await page.waitForTimeout(300);

    const vaultNameInput = page.locator('input[placeholder*="Analytics Snowflake Target Production"]');
    await vaultNameInput.fill('Target PostgreSQL Replica Vault');
    await page.waitForTimeout(200);

    const saveVaultBtn = page.locator('button:has-text("Save Connection")');
    await saveVaultBtn.click();
    await page.waitForTimeout(300);

    // Scroll to bottom so probe results and vault confirmation are visible
    await page.evaluate(() => window.scrollTo({ top: document.body.scrollHeight, behavior: 'instant' }));
    await page.waitForTimeout(300);

    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_23_step3_read_probe_verified_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_23_step3_read_probe_verified_${vp.name}.png`);

    await context.close();
  }

  await browser.close();
  server.close();
  console.log('\nAll Step 3 screenshots captured successfully!');
  process.exit(0);
});
