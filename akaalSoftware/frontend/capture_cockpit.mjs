import http from 'http';
import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const distDir = path.resolve('a:/temp_akaal/akaalSoftware/frontend/dist/akaal-software/browser');
const outDir = path.resolve('C:/Users/AALOK/.gemini/antigravity/brain/f8de0286-7b06-4fcc-be55-80e48d218a00');
const studyDir = path.join(outDir, 'study');

if (!fs.existsSync(studyDir)) {
  fs.mkdirSync(studyDir, { recursive: true });
}

// Static HTTP server for Angular SPA
const server = http.createServer((req, res) => {
  let reqPath = req.url.split('?')[0];
  if (reqPath === '/' || reqPath === '') reqPath = '/index.html';
  
  let filePath = path.join(distDir, reqPath);
  if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    filePath = path.join(distDir, 'index.html');
  }

  const ext = path.extname(filePath).toLowerCase();
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

  const contentType = mimeTypes[ext] || 'application/octet-stream';
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

server.listen(4298, async () => {
  console.log('Static server listening on http://localhost:4298');

  const browser = await chromium.launch({ headless: true, channel: 'msedge' });

  const resolutions = [
    { name: '1920x1080', width: 1920, height: 1080 },
    { name: '1440x900', width: 1440, height: 900 }
  ];

  for (const res of resolutions) {
    const page = await browser.newPage({ viewport: { width: res.width, height: res.height } });
    await page.goto('http://localhost:4298/cockpit');
    await page.waitForLoadState('networkidle');
    await page.waitForFunction(() => typeof window.__cockpitStore !== 'undefined', { timeout: 10000 });

    const saveScreenshot = async (name) => {
      const fileName = `${name}_${res.name}.png`;
      const rootPath = path.join(outDir, fileName);
      const studyPath = path.join(studyDir, fileName);
      await page.screenshot({ path: rootPath });
      fs.copyFileSync(rootPath, studyPath);
      console.log(`Saved screenshot: ${fileName}`);

      // Also capture middle zone (DAG & Activity)
      await page.evaluate(() => {
        const main = document.querySelector('main');
        if (main) main.scrollTop = 550;
      });
      await page.waitForTimeout(150);
      const midFileName = `${name}_mid_${res.name}.png`;
      const midRootPath = path.join(outDir, midFileName);
      const midStudyPath = path.join(studyDir, midFileName);
      await page.screenshot({ path: midRootPath });
      fs.copyFileSync(midRootPath, midStudyPath);

      // Also capture Operational Workbench zone
      await page.evaluate(() => {
        const main = document.querySelector('main');
        if (main) main.scrollTop = 950;
      });
      await page.waitForTimeout(150);
      const wbFileName = `${name}_workbench_${res.name}.png`;
      const wbRootPath = path.join(outDir, wbFileName);
      const wbStudyPath = path.join(studyDir, wbFileName);
      await page.screenshot({ path: wbRootPath });
      fs.copyFileSync(wbRootPath, wbStudyPath);

      // Also capture scrolled lower zone
      await page.evaluate(() => {
        const main = document.querySelector('main');
        if (main) main.scrollTop = main.scrollHeight;
      });
      await page.waitForTimeout(150);
      const lowerFileName = `${name}_lower_${res.name}.png`;
      const lowerRootPath = path.join(outDir, lowerFileName);
      const lowerStudyPath = path.join(studyDir, lowerFileName);
      await page.screenshot({ path: lowerRootPath });
      fs.copyFileSync(lowerRootPath, lowerStudyPath);

      // Scroll back up
      await page.evaluate(() => {
        const main = document.querySelector('main');
        if (main) main.scrollTop = 0;
      });
    };

    // 1. Scenario 1: M1 Bulk Running
    await page.evaluate(() => {
      const store = window.__cockpitStore;
      store.setSessionState({
        mode: 'M1_BULK',
        name: 'Enterprise Historical Data Migration',
        sourceProvider: 'Oracle',
        targetProvider: 'PostgreSQL',
        lifecycleState: 'RUNNING',
        currentStage: 'Parallel Bulk Table Extraction & Load',
        activeTaskDescription: 'Copying GL_BALANCES · Partition 12/24',
        activeEntityName: 'GL_BALANCES',
        rowsProcessed: 310000000,
        rowsTotal: 450000000,
        progressPercent: 68.9,
        throughputRowsSec: 284000,
        throughputRowsSecFormatted: '284K',
        throughputBytesSecFormatted: '1.18 GB/s',
        etaString: '08:14',
        elapsedTimeString: '00:54:12',
        activeWorkers: 16,
        isHealthDegraded: false
      });
      store.setActiveWorkbenchTab('data_movement');
      store.selectDagNode(null);
      store.toggleFullDagModal(false);
      store.cancelPendingAction();
    });
    await page.waitForTimeout(400);
    await saveScreenshot('cockpit_01_mode_m1_bulk_running');

    // 2. Scenario 2: M2 Bulk + CDC Running
    await page.evaluate(() => {
      const store = window.__cockpitStore;
      store.setSessionState({
        mode: 'M2_BULK_CDC',
        name: 'Core Banking Ledger Migration',
        sourceProvider: 'Oracle',
        targetProvider: 'PostgreSQL',
        lifecycleState: 'RUNNING',
        currentStage: 'Parallel Bulk Table Extraction & Load',
        activeTaskDescription: 'Copying CUSTOMER_LEDGER · Partition 18/32',
        activeEntityName: 'CUSTOMER_LEDGER',
        rowsProcessed: 418700000,
        rowsTotal: 600000000,
        progressPercent: 69.8,
        throughputRowsSec: 327000,
        throughputRowsSecFormatted: '327K',
        throughputBytesSecFormatted: '1.42 GB/s',
        cdcLagMs: 12,
        backlogMbFormatted: '14.2 MB',
        applyTxSecFormatted: '38.4K',
        convergenceState: 'CONVERGED',
        checkpointFreshness: '1.2s',
        etaString: '09:18',
        elapsedTimeString: '01:18:42',
        activeWorkers: 16,
        isHealthDegraded: false
      });
      store.setActiveWorkbenchTab('cdc_convergence');
    });
    await page.waitForTimeout(400);
    await saveScreenshot('cockpit_02_mode_m2_bulk_cdc_running');

    // 3. Scenario 3: M3 CDC Continuous Stream
    await page.evaluate(() => {
      const store = window.__cockpitStore;
      store.setSessionState({
        mode: 'M3_CDC',
        name: 'Real-Time Financial Transaction Pipeline',
        sourceProvider: 'Oracle',
        targetProvider: 'PostgreSQL',
        lifecycleState: 'RUNNING',
        currentStage: 'Continuous Change Streaming & Convergence',
        activeTaskDescription: 'Applying transaction stream batch #81,204',
        activeEntityName: 'TRANSACTION_LOG_STREAM',
        cdcLagMs: 4,
        backlogMbFormatted: '1.2 MB',
        applyTxSecFormatted: '52.1K',
        convergenceState: 'CONVERGED',
        checkpointFreshness: '0.8s',
        elapsedTimeString: '06:42:15',
        activeWorkers: 8,
        isHealthDegraded: false
      });
      store.setActiveWorkbenchTab('cdc_convergence');
    });
    await page.waitForTimeout(400);
    await saveScreenshot('cockpit_03_mode_m3_cdc_continuous');

    // 4. Scenario 4: M4 Incremental Polling
    await page.evaluate(() => {
      const store = window.__cockpitStore;
      store.setSessionState({
        mode: 'M4_INCREMENTAL',
        name: 'Warehouse Daily Delta Ingestion',
        sourceProvider: 'SQL Server',
        targetProvider: 'Snowflake',
        lifecycleState: 'RUNNING',
        currentStage: 'Incremental High-Watermark Polling',
        activeTaskDescription: 'Polling modified records since 2026-09-06 14:00:00 UTC',
        activeEntityName: 'SALES_ORDERS_DELTA',
        elapsedTimeString: '02:05:00',
        activeWorkers: 6,
        isHealthDegraded: false
      });
      store.setActiveWorkbenchTab('incremental_polling');
    });
    await page.waitForTimeout(400);
    await saveScreenshot('cockpit_04_mode_m4_incremental_polling');

    // 5. Scenario 5: M5 State Sync
    await page.evaluate(() => {
      const store = window.__cockpitStore;
      store.setSessionState({
        mode: 'M5_STATE_SYNC',
        name: 'Customer Master Multi-Master Reconciliation',
        sourceProvider: 'PostgreSQL',
        targetProvider: 'PostgreSQL',
        lifecycleState: 'RUNNING',
        currentStage: 'Active Multi-Master State Reconciliation',
        activeTaskDescription: 'Executing cycle #14 reconciliation against shard 03',
        activeEntityName: 'CUSTOMER_MASTER_SHARD_03',
        elapsedTimeString: '03:12:44',
        activeWorkers: 8,
        isHealthDegraded: false
      });
      store.setActiveWorkbenchTab('state_sync');
    });
    await page.waitForTimeout(400);
    await saveScreenshot('cockpit_05_mode_m5_state_sync');

    // 6. Scenario 6: M6 Schema Only
    await page.evaluate(() => {
      const store = window.__cockpitStore;
      store.setSessionState({
        mode: 'M6_SCHEMA_ONLY',
        name: 'Enterprise DDL & Stored Procedure Transpilation',
        sourceProvider: 'Oracle',
        targetProvider: 'PostgreSQL',
        lifecycleState: 'RUNNING',
        currentStage: 'DDL Generation & Target Schema Execution',
        activeTaskDescription: 'Applying DDL: CREATE TABLE ACCOUNTS_LEDGER',
        activeEntityName: 'ACCOUNTS_LEDGER',
        elapsedTimeString: '00:04:18',
        activeWorkers: 4,
        isHealthDegraded: false
      });
      store.setActiveWorkbenchTab('schema_execution');
    });
    await page.waitForTimeout(400);
    await saveScreenshot('cockpit_06_mode_m6_schema_only');

    // 7. Scenario 7: M7 Data Only
    await page.evaluate(() => {
      const store = window.__cockpitStore;
      store.setSessionState({
        mode: 'M7_DATA_ONLY',
        name: 'High-Throughput Analytics Table Seed',
        sourceProvider: 'MySQL',
        targetProvider: 'ClickHouse',
        lifecycleState: 'RUNNING',
        currentStage: 'Pre-Created Target Table Data Population',
        activeTaskDescription: 'Streaming clickstream_events partitions into ClickHouse MergeTree',
        activeEntityName: 'clickstream_events',
        rowsProcessed: 890000000,
        rowsTotal: 1200000000,
        progressPercent: 74.2,
        throughputRowsSec: 512000,
        throughputRowsSecFormatted: '512K',
        throughputBytesSecFormatted: '2.34 GB/s',
        etaString: '10:05',
        elapsedTimeString: '01:45:30',
        activeWorkers: 24,
        isHealthDegraded: false
      });
      store.setActiveWorkbenchTab('data_movement');
    });
    await page.waitForTimeout(400);
    await saveScreenshot('cockpit_07_mode_m7_data_only');

    // 8. Scenario 8: Approval Barrier Promoted
    await page.evaluate(() => {
      const store = window.__cockpitStore;
      store.setSessionState({
        mode: 'M2_BULK_CDC',
        name: 'Core Banking Ledger Migration',
        lifecycleState: 'WAITING_FOR_APPROVAL',
        currentStage: 'Cutover Approval Barrier',
        activeTaskDescription: 'Source writes quiesced. CDC converged (12ms lag). Awaiting Dual DBA / SecOps sign-off.',
        isHealthDegraded: false
      });
      store.setActiveWorkbenchTab('data_movement');
    });
    await page.waitForTimeout(400);
    await saveScreenshot('cockpit_08_approval_barrier_promoted');

    // 9. Scenario 9: Paused Operator Hold
    await page.evaluate(() => {
      const store = window.__cockpitStore;
      store.setSessionState({
        mode: 'M2_BULK_CDC',
        name: 'Core Banking Ledger Migration',
        lifecycleState: 'PAUSED',
        currentStage: 'Replication Checkpointed & Workers Idled',
        activeTaskDescription: 'State persisted at durable Checkpoint #48,210. Ready for resume.',
        isHealthDegraded: false
      });
      store.setActiveWorkbenchTab('checkpoint_recovery');
    });
    await page.waitForTimeout(400);
    await saveScreenshot('cockpit_09_paused_operator_hold');

    // 10. Scenario 10: Execution Failure & Recovery
    await page.evaluate(() => {
      const store = window.__cockpitStore;
      store.setSessionState({
        mode: 'M2_BULK_CDC',
        name: 'Core Banking Ledger Migration',
        lifecycleState: 'FAILED',
        currentStage: 'Parallel Bulk Table Extraction & Load',
        activeTaskDescription: 'Worker thread pool exhausted available connections. Operator action required.',
        isHealthDegraded: false
      });
      store.setActiveWorkbenchTab('retry_throttling');
    });
    await page.waitForTimeout(400);
    await saveScreenshot('cockpit_10_execution_failure_state');

    // 11. Scenario 11: Subsystem Degraded Alert
    await page.evaluate(() => {
      const store = window.__cockpitStore;
      store.setSessionState({
        mode: 'M2_BULK_CDC',
        name: 'Core Banking Ledger Migration',
        lifecycleState: 'RUNNING',
        currentStage: 'Parallel Bulk Table Extraction & Load',
        activeTaskDescription: 'Copying CUSTOMER_LEDGER · Partition 18/32',
        isHealthDegraded: true
      });
      store.setActiveWorkbenchTab('workers_pool');
    });
    await page.waitForTimeout(400);
    await saveScreenshot('cockpit_11_subsystem_degraded');

    // 12. Scenario 12: DAG Node Selected
    await page.evaluate(() => {
      const store = window.__cockpitStore;
      store.setSessionState({
        lifecycleState: 'RUNNING',
        isHealthDegraded: false
      });
      const topology = store.runtimeDag();
      if (topology.nodes.length > 2) {
        store.selectDagNode(topology.nodes[2].id);
      }
    });
    await page.waitForTimeout(400);
    await saveScreenshot('cockpit_12_dag_node_selected');

    // 13. Scenario 13: Full DAG Modal Open
    await page.evaluate(() => {
      const store = window.__cockpitStore;
      store.toggleFullDagModal(true);
    });
    await page.waitForTimeout(400);
    await saveScreenshot('cockpit_13_full_dag_modal');

    // 14. Scenario 14: Action Confirmation Modal
    await page.evaluate(() => {
      const store = window.__cockpitStore;
      store.toggleFullDagModal(false);
      store.triggerAction('TERMINATE');
    });
    await page.waitForTimeout(400);
    await saveScreenshot('cockpit_14_action_confirmation_modal');

    // 15. Scenario 15: Events Audit Trail Category Filtered
    await page.evaluate(() => {
      const store = window.__cockpitStore;
      store.cancelPendingAction();
      store.setEventFilter('STAGE');
      store.setActiveWorkbenchTab('execution_sites');
    });
    await page.waitForTimeout(400);
    await saveScreenshot('cockpit_15_events_audit_dock');

    await page.close();
  }

  await browser.close();
  server.close();
  console.log('Finished capturing all 15 operational scenarios successfully.');
  process.exit(0);
});
