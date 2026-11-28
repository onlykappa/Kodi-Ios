"""Remember Umbrella/AllDebrid's selected file in RAM; renew that link once without scraping or downloading again."""
import ast,json,urllib.parse,urllib.request
from pathlib import Path

import re,time
PROPERTY='KodiIOS.UmbrellaRenewal'
WANT='KodiIOS.UnlockWant'   # set when a version is picked: {"t": pick time, "season": n, "episode": n} (season/episode only for an episode)
MARK='# KODI-IOS-LINK-RENEWAL'

def episode_named(name,season,episode):
 """True when a file name carries this season and episode (S01E01, 1x01, Season 1 Episode 1). An empty name cannot say, so it counts."""
 text=str(name or '').lower()
 if not text:return True
 s,e=int(season),int(episode)
 patterns=(r'(?<![a-z0-9])s0*%d[ ._-]*e0*%d(?!\d)'%(s,e),r'(?<!\d)%dx0*%d(?!\d)'%(s,e),r'season[ ._-]*0*%d[ ._-]*(?:episode|ep|e)[ ._-]*0*%d(?!\d)'%(s,e))
 return any(re.search(p,text) for p in patterns)

def worth_checking(want_text,filename,state):
 """ISSUE-490 (owner log f155938b, Wi-Fi: a movie pick unlocks one link; an episode pick unlocked 3 to 20 and each went through the 1.3 s direct check, 49-86 % of the 8-17 s
 from the pick to the player): only ONE unlock per pick is checked, and for an episode only a file that carries that season and episode. Everything else is handed back
 untouched at once. `state` is {'t': the pick last checked}. No pick note (Umbrella started some other way) checks as before."""
 try:want=json.loads(want_text) if want_text else None
 except (ValueError,TypeError):want=None
 if not isinstance(want,dict) or not want.get('t'):return True
 if state.get('t')==want['t']:return False
 if want.get('season') is not None and want.get('episode') is not None:
  try:
   if not episode_named(filename,want['season'],want['episode']):return False
  except (TypeError,ValueError):pass
 state['t']=want['t']
 return True

_CHECKED={}

def web(url):
 try:
  p=urllib.parse.urlsplit(url)
  return p.scheme in ('http','https') and bool(p.hostname)
 except (TypeError,ValueError):return False

def remember(link,response,home=None,warm=None,route=None):
 if not isinstance(response,dict) or not web(response.get('link','')) or not isinstance(link,str) or not 0<len(link)<8192:return
 real=home is None
 if real:
  import xbmcgui
  home=xbmcgui.Window(10000)
  if warm is None:   # the real call from Umbrella's unlock: roadmap 1B.4, read the link's start while Umbrella's window closes
   try:
    import link_warm;warm=link_warm.start
   except Exception:warm=None
 record={'source':response['link'],'link':link,'size':int(response.get('filesize') or 0),'filename':str(response.get('filename') or '')}
 if len(json.dumps(record))<20000:home.setProperty(PROPERTY,json.dumps(record))
 # ISSUE-280: Umbrella returns response['link'] to Kodi; an MKV / AVI / WebM goes through the service's cache (four
 # connections, its start and end already asked for). The record above keeps the real link for renewal and Play on TV.
 if route is None and real:
  try:
   import remote_media,time
   # ISSUE-488: an Umbrella that unlocks link after link (owner log ff742bd7: 1,571 in 7 minutes) gets no cache attempt, direct check or warm-up for them.
   check=worth_checking(home.getProperty(WANT),record['filename'],_CHECKED)
   _note(home,record,check)
   route=remote_media.for_kodi if check and not remote_media.cycling(time.monotonic()) else None
   if route is None:warm=None
  except Exception:route=None
 if route:
  try:
   local=route(response['link'],home)
   if local!=response['link'] and web(local):
    response['link']=local
    return   # the cache reads the start and the end itself
  except Exception:pass
 if warm:
  try:warm(response['link'],record['size'])
  except Exception:pass

def _note(home,record,checked=True):
 """ISSUE-488: one line per unlock Umbrella hands over (the first few of a cycle), so a slow open shows how many files Umbrella went through between the pick and Kodi,
 which file each was, how big, and how long after the tap. Release name and size only, never the address."""
 try:
  import json as _j,time,xbmc
  mark=_j.loads(home.getProperty('KodiIOS.Open') or '{}')
  since=time.time()-float(mark['t']) if mark.get('t') else -1
  xbmc.log('Kodi iOS Umbrella unlock: %s, %.0f MB, %s'%(str(record.get('filename') or '?')[:90],int(record.get('size') or 0)/1048576.0,
           '%.1f s after the tap'%since if since>=0 else 'no open mark')+('' if checked else ' (not checked)'),xbmc.LOGINFO)
 except Exception:pass

def selected(source,home):
 try:
  record=json.loads(home.getProperty(PROPERTY))
  return record if record.get('source')==source.partition('|')[0] and record.get('link') else None
 except (ValueError,TypeError,AttributeError):return None

def renew(record,context=None,token=None,request=None):
 import alldebrid
 if token is None:
  import debrid_token
  token=debrid_token.get()
 def send(method,url,data=None,headers=None):
  body=urllib.parse.urlencode(data,doseq=True).encode() if data is not None else None
  req=urllib.request.Request(url,data=body,headers=headers or {},method=method)
  with urllib.request.urlopen(req,timeout=15,context=context) as response:return response.read()
 url,name,size=alldebrid.AllDebrid(token,request=request or send).unlock(record['link'])
 if not web(url):raise RuntimeError('The source did not give a valid stream link')
 if record.get('size') and size!=int(record['size']):raise RuntimeError('The refreshed stream is a different file')
 if record.get('filename') and name!=record['filename']:raise RuntimeError('The refreshed stream is a different file')
 return url

def hook(path):
 """Patch only a recognized AllDebrid unlock response, once. Unknown upstream versions remain untouched."""
 path=Path(path)
 if not path.is_file():return False
 text=path.read_text(encoding='utf-8')
 if MARK in text:return False
 try:
  tree=ast.parse(text)
  cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='AllDebrid')
  method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='unrestrict_link')
 except (SyntaxError,StopIteration):return False
 lines=text.splitlines(keepends=True);body=''.join(lines[method.lineno-1:method.end_lineno])
 anchor="\t\t\tresponse = self._get(url, url_append)\n"
 if body.count(anchor)!=1 or 'link' not in [a.arg for a in method.args.args]:return False
 injection=('\t\t\ttry: '+MARK+'\n'
            '\t\t\t\timport sys as _ksys, xbmcvfs as _kvfs\n'
            "\t\t\t\t_klib = _kvfs.translatePath('special://xbmc/addons/service.kodi.ios.bootstrap/resources/lib')\n"
            '\t\t\t\tif _klib not in _ksys.path: _ksys.path.insert(0, _klib)\n'
            '\t\t\t\timport umbrella_recovery as _krenew\n'
            '\t\t\t\t_krenew.remember(link, response)\n'
            '\t\t\texcept Exception: pass\n')
 lines[method.lineno-1:method.end_lineno]=[body.replace(anchor,anchor+injection)]
 updated=''.join(lines)
 try:compile(updated,str(path),'exec')
 except SyntaxError:return False
 path.write_text(updated,encoding='utf-8');return True


# ISSUE-494 (owner log e41f48ad, build 711): after an episode pick Umbrella unlocks the files of the picked pack one after another until the right one turns up, about 0.25 s each:
# 26 files 15.8 s (Dragon Ball), 158 files 38.2 s (Fullmetal Alchemist: Brotherhood). The next episode of the same pack unlocked the same files again. AllDebrid's answer for a locked
# link is cached for a few minutes (in memory only) so a second pass over a pack makes no calls. The cache is under Umbrella's own unrestrict_link, so everything after the
# answer (the selected-file record, the one check per pick, the cache route) still runs for every unlock. The first pass over a pack is as slow as before.
UNLOCK_CACHE={}
UNLOCK_FRESH=600.0
UNLOCK_MAX=600
CACHE_MARK='# KODI-IOS-UNLOCK-CACHE'

def wrap_get(cls,clock=time.time):
 """Make cls._get answer a repeated 'link/unlock' of the same locked link from memory. True when wrapped now."""
 import copy
 original=getattr(cls,'_get',None)
 if original is None or getattr(original,'_kodi_ios_cached',False):return False
 def cached(self,url,*args,**kwargs):
  key=str(args[0]) if args else None
  if url=='link/unlock' and key and not kwargs:
   hit=UNLOCK_CACHE.get(key)
   if hit and 0<=clock()-hit[0]<UNLOCK_FRESH:return copy.deepcopy(hit[1])
  answer=original(self,url,*args,**kwargs)
  if url=='link/unlock' and key and not kwargs and isinstance(answer,dict) and web(answer.get('link','')):
   if len(UNLOCK_CACHE)>=UNLOCK_MAX:UNLOCK_CACHE.clear()
   UNLOCK_CACHE[key]=(clock(),copy.deepcopy(answer))
  return answer
 cached._kodi_ios_cached=True
 cls._get=cached
 return True

def cache_hook(path):
 """Add the unlock cache to Umbrella's AllDebrid module once; a module of another shape is left alone. True when the file changed."""
 path=Path(path)
 if not path.is_file():return False
 text=path.read_text(encoding='utf-8')
 if CACHE_MARK in text:return False
 try:
  tree=ast.parse(text)
  cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='AllDebrid')
  next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_get')
  next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='unrestrict_link')
 except (SyntaxError,StopIteration):return False
 addition=('\n'+CACHE_MARK+'\n'
           'try:\n'
           '\timport sys as _ksys, xbmcvfs as _kvfs\n'
           "\t_klib = _kvfs.translatePath('special://xbmc/addons/service.kodi.ios.bootstrap/resources/lib')\n"
           '\tif _klib not in _ksys.path: _ksys.path.insert(0, _klib)\n'
           '\timport umbrella_recovery as _kcache\n'
           '\t_kcache.wrap_get(AllDebrid)\n'
           'except Exception: pass\n')
 updated=text.rstrip('\n')+'\n'+addition
 try:compile(updated,str(path),'exec')
 except SyntaxError:return False
 path.write_text(updated,encoding='utf-8');return True
