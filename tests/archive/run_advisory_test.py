import json
from akaal.core.pipeline import AkaalPipeline, MigrationConfig
from akaal.core.models.project import ConnectionConfig
from akaal.core.models.enums import SystemType, MigrationStrategy

source_config = ConnectionConfig(
    system_type=SystemType.ORACLE,
    host="localhost",
    port=1521,
    database_name="orcl",
    credentials_ref="vault:orcl"
)

target_config = ConnectionConfig(
    system_type=SystemType.POSTGRESQL,
    host="localhost",
    port=5432,
    database_name="pgdb",
    credentials_ref="vault:pg"
)

config = MigrationConfig(
    source_config=source_config,
    target_config=target_config,
    strategy=MigrationStrategy.BIG_BANG,
    workspace_dir="./akaal_workspace",
    project_name="Test Oracle to PG",
    ddl_schema_path="test_ddl.sql"
)

pipeline = AkaalPipeline()
result = pipeline._run_advisory(config)

output_text = []
output_text.append("--- SUMMARY STATS ---")
output_text.append(f"source_engine: {result.get('source_engine')}")
output_text.append(f"tables_analyzed: {result.get('tables_analyzed')}")
output_text.append(f"relationships: {result.get('relationships')}")
output_text.append(f"risk_summary: {json.dumps(result.get('risk_summary'), indent=2)}")
output_text.append("\n--- ALL RESULTS ---")
output_text.append(json.dumps(result, indent=2))

content = "\n".join(output_text)
print(content)

with open("run_advisory_test_output_utf8.txt", "w", encoding="utf-8") as f:
    f.write(content)
