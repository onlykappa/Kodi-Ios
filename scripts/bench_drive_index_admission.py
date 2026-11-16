"""Loopback benchmark isolating index cache admission; no Google/iPhone timing claim.
Five fresh proxies per mode, identical synthetic bytes, 200 ms per metadata request.
Run: python3 -B scripts/bench_drive_index_admission.py
"""
import sys,time,tempfile,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'migration/bundled-bootstrap/resources/lib')]
from test_drive_index import Drive
import drive_index as di, drive_proxy as dp
import urllib.request,json
class Conn:
 def __init__(self,drive):self.drive=drive
 def request(self,method,path,headers):self.path,self.headers=path,headers
 def getresponse(self):
  from test_drive_index import Response
  if 'fields=' in self.path:
   time.sleep(.2)
   return Response(200,json.dumps(self.drive.metadata('synthetic-file')).encode(),{})
  return self.drive.get('synthetic-file',self.headers.get('Range'))
 def close(self):pass
for background in (False,True):
 cold=[];warm=[]
 for _ in range(5):
  with tempfile.TemporaryDirectory() as directory:
   drive=Drive();server,port=dp.start(lambda force:'synthetic',connect=lambda:Conn(drive),state_dir=directory)
   server.RequestHandlerClass.indices.background=background
   url=dp.url(port,'synthetic-file','fixture.mp4')
   def fetch():
    t=time.monotonic()
    with urllib.request.urlopen(urllib.request.Request(url,headers={'Range':'bytes=128-'})) as r:assert r.read()==drive.index
    return time.monotonic()-t
   cold.append(fetch())
   cache=server.RequestHandlerClass.indices
   while cache.admitting:time.sleep(.005)
   warm.append(fetch())
   server.shutdown();server.server_close()
 print(json.dumps({'background':background,'cold_s':cold,'cold_median_s':statistics.median(cold),'warm_s':warm,'warm_median_s':statistics.median(warm)}))
