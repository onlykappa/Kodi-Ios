#!/usr/bin/env python3
"""Backup playback inside real Kodi 21.3 on the desktop rig (steps 6, 7 and 18 groundwork): no debrid key, no account.

Run after `kodi_rig.py setup`/`start`. The orchestrator makes small media with ffmpeg, serves it over loopback HTTP (one server demands a header and a
cookie), seeds a generated torrent with libtorrent on loopback, then asks Kodi (RunScript) to open each stream through this repository's
backup_playback / fresh_resolve / KodiPlayer and reports what Kodi really did: playback time advancing, then stop.
Evidence class: desktop Kodi rig. The torrent case uses libtorrent plus a small HTTP gateway as a STAND-IN for Elementum's engine (which is the iOS
native build and is not here), and a loopback seed, because this sandbox cannot reach real swarms. Reports stay private (KODI_RIG_HOME), never in Git.
"""
import hashlib,http.server,json,os,shutil,socketserver,subprocess,sys,tempfile,threading,time,urllib.parse
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'migration/bundled-bootstrap/resources/lib'
RIG=Path(os.environ.get('KODI_RIG_HOME',Path.home()/'.cache/kodi-rig'))
LT=os.environ.get('KODI_RIG_LIBTORRENT','')       # folder holding a libtorrent wheel's files (optional)
TOKEN='rig-token-1'
COOKIE='sid=rigcookie'
INTERNET_HLS='https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8'     # Big Buck Bunny, a public test stream (no account, no key)


def make_media(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    mp4=folder/'clip.mp4'
    base=['ffmpeg','-v','error','-y','-f','lavfi','-i','testsrc2=size=320x180:rate=25','-f','lavfi','-i','sine=frequency=440:sample_rate=44100','-t','20','-c:v','libx264','-pix_fmt','yuv420p','-g','50','-c:a','aac']
    subprocess.run(base+[str(mp4)],check=True)
    hls=folder/'hls';hls.mkdir(exist_ok=True)
    subprocess.run(base+['-f','hls','-hls_time','2','-hls_playlist_type','vod','-hls_segment_filename',str(hls/'seg%d.ts'),str(hls/'index.m3u8')],check=True)
    (folder/'master.m3u8').write_text('#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=400000,RESOLUTION=320x180\nhls/index.m3u8\n')
    return folder


class Handler(http.server.SimpleHTTPRequestHandler):
    """Serves the media folder; a path under /guarded/ needs the header and (after the master) the cookie."""
    root=None;hits=[]
    def translate_path(self,path):
        p=urllib.parse.urlsplit(path).path
        if p.startswith('/guarded/'):p=p[len('/guarded'):]
        return str(Path(self.root)/p.lstrip('/'))
    def log_message(self,*a):pass
    def guard(self):
        path=urllib.parse.urlsplit(self.path).path
        Handler.hits.append((path,self.headers.get('X-Token'),self.headers.get('Cookie'),self.headers.get('Range')))
        if path.startswith('/guarded/'):
            if self.headers.get('X-Token')!=TOKEN:self.send_error(403);return False
            if path.startswith('/guarded/hls/') and COOKIE not in (self.headers.get('Cookie') or ''):self.send_error(403);return False
        return True
    def do_GET(self):
        if self.guard():super().do_GET()
    def do_HEAD(self):
        if self.guard():super().do_HEAD()
    def end_headers(self):
        if urllib.parse.urlsplit(self.path).path.endswith('master.m3u8') and self.path.startswith('/guarded/'):self.send_header('Set-Cookie',COOKIE+'; Path=/')
        super().end_headers()


def serve(folder):
    Handler.root=str(folder);server=socketserver.ThreadingTCPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
    threading.Thread(target=server.serve_forever,daemon=True).start();return server


def torrent_case(folder):
    """A real .torrent of the clip, seeded and fetched with libtorrent on loopback; returns its description or None when libtorrent is missing."""
    if LT:sys.path.insert(0,LT)
    try:import libtorrent as lt
    except ImportError:return None
    src=Path(folder)/'seed';src.mkdir(exist_ok=True);shutil.copy(Path(folder)/'clip.mp4',src/'clip.mp4')
    fs=lt.file_storage();lt.add_files(fs,str(src/'clip.mp4'));ct=lt.create_torrent(fs,piece_size=16384);lt.set_piece_hashes(ct,str(src))
    data=lt.bencode(ct.generate());info=lt.torrent_info(data)
    seed=lt.session({'listen_interfaces':'127.0.0.1:0','enable_dht':False,'enable_lsd':False,'enable_upnp':False,'enable_natpmp':False,'allow_multiple_connections_per_ip':True})
    h=seed.add_torrent({'ti':info,'save_path':str(src),'flags':lt.torrent_flags.seed_mode});time.sleep(.5)
    leech=lt.session({'listen_interfaces':'127.0.0.1:0','enable_dht':False,'enable_lsd':False,'enable_upnp':False,'enable_natpmp':False,'allow_multiple_connections_per_ip':True})
    down=Path(folder)/'leech';down.mkdir(exist_ok=True)
    hl=leech.add_torrent({'ti':info,'save_path':str(down)});hl.connect_peer(('127.0.0.1',seed.listen_port()))
    t0=time.time()
    while not hl.status().is_seeding and time.time()-t0<60:time.sleep(.3)
    return {'data':data,'hash':str(info.info_hashes().v1),'done':hl.status().is_seeding,'file':down/'clip.mp4','sessions':(seed,leech,h,hl)}


def run(args):
    sys.path.insert(0,str(ROOT/'scripts'));global kodi_rig;import kodi_rig
    work=Path(tempfile.mkdtemp(prefix='rig-backup-'));media=make_media(work/'media');server=serve(media);port=server.server_address[1]
    cases={'file_header':{'kind':'file','url':'http://127.0.0.1:%d/guarded/clip.mp4'%port,'headers':{'X-Token':TOKEN}},
           'hls_header_cookie':{'kind':'hls','url':'http://127.0.0.1:%d/guarded/master.m3u8'%port,'headers':{'X-Token':TOKEN}},
           'hls_missing_header':{'kind':'hls','url':'http://127.0.0.1:%d/guarded/master.m3u8'%port,'headers':{},'expect':'refused'},
           'internet_hls_no_key':{'kind':'hls','url':INTERNET_HLS,'headers':{}}}
    torrent=torrent_case(media)
    if torrent:
        (work/'clip.torrent').write_bytes(torrent['data'])
        cases['torrent_loopback_standin']={'kind':'torrent','url':'http://127.0.0.1:%d/leech/clip.mp4'%port,'hash':torrent['hash'],'torrent':str(work/'clip.torrent'),'headers':{}}
        cases['torrent_loopback_standin']['url']='http://127.0.0.1:%d/leech/clip.mp4'%port
    report={}
    for name,case in cases.items():
        out=RIG/('backup-'+name+'.json');out.unlink(missing_ok=True)
        (RIG/('backup-'+name+'.case')).write_text(json.dumps(case))
        kodi_rig.run_builtins('RunScript(%s,--inside-kodi,%s,%s)'%(Path(__file__).resolve(),name,out))
        t0=time.time()
        while not out.exists() and time.time()-t0<90:time.sleep(.5)
        report[name]=json.loads(out.read_text()) if out.exists() else {'error':'no answer from Kodi in 90 s'}
    (RIG/'backup-report.json').write_text(json.dumps(report,indent=1))
    for k,v in report.items():print(k,json.dumps(v)[:300])
    print('guarded requests seen by the server:',[(h[0],h[1] is not None,bool(h[2])) for h in Handler.hits if h[0].startswith('/guarded/')][:12])
    return 0


def inside(name,output):
    """Runs in Kodi's Python: opens the case through the repository's own modules and records what Kodi did."""
    import xbmc
    sys.path.insert(0,str(LIB))
    import backup_playback as bp,fresh_resolve as fr,source_contract as sc
    case=json.loads((RIG/('backup-'+name+'.case')).read_text());result={'case':name}
    try:
        player=bp.KodiPlayer();pb=bp.Playback(player)
        if case['kind']=='torrent':
            data=Path(case['torrent']).read_bytes();result['hash_ok']=bp.verify_torrent({'torrent_hash':case['hash'],'magnet':'magnet:?xt=urn:btih:'+case['hash']},data)==case['hash']
        def resolve():
            r=fr.Resolved(case['url'],case['headers'],time.time(),ttl=300)
            if case['kind']!='torrent':fr.verify_chain(r)
            return r
        t0=time.time();state=pb.start_resolved(('rig',name),resolve)
        result.update(outcome=state,seconds=round(time.time()-t0,1),time=round(player.time(),1))
        time.sleep(3);later=player.time();result.update(time_later=round(later,1),advanced=later>result['time']+1.5,playing=xbmc.Player().isPlayingVideo())
        pb.stop();time.sleep(1.5);result['stopped']=not xbmc.Player().isPlaying()
    except sc.Outcome as outcome:result.update(outcome=outcome.kind,expected=case.get('expect')==outcome.kind)
    except Exception as error:result.update(error=type(error).__name__,detail=str(error)[:200])
    Path(output).write_text(json.dumps(result))


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--inside-kodi':inside(*sys.argv[2:4])
    else:sys.exit(run(sys.argv[1:]))
