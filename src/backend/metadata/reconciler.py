"""
Declared Metadata Reconciliation Module for DataPulse.
Loads declared policy metadata (V1 or V2), reconciles against discovered columns,
and flags privacy gaps (missing purpose, missing retention, policy drift).
"""
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from ..config import DECLARED_METADATA_V1, DECLARED_METADATA_V2

class MetadataReconciler:
    """Reconciles discovered data elements with declared company privacy policies."""

    def __init__(self, metadata_path: Optional[Path] = None):
        self.metadata_path = metadata_path or DECLARED_METADATA_V1
        self.policy_version = "v1"
        self.declared_entries: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.load_metadata(self.metadata_path)

    def load_metadata(self, path: Path):
        """Loads and indexes declared metadata CSV by (normalized_source, normalized_column)."""
        self.metadata_path = path
        self.declared_entries.clear()
        if not path.exists():
            return

        with open(path, mode="r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                src = self._normalize_source(row.get("source", ""))
                col = row.get("column", "").strip().lower()
                purpose = row.get("purpose", "").strip()
                retention = row.get("retention_rule", "").strip()
                policy_ver = row.get("policy_version", "v1").strip()
                review_owner = row.get("review_owner", "Privacy Team").strip()
                self.policy_version = policy_ver

                self.declared_entries[(src, col)] = {
                    "source": src,
                    "column": col,
                    "purpose": purpose,
                    "retention_rule": retention,
                    "policy_version": policy_ver,
                    "review_owner": review_owner
                }

    def _normalize_source(self, source_name: str) -> str:
        """
        Normalizes various representations of sources to standard logical names.
        Examples:
        'marketing_leads_v1.csv' -> 'marketing_leads'
        'marketing_leads_v2.csv' -> 'marketing_leads'
        'sql/marketing_company.sqlite::lead_interactions' -> 'lead_interactions'
        'lead_interactions' -> 'lead_interactions'
        'customers.csv' -> 'customers'
        'employees.csv' -> 'employees'
        """
        s = source_name.lower().replace("\\", "/").strip()
        if "::" in s:
            s = s.split("::")[-1]
        elif "/" in s:
            s = s.split("/")[-1]

        if s.endswith(".csv"):
            s = s[:-4]

        # Handle V1 / V2 logical mapping as per Dataset README
        if s.startswith("marketing_leads"):
            return "marketing_leads"

        return s

    def reconcile(self, source_name: str, table_name: str, column_name: str, detected_category: str) -> Dict[str, Any]:
        """
        Reconciles a discovered column with declared metadata.
        Returns declared details and completeness status.
        """
        if detected_category == "NONE":
            return {
                "declared_purpose": None,
                "retention_rule": None,
                "policy_version": self.policy_version,
                "review_owner": None,
                "completeness_status": "NOT_APPLICABLE",
                "is_declared": False
            }

        # Try matching table name first, then source name
        norm_tbl = self._normalize_source(table_name)
        norm_src = self._normalize_source(source_name)
        col_lower = column_name.strip().lower()

        entry = self.declared_entries.get((norm_tbl, col_lower))
        if not entry:
            entry = self.declared_entries.get((norm_src, col_lower))

        if not entry:
            # Personal data detected but completely absent from declared metadata
            return {
                "declared_purpose": "",
                "retention_rule": "",
                "policy_version": self.policy_version,
                "review_owner": "Unassigned",
                "completeness_status": "MISSING_BOTH",
                "is_declared": False
            }

        purpose = entry.get("purpose", "")
        retention = entry.get("retention_rule", "")

        has_purpose = bool(purpose and purpose.strip())
        has_retention = bool(retention and retention.strip())

        if has_purpose and has_retention:
            completeness = "COMPLETE"
        elif not has_purpose and not has_retention:
            completeness = "MISSING_BOTH"
        elif not has_purpose:
            completeness = "MISSING_PURPOSE"
        else:
            completeness = "MISSING_RETENTION"

        return {
            "declared_purpose": purpose,
            "retention_rule": retention,
            "policy_version": entry.get("policy_version", self.policy_version),
            "review_owner": entry.get("review_owner", "Privacy Team"),
            "completeness_status": completeness,
            "is_declared": True
        }
