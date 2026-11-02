"""Repeatable performance benchmark for the portrait layout in the desktop rig (scripts/portrait_rig.py).

Starts Kodi (debug log on) under Xvfb at the phone's portrait safe area, then measures through JSON-RPC and kodi.log:
- start: Kodi process start -> Home window initialised;
- hero / rows: Home initialised -> the hero list (4000) and the first rows (5001-5003) have items;
- plugin_runs: Python plugin invocations (widget loads) in the first `settle` seconds after Home;
- tab switches: Portrait.Tab change -> that hub's hero list has items (Movies 14000, TV 24000);
- idle CPU (% of one core, averaged over `idle` seconds on Home) and resident memory (MB).
Prints one JSON line. Run with Kodi's default dirty-region rendering (portrait_rig.py writes algorithmdirtyregions 0 for screenshots:
override userdata/advancedsettings.xml first). These are desktop-rig figures (x86, software GL, Kodi 21.2/20.5); they compare builds with each
other, they are not iPhone timings.
usage: perf_rig_bench.py --rig DIR [--launcher CMD --log FILE] [--runs 3] [--display :7]
(the default launcher is the system `kodi`; for Kodi 21 from Flathub pass a script that runs it, and its kodi.log)
"""
import argparse,json,os,re,signal,statistics,subprocess,sys,time,urllib.request
from pathlib import Path

def rpc(method,params=None,port=8089,timeout=3):
 body=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params or {}}).encode()
 req=urllib.request.Request('http://127.0.0.1:%d/jsonrpc'%port,body,{'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=timeout) as r:return json.loads(r.read()).get('result')

def labels(*names):
 try:return rpc('XBMC.GetInfoLabels',{'labels':list(names)}) or {}
 except Exception:return {}

def booleans(*names):
 try:return rpc('XBMC.GetInfoBooleans',{'booleans':list(names)}) or {}
 except Exception:return {}

def builtin(command):
 rpc('Addons.ExecuteAddon',{'addonid':'script.rig','params':['builtin='+command]})

def prop(name,value):
 rpc('Addons.ExecuteAddon',{'addonid':'script.rig','params':['prop='+name,'value='+value]})

def wait_for(check,timeout,step=0.05):
 start=time.monotonic()
 while time.monotonic()-start<timeout:
  if check():return time.monotonic()-start
  time.sleep(step)
 return None

def no_dialog():
 """Close a prompt an add-on opened (TMDb Helper's Trakt sign-in): list labels are read from the top window."""
 if booleans('System.HasActiveModalDialog').get('System.HasActiveModalDialog'):
  try:rpc('Input.Back')
  except Exception:pass

def filled(container):
 def check():
  no_dialog()
  return (labels('Container(%d).NumItems'%container).get('Container(%d).NumItems'%container) or '0') not in ('','0')
 return check

def proc_stats(pid,seconds):
 """(average CPU % of one core over `seconds`, resident MB) from /proc."""
 tick=os.sysconf('SC_CLK_TCK')
 def cpu():
  fields=open('/proc/%d/stat'%pid).read().rsplit(')',1)[1].split()
  return int(fields[11])+int(fields[12])
 a=cpu();time.sleep(seconds);b=cpu()
 rss=int(open('/proc/%d/statm'%pid).read().split()[1])*os.sysconf('SC_PAGE_SIZE')/2**20
 return round(100.0*(b-a)/tick/seconds,1),round(rss)

def kodi_pid(fallback):
 """The Kodi process itself (a Flathub launcher wraps it in dbus/bwrap processes)."""
 try:
  pids=subprocess.run(['pgrep','-x','kodi.bin'],capture_output=True,text=True).stdout.split()
  return int(pids[-1]) if pids else fallback
 except Exception:return fallback

RIG_SETTINGS={'services.webserver':'true','services.webserverport':'8089','services.webserverauthentication':'false',
              'lookandfeel.skin':'skin.arctic.fuse.3','filelists.showparentdiritems':'false'}

def fix_settings(path):
 """A crashed run can leave Kodi to recreate guisettings.xml with defaults (web server off): put the rig's back."""
 if not path.exists():return
 text=path.read_text(errors='replace')
 for key,value in RIG_SETTINGS.items():
  pattern=r'<setting id="%s"[^>]*?(?:/>|>[^<]*</setting>)'%re.escape(key)
  line='<setting id="%s">%s</setting>'%(key,value)
  text=re.sub(pattern,line,text) if re.search(pattern,text) else text.replace('</settings>',line+'\n</settings>')
 path.write_text(text)

def one_run(rig,display,settle,idle,launcher=None,log=None):
 home=Path(rig)/'home';log=Path(log) if log else home/'.kodi/temp/kodi.log'
 fix_settings(log.parent.parent/'userdata/guisettings.xml')
 env=dict(os.environ,DISPLAY=display,HOME=str(home),LIBGL_ALWAYS_SOFTWARE='1')
 if launcher:env['HOME']=os.environ.get('HOME','/root')
 t0=time.monotonic()
 kodi=subprocess.Popen((launcher.split() if launcher else ['kodi','--standalone','-fs'])+['--debug'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 out={}
 try:
  up=wait_for(lambda:labels('System.CurrentWindow').get('System.CurrentWindow') not in (None,''),90,0.2)
  if up is None:raise RuntimeError('Kodi did not answer')
  at_home=wait_for(lambda:booleans('Window.IsActive(home)').get('Window.IsActive(home)') is True,90,0.1)
  out['start_s']=round(time.monotonic()-t0,2)
  # Close a sign-in prompt from an add-on (Trakt) if one opened over Home.
  if booleans('System.HasActiveModalDialog').get('System.HasActiveModalDialog'):rpc('Input.Back')
  h0=time.monotonic()
  # Every list polled together; first time each has items (the hero and Home's first rows after the Continue
  # Watching row, whose add-on the rig does not carry).
  pending={'hero':4000,'row1':5002,'row2':5003,'row3':5004}
  while pending and time.monotonic()-h0<45:
   no_dialog()
   got=labels(*['Container(%d).NumItems'%c for c in pending.values()])
   for name,c in list(pending.items()):
    if (got.get('Container(%d).NumItems'%c) or '0') not in ('','0'):out[name+'_s']=round(time.monotonic()-h0,2);del pending[name]
   time.sleep(0.05)
  for name in pending:out[name+'_s']=None
  time.sleep(max(0,settle-(time.monotonic()-h0)))
  text=log.read_text(errors='replace')
  out['plugin_runs']=len(re.findall(r'CPythonInvoker\(\d+, [^)]*?/plugin\.video\.[^)]*?\): the source directory',text)) or \
                     len(re.findall(r'running add-on script|CPythonInvoker\(\d+\): plugin://',text))
  out['python_invocations']=len(re.findall(r'CPythonInvoker\(\d+, ',text)) and len(set(re.findall(r'CPythonInvoker\((\d+), ',text)))
  # Tab switches (the portrait hubs share one window; Portrait.Tab picks the group).
  # Tab switches with the tab bar's own actions (portrait.tab_actions of the tree under test, conditions dropped).
  sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
  import portrait
  for name,container in (('movies',14000),('tv',24000),('home',4000)):
   t=time.monotonic()
   actions=[a for _,a in portrait.tab_actions(name) if not a.startswith(('ReplaceWindow','SetFocus'))]
   rpc('Addons.ExecuteAddon',{'addonid':'script.rig','params':['builtin%d=%s'%(n,a) for n,a in enumerate(actions)]})
   took=wait_for(filled(container),30)
   out['tab_%s_s'%name]=round(time.monotonic()-t,2) if took is not None else None
  out['idle_cpu_pct'],out['rss_mb']=proc_stats(kodi_pid(kodi.pid),idle)
 finally:
  try:rpc('Application.Quit')
  except Exception:pass
  try:kodi.wait(25)
  except subprocess.TimeoutExpired:os.killpg(kodi.pid,signal.SIGKILL)
  time.sleep(3)
 return out

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--rig',type=Path,required=True);p.add_argument('--runs',type=int,default=3)
 p.add_argument('--launcher');p.add_argument('--log')
 p.add_argument('--display',default=':7');p.add_argument('--settle',type=float,default=40);p.add_argument('--idle',type=float,default=20)
 a=p.parse_args();runs=[]
 for n in range(a.runs):
  try:runs.append(one_run(a.rig,a.display,a.settle,a.idle,a.launcher,a.log))
  except Exception as error:
   # The desktop Kodi crashes now and then while several add-ons start at once (Python 3.13+, see docs/PERFORMANCE.md).
   runs.append({'crashed':type(error).__name__})
   subprocess.run(['pkill','-x','kodi.bin']);time.sleep(5)
  print(json.dumps({'run':n+1,**runs[-1]}),flush=True)
 runs=[r for r in runs if 'crashed' not in r] or [{}]
 keys=sorted({k for r in runs for k in r})
 median={k:statistics.median([r[k] for r in runs if r.get(k) is not None]) if any(r.get(k) is not None for r in runs) else None for k in keys}
 print(json.dumps({'median':median}))
