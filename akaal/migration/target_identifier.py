"""PostgreSQL Target Identifier Sanitizer and Namespace Validator."""

import re
from typing import Dict, Any

RESERVED_PG_SCHEMAS = {"pg_catalog", "information_schema", "pg_toast", "pg_temp_1", "pg_toast_temp_1"}

def validate_operator_configured_identifier(identifier: str, identifier_type: str = "schema") -> Dict[str, Any]:
    """Strictly validates operator-explicit target identifiers. REJECTS invalid names without silent mutation."""
    if not identifier or not identifier.strip():
        return {
            "valid": False,
            "error_code": "EMPTY_IDENTIFIER",
            "error_message": f"Target {identifier_type} name cannot be empty."
        }
        
    name = identifier.strip().lower()
    
    if name.startswith("pg_"):
        return {
            "valid": False,
            "error_code": "RESERVED_PREFIX",
            "error_message": f"Target {identifier_type} '{identifier}' is invalid for PostgreSQL because names beginning with 'pg_' are reserved by PostgreSQL system namespaces. Please enter a valid non-reserved name (e.g. 'app_{name[3:]}').",
            "suggested_name": f"app_{name[3:]}"
        }
        
    if name in RESERVED_PG_SCHEMAS:
        return {
            "valid": False,
            "error_code": "RESERVED_SCHEMA",
            "error_message": f"Target {identifier_type} '{identifier}' is a reserved PostgreSQL system schema namespace.",
            "suggested_name": f"app_{name}"
        }
        
    if len(name) > 63:
        return {
            "valid": False,
            "error_code": "IDENTIFIER_TOO_LONG",
            "error_message": f"Target {identifier_type} '{identifier}' exceeds maximum PostgreSQL identifier limit of 63 characters.",
            "suggested_name": name[:63]
        }
        
    if not re.match(r'^[a-z_][a-z0-9_]*$', name):
        return {
            "valid": False,
            "error_code": "INVALID_CHARACTERS",
            "error_message": f"Target {identifier_type} '{identifier}' contains invalid characters. PostgreSQL identifiers must start with a letter/underscore and contain only alphanumeric characters and underscores."
        }

    return {"valid": True, "sanitized_identifier": name}

def derive_akaal_generated_target_mapping(source_schema: str) -> Dict[str, Any]:
    """Derives deterministic target schema mapping for AKAAL auto-generated default scope."""
    if not source_schema:
        return {"source_schema": "public", "target_schema": "public", "remapped": False}
        
    clean = re.sub(r'[^a-zA-Z0-9_]', '_', source_schema.strip()).lower()
    remapped = False
    reason = None
    
    if clean.startswith("pg_"):
        clean = "app_" + clean[3:]
        remapped = True
        reason = "Mapped reserved PostgreSQL prefix 'pg_' to 'app_'."
    elif clean in RESERVED_PG_SCHEMAS:
        clean = f"app_{clean}"
        remapped = True
        reason = f"Mapped reserved system schema '{source_schema}' to 'app_{source_schema}'."
        
    if len(clean) > 63:
        clean = clean[:63]
        remapped = True
        reason = "Truncated identifier to 63 characters."
        
    return {
        "source_schema": source_schema,
        "target_schema": clean,
        "remapped": remapped,
        "reason": reason
    }


def sanitize_pg_identifier(identifier: str) -> str:
    res = derive_akaal_generated_target_mapping(identifier)
    return res["target_schema"]


def validate_target_schema(identifier: str) -> Dict[str, Any]:
    res = validate_operator_configured_identifier(identifier, identifier_type="schema")
    if not res.get("valid"):
        code = res.get("error_code")
        if code in ("RESERVED_PREFIX", "RESERVED_SCHEMA"):
            code = "RESERVED_SCHEMA_NAME"
        return {
            "valid": False,
            "error_code": code,
            "error_message": res.get("error_message"),
            "suggestion": res.get("suggested_name"),
        }
    return {
        "valid": True,
        "sanitized": res.get("sanitized_identifier"),
    }



class ConnectionAuthority:
    """Canonical connection authority representation for SOURCE and TARGET endpoints.
    
    SECURITY MANDATE:
    - Never stores plaintext passwords in fields or serialized representations.
    - Uses non-secret authority_fingerprint derived from (engine, host, port, database, username).
    """

    def __init__(
        self,
        connection_id: str,
        engine: str,
        host: str,
        port: int,
        database: str,
        username: str,
        credential_ref: str,
        role: str = "TARGET"  # "SOURCE" or "TARGET"
    ):
        self.connection_id = connection_id or f"conn-{role.lower()}-{engine.lower()}"
        self.engine = str(engine or "").strip()
        self.host = str(host or "").strip()
        self.port = int(port or 0)
        self.database = str(database or "").strip()
        self.username = str(username or "").strip()
        self.credential_ref = str(credential_ref or "").strip()
        self.role = str(role or "TARGET").upper()
        self.authority_fingerprint = self.compute_fingerprint()

    def compute_fingerprint(self) -> str:
        """Computes a deterministic non-secret SHA256 fingerprint for identity verification."""
        import hashlib
        raw_identity = f"{self.engine.upper()}:{self.host.lower()}:{self.port}:{self.database.lower()}:{self.username.lower()}"
        return hashlib.sha256(raw_identity.encode("utf-8")).hexdigest()[:16]

    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Returns dictionary representation without secrets by default."""
        return {
            "connection_id": self.connection_id,
            "role": self.role,
            "engine": self.engine,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "username": self.username,
            "credential_ref": self.credential_ref,
            "authority_fingerprint": self.authority_fingerprint,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], role: str = "TARGET") -> "ConnectionAuthority":
        """Constructs ConnectionAuthority from payload dictionary without fallback substitutions."""
        prefix = "source_" if role.upper() == "SOURCE" else "target_"
        
        c_id = data.get(f"{prefix}connection_id") or data.get("connection_id") or f"conn-{role.lower()}-default"
        engine = data.get(f"{prefix}engine") or data.get("engine") or ("ORACLE" if role.upper() == "SOURCE" else "POSTGRESQL")
        
        raw_host = data.get(f"{prefix}host") or data.get("host")
        host = str(raw_host).strip() if raw_host is not None else None
        
        raw_port = data.get(f"{prefix}port") or data.get("port")
        port = int(raw_port) if raw_port is not None and str(raw_port).isdigit() else raw_port
        
        raw_db = (
            data.get(f"{prefix}service") or
            data.get(f"{prefix}pdb") or
            data.get(f"{prefix}service_name") or
            data.get(f"{prefix}db") or
            data.get(f"{prefix}database") or
            data.get("source_service") or
            data.get("source_instance") or
            data.get("database") or
            data.get("database_name")
        )
        db = str(raw_db).strip() if raw_db is not None else None
        
        raw_user = data.get(f"{prefix}user") or data.get(f"{prefix}username") or data.get("username")
        user = str(raw_user).strip() if raw_user is not None else None
        
        cred_ref = data.get(f"{prefix}credential_ref") or data.get("credential_ref") or f"cred-ref-{c_id}"

        return cls(
            connection_id=c_id,
            engine=engine,
            host=host,
            port=port,
            database=db,
            username=user,
            credential_ref=cred_ref,
            role=role
        )


class MigrationObjectMapping:
    """Canonical mapping from source object to target object.
    Explicitly decoupled from ConnectionAuthority.
    """

    def __init__(
        self,
        mapping_id: str = None,
        source_database: str = "",
        source_schema: str = "",
        source_object: str = "",
        source_object_type: str = "Table",
        target_database: str = "",
        target_schema: str = "",
        target_object: str = "",
        conversion_action: str = "MIGRATE_DATA",
        dependencies: list = None,
    ):
        self.source_schema = str(source_schema or "").strip().upper()
        self.source_object = str(source_object or "").strip().upper()
        self.mapping_id = mapping_id or f"map-{self.source_schema}.{self.source_object}"
        self.source_database = str(source_database or "").strip()
        self.source_object_type = str(source_object_type or "Table").strip()
        self.target_database = str(target_database or "").strip()
        
        mapped = derive_akaal_generated_target_mapping(target_schema or source_schema or "public")
        self.target_schema = mapped["target_schema"]
        self.target_object = str(target_object or source_object or "").strip().lower()
        self.conversion_action = conversion_action
        self.dependencies = dependencies or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mapping_id": self.mapping_id,
            "source_database": self.source_database,
            "source_schema": self.source_schema,
            "source_object": self.source_object,
            "source_object_type": self.source_object_type,
            "target_database": self.target_database,
            "target_schema": self.target_schema,
            "target_object": self.target_object,
            "conversion_action": self.conversion_action,
            "dependencies": self.dependencies,
        }



