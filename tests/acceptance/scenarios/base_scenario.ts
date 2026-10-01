import { Page } from 'playwright';
import { HARNESS_CONFIG } from '../harness.config.js';
import {
  MigrationModeCode,
  ScenarioContext,
  ScenarioRunResult,
  AcceptanceStatus,
  ProofClassification,
} from '../core/types.js';
import { DesktopProcessManager } from '../core/process_manager.js';
import { CdpClient, CdpSession } from '../core/cdp_client.js';
import { EvidenceCollector } from '../core/evidence_collector.js';
import { IntegrityGuard } from '../core/integrity_guard.js';
import { DbAuditor } from '../core/db_auditor.js';
import { SynchronizationHelper } from '../core/synchronization.js';
import { AppShellPOM } from '../pom/app_shell.pom.js';
import { Step1DefinitionPOM } from '../pom/wizard/step1_definition.pom.js';
import { Step2SourcePOM } from '../pom/wizard/step2_source.pom.js';
import { Step3TargetPOM } from '../pom/wizard/step3_target.pom.js';
import { Step4DiscoveryPOM } from '../pom/wizard/step4_discovery.pom.js';
import { Step5MappingPOM } from '../pom/wizard/step5_mapping.pom.js';
import { Step6ConfigPOM } from '../pom/wizard/step6_config.pom.js';
import { Step7PlanPOM } from '../pom/wizard/step7_plan.pom.js';
import { Step8GovernancePOM } from '../pom/wizard/step8_governance.pom.js';
import { Step9ReviewPOM } from '../pom/wizard/step9_review.pom.js';
import { CockpitProgressPOM } from '../pom/cockpit/cockpit_progress.pom.js';

export abstract class BaseAcceptanceScenario {
  public abstract readonly scenarioId: string;
  public abstract readonly mode: MigrationModeCode;

  protected processManager: DesktopProcessManager | null = null;
  protected cdpClient: CdpClient | null = null;
  protected cdpSession: CdpSession | null = null;
  protected evidence: EvidenceCollector | null = null;
  protected dbAuditor: DbAuditor = new DbAuditor();

  public async execute(runId?: string): Promise<ScenarioRunResult> {
    const activeRunId = runId || `${this.scenarioId}_${new Date().toISOString().replace(/[:.]/g, '-')}`;
    this.evidence = new EvidenceCollector(this.scenarioId, this.mode, activeRunId);
    this.processManager = new DesktopProcessManager(activeRunId);
    this.cdpClient = new CdpClient(this.processManager.getCdpPort());

    let finalStatus: AcceptanceStatus = 'FAIL';
    let finalProof: ProofClassification = 'NOT_LIVE_PROVEN';
    let integrityPassed = false;
    let durableVerified = false;

    try {
      this.evidence.log('PHASE', '1. Static Harness Integrity Scan');
      const scanResult = IntegrityGuard.scanHarnessSource();
      if (!scanResult.passed) {
        throw new Error(`Integrity violation in test source: ${scanResult.violations.join('; ')}`);
      }
      integrityPassed = true;
      this.evidence.log('INFO', 'Static integrity scan passed (0 bypasses detected).');

      this.evidence.log('PHASE', '2. Desktop AUT Process Launch');
      const procInfo = await this.processManager.start();
      this.evidence.log('INFO', `AKAAL.exe started with PID ${procInfo.pid} on CDP port ${procInfo.cdpPort}`);

      this.evidence.log('PHASE', '3. Playwright CDP Attachment');
      this.cdpSession = await this.cdpClient.connect();
      const page = this.cdpSession.page;

      this.evidence.log('PHASE', '4. Wails Runtime Attestation');
      await IntegrityGuard.assertWailsRuntimeAttestation(page);
      this.evidence.log('INFO', 'Authentic Wails runtime detected in WebView2 context.');

      this.evidence.log('PHASE', '5. Waiting for Shell & IPC Readiness');
      const ipcReady = await SynchronizationHelper.waitForIpcConnected(page, HARNESS_CONFIG.timeouts.ipcReadinessMs);
      if (!ipcReady) {
        throw new Error('Desktop IPC bridge connection not ready within timeout.');
      }
      this.evidence.log('INFO', 'Desktop IPC bridge connected.');

      const context: ScenarioContext = {
        runId: activeRunId,
        mode: this.mode,
        migrationTitle: `Acceptance ${this.mode} ${activeRunId}`,
        sourceConnectionName: HARNESS_CONFIG.oracle.serviceName || 'Oracle',
        targetConnectionName: 'PostgreSQL',
        selectedTables: [],
        observedDiscoveredTables: [],
        allocatedPort: procInfo.cdpPort,
      };

      // Run the scenario journey
      this.evidence.log('PHASE', '6. Executing Scenario Journey');
      await this.runJourney(page, context);

      finalStatus = 'PASS';
      finalProof = 'LIVE_PROVEN';
      durableVerified = true;
    } catch (err: any) {
      finalStatus = 'FAIL';
      finalProof = 'NOT_LIVE_PROVEN';
      this.evidence?.addBlocker(`Execution failure: ${err.message}`);
      if (this.cdpSession?.page && this.evidence) {
        await this.evidence.captureMilestone(this.cdpSession.page, 'Failure State', 'FAIL', 'NOT_LIVE_PROVEN', {
          error: err.message,
        }).catch(() => {});
      }
    } finally {
      this.evidence?.log('PHASE', '7. Clean Teardown');
      await this.cdpClient?.disconnect().catch(() => {});
      await this.processManager?.stop().catch(() => {});
    }

    const binarySha = this.processManager?.getExecutableSha256();
    return this.evidence!.finalize(finalStatus, finalProof, integrityPassed, durableVerified, binarySha);
  }

  /**
   * Mode-specific workflow steps implemented by each scenario.
   */
  protected abstract runJourney(page: Page, context: ScenarioContext): Promise<void>;

  /**
   * Helper to traverse common Creation Wizard steps 1 to 9.
   */
  protected async traverseCommonWizard(page: Page, context: ScenarioContext): Promise<void> {
    const shell = new AppShellPOM(page);
    const step1 = new Step1DefinitionPOM(page);
    const step2 = new Step2SourcePOM(page);
    const step3 = new Step3TargetPOM(page);
    const step4 = new Step4DiscoveryPOM(page);
    const step5 = new Step5MappingPOM(page);
    const step6 = new Step6ConfigPOM(page);
    const step7 = new Step7PlanPOM(page);
    const step8 = new Step8GovernancePOM(page);
    const step9 = new Step9ReviewPOM(page);

    // Step 1: Definition
    await shell.openCreateMigrationWizard();
    await step1.fillTitle(context.migrationTitle);
    await step1.selectMode(this.mode);
    await this.evidence?.captureMilestone(page, 'Step1 Mode Defined', 'PASS', 'LIVE_PROVEN');
    await step1.continueToStep2();

    // Step 2: Source
    await step2.selectSourceConnection(context.sourceConnectionName);
    await this.evidence?.captureMilestone(page, 'Step2 Source Selected', 'PASS', 'LIVE_PROVEN');
    await step2.continueToStep3();

    // Step 3: Target
    await step3.selectTargetConnection(context.targetConnectionName);
    await this.evidence?.captureMilestone(page, 'Step3 Target Selected', 'PASS', 'LIVE_PROVEN');
    await step3.continueToStep4();

    // Step 4: Discovery (Blind)
    await step4.triggerDiscovery();
    context.observedDiscoveredTables = await step4.observeAndSelectDiscoveredTables(HARNESS_CONFIG.timeouts.discoveryMs);
    this.evidence?.log('DISCOVERY', `Observed tables: ${context.observedDiscoveredTables.join(', ')}`);
    await this.evidence?.captureMilestone(page, 'Step4 Discovery Completed', 'PASS', 'LIVE_PROVEN');
    await step4.continueToStep5();

    // Step 5: Mapping
    const mappingReady = await step5.verifyReadiness();
    if (!mappingReady) throw new Error('Step 5 Mapping validation has unresolved blockers.');
    await this.evidence?.captureMilestone(page, 'Step5 Mapping Verified', 'PASS', 'LIVE_PROVEN');
    await step5.continueToStep6();

    // Step 6: Config
    const configReady = await step6.verifyReadiness();
    if (!configReady) throw new Error('Step 6 Configuration parameters incomplete.');
    await this.evidence?.captureMilestone(page, 'Step6 Config Verified', 'PASS', 'LIVE_PROVEN');
    await step6.continueToStep7();

    // Step 7: Plan
    await step7.verifyPlanCompiled(HARNESS_CONFIG.timeouts.planCompilationMs);
    await this.evidence?.captureMilestone(page, 'Step7 Plan Compiled', 'PASS', 'LIVE_PROVEN');
    await step7.continueToStep8();

    // Step 8: Governance
    await step8.verifyReadiness();
    await this.evidence?.captureMilestone(page, 'Step8 Governance Ready', 'PASS', 'LIVE_PROVEN');
    await step8.continueToStep9();

    // Step 9: Launch
    await this.evidence?.captureMilestone(page, 'Step9 Review Ready', 'PASS', 'LIVE_PROVEN');
    await step9.initializeAndLaunch();
  }
}
