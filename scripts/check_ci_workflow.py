"""Verify conformance to the owner-approved workflow and shell syntax."""
from pathlib import Path
import re,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
def validate(text):
 expected=re.search(r'```yaml\n(.*?)```',(ROOT/'docs/proposed-drive-test-workflow.md').read_text(),re.S).group(1)
 assert text==expected,'Workflow differs from approved proposal'
 lock=json.loads((ROOT/'migration/google-drive/source-lock.json').read_text())
 pin=next(x['commit'] for x in lock['repositories'] if x['addon_id']=='script.module.clouddrive.common')
 assert pin in text and 'timeout-minutes: 5' in text
 assert 'permissions: {}' in text and 'pull_request_target' not in text
 assert 'uses:' not in text and 'continue-on-error:' not in text
 assert '${{' not in text and 'secrets.' not in text
 blocks=re.findall(r'        run: \|\n((?:          .*\n)+)',text)
 assert len(blocks)==2,'Expected both shell steps'
 for block in blocks:
  script='\n'.join(line[10:] for line in block.splitlines())
  subprocess.run(['bash','-n'],input=script,text=True,check=True)
 return {'approved_template_match':True,'shell_syntax_valid':True,'timeout_minutes':5,'upstream_commit':pin,'execution_passed':False}
if __name__=='__main__':print(json.dumps(validate((ROOT/'.github/workflows/drive-upstream.yml').read_text())))
