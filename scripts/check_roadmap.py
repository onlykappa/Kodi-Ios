"""Validate task-derived progress, evidence, phase gates and dependencies."""
from pathlib import Path
import re,json
root=Path(__file__).resolve().parents[1]
def summarize(text):
 tasks=re.findall(r'^- \[([ x])\] (P[1-5]-\d{3}) — ([^\n]+)\n(.*?)(?=^- \[|^## |\Z)',text,re.M|re.S)
 assert tasks,'No tasks'
 ids=[t[1] for t in tasks];assert len(ids)==len(set(ids)),'Duplicate ID'
 assert set(re.findall(r'^## Phase ([1-5]) —',text,re.M))==set('12345')
 complete=[]
 for mark,id,title,body in tasks:
  status=re.search(r'Status: (NOT STARTED|IN PROGRESS|BLOCKED|READY FOR REVIEW|COMPLETE)\.',body)
  assert status and (mark=='x')==(status[1]=='COMPLETE'),'Status mismatch'
  for field in ['Dependencies:','Deliverable and acceptance:','Validation:','Evidence:']:assert field in body
  if mark=='x':
   assert 'Evidence: pending' not in body,'Missing evidence'
   complete.append(id)
  dep=body.split('Dependencies:',1)[1].split('\n',1)[0]
  assert all(d in ids for d in re.findall(r'P[1-5]-\d{3}',dep))
 for phase in range(1,6):assert f'REVIEW-GATE-{phase}' in text
 return {'passed':True,'phases':5,'tasks':len(ids),'complete':complete,'completed_count':len(complete),'awaiting_implementation':len(ids)-len(complete),'percent':round(100*len(complete)/len(ids),2)}
def progress_line(result):
 return f"Progress: {result['completed_count']}/{result['tasks']} task IDs COMPLETE ({result['percent']:.2f}%); {result['awaiting_implementation']} awaiting implementation."
def validate(text,progress):
 result=summarize(text)
 assert progress_line(result) in text and progress_line(result) in progress,'Stale progress'
 return result
if __name__=='__main__':
 result=validate((root/'ROADMAP.md').read_text(),(root/'docs/PROGRESS.md').read_text())
 (root/'reports/roadmap-validation.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result))
