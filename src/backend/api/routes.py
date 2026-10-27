"""
FastAPI REST API Routes for DataPulse.
"""
from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from pathlib import Path

from ..config import DEFAULT_SQLITE_PATH, CSV_DIR
from ..db.connector import SQLiteConnector
from ..inventory.manager import InventoryManager
from ..evaluation.evaluator import SystemEvaluator
from ..reports.exporter import ReportExporter

router = APIRouter(prefix="/api")
inventory_mgr = InventoryManager()
evaluator = SystemEvaluator()

class ScanRequest(BaseModel):
    source_type: str = Field(default="sqlite", description="'sqlite' or 'csv_collection'")
    policy_version: str = Field(default="v1", description="'v1' or 'v2'")
    custom_path: Optional[str] = Field(default=None, description="Optional custom sqlite path")

class MetadataUpdateRequest(BaseModel):
    purpose: Optional[str] = None
    retention_rule: Optional[str] = None
    review_status: Optional[str] = None
    notes: Optional[str] = None

@router.get("/status")
def get_system_status():
    """Returns database connection status, path diagnostics, and high-level health."""
    connector = SQLiteConnector(DEFAULT_SQLITE_PATH)
    is_conn, msg = connector.test_connection()
    summary = inventory_mgr.get_dashboard_summary()
    return {
        "status": "healthy",
        "database_connected": is_conn,
        "database_message": msg,
        "database_path": str(DEFAULT_SQLITE_PATH),
        "database_exists": DEFAULT_SQLITE_PATH.exists(),
        "summary": summary
    }

@router.get("/tables")
def list_discovered_tables():
    """Discovers tables and columns dynamically from the SQLite database."""
    connector = SQLiteConnector(DEFAULT_SQLITE_PATH)
    is_conn, msg = connector.test_connection()
    if not is_conn:
        raise HTTPException(status_code=500, detail=f"Database inaccessible: {msg}")
    tables = connector.discover_schema()
    return {"tables": tables}

@router.get("/tables/{table_name}/records")
def get_table_records(table_name: str, limit: int = 50, unmask: bool = False):
    """Fetches sample records for browsing, with personal data masked by default."""
    try:
        data = inventory_mgr.get_masked_table_records(table_name, limit=limit, unmask_allowed=unmask)
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/scan")
def trigger_scan(req: ScanRequest):
    """Triggers a scan against the database or synthetic CSV collection."""
    if req.source_type == "sqlite":
        db_p = Path(req.custom_path) if req.custom_path else DEFAULT_SQLITE_PATH
        result = inventory_mgr.run_database_scan(db_path=db_p, policy_version=req.policy_version)
    elif req.source_type == "csv_collection":
        result = inventory_mgr.run_csv_dataset_scan(csv_version=req.policy_version)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown source type: {req.source_type}")
    return result

@router.get("/scan/history")
def get_scan_history(limit: int = 20):
    """Returns history of all scan runs."""
    from ..db.app_db import get_app_db_connection
    conn = get_app_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM scan_runs ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"scans": rows}

@router.get("/inventory")
def search_inventory(
    search: Optional[str] = None,
    category: Optional[str] = None,
    table_name: Optional[str] = None,
    completeness: Optional[str] = None,
    review_status: Optional[str] = None,
    scan_run_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 15
):
    """Search and filter inventory with pagination."""
    return inventory_mgr.query_inventory(
        search=search,
        category=category,
        table_name=table_name,
        completeness=completeness,
        review_status=review_status,
        scan_run_id=scan_run_id,
        page=page,
        page_size=page_size
    )

@router.patch("/inventory/{item_id}")
def update_inventory_item(item_id: int, req: MetadataUpdateRequest):
    """Updates purpose, retention rule, review status, or notes on an inventory item."""
    success = inventory_mgr.update_metadata_item(
        item_id=item_id,
        purpose=req.purpose,
        retention_rule=req.retention_rule,
        review_status=req.review_status,
        notes=req.notes
    )
    if not success:
        raise HTTPException(status_code=404, detail="Inventory item not found.")
    return {"success": True, "message": "Inventory metadata updated successfully."}

@router.get("/gaps")
def get_privacy_gaps(scan_run_id: Optional[int] = None):
    """Retrieves all personal data items missing purpose, retention, or awaiting review."""
    from ..db.app_db import get_app_db_connection
    conn = get_app_db_connection()
    cur = conn.cursor()

    if not scan_run_id:
        cur.execute("SELECT id FROM scan_runs WHERE status = 'COMPLETED' ORDER BY id DESC LIMIT 1")
        latest = cur.fetchone()
        scan_run_id = latest[0] if latest else -1

    cur.execute("""
        SELECT * FROM inventory_items
        WHERE scan_run_id = ? AND detected_category != 'NONE'
        AND (completeness_status != 'COMPLETE' OR review_status = 'pending')
        ORDER BY completeness_status DESC, table_name, column_name
    """, (scan_run_id,))
    gaps = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"scan_run_id": scan_run_id, "total_gaps": len(gaps), "gaps": gaps}

@router.get("/drift")
def get_drift_events(current_run_id: Optional[int] = None, previous_run_id: Optional[int] = None):
    """Retrieves drift comparison between two scans."""
    from ..db.app_db import get_app_db_connection
    conn = get_app_db_connection()
    cur = conn.cursor()

    if not current_run_id:
        cur.execute("SELECT id FROM scan_runs WHERE status = 'COMPLETED' ORDER BY id DESC LIMIT 1")
        latest = cur.fetchone()
        current_run_id = latest[0] if latest else -1

    cur.execute("""
        SELECT * FROM drift_events
        WHERE scan_run_id = ?
        ORDER BY id ASC
    """, (current_run_id,))
    events = [dict(r) for r in cur.fetchall()]

    # Also list available scan runs for comparison selector
    cur.execute("SELECT id, source_id, status, started_at, completed_at FROM scan_runs ORDER BY id DESC LIMIT 20")
    scans = [dict(r) for r in cur.fetchall()]
    conn.close()

    return {
        "current_run_id": current_run_id,
        "previous_run_id": previous_run_id,
        "total_events": len(events),
        "events": events,
        "available_scans": scans
    }

@router.get("/evaluation/holdout")
def get_holdout_evaluation():
    """Runs evaluation on holdout_test.csv against holdout_ground_truth.csv."""
    return evaluator.evaluate_holdout()

@router.get("/evaluation/development")
def get_development_evaluation():
    """Runs evaluation on development dataset against development_expected_columns.csv."""
    return evaluator.evaluate_development()

@router.get("/export/csv")
def export_csv(scan_run_id: Optional[int] = None):
    """Exports inventory as a CSV file."""
    csv_text = ReportExporter.generate_csv_inventory(scan_run_id=scan_run_id)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=datapulse_inventory_{scan_run_id or 'latest'}.csv"}
    )

@router.get("/export/pdf")
def export_pdf(scan_run_id: Optional[int] = None):
    """Exports inventory and drift summary as an enterprise PDF report."""
    pdf_bytes = ReportExporter.generate_pdf_report(scan_run_id=scan_run_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=datapulse_report_{scan_run_id or 'latest'}.pdf"}
    )
