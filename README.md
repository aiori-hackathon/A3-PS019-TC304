# DataPulse

**PS-019: Personal-Data Discovery and Privacy Evidence Inventory**  
**Team Code:** A3-PS019-TC304 | **Team Name:** Forge | **Institution:** Muthoot Institute of Technology and Science  
**Hackathon:** AIORI 3

---

## 1. Executive Summary

**DataPulse** is a personal-data discovery and privacy inventory system designed for cybersecurity and data privacy teams. It dynamically connects to relational databases (SQLite, with extensible interfaces for MySQL/PostgreSQL) and structured CSV collections, identifies personal data categories across schema and data values, flags documentation gaps (missing purpose and retention policies), detects privacy drift across consecutive scans, and provides an enterprise-grade web dashboard with masked data exploration, evaluation benchmarking, and compliance export (CSV & formatted PDF).

---

## 2. Team Details

- **Team Name:** Forge
- **Team Code:** A3-PS019-TC304
- **Institution:** Muthoot Institute of Technology and Science
- **Faculty Mentor:** Sheena Kurian K
- **Team Members:**
  1. **Rajalakshmi R** — Data Discovery & Detection Lead
  2. **Jiya Joe Palathinkal** — Privacy Intelligence & Product Lead

### Presentation & Architecture Documentation
- **YouTube Video:** [A3-PS019-TC304_step7_video](https://youtu.be/m6gh2KkUAQU)
- **Project Proposal Document:** [View Proposal PDF](src/Proposed-structure-hackathon.pdf)

---

## 3. Technology Stack & Architecture

- **Backend:** Python 3.10+ / FastAPI / Uvicorn (Modular, asynchronous REST API)
- **Database Connector:** Read-Only SQLite connector with dynamic schema reflection & parameterization
- **Application Persistence:** Local SQLite database (`src/backend/data/privacy_inventory.sqlite`), strictly isolated from the source database
- **Personal-Data Engine:** Configurable heuristic rules, regex patterns, contextual negative guards, and sample value inspection
- **Frontend Dashboard:** Modern, responsive single-page application built with enterprise cybersecurity design system (Navy, Royal Blue, Teal, and restrained Purple accents)
- **Report Generation:** Tabular CSV exports and styled enterprise PDF reports via ReportLab

### System Directory Structure

```text
A3-PS019-TC304/
├── Dataset/
│   ├── config/              # classes.json, declared_metadata_v1.csv, declared_metadata_v2.csv
│   ├── csv/                 # Synthetic marketing CSV datasets (v1, v2, customers, employees, holdout)
│   ├── labels/              # holdout_ground_truth.csv, development_expected_columns.csv
│   ├── scripts/             # evaluate.py, validate_package.py
│   └── sql/                 # marketing_company.sqlite (Source database)
├── src/
│   ├── backend/
│   │   ├── api/routes.py           # FastAPI endpoints
│   │   ├── config.py               # Path resolution relative to project root
│   │   ├── db/
│   │   │   ├── connector.py        # Safe read-only SQLite connector & extension base
│   │   │   └── app_db.py           # Application inventory SQLite schema
│   │   ├── drift/detector.py       # Scan comparison and drift event logging
│   │   ├── evaluation/evaluator.py # Per-class precision & recall evaluation
│   │   ├── inventory/manager.py    # Scan orchestration, persistence & overrides
│   │   ├── metadata/reconciler.py  # Declared metadata reconciliation (v1/v2)
│   │   ├── reports/exporter.py     # CSV and PDF report generation
│   │   └── scanner/
│   │       ├── engine.py           # Multi-stage detection engine
│   │       └── masking.py          # Privacy-by-design data masking
│   │   ├── main.py                 # FastAPI application server
│   ├── frontend/
│   │   ├── index.html              # Modern cybersecurity dashboard
│   │   ├── css/style.css           # Vanilla CSS enterprise design system
│   │   └── js/app.js               # Client-side reactivity & API integration
├── run.py                          # Single-command launcher
├── requirements.txt                # Python dependencies
└── README.md
```

---

## 4. Key Features

### Dynamic Database Discovery
- Automatically resolves paths relative to the project root regardless of terminal working directory.
- Connects in strict read-only mode (`?mode=ro`) to prevent accidental writes or data alteration.
- Discovers user tables and columns dynamically via schema pragmas without hardcoding table names.
- Safely quotes identifiers and uses parameterized queries to prevent SQL injection.

### Personal-Data Scanning Engine
- Configured via `Dataset/config/classes.json` supporting 5 personal-data classes:
  1. `PERSON_NAME`
  2. `EMAIL`
  3. `PHONE`
  4. `DATE_OF_BIRTH`
  5. `GOVERNMENT_ID` (fictional surrogate format `FICTIONAL-ID-xxxxx`)
  - Negative label: `NONE`
- Contextual negative guards prevent false positives on deceptive non-personal columns (`campaign_name`, `phone_model`, `email_template`, `event_date`, `serial_number`, `government_id_policy`, `birth_date_label`).
- Value-level regex inspection analyzes sample values to validate data types and confidence scores.

### Privacy Evidence Inventory & Human Review
- Maintains a persistent local inventory database completely separate from the source database.
- Tracks source identifier, table, column, category, confidence, detection method, declared purpose, retention rule, review owner, and completeness status.
- Reconciles findings with `declared_metadata_v1.csv` and `v2.csv`.
- Allows privacy officers to edit business purpose, retention rule, and mark items as verified/rejected.
- Persistent overrides ensure user edits survive subsequent rescans.

### Privacy-by-Design Data Masking
- Sensitive data is masked by default in table record previews (e.g. `J*** D**`, `k***@example.com`, `+1-202-***-0101`, `1981-**-**`, `FICT****-00001`).
- Provides an authorized preview toggle to reveal unmasked values during audit investigation.

### Drift & Change Detection
- Genuine scan-history diffing between consecutive scans.
- Flags:
  - Newly discovered tables or columns.
  - Newly detected personal data categories.
  - Policy retention changes (e.g. `work_email` changing from 24 months to 12 months in v2).
  - Newly introduced metadata gaps (e.g. `secondary_email` added in v2 without purpose/retention).
- Visual timeline with detailed audit logs.

### Evaluation Benchmarking
- Directly runs evaluation adhering to `Dataset/scripts/evaluate.py`.
- Benchmark against `Dataset/labels/holdout_ground_truth.csv`:
  - `PERSON_NAME`: Precision 1.000, Recall 1.000 (TP: 1, FP: 0, FN: 0)
  - `EMAIL`: Precision 1.000, Recall 1.000 (TP: 1, FP: 0, FN: 0)
  - `PHONE`: Precision 1.000, Recall 1.000 (TP: 1, FP: 0, FN: 0)
  - `DATE_OF_BIRTH`: Precision 1.000, Recall 1.000 (TP: 1, FP: 0, FN: 0)
  - `GOVERNMENT_ID`: Precision 1.000, Recall 1.000 (TP: 1, FP: 0, FN: 0)
- Benchmark against development dataset (`labels/development_expected_columns.csv`): 84/84 columns correctly classified (100% accuracy).

### Compliance Reports
- Export inventory as CSV.
- Export executive audit report as a formatted PDF using ReportLab with executive summary metrics, personal data inventory tables, privacy gaps, and drift timeline.

---

## 5. Quickstart & Setup Commands

### Prerequisites
- Python 3.10 or higher
- Modern web browser (Chrome, Edge, Firefox, Safari)

### Installation

1. Navigate to the project directory:
   ```bash
   cd A3-PS019-TC304
   ```

2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Launch DataPulse:
   ```bash
   python run.py
   ```

4. Open your browser and navigate to:
   ```text
   http://127.0.0.1:8000
   ```

---

## 6. Verification & Testing

To execute automated end-to-end tests covering database connectivity, scanning, drift detection, overrides, evaluation, and report generation:

```bash
python Dataset/scripts/validate_package.py
python Dataset/scripts/evaluate.py Dataset/predictions.csv
```

---

## 7. Limitations & Future Roadmap

- **Evaluation Granularity:** The holdout evaluation dataset is intentionally small with one positive column per category designed for hackathon demonstration.
- **Surrogate Tokens:** Real government ID detectors require jurisdiction-specific verification (SSN, Aadhaar, Passport); the current MVP evaluates against synthetic design tokens (`FICTIONAL-ID-xxxxx`).
- **Distributed Databases:** The current implementation uses local SQLite and synthetic datasets with extension points for MySQL and PostgreSQL. Future iterations can integrate remote database drivers and cloud data warehouses.
