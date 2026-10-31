# DataPulse — Personal-Data Discovery & Privacy Evidence Inventory

**Problem Statement:** PS-019 — Personal-Data Discovery and Privacy Evidence Inventory  
**Hackathon:** AIORI 3  
**Team Name:** Forge  
**Team Code:** A3-PS019-TC304  
**Institution:** Muthoot Institute of Technology and Science  
**Faculty Mentor:** Sheena Kurian K  

### Team Members

| Name                 | Role                                |
| -------------------- | ----------------------------------- |
| Rajalakshmi R        | Data Discovery & Detection Lead     |
| Jiya Joe Palathinkal | Privacy Intelligence & Product Lead |

---
### Presentation and Architecture Documentation

- **YouTube Presentation:** [Introduction Video](https://youtu.be/m6gh2KkUAQU) 
- **Project Proposal Document:** [View PDF](https://github.com/aiori-hackathon/A3-PS019-TC304/blob/main/src/Proposed-structure-hackathon.pdf)  

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Executive Summary](#2-executive-summary)
3. [Live Deployment](#3-live-deployment)
4. [Problem Statement](#4-problem-statement)
5. [Objectives](#5-objectives)
6. [Key Features](#6-key-features)
7. [System Architecture](#7-system-architecture)
8. [Technology Stack](#8-technology-stack)
9. [Personal-Data Scanning Workflow](#9-personal-data-scanning-workflow)
10. [Privacy Inventory and Metadata Reconciliation](#10-privacy-inventory-and-metadata-reconciliation)
11. [Drift Detection](#11-drift-detection)
12. [Evaluation and Benchmarking](#12-evaluation-and-benchmarking)
13. [API Reference](#13-api-reference)
14. [Project Directory Structure](#14-project-directory-structure)
15. [Installation and Setup](#15-installation-and-setup)
16. [Limitations](#16-limitations)
17. [Future Roadmap](#17-future-roadmap)

---

## 1. Project Overview

**DataPulse** is a personal-data discovery and privacy evidence inventory system designed for cybersecurity teams, privacy officers, and organizations that need better visibility into the personal information stored across their data sources.

The system discovers database tables and columns dynamically, identifies potential personal-data categories using configurable heuristic rules and regular expressions, reconciles findings with declared privacy metadata, and highlights missing documentation and changes between consecutive scans.

DataPulse provides a centralized web dashboard for exploring scan results, reviewing privacy gaps, managing metadata, inspecting masked data previews, evaluating detection performance, and exporting audit reports.

---

## 2. Executive Summary

Organizations frequently store personal information across multiple databases and structured datasets. Identifying this information, maintaining appropriate documentation, and tracking changes over time can be challenging when these processes rely on manual inspection.

DataPulse addresses this challenge through an automated personal-data discovery and privacy inventory workflow.

The application connects to a source database in read-only mode, discovers its schema, examines representative column values, and classifies potential personal data into supported categories. The resulting findings are reconciled with declared business purposes and retention rules to identify documentation gaps.

The system also maintains scan history, detects privacy-related drift between scans, supports human review and persistent metadata overrides, and generates reports that can support internal privacy assessments and audit preparation.

The current implementation supports SQLite databases and structured CSV collections containing synthetic datasets. Its modular architecture provides extension points for additional database connectors.

### Core Capabilities

- Dynamic database schema discovery.
- Rule-based personal-data classification.
- Contextual exclusions to reduce false positives.
- Persistent privacy inventory and metadata reconciliation.
- Masked data previews with an optional unmasked-preview control.
- Privacy documentation gap identification.
- Scan-history comparison and drift detection.
- Development and holdout evaluation.
- CSV inventory exports and formatted PDF audit reports.

---

## 3. Live Deployment

**Deployed Application:** https://datapulse-cm5t.onrender.com/

**Local Application URL:** [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 4. Problem Statement

Organizations may store personal information across customer databases, employee records, marketing systems, and other structured datasets. Without a centralized discovery mechanism, it can be difficult to determine where personal data exists and whether its use and retention are adequately documented.

Common challenges include:

- Discovering personal information across multiple tables and columns.
- Distinguishing actual personal data from misleading column names.
- Identifying missing business purposes and retention rules.
- Tracking newly introduced personal-data fields.
- Detecting changes to existing classifications and privacy metadata.
- Maintaining an auditable record of discovery and review activities.

### Proposed Solution

DataPulse provides a centralized application that combines automated discovery, privacy metadata reconciliation, change tracking, human review, evaluation, and report generation.

It helps privacy teams move from isolated, manual inspection toward a repeatable and reviewable personal-data inventory process.

---

## 5. Objectives

The primary objectives of DataPulse are:

1. **Automate discovery:** Dynamically inspect database schemas and identify potential personal-data fields.
2. **Improve classification:** Combine column-name heuristics, value-level pattern matching, and contextual negative guards.
3. **Maintain privacy evidence:** Associate detected fields with business purposes, retention rules, review owners, and completeness statuses.
4. **Identify documentation gaps:** Highlight personal-data fields with missing purpose or retention information.
5. **Track changes:** Compare consecutive scans to identify changes in schemas, classifications, and privacy metadata.
6. **Protect sensitive information:** Mask personal-data values in previews by default.
7. **Support human review:** Allow reviewers to update metadata and record verification decisions.
8. **Evaluate detection quality:** Measure performance against labeled development and holdout datasets.
9. **Generate reports:** Export inventory data and audit summaries in CSV and PDF formats.

---

## 6. Key Features

### 6.1 Dynamic Database Discovery

DataPulse discovers database structures dynamically rather than depending on a hardcoded list of tables.

Features include:

- Project-root-relative path resolution.
- Read-only SQLite source connections using `mode=ro`.
- Dynamic table discovery through SQLite schema metadata.
- Column discovery using `PRAGMA table_info`.
- Identifier quoting and parameterized query handling.
- Connection status and schema information through the dashboard.

The current implementation uses SQLite as its implemented relational database connector. The connector architecture provides an extension point for future MySQL and PostgreSQL support.

### 6.2 Personal-Data Scanning Engine

The scanner uses configurable heuristic rules, regular expressions, contextual exclusions, and representative sample-value inspection.

It supports five personal-data categories and one negative classification:

| Category        | Description                                             |
| --------------- | ------------------------------------------------------- |
| `PERSON_NAME`   | Potential names of individuals                          |
| `EMAIL`         | Email addresses                                         |
| `PHONE`         | Phone numbers                                           |
| `DATE_OF_BIRTH` | Dates identified as dates of birth                      |
| `GOVERNMENT_ID` | Identifiers matching the configured fictional ID format |
| `NONE`          | No supported personal-data category detected            |

The classification configuration is maintained in `Dataset/config/classes.json`.

The scanner considers both schema context and sample values. It also applies negative guards to reduce incorrect classifications of non-personal fields.

Examples include:

- `campaign_name`
- `phone_model`
- `email_template`
- `event_date`
- `serial_number`
- `government_id_policy`
- `birth_date_label`

These safeguards help distinguish personal-data fields from product names, templates, policy descriptions, and other similarly named columns.

### 6.3 Privacy Evidence Inventory

The application maintains a persistent inventory in a dedicated SQLite database, separate from the source database.

Inventory records track information such as:

- Source identifier.
- Table and column names.
- Detected personal-data category.
- Classification confidence.
- Detection method.
- Declared business purpose.
- Retention rule.
- Review owner.
- Metadata completeness status.
- Review decisions and notes.

The inventory supports searching, filtering, pagination, metadata updates, and review workflows.

### 6.4 Privacy Metadata Reconciliation

DataPulse reconciles scanner findings with declared privacy metadata supplied through:

- `Dataset/config/declared_metadata_v1.csv`
- `Dataset/config/declared_metadata_v2.csv`

The reconciliation process identifies whether detected personal-data fields have documented purposes and retention rules.

### 6.5 Privacy-by-Design Data Masking

Sensitive values are masked by default in record previews.An unmasked-preview toggle is available for audit investigations where access to the original values is necessary.

Masking is intended to reduce accidental exposure during normal exploration. It does not replace authentication, access control, encryption, or other security measures.

### 6.6 Privacy Gap Identification

The Privacy Gaps section highlights personal-data fields with incomplete privacy documentation.

Examples include:

- A customer email column without a declared business purpose.
- An employee birth-date column without a retention rule.
- A newly introduced personal-data field with no corresponding metadata record.

This feature helps reviewers identify outstanding documentation requirements and determine which records need further attention.

### 6.7 Drift and Change Detection

DataPulse compares stored scan results to identify changes between consecutive scans.

It can record events involving:

- Newly discovered tables.
- Removed tables.
- Newly discovered columns.
- Removed columns.
- Newly detected personal-data classifications.
- Classification changes.
- Retention-policy changes.
- Changes in metadata completeness.

The drift dashboard provides a visual history of recorded changes and associated audit information.

### 6.8 Evaluation and Benchmarking

The evaluation module compares scanner predictions against labeled datasets.

It supports:

- Development-dataset evaluation.
- Holdout-dataset evaluation.
- Per-class precision and recall.
- True-positive, false-positive, and false-negative counts.
- F1-score calculations where reported by the evaluator.

The benchmark datasets are stored in `Dataset/labels/`.

The evaluation feature helps assess how the configured detection rules perform on known examples.

### 6.9 Compliance Report Generation

DataPulse provides export capabilities for further analysis and audit preparation.

**CSV export**

- Exports inventory records in a structured tabular format.
- Supports downstream analysis using spreadsheet tools.

**PDF export**

- Generates a formatted audit report using ReportLab.
- Includes executive summary metrics.
- Presents personal-data inventory tables.
- Summarizes privacy documentation gaps.
- Includes recorded drift information.

The generated reports can support internal review and documentation. They do not, by themselves, certify regulatory compliance.

### 6.10 Enterprise Dashboard

The frontend is a responsive single-page application with a cybersecurity-oriented visual design.

The main dashboard sections are:

1. **Executive Overview** — summary metrics and application status.
2. **Data Sources** — source connectivity and schema discovery.
3. **Scanner** — scan configuration and execution.
4. **Privacy Inventory** — detected fields and associated metadata.
5. **Privacy Gaps** — incomplete privacy documentation.
6. **Drift Detection** — recorded changes between scans.
7. **Evaluation** — benchmark results and classification metrics.
8. **Reports** — CSV and PDF export.

The frontend communicates with the backend through HTTP API requests and updates the interface using JavaScript.

---

## 7. System Architecture

DataPulse follows a modular client-server architecture.

### High-Level Workflow

```text
                  USER
                   |
                   v
       +--------------------------+
       |   Frontend Dashboard    |
       |      HTML / CSS / JS    |
       +--------------------------+
                   |
                   | HTTP / JSON
                   v
       +--------------------------+
       |      FastAPI Backend     |
       |       API Routes         |
       +--------------------------+
                   |
                   v
       +--------------------------+
       |    Inventory Manager    |
       | Scan orchestration      |
       | Persistence and review  |
       +--------------------------+
                   |
       +-----------+------------+----------------+
       |                        |                |
       v                        v                v
+----------------+    +----------------+  +----------------+
| Scanner Engine |    | Metadata       |  | Drift Detector |
|                |    | Reconciler     |  |                |
+----------------+    +----------------+  +----------------+
       |                        |                |
       +------------------------+----------------+
                                |
                                v
                   +--------------------------+
                   |  Application SQLite DB   |
                   | Inventory and history    |
                   +--------------------------+

       +--------------------------+
       |  Source SQLite / CSV     |
       |  Read and inspect data   |
       +--------------------------+
```

---

## 8. Technology Stack

| Technology          | Role in DataPulse                           | Reason for Selection                                                                                                                  |
| ------------------- | ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Python 3.10+        | Primary programming language                | Suitable for data processing, pattern matching, database operations, and report generation                                            |
| FastAPI             | Backend REST API framework                  | Supports structured endpoints, request validation, and API documentation                                                              |
| Uvicorn             | ASGI server                                 | Runs and serves the FastAPI application                                                                                               |
| SQLite              | Source database and application persistence | Lightweight, file-based, and convenient for a portable prototype                                                                      |
| Pandas              | Structured CSV processing                   | Simplifies loading and processing tabular datasets                                                                                    |
| HTML                | Frontend structure                          | Provides the dashboard markup                                                                                                         |
| CSS                 | Frontend styling                            | Enables a responsive cybersecurity-oriented interface                                                                                 |
| JavaScript          | Frontend interactions                       | Connects the dashboard to backend APIs and updates the UI                                                                             |
| Regular Expressions | Pattern-based detection                     | Supports matching structured values such as email addresses and configured identifier formats                                         |
| Pydantic            | Request and data validation                 | Helps validate structured API inputs                                                                                                  |
| ReportLab           | PDF report generation                       | Creates formatted, programmatically generated audit reports                                                                           |
| SQLAlchemy          | Listed dependency / database toolkit        | Available for database abstraction where used; its presence in dependencies does not imply that every database operation uses the ORM |

---

## 9. Personal-Data Scanning Workflow

The scanning engine is implemented in:

`src/backend/scanner/engine.py`

The inventory manager coordinates scanning through:

`src/backend/inventory/manager.py`

The scanner follows a multi-stage workflow.

### Stage 1: Source Connection

The application opens the selected SQLite source in read-only mode or loads a supported CSV collection.

### Stage 2: Schema Discovery

For SQLite, the connector discovers tables using database schema metadata and retrieves column definitions using `PRAGMA table_info`.

This allows the scanner to process tables and columns that were not explicitly hardcoded into the application.

### Stage 3: Sample-Value Inspection

The inventory manager fetches representative records for each table and examines column values.

The current database scanning implementation uses a sample limit of up to 100 records per table for classification.

### Stage 4: Contextual Negative Guards

The engine checks for known non-personal field names and misleading terms before applying positive classification rules.

This reduces false positives for columns such as `email_template`, `phone_model`, and `campaign_name`.

### Stage 5: Classification

The `classify_column()` method evaluates column context and sample values against configured detection rules.

The supported classes are:

- `PERSON_NAME`
- `EMAIL`
- `PHONE`
- `DATE_OF_BIRTH`
- `GOVERNMENT_ID`
- `NONE`

The fictional government-ID detector recognizes the configured surrogate format `FICTIONAL-ID-xxxxx`.

### Stage 6: Confidence and Detection Evidence

The engine returns classification information such as:

- Predicted category.
- Confidence score.
- Detection method.
- Number of matching sample values.
- Sample count.
- Human-readable reasoning.

The confidence score reflects the configured rule logic; it is not a statistically calibrated probability.

### Stage 7: Metadata Reconciliation

The scanner's findings are matched against declared metadata from the configured CSV files.

The reconciliation process determines whether the detected field has a declared purpose and retention rule.

### Stage 8: Persistence

The inventory manager saves scan findings and associated metadata in the application database.

Scan history is retained so that later scans can be compared with earlier results.

### Stage 9: Review and Reporting

The dashboard presents the inventory, documentation gaps, drift events, and evaluation results. Users can review metadata and export the findings.

---

## 10. Privacy Inventory and Metadata Reconciliation

The privacy inventory is the central evidence store of DataPulse.

It combines automatically detected fields with declared metadata and reviewer-provided information.

### Inventory Lifecycle

1. A scan discovers a candidate personal-data field.
2. The scanner assigns a category and confidence score.
3. The metadata reconciler looks for a matching declared metadata record.
4. The system calculates the metadata completeness status.
5. The inventory manager persists the finding.
6. A reviewer can update metadata and record a review decision.
7. Subsequent scans can use persisted review overrides where applicable.

### Human Review

Automatic classification is not treated as a substitute for human judgment.

Privacy reviewers can update business purpose, retention rules, review information, and verification status. Persistent overrides help preserve review decisions across rescans.

A reviewer should still validate the accuracy and appropriateness of declared purposes and retention rules.

---

## 11. Drift Detection

Drift detection compares inventory information from earlier and later scans.

The implementation is located in:

`src/backend/drift/detector.py`

### Types of Drift

| Event                         | Description                                  |
| ----------------------------- | -------------------------------------------- |
| `NEW_TABLE`                   | A table appears in a later scan              |
| `REMOVED_TABLE`               | A previously discovered table is absent      |
| `NEW_COLUMN`                  | A new column appears                         |
| `REMOVED_COLUMN`              | A previously discovered column is absent     |
| `NEW_PERSONAL_DATA`           | A new field is identified as personal data   |
| `CATEGORY_DRIFT`              | A field's classification changes             |
| `POLICY_RETENTION_CHANGED`    | A recorded retention rule changes            |
| `METADATA_COMPLETENESS_DRIFT` | A field's documentation completeness changes |

---

## 12. Evaluation and Benchmarking

### Evaluation Metrics

- **Precision:** The proportion of predicted positive classifications that are correct.
- **Recall:** The proportion of actual positive examples that are correctly identified.
- **F1 score:** The harmonic mean of precision and recall.
- **True positives:** Correct positive classifications.
- **False positives:** Incorrect positive classifications.
- **False negatives:** Missed positive classifications.

The results depend on the labels, dataset composition, and configured scanner rules. The evaluation should be rerun whenever the scanner implementation or datasets change.

---

## 13. API Reference

The FastAPI backend exposes endpoints for source discovery, scanning, inventory management, drift detection, evaluation, and report generation.

The following table summarizes the documented API routes.

| Method  | Endpoint                      | Purpose                                              |
| ------- | ----------------------------- | ---------------------------------------------------- |
| `GET`   | `/api/status`                 | Retrieves application status and summary information |
| `GET`   | `/api/tables`                 | Discovers source tables and columns                  |
| `POST`  | `/api/scan`                   | Starts a scan                                        |
| `GET`   | `/api/scan/history`           | Retrieves scan history                               |
| `GET`   | `/api/inventory`              | Retrieves inventory with search and filtering        |
| `PATCH` | `/api/inventory/{item_id}`    | Updates inventory metadata                           |
| `GET`   | `/api/gaps`                   | Retrieves privacy documentation gaps                 |
| `GET`   | `/api/drift`                  | Retrieves recorded drift events                      |
| `GET`   | `/api/evaluation/holdout`     | Runs holdout evaluation                              |
| `GET`   | `/api/evaluation/development` | Runs development evaluation                          |
| `GET`   | `/api/export/csv`             | Exports inventory as CSV                             |
| `GET`   | `/api/export/pdf`             | Generates a PDF audit report                         |

---

## 14. Project Directory Structure

```text
A3-PS019-TC304/
│
├── Dataset/
│   ├── config/
│   │   ├── classes.json
│   │   ├── declared_metadata_v1.csv
│   │   └── declared_metadata_v2.csv
│   │
│   ├── csv/
│   │   └── Synthetic marketing CSV datasets
│   │
│   ├── labels/
│   │   ├── holdout_ground_truth.csv
│   │   └── development_expected_columns.csv
│   │
│   ├── scripts/
│   │   ├── evaluate.py
│   │   └── validate_package.py
│   │
│   └── sql/
│       └── marketing_company.sqlite
│
├── src/
│   ├── backend/
│   │   ├── api/
│   │   │   └── routes.py
│   │   ├── db/
│   │   │   ├── connector.py
│   │   │   └── app_db.py
│   │   ├── drift/
│   │   │   └── detector.py
│   │   ├── evaluation/
│   │   │   └── evaluator.py
│   │   ├── inventory/
│   │   │   └── manager.py
│   │   ├── metadata/
│   │   │   └── reconciler.py
│   │   ├── reports/
│   │   │   └── exporter.py
│   │   ├── scanner/
│   │   │   ├── engine.py
│   │   │   └── masking.py
│   │   ├── config.py
│   │   └── main.py
│   │
│   └── frontend/
│       ├── index.html
│       ├── css/
│       │   └── style.css
│       └── js/
│           └── app.js
│
├── run.py
├── requirements.txt
└── README.md
```

The application also creates or uses the local inventory database at:

`src/backend/data/privacy_inventory.sqlite`

The CSV directory contains synthetic datasets used for scanning demonstrations and version comparisons.

---

## 15. Installation and Setup

### Prerequisites
- Python 3.10 or later
- Git

### Installation Steps

1. Navigate to the project directory:
   ```bash
   cd A3-PS019-TC304
   ```

2. Install the required dependencies:
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

The DataPulse dashboard should now be accessible locally.

---

## 16. Limitations

- **Rule-based detection:** Classification relies on heuristics and regular expressions, which may produce false positives or miss certain data.
- **Limited evaluation:** The small synthetic evaluation datasets do not establish production-level accuracy.
- **Database support:** SQLite is currently supported; other database connectors are future enhancements.
- **Security:** Production deployment requires stronger authentication, access control, and safeguards for unmasked data previews.

---

## 17. Future Roadmap

- Add MySQL and PostgreSQL support.
- Improve detection accuracy and expand labeled evaluation datasets.
- Support more personal-data categories and international identifiers.
- Introduce role-based access control and enhanced audit logging.
- Improve cloud deployment and persistent storage.

---

**DataPulse — Discover personal data. Identify privacy gaps. Track changes. Strengthen privacy evidence.**
