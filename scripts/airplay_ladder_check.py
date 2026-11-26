"""ISSUE-495 host check: what the AirPlay remuxer's own timestamp code (gm_ts.c) does to a video's picture times.
Needs cc, ffprobe and (with no file given) ffmpeg with libx265. It imitates gm_stream.c's segment plan and cut (first keyframe
at or after each 6 s boundary, packets in decode order) and does not run the MP4 muxer, so it proves nothing about a TV.
usage: python3 -B scripts/airplay_ladder_check.py [video ...]"""
import ctypes as C,subprocess,sys,tempfile
from pathlib import Path
SRC=Path(__file__).resolve().parents[1]/'migration/airplay-ios/remux/gmplayer'
class State(C.Structure):_fields_=[(n,C.c_int64) for n in ('step_num','step_den','lead','count','first_pts','last_dts')]+[('have_first',C.c_int)]
class Fixed(C.Structure):_fields_=[('pts',C.c_int64),('dts',C.c_int64),('clamped',C.c_int)]

def build(folder):
 out=Path(folder)/'libgmts.so';subprocess.check_call(['cc','-shared','-fPIC','-O2','-o',str(out),str(SRC/'gm_ts.c')])
 lib=C.CDLL(str(out));lib.gm_ts_next.restype=Fixed;lib.gm_ts_next.argtypes=[C.POINTER(State)]+[C.c_int64]*3
 lib.gm_ts_init.argtypes=[C.POINTER(State)]+[C.c_int64]*5;return lib

def probe(path,entries):
 return subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries',entries,'-of','csv=p=0',str(path)],text=True).split()

def check(lib,path):
 delay,rate,base=probe(path,'stream=has_b_frames,r_frame_rate,time_base')[0].split(',')[:3]
 num,den=map(int,rate.split('/'));ticks=int(base.split('/')[1]);delay=int(delay)
 packets=[(int(a),int(b),'K' in c) for a,b,c in (line.split(',')[:3] for line in probe(path,'packet=pts,dts,flags'))]
 starts=[0]
 for i,(pts,_,key) in enumerate(packets):
  if key and pts-packets[starts[-1]][0]>=6*ticks and packets[-1][0]-pts>=3*ticks:starts.append(i)
 lead=min((delay or 1)+2,16);step=ticks*den/num;ends=starts[1:]+[len(packets)];previous=None;shown=[]
 print('%s: %d frames, reorder %d, lead %d'%(path,len(packets),delay,lead));print(' segment starts_at_s frames leading moved largest_move_frames join_error_frames')
 for number,(first,last) in enumerate(zip(starts,ends)):
  part=packets[first:last];state=State();lib.gm_ts_init(C.byref(state),num,den,1,ticks,lead)
  out=[lib.gm_ts_next(C.byref(state),p,d,0) for p,d,_ in part];moves=[o.pts-p for o,(p,_,_) in zip(out,part) if o.pts!=p]
  join=0 if previous is None else round((out[0].dts-previous)/step-1,2);previous=out[-1].dts;shown+=[o.pts for o in out]
  print(' ',number,round(part[0][0]/ticks,3),len(part),sum(p<part[0][0] for p,_,_ in part),len(moves),round(max(moves,default=0)/step,2),join,sep='\t')
 print(' frames sharing a picture time with another: %d'%(len(shown)-len(set(shown))))

def samples(folder):
 for name,options in (('closed-bframes8','bframes=8:b-adapt=0:open-gop=0'),('open-bframes4','bframes=4:b-adapt=0:open-gop=1'),
                      ('open-bframes8','bframes=8:b-adapt=0:open-gop=1'),('open-bframes8-adaptive','bframes=8:b-adapt=2:open-gop=1')):
  path=Path(folder)/(name+'.mp4')
  subprocess.check_call(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i','testsrc2=size=320x160:rate=24000/1001:duration=60','-vf','format=yuv420p10le',
   '-c:v','libx265','-preset','fast','-x265-params',options+':b-pyramid=1:keyint=96:min-keyint=24:scenecut=40:log-level=error','-video_track_timescale','24000',str(path)])
  yield path

if __name__=='__main__':
 with tempfile.TemporaryDirectory() as folder:
  lib=build(folder)
  for path in sys.argv[1:] or samples(folder):check(lib,path)
