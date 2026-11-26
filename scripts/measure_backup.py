#!/usr/bin/env python3
"""Before/after timing of the fallback chain on identical controlled fixtures (roadmap step 14). Host measurement, not the phone.

`python3 scripts/measure_backup.py --lib <resources/lib>` prints JSON for one checkout; `--compare MAIN_LIB BRANCH_LIB` runs both in child processes and
prints the table. Fixtures: five add-on providers with a fixed latency, and (branch only) ten site searches with a fixed latency per request. Times are wall
clock medians of 5 runs, request counts are calls made, memory is the peak resident size of the process.
"""
import json,os,resource,statistics,subprocess,sys,time
sys.dont_write_bytecode=True
LATENCY=.05;SITE_LATENCY=.15
REQ={'media_type':'movie','title':'Example Film','year':2024,'quality':'1080p','profile':{}}
SRC={'name':'Example.Film.2024.1080p.WEB-DL.mkv','quality':'1080p','url':'https://fixture.invalid/m.mkv','size':1,'seeders':0}

class Transport:
    def __init__(self,answers):self.answers=answers;self.calls=0
    def available(self,p):return p in self.answers
    def search(self,p,r,d,c):
        self.calls+=1;time.sleep(LATENCY);a=self.answers[p]
        if isinstance(a,Exception):raise a
        return a
    def resolve(self,p,cand,r,d,cancel):return cand.get('url')

def timed(fn,n=5):
    runs=[];calls=0
    for _ in range(n):
        t0=time.perf_counter();calls=fn();runs.append(time.perf_counter()-t0)
    return {'median_ms':round(statistics.median(runs)*1000),'requests':calls}

def child(lib):
    sys.path.insert(0,lib);import provider_fallback as pf
    out={}
    def chain(answers,**kw):
        def run():
            t=Transport(answers);pf.search(REQ,transport=t,**kw);return t.calls
        return run
    out['healthy primary (no backup runs)']={'median_ms':0,'requests':0}
    out['first backup answers']=timed(chain({'jacktook':[SRC]}))
    out['three backups fail, fourth answers']=timed(chain({'jacktook':ConnectionError(),'pov':TimeoutError(),'otaku':ConnectionError(),'thecrew':[SRC]}))
    out['every add-on backup empty']=timed(chain({'jacktook':[],'pov':[],'thecrew':[],'prism':[]}))
    try:
        import independent_sites as s,fixtures_independent_sites as fx
    except ImportError:s=None
    if s is not None:
        def sites_run():
            n=[0]
            def fetch(url,timeout):
                n[0]+=1;time.sleep(SITE_LATENCY);return fx.PAGES.get(url.split('/')[2],'')
            s.search_all(REQ,fetch=fetch);return n[0]
        out['ten site searches in parallel (branch only)']=timed(sites_run)
        out['sequential equivalent of the same requests (computed)']={'median_ms':round(out['ten site searches in parallel (branch only)']['requests']*SITE_LATENCY*1000),'requests':out['ten site searches in parallel (branch only)']['requests']}
        try:
            import source_health as sh
            h=sh.Health('');
            for i in range(1):pass
            def with_health():
                t=Transport({'jacktook':ConnectionError(),'pov':[SRC]});pf.search(REQ,transport=t,health=h);return t.calls
            first=timed(with_health,1);second=timed(with_health,1)
            out['dead provider: first search / next search (cooldown skips it)']={'first_ms':first['median_ms'],'first_requests':first['requests'],'next_ms':second['median_ms'],'next_requests':second['requests']}
        except ImportError:pass
    out['peak resident memory MB']=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,1)
    out['threads at end']=__import__('threading').active_count()
    return out

if __name__=='__main__':
    if '--compare' in sys.argv:
        i=sys.argv.index('--compare');libs=sys.argv[i+1:i+3];res={}
        for name,lib in zip(('main (before)','branch (after)'),libs):
            res[name]=json.loads(subprocess.run([sys.executable,'-B',__file__,'--lib',lib],capture_output=True,text=True,cwd=os.path.dirname(__file__),check=True).stdout.splitlines()[-1])
        print(json.dumps(res,indent=1))
    else:print(json.dumps(child(sys.argv[sys.argv.index('--lib')+1])))
