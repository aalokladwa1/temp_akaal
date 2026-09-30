import { Page, Locator } from 'playwright';
import { SynchronizationHelper } from '../../core/synchronization.js';

export class CockpitProgressPOM {
  private page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  public get statusBadge(): Locator {
    return this.page.locator('app-status-badge, [data-testid="migration-status-badge"], text="RUNNING", text="COMPLETED", text="INITIALIZED", text="FAILED"').first();
  }

  public get completedBadge(): Locator {
    return this.page.locator('text="Completed", text="COMPLETED", .bg-emerald-50:has-text("Completed")').first();
  }

  public get failedBadge(): Locator {
    return this.page.locator('text="Failed", text="FAILED", text="Aborted", .bg-rose-50').first();
  }

  public async getStatusText(): Promise<string> {
    const text = await this.statusBadge.textContent().catch(() => '');
    return (text || '').trim();
  }

  public async waitForTerminalState(timeoutMs: number = 60000): Promise<'COMPLETED' | 'FAILED'> {
    return SynchronizationHelper.waitForCondition(
      async () => {
        if (await this.completedBadge.isVisible().catch(() => false)) {
          return 'COMPLETED';
        }
        if (await this.failedBadge.isVisible().catch(() => false)) {
          return 'FAILED';
        }
        return false;
      },
      timeoutMs,
      500,
      'Cockpit Terminal State'
    );
  }
}
