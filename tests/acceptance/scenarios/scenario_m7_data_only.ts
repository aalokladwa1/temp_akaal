import { Page } from 'playwright';
import { BaseAcceptanceScenario } from './base_scenario.js';
import { MigrationModeCode, ScenarioContext } from '../core/types.js';

export class ScenarioM7DataOnly extends BaseAcceptanceScenario {
  public readonly scenarioId = 'P8_ACC_M7_DATA_ONLY';
  public readonly mode: MigrationModeCode = 'M7_DATA_ONLY';

  protected async runJourney(page: Page, context: ScenarioContext): Promise<void> {
    await this.traverseCommonWizard(page, context);
    this.evidence?.log('INFO', 'M7 Data-Only migration pipeline scenario initialized.');
  }
}
