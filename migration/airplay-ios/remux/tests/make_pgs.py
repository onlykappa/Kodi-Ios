"""Synthetic PGS display/clear; --long adds seek/cache cues, --vobsub generates an IDX/SUB pair via FFmpeg."""
import struct,sys
from pathlib import Path
out=bytearray()
def segment(kind,payload,time):
 out.extend(b'PG'+struct.pack('>II',time*90000,time*90000)+bytes([kind])+struct.pack('>H',len(payload))+payload)
def pcs(time,objects,state=0):
 data=struct.pack('>HHBHB',320,180,0x20,time,state)+bytes([0,0,len(objects)])
 for oid,x,y in objects:data+=struct.pack('>HBBHH',oid,0,0,x,y)
 segment(0x16,data,time)
def cue(start,end):
 pcs(start,[(1,40,130)],0x80)
 segment(0x17,bytes([1])+struct.pack('>BHHHH',0,40,130,32,8),start)
 segment(0x14,bytes([0,0,0,16,128,128,0,1,235,128,128,255,2,81,240,90,128]),start)
 rle=(bytes([1])*16+bytes([2])*16+b'\0\0')*8
 segment(0x15,struct.pack('>HBB',1,0,0xc0)+(len(rle)+4).to_bytes(3,'big')+struct.pack('>HH',32,8)+rle,start)
 segment(0x80,b'',start)
 pcs(end,[])
 segment(0x80,b'',end)
if '--long' in sys.argv:
 cue(1,60);cue(120,150)
 for t in range(200,800,2):cue(t,t+1)
else:cue(1,3)
target=Path(sys.argv[1])
if '--vobsub' in sys.argv:
 import subprocess,tempfile
 with tempfile.TemporaryDirectory() as work:
  source=Path(work)/'fixture.sup';source.write_bytes(out)
  subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-fix_sub_duration','-i',str(source),
                  '-map','0:s:0','-c:s','dvdsub','-f','mpeg',str(target.with_suffix('.sub'))],check=True)
 target.write_text('# VobSub index file, v7 (do not modify this line!)\nsize: 320x180\n'
                   'palette: 000000, 0000ff, 00ff00, ff0000, ffff00, ff00ff, 00ffff, ffffff, '
                   '808000, 8080ff, 800080, 80ff80, 008080, ff8080, 555555, aaaaaa\n'
                   'id: en, index: 0\ntimestamp: 00:00:01:000, filepos: 000000000\n')
else:target.write_bytes(out)
