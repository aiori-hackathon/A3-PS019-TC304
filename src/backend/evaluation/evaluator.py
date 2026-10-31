"""
Evaluation Module for DataPulse.
Directly implements the evaluation logic of Dataset/scripts/evaluate.py.
Computes per-class TP, FP, FN, Precision, and Recall against ground truth labels.
Keeps evaluation strictly separated from live inventory findings.
"""
import csv
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional

from ..config import (
    CLASSES_JSON_PATH, HOLDOUT_GROUND_TRUTH_PATH,
    DEV_EXPECTED_COLUMNS_PATH, CSV_DIR, DATASET_DIR
)
from ..scanner.engine import PersonalDataScanner

class SystemEvaluator:
    """Evaluates scanner accuracy against ground truth datasets."""

    def __init__(self):
        self.scanner = PersonalDataScanner()

        if CLASSES_JSON_PATH.exists():
            with open(CLASSES_JSON_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self.classes = list(cfg.get("classes", {}).keys())
        else:
            self.classes = list(self.scanner.classes.keys())

    def evaluate_holdout(self) -> Dict[str, Any]:
        """
        Runs scanner against holdout_test.csv and benchmarks against holdout_ground_truth.csv.
        Returns detailed classification breakdown and per-class precision/recall.
        """
        if not HOLDOUT_GROUND_TRUTH_PATH.exists():
            return {"error": "Holdout ground truth file not found."}

        holdout_csv = CSV_DIR / "holdout_test.csv"
        if not holdout_csv.exists():
            return {"error": "Holdout test CSV file not found."}

        df = pd.read_csv(holdout_csv)

        with open(HOLDOUT_GROUND_TRUTH_PATH, mode="r", encoding="utf-8") as f:
            gt_rows = list(csv.DictReader(f))

        predictions = []
        for row in gt_rows:
            col = row["column"]
            true_cls = row["true_class"]
            sample_vals = df[col].dropna().tolist() if col in df.columns else []

            classification = self.scanner.classify_column(
                source_name="csv/holdout_test.csv",
                table_name="holdout_test",
                col_name=col,
                sample_values=sample_vals
            )

            pred_cls = classification["category"]
            predictions.append({
                "source": row["source"],
                "column": col,
                "true_class": true_cls,
                "predicted_class": pred_cls,
                "confidence": classification["confidence"],
                "method": classification["detection_method"],
                "rationale": row.get("rationale", ""),
                "is_match": (true_cls == pred_cls)
            })

        # Calculate per-class metrics
        class_metrics = []
        total_tp = 0
        total_fp = 0
        total_fn = 0

        for cls in self.classes:
            tp = sum(1 for p in predictions if p["true_class"] == cls and p["predicted_class"] == cls)
            fp = sum(1 for p in predictions if p["true_class"] != cls and p["predicted_class"] == cls)
            fn = sum(1 for p in predictions if p["true_class"] == cls and p["predicted_class"] != cls)

            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

            total_tp += tp
            total_fp += fp
            total_fn += fn

            class_metrics.append({
                "class_name": cls,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1_score": round(f1, 4)
            })

        macro_prec = sum(m["precision"] for m in class_metrics) / len(class_metrics)
        macro_rec = sum(m["recall"] for m in class_metrics) / len(class_metrics)

        return {
            "dataset_name": "Holdout Test Dataset (csv/holdout_test.csv)",
            "ground_truth_file": str(HOLDOUT_GROUND_TRUTH_PATH.name),
            "total_columns_evaluated": len(predictions),
            "correct_predictions": sum(1 for p in predictions if p["is_match"]),
            "macro_precision": round(macro_prec, 4),
            "macro_recall": round(macro_rec, 4),
            "class_metrics": class_metrics,
            "predictions": predictions,
            "evaluation_notice": (
                "Evaluation adheres strictly to Dataset/scripts/evaluate.py standards. "
                "The holdout dataset contains synthetic tokens for demonstration. "
                "Per-class metrics reflect column-level precision and recall."
            )
        }

    def evaluate_development(self) -> Dict[str, Any]:
        """
        Runs scanner against development dataset (84 columns across all dev CSV and SQL tables)
        benchmarking against development_expected_columns.csv.
        """
        if not DEV_EXPECTED_COLUMNS_PATH.exists():
            return {"error": "Development expected columns file not found."}

        with open(DEV_EXPECTED_COLUMNS_PATH, mode="r", encoding="utf-8") as f:
            dev_rows = list(csv.DictReader(f))

        predictions = []
        import sqlite3
        sql_db_path = DATASET_DIR / "sql/marketing_company.sqlite"

        for row in dev_rows:
            src = row["source"]
            col = row["column"]
            true_cls = row["true_class"]
            sample_vals = []

            if src.startswith("csv/"):
                csv_file = DATASET_DIR / src
                if csv_file.exists():
                    df = pd.read_csv(csv_file)
                    if col in df.columns:
                        sample_vals = df[col].dropna().head(100).tolist()
            elif "::" in src:
                tbl = src.split("::")[-1]
                if sql_db_path.exists():
                    conn = sqlite3.connect(sql_db_path)
                    cur = conn.cursor()
                    try:
                        safe_col = col.replace("]", "]]")
                        safe_tbl = tbl.replace("]", "]]")

                        cur.execute(
                            f"SELECT [{safe_col}] FROM [{safe_tbl}] LIMIT 100"
                        )
                        sample_vals = [r[0] for r in cur.fetchall()]
                    except Exception:
                        sample_vals = []
                    conn.close()

            classification = self.scanner.classify_column(
                source_name=src,
                table_name=src.split("::")[-1] if "::" in src else src,
                col_name=col,
                sample_values=sample_vals
            )

            pred_cls = classification["category"]
            predictions.append({
                "source": src,
                "column": col,
                "true_class": true_cls,
                "predicted_class": pred_cls,
                "is_match": (true_cls == pred_cls)
            })

        class_metrics = []
        for cls in self.classes:
            tp = sum(1 for p in predictions if p["true_class"] == cls and p["predicted_class"] == cls)
            fp = sum(1 for p in predictions if p["true_class"] != cls and p["predicted_class"] == cls)
            fn = sum(1 for p in predictions if p["true_class"] == cls and p["predicted_class"] != cls)

            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

            class_metrics.append({
                "class_name": cls,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1_score": round(f1, 4)
            })

        return {
            "dataset_name": "Full Development Dataset (CSVs + SQLite)",
            "ground_truth_file": str(DEV_EXPECTED_COLUMNS_PATH.name),
            "total_columns_evaluated": len(predictions),
            "correct_predictions": sum(1 for p in predictions if p["is_match"]),
            "class_metrics": class_metrics,
            "predictions_summary": f"{sum(1 for p in predictions if p['is_match'])}/{len(predictions)} matches"
        }
