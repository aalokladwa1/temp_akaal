package prototypedb

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"

	_ "modernc.org/sqlite"
)

type MigrationRowDTO struct {
	ID                   string   `json:"id"`
	Name                 string   `json:"name"`
	SourceProvider       string   `json:"source_provider"`
	SourceLabel          string   `json:"source_label"`
	TargetProvider       string   `json:"target_provider"`
	TargetLabel          string   `json:"target_label"`
	Mode                 string   `json:"mode"`
	LifecycleState       string   `json:"lifecycle_state"`
	CurrentStage         string   `json:"current_stage"`
	ProgressPercent      float64  `json:"progress_percent"`
	ThroughputRowsPerSec *float64 `json:"throughput_rows_per_sec,omitempty"`
	CdcLagMs             *float64 `json:"cdc_lag_ms,omitempty"`
	ObjectsCompleted     *int     `json:"objects_completed,omitempty"`
	ObjectsTotal         *int     `json:"objects_total,omitempty"`
	StateSyncPercent     *float64 `json:"state_sync_percent,omitempty"`
	DifferenceCount      *int     `json:"difference_count,omitempty"`
	IncrementalWatermark *string  `json:"incremental_watermark,omitempty"`
	AttentionLevel       *string  `json:"attention_level,omitempty"`
	AttentionText        *string  `json:"attention_text,omitempty"`
	ProjectID            *string  `json:"project_id,omitempty"`
	StartedAt            string   `json:"started_at"`
	ScheduledAt          *string  `json:"scheduled_at,omitempty"`
	UpdatedAt            string   `json:"updated_at"`
}

type ProjectRowDTO struct {
	ID              string  `json:"id"`
	Name            string  `json:"name"`
	Environment     string  `json:"environment"`
	Health          string  `json:"health"`
	MigrationCount  int     `json:"migration_count"`
	ActiveCount     int     `json:"active_count"`
	AttentionCount  int     `json:"attention_count"`
	ScheduledCount  int     `json:"scheduled_count"`
	DeliveryPercent float64 `json:"delivery_percent"`
	TargetDate      *string `json:"target_date,omitempty"`
	Owner           string  `json:"owner"`
	UpdatedAt       string  `json:"updated_at"`
}

type ActivityRowDTO struct {
	ID           string `json:"id"`
	ActivityType string `json:"activity_type"`
	Title        string `json:"title"`
	SubjectType  string `json:"subject_type"`
	SubjectID    string `json:"subject_id"`
	SubjectName  string `json:"subject_name"`
	StatusText   string `json:"status_text"`
	OccurredAt   string `json:"occurred_at"`
	ActionType   string `json:"action_type"`
	Severity     string `json:"severity"`
}

type MigrationHomeSummaryDTO struct {
	ActiveCount     int    `json:"active_count"`
	AttentionCount  int    `json:"attention_count"`
	ScheduledCount  int    `json:"scheduled_count"`
	CompletedCount  int    `json:"completed_count"`
	TotalCount      int    `json:"total_count"`
	DynamicHeadline string `json:"dynamic_headline"`
}

type Store struct {
	dbPath string
	db     *sql.DB
	mu     sync.RWMutex
}

var (
	globalStore *Store
	onceStore   sync.Once
)

func GetStore() (*Store, error) {
	var initErr error
	onceStore.Do(func() {
		cwd, err := os.Getwd()
		if err != nil {
			cwd = "."
		}
		dataDir := filepath.Join(cwd, "data")
		_ = os.MkdirAll(dataDir, 0755)
		dbPath := filepath.Join(dataDir, "akaal-ui-prototype.db")

		store, err := NewStore(dbPath)
		if err != nil {
			initErr = err
			return
		}
		globalStore = store
	})
	if initErr != nil {
		return nil, initErr
	}
	return globalStore, nil
}

func NewStore(dbPath string) (*Store, error) {
	dir := filepath.Dir(dbPath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create db directory: %w", err)
	}

	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open sqlite db at %s: %w", dbPath, err)
	}

	// PRAGMA tuning for local prototype
	if _, err := db.Exec(`PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;`); err != nil {
		// Ignore if non-fatal
	}

	s := &Store{
		dbPath: dbPath,
		db:     db,
	}

	if err := s.bootstrapSchema(); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("failed to bootstrap schema: %w", err)
	}

	if err := s.seedIfEmpty(); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("failed to seed prototype db: %w", err)
	}

	return s, nil
}

func (s *Store) bootstrapSchema() error {
	s.mu.Lock()
	defer s.mu.Unlock()

	schema := `
	CREATE TABLE IF NOT EXISTS migration_home_migrations (
		id TEXT PRIMARY KEY,
		name TEXT NOT NULL,
		source_provider TEXT NOT NULL,
		source_label TEXT NOT NULL,
		target_provider TEXT NOT NULL,
		target_label TEXT NOT NULL,
		mode TEXT NOT NULL,
		lifecycle_state TEXT NOT NULL,
		current_stage TEXT NOT NULL,
		progress_percent REAL NOT NULL DEFAULT 0,
		throughput_rows_per_sec REAL,
		cdc_lag_ms REAL,
		objects_completed INTEGER,
		objects_total INTEGER,
		state_sync_percent REAL,
		difference_count INTEGER,
		incremental_watermark TEXT,
		attention_level TEXT,
		attention_text TEXT,
		project_id TEXT,
		started_at TEXT NOT NULL,
		scheduled_at TEXT,
		updated_at TEXT NOT NULL
	);

	CREATE TABLE IF NOT EXISTS migration_home_projects (
		id TEXT PRIMARY KEY,
		name TEXT NOT NULL,
		environment TEXT NOT NULL,
		health TEXT NOT NULL,
		migration_count INTEGER NOT NULL DEFAULT 0,
		active_count INTEGER NOT NULL DEFAULT 0,
		attention_count INTEGER NOT NULL DEFAULT 0,
		scheduled_count INTEGER NOT NULL DEFAULT 0,
		delivery_percent REAL NOT NULL DEFAULT 0,
		target_date TEXT,
		owner TEXT NOT NULL,
		updated_at TEXT NOT NULL
	);

	CREATE TABLE IF NOT EXISTS migration_home_activity (
		id TEXT PRIMARY KEY,
		activity_type TEXT NOT NULL,
		title TEXT NOT NULL,
		subject_type TEXT NOT NULL,
		subject_id TEXT NOT NULL,
		subject_name TEXT NOT NULL,
		status_text TEXT NOT NULL,
		occurred_at TEXT NOT NULL,
		action_type TEXT NOT NULL,
		severity TEXT NOT NULL
	);
	`
	_, err := s.db.Exec(schema)
	return err
}

func (s *Store) seedIfEmpty() error {
	s.mu.Lock()
	defer s.mu.Unlock()

	var count int
	err := s.db.QueryRow("SELECT COUNT(*) FROM migration_home_migrations").Scan(&count)
	if err != nil {
		return err
	}
	if count > 0 {
		return nil // Idempotent: already seeded
	}

	tx, err := s.db.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()

	// Seed Migrations (3 Independent with project_id IS NULL + 2 Project-assigned)
	now := time.Now().UTC().Format(time.RFC3339)
	schedTime := time.Now().UTC().Add(12 * time.Hour).Format(time.RFC3339)

	stmtMig, err := tx.Prepare(`
		INSERT INTO migration_home_migrations (
			id, name, source_provider, source_label, target_provider, target_label,
			mode, lifecycle_state, current_stage, progress_percent, throughput_rows_per_sec,
			cdc_lag_ms, objects_completed, objects_total, state_sync_percent, difference_count,
			incremental_watermark, attention_level, attention_text, project_id, started_at, scheduled_at, updated_at
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`)
	if err != nil {
		return err
	}
	defer stmtMig.Close()

	// M1: Bulk + CDC (Independent)
	_, _ = stmtMig.Exec(
		"mig-001", "Core Accounts Ledger Migration", "Oracle", "prod-oracle-01.internal:1521/ORCL",
		"PostgreSQL", "aurora-pg.cluster-ro.internal:5432/finance", "BULK_CDC", "ACTIVE",
		"CDC Catchup Phase", 84.2, 142500.0, 400.0, nil, nil, nil, nil, nil, nil, nil, nil,
		now, nil, now,
	)

	// M2: Bulk Migration (Independent)
	_, _ = stmtMig.Exec(
		"mig-002", "Customer Analytics Warehouse Load", "PostgreSQL", "rds-pg-analytics.internal:5432/reporting",
		"Snowflake", "xy12345.us-east-1.snowflakecomputing.com", "BULK_ONLY", "ACTIVE",
		"Direct-Path COPY Worker 4/8", 62.0, 88000.0, nil, nil, nil, nil, nil, nil, nil, nil, nil,
		now, nil, now,
	)

	// M3: State Sync with Attention (Independent)
	_, _ = stmtMig.Exec(
		"mig-003", "Payment Gateway State Reconciliation", "MySQL", "mysql-primary-02.internal:3306/payments",
		"PostgreSQL", "pg-payments-dr.internal:5432/payments", "STATE_SYNC", "ATTENTION",
		"Merkle Discrepancy Localization", 98.7, nil, nil, nil, nil, 98.7, 7, nil,
		"WARNING", "7 cell differences detected in settlement partition", nil,
		now, nil, now,
	)

	// M4: Scheduled CDC Migration (Independent)
	_, _ = stmtMig.Exec(
		"mig-004", "Inventory Stream Replication", "MongoDB", "mongo-shard-01.internal:27017/catalog",
		"Kafka", "kafka-broker-01.internal:9092", "CDC_ONLY", "SCHEDULED",
		"Pending Window Authorization", 0.0, nil, nil, nil, nil, nil, nil, nil, nil, nil, nil,
		now, schedTime, now,
	)

	// M5: Completed Migration (Independent)
	_, _ = stmtMig.Exec(
		"mig-005", "Customer Master Archive", "Oracle", "oracle-legacy.internal:1521/ARCH",
		"PostgreSQL", "pg-archive.internal:5432/public", "BULK_ONLY", "COMPLETED",
		"Verified 100% Certified", 100.0, nil, nil, nil, nil, nil, 0, nil, nil, nil, nil,
		now, nil, now,
	)

	// Seed Projects
	stmtProj, err := tx.Prepare(`
		INSERT INTO migration_home_projects (
			id, name, environment, health, migration_count, active_count, attention_count,
			scheduled_count, delivery_percent, target_date, owner, updated_at
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`)
	if err != nil {
		return err
	}
	defer stmtProj.Close()

	// Proj 1: 46 days left (Target ~Oct 15)
	targetDate1 := time.Now().AddDate(0, 0, 46).Format("2006-01-02")
	_, _ = stmtProj.Exec("proj-001", "Core Banking Modernization", "Production", "HEALTHY", 12, 7, 0, 1, 74.0, targetDate1, "Aalok Ladwa", now)

	// Proj 2: 8 days left with 2 attention items (Target ~Sep 7)
	targetDate2 := time.Now().AddDate(0, 0, 8).Format("2006-01-02")
	_, _ = stmtProj.Exec("proj-002", "Payment Gateway Sharding", "Staging", "ATTENTION", 6, 2, 2, 0, 42.0, targetDate2, "Sarah Jenkins", now)

	// Proj 3: 3 months left (Target ~Nov 30)
	targetDate3 := time.Now().AddDate(0, 3, 0).Format("2006-01-02")
	_, _ = stmtProj.Exec("proj-003", "Data Lake Consolidation", "Development", "HEALTHY", 8, 3, 0, 2, 88.0, targetDate3, "Dev Ops Team", now)

	// Seed Meaningful Recent Operational Activity
	stmtAct, err := tx.Prepare(`
		INSERT INTO migration_home_activity (
			id, activity_type, title, subject_type, subject_id, subject_name, status_text, occurred_at, action_type, severity
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`)
	if err != nil {
		return err
	}
	defer stmtAct.Close()

	t4m := time.Now().Add(-4 * time.Minute).Format(time.RFC3339)
	t30m := time.Now().Add(-30 * time.Minute).Format(time.RFC3339)
	t48m := time.Now().Add(-48 * time.Minute).Format(time.RFC3339)
	t1h := time.Now().Add(-1 * time.Hour).Format(time.RFC3339)

	_, _ = stmtAct.Exec("act-001", "cutover", "Cutover approved", "migration", "mig-001", "ERP Core", "Source quiesced · Write authority transferred", t4m, "VIEW", "INFO")
	_, _ = stmtAct.Exec("act-002", "validation", "Validation certified", "validation", "val-002", "Customer Archive", "Merkle root hash sealed · 0 discrepancies", t30m, "VIEW", "SUCCESS")
	_, _ = stmtAct.Exec("act-003", "approval", "Approval requested", "migration", "mig-003", "Finance CDC", "Waiting for SecOps maker-checker sign-off", t48m, "REVIEW", "WARNING")
	_, _ = stmtAct.Exec("act-004", "execution", "Migration completed", "migration", "mig-005", "Customer Master", "10.4M rows committed across 64 partitions", t1h, "VIEW", "INFO")

	return tx.Commit()
}

func (s *Store) GetIndependentMigrations() ([]MigrationRowDTO, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	rows, err := s.db.Query(`
		SELECT id, name, source_provider, source_label, target_provider, target_label,
		       mode, lifecycle_state, current_stage, progress_percent, throughput_rows_per_sec,
		       cdc_lag_ms, objects_completed, objects_total, state_sync_percent, difference_count,
		       incremental_watermark, attention_level, attention_text, project_id, started_at, scheduled_at, updated_at
		FROM migration_home_migrations
		WHERE project_id IS NULL
		ORDER BY CASE lifecycle_state WHEN 'ACTIVE' THEN 1 WHEN 'ATTENTION' THEN 2 WHEN 'SCHEDULED' THEN 3 ELSE 4 END, updated_at DESC
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var list []MigrationRowDTO
	for rows.Next() {
		var m MigrationRowDTO
		if err := rows.Scan(
			&m.ID, &m.Name, &m.SourceProvider, &m.SourceLabel, &m.TargetProvider, &m.TargetLabel,
			&m.Mode, &m.LifecycleState, &m.CurrentStage, &m.ProgressPercent, &m.ThroughputRowsPerSec,
			&m.CdcLagMs, &m.ObjectsCompleted, &m.ObjectsTotal, &m.StateSyncPercent, &m.DifferenceCount,
			&m.IncrementalWatermark, &m.AttentionLevel, &m.AttentionText, &m.ProjectID, &m.StartedAt, &m.ScheduledAt, &m.UpdatedAt,
		); err != nil {
			return nil, err
		}
		list = append(list, m)
	}
	return list, nil
}

func (s *Store) GetAllProjects() ([]ProjectRowDTO, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	rows, err := s.db.Query(`
		SELECT id, name, environment, health, migration_count, active_count, attention_count,
		       scheduled_count, delivery_percent, target_date, owner, updated_at
		FROM migration_home_projects
		ORDER BY attention_count DESC, delivery_percent ASC
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var list []ProjectRowDTO
	for rows.Next() {
		var p ProjectRowDTO
		if err := rows.Scan(
			&p.ID, &p.Name, &p.Environment, &p.Health, &p.MigrationCount, &p.ActiveCount, &p.AttentionCount,
			&p.ScheduledCount, &p.DeliveryPercent, &p.TargetDate, &p.Owner, &p.UpdatedAt,
		); err != nil {
			return nil, err
		}
		list = append(list, p)
	}
	return list, nil
}

func (s *Store) GetRecentActivity() ([]ActivityRowDTO, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	rows, err := s.db.Query(`
		SELECT id, activity_type, title, subject_type, subject_id, subject_name, status_text, occurred_at, action_type, severity
		FROM migration_home_activity
		ORDER BY occurred_at DESC
		LIMIT 10
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var list []ActivityRowDTO
	for rows.Next() {
		var a ActivityRowDTO
		if err := rows.Scan(
			&a.ID, &a.ActivityType, &a.Title, &a.SubjectType, &a.SubjectID, &a.SubjectName,
			&a.StatusText, &a.OccurredAt, &a.ActionType, &a.Severity,
		); err != nil {
			return nil, err
		}
		list = append(list, a)
	}
	return list, nil
}

func (s *Store) GetSummary() (MigrationHomeSummaryDTO, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	var summary MigrationHomeSummaryDTO

	// Compute derived counts from migrations
	err := s.db.QueryRow(`
		SELECT 
			COUNT(CASE WHEN lifecycle_state = 'ACTIVE' OR lifecycle_state = 'RUNNING' THEN 1 END),
			COUNT(CASE WHEN lifecycle_state = 'ATTENTION' OR attention_level IS NOT NULL THEN 1 END),
			COUNT(CASE WHEN lifecycle_state = 'SCHEDULED' THEN 1 END),
			COUNT(CASE WHEN lifecycle_state = 'COMPLETED' THEN 1 END),
			COUNT(*)
		FROM migration_home_migrations
	`).Scan(&summary.ActiveCount, &summary.AttentionCount, &summary.ScheduledCount, &summary.CompletedCount, &summary.TotalCount)
	if err != nil {
		return summary, err
	}

	// Determine dynamic subtext using prioritized selector (Section 13)
	summary.DynamicHeadline = s.computeDynamicHeadline(summary)

	return summary, nil
}

func (s *Store) computeDynamicHeadline(summary MigrationHomeSummaryDTO) string {
	if summary.TotalCount == 0 {
		return "Clean slate. Pick where the data goes next."
	}
	if summary.AttentionCount > 0 {
		return "The next move is waiting on a decision."
	}
	if summary.ActiveCount >= 5 {
		return "The fleet is busy. The important bits are below."
	}
	if summary.ActiveCount > 0 {
		return "Things are moving. Nothing important is hiding."
	}
	if summary.ScheduledCount > 0 {
		return "The next moves are already lined up."
	}
	if summary.CompletedCount > 0 {
		return "Another one across. The next move is yours."
	}
	return "Nothing urgent. Everything ready when you are."
}

func (s *Store) ResetDemoState() error {
	s.mu.Lock()
	defer s.mu.Unlock()

	_, _ = s.db.Exec("DELETE FROM migration_home_migrations")
	_, _ = s.db.Exec("DELETE FROM migration_home_projects")
	_, _ = s.db.Exec("DELETE FROM migration_home_activity")

	s.mu.Unlock()
	return s.seedIfEmpty()
}
