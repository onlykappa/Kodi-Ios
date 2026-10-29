"""Validate research/approval/failure consistency, not live integration readiness."""
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1]
def validate(lock,research,suite,roadmap):
 assert lock['owner_approved'] and research['owner_approved'],'Missing owner approval'
 assert lock['selected_architecture']==research['architecture_selection']=='direct-addon-maintainer-oauth-relay'
 assert lock['relay']['endpoint']=='https://drive.signinserver.com','Unexpected or legacy relay'
 assert lock['relay']['scope']=='https://www.googleapis.com/auth/drive.readonly','Scope expansion'
 assert not research['ios_runtime_verified'] and not suite['ios_runtime_verified']
 identities=[]
 for repo in lock['repositories']:
  assert re.fullmatch('[0-9a-f]{40}',repo['commit'])
  assert repo['files'],'Missing source identities'
  paths=[]
  for f in repo['files']:
   p=Path(f['path']);assert not p.is_absolute() and '..' not in p.parts
   assert re.fullmatch('[0-9a-f]{40}',f['git_blob_sha'])
   paths.append(f['path'])
  assert len(paths)==len(set(paths)) and 'addon.xml' in paths
  identities+=paths
 assert suite['complete_upstream_file_identities_recorded']==len(identities)
 assert suite['passed']+suite['failures']+suite['errors']==suite['tests_run'],'Wrong suite accounting'
 assert suite['suite_passed']==(suite['failures']==0 and suite['errors']==0),'False suite pass'
 assert len(suite['failed_tests'])==suite['errors']+suite['failures']
 if not suite['suite_passed']:
  assert not research['phase3_ready'],'Cannot declare Phase 3 ready with failed required tests'
  assert re.search(r'P3-00[456] — [^\n]+\n  - Status: BLOCKED\.',roadmap),'Failure not reflected in roadmap'
 if research['phase3_ready']:
  assert research['implementation_complete']
  for n in range(1,7):assert f'- [x] P3-{n:03d}' in roadmap
 return {'research_consistent':True,'phase3_ready':research['phase3_ready'],'upstream_suite_passed':suite['suite_passed'],'source_file_identities':len(identities),'owner_approved_architecture':research['architecture_selection']}
if __name__=='__main__':
 result=validate(json.loads((ROOT/'migration/google-drive/source-lock.json').read_text()),json.loads((ROOT/'reports/google-drive-research.json').read_text()),json.loads((ROOT/'reports/drive-upstream-validation.json').read_text()),(ROOT/'ROADMAP.md').read_text())
 print(json.dumps(result))
