"""
Application persistence database for DataPulse.
Stored locally in `src/backend/data/privacy_inventory.sqlite`.
Strictly isolated from source database.
"""
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from ..config import INVENTORY_DB_PATH

def get_app_db_connection() -> sqlite3.Connection:
    """Connect to the local application database with row factory."""
    INVENTORY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(INVENTORY_DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for concurrent reads/writes
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_app_database():
    """Initializes tables for scan runs, inventory items, drift events, and overrides."""
    conn = get_app_db_connection()
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS scan_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id TEXT NOT NULL,
        source_type TEXT NOT NULL,  -- 'sqlite', 'csv_collection', 'holdout_csv'
        source_path TEXT NOT NULL,
        status TEXT NOT NULL,       -- 'RUNNING', 'COMPLETED', 'FAILED', 'PARTIAL'
        started_at TEXT NOT NULL,
        completed_at TEXT,
        tables_discovered INTEGER DEFAULT 0,
        columns_inspected INTEGER DEFAULT 0,
        personal_columns_detected INTEGER DEFAULT 0,
        missing_purpose_count INTEGER DEFAULT 0,
        missing_retention_count INTEGER DEFAULT 0,
        error_message TEXT
    );

    CREATE TABLE IF NOT EXISTS inventory_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scan_run_id INTEGER NOT NULL,
        source_id TEXT NOT NULL,
        table_name TEXT NOT NULL,
        column_name TEXT NOT NULL,
        data_type TEXT NOT NULL,
        detected_category TEXT NOT NULL, -- 'PERSON_NAME', 'EMAIL', 'PHONE', 'DATE_OF_BIRTH', 'GOVERNMENT_ID', 'NONE'
        confidence REAL NOT NULL,
        detection_method TEXT NOT NULL,
        matching_values_count INTEGER DEFAULT 0,
        sample_total_count INTEGER DEFAULT 0,
        declared_purpose TEXT,
        retention_rule TEXT,
        policy_version TEXT,
        review_owner TEXT,
        review_status TEXT DEFAULT 'pending', -- 'pending', 'verified', 'rejected', 'dismissed'
        completeness_status TEXT,             -- 'COMPLETE', 'MISSING_PURPOSE', 'MISSING_RETENTION', 'MISSING_BOTH', 'NOT_APPLICABLE'
        notes TEXT,
        first_discovered_at TEXT NOT NULL,
        last_scanned_at TEXT NOT NULL,
        FOREIGN KEY (scan_run_id) REFERENCES scan_runs(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS user_metadata_overrides (
        source_id TEXT NOT NULL,
        table_name TEXT NOT NULL,
        column_name TEXT NOT NULL,
        purpose TEXT,
        retention_rule TEXT,
        review_status TEXT,
        notes TEXT,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (source_id, table_name, column_name)
    );

    CREATE TABLE IF NOT EXISTS drift_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scan_run_id INTEGER NOT NULL,
        previous_scan_run_id INTEGER,
        source_id TEXT NOT NULL,
        event_type TEXT NOT NULL, -- 'NEW_TABLE', 'NEW_COLUMN', 'NEW_PERSONAL_DATA', 'REMOVED_COLUMN', 'PURPOSE_GAP', 'RETENTION_GAP', 'POLICY_RETENTION_CHANGED', 'SCAN_FAILED'
        table_name TEXT,
        column_name TEXT,
        details TEXT NOT NULL,
        detected_at TEXT NOT NULL,
        FOREIGN KEY (scan_run_id) REFERENCES scan_runs(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_inv_source_tbl ON inventory_items(source_id, table_name);
    CREATE INDEX IF NOT EXISTS idx_inv_category ON inventory_items(detected_category);
    CREATE INDEX IF NOT EXISTS idx_drift_scan ON drift_events(scan_run_id);
    """)

    conn.commit()
    conn.close()
