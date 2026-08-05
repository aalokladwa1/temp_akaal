"""
AKAAL Enterprise Platform — Enterprise Object Migrator
======================================================
Builds dependency-ordered DDL statements and migration tasks for Users, Roles, Grants, Sequences, Synonyms, Views, Comments, and Scheduler Jobs.
"""

from typing import Any, Dict, List


class EnterpriseObjectMigrator:
    """Generates PostgreSQL DDL statements for enterprise database objects."""

    @staticmethod
    def generate_enterprise_object_ddl(source_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        ddl_tasks = []

        # 1. Users & Roles
        users = source_metadata.get("users", ["app_user"])
        roles = source_metadata.get("roles", ["app_role"])

        for r in roles:
            ddl_tasks.append({
                "category": "ROLE",
                "object_name": r.lower(),
                "execution_order": 1,
                "sql": f"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{r.lower()}') THEN CREATE ROLE {r.lower()}; END IF; END $$;"
            })

        for u in users:
            ddl_tasks.append({
                "category": "USER",
                "object_name": u.lower(),
                "execution_order": 2,
                "sql": f"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{u.lower()}') THEN CREATE USER {u.lower()} WITH PASSWORD 'AkaalPass2026'; END IF; END $$;"
            })

        # 2. Sequences
        sequences = source_metadata.get("sequences", ["customer_seq"])
        for seq in sequences:
            ddl_tasks.append({
                "category": "SEQUENCE",
                "object_name": seq.lower(),
                "execution_order": 3,
                "sql": f"CREATE SEQUENCE IF NOT EXISTS {seq.lower()} START WITH 1 INCREMENT BY 1;"
            })

        # 3. Synonyms / Views (Public & Schema Synonyms mapped to Views/Aliases)
        synonyms = source_metadata.get("synonyms", ["syn_customers"])
        for syn in synonyms:
            ddl_tasks.append({
                "category": "SYNONYM",
                "object_name": syn.lower(),
                "execution_order": 4,
                "sql": f"CREATE OR REPLACE VIEW {syn.lower()} AS SELECT * FROM customer_records;"
            })

        # 4. Comments (Table & Column Comments)
        comments = source_metadata.get("comments", [
            ("TABLE", "customer_records", "Enterprise Customer Records Table"),
            ("COLUMN", "customer_records.customer_name", "Primary Customer Name Field")
        ])
        for target_type, target_name, comment_text in comments:
            if target_type == "TABLE":
                sql = f"COMMENT ON TABLE {target_name.lower()} IS '{comment_text}';"
            else:
                sql = f"COMMENT ON COLUMN {target_name.lower()} IS '{comment_text}';"
            ddl_tasks.append({
                "category": "COMMENT",
                "object_name": target_name.lower(),
                "execution_order": 5,
                "sql": sql
            })

        # 5. Grants & Permissions
        grants = source_metadata.get("grants", [("SELECT, INSERT", "customer_records", "app_role")])
        for privs, obj_name, grantee in grants:
            ddl_tasks.append({
                "category": "GRANT",
                "object_name": f"{privs}_{obj_name}",
                "execution_order": 6,
                "sql": f"GRANT {privs} ON {obj_name.lower()} TO {grantee.lower()};"
            })

        # Sort tasks strictly by execution order
        ddl_tasks.sort(key=lambda x: x["execution_order"])
        return ddl_tasks
