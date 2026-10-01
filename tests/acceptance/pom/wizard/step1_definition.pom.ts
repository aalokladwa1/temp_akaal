import { Page, Locator } from 'playwright';
import { SynchronizationHelper } from '../../core/synchronization.js';
import { MigrationModeCode } from '../../core/types.js';

export class Step1DefinitionPOM {
  private page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  public get migrationTitleInput(): Locator {
    return this.page.locator('#step1-migration-title, input[placeholder*="Core Banking"], input[name="migrationTitle"]').first();
  }

  public get continueButton(): Locator {
    return this.page.locator('button[title="Continue to next step"], button:has-text("Continue to Select Source"), button:has-text("Continue to")').first();
  }

  public modeCard(mode: MigrationModeCode): Locator {
    const modeLabelMap: Record<MigrationModeCode, string> = {
      M1_BULK: 'Bulk Load',
      M2_BULK_CDC: 'Bulk + CDC',
      M3_CDC: 'CDC Only',
      M4_INCREMENTAL: 'Incremental',
      M5_STATE_SYNC: 'State-Based Sync',
      M6_SCHEMA_ONLY: 'Schema Only',
      M7_DATA_ONLY: 'Data Only',
      M8_VALIDATION_ONLY: 'Validation Only',
    };
    const label = modeLabelMap[mode] || mode;
    return this.page.locator(`div:has-text("${label}"), button:has-text("${label}")`).first();
  }

  public async fillTitle(title: string): Promise<void> {
    await SynchronizationHelper.waitForVisible(this.migrationTitleInput, 8000, 'Step 1 Title Input');
    await this.migrationTitleInput.fill(title);
  }

  public async selectMode(mode: MigrationModeCode): Promise<void> {
    const card = this.modeCard(mode);
    await SynchronizationHelper.waitForVisible(card, 8000, `Mode Card: ${mode}`);
    await card.click();
  }

  public async continueToStep2(): Promise<void> {
    await SynchronizationHelper.waitForEnabled(this.continueButton, 8000, 'Continue to Step 2');
    await this.continueButton.click();
  }
}
