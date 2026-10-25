import csv,sqlite3,json
from pathlib import Path
r=Path(__file__).resolve().parents[1]
assert len(list((r/'sql').glob('*.sqlite')))==1
classes=json.loads((r/'config/classes.json').read_text())['classes'];assert len(classes)==5
for p in (r/'csv').glob('*.csv'):
 with p.open(newline='') as f:
  rows=list(csv.DictReader(f));assert rows and len(rows[0])>1,p
conn=sqlite3.connect(r/'sql/marketing_company.sqlite');assert len(conn.execute("select name from sqlite_master where type='table'").fetchall())==2;conn.close()
with (r/'labels/holdout_ground_truth.csv').open(newline='') as f:gt=list(csv.DictReader(f))
assert {x['true_class'] for x in gt}==set(classes)|{'NONE'}
assert len({(x['source'],x['column']) for x in gt})==len(gt)
print('PASS: CSV files, one SQLite database, five classes, and holdout labels validated.')
