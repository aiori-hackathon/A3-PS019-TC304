"""Evaluate column-level predicted classes against designed ground-truth labels.
Usage: python scripts/evaluate.py predictions.csv
Predictions must have source,column,predicted_class; use NONE for no finding.
"""
import csv,sys,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
CLASSES=['PERSON_NAME','EMAIL','PHONE','DATE_OF_BIRTH','GOVERNMENT_ID']
def load(path,cls_col):
 with open(path,newline='',encoding='utf-8') as f:
  rows=list(csv.DictReader(f))
 out={}
 for r in rows:
  key=(r['source'],r['column'])
  if key in out:raise ValueError(f'Duplicate source/column: {key}')
  if r[cls_col] not in CLASSES+['NONE']:raise ValueError(f'Unknown class: {r[cls_col]}')
  out[key]=r[cls_col]
 return out
if len(sys.argv)!=2:raise SystemExit('Usage: python scripts/evaluate.py predictions.csv')
truth=load(ROOT/'labels/ground_truth_columns.csv','true_class')
pred=load(sys.argv[1],'predicted_class')
if set(pred)!=set(truth):
 missing=set(truth)-set(pred);extra=set(pred)-set(truth)
 raise SystemExit(f'Prediction keys must match all labelled columns. Missing={len(missing)}, extra={len(extra)}')
print('CLASS,TP,FP,FN,PRECISION,RECALL')
for cls in CLASSES:
 tp=sum(truth[k]==cls and pred[k]==cls for k in truth)
 fp=sum(truth[k]!=cls and pred[k]==cls for k in truth)
 fn=sum(truth[k]==cls and pred[k]!=cls for k in truth)
 p=tp/(tp+fp) if tp+fp else 0.0
 r=tp/(tp+fn) if tp+fn else 0.0
 print(f'{cls},{tp},{fp},{fn},{p:.3f},{r:.3f}')
