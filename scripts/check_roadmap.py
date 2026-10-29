"""Validate roadmap IDs, dependencies, acceptance and persistent tracking."""
from pathlib import Path
import re,json
root=Path(__file__).resolve().parents[1]
def validate(text,progress):
 tasks=re.findall(r'^- \[([ x])\] (P[1-5]-\d{3}) — (.+)$',text,re.M)
 ids=[x[1] for x in tasks];assert len(ids)==len(set(ids))==32
 assert len(re.findall(r'^## Phase [1-5] —',text,re.M))==5
 blocks=re.split(r'(?m)^- \[[ x]\] ',text)[1:]
 for b in blocks:
  assert 'Dependencies:' in b and 'Deliverable and acceptance:' in b and 'Validation:' in b and 'Evidence:' in b
  for dep in re.findall(r'P[1-5]-\d{3}',b):assert dep in ids
 done=[id for mark,id,_ in tasks if mark=='x'];assert done==['P1-001','P2-001']
 assert '2/32' in progress and 'READY FOR REVIEW' in progress and 'P1-002' in progress
 for term in ['real-device','rollback','credentials','Google Drive','owner approval']:assert term.lower() in text.lower()
 return {'passed':True,'phases':5,'tasks':len(ids),'complete':done,'awaiting_implementation':30}
if __name__=='__main__':
 text=(root/'ROADMAP.md').read_text();progress=(root/'docs/PROGRESS.md').read_text()
 result=validate(text,progress)
 for bad in [text.replace('P5-005 —','P5-004 —'),text.replace('Dependencies:','Missing:',1),text.replace('[x] P1-001','[ ] P1-001')]:
  try:validate(bad,progress)
  except AssertionError:pass
  else:raise AssertionError('Invalid roadmap accepted')
 for name in ['CHANGELOG','ISSUES','DECISIONS']:assert (root/'docs'/f'{name}.md').is_file()
 result['negative_cases_passed']=3
 (root/'reports/roadmap-validation.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result))
