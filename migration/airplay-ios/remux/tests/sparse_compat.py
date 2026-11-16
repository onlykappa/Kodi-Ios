"""Real host native HTTP test of long copy windows versus converted video/audio.

Usage: sparse_compat.py LIBKODIAIRPLAY.so FIXTURES WORK
Uses the generated 32-second long-gop.mp4 and subs.srt from run_host_tests.sh.
Host MPEG-4 encoder substitutes for iPhone VideoToolbox; no receiver/device claim.
All media and decoded artifacts remain in WORK, outside Git.
"""
import ctypes,json,re,subprocess,sys,time,urllib.request
from pathlib import Path


def run(library, fixtures, work):
    work.mkdir(parents=True,exist_ok=True)
    lib=ctypes.CDLL(str(library))
    lib.kr_remux_start.argtypes=[ctypes.c_char_p,ctypes.c_int,ctypes.c_int,ctypes.c_char_p,ctypes.c_int]
    lib.kr_remux_message.restype=ctypes.c_char_p
    lib.kr_video_set_encoder.argtypes=[ctypes.c_char_p]
    lib.kr_remux_set_subtitles.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_char_p]
    lib.kr_video_set_encoder(b'mpeg4');lib.kr_remux_set_prefetch(0)
    lib.kr_remux_set_subtitles(-2,str(fixtures/'subs.srt').encode(),b'eng')
    out=ctypes.create_string_buffer(1024)
    assert lib.kr_remux_start(('file:'+str(fixtures/'long-gop.mp4')).encode(),0,2,out,len(out))==2,lib.kr_remux_message()
    root=out.value.decode().rsplit('/',1)[0]
    def get(path, agent='AirPlay/2.0 MFi_AirPlay_Device'):
        url=path if path.startswith('http:') else root+path
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':agent}),timeout=40) as r:return r.read()
    def playlist(path):
        data=get(path).decode();dur=[float(x) for x in re.findall(r'#EXTINF:([\d.]+)',data)]
        urls=[l for l in data.splitlines() if l and not l.startswith('#')]
        return dur,urls
    def packets(path, selector):
        raw=subprocess.check_output(['ffprobe','-v','error','-select_streams',selector,'-show_packets',
                                     '-show_entries','packet=pts_time,duration_time','-of','json',str(path)])
        return [(float(p['pts_time']),float(p.get('duration_time',0))) for p in json.loads(raw)['packets']]
    result={}
    try:
        master=get('/master.m3u8').decode()
        audio=re.search(r'TYPE=AUDIO[^\n]+URI="([^"]+)"',master).group(1)
        copy_dur,copy_urls=playlist('/video/index.m3u8')
        video_dur,video_urls=playlist('/cvideo/index.m3u8')
        audio_dur,audio_urls=playlist(audio)
        result.update(copy_max_s=max(copy_dur),converted_max_s=max(video_dur),converted_segments=len(video_dur),audio_segments=len(audio_dur))
        assert max(copy_dur)>25,'fixture must retain long genuine GOPs'
        assert max(video_dur)<=6.1,result
        assert video_dur==audio_dur,'converted audio and picture must share one timeline'
        assert '/caudio/' in audio,'independent URLs prevent reuse of incompatible audio cache'
        video_init=get('/cvideo/init.mp4');audio_init=get(audio.rsplit('/',1)[0]+'/init.mp4')
        all_video=bytearray(video_init);all_audio=bytearray(audio_init)
        first=time.monotonic()
        # Out-of-order demand exercises resume/seek before fetching the whole sequence.
        seek=get(video_urls[3]);assert seek
        for i,(v,a) in enumerate(zip(video_urls,audio_urls)):
            vp=work/f'video-{i}.mp4';ap=work/f'audio-{i}.mp4'
            vb=get(v);ab=get(a);vp.write_bytes(video_init+vb);ap.write_bytes(audio_init+ab)
            vs=packets(vp,'v');as_=packets(ap,'a')
            assert vs and as_
            assert abs(min(t for t,_ in vs)-min(t for t,_ in as_))<.08,(i,vs[0],as_[0])
            assert max(t+d for t,d in vs)-min(t for t,_ in vs)<=6.1
            all_video+=vb;all_audio+=ab
        (work/'converted.mp4').write_bytes(all_video);(work/'audio.mp4').write_bytes(all_audio)
        video_packets=packets(work/'converted.mp4','v');audio_packets=packets(work/'audio.mp4','a')
        for sequence in (video_packets,audio_packets):
            # The first packet may be edit-list adjusted (and ffprobe may omit its
            # duration). Check continuity after that initial presentation anchor.
            for previous,current in zip(sequence[1:],sequence[2:]):
                assert abs(current[0]-(previous[0]+previous[1]))<.002,'gap/duplicate at a segment boundary'
        assert abs(max(t+d for t,d in video_packets)-max(t+d for t,d in audio_packets))<.08
        # Shared audio demuxer must restore the copy grid after a converted read.
        copy_audio_init=get('/audio/1/init.mp4','AppleCoreMedia/1.0 (iPhone)')
        copy_audio=get('/audio/1/seg0.m4s','AppleCoreMedia/1.0 (iPhone)')
        copy_audio_file=work/'copy-audio.mp4';copy_audio_file.write_bytes(copy_audio_init+copy_audio)
        copied_audio_packets=packets(copy_audio_file,'a')
        assert max(t+d for t,d in copied_audio_packets)-min(t for t,_ in copied_audio_packets)>25
        count=int(subprocess.check_output(['ffprobe','-v','error','-select_streams','v','-count_frames',
                                          '-show_entries','stream=nb_read_frames','-of','csv=p=0',str(work/'converted.mp4')]))
        assert count==768,('converted frame coverage',count)
        result.update(converted_frames=count,sequence_elapsed_s=round(time.monotonic()-first,3))
        # Copied clients keep the long plan even after converted audio has used its own grid.
        copy_init=get('/video/init.mp4','AppleCoreMedia/1.0 (iPhone)')
        copied=bytearray(copy_init)
        for url in copy_urls:copied+=get(url,'AppleCoreMedia/1.0 (iPhone)')
        (work/'copied.mp4').write_bytes(copied)
        def digest(path):
            import hashlib
            return hashlib.sha256(subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:v:0','-c','copy','-f','data','-'])).hexdigest()
        assert digest(fixtures/'long-gop.mp4')==digest(work/'copied.mp4'),'original compressed picture must survive exactly'
        logs=ctypes.create_string_buffer(32768)
        lib.kr_remux_log(logs,len(logs))
        assert re.search(rb'[1-9][0-9]* frames drawn',logs.value),'captions must actually draw into converted frames'
        result['burned_caption_frames_observed']=True
        result['copy_packet_digest_equal']=True
        print(json.dumps(result,sort_keys=True))
    finally:lib.kr_remux_stop()
    # Cleanup owns the timeline view; a second session must remain usable.
    lib.kr_remux_set_subtitles(-1,None,None)
    assert lib.kr_remux_start(('file:'+str(fixtures/'long-gop.mp4')).encode(),0,2,out,len(out))==2
    # Cancel while six-second rendition read-ahead can still own the timeline.
    lib.kr_remux_set_prefetch(1)
    with urllib.request.urlopen(out.value.decode(),timeout=10) as response:response.read()
    # A phone master leaves the copy intact; the TV master begins conversion.
    tv=urllib.request.Request(out.value.decode(),headers={'User-Agent':'AirPlay/2.0 MFi_AirPlay_Device'})
    with urllib.request.urlopen(tv,timeout=10) as response:response.read()
    began=time.monotonic();lib.kr_remux_cancel(0);lib.kr_remux_stop()
    assert time.monotonic()-began<2,'cancel must release active producers and the timeline'
    assert lib.kr_remux_start(('file:'+str(fixtures/'long-gop.mp4')).encode(),0,2,out,len(out))==2
    lib.kr_remux_stop()

if __name__=='__main__':run(*(Path(p).resolve() for p in sys.argv[1:]))
