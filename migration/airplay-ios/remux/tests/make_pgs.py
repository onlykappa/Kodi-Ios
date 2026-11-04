"""Generate a small PGS display set and explicit clear; synthetic pixels only."""
import struct,sys
from pathlib import Path
out=bytearray()
def segment(kind,payload,time):
 out.extend(b'PG'+struct.pack('>II',time*90000,time*90000)+bytes([kind])+struct.pack('>H',len(payload))+payload)
def pcs(time,objects,state=0):
 data=struct.pack('>HHBHB',320,180,0x20,time,state)+bytes([0,0,len(objects)])
 for oid,x,y in objects:data+=struct.pack('>HBBHH',oid,0,0,x,y)
 segment(0x16,data,time)
pcs(1,[(1,40,130)],0x80)
segment(0x17,bytes([1])+struct.pack('>BHHHH',0,40,130,32,8),1)
segment(0x14,bytes([0,0,0,16,128,128,0,1,235,128,128,255,2,81,240,90,128]),1)
rle=(bytes([1])*16+bytes([2])*16+b'\0\0')*8
segment(0x15,struct.pack('>HBB',1,0,0xc0)+(len(rle)+4).to_bytes(3,'big')+struct.pack('>HH',32,8)+rle,1)
segment(0x80,b'',1)
pcs(3,[])
segment(0x80,b'',3)
Path(sys.argv[1]).write_bytes(out)
