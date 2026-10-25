# Privacy Drift Radar — Synthetic Hackathon Datasets

For PS-019: Personal-Data Discovery and Privacy Evidence Inventory. All names, emails, telephone-like values, and IDs are **fictional demonstration data**. No real individuals or genuine government identifiers are represented. `example.com`, `example.org`, and `example.net` are reserved example domains.

## Files

- `csv/customers_v1.csv` — baseline customer dataset (40 rows)
- `csv/customers_v2.csv` — same customer records plus a new `backup_email` column for a drift demonstration
- `csv/employees.csv` — 30 employee-like synthetic rows
- `csv/non_personal_controls.csv` — 25 rows with misleading names, phone-like serials, and dates; negative tests
- `sql/company_demo.sqlite` — SQLite database with `orders` (25 rows) and `source_notes` (1 row)
- `labels/ground_truth_columns.csv` — hand-authored design labels for **each column**, including `NONE` negatives
- `config/classes.json` — five data classes and evaluation unit
- `config/declared_metadata.csv` — illustrative purposes and retention values, with deliberate gaps
- `scripts/evaluate.py` — per-class precision and recall evaluator
- `scripts/create_example_predictions.py` — tests input format only; **not an actual detector**

## The five predefined classes (project choice)

`PERSON_NAME`, `EMAIL`, `PHONE`, `DATE_OF_BIRTH`, `GOVERNMENT_ID`. The PS-019 problem statement specifies five classes but does not enumerate them; confirm these with your mentor. Government ID values use `DEMO-ID-#####` tokens instead of genuine ID formats, so a real-world government ID validator should not be expected to match them.

## Evaluation protocol

**Unit = column**, not individual cell. `true_class=NONE` denotes a non-PII column. Each `(source, column)` is a unique test case. The labels were deliberately authored during dataset design and should be reviewed by a teammate before calling them independently manually validated.

Your scanner should write a CSV with header `source,column,predicted_class`, one prediction for every labelled column, including `NONE`. For example:

```csv
source,column,predicted_class
csv/customers_v1.csv,customer_id,NONE
csv/customers_v1.csv,full_name,PERSON_NAME
```

Run `python scripts/evaluate.py predictions.csv` from this folder. The evaluator requires all labelled columns and reports per-class TP, FP, FN, precision and recall. A class with zero predicted positives gets precision 0.000 by convention; a class with zero actual positives gets recall 0.000. Do not train or tune on this test set if you intend to claim unbiased results.

**IMPORTANT:** `python scripts/create_example_predictions.py` creates perfect, copied predictions purely to test the evaluation pipeline. It is *not* a real classifier or a valid performance benchmark.

## Demonstrate drift

1. Scan `csv/customers_v1.csv` and save the inventory snapshot.
2. Scan `csv/customers_v2.csv` as **the next version of the same logical source**, not as a second unrelated source.
3. Compare column sets: the added `backup_email` field should be discovered and classified as EMAIL.
4. Map the baseline purpose and retention records, then flag missing documentation for the new field.

## Metadata gaps

`config/declared_metadata.csv` includes intentionally missing purpose/retention entries. The scanner should also flag absent rows in this file as missing metadata; never infer purpose or retention from the column value. These retention strings are **illustrative**, not legal advice.

## SQL example

```python
import sqlite3
with sqlite3.connect('sql/company_demo.sqlite') as conn:
    print(conn.execute('SELECT COUNT(*) FROM orders').fetchone())
    print(conn.execute('PRAGMA table_info(orders)').fetchall())
```

## GitHub upload

Upload the **contents of this folder** to your team's private GitHub repository, keeping the directory structure. Git CLI alternative:

```bash
git init
git add README.md csv/ sql/ labels/ config/ scripts/ .gitignore
git commit -m "Add synthetic PS-019 datasets and evaluation fixtures"
git branch -M main
git remote add origin https://github.com/YOUR-ACCOUNT/YOUR-PRIVATE-REPO.git
git push -u origin main
```

Replace the URL with your actual repository URL. Follow the organizer's separate collaborator/ownership instructions only after verifying them with the organizer. Do **not** upload real customer databases or secrets.
