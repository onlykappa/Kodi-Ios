"""Headless bridge to the pinned Jacktook search API; scraping and playback implementations stay upstream."""
import contextlib,dataclasses,enum,importlib,json,re

ADDON='plugin.video.jacktook'
VERSION='1.22.0'
DEFAULT_MANIFESTS=('https://torrentio.strem.fun/manifest.json','https://comet.elfhosted.com/manifest.json')

def _load(context,name):return context.import_module(name) if hasattr(context,'import_module') else importlib.import_module(name)

def _plain(value):
 if isinstance(value,enum.Enum):return _plain(value.value)
 if dataclasses.is_dataclass(value):return _plain(dataclasses.asdict(value))
 if isinstance(value,dict):return {str(key):_plain(item) for key,item in value.items()}
 if isinstance(value,(tuple,list)):return [_plain(item) for item in value]
 if value is None or isinstance(value,(str,int,float,bool)):return value
 return None

def _quality(value,name=''):
 text=str(value or '').lower()+' '+name.lower()
 if re.search(r'\b(?:2160p?|4k|uhd)\b',text):return '4k'
 for label in ('1080p','720p','480p'):
  if label in text:return label
 return 'sd' if 'sd' in text else 'unknown'

def _identity(request):
 return {key:request[key] for key in ('media_type','title','show_title','year','season','episode','tmdb','imdb','tvdb') if key in request}

def _number(value,default=0):
 try:return int(value)
 except (TypeError,ValueError):return default

def _defaults(module,context):
 """An untouched install gets public discovery endpoints through Jacktook's own manifest parser, only in RAM."""
 if not hasattr(module,'cache'):return None
 if any(module.cache.get(key) is not None for key in ('stremio_user_addons','stremio_addons')):return None
 selection=module.cache.get('source_manager_selection')
 if selection is not None:return None
 if any(context.settings.getSetting(key) for key in ('jackett_host','prowlarr_host','jackgram_host','external_scraper_module')):return None
 helpers=_load(context,'lib.clients.stremio.helpers');records=[]
 for url in DEFAULT_MANIFESTS:
  context.check()
  try:
   response=context.session.get(url,timeout=min(5,max(.05,context.remaining())))
   response.raise_for_status();manifest=response.json()
   if not isinstance(manifest,dict) or not manifest.get('id'):continue
   records.append({'transportUrl':url,'transportName':'custom','manifest':manifest})
  except Exception:
   context.check()  # cancellation/deadline is never a successful empty scrape
  finally:
   if 'response' in locals():response.close();del response
 return helpers.AddonManager(records).addons

class _SilentDialog:
 def __init__(self,context):self.context=context
 def create(self,*args,**kwargs):self.context.check()
 def update(self,*args,**kwargs):self.context.check()
 def close(self):pass
 def iscanceled(self):return self.context.cancelled()

class _Listener:
 def __init__(self,context):self.dialog=_SilentDialog(context)
 def __enter__(self):return self
 def __exit__(self,*args):pass

class _CacheOverlay:
 """Search's automatic source-manager reconciliation must not persist ephemeral default selections."""
 def __init__(self,base):self.base=base;self.values={}
 def get(self,key,*args,**kwargs):return self.values[key] if key in self.values else self.base.get(key,*args,**kwargs)
 def set(self,key,value,*args,**kwargs):self.values[key]=value
 def __getattr__(self,key):return getattr(self.base,key)

@contextlib.contextmanager
def _headless(module,context,defaults=None):
 saved={}
 changes={'close_busy_dialog':lambda:None,'notification':lambda *args,**kwargs:None,'DialogListener':lambda:_Listener(context)}
 if defaults is not None:
  getter=module.get_setting
  changes.update(get_selected_stream_addons=lambda:defaults,
                 get_addon_by_base_url=lambda url:next((addon for addon in defaults if addon.url()==url),None),
                 cache=_CacheOverlay(module.cache),
                 get_setting=lambda key,*args,**kwargs:True if key=='stremio_enabled' else getter(key,*args,**kwargs))
 for name,value in changes.items():
  if hasattr(module,name):saved[name]=getattr(module,name);setattr(module,name,value)
 try:yield
 finally:
  for name,value in saved.items():setattr(module,name,value)

def search(request,context):
 context.check();module=_load(context,'lib.search');defaults=_defaults(module,context)
 episode=request.get('media_type')=='episode';mode='tv' if episode else 'movies'
 title=(request.get('show_title') if episode else request.get('title')) or request.get('title','')
 ids={name+'_id':request[name] for name in ('imdb','tmdb','tvdb') if request.get(name)}
 season=_number(request.get('season'));number=_number(request.get('episode'))
 if not title or (episode and (not str(request.get('season','')).isdigit() or not str(request.get('episode','')).isdigit())):return []
 with _headless(module,context,defaults):
  found=module.search_client(title,ids,mode,mode,False,season,number,show_dialog=False,
                             year=_number(request.get('year')) or None)
  context.check()
  # Native pre-processing adds quality and applies the exact episode filter; it does not resolve or play.
  found=module.pre_process_results(found or [],mode,request.get('title',''),number,season,
                                    skip_episode_filter=request.get('purpose')=='packs')
 context.check();out=[]
 for source in found or []:
  context.check();native=_plain(source if isinstance(source,dict) else vars(source))
  name=str(native.get('title') or '')
  if not name:continue
  size=native.get('size') or 0
  try:size=max(0,float(size))/(1024**3)
  except (ValueError,TypeError):size=0
  candidate={'name':name,'quality':_quality(native.get('quality'),name),'size':size,'seeders':max(0,_number(native.get('seeders'))),
             'media_type':request.get('media_type','movie'),'resolver':{'native':native,'request':_identity(request)},
             'upstream_provider':str(native.get('addonName') or native.get('indexer') or 'Jacktook')}
  for key in ('imdb','tmdb'):
   if request.get(key):candidate[key]=str(request[key])
  if native.get('url'):candidate['url']=native['url']
  if native.get('infoHash'):candidate['torrent_hash']=native['infoHash']
  out.append(candidate)
 return out

def resolve(candidate,context):
 context.check();payload=candidate.get('resolver') or {};native=payload.get('native') or {}
 module=_load(context,'lib.clients.stremio.playback')
 converted=module.payload_from_torrent(native)
 # Torrents remain magnets here: the app's existing chosen-source resolver handles Elementum/AllDebrid.
 resolved=module.resolve(module.candidate_from_payload(converted),{'torrent_enabled':True,'is_torrent':True})
 context.check()
 url=resolved.get('url') if isinstance(resolved,dict) else resolved
 if isinstance(url,str) and url.startswith(('http://','https://','magnet:')):return url
 raise ValueError('Jacktook did not resolve a playable source')
