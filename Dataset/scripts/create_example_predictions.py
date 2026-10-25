"""Generate a demo predictions file equal to the designed labels. NOT a detector.
Use only to verify the evaluation script; never report this as model performance.
"""
import csv,pathlib
root=pathlib.Path(__file__).resolve().parents[1]
with (root/'labels/ground_truth_columns.csv').open(newline='') as f:rows=list(csv.DictReader(f))
with (root/'example_predictions.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['source','column','predicted_class'])
 for r in rows:w.writerow([r['source'],r['column'],r['true_class']])
print('Wrote example_predictions.csv; this is a format test, NOT a real detection result.')
