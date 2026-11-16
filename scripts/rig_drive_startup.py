"""Exercise a running desktop Kodi over the production Drive proxy with a local media fixture.

Usage: python3 -B scripts/rig_drive_startup.py --fixture /tmp/fixtures/coalesced.mp4 --work /tmp/drive-rig
Requires Kodi JSON-RPC on port 8089, ImageMagick import and an X server (default :97).
These are desktop fixture checks: timeline advance and saved screenshots, not precise first-picture timings,
real OAuth/Google throughput, full skin/watch lookup, iPhone or TV evidence. Media/screenshots stay outside Git.
"""
import sys,json,time,urllib.request,tempfile,hashlib,io,re,subprocess,threading
from pathlib import Path
import argparse,os
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--fixture',required=True,type=Path)
parser.add_argument('--work',required=True,type=Path)
parser.add_argument('--display',default=':97')
args=parser.parse_args()
work=args.work.resolve()
if work==ROOT or ROOT in work.parents:parser.error('--work must be outside the checkout')
work.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import drive_proxy as dp
fixture=args.fixture.read_bytes()
class Resp(io.BytesIO):
 def __init__(self,status,data,h):super().__init__(data);self.status=status;self.h=h
 def getheader(self,key,default=None):return self.h.get(key,default)
class Conn:
 mode='normal';requests=0
 def request(self,m,path,headers):self.path,self.headers=path,headers
 def getresponse(self):
  Conn.requests+=1
  if Conn.mode=='fail':return Resp(503,b'',{})
  if Conn.mode=='slow':time.sleep(.3)
  if 'fields=' in self.path:
   meta={'id':'fixture','size':len(fixture),'md5Checksum':hashlib.md5(fixture).hexdigest(),'version':'1','modifiedTime':'2026-11-16','mimeType':'video/mp4'}
   return Resp(200,json.dumps(meta).encode(),{})
  span=re.match(r'bytes=(\d+)-(\d*)',self.headers.get('Range',''))
  if span:
   a=int(span[1]);b=min(int(span[2]) if span[2] else len(fixture)-1,len(fixture)-1)
   return Resp(206,fixture[a:b+1],{'Content-Length':str(b-a+1),'Content-Range':f'bytes {a}-{b}/{len(fixture)}','Content-Type':'video/mp4'})
  return Resp(200,fixture,{'Content-Length':str(len(fixture)),'Content-Type':'video/mp4'})
 def close(self):pass

def rpc(method,params=None):
 req=urllib.request.Request('http://127.0.0.1:8089/jsonrpc',data=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params or {}}).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=5) as r:
  response=json.load(r)
  if 'error' in response:raise RuntimeError(response['error'])
  return response.get('result')

def players():return rpc('Player.GetActivePlayers') or []
def stop():
 for p in players():rpc('Player.Stop',{'playerid':p['playerid']})
 time.sleep(.3)

with tempfile.TemporaryDirectory() as folder:
 server,port=dp.start(lambda force:'fixture',connect=Conn,state_dir=folder)
 url=dp.url(port,'fixture','Completed.mp4')
 outcomes=[]
 def play(name,mode='normal',resume=None):
  stop();Conn.mode=mode;began=time.monotonic();seen=0;last=None
  options={}
  if resume is not None:options['resume']={'hours':0,'minutes':0,'seconds':resume,'milliseconds':0}
  rpc('Player.Open',{'item':{'file':url},'options':options})
  while time.monotonic()-began<10:
   ps=players()
   if ps:
    last=rpc('Player.GetProperties',{'playerid':ps[0]['playerid'],'properties':['time','speed','position']})
    t=(last.get('time') or {}) if isinstance(last,dict) else {}
    at=t.get('minutes',0)*60+t.get('seconds',0)+t.get('milliseconds',0)/1000
    if at>=(resume or 0)+.3:
     seen=at;break
   time.sleep(.1)
  subprocess.run(['import','-display',args.display,'-window','root',str(work/f'{name}.png')],check=True)
  record={'scenario':name,'timeline_advanced':bool(seen),'observed_position':seen,'elapsed_to_timeline_s':round(time.monotonic()-began,3)}
  outcomes.append(record);print(json.dumps(record),flush=True)
  if mode!='fail':assert seen,record
  else:assert not seen,record
  return record
 try:
  play('cold');play('warm');r=play('resume',resume=18);assert r['observed_position']>=18
  play('slow',mode='slow');play('failed',mode='fail')
  play('recovered');stop()
  # Cancel an in-progress slow open, then verify the next open works.
  Conn.mode='slow';rpc('Player.Open',{'item':{'file':url}});time.sleep(.1);stop()
  play('after-cancel');stop()
  print(json.dumps({'evidence':'desktop Kodi, production proxy with Drive-interface fixture','scenarios':outcomes,'upstream_requests':Conn.requests}),flush=True)
 finally:server.shutdown();server.server_close()
