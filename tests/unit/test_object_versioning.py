import pytest
import threading
from akaal.migration.versioning import (
    VersionStatus,
    RollbackMetadata,
    CanonicalVersionRecord,
    VersionMetrics,
    VersionDiff,
    ObjectVersionSnapshot,
    ObjectVersionHistory,
    ConcurrencyConflictError,
    FingerprintEngine,
    ComparisonEngine,
    VersionStore,
    VersioningCorruptionException,
    RollbackManager,
    RollbackLineageException
)

# --- 1. Fingerprint Normalization Tests ---

def test_fingerprint_normalization():
    ddl1 = "CREATE TABLE users ( id INT, name VARCHAR(50) );"
    ddl2 = "  create   table   users   (\n  id INT,\n  name VARCHAR(50)\n);"
    ddl3 = "CREATE TABLE [users] ( -- this is a comment\n id INT,\n name VARCHAR(50) /* inline */ );"
    
    fp1 = FingerprintEngine.generate_fingerprint(ddl1)
    fp2 = FingerprintEngine.generate_fingerprint(ddl2)
    fp3 = FingerprintEngine.generate_fingerprint(ddl3)
    
    assert fp1 == fp2
    assert fp1 == fp3

def test_fingerprint_sorting():
    ddl1 = "CREATE TABLE orders ( customer_id INT, order_id INT );"
    ddl2 = "CREATE TABLE orders ( order_id INT, customer_id INT );"
    
    fp1 = FingerprintEngine.generate_fingerprint(ddl1)
    fp2 = FingerprintEngine.generate_fingerprint(ddl2)
    assert fp1 == fp2

# --- 2. Version Store Invariants ---

def test_version_store_uniqueness():
    store = VersionStore()
    history = ObjectVersionHistory(store)
    
    snap1 = history.commit_version("o1", "TABLE", "orders", "public", "postgresql", "CREATE TABLE orders (id INT);", "sess1", "author1")
    
    # Attempting to register the same snapshot raises ValueError due to version_id collision
    with pytest.raises(ValueError):
        store.register(snap1)

def test_version_store_cycle_prevention():
    from datetime import datetime, timezone
    store = VersionStore()
    
    meta1 = CanonicalVersionRecord(
        version_id="v1", object_id="o1", object_type="TABLE", object_name="orders", parent_schema="public",
        database_dialect="postgresql", object_definition_hash="h1", canonical_metadata_hash="h1",
        creation_timestamp=datetime.now(timezone.utc), modification_timestamp=datetime.now(timezone.utc),
        migration_session_id="sess1", parent_version_id=None, current_version_id="v1",
        version_status=VersionStatus.CREATED, author="a1",
        rollback_metadata=RollbackMetadata(None, None, None), integrity_checksum=""
    )
    snap1 = ObjectVersionSnapshot(metadata=meta1, serialized_payload="")
    
    meta2 = CanonicalVersionRecord(
        version_id="v2", object_id="o1", object_type="TABLE", object_name="orders", parent_schema="public",
        database_dialect="postgresql", object_definition_hash="h2", canonical_metadata_hash="h2",
        creation_timestamp=datetime.now(timezone.utc), modification_timestamp=datetime.now(timezone.utc),
        migration_session_id="sess1", parent_version_id="v1", current_version_id="v2",
        version_status=VersionStatus.CREATED, author="a1",
        rollback_metadata=RollbackMetadata(None, None, None), integrity_checksum=""
    )
    snap2 = ObjectVersionSnapshot(metadata=meta2, serialized_payload="")
    
    meta3 = CanonicalVersionRecord(
        version_id="v3", object_id="o1", object_type="TABLE", object_name="orders", parent_schema="public",
        database_dialect="postgresql", object_definition_hash="h3", canonical_metadata_hash="h3",
        creation_timestamp=datetime.now(timezone.utc), modification_timestamp=datetime.now(timezone.utc),
        migration_session_id="sess1", parent_version_id="v2", current_version_id="v3",
        version_status=VersionStatus.CREATED, author="a1",
        rollback_metadata=RollbackMetadata(None, None, None), integrity_checksum=""
    )
    snap3 = ObjectVersionSnapshot(metadata=meta3, serialized_payload="")
    
    store.register(snap1)
    store.register(snap2)
    
    # Inject cycle: v1 -> v2 -> v1
    object.__setattr__(snap1.metadata, "parent_version_id", "v2")
    
    with pytest.raises(VersioningCorruptionException):
        store.register(snap3)

# --- 3. Comparison Engine Tests ---

def test_comparison_engine():
    store = VersionStore()
    history = ObjectVersionHistory(store)
    
    snap_a1 = history.commit_version("o1", "TABLE", "orders", "public", "postgresql", "CREATE TABLE orders (id INT);", "sess1", "author1")
    
    # Snapshot B has modified o1, deleted o2 (not present), and created o3
    snap_b1 = history.commit_version("o1", "TABLE", "orders", "public", "postgresql", "CREATE TABLE orders (id INT, status VARCHAR);", "sess1", "author1", expected_parent_id=snap_a1.metadata.version_id)
    snap_b2 = history.commit_version("o3", "TABLE", "payments", "public", "postgresql", "CREATE TABLE payments (id INT);", "sess1", "author1")
    
    diffs = ComparisonEngine.compare_snapshots([snap_a1], [snap_b1, snap_b2])
    
    change_types = {d.object_key: d.change_type for d in diffs}
    assert change_types["orders"] == "MODIFIED"
    assert change_types["payments"] == "CREATED"

# --- 4. Rollback Lineage Tests ---

def test_rollback_reconstruction():
    store = VersionStore()
    history = ObjectVersionHistory(store)
    
    snap1 = history.commit_version("o1", "TABLE", "orders", "public", "postgresql", "CREATE TABLE orders (id INT);", "sess1", "author1")
    snap2 = history.commit_version("o1", "TABLE", "orders", "public", "postgresql", "CREATE TABLE orders (id INT, status VARCHAR);", "sess1", "author1", expected_parent_id=snap1.metadata.version_id)
    
    rb_manager = RollbackManager(store)
    lineage = rb_manager.reconstruct_rollback_lineage(snap2.metadata.version_id)
    
    assert len(lineage) == 2
    assert lineage[0].metadata.version_id == snap2.metadata.version_id
    assert lineage[1].metadata.version_id == snap1.metadata.version_id

# --- 5. Concurrency Isolation Tests ---

def test_concurrent_snapshot_updates():
    store = VersionStore()
    history = ObjectVersionHistory(store)
    
    def worker_task(idx):
        history.commit_version(f"o_{idx}", "TABLE", f"tbl_{idx}", "public", "postgresql", f"CREATE TABLE tbl_{idx} (id INT);", "sess1", "author1")
        
    threads = []
    for i in range(10):
        t = threading.Thread(target=worker_task, args=(i,))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    assert len(store.snapshots) == 10
