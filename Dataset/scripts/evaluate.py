"""Run: python scripts/evaluate.py path/to/predictions.csv  (from package root)."""
import csv,sys
from pathlib import Path
CLASSES=['PERSON_NAME','EMAIL','PHONE','DATE_OF_BIRTH','GOVERNMENT_ID']
def read(path):
 with open(path,newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def main(path):
 gt=read('labels/holdout_ground_truth.csv');pred=read(path)
 expected={(x['source'],x['column']):x['true_class'] for x in gt}
 seen={}
 for x in pred:
  k=(x['source'],x['column']);v=x['predicted_class']
  if k in seen:raise ValueError(f'Duplicate prediction: {k}')
  if v not in CLASSES+['NONE']:raise ValueError(f'Invalid class: {v}')
  seen[k]=v
 if set(seen)!=set(expected):raise ValueError(f'Missing: {set(expected)-set(seen)}; extra: {set(seen)-set(expected)}')
 print('Class,TP,FP,FN,Precision,Recall')
 for cls in CLASSES:
  tp=sum(expected[k]==cls and seen[k]==cls for k in expected)
  fp=sum(expected[k]!=cls and seen[k]==cls for k in expected)
  fn=sum(expected[k]==cls and seen[k]!=cls for k in expected)
  print(f'{cls},{tp},{fp},{fn},{tp/(tp+fp) if tp+fp else 0:.3f},{tp/(tp+fn) if tp+fn else 0:.3f}')
if __name__=='__main__':
 if len(sys.argv)!=2:sys.exit('Usage: python scripts/evaluate.py predictions.csv')
 main(sys.argv[1])
