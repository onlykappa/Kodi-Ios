"""Generate a capture checklist from all sanitized original/target Fuse routes."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def preserve_evidence(records,previous):
 old={r['id']:r for r in previous};merged=[]
 for row in records:
  prior=old.pop(row['id'],None)
  if prior:
   if prior.get('route_sha256',prior.get('route'))==row.get('route_sha256',row.get('route')):
    row={**prior,**row,'status':prior.get('status',row['status']),'evidence':prior.get('evidence')}
   else:
    history=prior.pop('previous_versions',[])
    row['previous_versions']=history+[prior]
  merged.append(row)
 for row in old.values():merged.append({**row,'source_removed':True,'exclusion_review_required':True})
 return merged

def build():
 records=[]
 for origin,base in [('baseline','snapshot/userdata'),('target','migration/ios/userdata')]:
  folder=ROOT/base/'addon_data/script.skinvariables/nodes/skin.arctic.fuse.3'
  for path in sorted(folder.glob('*.json')):
   for index,item in enumerate(json.loads(path.read_text())):
    key=f'{origin}/{path.name}/{index}';records.append({'id':'MENU-'+hashlib.sha256(key.encode()).hexdigest()[:12],'origin':origin,'source':path.relative_to(ROOT).as_posix(),'slot':index,'label':item.get('label',''),'route_sha256':hashlib.sha256(item.get('path','').encode()).hexdigest(),'required_states':['populated','loading','empty','error'],'orientations':['landscape-left','landscape-right','portrait-attempt-record-supported-or-rejected'],'status':'AWAITING DEVICE TESTING' if origin=='target' else 'AWAITING SAFE-COPY CAPTURE','evidence':None})
 fixed=['cold-start','home-main','home-spotlight','all-main-menu-navigation','media-list','media-details-artwork','global-search','search-keyboard','addon-browser','addon-install','addon-settings','skin-layout-settings','skin-navigation-settings','general-settings','system-settings','player-settings','interface-settings','media-settings','services-settings','file-manager-profile-path','selection-dialog','context-menu','confirmation-dialog','network-error','dependency-error','drive-consent-safe-entry','drive-cancelled-auth','drive-auth-error','drive-browse','drive-play-start','video-osd','video-controls-touch','video-pause','video-seek','video-subtitles','video-audio','video-resume-prompt','video-resume-cancel','background-foreground','process-relaunch','clean-target-rollback']
 for route in fixed:records.append({'id':'SCREEN-'+route,'route':route,'origin':'paired','required_states':['normal','empty-or-loading-if-applicable','safe-error-if-applicable'],'orientations':['landscape-left','landscape-right','portrait-attempt-record-supported-or-rejected'],'status':'AWAITING DEVICE TESTING','evidence':None})
 destination=ROOT/'reports/device-capture-roster.json'
 previous=json.loads(destination.read_text())['records'] if destination.exists() else []
 records=preserve_evidence(records,previous)
 result={'status':'CAPTURE CHECKLIST METADATA ONLY; THIS GENERATOR CREATES NO SCREENSHOTS','records':records,'count':len(records),'device':'owner-reported iPhone 16 Pro / iOS 27.0.1','requirements':'Every applicable state/orientation needs actual capture or issue/owner-accepted exclusion. No mockups. Raw images, account codes and private media stay outside Git.'}
 assert len({r['id'] for r in records})==len(records)
 (ROOT/'reports/device-capture-roster.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'roster_entries':len(records),'screenshots_generated':0,'entries_with_recorded_evidence':sum(bool(r.get('evidence')) for r in records)}))
if __name__=='__main__':build()
