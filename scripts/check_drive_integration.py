"""Check the credential-free Drive integration contract; no device claims."""
from pathlib import Path
import json,xml.etree.ElementTree as ET
from check_ios import check as check_ios
ROOT=Path(__file__).resolve().parents[1]
def check(root=ROOT):
 lock=json.loads((root/'migration/google-drive/source-lock.json').read_text())
 contracts=json.loads((root/'reports/drive-addon-contracts.json').read_text())
 assert lock['owner_approved'] and contracts['owner_approved']
 pinned={x['addon_id']:x for x in lock['repositories']}
 for a in contracts['addons']:
  assert a['commit']==pinned[a['id']]['commit'] and a['version']==pinned[a['id']]['version']
  assert a['manifest_git_blob']==next(f['git_blob_sha'] for f in pinned[a['id']]['files'] if f['path']=='addon.xml')
 plan=json.loads((root/'migration/ios/addon-plan.json').read_text());assert 'plugin.googledrive' in plan['roots']
 selected={x['id']:x for x in plan['addons']}
 for a in contracts['addons']:assert selected[a['id']]['source_version_candidate']==a['version']
 config=root/'migration/ios/userdata/addon_data/plugin.googledrive'
 assert {p.name for p in config.iterdir()}=={'settings.xml'},'Unexpected private account-state file'
 settings={x.get('id'):x.text for x in ET.parse(config/'settings.xml').getroot().findall('setting')}
 expected={'sign-in-server':'https://drive.signinserver.com','set_subtitle':'true','ask_resume':'true','allow_directory_listing':'false','clean_folder':'false'}
 assert settings==expected,'Unexpected endpoint, private setting, or unsafe preference'
 menu=json.loads((root/'migration/ios/userdata/addon_data/script.skinvariables/nodes/skin.arctic.fuse.3/skinvariables-shortcut-homesubmenu.json').read_text())
 entries=[x for x in menu if x.get('label')=='Google Drive']
 assert len(entries)==1 and entries[0]['path']=='plugin://plugin.googledrive/','Personalized or duplicate Drive route'
 result=check_ios(root)
 return {'passed':True,'credential_free_profile':True,'approved_relay':settings['sign-in-server'],'private_account_state_included':False,'subtitles_enabled':True,'resume_prompt_enabled':True,'directory_listing_enabled':False,'export_folder_cleanup_enabled':False,'dependency_candidates':result['dependency_candidates'],'ios_runtime_verified':False}
if __name__=='__main__':
 result=check();(ROOT/'reports/drive-integration-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
