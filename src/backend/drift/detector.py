"""
Drift and Change Detection Engine for DataPulse.
Compares scan results across time to detect new tables, new columns,
new personal data categories, schema alterations, and policy drift.
"""
import sqlite3
from typing import Dict, List, Any, Optional
from datetime import datetime
from ..db.app_db import get_app_db_connection

class DriftDetector:
    """Detects differences between successive scan runs for the same or related data sources."""

    def compare_scans(self, current_run_id: int, previous_run_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Compares `current_run_id` with `previous_run_id`.
        If `previous_run_id` is None, looks up the latest prior completed scan for the same source.
        Returns list of detected drift events and stores them in drift_events table.
        """
        conn = get_app_db_connection()
        cur = conn.cursor()

        # Fetch current run details
        cur.execute("SELECT * FROM scan_runs WHERE id = ?", (current_run_id,))
        curr_run = cur.fetchone()
        if not curr_run:
            conn.close()
            return []

        source_id = curr_run["source_id"]

        # If previous_run_id not specified, find previous successful run
        if previous_run_id is None:
            cur.execute("""
                SELECT id FROM scan_runs
                WHERE source_id = ? AND id < ? AND status = 'COMPLETED'
                ORDER BY id DESC LIMIT 1
            """, (source_id, current_run_id))
            prev_row = cur.fetchone()
            if prev_row:
                previous_run_id = prev_row["id"]

        drift_events = []

        if not previous_run_id:
            # Baseline initial scan — record baseline establishment event
            now_iso = datetime.now().isoformat()
            cur.execute("""
                INSERT INTO drift_events (scan_run_id, previous_scan_run_id, source_id, event_type, details, detected_at)
                VALUES (?, NULL, ?, 'BASELINE_ESTABLISHED', ?, ?)
            """, (current_run_id, source_id, f"Initial baseline scan completed with {curr_run['tables_discovered']} tables and {curr_run['columns_inspected']} columns.", now_iso))
            conn.commit()
            conn.close()
            return [{
                "event_type": "BASELINE_ESTABLISHED",
                "table_name": None,
                "column_name": None,
                "details": f"Initial baseline scan completed with {curr_run['tables_discovered']} tables and {curr_run['columns_inspected']} columns.",
                "detected_at": now_iso
            }]

        # Fetch items from current scan
        cur.execute("SELECT * FROM inventory_items WHERE scan_run_id = ?", (current_run_id,))
        curr_items = { (r["table_name"], r["column_name"]): dict(r) for r in cur.fetchall() }

        # Fetch items from previous scan
        cur.execute("SELECT * FROM inventory_items WHERE scan_run_id = ?", (previous_run_id,))
        prev_items = { (r["table_name"], r["column_name"]): dict(r) for r in cur.fetchall() }

        now_iso = datetime.now().isoformat()

        # Tables in current vs previous
        curr_tables = set(t for t, _ in curr_items.keys())
        prev_tables = set(t for t, _ in prev_items.keys())

        # 1. Check for New Tables
        for new_tbl in (curr_tables - prev_tables):
            event = {
                "scan_run_id": current_run_id,
                "previous_scan_run_id": previous_run_id,
                "source_id": source_id,
                "event_type": "NEW_TABLE",
                "table_name": new_tbl,
                "column_name": None,
                "details": f"New table '{new_tbl}' discovered in data source.",
                "detected_at": now_iso
            }
            drift_events.append(event)

        # 2. Check for Removed Tables
        for rem_tbl in (prev_tables - curr_tables):
            event = {
                "scan_run_id": current_run_id,
                "previous_scan_run_id": previous_run_id,
                "source_id": source_id,
                "event_type": "REMOVED_TABLE",
                "table_name": rem_tbl,
                "column_name": None,
                "details": f"Table '{rem_tbl}' is no longer present in source.",
                "detected_at": now_iso
            }
            drift_events.append(event)

        # 3. Check for Column Additions & Category Drift
        for (tbl, col), curr_data in curr_items.items():
            if (tbl, col) not in prev_items:
                # Newly added column!
                is_pii = curr_data["detected_category"] != "NONE"
                event_type = "NEW_PERSONAL_DATA" if is_pii else "NEW_COLUMN"
                details = (
                    f"New column '{col}' discovered in table '{tbl}' containing personal data ({curr_data['detected_category']})."
                    if is_pii else
                    f"New non-personal column '{col}' discovered in table '{tbl}'."
                )
                drift_events.append({
                    "scan_run_id": current_run_id,
                    "previous_scan_run_id": previous_run_id,
                    "source_id": source_id,
                    "event_type": event_type,
                    "table_name": tbl,
                    "column_name": col,
                    "details": details,
                    "detected_at": now_iso
                })
            else:
                prev_data = prev_items[(tbl, col)]
                # Category drift (e.g. was NONE before, now personal data or changed category)
                if curr_data["detected_category"] != prev_data["detected_category"]:
                    drift_events.append({
                        "scan_run_id": current_run_id,
                        "previous_scan_run_id": previous_run_id,
                        "source_id": source_id,
                        "event_type": "CATEGORY_DRIFT",
                        "table_name": tbl,
                        "column_name": col,
                        "details": f"Classification changed for '{col}' from '{prev_data['detected_category']}' to '{curr_data['detected_category']}'.",
                        "detected_at": now_iso
                    })

                # Policy retention rule changed!
                curr_ret = (curr_data.get("retention_rule") or "").strip()
                prev_ret = (prev_data.get("retention_rule") or "").strip()
                if curr_ret and prev_ret and curr_ret != prev_ret:
                    drift_events.append({
                        "scan_run_id": current_run_id,
                        "previous_scan_run_id": previous_run_id,
                        "source_id": source_id,
                        "event_type": "POLICY_RETENTION_CHANGED",
                        "table_name": tbl,
                        "column_name": col,
                        "details": f"Retention rule for '{col}' changed from '{prev_ret}' to '{curr_ret}'.",
                        "detected_at": now_iso
                    })

                # Metadata completeness changed
                if curr_data["completeness_status"] != prev_data["completeness_status"]:
                    drift_events.append({
                        "scan_run_id": current_run_id,
                        "previous_scan_run_id": previous_run_id,
                        "source_id": source_id,
                        "event_type": "METADATA_COMPLETENESS_DRIFT",
                        "table_name": tbl,
                        "column_name": col,
                        "details": f"Documentation status for '{col}' changed from {prev_data['completeness_status']} to {curr_data['completeness_status']}.",
                        "detected_at": now_iso
                    })

        # 4. Check for Removed Columns
        for (tbl, col), prev_data in prev_items.items():
            if (tbl, col) not in curr_items:
                drift_events.append({
                    "scan_run_id": current_run_id,
                    "previous_scan_run_id": previous_run_id,
                    "source_id": source_id,
                    "event_type": "REMOVED_COLUMN",
                    "table_name": tbl,
                    "column_name": col,
                    "details": f"Column '{col}' in table '{tbl}' was removed or dropped.",
                    "detected_at": now_iso
                })

        # Persist drift events in database
        for ev in drift_events:
            cur.execute("""
                INSERT INTO drift_events (scan_run_id, previous_scan_run_id, source_id, event_type, table_name, column_name, details, detected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (ev["scan_run_id"], ev["previous_scan_run_id"], ev["source_id"], ev["event_type"], ev["table_name"], ev["column_name"], ev["details"], ev["detected_at"]))

        conn.commit()
        conn.close()
        return drift_events
