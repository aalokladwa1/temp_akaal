import { BaseAcceptanceScenario } from './scenarios/base_scenario.js';
import { ScenarioM1Bulk } from './scenarios/scenario_m1_bulk.js';
import { ScenarioM2BulkCdc } from './scenarios/scenario_m2_bulk_cdc.js';
import { ScenarioM3Cdc } from './scenarios/scenario_m3_cdc.js';
import { ScenarioM4Incremental } from './scenarios/scenario_m4_incremental.js';
import { ScenarioM5StateSync } from './scenarios/scenario_m5_state_sync.js';
import { ScenarioM6SchemaOnly } from './scenarios/scenario_m6_schema_only.js';
import { ScenarioM7DataOnly } from './scenarios/scenario_m7_data_only.js';
import { ScenarioM8ValidationOnly } from './scenarios/scenario_m8_validation_only.js';

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  const modeIndex = args.indexOf('--mode');
  const targetMode = modeIndex !== -1 ? args[modeIndex + 1]?.toUpperCase() : null;

  console.log('========================================================');
  console.log('  DevKros P8 — Acceptance Test Runner');
  console.log('========================================================\n');

  if (!targetMode) {
    console.log('Usage: node runner.ts --mode <M1|M2|M3|M4|M5|M6|M7|M8>');
    process.exit(0);
  }

  console.log(`Configured target mode: ${targetMode}\n`);

  let scenario: BaseAcceptanceScenario;
  switch (targetMode) {
    case 'M1':
    case 'M1_BULK':
      scenario = new ScenarioM1Bulk();
      break;
    case 'M2':
    case 'M2_BULK_CDC':
      scenario = new ScenarioM2BulkCdc();
      break;
    case 'M3':
    case 'M3_CDC':
      scenario = new ScenarioM3Cdc();
      break;
    case 'M4':
    case 'M4_INCREMENTAL':
      scenario = new ScenarioM4Incremental();
      break;
    case 'M5':
    case 'M5_STATE_SYNC':
      scenario = new ScenarioM5StateSync();
      break;
    case 'M6':
    case 'M6_SCHEMA_ONLY':
      scenario = new ScenarioM6SchemaOnly();
      break;
    case 'M7':
    case 'M7_DATA_ONLY':
      scenario = new ScenarioM7DataOnly();
      break;
    case 'M8':
    case 'M8_VALIDATION_ONLY':
      scenario = new ScenarioM8ValidationOnly();
      break;
    default:
      console.error(`Unknown migration mode: ${targetMode}`);
      process.exit(1);
  }

  console.log(`Starting execution for ${scenario.scenarioId}...`);
  const result = await scenario.execute();

  console.log('\n========================================================');
  console.log('  SCENARIO RESULT SUMMARY');
  console.log('========================================================');
  console.log(`Scenario ID:        ${result.scenarioId}`);
  console.log(`Mode:               ${result.mode}`);
  console.log(`Status:             ${result.status}`);
  console.log(`Proof:              ${result.proof}`);
  console.log(`Duration:           ${(result.durationMs / 1000).toFixed(2)}s`);
  console.log(`Evidence Location:  ${result.evidenceDirectory}`);
  console.log('========================================================\n');
}

main().catch((err) => {
  console.error('Fatal acceptance runner error:', err);
  process.exit(1);
});
