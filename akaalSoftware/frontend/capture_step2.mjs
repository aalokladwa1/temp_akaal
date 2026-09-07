import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from './node_modules/@playwright/test/index.js';

const DIST_DIR = './dist/akaal-software/browser';
const OUT_DIR = 'C:/Users/AALOK/.gemini/antigravity/brain/f8de0286-7b06-4fcc-be55-80e48d218a00';
const PORT = 4299;

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

  const browser = await chromium.launch({ headless: true });

  const viewports = [
    { name: '1920x1080', width: 1920, height: 1080 },
    { name: '1440x900', width: 1440, height: 900 }
  ];

  for (const vp of viewports) {
    console.log(`Capturing for viewport: ${vp.name}...`);
    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height }
    });
    const page = await context.newPage();

    // 1. Navigate to Create Validation
    await page.goto(`http://localhost:${PORT}/migration/validation/new`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);

    // Step 1: Fill name so step 1 is valid
    const nameInput = page.locator('input[placeholder*="Customer Ledger"]');
    await nameInput.fill('Oracle to Postgres Core Parity');
    await page.waitForTimeout(300);

    // Click Continue to Source (Step 2)
    const continueBtn = page.locator('button:has-text("Continue to Source")');
    await continueBtn.click();
    await page.waitForTimeout(600);

    // Screenshot 1: Step 2 Hero Selection (Saved vs New)
    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_07_step2_hero_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_07_step2_hero_${vp.name}.png`);

    // Click "Saved Connection" hero card
    const savedCard = page.locator('button:has-text("Saved Connection")').first();
    await savedCard.click();
    await page.waitForTimeout(500);

    // Screenshot 2: Step 2 Saved Grid
    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_08_step2_saved_grid_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_08_step2_saved_grid_${vp.name}.png`);

    // Click Filter button to open filter popover
    const filterBtn = page.locator('button:has-text("Filter")').first();
    await filterBtn.click();
    await page.waitForTimeout(400);

    // Screenshot 3: Step 2 Filter Popover Open
    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_09_step2_filter_popover_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_09_step2_filter_popover_${vp.name}.png`);

    // Close Filter popover
    await filterBtn.click();
    await page.waitForTimeout(300);

    // Select Aurora Postgres connection card
    const pgCard = page.locator('div:has-text("AWS Aurora PostgreSQL Cluster")').last();
    await pgCard.click();
    await page.waitForTimeout(500);

    // Screenshot 4: Step 2 Saved Connection Selected (Green Banner)
    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_10_step2_saved_selected_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_10_step2_saved_selected_${vp.name}.png`);

    // Switch to "New Connection" via top-right segmented control
    const newSegment = page.locator('app-segmented-control button:has-text("New Connection")');
    await newSegment.click();
    await page.waitForTimeout(500);

    // Screenshot 5: Step 2 New Connection 28-Engine Catalog
    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_11_step2_catalog_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_11_step2_catalog_${vp.name}.png`);

    // Select Oracle Database engine card
    const oracleEngine = page.locator('button:has-text("Oracle Database")');
    await oracleEngine.click();
    await page.waitForTimeout(500);

    // Screenshot 6: Step 2 Oracle Dynamic Form
    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_12_step2_oracle_form_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_12_step2_oracle_form_${vp.name}.png`);

    // Expand Network Route accordion & TLS accordion
    const routeAccordion = page.locator('app-accordion:has-text("Network Route") button').first();
    await routeAccordion.click();
    await page.waitForTimeout(300);

    const tlsAccordion = page.locator('app-accordion:has-text("TLS & Transport Encryption") button').first();
    await tlsAccordion.click();
    await page.waitForTimeout(400);

    // Screenshot 7: Step 2 Accordions Open
    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_13_step2_accordions_open_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_13_step2_accordions_open_${vp.name}.png`);

    // Change Engine to PostgreSQL
    const changeEngineBtn = page.locator('button:has-text("Change Engine")');
    await changeEngineBtn.click();
    await page.waitForTimeout(400);

    const pgEngine = page.locator('button:has-text("PostgreSQL")').first();
    await pgEngine.click();
    await page.waitForTimeout(400);

    // Fill PostgreSQL required parameters
    const hostInput = page.locator('#field-host');
    await hostInput.fill('aurora-pg.prod.internal');

    const portInput = page.locator('#field-port');
    await portInput.fill('5432');

    const dbInput = page.locator('#field-database');
    await dbInput.fill('banking_core');

    const userInput = page.locator('#field-username');
    await userInput.fill('akaal_validator');

    const passInput = page.locator('#field-password, #field-secret_ref');
    await passInput.fill('vault://secret/prod/pg/akaal_val');

    await page.waitForTimeout(300);

    // Click "Verify Connection"
    const verifyBtn = page.locator('button:has-text("Verify Connection")');
    await verifyBtn.click();

    // Wait for the 7-phase probe to complete (~1.5s)
    await page.waitForTimeout(2000);

    // Screenshot 8: Step 2 Verified with 7 check chips & save to vault
    await page.screenshot({
      path: path.join(OUT_DIR, `validation_create_14_step2_postgres_verified_${vp.name}.png`),
      fullPage: false
    });
    console.log(`Saved: validation_create_14_step2_postgres_verified_${vp.name}.png`);

    await context.close();
  }

  await browser.close();
  server.close();
  console.log('All screenshots captured successfully!');
  process.exit(0);
});
