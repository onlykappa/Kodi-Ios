#!/usr/bin/env python3
"""Desktop-rig check with Elementum and Burst disabled (Umbrella is not installed in the rig profile): does TMDb work, and what does the independent
search find and how fast, for five films? Needs a running rig (kodi_rig.py start). Evidence class: desktop Kodi rig plus live public sites at one moment.
Nothing is downloaded or played from the sites; screenshots and the report stay in KODI_RIG_HOME (never in Git)."""
import json,os,statistics,subprocess,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'migration/bundled-bootstrap/resources/lib'),str(ROOT/'scripts')]
RIG=Path(os.environ.get('KODI_RIG_HOME',Path.home()/'.cache/kodi-rig'))
FILMS=[('The Dark Knight',2008,155),('Parasite',2019,496243),('Spirited Away',2001,129),('Mad Max: Fury Road',2015,76341),('Big Buck Bunny',2008,10378)]
DISABLE=('plugin.video.elementum','script.elementum.burst','plugin.video.umbrella')
HELPER='plugin://plugin.video.themoviedb.helper/'

def rpc(method,params=None):
    import kodi_rig
    return kodi_rig.rpc(method,params)

def toggle(enabled):
    out={}
    for a in DISABLE:
        try:out[a]=rpc('Addons.SetAddonEnabled',{'addonid':a,'enabled':enabled}).get('result','?') if True else ''
        except Exception as e:out[a]='absent' if 'Invalid' in str(e) or 'not' in str(e).lower() else str(e)[:60]
    return out

def enabled_state():
    got=rpc('Addons.GetAddons',{'properties':['enabled'],'enabled':True}).get('result',{}).get('addons',[])
    ids={a['addonid'] for a in got};return {a:(a in ids) for a in DISABLE}

def directory(path):
    t0=time.perf_counter();r=rpc('Files.GetDirectory',{'directory':path,'media':'video','properties':['title','year']})
    items=(r.get('result') or {}).get('files') or []
    return {'seconds':round(time.perf_counter()-t0,2),'items':len(items),'sample':[i.get('label') for i in items[:3]],'error':(r.get('error') or {}).get('message')}

def run():
    import kodi_rig,source_match as sm,independent_sites as sites,source_contract as c,source_health as sh
    report={'disable':toggle(False),'enabled_now':enabled_state()}
    time.sleep(2)
    kodi_rig.rpc('GUI.ActivateWindow',{'window':'home'});time.sleep(6);kodi_rig.shot('tmdb-home-no-elementum')
    report['home_screenshot']='shots/tmdb-home-no-elementum.png'
    report['tmdb_helper_lists']={name:directory(HELPER+q) for name,q in (('popular movies','?info=popular&tmdb_type=movie'),('trending movies','?info=trending_day&tmdb_type=movie'),('top rated movies','?info=top_rated&tmdb_type=movie'))}
    key=sm.tmdb_key([str(RIG/'home/.kodi/addons/plugin.video.themoviedb.helper')]);report['tmdb_key_found_in_helper']=bool(key)
    films=[];health=sh.Health('')
    for title,year,tmdb in FILMS:
        row={'film':'%s (%d)'%(title,year)}
        t0=time.perf_counter();exp=sm.enrich(sm.expected('movie',[title],year,tmdb=str(tmdb)),key=key);row['tmdb_ms']=round((time.perf_counter()-t0)*1000)
        row.update(metadata=exp.get('metadata'),aliases=len(exp.get('titles',[])),years=exp.get('years'),another_film_has_title=exp.get('others'))
        req={'media_type':'movie','title':title,'year':year,'tmdb':str(tmdb),'expected':exp,'profile':{}}
        t1=time.perf_counter();out,found,rep=sites.search_all(req,health=health);row['search_s']=round(time.perf_counter()-t1,2)
        row.update(search_outcome=out,candidates=len(found),best=[{'name':i['name'][:70],'seeders':i['seeders'],'quality':i.get('quality'),'site':i.get('site')} for i in found[:2]],sites=rep)
        films.append(row)
    report['films']=films
    report['tmdb_second_pass_ms']=[round((lambda t:(sm.enrich(sm.expected('movie',[x[0]],x[1],tmdb=str(x[2])),key=key),time.perf_counter()-t)[1])(time.perf_counter())*1000) for x in FILMS]
    report['restore']=toggle(True);report['enabled_after_restore']=enabled_state()
    (RIG/'tmdb-films-report.json').write_text(json.dumps(report,indent=1))
    print(json.dumps(report,indent=1)[:6000])

if __name__=='__main__':run()
