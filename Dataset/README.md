# Privacy Drift Radar — Marketing Company Synthetic Dataset

**Scenario:** fictional digital marketing agency **LumenReach Demo Marketing**. This package replaces the earlier generic-company sample with related marketing leads, customers, campaigns, employee data and SQL campaign interactions. Designed for PS-019. No real people or actual government identifiers are intended. Example emails use the reserved `example.com` domain; phone numbers use the reserved US 202-555-01xx fictional range. Government IDs are **FICTIONAL-ID-xxxxx** markers, not government-issued formats.

## PS-019 requirement mapping

- Synthetic CSV files: `csv/` contains leads V1/V2, customers, employees, campaigns, non-personal controls and a separate holdout.
- One SQL database: `sql/marketing_company.sqlite` with `lead_interactions` and `campaign_performance`.
- Five predefined classes: `config/classes.json` (PERSON_NAME, EMAIL, PHONE, DATE_OF_BIRTH, GOVERNMENT_ID). PS-019 does **not** name the five classes: confirm with mentor.
- Configurable detection: design your scanner to read class rules; this package provides class definitions, **not** a trained classifier or full detection implementation.
- Purpose/retention: `config/declared_metadata_v1.csv` and `v2.csv` include deliberate gaps and a changed retention rule. These are illustrative company policies, not legal recommendations.
- Ground truth: `labels/holdout_ground_truth.csv` is a separate small **human-authored synthetic design label** set (one row per column), with independent review marked **pending**. Do not call it independently manually validated until a teammate reviews it.
- Development labels: `labels/development_expected_columns.csv` are design labels for debugging only, NOT held-out evaluation.
- Negative examples: `csv/non_personal_controls.csv` and holdout fields `campaign_name`, `campaign_code`, `email_template`, `event_date` are non-personal in the context of this test. Some contain misleading strings, so column context matters.
- Drift: `marketing_leads_v2.csv` adds `secondary_email` and `preferred_contact_window`; metadata V2 omits purpose/retention for the new email field and changes the retention rule for `work_email`. Treat V1/V2 as **one logical source** (`marketing_leads`), not two unrelated sources.

## File guide

| File | Purpose |
|---|---|
| `csv/marketing_leads_v1.csv`, `csv/marketing_leads_v2.csv` | Same synthetic lead IDs; new fields in V2 |
| `csv/customers.csv` | Agency customer accounts and contact details |
| `csv/employees.csv` | Employee contacts and HR-related fields |
| `csv/campaigns.csv` | Campaign analytics; non-personal metrics |
| `csv/non_personal_controls.csv` | Hard negatives and misleading labels |
| `csv/holdout_test.csv` | Separate evaluation data; do not tune rules on this |
| `sql/marketing_company.sqlite` | Interactions linked by lead and campaign IDs; campaign performance |
| `config/classes.json` | Class definitions and evaluation unit |
| `config/declared_metadata_v1.csv`, `v2.csv` | Purposes, retention, missing metadata, policy drift |
| `labels/development_expected_columns.csv` | Development-time expected labels |
| `labels/holdout_ground_truth.csv` | Hand-authored holdout truth, awaiting independent review |
| `scripts/evaluate.py` | Per-class precision/recall of scanner output |
| `scripts/validate_package.py` | Dataset integrity checks |

## How to use

1. Run `python scripts/validate_package.py` from the package root.
2. Develop a rule-based scanner using the development CSV/SQL data and `labels/development_expected_columns.csv`. No machine-learning training is required.
3. Keep `csv/holdout_test.csv` and `labels/holdout_ground_truth.csv` separate from rule tuning. Have a teammate review the labels and change `independent_review_status` to `reviewed` only after actual review.
4. Your scanner must produce `source,column,predicted_class` with one prediction for **every holdout column**, including `NONE`. The holdout `source` value is exactly `csv/holdout_test.csv`.
5. Run `python scripts/evaluate.py predictions.csv` to report TP, FP, FN, precision and recall **per class**. No fabricated model scores are included.
6. Scan V1, save inventory snapshot, scan V2 as the same logical source, compare schema and metadata, then flag the new `secondary_email` and missing documentation.

**Example prediction format** (illustrative only):

```csv
source,column,predicted_class
csv/holdout_test.csv,case_id,NONE
csv/holdout_test.csv,primary_contact,PERSON_NAME
```

## Evaluation limitations

This is a small **column-level** holdout with one positive column per category; precision/recall therefore have coarse granularity and are for hackathon demonstration, not production benchmarking. Human-authored labels are not independently validated until your team reviews them. A government-ID detector for real jurisdiction-specific formats cannot be evaluated with fictional tokens; these test only your demo-token rule. Synthetic labels are separate from predictions; do not copy ground truth into scanner output.

## GitHub upload

Extract this folder into your team's private repository and commit the files. Only one `.sqlite` file is included. Avoid committing `.env`, database credentials, or real customer information.

```bash
git add privacy_drift_radar_marketing_dataset
git commit -m "Add marketing-company synthetic PS-019 datasets"
git push
```
