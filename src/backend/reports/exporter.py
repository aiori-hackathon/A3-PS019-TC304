"""
Report Generation Module for DataPulse.
Generates comprehensive CSV inventory exports and enterprise-grade PDF audit reports.
"""
import io
import csv
from datetime import datetime
from typing import Dict, List, Any, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)

from ..db.app_db import get_app_db_connection

class ReportExporter:
    """Generates downloadable audit artifacts in CSV and PDF formats."""

    @staticmethod
    def generate_csv_inventory(scan_run_id: Optional[int] = None) -> str:
        """Exports the inventory items to a CSV string."""
        conn = get_app_db_connection()
        cur = conn.cursor()

        if not scan_run_id:
            cur.execute("SELECT id FROM scan_runs WHERE status = 'COMPLETED' ORDER BY id DESC LIMIT 1")
            latest = cur.fetchone()
            scan_run_id = latest[0] if latest else -1

        cur.execute("""
            SELECT
                source_id, table_name, column_name, data_type, detected_category,
                confidence, detection_method, declared_purpose, retention_rule,
                review_owner, review_status, completeness_status, notes, last_scanned_at
            FROM inventory_items
            WHERE scan_run_id = ?
            ORDER BY table_name, column_name
        """, (scan_run_id,))

        rows = cur.fetchall()
        conn.close()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Source", "Table", "Column", "Data Type", "Detected Category",
            "Confidence", "Detection Method", "Declared Purpose", "Retention Rule",
            "Review Owner", "Review Status", "Documentation Completeness", "Scanner Notes", "Last Scanned"
        ])

        for r in rows:
            writer.writerow(list(r))

        return output.getvalue()

    @staticmethod
    def generate_pdf_report(scan_run_id: Optional[int] = None) -> bytes:
        """
        Generates a formatted enterprise PDF report using ReportLab.
        Returns PDF bytes.
        """
        conn = get_app_db_connection()
        cur = conn.cursor()

        if not scan_run_id:
            cur.execute("SELECT id FROM scan_runs WHERE status = 'COMPLETED' ORDER BY id DESC LIMIT 1")
            latest = cur.fetchone()
            scan_run_id = latest[0] if latest else -1

        cur.execute("SELECT * FROM scan_runs WHERE id = ?", (scan_run_id,))
        run_row = cur.fetchone()
        run_data = dict(run_row) if run_row else {}

        # Fetch personal data findings
        cur.execute("""
            SELECT table_name, column_name, detected_category, confidence,
                   declared_purpose, retention_rule, review_status, completeness_status
            FROM inventory_items
            WHERE scan_run_id = ? AND detected_category != 'NONE'
            ORDER BY table_name, column_name
        """, (scan_run_id,))
        pii_items = [dict(r) for r in cur.fetchall()]

        # Fetch drift events
        cur.execute("""
            SELECT event_type, table_name, column_name, details, detected_at
            FROM drift_events
            WHERE scan_run_id = ?
            ORDER BY id ASC
        """, (scan_run_id,))
        drift_items = [dict(r) for r in cur.fetchall()]

        conn.close()

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()

        # Custom Enterprise Styling
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0f172a")
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#475569")
        )
        section_heading = ParagraphStyle(
            "SectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=14,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155")
        )
        table_text = ParagraphStyle(
            "TableText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1e293b")
        )
        table_header = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white
        )

        elements = []

        # Header Banner
        elements.append(Paragraph("DATAPULSE", title_style))
        elements.append(Paragraph("Personal-Data Discovery & Privacy Evidence Inventory Audit Report", subtitle_style))
        elements.append(Spacer(1, 8))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2563eb"), spaceAfter=12))

        # Metadata Card
        scan_time = run_data.get("completed_at", datetime.now().isoformat())
        meta_table_data = [
            [
                Paragraph("<b>Audit ID:</b>", body_style),
                Paragraph(f"PDR-RUN-{scan_run_id}", body_style),
                Paragraph("<b>Source Target:</b>", body_style),
                Paragraph(str(run_data.get("source_id", "N/A")), body_style)
            ],
            [
                Paragraph("<b>Audit Date:</b>", body_style),
                Paragraph(scan_time[:19].replace("T", " "), body_style),
                Paragraph("<b>Scan Status:</b>", body_style),
                Paragraph(str(run_data.get("status", "COMPLETED")), body_style)
            ]
        ]
        meta_table = Table(meta_table_data, colWidths=[80, 180, 80, 200])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#e2e8f0")),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 14))

        # Executive Metrics Summary
        elements.append(Paragraph("1. Executive Summary & Radar Metrics", section_heading))
        summary_data = [
            [
                Paragraph("Discovered Tables", table_header),
                Paragraph("Inspected Columns", table_header),
                Paragraph("Personal Data Columns", table_header),
                Paragraph("Missing Purpose", table_header),
                Paragraph("Missing Retention", table_header)
            ],
            [
                Paragraph(str(run_data.get("tables_discovered", 0)), body_style),
                Paragraph(str(run_data.get("columns_inspected", 0)), body_style),
                Paragraph(str(run_data.get("personal_columns_detected", len(pii_items))), body_style),
                Paragraph(str(run_data.get("missing_purpose_count", 0)), body_style),
                Paragraph(str(run_data.get("missing_retention_count", 0)), body_style),
            ]
        ]
        sum_table = Table(summary_data, colWidths=[108, 108, 108, 108, 108])
        sum_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(sum_table)
        elements.append(Spacer(1, 14))

        # Personal Data Findings Table
        elements.append(Paragraph("2. Discovered Personal Data Elements", section_heading))
        if pii_items:
            pii_table_data = [
                [
                    Paragraph("Table", table_header),
                    Paragraph("Column", table_header),
                    Paragraph("Category", table_header),
                    Paragraph("Declared Purpose", table_header),
                    Paragraph("Retention Rule", table_header),
                    Paragraph("Status", table_header)
                ]
            ]
            for itm in pii_items:
                purpose = itm.get("declared_purpose") or "<Missing Purpose>"
                retention = itm.get("retention_rule") or "<Missing Retention>"
                pii_table_data.append([
                    Paragraph(itm["table_name"], table_text),
                    Paragraph(itm["column_name"], table_text),
                    Paragraph(f"<b>{itm['detected_category']}</b>", table_text),
                    Paragraph(purpose, table_text),
                    Paragraph(retention, table_text),
                    Paragraph(itm["completeness_status"], table_text),
                ])

            pii_tbl = Table(pii_table_data, colWidths=[90, 95, 85, 115, 95, 60])
            pii_tbl.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
                ('PADDING', (0,0), (-1,-1), 4),
            ]))
            elements.append(pii_tbl)
        else:
            elements.append(Paragraph("No personal data fields detected in this scan.", body_style))

        elements.append(Spacer(1, 14))

        # Drift & Change Events
        elements.append(Paragraph("3. Drift & Change Monitoring Log", section_heading))
        if drift_items:
            drift_data = [
                [
                    Paragraph("Event Type", table_header),
                    Paragraph("Target", table_header),
                    Paragraph("Details", table_header),
                    Paragraph("Timestamp", table_header)
                ]
            ]
            for ev in drift_items[:10]:
                target = f"{ev['table_name'] or ''}.{ev['column_name'] or ''}".strip(".")
                drift_data.append([
                    Paragraph(f"<b>{ev['event_type']}</b>", table_text),
                    Paragraph(target or "Source Root", table_text),
                    Paragraph(ev["details"], table_text),
                    Paragraph(ev["detected_at"][:19].replace("T", " "), table_text),
                ])

            drift_tbl = Table(drift_data, colWidths=[110, 90, 240, 100])
            drift_tbl.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2563eb")),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
                ('PADDING', (0,0), (-1,-1), 4),
            ]))
            elements.append(drift_tbl)
        else:
            elements.append(Paragraph("No drift events detected compared to previous baseline.", body_style))

        elements.append(Spacer(1, 20))
        elements.append(Paragraph("Generated by DataPulse — Confidential Compliance Documentation", subtitle_style))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
