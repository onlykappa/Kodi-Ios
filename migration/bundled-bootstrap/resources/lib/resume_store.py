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
       'tail':base64.b64encode(bytes(checkpoint['tail'])).decode(),'mark':checkpoint['mark'],
       'pieces':[list(p) for p in checkpoint.get('pieces') or []]}
 path=folder(profile)/(slot+'.json');tmp=path.with_suffix('.tmp')
 with open(tmp,'w',encoding='utf-8') as f:json.dump(data,f);f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)

def load(profile,slot,identity):
 """The checkpoint for this exact Drive file (same id, checksum, size, version), or None."""
 try:data=json.loads((folder(profile)/(slot+'.json')).read_text(encoding='utf-8'))
 except (OSError,ValueError):return None
 if [str(x) for x in data.get('identity',[])]!=[str(x) for x in identity]:return None
 try:return {'url':data['url'],'offset':int(data['offset']),'tail':base64.b64decode(data['tail']),'mark':data['mark'],
             'pieces':[[int(a),int(b),str(c)] for a,b,c in data.get('pieces') or []]}
 except (KeyError,ValueError,TypeError):return None

def clear(profile,slot):
 for path in folder(profile).glob(slot+'.*'):
  try:path.unlink()
  except OSError:pass

def confirmed(drive,checkpoint):
 """How many bytes Drive holds in the checkpoint's upload session, or None when the session is gone (they last about a
 week)."""
 import driveupload
 try:status,headers,_=drive.call('PUT',checkpoint['url'],b'',{'Content-Range':'bytes */*'})
 except Exception:return None
 return driveupload._next_offset(headers) if status==308 else None

def alive(drive,checkpoint):
 """Drive holds exactly the checkpoint's confirmed bytes."""
 return confirmed(drive,checkpoint)==checkpoint['offset']

def mark_seconds(text):
 """How far into the film a mark is (the latest of its inputs' next packets), in seconds."""
 out=0.0
 for line in str(text or '').splitlines():
  parts=line.split()
  if len(parts)==7 and parts[0]=='in' and parts[2]=='0':
   try:out=max(out,float(parts[6]))
   except ValueError:pass
 return out

def pieces_from(pieces,first,end):
 """The bytes [first, end) from kept piece files, or None if any of them is missing."""
 out=bytearray();at=first
 for start,stop,path in sorted(pieces):
  if stop<=at or start>=end:continue
  if start>at:return None
  try:
   with open(path,'rb') as f:f.seek(at-start);out+=f.read(min(stop,end)-at)
  except OSError:return None
  at=min(stop,end)
  if at>=end:break
 return bytes(out) if at>=end else None

def fit(checkpoint,held,copied):
 """The checkpoint for carrying on when Drive holds `held` bytes, or None to start again.
 Build 190 (end-to-end test): on a slow line Drive is nearly always between two marks, past the saved one, when Kodi
 is closed. Up to the mark, the kept tail fills the gap. Past it, a copied picture (and its audio, re-encoded or not)
 comes out byte for byte the same from the mark on, so the converter carries on from the mark and the bytes Drive
 already has are skipped. A re-encoded picture is not known to repeat exactly (hardware encoder), so it starts again."""
 if checkpoint is None or held is None:return None
 start=checkpoint['offset'];tail=bytes(checkpoint['tail']);mark=start+len(tail)
 if held<start:
  # Build 190: pieces kept on disk (a re-encode) cover what Drive has not confirmed yet.
  kept=pieces_from(checkpoint.get('pieces') or [],held,start)
  if kept is None:return None
  return dict(checkpoint,offset=held,tail=kept+tail,skip=0)
 if held<=mark:return dict(checkpoint,offset=held,tail=tail[held-start:],skip=0)
 if copied:return dict(checkpoint,offset=held,tail=b'',skip=held-mark)
 return None
