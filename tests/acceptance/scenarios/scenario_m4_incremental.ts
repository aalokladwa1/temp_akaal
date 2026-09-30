import { Page } from 'playwright';
import { BaseAcceptanceScenario } from './base_scenario.js';
import { MigrationModeCode, ScenarioContext } from '../core/types.js';

export class ScenarioM4Incremental extends BaseAcceptanceScenario {
  public readonly scenarioId = 'P8_ACC_M4_INCREMENTAL';
  public readonly mode: MigrationModeCode = 'M4_INCREMENTAL';

  protected async runJourney(page: Page, context: ScenarioContext): Promise<void> {
    await this.traverseCommonWizard(page, context);
    this.evidence?.log('INFO', 'M4 Incremental watermark polling scenario initialized.');
  }
}
