"""Owner-invoked iOS-only enable helper. Does not apply live filesystem imports."""
import hashlib,json,os,sys,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'resources','lib'))
from activation import activate

def run():
 import xbmc,xbmcgui,xbmcvfs
 dialog=xbmcgui.Dialog()
 if not xbmc.getCondVisibility('System.Platform.IOS'):
  dialog.ok('iOS only','This helper refuses to change a Steam Deck or other non-iOS Kodi installation.');return
 home=Path(xbmcvfs.translatePath('special://home/')).resolve();receipt=home/'.kodi-ios-import-receipt.json'
 if not receipt.is_file():dialog.ok('No staged import','Use the reviewed offline import procedure first. No settings or add-ons were changed.');return
 record=json.loads(receipt.read_text());manifests={}
 for rel,expected in record['managed_files'].items():
  parts=Path(rel).parts
  if not parts or parts[0]!='addons':continue
  if '..' in parts or Path(rel).is_absolute():raise ValueError('Unsafe receipt path')
  path=home/rel
  if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
   dialog.ok('Import changed','Copied add-on code differs from the reviewed receipt. Stop and diagnose before enabling it.');return
  if path.name=='addon.xml':
   root=ET.parse(path).getroot();id=root.get('id');manifests[id]={'requires':[d.get('addon') for d in root.findall('requires/import') if d.get('optional')!='true']}
 if not manifests:dialog.ok('No add-ons','No reviewed copied add-on manifests were found.');return
 if not dialog.yesno('Review copied add-ons',str(len(manifests))+' add-ons match the private import receipt. Enable them through Kodi in dependency order? Elementum engine is not included.'):return
 def api(method,params):return json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params})))
 result=activate(api,manifests)
 if result['status']!='API ENABLE REQUESTS ACCEPTED':
  dialog.ok('Activation failed','Stop and record the failed add-on: '+str(result.get('failed_addon'))+'. Newly enabled components were requested disabled again; actual rollback still needs verification.');return
 if dialog.yesno('Enable requests accepted','Inspect add-on errors before proceeding. Select Arctic Fuse 3 now? Kodi may ask you to confirm the skin change.'):
  response=api('Settings.SetSettingValue',{'setting':'lookandfeel.skin','value':'skin.arctic.fuse.3'})
  if 'error' in response or response.get('result') is not True:dialog.ok('Skin change failed','Record the error and keep Estuary available. No runtime success is claimed.')
if __name__=='__main__':run()
