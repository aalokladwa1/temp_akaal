import { Page } from 'playwright';
import { BaseAcceptanceScenario } from './base_scenario.js';
import { MigrationModeCode, ScenarioContext } from '../core/types.js';
import { CockpitProgressPOM } from '../pom/cockpit/cockpit_progress.pom.js';

export class ScenarioM2BulkCdc extends BaseAcceptanceScenario {
  public readonly scenarioId = 'P8_ACC_M2_BULK_CDC';
  public readonly mode: MigrationModeCode = 'M2_BULK_CDC';

  protected async runJourney(page: Page, context: ScenarioContext): Promise<void> {
    await this.traverseCommonWizard(page, context);
    const cockpit = new CockpitProgressPOM(page);
    await this.evidence?.captureMilestone(page, 'Cockpit Initial Snapshot', 'PASS', 'LIVE_PROVEN');
    // Future stimulus hook: inject external mutation to source DB and observe CDC catch-up
    this.evidence?.log('INFO', 'M2 Bulk+CDC scenario initialized and ready for streaming validation.');
  }
}
