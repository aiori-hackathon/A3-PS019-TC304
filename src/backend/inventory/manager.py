"""
Inventory Manager for DataPulse.
Handles scan execution orchestration, inventory persistence, search,
filtering, metadata overrides, and statistical aggregations.
"""
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from ..config import (
    DEFAULT_SQLITE_PATH, CSV_DIR, DATASET_DIR,
    DECLARED_METADATA_V1, DECLARED_METADATA_V2
)
from ..db.connector import SQLiteConnector
from ..db.app_db import get_app_db_connection, init_app_database
from ..scanner.engine import PersonalDataScanner
from ..scanner.masking import mask_record_dict, mask_value_by_category
from ..metadata.reconciler import MetadataReconciler
from ..drift.detector import DriftDetector

class InventoryManager:
    """Core coordinator for scanning data sources, updating inventory, and querying findings."""

    def __init__(self):
        init_app_database()
        self.scanner = PersonalDataScanner()
        self.reconciler = MetadataReconciler()
        self.drift_detector = DriftDetector()

    def run_database_scan(self, db_path: Optional[Path] = None, policy_version: str = "v1") -> Dict[str, Any]:
        """
        Executes a complete scan against the SQLite database.
        Discovers tables and columns dynamically, scans sample values,
        reconciles with declared metadata, applies user overrides, records scan history,
        and triggers drift detection against previous scan.
        """
        target_path = Path(db_path) if db_path else DEFAULT_SQLITE_PATH
        connector = SQLiteConnector(target_path)
        is_conn, msg = connector.test_connection()

        started_at = datetime.now().isoformat()
        conn = get_app_db_connection()
        cur = conn.cursor()

        # Load appropriate metadata version
        meta_file = DECLARED_METADATA_V2 if policy_version == "v2" else DECLARED_METADATA_V1
        self.reconciler.load_metadata(meta_file)

        source_id = f"sqlite::{target_path.name}"

        # Initialize scan run record
        cur.execute("""
            INSERT INTO scan_runs (source_id, source_type, source_path, status, started_at)
            VALUES (?, 'sqlite', ?, 'RUNNING', ?)
        """, (source_id, str(target_path), started_at))
        scan_run_id = cur.lastrowid
        conn.commit()

        if not is_conn:
            # Handle database connection failure gracefully
            cur.execute("""
                UPDATE scan_runs
                SET status = 'FAILED', completed_at = ?, error_message = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), msg, scan_run_id))
            conn.commit()
            conn.close()
            return {
                "scan_run_id": scan_run_id,
                "status": "FAILED",
                "error": msg,
                "tables_scanned": 0,
                "columns_scanned": 0,
                "personal_data_columns": 0
            }

        try:
            # Discover schema dynamically
            tables_meta = connector.discover_schema()
            total_tables = len(tables_meta)
            total_columns = 0
            personal_cols_count = 0
            missing_purpose_cnt = 0
            missing_retention_cnt = 0

            # Load persistent user overrides
            cur.execute("SELECT * FROM user_metadata_overrides WHERE source_id = ?", (source_id,))
            overrides = { (r["table_name"], r["column_name"]): dict(r) for r in cur.fetchall() }

            now_iso = datetime.now().isoformat()

            for tbl in tables_meta:
                tbl_name = tbl["table_name"]
                # Fetch up to 100 sample records for inspection
                sample_records = connector.fetch_sample_records(tbl_name, limit=100)

                for col in tbl["columns"]:
                    total_columns += 1
                    col_name = col["name"]
                    data_type = col["type"]

                    # Extract sample values for this column
                    sample_vals = [r.get(col_name) for r in sample_records]

                    # Perform classification
                    classification = self.scanner.classify_column(
                        source_name=source_id,
                        table_name=tbl_name,
                        col_name=col_name,
                        sample_values=sample_vals
                    )

                    category = classification["category"]
                    confidence = classification["confidence"]
                    det_method = classification["detection_method"]
                    matches_cnt = classification["matching_values_count"]
                    samples_total = classification["sample_count"]

                    is_personal = (category != "NONE")
                    if is_personal:
                        personal_cols_count += 1

                    # Reconcile with declared metadata
                    rec = self.reconciler.reconcile(
                        source_name=source_id,
                        table_name=tbl_name,
                        column_name=col_name,
                        detected_category=category
                    )

                    declared_purpose = rec["declared_purpose"]
                    retention_rule = rec["retention_rule"]
                    policy_ver = rec["policy_version"]
                    review_owner = rec["review_owner"]
                    completeness = rec["completeness_status"]
                    review_status = "pending"
                    notes = classification["reasoning"]

                    # Apply user overrides if present
                    if (tbl_name, col_name) in overrides:
                        ov = overrides[(tbl_name, col_name)]
                        if ov.get("purpose") is not None:
                            declared_purpose = ov["purpose"]
                        if ov.get("retention_rule") is not None:
                            retention_rule = ov["retention_rule"]
                        if ov.get("review_status"):
                            review_status = ov["review_status"]
                        if ov.get("notes"):
                            notes = ov["notes"]

                        # Re-calculate completeness with override values
                        if is_personal:
                            has_p = bool(declared_purpose and declared_purpose.strip())
                            has_r = bool(retention_rule and retention_rule.strip())
                            if has_p and has_r:
                                completeness = "COMPLETE"
                            elif not has_p and not has_r:
                                completeness = "MISSING_BOTH"
                            elif not has_p:
                                completeness = "MISSING_PURPOSE"
                            else:
                                completeness = "MISSING_RETENTION"

                    if is_personal:
                        if completeness in ("MISSING_PURPOSE", "MISSING_BOTH"):
                            missing_purpose_cnt += 1
                        if completeness in ("MISSING_RETENTION", "MISSING_BOTH"):
                            missing_retention_cnt += 1

                    # Determine first_discovered_at timestamp from previous entries
                    cur.execute("""
                        SELECT first_discovered_at FROM inventory_items
                        WHERE source_id = ? AND table_name = ? AND column_name = ?
                        ORDER BY id ASC LIMIT 1
                    """, (source_id, tbl_name, col_name))
                    first_row = cur.fetchone()
                    first_discovered = first_row[0] if first_row else now_iso

                    # Insert inventory entry
                    cur.execute("""
                        INSERT INTO inventory_items (
                            scan_run_id, source_id, table_name, column_name, data_type,
                            detected_category, confidence, detection_method,
                            matching_values_count, sample_total_count,
                            declared_purpose, retention_rule, policy_version,
                            review_owner, review_status, completeness_status, notes,
                            first_discovered_at, last_scanned_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        scan_run_id, source_id, tbl_name, col_name, data_type,
                        category, confidence, det_method,
                        matches_cnt, samples_total,
                        declared_purpose, retention_rule, policy_ver,
                        review_owner, review_status, completeness, notes,
                        first_discovered, now_iso
                    ))

            # Update scan run record to COMPLETED
            completed_at = datetime.now().isoformat()
            cur.execute("""
                UPDATE scan_runs
                SET status = 'COMPLETED', completed_at = ?,
                    tables_discovered = ?, columns_inspected = ?,
                    personal_columns_detected = ?,
                    missing_purpose_count = ?, missing_retention_count = ?
                WHERE id = ?
            """, (
                completed_at, total_tables, total_columns,
                personal_cols_count, missing_purpose_cnt, missing_retention_cnt,
                scan_run_id
            ))
            conn.commit()

            # Execute drift detection against previous scan
            drift_events = self.drift_detector.compare_scans(current_run_id=scan_run_id)

            conn.close()

            return {
                "scan_run_id": scan_run_id,
                "status": "COMPLETED",
                "tables_scanned": total_tables,
                "columns_scanned": total_columns,
                "personal_data_columns": personal_cols_count,
                "missing_purpose_count": missing_purpose_cnt,
                "missing_retention_count": missing_retention_cnt,
                "drift_events_count": len(drift_events),
                "started_at": started_at,
                "completed_at": completed_at
            }

        except Exception as e:
            cur.execute("""
                UPDATE scan_runs
                SET status = 'FAILED', completed_at = ?, error_message = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), str(e), scan_run_id))
            conn.commit()
            conn.close()
            return {
                "scan_run_id": scan_run_id,
                "status": "FAILED",
                "error": str(e)
            }

    def run_csv_dataset_scan(self, csv_version: str = "v1") -> Dict[str, Any]:
        """
        Scans synthetic CSV datasets to demonstrate multi-source discovery and drift
        (e.g., comparing marketing_leads V1 vs V2 with secondary_email and policy change).
        """
        lead_csv = CSV_DIR / f"marketing_leads_{csv_version}.csv"
        customers_csv = CSV_DIR / "customers.csv"
        employees_csv = CSV_DIR / "employees.csv"
        campaigns_csv = CSV_DIR / "campaigns.csv"
        controls_csv = CSV_DIR / "non_personal_controls.csv"

        target_files = [
            ("marketing_leads", lead_csv),
            ("customers", customers_csv),
            ("employees", employees_csv),
            ("campaigns", campaigns_csv),
            ("non_personal_controls", controls_csv)
        ]

        started_at = datetime.now().isoformat()
        conn = get_app_db_connection()
        cur = conn.cursor()

        source_id = f"csv_collection::marketing_leads_{csv_version}"
        policy_ver = "v2" if csv_version == "v2" else "v1"
        meta_file = DECLARED_METADATA_V2 if csv_version == "v2" else DECLARED_METADATA_V1
        self.reconciler.load_metadata(meta_file)

        cur.execute("""
            INSERT INTO scan_runs (source_id, source_type, source_path, status, started_at)
            VALUES (?, 'csv_collection', ?, 'RUNNING', ?)
        """, (source_id, str(CSV_DIR), started_at))
        scan_run_id = cur.lastrowid
        conn.commit()

        try:
            total_tables = len(target_files)
            total_columns = 0
            personal_cols_count = 0
            missing_purpose_cnt = 0
            missing_retention_cnt = 0
            now_iso = datetime.now().isoformat()

            cur.execute("SELECT * FROM user_metadata_overrides WHERE source_id = ?", (source_id,))
            overrides = { (r["table_name"], r["column_name"]): dict(r) for r in cur.fetchall() }

            for logical_name, file_path in target_files:
                if not file_path.exists():
                    continue
                df = pd.read_csv(file_path)

                for col_name in df.columns:
                    total_columns += 1
                    sample_vals = df[col_name].dropna().head(100).tolist()
                    dtype_str = str(df[col_name].dtype)

                    classification = self.scanner.classify_column(
                        source_name=source_id,
                        table_name=logical_name,
                        col_name=col_name,
                        sample_values=sample_vals
                    )

                    category = classification["category"]
                    confidence = classification["confidence"]
                    det_method = classification["detection_method"]
                    matches_cnt = classification["matching_values_count"]
                    samples_total = classification["sample_count"]

                    is_personal = (category != "NONE")
                    if is_personal:
                        personal_cols_count += 1

                    rec = self.reconciler.reconcile(
                        source_name=source_id,
                        table_name=logical_name,
                        column_name=col_name,
                        detected_category=category
                    )

                    declared_purpose = rec["declared_purpose"]
                    retention_rule = rec["retention_rule"]
                    p_ver = rec["policy_version"]
                    review_owner = rec["review_owner"]
                    completeness = rec["completeness_status"]
                    review_status = "pending"
                    notes = classification["reasoning"]

                    if (logical_name, col_name) in overrides:
                        ov = overrides[(logical_name, col_name)]
                        if ov.get("purpose") is not None:
                            declared_purpose = ov["purpose"]
                        if ov.get("retention_rule") is not None:
                            retention_rule = ov["retention_rule"]
                        if ov.get("review_status"):
                            review_status = ov["review_status"]
                        if ov.get("notes"):
                            notes = ov["notes"]

                        if is_personal:
                            has_p = bool(declared_purpose and declared_purpose.strip())
                            has_r = bool(retention_rule and retention_rule.strip())
                            if has_p and has_r:
                                completeness = "COMPLETE"
                            elif not has_p and not has_r:
                                completeness = "MISSING_BOTH"
                            elif not has_p:
                                completeness = "MISSING_PURPOSE"
                            else:
                                completeness = "MISSING_RETENTION"

                    if is_personal:
                        if completeness in ("MISSING_PURPOSE", "MISSING_BOTH"):
                            missing_purpose_cnt += 1
                        if completeness in ("MISSING_RETENTION", "MISSING_BOTH"):
                            missing_retention_cnt += 1

                    cur.execute("""
                        INSERT INTO inventory_items (
                            scan_run_id, source_id, table_name, column_name, data_type,
                            detected_category, confidence, detection_method,
                            matching_values_count, sample_total_count,
                            declared_purpose, retention_rule, policy_version,
                            review_owner, review_status, completeness_status, notes,
                            first_discovered_at, last_scanned_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        scan_run_id, source_id, logical_name, col_name, dtype_str,
                        category, confidence, det_method,
                        matches_cnt, samples_total,
                        declared_purpose, retention_rule, p_ver,
                        review_owner, review_status, completeness, notes,
                        now_iso, now_iso
                    ))

            completed_at = datetime.now().isoformat()
            cur.execute("""
                UPDATE scan_runs
                SET status = 'COMPLETED', completed_at = ?,
                    tables_discovered = ?, columns_inspected = ?,
                    personal_columns_detected = ?,
                    missing_purpose_count = ?, missing_retention_count = ?
                WHERE id = ?
            """, (
                completed_at, total_tables, total_columns,
                personal_cols_count, missing_purpose_cnt, missing_retention_cnt,
                scan_run_id
            ))
            conn.commit()

            drift_events = self.drift_detector.compare_scans(current_run_id=scan_run_id)
            conn.close()

            return {
                "scan_run_id": scan_run_id,
                "status": "COMPLETED",
                "tables_scanned": total_tables,
                "columns_scanned": total_columns,
                "personal_data_columns": personal_cols_count,
                "missing_purpose_count": missing_purpose_cnt,
                "missing_retention_count": missing_retention_cnt,
                "drift_events_count": len(drift_events)
            }
        except Exception as e:
            cur.execute("UPDATE scan_runs SET status = 'FAILED', completed_at = ?, error_message = ? WHERE id = ?", (datetime.now().isoformat(), str(e), scan_run_id))
            conn.commit()
            conn.close()
            return {"scan_run_id": scan_run_id, "status": "FAILED", "error": str(e)}

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Calculates real-time metrics across scan history and latest inventory."""
        conn = get_app_db_connection()
        cur = conn.cursor()

        # Database connection check
        db_connector = SQLiteConnector(DEFAULT_SQLITE_PATH)
        is_connected, db_msg = db_connector.test_connection()

        # Latest scan run
        cur.execute("SELECT * FROM scan_runs ORDER BY id DESC LIMIT 1")
        latest_run = cur.fetchone()
        latest_run_dict = dict(latest_run) if latest_run else None

        # Counts from latest scan or overall
        if latest_run_dict and latest_run_dict["status"] == "COMPLETED":
            run_id = latest_run_dict["id"]
            cur.execute("SELECT COUNT(DISTINCT table_name) FROM inventory_items WHERE scan_run_id = ?", (run_id,))
            discovered_tables = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM inventory_items WHERE scan_run_id = ?", (run_id,))
            inspected_columns = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM inventory_items WHERE scan_run_id = ? AND detected_category != 'NONE'", (run_id,))
            personal_columns = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM inventory_items WHERE scan_run_id = ? AND detected_category != 'NONE' AND review_status = 'pending'", (run_id,))
            pending_reviews = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM inventory_items WHERE scan_run_id = ? AND detected_category != 'NONE' AND (declared_purpose IS NULL OR declared_purpose = '')", (run_id,))
            missing_purpose = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM inventory_items WHERE scan_run_id = ? AND detected_category != 'NONE' AND (retention_rule IS NULL OR retention_rule = '')", (run_id,))
            missing_retention = cur.fetchone()[0]

            # Category distribution
            cur.execute("""
                SELECT detected_category, COUNT(*) as cnt
                FROM inventory_items
                WHERE scan_run_id = ? AND detected_category != 'NONE'
                GROUP BY detected_category
            """, (run_id,))
            cat_distribution = { r[0]: r[1] for r in cur.fetchall() }
        else:
            discovered_tables = 0
            inspected_columns = 0
            personal_columns = 0
            pending_reviews = 0
            missing_purpose = 0
            missing_retention = 0
            cat_distribution = {}

        # Recent drift count
        cur.execute("SELECT COUNT(*) FROM drift_events")
        total_drift_events = cur.fetchone()[0]

        conn.close()

        return {
            "database_connected": is_connected,
            "database_status_message": db_msg,
            "database_path": str(DEFAULT_SQLITE_PATH),
            "discovered_tables": discovered_tables,
            "inspected_columns": inspected_columns,
            "personal_columns": personal_columns,
            "pending_reviews": pending_reviews,
            "missing_purpose": missing_purpose,
            "missing_retention": missing_retention,
            "total_drift_events": total_drift_events,
            "latest_scan": latest_run_dict,
            "category_distribution": cat_distribution
        }

    def query_inventory(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        table_name: Optional[str] = None,
        completeness: Optional[str] = None,
        review_status: Optional[str] = None,
        scan_run_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 15
    ) -> Dict[str, Any]:
        """Queries inventory with filtering, searching, and pagination."""
        conn = get_app_db_connection()
        cur = conn.cursor()

        # If scan_run_id not provided, default to latest completed scan
        if not scan_run_id:
            cur.execute("SELECT id FROM scan_runs WHERE status = 'COMPLETED' ORDER BY id DESC LIMIT 1")
            latest = cur.fetchone()
            scan_run_id = latest[0] if latest else -1

        where_clauses = ["scan_run_id = ?"]
        params = [scan_run_id]

        if search:
            term = f"%{search.strip()}%"
            where_clauses.append("(table_name LIKE ? OR column_name LIKE ? OR detected_category LIKE ? OR declared_purpose LIKE ? OR retention_rule LIKE ?)")
            params.extend([term, term, term, term, term])

        if category and category != "ALL":
            where_clauses.append("detected_category = ?")
            params.append(category)

        if table_name and table_name != "ALL":
            where_clauses.append("table_name = ?")
            params.append(table_name)

        if completeness and completeness != "ALL":
            where_clauses.append("completeness_status = ?")
            params.append(completeness)

        if review_status and review_status != "ALL":
            where_clauses.append("review_status = ?")
            params.append(review_status)

        where_sql = " AND ".join(where_clauses)

        # Count query
        cur.execute(f"SELECT COUNT(*) FROM inventory_items WHERE {where_sql}", params)
        total_items = cur.fetchone()[0]

        # Items query with pagination
        offset = (page - 1) * page_size
        params_with_paging = list(params) + [page_size, offset]
        cur.execute(f"""
            SELECT * FROM inventory_items
            WHERE {where_sql}
            ORDER BY
                CASE WHEN detected_category = 'NONE' THEN 1 ELSE 0 END,
                table_name ASC, column_name ASC
            LIMIT ? OFFSET ?
        """, params_with_paging)

        items = [dict(r) for r in cur.fetchall()]
        conn.close()

        return {
            "scan_run_id": scan_run_id,
            "total_items": total_items,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total_items + page_size - 1) // page_size),
            "items": items
        }

    def update_metadata_item(
        self,
        item_id: int,
        purpose: Optional[str] = None,
        retention_rule: Optional[str] = None,
        review_status: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Updates an inventory item and persists user overrides in user_metadata_overrides table.
        Does NOT alter source database.
        """
        conn = get_app_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM inventory_items WHERE id = ?", (item_id,))
        item = cur.fetchone()
        if not item:
            conn.close()
            return False

        source_id = item["source_id"]
        table_name = item["table_name"]
        col_name = item["column_name"]
        cat = item["detected_category"]

        new_purpose = purpose if purpose is not None else item["declared_purpose"]
        new_retention = retention_rule if retention_rule is not None else item["retention_rule"]
        new_status = review_status if review_status is not None else item["review_status"]
        new_notes = notes if notes is not None else item["notes"]

        # Re-evaluate completeness
        if cat != "NONE":
            has_p = bool(new_purpose and new_purpose.strip())
            has_r = bool(new_retention and new_retention.strip())
            if has_p and has_r:
                completeness = "COMPLETE"
            elif not has_p and not has_r:
                completeness = "MISSING_BOTH"
            elif not has_p:
                completeness = "MISSING_PURPOSE"
            else:
                completeness = "MISSING_RETENTION"
        else:
            completeness = "NOT_APPLICABLE"

        cur.execute("""
            UPDATE inventory_items
            SET declared_purpose = ?, retention_rule = ?, review_status = ?,
                completeness_status = ?, notes = ?
            WHERE id = ?
        """, (new_purpose, new_retention, new_status, completeness, new_notes, item_id))

        # Save to persistent user overrides table
        now_iso = datetime.now().isoformat()
        cur.execute("""
            INSERT INTO user_metadata_overrides (source_id, table_name, column_name, purpose, retention_rule, review_status, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id, table_name, column_name) DO UPDATE SET
                purpose = excluded.purpose,
                retention_rule = excluded.retention_rule,
                review_status = excluded.review_status,
                notes = excluded.notes,
                updated_at = excluded.updated_at
        """, (source_id, table_name, col_name, new_purpose, new_retention, new_status, new_notes, now_iso))

        conn.commit()
        conn.close()
        return True

    def get_masked_table_records(self, table_name: str, limit: int = 50, unmask_allowed: bool = False) -> Dict[str, Any]:
        """
        Retrieves table records from SQLite database with sensitive fields masked by default.
        """
        connector = SQLiteConnector(DEFAULT_SQLITE_PATH)
        raw_records = connector.fetch_sample_records(table_name, limit=limit)

        # Get column categories from latest inventory
        conn = get_app_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT column_name, detected_category
            FROM inventory_items
            WHERE table_name = ?
            ORDER BY id DESC
        """, (table_name,))
        col_cat_map = { r[0]: r[1] for r in cur.fetchall() }
        conn.close()

        records_output = []
        for r in raw_records:
            if unmask_allowed:
                records_output.append(r)
            else:
                records_output.append(mask_record_dict(r, col_cat_map))

        return {
            "table_name": table_name,
            "total_sample_records": len(records_output),
            "is_masked": not unmask_allowed,
            "column_categories": col_cat_map,
            "records": records_output
        }
