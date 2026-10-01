import { Page } from 'playwright';
import { BaseAcceptanceScenario } from './base_scenario.js';
import { MigrationModeCode, ScenarioContext } from '../core/types.js';

export class ScenarioM3Cdc extends BaseAcceptanceScenario {
  public readonly scenarioId = 'P8_ACC_M3_CDC';
  public readonly mode: MigrationModeCode = 'M3_CDC';

  protected async runJourney(page: Page, context: ScenarioContext): Promise<void> {
    await this.traverseCommonWizard(page, context);
    this.evidence?.log('INFO', 'M3 Pure CDC streaming scenario initialized.');
  }
}
