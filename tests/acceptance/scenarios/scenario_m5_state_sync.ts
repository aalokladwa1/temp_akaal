import { Page } from 'playwright';
import { BaseAcceptanceScenario } from './base_scenario.js';
import { MigrationModeCode, ScenarioContext } from '../core/types.js';

export class ScenarioM5StateSync extends BaseAcceptanceScenario {
  public readonly scenarioId = 'P8_ACC_M5_STATE_SYNC';
  public readonly mode: MigrationModeCode = 'M5_STATE_SYNC';

  protected async runJourney(page: Page, context: ScenarioContext): Promise<void> {
    await this.traverseCommonWizard(page, context);
    this.evidence?.log('INFO', 'M5 State-Based Sync scenario initialized.');
  }
}
