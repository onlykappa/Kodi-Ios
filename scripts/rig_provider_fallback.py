#!/usr/bin/env python3
"""Deterministic provider fallback checks inside real Kodi 21.3, with local upstream-interface fixtures.

Run after kodi_rig.py setup/start. Uses real Kodi, genuine installed add-on imports, production adapters, worker
guards and private RunScript mailboxes. Fixture search/resolve replies replace upstream network/account results.
This is desktop Kodi rig evidence, not live-provider or iPhone playback verification. Reports/screenshots stay private.
"""
import importlib,importlib.util,json,os,re,shutil,sys,threading,time,traceback,unittest
from pathlib import Path
sys.dont_write_bytecode=True
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'migration/bundled-bootstrap/resources/lib'
RIG=Path(os.environ.get('KODI_RIG_HOME',Path.home()/'.cache/kodi-rig'))
TITLE='Provider Rig Show'
NAME='Provider.Rig.Show.S01E02.1080p.WEB-DL.H264.mkv'
LINK='https://media.example.invalid/fixture.mkv'
HASH='1234567890abcdef1234567890abcdef12345678'
PROVIDERS=('jacktook','pov','prism','thecrew','otaku')


def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value));os.replace(temp,path)


def fixture_modules(context,scenario,events):
    """Import pinned installed upstream modules first; replace only their search/resolve interface replies."""
    original=importlib.import_module;provider=context.provider
    def rows():
        context.check();events.append({'provider':provider,'operation':'search'})
        if scenario=='chain' and provider=='jacktook':raise ConnectionError('Fixture provider offline')
        if scenario=='chain' and provider=='pov':return []
        if scenario=='empty':return []
        if scenario=='slow':
            while True:context.check();time.sleep(.02)
        names=[NAME]
        if scenario=='strict':names=['Other.Show.S01E02.1080p.mkv','Provider.Rig.Show.S01E03.1080p.mkv',
                                    'Provider.Rig.Show.S01E02.720p.mkv',NAME]
        return [{'name':name,'quality':'720p' if '720p' in name else '1080p','url':LINK,'hash':HASH,
                 'seeders':20,'size':2,'direct':True} for name in names]
    def resolved(*args,**kwargs):
        context.check();events.append({'provider':provider,'operation':'resolve'});return LINK
    def load(name):
        try:module=original(name)
        except Exception as error:
            events.append({'import_error':name,'detail':repr(error)});raise
        events.append({'provider':provider,'import':name})
        if provider=='jacktook' and name=='lib.search':
            module.cache=SimpleNamespace(get=lambda key:'configured')
            module.search_client=lambda *a,**k:[dict(row,title=row['name'],size=2*1024**3,addonName='Fixture') for row in rows()]
            module.pre_process_results=lambda found,*a,**k:found
        elif provider=='jacktook' and name=='lib.clients.stremio.playback':
            module.payload_from_torrent=lambda value:value;module.candidate_from_payload=lambda value:value;module.resolve=resolved
        elif provider=='pov' and name=='pov':
            class Source:
                hasMovies=True;hasEpisodes=True
                def sources(self,*a,**k):return rows()
            module.sources=lambda:[('fixture',Source)]
        elif provider=='thecrew' and name=='resources.lib.modules.sources':
            class Sources:
                def getSources(self,*a,**kwargs):
                    if kwargs.get('show_dialog') is not False or kwargs.get('use_overlay') is not False:
                        raise AssertionError('Crew opened a discovery dialog')
                    return [dict(row,release_title=row['name']) for row in rows()]
                def sourcesResolve(self,*a,**k):return resolved()
            module.Sources=Sources
        elif provider=='prism' and name=='resources.lib.modules.providers':
            class Packages:
                def update_known_packages(self):pass
                def update_known_providers(self):pass
            module.CustomProviders=Packages
        elif provider=='prism' and name=='resources.lib.modules.getSources':
            class Sources:
                def __init__(self,*a):self.window=SimpleNamespace(silent=True)
                def get_sources(self):
                    return [],[dict(row,release_title=row['name'],type='torrent',size=2048) for row in rows()],{}
                def _send_provider_stop_event(self):pass
            module.Sources=Sources
        elif provider=='prism' and name=='resources.lib.modules.resolver':
            class Resolver:
                def resolve_single_source(self,*a,**k):return resolved(),{}
            module.Resolver=Resolver
        elif provider=='otaku' and name=='resources.lib.ui.database':
            module.get_mappings=lambda *a:{'themoviedb_id':'12345','mal_id':'1'}
        elif provider=='otaku' and name=='resources.lib.ui.control':
            module.getBool=lambda key:key=='provider.torrentio'
        elif provider=='otaku' and name=='resources.lib.pages.torrentio':
            class Sources:
                def get_sources(self,*a,**k):
                    return {'cached':[dict(row,release_title=row['name'],type='torrent',cached=True,
                        byte_size=2*1024**3,debrid_provider='Alldebrid') for row in rows()]}
            module.Sources=Sources
        elif provider=='otaku' and name=='resources.lib.debrid.all_debrid':
            class Debrid:
                def resolve_single_magnet(self,*a,**k):return resolved()
            module.AllDebrid=Debrid
        return module
    return load


def fixture_worker(job,scenario,events_path):
    import xbmc,xbmcgui,xbmcaddon,xbmcvfs
    sys.path.insert(0,os.path.join(xbmcaddon.Addon('service.kodi.ios.bootstrap').getAddonInfo('path'),'resources/lib'))
    import provider_fallback_worker as worker
    profile=xbmcvfs.translatePath('special://profile/')
    folder=Path(profile)/'addon_data/service.kodi.ios.bootstrap/provider-fallback-jobs'/job
    global LINK,NAME
    body=json.loads((folder/'request.json').read_text()).get('request',{})
    LINK=body.get('_rig_url',LINK)
    if body.get('_rig_mapped'):NAME='Mapped.Anime.-.014.1080p.WEB-DL.H264.mkv'
    original=worker.Context;events=[]
    def context(*args,**kwargs):
        value=original(*args,**kwargs);value.import_module=fixture_modules(value,scenario,events);return value
    worker.Context=context
    adapter=importlib.import_module('provider_adapters.'+json.loads((folder/'request.json').read_text())['provider'])
    for method in ('search','resolve'):
        real=getattr(adapter,method)
        def wrapped(*args,_real=real,_method=method,**kwargs):
            try:return _real(*args,**kwargs)
            except Exception as error:
                events.append({'adapter_error':_method,'detail':repr(error),'trace':traceback.format_exc(limit=5)});raise
        setattr(adapter,method,wrapped)
    try:worker.run(folder,profile,xbmc,xbmcgui,xbmcaddon)
    except Exception as error:events.append({'worker_error':type(error).__name__,'detail':str(error)[:350]})
    finally:write(events_path,events)


def inside(case,output):
    import xbmc,xbmcgui,xbmcaddon,xbmcvfs
    sys.path.insert(0,os.path.join(xbmcaddon.Addon('service.kodi.ios.bootstrap').getAddonInfo('path'),'resources/lib'))
    import provider_fallback as fallback,provider_fallback_worker as worker,source_match
    output=Path(output);events_dir=output.parent/'events';events_dir.mkdir(exist_ok=True)
    global LINK
    import http.server
    class Media(http.server.BaseHTTPRequestHandler):
        def log_message(self,*a):pass
        def do_HEAD(self):
            self.send_response(404 if self.path=='/offline' else 200);self.send_header('Content-Length','100');self.end_headers()
        def do_GET(self):
            if self.path=='/offline':self.send_error(404);return
            self.send_response(206);self.send_header('Content-Range','bytes 0-0/100');self.send_header('Content-Length','1');self.end_headers();self.wfile.write(b'x')
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Media);server.daemon_threads=True
    threading.Thread(target=server.serve_forever,daemon=True).start()
    LINK='http://127.0.0.1:%d/media.mkv'%server.server_port
    launched=[];available='otaku' if case=='mapped-auto' else case.split(':')[-1] if case.startswith('adapter:') else None
    original_transport=fallback.KodiTransport
    class Transport(original_transport):
        def __init__(self):super().__init__(launch=self.launch_worker)
        def call(self,provider,operation,request,candidate,deadline,cancel):
            link=LINK.replace('/media.mkv','/offline') if case=='resolver-offline' and provider=='jacktook' else LINK
            return super().call(provider,operation,dict(request,_rig_url=link,_rig_mapped=case=='mapped-auto'),candidate,deadline,cancel)
        def available(self,provider):
            return (available is None or provider==available) and super().available(provider)
        def launch_worker(self,command):
            ident=re.search(r',([0-9a-f]{32})\)$',command).group(1)
            eventfile=events_dir/(ident+'.json');launched.append(eventfile)
            scenario='strict' if case=='strict' else 'chain' if case=='chain' else 'slow' if case in ('timeout','cancel') else 'empty' if case=='empty' else 'valid'
            xbmc.executebuiltin('RunScript(%s,--fixture-worker,%s,%s,%s)'%(__file__,ident,scenario,eventfile))
    request={'media_type':'episode','title':TITLE,'show_title':TITLE,'year':2020,'season':1,'episode':2,
        'imdb':'tt1234567','tmdb':'12345','quality':'1080p','profile':{'quality':'1080p','strict_quality':True}}
    if available=='otaku':
        request.update(anime=True,anime_mapping={'verified':True,'mal_id':1,'absolute_episode':2,'tmdb':'12345','season':1,'episode':2})
    began=time.monotonic();report={'case':case,'status':'running','evidence_class':'desktop Kodi rig','live_provider_results':False,'python_version':sys.version.split()[0]}
    write(output,report)
    try:
        if case in ('auto-primary','auto-queue','mapped-auto'):
            import umbrella_picker,debrid_drive
            fallback.KodiTransport=Transport
            real_addon=xbmcaddon.Addon;xbmcaddon.Addon=lambda ident=None:real_addon(ident or 'service.kodi.ios.bootstrap')
            deck=umbrella_picker.load(path=str(ROOT/'migration/deck-picker/deck_picker.py'),addon_path=real_addon('service.kodi.ios.bootstrap').getAddonInfo('path'))
            exp=source_match.expected('episode',[TITLE],season=1,episode=2,tmdb='12345')
            if case=='mapped-auto':
                exp.update(season=2,episode=2,anime=True,anime_mapping={'verified':True,'source':'otaku-db+tmdb-episode+ani.zip','title':'Mapped Anime','mal_id':1,'absolute_episode':14,'anime_season':1,'tmdb':'12345','season':2,'episode':2})
            home=xbmcgui.Window(10000);ident='rig-auto';auto={'request_id':ident,'until':time.time()+60,'target':{'tmdb':'12345','season':1,'episode':2},'purpose':'queue','profile':{'quality':'1080p','strict_quality':True}}
            if case=='mapped-auto':auto['target'].update(season=2,episode=2)
            profile=xbmcvfs.translatePath('special://profile/');queue=debrid_drive.location(profile);before=queue.read_bytes() if queue.exists() else None
            home.setProperty('KodiIOS.AutoPick',json.dumps(auto));home.clearProperty('KodiIOS.AutoPick.Queued')
            try:
                labels=[] if case in ('auto-queue','mapped-auto') else ['1080p (20/0) [2.00 GB] WEB-DL H264 - Primary\n'+NAME]
                result=deck.run(TITLE,labels,expect=exp,mode='download')
                if case=='auto-primary':assert result==0 and not launched,(result,launched)
                else:
                    receipt=json.loads(home.getProperty('KodiIOS.AutoPick.Queued') or '{}')
                    assert receipt.get('request_id')==ident and receipt.get('queued') is True,receipt
                    assert any(job.get('title')==TITLE and job.get('status')=='copying' for job in debrid_drive.load(profile)['jobs'])
                    report['queued_receipt']=True
            finally:
                home.clearProperty('KodiIOS.AutoPick');home.clearProperty('KodiIOS.AutoPick.Queued')
                if before is None:queue.unlink(missing_ok=True)
                else:queue.write_bytes(before)
        elif case=='resolver-offline':
            import provider_fallback_hooks as hooks,umbrella_picker
            fallback.KodiTransport=Transport
            real_addon=xbmcaddon.Addon;xbmcaddon.Addon=lambda ident=None:real_addon(ident or 'service.kodi.ios.bootstrap')
            deck=umbrella_picker.load(path=str(ROOT/'migration/deck-picker/deck_picker.py'),addon_path=real_addon('service.kodi.ios.bootstrap').getAddonInfo('path'))
            exp=source_match.expected('episode',[TITLE],season=1,episode=2,tmdb='12345')
            ident='rig-offline';auto={'request_id':ident,'until':time.time()+60,'target':{'tmdb':'12345','season':1,'episode':2},'purpose':'queue','profile':{'quality':'1080p','strict_quality':True}}
            home=xbmcgui.Window(10000);home.setProperty('KodiIOS.AutoPick',json.dumps(auto))
            try:selected=hooks._resolved(deck,exp,TITLE,'download',auto=auto,timeout=20)
            finally:home.clearProperty('KodiIOS.AutoPick')
            assert selected and selected['candidate']['provider']=='pov',selected
            report.update(provider='pov',offline_origin='jacktook')
        elif case in ('primary-picker','fallback-picker','cancel-picker'):
            import umbrella_picker
            common=xbmcvfs.translatePath(xbmcaddon.Addon('script.module.kodi-six').getAddonInfo('path'))
            sys.path.insert(0,os.path.join(common,'lib'));import kodi_six
            real_addon=xbmcaddon.Addon
            xbmcaddon.Addon=lambda ident=None:real_addon(ident or 'service.kodi.ios.bootstrap')
            deck=umbrella_picker.load(path=str(ROOT/'migration/deck-picker/deck_picker.py'),
                addon_path=xbmcvfs.translatePath(xbmcaddon.Addon('service.kodi.ios.bootstrap').getAddonInfo('path')))
            exp=source_match.expected('episode',[TITLE],season=1,episode=2,imdb='tt1234567',tmdb='12345')
            labels=['1080p (20/0) [2.00 GB] WEB-DL H264 - Primary\n'+NAME]
            fallback.KodiTransport=Transport
            if case=='fallback-picker':
                found=fallback.search(request,primary='elementum',timeout=15)
                if not found:raise AssertionError('No fixture fallback sources')
                labels=fallback.picker_items(found)
            report.update(stage='picker');write(output,report)
            choice=deck.run(TITLE,labels,expect=exp,mode='stream')
            if case=='cancel-picker':assert choice==-1,choice
            else:assert choice==0,choice
            if case=='primary-picker':assert not launched,'Primary success queried backups'
            report['choice']=choice
        else:
            transport=Transport();cancel_at=began+.25
            if case=='cancel':
                try:fallback.search(request,primary='elementum',transport=transport,cancel=lambda:time.monotonic()>=cancel_at,timeout=5)
                except fallback.Canceled:pass
                else:raise AssertionError('Cancellation was ignored')
            elif case=='timeout':
                try:fallback.search(request,primary='elementum',transport=transport,timeout=.3)
                except TimeoutError:pass
                else:raise AssertionError('Total deadline was ignored')
            else:
                found=fallback.search(request,primary='elementum',transport=transport,timeout=20)
                if case=='empty':assert not found,found
                else:
                    if not found:raise AssertionError('No verified fixture source')
                    assert all(row['name']==NAME and row['quality']=='1080p' for row in found),found
                    if case=='chain':assert found[0]['provider']=='prism',found
                    if available:assert found[0]['provider']==available,found
                    resolved=fallback.resolve(found[0],request,transport=transport,timeout=15)
                    assert resolved==LINK,resolved
                    report.update(provider=found[0]['provider'],count=len(found),resolved=True)
        report['status']='pass'
    except Exception as error:
        report.update(status='fail',error=type(error).__name__,detail=str(error)[:500],traceback=traceback.format_exc(limit=9))
    finally:
        fallback.KodiTransport=original_transport
        server.shutdown();server.server_close()
        report['seconds']=round(time.monotonic()-began,3)
        report['events']=[event for path in launched if path.exists() for event in json.loads(path.read_text())]
        report['mailboxes_left']=len(list((Path(xbmcvfs.translatePath('special://profile/'))/'addon_data/service.kodi.ios.bootstrap/provider-fallback-jobs').glob('*')))
        write(output,report)


def host():
    import argparse,subprocess
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('cases',nargs='*');parser.add_argument('--staged-addons',type=Path,default=Path('/workspace/scratch/provider-fallback/test-stage/addons'))
    args=parser.parse_args()
    spec=importlib.util.spec_from_file_location('kodi_rig',ROOT/'scripts/kodi_rig.py');rig=importlib.util.module_from_spec(spec);spec.loader.exec_module(rig)
    version=rig.rpc('Application.GetProperties',{'properties':['version']})['result']['version']
    if (version['major'],version['minor'])!=(21,3):raise SystemExit('Requires actual Kodi 21.3')
    rig.sync(None)
    boot=rig.HOME/'.kodi/addons/service.kodi.ios.bootstrap'
    shutil.copy2(ROOT/'migration/deck-picker/deck_picker.py',boot/'resources/lib/deck_picker.py')
    staged=args.staged_addons
    for source in staged.iterdir():
        dest=rig.HOME/'.kodi/addons'/source.name
        if not dest.exists():shutil.copytree(source,dest)
    providers=staged.parent/'bootstrap/provider-fallback'
    if providers.exists():shutil.copytree(providers,boot/'provider-fallback',dirs_exist_ok=True)
    rig.run_builtins('Dialog.Close(all,true)','UpdateLocalAddons')
    for source in staged.iterdir():
        try:rig.rpc('Addons.SetAddonEnabled',{'addonid':source.name,'enabled':True})
        except Exception:pass
    output=rig.RIG/'provider-fallback';output.mkdir(exist_ok=True)
    cases=args.cases or ['adapter:'+name for name in PROVIDERS]+['strict','chain','empty','timeout','cancel','auto-primary','auto-queue','mapped-auto','resolver-offline','primary-picker','fallback-picker','cancel-picker']
    reports=[]
    for case in cases:
        result=output/(case.replace(':','-')+'.json');result.unlink(missing_ok=True)
        rig.run_builtins('Dialog.Close(all,true)','RunScript(%s,--inside-kodi,%s,%s)'%(__file__,case,result))
        deadline=time.monotonic()+90;clicked_at=0;screenshot=False
        while time.monotonic()<deadline:
            report=json.loads(result.read_text()) if result.exists() else {}
            if report.get('status') in ('pass','fail'):break
            if report.get('stage')=='picker' and time.monotonic()-clicked_at>1:
                if not screenshot:
                    try:rig.shot('provider-'+case);screenshot=True
                    except Exception:pass
                rig.rpc('Input.Back' if case=='cancel-picker' else 'Input.Select');clicked_at=time.monotonic()
            time.sleep(.1)
        else:report={'case':case,'status':'fail','error':'Rig timeout'}
        reports.append(report);print(case,report['status'],report.get('detail',''),flush=True)
    summary={'evidence_class':'desktop Kodi rig','version':version,'live_provider_results':False,'cases':reports,
             'passed':sum(r['status']=='pass' for r in reports),'total':len(reports)}
    write(output/'report.json',summary)
    print(json.dumps({'passed':summary['passed'],'total':len(reports),'report':str(output/'report.json')}),flush=True)
    raise SystemExit(0 if summary['passed']==len(reports) else 1)


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--fixture-worker':fixture_worker(*sys.argv[2:])
    elif len(sys.argv)>1 and sys.argv[1]=='--inside-kodi':inside(*sys.argv[2:])
    else:host()
