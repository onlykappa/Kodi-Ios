"""Synthetic HEVC + public profile-5 RPU metadata; no picture/audio from the upstream fixture.
RPU fixture: quietvoid/dovi_tool, 41dae646193c12de152333ff5dbc33579cb9ef4a,
assets/tests/profile5-02.bin (MIT, Copyright (c) 2026 quietvoid). Full terms in THIRD-PARTY-NOTICES.
"""
import math,re,struct,subprocess,sys,tempfile
from pathlib import Path
# Reshaping curves changed to identity with pinned FFmpeg 8.1.1 RPU encoder; color matrices retained.
RPU=bytes.fromhex('00000001190809004061b6506f003ff801ffc00fffd0000008000006800000400000340000030200000301a2000031f06912000fc5b04432000010bea57000000300008000000300800000042b9fea3fea3fea342b9fea3fea3fea342b9ffff000000300000300000300064200f80e1518120c07d00002075e000060100082133301805043ffefe30010010008000404004001100a0000030001dc0ee0cc2e525a80')
with tempfile.TemporaryDirectory() as work:
 raw=Path(work)/'source.hevc';annotated=Path(work)/'rpu.hevc'
 # Construct physically valid BT.2020/PQ RGB colors, then invert this fixture's RPU matrices to IPT codes.
 # Ordinary YCbCr test bars are not valid profile-5 colors and confound color-transform/gamut comparisons.
 inv_n=((.4001284426768005,.3998902762533815,.19998128106981802),
        (4.4553440414793135,-4.851464141610838,.39612010013152427),(.805668000267507,.35717948011859474,-1.1628474803861018))
 inv_l=((.4264360533712833,.5296722954198111,.043955033674126974),
        (.16433479032967263,.7395529653593176,.09617127989717897),(.012070665891385106,.050658337687246625,.9371883992656217))
 def decode(v):
  p=v**(32/2523);return (max(p-3424/4096,0)/(2413/128-2392/128*p))**(16384/2610)
 def encode(v):
  p=max(v,0)**(2610/16384);return ((3424/4096+2413/128*p)/(1+2392/128*p))**(2523/32)
 planes=[[],[],[]]
 for y in range(180):
  for x in range(320):
   rgb=list(map(decode,(.2+.5*x/319,.2+.4*y/179,.3+.2*math.sin(x/319*math.pi))))
   lms=[encode(sum(row[j]*rgb[j] for j in range(3))) for row in inv_l]
   for k,row in enumerate(inv_n):planes[k].append(max(0,min(1023,round((sum(row[j]*lms[j] for j in range(3))+(0 if k==0 else .5))*1024))))
 picture=Path(work)/'pattern.yuv';data=bytearray()
 for k,plane in enumerate(planes):
  values=plane if k==0 else [round(sum(plane[(y+dy)*320+x+dx] for dy in range(2) for dx in range(2))/4) for y in range(0,180,2) for x in range(0,320,2)]
  data.extend(struct.pack('<'+'H'*len(values),*values))
 picture.write_bytes(data)
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-stream_loop','-1','-f','rawvideo','-pixel_format','yuv420p10le',
  '-video_size','320x180','-framerate','12','-i',str(picture),'-t','20','-c:v','libx265','-preset','ultrafast','-pix_fmt','yuv420p10le',
  '-color_range','pc','-x265-params','lossless=1:keyint=24:min-keyint=24:scenecut=0:bframes=0:slices=1:log-level=error:pools=none',str(raw)],check=True)
 data=raw.read_bytes();starts=list(re.finditer(b'\x00\x00(?:\x00)?\x01',data));output=bytearray()
 for i,m in enumerate(starts):
  end=starts[i+1].start() if i+1<len(starts) else len(data)
  output.extend(data[m.start():end]);kind=(data[m.end()]>>1)&63
  if kind<=31:output.extend(b'\x00\x00\x00\x01\x7c\x01'+RPU[4:])
 annotated.write_bytes(output)
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-fflags','+genpts','-r','12','-i',str(annotated),'-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=20','-map','0:v','-map','1:a','-c:v','copy','-c:a','aac',sys.argv[1]],check=True)
