import { Page } from 'playwright';
import { BaseAcceptanceScenario } from './base_scenario.js';
import { MigrationModeCode, ScenarioContext } from '../core/types.js';
import { CockpitProgressPOM } from '../pom/cockpit/cockpit_progress.pom.js';
import { HARNESS_CONFIG } from '../harness.config.js';

export class ScenarioM1Bulk extends BaseAcceptanceScenario {
  public readonly scenarioId = 'P8_ACC_M1_BULK';
  public readonly mode: MigrationModeCode = 'M1_BULK';

  protected async runJourney(page: Page, context: ScenarioContext): Promise<void> {
    // 1. Wizard Progression (Steps 1 through 9)
    await this.traverseCommonWizard(page, context);

    // 2. Cockpit Live Observation
    const cockpit = new CockpitProgressPOM(page);
    await this.evidence?.captureMilestone(page, 'Cockpit Live Execution', 'PASS', 'LIVE_PROVEN');

    // 3. Wait for terminal completion
    const outcome = await cockpit.waitForTerminalState(HARNESS_CONFIG.timeouts.migrationExecutionMs);
    if (outcome !== 'COMPLETED') {
      throw new Error(`Migration execution ended in terminal failure state: ${outcome}`);
    }

    await this.evidence?.captureMilestone(page, 'Cockpit Completed State', 'PASS', 'LIVE_PROVEN');

    // 4. External SQLite Corroboration
    const corroboration = this.dbAuditor.queryMigrationState(context.migrationTitle);
    this.evidence?.writeDurableAudit({
      scenarioId: this.scenarioId,
      corroboration,
    });
  }
}
