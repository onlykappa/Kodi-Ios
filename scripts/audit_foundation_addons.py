"""Inventory real iOS foundation APIs/native dependencies without executing them."""
import argparse,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def audit(app,plan):
 selected={a['id']:a for a in plan['addons']};found={}
 for p in app.rglob('addon.xml'):
  if p.is_symlink():continue
  try:r=ET.parse(p).getroot()
  except ET.ParseError:continue
  id=r.get('id')
  if id not in selected:continue
  found.setdefault(id,[]).append({'version':r.get('version'),'manifest':p.relative_to(app).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'requires':[{'id':d.get('addon'),'minimum_version':d.get('version'),'optional':d.get('optional')=='true'} for d in r.findall('requires/import')]})
 return {'source':'Actual hash-pinned official Kodi iOS 21.3 app, static inspection only','found':found,'not_bundled':[i for i in selected if i not in found],'pillow_candidates':[p.relative_to(app).as_posix() for p in app.rglob('*') if p.is_file() and ('_imaging' in p.name or p.name=='Image.py')],'python_layout_directories':sorted({p.parent.as_posix().split('/')[-1] for p in app.rglob('os.py') if p.is_file()}),'runtime_import_or_playback_tested':False}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('app',type=Path);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
 result=audit(a.app,json.loads((ROOT/'migration/ios/addon-plan.json').read_text()));a.report.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
