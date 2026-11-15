"""Use installed Prism Sources/Resolver APIs with its real pinned provider package and no cache-assist side effects."""
import contextlib,json,os,shutil
from pathlib import Path
from urllib.parse import parse_qsl


def _safe(value):
 return json.loads(json.dumps(value,default=lambda item:list(item) if isinstance(item,(set,tuple)) else str(item)))


def _metadata(request):
 episode=request.get('media_type')=='episode';aliases=[a if isinstance(a,str) else a.get('title','') for a in request.get('aliases') or [] if isinstance(a,(str,dict))]
 info={'mediatype':'episode' if episode else 'movie','title':str(request.get('title') or request.get('show_title') or ''),
  'originaltitle':str(request.get('title') or ''),'year':request.get('year') or '', 'aliases':aliases,
  'imdb_id':request.get('imdb') or '', 'tmdb_id':request.get('tmdb') or '', 'tvdb_id':request.get('tvdb') or ''}
 if episode:info.update(tvshowtitle=request.get('show_title') or '',season=request.get('season'),episode=request.get('episode'),
  **{'tvshow.imdb_id':request.get('imdb') or '', 'tvshow.year':request.get('year') or ''})
 # A missing pack episode count must not divide a package to zero or invent an episode mapping.
 return {'info':info,'episode_count':int(request.get('episode_count') or 1),'show_episode_count':int(request.get('show_episode_count') or 1),
  'season_count':int(request.get('season_count') or request.get('season') or 1),'is_airing':bool(request.get('is_airing')),
  'absoluteNumber':request.get('absolute_episode') or '', 'simkl_id':request.get('simkl') or 0}


def _copy_missing(source,destination,context):
 for folder,dirs,files in os.walk(source):
  dirs[:]=[name for name in dirs if not name.startswith('.') and name!='__pycache__']
  for name in files:
   context.check()
   if name.endswith(('.pyc','.pyo')):continue
   origin=Path(folder)/name;target=destination/origin.relative_to(source)
   if origin.is_symlink() or target.exists():continue
   target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(origin,target)


def _providers(context,g):
 """Seed missing bundled provider files, then use Prism's own compatible loader and provider DB registration."""
 source=Path(__file__).resolve().parents[3]/'provider-fallback/prism-a4k'
 if not (source/'meta.json').is_file():raise RuntimeError('The bundled Prism provider package is unavailable')
 user=Path(g.ADDON_USERDATA_PATH)
 for folder in ('providers','providerModules','providerMedia'):
  if (source/folder).is_dir():_copy_missing(source/folder,user/folder,context)
 meta=json.loads((source/'meta.json').read_text(encoding='utf-8'))
 name=meta['name']
 if not name or any(character in name for character in '/\\'):raise ValueError('Invalid bundled Prism package name')
 path=user/'providerMeta'/(name+'.json');path.parent.mkdir(parents=True,exist_ok=True)
 try:
  with path.open('x',encoding='utf-8') as output:json.dump(meta,output)
 except FileExistsError:pass
 manager=context.import_module('resources.lib.modules.providers').CustomProviders()
 manager.update_known_packages();manager.update_known_providers()


def _globals(context):
 g=context.import_module('resources.lib.modules.globals').g
 if getattr(g,'ADDON_ID',None)!='plugin.video.prism':
  # A positive plugin handle avoids invoking first-run service/migration work from a source search.
  g.init_globals(['plugin://plugin.video.prism','1',''],addon_id='plugin.video.prism')
 return g


@contextlib.contextmanager
def _quiet(g):
 names=('cancel_playback','notification');saved={name:getattr(g,name) for name in names if hasattr(g,name)}
 original_abort=getattr(g,'abort_requested',lambda:False)
 try:
  for name in saved:setattr(g,name,lambda *args,**kwargs:None)
  yield original_abort
 finally:
  for name,value in saved.items():setattr(g,name,value)


def search(request,context):
 context.check()
 if request.get('media_type') not in ('movie','episode'):return []
 if request.get('media_type')=='episode' and (not request.get('show_title') or request.get('season') is None or request.get('episode') is None):return []
 g=_globals(context);_providers(context,g);context.check()
 module=context.import_module('resources.lib.modules.getSources');meta=_metadata(request)
 with _quiet(g) as abort:
  g.abort_requested=lambda:context.cancelled() or context.remaining()<=0 or abort()
  try:
   scraper=module.Sources(meta);scraper.silent=True;scraper.window.silent=True
   scraper.timeout=max(0.1,context.remaining())
   # Even a silent stock scrape starts cache-assist on a miss. Searching never enqueues a download.
   scraper._build_cache_assist=lambda:None
   try:result=scraper.get_sources()
   finally:
    scraper.canceled=True;scraper._send_provider_stop_event()
  finally:g.abort_requested=abort
 context.check();sources=result[1] if isinstance(result,(tuple,list)) and len(result)>=2 else [];out=[]
 for source in sources or []:
  if not isinstance(source,dict) or 'uncached' in str(source.get('type','')).lower():continue
  quality=str(source.get('quality') or '').lower();quality='4k' if quality in ('4k','2160p') else quality
  try:size=max(0,float(source.get('size') or 0))/1024;seeders=max(0,int(source.get('seeds') or source.get('seeders') or 0))
  except (ValueError,TypeError):size=0.0;seeders=0
  out.append({'name':str(source.get('release_title') or request.get('title') or request.get('show_title') or ''),
   'quality':quality,'size':size,'seeders':seeders,'resolver':{'source':_safe(source),'metadata':_safe(meta)},
   'torrent_hash':str(source.get('hash') or ''),'cached':source.get('type')=='torrent' and bool(source.get('debrid_provider')),
   'media_type':request['media_type']})
 return out


def resolve(candidate,context):
 context.check();payload=candidate.get('resolver') or {};source=payload.get('source');meta=payload.get('metadata')
 if not isinstance(source,dict) or not isinstance(meta,dict) or 'uncached' in str(source.get('type','')).lower():return None
 g=_globals(context);module=context.import_module('resources.lib.modules.resolver')
 with _quiet(g):result=module.Resolver().resolve_single_source(source,meta,pack_select=False,silent=True,allow_manual_prompt=False)
 context.check();link=result[0] if isinstance(result,(tuple,list)) else result
 if isinstance(link,str) and '|' in link:
  url,headers=link.split('|',1);return {'url':url,'headers':dict(parse_qsl(headers))}
 return link
