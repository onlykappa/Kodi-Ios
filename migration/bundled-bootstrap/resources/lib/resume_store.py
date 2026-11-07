"""r30 (owner: "fix restarting when its closed and have it keep progress"): where a conversion can carry on from.

One file per video in addon_data/service.kodi.ios.bootstrap/preparation-resume/<slot>.json: the Drive upload session,
how far Drive confirmed, the few bytes from there to the mark (under 256 KiB) and the mark itself (KodiAirPlay's
text). The picture subtitle files wait in the same folder (<slot>.side<track>). Written after Drive confirms a piece
that ends at a mark; read when the conversion starts again; removed when the movie is done or cannot carry on."""
import base64,json,os
from pathlib import Path

def folder(profile):
 path=Path(profile)/'addon_data/service.kodi.ios.bootstrap/preparation-resume';path.mkdir(parents=True,exist_ok=True);return path

def save(profile,slot,identity,checkpoint):
 data={'identity':list(identity),'url':checkpoint['url'],'offset':int(checkpoint['offset']),
       'tail':base64.b64encode(bytes(checkpoint['tail'])).decode(),'mark':checkpoint['mark']}
 path=folder(profile)/(slot+'.json');tmp=path.with_suffix('.tmp')
 with open(tmp,'w',encoding='utf-8') as f:json.dump(data,f);f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)

def load(profile,slot,identity):
 """The checkpoint for this exact Drive file (same id, checksum, size, version), or None."""
 try:data=json.loads((folder(profile)/(slot+'.json')).read_text(encoding='utf-8'))
 except (OSError,ValueError):return None
 if [str(x) for x in data.get('identity',[])]!=[str(x) for x in identity]:return None
 try:return {'url':data['url'],'offset':int(data['offset']),'tail':base64.b64decode(data['tail']),'mark':data['mark']}
 except (KeyError,ValueError,TypeError):return None

def clear(profile,slot):
 for path in folder(profile).glob(slot+'.*'):
  try:path.unlink()
  except OSError:pass

def alive(drive,checkpoint):
 """Drive still has the upload session and exactly the confirmed bytes (sessions last about a week)."""
 import driveupload
 try:status,headers,_=drive.call('PUT',checkpoint['url'],b'',{'Content-Range':'bytes */*'})
 except Exception:return False
 return status==308 and driveupload._next_offset(headers)==checkpoint['offset']
