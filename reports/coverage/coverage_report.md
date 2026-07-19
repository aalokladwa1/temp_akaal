# AKAAL Official Enterprise Coverage Report — Advisor Platform

> [!NOTE]
> **Execution Environment**: OS: `Windows 11` | Python: `3.14.6` | Duration: `27.97s` | Timestamp: `2026-07-19 11:49:41`

## 1. Executive Summary

| Metric | Value |
| --- | --- |
| **Overall Statement Coverage** | **`94.1%`** (`GOOD`) |
| **Executed Statements** | `964` / `1024` |
| **Missing Executable Statements** | `60` |
| **Total Packages / Modules** | `12` Packages / `44` Modules |
| **Total Classes / Functions** | `38` Classes / `126` Functions |
| **Lowest Covered Module** | `advisor_events (77.4%)` |
| **Highest Covered Module** | `__init__ (100.0%)` |
| **Average Package Coverage** | `92.5%` |

## 2. Package Coverage Summary

| Package Name | Modules | Executed Statements | Total Statements | Coverage % | Status |
| --- | --- | --- | --- | --- | --- |
| `akaal.advisor.events` | `2` | `26` | `33` | `78.8%` | `NEEDS_IMPROVEMENT` |
| `akaal.advisor.registry` | `2` | `73` | `87` | `83.9%` | `ACCEPTABLE` |
| `akaal.advisor.api` | `2` | `33` | `38` | `86.8%` | `ACCEPTABLE` |
| `akaal.advisor.engine` | `3` | `86` | `95` | `90.5%` | `GOOD` |
| `akaal.advisor.governance` | `2` | `23` | `25` | `92.0%` | `GOOD` |
| `akaal.advisor.serialization` | `2` | `49` | `53` | `92.5%` | `GOOD` |
| `akaal.advisor.validation` | `2` | `48` | `51` | `94.1%` | `GOOD` |
| `akaal.advisor.metrics` | `2` | `44` | `46` | `95.7%` | `PASS` |
| `akaal.advisor.analyzers` | `13` | `337` | `351` | `96.0%` | `PASS` |
| `akaal.advisor` | `1` | `4` | `4` | `100.0%` | `PASS` |
| `akaal.advisor.models` | `11` | `218` | `218` | `100.0%` | `PASS` |
| `akaal.advisor.reporting` | `2` | `23` | `23` | `100.0%` | `PASS` |

## 3. Module Coverage Breakdown (Sorted Lowest -> Highest Coverage)

| Module File | Executed Statements | Total Statements | Coverage % | Status | Classes | Functions |
| --- | --- | --- | --- | --- | --- | --- |
| `akaal\advisor\events\advisor_events.py` | `24` | `31` | `77.4%` | `NEEDS_IMPROVEMENT` | `1` | `9` |
| `akaal\advisor\registry\advisor_registry.py` | `71` | `85` | `83.5%` | `ACCEPTABLE` | `2` | `10` |
| `akaal\advisor\api\advisor_platform.py` | `31` | `36` | `86.1%` | `ACCEPTABLE` | `1` | `13` |
| `akaal\advisor\analyzers\best_practice_analyzer.py` | `29` | `33` | `87.9%` | `ACCEPTABLE` | `1` | `4` |
| `akaal\advisor\engine\aggregation_engine.py` | `27` | `30` | `90.0%` | `GOOD` | `1` | `1` |
| `akaal\advisor\engine\advisor_engine.py` | `56` | `62` | `90.3%` | `GOOD` | `1` | `2` |
| `akaal\advisor\governance\advisor_governance.py` | `21` | `23` | `91.3%` | `GOOD` | `2` | `3` |
| `akaal\advisor\serialization\advisor_serializer.py` | `47` | `51` | `92.2%` | `GOOD` | `2` | `5` |
| `akaal\advisor\validation\advisor_validator.py` | `46` | `49` | `93.9%` | `GOOD` | `2` | `3` |
| `akaal\advisor\metrics\advisor_metrics.py` | `42` | `44` | `95.5%` | `PASS` | `1` | `8` |
| `akaal\advisor\analyzers\checkpoint_analyzer.py` | `28` | `29` | `96.6%` | `PASS` | `1` | `4` |
| `akaal\advisor\analyzers\parallelism_analyzer.py` | `28` | `29` | `96.6%` | `PASS` | `1` | `4` |
| `akaal\advisor\analyzers\rollback_analyzer.py` | `28` | `29` | `96.6%` | `PASS` | `1` | `4` |
| `akaal\advisor\analyzers\topology_analyzer.py` | `28` | `29` | `96.6%` | `PASS` | `1` | `4` |
| `akaal\advisor\analyzers\worker_analyzer.py` | `28` | `29` | `96.6%` | `PASS` | `1` | `4` |
| `akaal\advisor\analyzers\batch_analyzer.py` | `29` | `30` | `96.7%` | `PASS` | `1` | `4` |
| `akaal\advisor\analyzers\cost_analyzer.py` | `29` | `30` | `96.7%` | `PASS` | `1` | `4` |
| `akaal\advisor\analyzers\eta_analyzer.py` | `29` | `30` | `96.7%` | `PASS` | `1` | `4` |
| `akaal\advisor\analyzers\hardware_analyzer.py` | `29` | `30` | `96.7%` | `PASS` | `1` | `4` |
| `akaal\advisor\analyzers\resource_analyzer.py` | `29` | `30` | `96.7%` | `PASS` | `1` | `4` |
| `akaal\advisor\__init__.py` | `4` | `4` | `100.0%` | `PASS` | `0` | `0` |
| `akaal\advisor\analyzers\__init__.py` | `13` | `13` | `100.0%` | `PASS` | `0` | `0` |
| `akaal\advisor\analyzers\base_analyzer.py` | `10` | `10` | `100.0%` | `PASS` | `1` | `4` |
| `akaal\advisor\api\__init__.py` | `2` | `2` | `100.0%` | `PASS` | `0` | `0` |
| `akaal\advisor\engine\__init__.py` | `3` | `3` | `100.0%` | `PASS` | `0` | `0` |
| `akaal\advisor\events\__init__.py` | `2` | `2` | `100.0%` | `PASS` | `0` | `0` |
| `akaal\advisor\governance\__init__.py` | `2` | `2` | `100.0%` | `PASS` | `0` | `0` |
| `akaal\advisor\metrics\__init__.py` | `2` | `2` | `100.0%` | `PASS` | `0` | `0` |
| `akaal\advisor\models\__init__.py` | `11` | `11` | `100.0%` | `PASS` | `0` | `0` |
| `akaal\advisor\models\advisory_context.py` | `16` | `16` | `100.0%` | `PASS` | `1` | `2` |
| `akaal\advisor\models\advisory_decision.py` | `16` | `16` | `100.0%` | `PASS` | `1` | `2` |
| `akaal\advisor\models\advisory_enums.py` | `32` | `32` | `100.0%` | `PASS` | `3` | `2` |
| `akaal\advisor\models\advisory_event.py` | `10` | `10` | `100.0%` | `PASS` | `1` | `1` |
| `akaal\advisor\models\advisory_evidence.py` | `15` | `15` | `100.0%` | `PASS` | `1` | `2` |
| `akaal\advisor\models\advisory_manifest.py` | `21` | `21` | `100.0%` | `PASS` | `1` | `2` |
| `akaal\advisor\models\advisory_recommendation.py` | `32` | `32` | `100.0%` | `PASS` | `1` | `2` |
| `akaal\advisor\models\advisory_trace.py` | `14` | `14` | `100.0%` | `PASS` | `1` | `2` |
| `akaal\advisor\models\advisory_version.py` | `8` | `8` | `100.0%` | `PASS` | `1` | `1` |
| `akaal\advisor\models\migration_advisory_model.py` | `43` | `43` | `100.0%` | `PASS` | `1` | `5` |
| `akaal\advisor\registry\__init__.py` | `2` | `2` | `100.0%` | `PASS` | `0` | `0` |
| `akaal\advisor\reporting\__init__.py` | `2` | `2` | `100.0%` | `PASS` | `0` | `0` |
| `akaal\advisor\reporting\advisor_report_builder.py` | `21` | `21` | `100.0%` | `PASS` | `1` | `3` |
| `akaal\advisor\serialization\__init__.py` | `2` | `2` | `100.0%` | `PASS` | `0` | `0` |
| `akaal\advisor\validation\__init__.py` | `2` | `2` | `100.0%` | `PASS` | `0` | `0` |

## 4. Missing Coverage Line Details

| Module Name | Coverage % | Priority | Missing Line Numbers | Reason / Assessment |
| --- | --- | --- | --- | --- |
| `advisor_events` | `77.4%` (`NEEDS_IMPROVEMENT`) | `MEDIUM` | `21, 22, 27, 28, 33, 49, 50` | Needs improvement to reach target 90% threshold |
| `advisor_registry` | `83.5%` (`ACCEPTABLE`) | `HIGH` | `43, 44, 55, 56, 67, 72, 86, 90, 99, 112, 133, 145, 153, 161` | Core component or critical coverage level (<70%) |
| `advisor_platform` | `86.1%` (`ACCEPTABLE`) | `LOW` | `46, 51, 56, 61, 81` | Minor unexecuted fallback branches |
| `best_practice_analyzer` | `87.9%` (`ACCEPTABLE`) | `LOW` | `34, 85, 86, 92` | Minor unexecuted fallback branches |

---
_Report generated automatically by AKAAL Official Enterprise Coverage Tracer._