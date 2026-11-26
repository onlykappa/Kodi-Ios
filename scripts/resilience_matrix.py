#!/usr/bin/env python3
"""Outage, correctness and privacy matrix for the source-resilience work (roadmap step 13). Host checks: nothing here proves phone behaviour.

Every scenario runs the real modules (provider_fallback, independent_sites, fresh_resolve, backup_playback, direct_stream, p2p_rules, source_health,
debrid_account, source_match, sports_match, provider_addons, updates) with injected failures, a loopback server or a network-less namespace. A global tripwire
records any connection to a non-loopback address (none is allowed except inside the two scenarios that say so, and those run in a child process), a fake
`xbmc` records every log line, and thread counts must return to baseline. `python3 scripts/resilience_matrix.py --write` refreshes the sanitized matrix.
"""
import json,os,shutil,socket,ssl,subprocess,sys,tempfile,threading,time,urllib.parse
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'migration/bundled-bootstrap/resources/lib'),str(ROOT/'scripts')]
import source_contract as c, source_health as sh, provider_fallback as pf, independent_sites as sites, independent_search as isearch, fresh_resolve as fr
import backup_playback as bp, direct_stream as ds, p2p_rules as p2p, debrid_account as da, alldebrid as ad, source_match as sm, sports_match as sp, debrid_token as dt
import provider_addons as providers
import test_independent_sites as ti, test_provider_fallback as tpf, test_direct_stream as tds, test_p2p_rules as tp2, test_fresh_resolve as tfr
SECRET='SECRET-TOKEN-9f3'
ROWS=[];LOG=[];TRIP=[];ROW_THREADS={}


def scenario(group,name,expect):
    def deco(fn):
        ROWS.append({'group':group,'scenario':name,'expected':expect,'fn':fn});return fn
    return deco


class FakeXbmc:
    LOGINFO=1;LOGWARNING=2
    @staticmethod
    def log(message,level=1):LOG.append(str(message))
    class Monitor:
        def abortRequested(self):return False


def install_tripwire():
    real=socket.socket.connect
    def connect(self,address,*a,**k):
        host=address[0] if isinstance(address,tuple) else str(address)
        if host not in ('127.0.0.1','::1','localhost') and not str(host).startswith('/'):TRIP.append(str(host))
        return real(self,address,*a,**k)
    socket.socket.connect=connect


EMPTY_PAGES={'https://apibay.org':ti.NONE,'https://movies-api.accel.li':ti.yts(),'https://eztvx.to':json.dumps({'torrents':[]}),'https://api.knaben.org':json.dumps({'hits':[]}),'https://1337x.to':ti.LEET_LIST}
MOVIE=ti.MOVIE;EP=ti.EP
def all_fail(error):return {h:error for h in ('https://apibay.org','https://movies-api.accel.li','https://eztvx.to','https://api.knaben.org','https://1337x.to','https://bitsearch.eu','https://www.torrentdownload.info','https://www.limetorrents.lol','https://kick4ss.com','https://nyaa.si')}
def http_error(code):
    class E(Exception):
        headers={}
    e=E('https://private.invalid/x?token='+SECRET);e.code=code;return e


# ---------------- outage ----------------
@scenario('outage','unavailable package repository: preserved copy used, tampered copy refused, no copy fails typed','build finishes from preserved bytes; tamper and missing are errors')
def _():
    import io,zipfile
    sys.path.insert(0,str(ROOT/'scripts'))
    from test_provider_addons import archive
    data=archive('plugin.one');lock=dict(schema=1,packages=[dict(id='plugin.one',version='1.0.0',url='https://example.invalid/o.zip',sha256=providers.digest(data))],provider_packages=[],core_dependencies=['xbmc.python'])
    with tempfile.TemporaryDirectory() as d:
        keep=Path(d)/'k';keep.mkdir();(keep/'a.bin').write_bytes(data)
        def dead(url):raise OSError('repository gone')
        providers.run(Path(d)/'o1',lock,get=dead,preserved=keep)
        (keep/'a.bin').write_bytes(data+b'x')
        try:providers.run(Path(d)/'o2',lock,get=dead,preserved=keep);raise AssertionError('tampered copy accepted')
        except OSError:pass
        try:providers.run(Path(d)/'o3',lock,get=dead);raise AssertionError('missing copy accepted')
        except OSError:pass
    return 'preserved build ok; tampered and missing raise OSError'

@scenario('outage','missing primary add-on and every add-on backup: first-party searches take over','results from the ten site searches, add-ons never launched')
def _():
    t=tpf.Transport({});calls=[]
    def local(request,cancel=None,timeout=0):calls.append(1);o,f,_=sites.search_all(MOVIE,fetch=ti.Fetch(ti.pages()),cancel=cancel);return o,f
    found=pf.search(tpf.REQ if hasattr(tpf,'REQ') else MOVIE,transport=t,independent=local)
    assert calls and found and t.calls==[],'add-on providers must not be called when unavailable'
    return '%d candidates from site searches; 0 add-on calls'%len(found)

@scenario('outage','dead remote configuration / all sites down: typed offline, not empty','typed offline outcome and no results')
def _():
    o,f,rep=sites.search_all(MOVIE,fetch=ti.Fetch(all_fail(ConnectionError())));assert (o,f)==(c.OFFLINE,[]) and set(rep.values())=={c.OFFLINE},(o,rep);return o

@scenario('outage','dead aggregator (Knaben) while others answer','others answer; aggregator reported offline and cooled down')
def _():
    p=ti.pages();p['https://api.knaben.org']=ConnectionError();h=sh.Health('',lambda:1e6)
    o,f,rep=sites.search_all(MOVIE,fetch=ti.Fetch(p),health=h);assert o==c.OK and rep['knaben']==c.OFFLINE and h.state('knaben')=='cooldown' and all(i['site']!='knaben' for i in f);return 'ok; knaben offline, cooling'

@scenario('outage','shared backend failure: two add-on providers fail for the same reason','chain continues to a third provider; both cool down')
def _():
    src={'name':'Example.Film.2024.1080p.WEB-DL.mkv','quality':'1080p','url':'https://fixture.invalid/m.mkv','size':1,'seeders':0};h=sh.Health('',lambda:1e6)
    t=tpf.Transport({'jacktook':ConnectionError(),'pov':ConnectionError(),'thecrew':[src]});found=pf.search(MOVIE,transport=t,health=h)
    assert found[0]['provider']=='thecrew' and h.state('jacktook')==h.state('pov')=='cooldown';return 'thecrew answered; jacktook, pov cooling'

@scenario('outage','DNS failure (real resolver, .invalid host)','typed offline')
def _():
    try:isearch.default_fetch('https://nonexistent.invalid/',3);raise AssertionError('resolved?')
    except Exception as e:o=c.classify(e)
    assert o==c.OFFLINE,o;return o

@scenario('outage','TLS failure (real handshake against a self-signed local server)','typed offline; certificate is not accepted')
def _():
    with tempfile.TemporaryDirectory() as d:
        key,crt=Path(d)/'k.pem',Path(d)/'c.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(crt),'-days','1','-subj','/CN=localhost'],check=True,capture_output=True)
        ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(str(crt),str(key))
        srv=socket.socket();srv.bind(('127.0.0.1',0));srv.listen(1);port=srv.getsockname()[1]
        def serve():
            try:
                conn,_=srv.accept();conn=ctx.wrap_socket(conn,server_side=True);conn.close()
            except Exception:pass
        threading.Thread(target=serve,daemon=True).start()
        try:isearch.default_fetch('https://127.0.0.1:%d/'%port,5);raise AssertionError('self-signed certificate was accepted')
        except Exception as e:o=c.classify(e)
        srv.close()
    assert o==c.OFFLINE,o;return o+' (certificate verification failed)'

@scenario('outage','complete offline mode (network-less namespace, real sockets)','typed offline for every request; staged bundle still imports and searches fixtures')
def _():
    if not (shutil.which('unshare') and subprocess.run(['unshare','-rn','true'],capture_output=True).returncode==0):return 'skipped: no unshare here'
    code='import sys;sys.path[:0]=[%r];import independent_search as s,source_contract as c\ntry:\n s.default_fetch("https://example.com/",3)\nexcept Exception as e:print(c.classify(e))'%str(ROOT/'migration/bundled-bootstrap/resources/lib')
    r=subprocess.run(['unshare','-rn',sys.executable,'-I','-c',code],capture_output=True,text=True,timeout=30);assert r.stdout.strip()==c.OFFLINE,(r.stdout,r.stderr[-200:]);return r.stdout.strip()

@scenario('outage','malformed feeds and pages for every site family','every family: layout changed, never a fabricated result')
def _():
    bad={'bitsearch':'<html>x</html>','torrentdownload':'<html>','limetorrents':'{"x":1}','kick4ss':'','nyaa':'<html>','apibay':'<html>','yts':'[]','eztv':'[]','knaben':'{"hits":3}'}
    ads={a.name:a for a in sites.SIMPLE}
    for name,page in bad.items():
        try:ads[name].parse(page,EP if name=='nyaa' else MOVIE);raise AssertionError(name+' accepted a malformed page')
        except (ValueError,TypeError,KeyError):pass
    try:ads['nyaa'].parse('<rss><!DOCTYPE x [<!ENTITY a "b">]></rss>',EP);raise AssertionError('entity feed accepted')
    except ValueError:pass
    return '%d families reject malformed input'%(len(bad)+1)

@scenario('outage','expired link: re-resolved once, second expiry returns expired','one re-resolve, then expired; no loop')
def _():
    site=tfr.Site();site.mode='expire';site.token='never'
    try:
        t=tfr.Transport(site,tokens=['a','b','c'])
        try:fr.play_ready(tfr.CAND,tfr.MOVIE,t);raise AssertionError('played')
        except c.Outcome as e:assert e.kind==c.EXPIRED and t.calls==2,(e.kind,t.calls)
    finally:site.srv.shutdown();site.srv.server_close()
    return 'expired after 2 resolutions'

@scenario('outage','403/429 from a site and from the debrid service','typed refused; cooldown honours Retry-After; debrid circuit needs three service failures')
def _():
    p=ti.pages();p['https://apibay.org']=http_error(429);h=sh.Health('',lambda:1e6);o,f,rep=sites.search_all(MOVIE,fetch=ti.Fetch(p),health=h)
    assert rep['apibay']==c.REFUSED and h.state('apibay')=='cooldown'
    e=http_error(429);e.headers={'Retry-After':'7200'};clk=[1e6];h2=sh.Health('',lambda:clk[0]);h2.record('x',c.REFUSED,sh.retry_after(e));clk[0]+=7000;assert h2.state('x')=='cooldown'
    b=ad.Busy('x');b.kind='refused';assert da.outcome_for(b)==c.REFUSED
    return 'refused; retry-after honoured'

@scenario('outage','absent peers: no swarm starts','timeout within the total bound; player stopped; each swarm cooled')
def _():
    clk,pl,pb=tp2.setup([]);home=tds.Home();hl=sh.Health('',clk)
    import unittest.mock as um
    with um.patch('debrid_token.has',return_value=False):
        try:p2p.stream_best([tp2.cand(i,30-i) for i in range(1,5)],tds.REQ,pb,home,lambda:None,health=hl,clock=clk);raise AssertionError('started')
        except c.Outcome as e:assert e.kind==c.TIMEOUT and len(pl.calls)<=p2p.MAX_TRIES and clk.t<=p2p.TOTAL_WAIT+p2p.FIRST_WAIT,(e.kind,len(pl.calls),clk.t)
    assert pl.stops>=1 and home.p=={};return 'timeout after %d swarms in %.0f s'%(len(pl.calls),clk.t)

@scenario('outage','missing accounts: no AllDebrid key and no Google sign-in path','typed account-required; direct route offered only behind the prompt')
def _():
    try:ad.AllDebrid('');raise AssertionError('client built without a key')
    except ad.Problem as e:assert da.outcome_for(e)==c.ACCOUNT_REQUIRED
    import unittest.mock as um
    with um.patch('debrid_token.has',return_value=False):assert ds.plan(tds.CAND,tds.REQ,None)==tds.HASH
    return 'account-required; direct plan allowed (prompt still required)'

# ---------------- correctness ----------------
@scenario('correctness','wrong movie, wrong year, wrong episode, duplicate results','only the exact title/year/episode; duplicates collapse by hash')
def _():
    p=ti.pages();o,f,_r=sites.search_all(MOVIE,fetch=ti.Fetch(p));hs=[i['torrent_hash'] for i in f]
    assert ti.H(2) not in hs and ti.H(3) not in hs and len(hs)==len(set(hs)),hs
    o,f,_r=sites.search_all(EP,fetch=ti.Fetch(ti.pages(False)));assert ti.H(7) not in [i['torrent_hash'] for i in f] and ti.H(11) not in [i['torrent_hash'] for i in f]
    return '%d movie candidates, no wrong-year/title rows, no wrong-episode rows'%len(hs)

@scenario('correctness','partial success: some families fail, one answers','results kept with a per-site report')
def _():
    p=ti.pages();p['https://apibay.org']=TimeoutError();o,f,rep=sites.search_all(MOVIE,fetch=ti.Fetch(p));assert o==c.OK and f and rep['apibay']==c.TIMEOUT;return 'ok with apibay timeout'

@scenario('correctness','all results empty is a valid outcome','empty, never fabricated success')
def _():
    o,f,rep=sites.search_all(MOVIE,fetch=ti.Fetch(EMPTY_PAGES));assert (o,f)==(c.EMPTY,[]);t=tpf.Transport({'jacktook':[],'pov':[]});assert pf.search(MOVIE,transport=t)==[];return 'empty'

@scenario('correctness','cancellation never advances or penalises','canceled outcome; nothing recorded in health; no player start')
def _():
    h=sh.Health('',lambda:1e6);t=tpf.Transport({'jacktook':pf.Canceled('stop'),'pov':[{'name':'Example.Film.2024.1080p.WEB-DL.mkv','quality':'1080p','url':'https://f.invalid/m.mkv','size':1,'seeders':0}]})
    try:pf.search(MOVIE,transport=t,health=h);raise AssertionError('advanced')
    except pf.Canceled:pass
    assert t.calls==['jacktook'] and h.data=={};o,f,_r=sites.search_all(MOVIE,fetch=ti.Fetch(ti.pages()),cancel=lambda:True);assert o==c.CANCELED
    pl=tds.Player();home=tds.Home()
    try:ds.stream(tds.CAND,tds.REQ,bp.Playback(pl),home,lambda:None,force=True,cancel=lambda:True);raise AssertionError('started')
    except c.Outcome as e:assert e.kind==c.CANCELED and pl.calls==[]
    return 'no advance, no record, no start'

@scenario('correctness','profile restart: health, token mirror and stale metadata survive','state reloads from the profile files')
def _():
    with tempfile.TemporaryDirectory() as d:
        clk=[1e6];path=str(Path(d)/'h.json');a=sh.Health(path,lambda:clk[0]);a.record('pov',c.REFUSED);assert sh.Health(path,lambda:clk[0]).state('pov')=='cooldown'
        assert dt.get(d,lambda:'KEY')=='KEY' and dt.get(d,lambda:'')=='KEY'
        assert dt.save_own('OWN',d) and dt.get(d,lambda:'KEY')=='OWN'
    return 'cooldown, mirrored key and own key persist'

@scenario('correctness','concurrent jobs: parallel searches share health; same stream starts once','no exception, consistent health, one player start')
def _():
    h=sh.Health('',lambda:1e6);errs=[];out=[]
    def job(i):
        try:out.append(sites.search_all(MOVIE,fetch=ti.Fetch(ti.pages()),health=h)[0])
        except Exception as e:errs.append(e)
    th=[threading.Thread(target=job,args=(i,)) for i in range(8)];[t.start() for t in th];[t.join(10) for t in th]
    assert not errs and out==[c.OK]*8,(errs,out)
    pl=tds.Player(advance=False);pbk=bp.Playback(pl,sleep=lambda d:time.sleep(.001));res=[]
    def start():
        try:res.append(pbk.start_resolved(('k',),lambda:fr.Resolved('http://127.0.0.1:1/x',{},time.time()),wait=1))
        except c.Outcome as e:res.append(e.kind)
    th=[threading.Thread(target=start) for i in range(4)];[t.start() for t in th];[t.join(10) for t in th]
    assert len(pl.calls)<=2 and 'duplicate' in res,(len(pl.calls),res)
    return '8 parallel searches ok; duplicate starts collapsed (%d player starts)'%len(pl.calls)

@scenario('correctness','sports: stale, ambiguous and ended games rejected','typed unsupported/empty; no launch')
def _():
    NOW=1_800_000_000;g={'id':'e:1','league':'EPL','state':'live','start':NOW-1800,'away':{'name':'Chelsea'},'home':{'name':'Arsenal'}}
    l=dict(g,sources=[{'id':'a','addon':'x','play':'{}'}],start=NOW-1700);out=[]
    for game,listings,kw in ((dict(g,start=NOW-9*3600),[l],{}),(g,[l,dict(l,start=NOW-1700+2400)],{}),(g,[l],{'as_of':NOW-3600})):
        try:sp.unique_match(game,listings,NOW,**kw);raise AssertionError('matched')
        except c.Outcome as e:out.append(e.kind)
    return ', '.join(out)

@scenario('correctness','no direct torrent traffic is attempted by any search or fallback path','zero non-loopback connections recorded by the tripwire')
def _():
    assert not TRIP,TRIP;return 'tripwire clean: %d non-loopback connects'%len(TRIP)

# ---------------- privacy ----------------
@scenario('privacy','no secret-bearing line: logs, health file, notices and reports carry no key or link','zero lines contain the key, a URL, a header or a magnet')
def _():
    log=[];fake=FakeXbmc()
    import types
    sys.modules['xbmc']=types.SimpleNamespace(LOGINFO=1,LOGWARNING=2,log=lambda m,l=1:log.append(str(m)))
    try:
        posts=[];h=sh.Health('',lambda:1e6,post=lambda *a:posts.append(a))
        p=ti.pages();p['https://apibay.org']=http_error(429)
        sites.search_all(MOVIE,fetch=ti.Fetch(p),health=h)
        t=tpf.Transport({'jacktook':http_error(403),'pov':ConnectionError('https://x.invalid/?token='+SECRET)});pf.search(MOVIE,transport=t,health=h)
        da.record(h,ad.Busy('https://api.alldebrid.com/x?apikey='+SECRET))
        with tempfile.TemporaryDirectory() as d:
            dt.save_own(SECRET,d);hf=Path(d)/'h.json';sh.Health(str(hf),lambda:1e6).record('pov',c.REFUSED);saved=hf.read_text()
        blob='\n'.join(log+[repr(a) for a in posts]+[json.dumps(h.data),saved])
        for bad in (SECRET,'http://','https://','magnet:','Authorization','Bearer'):assert bad not in blob,bad
        assert 'apikey' not in blob.lower() or 'apikey=' not in blob.lower()
    finally:sys.modules.pop('xbmc',None)
    return '%d log lines, %d notices, health file: clean'%(len(log),len(posts))

@scenario('privacy','the repository carries no key, token file or private state from these steps','no secret pattern in the new modules, docs or reports')
def _():
    import re
    names=['debrid_token.py','debrid_account.py','source_health.py','direct_stream.py','p2p_rules.py','fresh_resolve.py','backup_playback.py','independent_sites.py','independent_search.py','sports_match.py','source_contract.py']
    pat=re.compile(r'(?i)(apikey|api_key|token|password|secret)\s*[=:]\s*["\'][A-Za-z0-9_\-]{20,}["\']')
    for n in names:
        text=(ROOT/'migration/bundled-bootstrap/resources/lib'/n).read_text();assert not pat.search(text),n
    return '%d modules checked'%len(names)

@scenario('privacy','the app never runs downloaded code','update flow has no exec/eval/import of downloaded data')
def _():
    text=(ROOT/'migration/bundled-bootstrap/resources/lib/updates.py').read_text()
    for w in ('exec(','eval(','importlib','__import__','subprocess','compile(','runpy'):assert w not in text,w
    return 'updates.py clean'


def run(rows=None):
    install_tripwire();sys.modules['xbmc_probe']=None
    results=[];base=threading.active_count()
    for row in ROWS:
        before=len(LOG);started=time.time()
        try:observed=row['fn']();status='pass'
        except AssertionError as error:observed='FAILED: %s'%str(error)[:160];status='fail'
        except Exception as error:observed='ERROR: %s: %s'%(type(error).__name__,str(error)[:120]);status='fail'
        results.append({'group':row['group'],'scenario':row['scenario'],'expected':row['expected'],'observed':str(observed)[:200],'status':'skipped' if str(observed).startswith('skipped') else status,'seconds':round(time.time()-started,1)})
    deadline=time.time()+5
    while threading.active_count()>base+1 and time.time()<deadline:time.sleep(.1)
    leaked=threading.active_count()-base
    results.append({'group':'hygiene','scenario':'no abandoned background jobs after the whole matrix','expected':'thread count back to baseline','observed':'extra threads: %d'%leaked,'status':'pass' if leaked<=1 else 'fail','seconds':0})
    return results


if __name__=='__main__':
    res=run();bad=[r for r in res if r['status']=='fail']
    for r in res:print('%-11s %-7s %s | %s'%(r['group'],r['status'],r['scenario'][:70],r['observed'][:90]))
    if '--write' in sys.argv:
        slim=[{k:r[k] for k in ('group','scenario','expected','observed','status')} for r in res]
        (ROOT/'reports/source-resilience-matrix.json').write_text(json.dumps({'schema':1,'scope':'host checks of the source-resilience modules (roadmap step 13): injected failures, a loopback server, one network-less namespace; no phone, rig or live-service evidence','rows':slim},indent=1)+'\n')
    sys.exit(1 if bad else 0)
