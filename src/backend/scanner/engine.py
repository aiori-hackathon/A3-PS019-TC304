"""
Personal-Data Scanning Engine for DataPulse.
Combines schema heuristics, regex patterns, negative guards, and value-level inspection.
"""
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
from ..config import CLASSES_JSON_PATH

class PersonalDataScanner:
    """Configurable rule-based scanner for discovering personal data fields."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or CLASSES_JSON_PATH
        self.classes = {}
        self.negative_label = "NONE"
        self._load_config()

        # Regular expressions for value validation
        self.EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
        self.PHONE_REGEX = re.compile(r"^\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$")
        self.GOV_ID_REGEX = re.compile(r"^FICTIONAL-ID-\d+$", re.IGNORECASE)
        # Year range: 1920-2015 for realistic birth dates (distinguishing from modern event dates like 2026)
        self.DOB_REGEX = re.compile(r"^(19\d\d|200\d|201[0-5])[-/.](0[1-9]|1[0-2])[-/.](0[1-9]|[12]\d|3[01])$")

        # Negative guards (hard negatives and context protection)
        self.NEGATIVE_COL_PATTERNS = [
            r"campaign_name", r"campaign_code", r"email_template", r"tracking_email_template",
            r"event_date", r"report_date", r"revenue", r"revenue_usd", r"spend", r"spend_usd",
            r"impressions", r"clicks", r"budget", r"budget_usd", r"conversion", r"conversion_rate",
            r"phone_model", r"government_id_policy", r"birth_date_label", r"account_name",
            r"organization", r"company_name", r"account_manager_role", r"product_code",
            r"serial_number", r"asset_id", r"case_id", r"lead_id", r"customer_id",
            r"interaction_id", r"employee_code", r"department", r"job_title", r"desk_extension",
            r"lead_source", r"lead_score", r"consent_status", r"created_at", r"contract_start",
            r"customer_status", r"start_date", r"end_date", r"channel", r"outcome", r"duration",
            r"call_duration_seconds", r"preferred_contact_window", r"region", r"account_tier",
            r"policy_version", r"review_owner"
        ]

    def _load_config(self):
        """Loads personal data classes from classes.json."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.classes = data.get("classes", {})
                    self.negative_label = data.get("negative_label", "NONE")
            except Exception as e:
                # Fallback to standard PS-019 classes
                self._load_default_classes()
        else:
            self._load_default_classes()

    def _load_default_classes(self):
        self.classes = {
            "PERSON_NAME": "Name of an individual, not an organization or campaign",
            "EMAIL": "Individual contact email, not a generic campaign template address",
            "PHONE": "Individual contact phone, not a product label or serial",
            "DATE_OF_BIRTH": "Date of birth of a person, not an event date",
            "GOVERNMENT_ID": "Fictional government-ID surrogate; not a valid real government ID"
        }
        self.negative_label = "NONE"

    def classify_column(self, source_name: str, table_name: str, col_name: str, sample_values: List[Any]) -> Dict[str, Any]:
        """
        Classifies a single column using combined heuristics, regex, and value inspection.
        Returns detailed classification result dictionary.
        """
        col_lower = col_name.lower().strip()
        clean_samples = [
            str(v).strip() for v in sample_values
            if v is not None and str(v).strip() != "" and str(v).lower() not in ("nan", "none", "<null>")
        ]
        sample_count = len(clean_samples)

        # 1. Negative Guards Check
        for neg_pat in self.NEGATIVE_COL_PATTERNS:
            if re.search(r"^" + neg_pat + r"$", col_lower):
                return {
                    "category": self.negative_label,
                    "confidence": 0.95,
                    "detection_method": "contextual_negative_guard",
                    "matching_values_count": 0,
                    "sample_count": sample_count,
                    "reasoning": f"Column '{col_name}' matched non-personal exclusion rule '{neg_pat}'"
                }

        # Context exclusion for template/label/policy/model/serial
        if any(term in col_lower for term in ["template", "policy", "model", "serial", "code"]):
            return {
                "category": self.negative_label,
                "confidence": 0.95,
                "detection_method": "non_personal_semantic_exclusion",
                "matching_values_count": 0,
                "sample_count": sample_count,
                "reasoning": f"Column '{col_name}' contains non-personal token indicator"
            }

        # 2. Government ID Check
        if any(k in col_lower for k in ["gov_id", "identity_token", "id_reference", "government_id"]):
            match_cnt = sum(1 for v in clean_samples if self.GOV_ID_REGEX.search(v))
            confidence = 0.98 if match_cnt > 0 else (0.85 if sample_count == 0 else 0.70)
            return {
                "category": "GOVERNMENT_ID",
                "confidence": confidence,
                "detection_method": "regex_and_column_heuristic" if match_cnt > 0 else "column_heuristic",
                "matching_values_count": match_cnt,
                "sample_count": sample_count,
                "reasoning": f"Matched government ID token pattern ({match_cnt}/{sample_count} values)"
            }

        # 3. Date of Birth Check
        if any(k in col_lower for k in ["birth_date", "date_of_birth", "dob", "dob_value"]):
            if "label" not in col_lower:
                match_cnt = sum(1 for v in clean_samples if self.DOB_REGEX.search(v))
                confidence = 0.95 if match_cnt > 0 else (0.85 if sample_count == 0 else 0.70)
                return {
                    "category": "DATE_OF_BIRTH",
                    "confidence": confidence,
                    "detection_method": "regex_and_column_heuristic" if match_cnt > 0 else "column_heuristic",
                    "matching_values_count": match_cnt,
                    "sample_count": sample_count,
                    "reasoning": f"Matched historical birth date format ({match_cnt}/{sample_count} values)"
                }

        # 4. Email Check
        if ("email" in col_lower and "template" not in col_lower) or col_lower in ["contact_channel", "reply_to_email"]:
            match_cnt = sum(1 for v in clean_samples if self.EMAIL_REGEX.search(v))
            if match_cnt > 0:
                return {
                    "category": "EMAIL",
                    "confidence": 0.99,
                    "detection_method": "regex_pattern_match",
                    "matching_values_count": match_cnt,
                    "sample_count": sample_count,
                    "reasoning": f"Validated email pattern across {match_cnt}/{sample_count} samples"
                }
            if "email" in col_lower:
                return {
                    "category": "EMAIL",
                    "confidence": 0.80,
                    "detection_method": "column_heuristic",
                    "matching_values_count": 0,
                    "sample_count": sample_count,
                    "reasoning": "Column name indicates email, no matching sample data"
                }

        # 5. Phone Check
        if any(k in col_lower for k in ["mobile_phone", "contact_number", "emergency_contact_phone", "reach_number"]) or (col_lower.endswith("phone") and "model" not in col_lower):
            match_cnt = sum(1 for v in clean_samples if self.PHONE_REGEX.search(v))
            confidence = 0.95 if match_cnt > 0 else (0.85 if sample_count == 0 else 0.70)
            return {
                "category": "PHONE",
                "confidence": confidence,
                "detection_method": "phone_pattern_match" if match_cnt > 0 else "column_heuristic",
                "matching_values_count": match_cnt,
                "sample_count": sample_count,
                "reasoning": f"Validated telephone format ({match_cnt}/{sample_count} samples)"
            }

        # 6. Person Name Check
        # Strict context check: only personal contacts/agents/employees, NOT campaign_name or account_name
        if any(k in col_lower for k in ["contact_name", "account_contact", "employee_full_name", "agent_name", "primary_contact"]):
            return {
                "category": "PERSON_NAME",
                "confidence": 0.92,
                "detection_method": "person_name_heuristic",
                "matching_values_count": sample_count,
                "sample_count": sample_count,
                "reasoning": f"Contextual individual contact name column with {sample_count} records"
            }

        if col_lower in ["full_name", "first_name", "last_name", "person_name"]:
            return {
                "category": "PERSON_NAME",
                "confidence": 0.90,
                "detection_method": "person_name_heuristic",
                "matching_values_count": sample_count,
                "sample_count": sample_count,
                "reasoning": "Standard individual name column identifier"
            }

        # 7. Value-level Fallback Pattern Analysis
        if clean_samples:
            gov_matches = sum(1 for v in clean_samples if self.GOV_ID_REGEX.search(v))
            if gov_matches / sample_count >= 0.5:
                return {
                    "category": "GOVERNMENT_ID",
                    "confidence": 0.95,
                    "detection_method": "value_level_regex_inspection",
                    "matching_values_count": gov_matches,
                    "sample_count": sample_count,
                    "reasoning": f"Over 50% values match government ID pattern ({gov_matches}/{sample_count})"
                }

            email_matches = sum(1 for v in clean_samples if self.EMAIL_REGEX.search(v))
            if email_matches / sample_count >= 0.5 and "template" not in col_lower:
                return {
                    "category": "EMAIL",
                    "confidence": 0.95,
                    "detection_method": "value_level_regex_inspection",
                    "matching_values_count": email_matches,
                    "sample_count": sample_count,
                    "reasoning": f"Over 50% values match email pattern ({email_matches}/{sample_count})"
                }

            phone_matches = sum(1 for v in clean_samples if self.PHONE_REGEX.search(v))
            if phone_matches / sample_count >= 0.5 and "serial" not in col_lower:
                return {
                    "category": "PHONE",
                    "confidence": 0.90,
                    "detection_method": "value_level_regex_inspection",
                    "matching_values_count": phone_matches,
                    "sample_count": sample_count,
                    "reasoning": f"Over 50% values match telephone pattern ({phone_matches}/{sample_count})"
                }

        # Negative default
        return {
            "category": self.negative_label,
            "confidence": 0.90,
            "detection_method": "no_personal_indicators",
            "matching_values_count": 0,
            "sample_count": sample_count,
            "reasoning": "No personal data patterns or heuristics detected"
        }
