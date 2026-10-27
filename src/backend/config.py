"""
Configuration and Path Resolution for DataPulse.
Resolves paths relative to the project root directory regardless of current working directory.
"""
import os
from pathlib import Path

# Project root: directory containing Dataset/ and src/
# e.g., c:\Users\HP\Desktop\aiori_forge\A3-PS019-TC304
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Dataset paths
DATASET_DIR = PROJECT_ROOT / "Dataset"
CONFIG_DIR = DATASET_DIR / "config"
CLASSES_JSON_PATH = CONFIG_DIR / "classes.json"
DECLARED_METADATA_V1 = CONFIG_DIR / "declared_metadata_v1.csv"
DECLARED_METADATA_V2 = CONFIG_DIR / "declared_metadata_v2.csv"

CSV_DIR = DATASET_DIR / "csv"
SQL_DIR = DATASET_DIR / "sql"
DEFAULT_SQLITE_PATH = SQL_DIR / "marketing_company.sqlite"

LABELS_DIR = DATASET_DIR / "labels"
HOLDOUT_GROUND_TRUTH_PATH = LABELS_DIR / "holdout_ground_truth.csv"
DEV_EXPECTED_COLUMNS_PATH = LABELS_DIR / "development_expected_columns.csv"

SCRIPTS_DIR = DATASET_DIR / "scripts"
EVALUATE_SCRIPT_PATH = SCRIPTS_DIR / "evaluate.py"

# Application persistence database (separate from source database)
APP_DATA_DIR = PROJECT_ROOT / "src" / "backend" / "data"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
INVENTORY_DB_PATH = APP_DATA_DIR / "privacy_inventory.sqlite"

# Static / Frontend directory
FRONTEND_DIR = PROJECT_ROOT / "src" / "frontend"

# Server configuration
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000
