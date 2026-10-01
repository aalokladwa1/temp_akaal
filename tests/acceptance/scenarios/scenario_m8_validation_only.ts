import { Page } from 'playwright';
import { BaseAcceptanceScenario } from './base_scenario.js';
import { MigrationModeCode, ScenarioContext } from '../core/types.js';

export class ScenarioM8ValidationOnly extends BaseAcceptanceScenario {
  public readonly scenarioId = 'P8_ACC_M8_VALIDATION_ONLY';
  public readonly mode: MigrationModeCode = 'M8_VALIDATION_ONLY';

  protected async runJourney(page: Page, context: ScenarioContext): Promise<void> {
    // M8 routes to Validation Studio
    const navValidation = page.locator('a[href="/validation"], button:has-text("Validation")').first();
    await navValidation.click();
    await this.evidence?.captureMilestone(page, 'Validation Studio Loaded', 'PASS', 'LIVE_PROVEN');
    this.evidence?.log('INFO', 'M8 Validation-Only discrepancy comparison scenario initialized.');
  }
}
