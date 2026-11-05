"""Independent optional libplacebo/Vulkan pixel comparison after the native host suite.
Usage: python3 -B test_dovi_reference.py FIXTURE_DIR [--legacy-code-normalization]
Requires a Vulkan driver (software lavapipe works) and system FFmpeg with libplacebo.
Old libplacebo 7.349 divides codes by 2^N-1; the flag adjusts its input to the current
libplacebo convention used by our renderer (code / 2^BL_bit_depth). No tolerance is
added for that convention difference. All generated picture/audio is synthetic.
"""
import argparse,array,json,math,os,subprocess,sys,tempfile
from pathlib import Path

def values(path):
 data=array.array('H');data.frombytes(Path(path).read_bytes())
 if sys.byteorder!='little':data.byteswap()
 return data

def nits(pq):
 p=pq**(32/2523)
 return (max(p-3424/4096,0)/(2413/128-2392/128*p))**(16384/2610)*10000

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('fixture_dir',type=Path);parser.add_argument('--legacy-code-normalization',action='store_true')
 args=parser.parse_args();actual=values(args.fixture_dir/'out/dovi-rgb48.raw')
 errors=[];linear=[];ignored=[]
 with tempfile.TemporaryDirectory() as work:
  for apply in (True,False):
   output=Path(work)/('reference.raw' if apply else 'ignored.raw')
   filters='scale=iw:ih:flags=bilinear:in_range=full:out_range=full:in_h_chr_pos=128,format=yuv444p16le,'
   if args.legacy_code_normalization:filters+="lut=y='val*65535/65536':u='val*65535/65536':v='val*65535/65536',"
   filters+=('hwupload,libplacebo=format=rgba64le:colorspace=gbr:color_primaries=bt2020:color_trc=smpte2084:range=pc:'
             'tonemapping=clip:gamut_mode=clip:peak_detect=false:upscaler=bilinear:downscaler=bilinear:'
             'sigmoid=false:dithering=none:apply_dolbyvision='+str(apply).lower()+',hwdownload,format=rgba64le')
   subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-init_hw_device','vulkan=vk:0','-filter_hw_device','vk',
                   '-i',str(args.fixture_dir/'dovi.mkv'),'-map','0:v:0','-vf',filters,'-frames:v','1','-f','rawvideo',str(output)],check=True)
   expected=values(output)
   if len(actual)!=320*180*3 or len(expected)!=320*180*4:raise AssertionError('unexpected reference image dimensions')
   for i,sample in enumerate(actual):
    a=sample/65535;b=expected[(i//3)*4+i%3]/65535
    if apply:errors.append(abs(a-b));linear.append(abs(nits(a)-nits(b)))
    else:ignored.append(abs(a-b))
 report={'renderer':'system FFmpeg/libplacebo on Vulkan (software driver permitted)',
         'legacy_code_normalization':args.legacy_code_normalization,'samples':len(errors),
         'mean_pq_error':sum(errors)/len(errors),'max_pq_error':max(errors),
         'mean_absolute_nits_error':sum(linear)/len(linear),'max_absolute_nits_error':max(linear),
         'mean_pq_error_when_reference_ignores_rpu':sum(ignored)/len(ignored),
         'limits':{'mean_pq_error':.0001,'mean_absolute_nits_error':.02,'max_absolute_nits_error':.5,
                   'minimum_negative_control_pq_error':.05}}
 report['passed']=(report['mean_pq_error']<.0001 and report['mean_absolute_nits_error']<.02 and
                   report['max_absolute_nits_error']<.5 and report['mean_pq_error_when_reference_ignores_rpu']>.05)
 print(json.dumps(report,indent=2));return 0 if report['passed'] else 1

if __name__=='__main__':sys.exit(main())
