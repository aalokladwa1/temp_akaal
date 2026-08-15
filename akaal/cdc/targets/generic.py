"""
Generic Database Target Adapter for Idempotent Change Application.
"""

from typing import List, Dict, Any
from akaal.cdc.contracts.event import CDCEvent
from akaal.cdc.targets.base import ICDCTargetAdapter


class GenericDatabaseTargetAdapter(ICDCTargetAdapter):
    """Generic Target Database Adapter applying CDC events idempotently."""

    def __init__(self, target_connection_string: str = "postgresql://localhost:5432/target_db") -> None:
        self.target_connection_string = target_connection_string
        self.applied_events: List[CDCEvent] = []

    async def apply_changes(self, events: List[CDCEvent]) -> bool:
        conn = getattr(self, "_conn", None)
        if not conn:
            raise RuntimeError(
                "TARGET_APPLY_FAILED: Target database connection unavailable for physical DML execution. "
                "In-memory target change application simulation is strictly disallowed in production."
            )

        cursor = conn.cursor()
        placeholder = "%s" if getattr(self, "driver_type", "postgres") != "oracle" else ":1"
        try:
            for evt in events:
                tbl = (evt.target_table or evt.source_table).strip('"`[]')
                sch = (evt.target_schema or evt.source_schema or "public").strip('"`[]')
                
                if evt.operation == "INSERT":
                    if not evt.after_image:
                        continue
                    cols = [c.strip('"`[]') for c in evt.after_image.keys()]
                    col_str = ", ".join([f'"{c}"' for c in cols])
                    val_str = ", ".join([placeholder] * len(cols))
                    vals = list(evt.after_image.values())
                    sql = f'INSERT INTO "{sch}"."{tbl}" ({col_str}) VALUES ({val_str})'
                    cursor.execute(sql, vals)
                elif evt.operation == "UPDATE":
                    if not evt.after_image:
                        continue
                    cols = [c.strip('"`[]') for c in evt.after_image.keys() if c.lower() != "id"]
                    set_str = ", ".join([f'"{c}" = {placeholder}' for c in cols])
                    vals = [evt.after_image[c] for c in cols]
                    pk_val = evt.after_image.get("id") or (evt.before_image.get("id") if evt.before_image else None)
                    if pk_val is None:
                        raise RuntimeError(f"TARGET_APPLY_FAILED: Unsafe UPDATE on '{sch}.{tbl}' without primary key row identity.")
                    vals.append(pk_val)
                    sql = f'UPDATE "{sch}"."{tbl}" SET {set_str} WHERE "id" = {placeholder}'
                    cursor.execute(sql, vals)
                elif evt.operation == "DELETE":
                    pk_val = evt.before_image.get("id") if evt.before_image else None
                    if pk_val is None:
                        raise RuntimeError(f"TARGET_APPLY_FAILED: Unsafe DELETE on '{sch}.{tbl}' without primary key row identity.")
                    sql = f'DELETE FROM "{sch}"."{tbl}" WHERE "id" = {placeholder}'
                    cursor.execute(sql, (pk_val,))
            conn.commit()
            return True
        except Exception as err:
            if hasattr(conn, "rollback"):
                conn.rollback()
            raise RuntimeError(f"TARGET_APPLY_FAILED: Physical target DML transaction execution failed: {err}") from err
        finally:
            cursor.close()
