# DataPulse Source Code (`src/`)

This directory contains the full implementation of **DataPulse**:

## Directory Layout

- `backend/`
  - `main.py`: FastAPI server entrypoint mounting REST endpoints and static assets.
  - `config.py`: Centralized path resolution ensuring paths resolve relative to project root.
  - `db/`
    - `connector.py`: Read-only SQLite connector, dynamic schema reflection, and database extension interface.
    - `app_db.py`: Application metadata database (`privacy_inventory.sqlite`) maintaining scan history, findings, overrides, and drift events.
  - `scanner/`
    - `engine.py`: Personal data discovery engine using heuristics, regex, contextual negative guards, and sample validation.
    - `masking.py`: Sensitive data masking utilities for privacy-by-design UI representation.
  - `metadata/`
    - `reconciler.py`: Reconciliation engine for declared policies (`v1` and `v2`) flagging missing purpose, missing retention, and policy changes.
  - `drift/`
    - `detector.py`: Historical scan comparison engine detecting added tables/columns, category drift, and policy drift.
  - `inventory/`
    - `manager.py`: Coordinator for scanning data sources, search & filter queries, pagination, and persistent user metadata overrides.
  - `evaluation/`
    - `evaluator.py`: Benchmark runner computing per-class Precision, Recall, and Confusion metrics on holdout and dev labels.
  - `reports/`
    - `exporter.py`: Tabular CSV and formatted ReportLab PDF report generation.
  - `api/`
    - `routes.py`: FastAPI routes for system health, scanning, inventory, table exploration, gaps, drift, evaluation, and exports.
- `frontend/`
  - `index.html`: Modern, responsive single-page cybersecurity dashboard.
  - `css/style.css`: Custom vanilla CSS design system following enterprise cybersecurity visual guidelines.
  - `js/app.js`: Client-side reactivity, interactive scanning progress, search filters, modals, and evaluation tables.
- `Proposed-structure-hackathon.pdf`: Original team proposal document preserved from initial repository setup.
