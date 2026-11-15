"""POV/Magneto adapter: call installed providers and the selected-source resolver, never the provider UI."""
import concurrent.futures,importlib,re

ADDON='plugin.video.pov'
VERSION='6.11.03'
MAGNETO_VERSION='6.11.01'

def _load(context,name):return context.import_module(name) if hasattr(context,'import_module') else importlib.import_module(name)

def _number(value,default=0):
 try:return int(value)
 except (ValueError,TypeError):return default

def _quality(value,name):
 text=str(value or '').lower()+' '+name.lower()
 if re.search(r'\b(?:4k|2160p?|uhd)\b',text):return '4k'
 for label in ('1080p','720p','480p'):
  if label in text:return label
 return 'sd' if 'sd' in text else 'unknown'

def _aliases(values):
 out=[]
 for value in values or []:
  if isinstance(value,str) and value:out.append({'title':value,'country':''})
  elif isinstance(value,dict) and value.get('title'):out.append({'title':str(value['title']),'country':str(value.get('country') or '')})
 return out

def _data(request,context):
 episode=request.get('media_type')=='episode'
 data={'imdb':request.get('imdb',''),'title':request.get('title',''),'year':str(request.get('year') or ''),
       'aliases':_aliases(request.get('aliases')),'timeout':max(1,min(15,int(context.remaining())))}
 if episode:data.update(tvdb=request.get('tvdb',''),tvshowtitle=request.get('show_title') or request.get('title',''),
                        season=str(request.get('season',0)),episode=str(request.get('episode',0)),total_seasons=request.get('total_seasons',''))
 return data

def _one(provider,data,packs,context):
 context.check();source=provider()
 if packs and getattr(provider,'pack_capable',False):
  # Magneto providers share their normal request with pack parsing through SourceRegistry futures.
  # Calling sources_packs alone leaves that future unfulfilled (Torrentio/Comet then time out).
  source.sources(dict(data),{});context.check()
  result=source.sources_packs(dict(data),{})
 else:result=source.sources(dict(data),{})
 context.check();return result or []

def search(request,context):
 context.check();api=_load(context,'pov');providers=api.sources()
 episode=request.get('media_type')=='episode';data=_data(request,context)
 if not data['imdb'] or not (data.get('tvshowtitle') or data['title']):return []
 if episode and (not data['season'].isdigit() or not data['episode'].isdigit()):return []
 providers=[(name,provider) for name,provider in providers if getattr(provider,'hasEpisodes' if episode else 'hasMovies',False)]
 executor=concurrent.futures.ThreadPoolExecutor(max_workers=6);pending={};out=[]
 try:
  for name,provider in providers:
   context.check()
   pending[executor.submit(_one,provider,data,request.get('purpose')=='packs',context)]=name
  while pending:
   context.check()
   done,_=concurrent.futures.wait(tuple(pending),timeout=min(.1,max(.01,context.remaining())),return_when=concurrent.futures.FIRST_COMPLETED)
   for future in done:
    provider_name=pending.pop(future)
    try:results=future.result()
    except Exception:
     context.check();continue
    for result in results:
     context.check()
     if not isinstance(result,dict):continue
     name=str(result.get('name') or result.get('display_name') or '')
     if not name:continue
     # Upstream provider sizes are already GiB (source_utils._size), unlike Jacktook's byte counts.
     try:size=max(0,float(result.get('size') or 0))
     except (ValueError,TypeError):size=0
     native=dict(result,provider=provider_name,scrape_provider='external',external=True)
     meta={key:request[key] for key in ('media_type','title','show_title','year','season','episode','tmdb','imdb','tvdb') if key in request}
     candidate={'name':name,'quality':_quality(result.get('quality'),name),'size':size,'seeders':max(0,_number(result.get('seeders'))),
                'media_type':request.get('media_type','movie'),'resolver':{'native':native,'request':meta},'upstream_provider':provider_name}
     if result.get('url'):candidate['url']=result['url']
     if result.get('hash'):candidate['torrent_hash']=str(result['hash']).lower()
     for key in ('imdb','tmdb'):
      if request.get(key):candidate[key]=str(request[key])
     out.append(candidate)
 finally:
  for future in pending:future.cancel()
  executor.shutdown(wait=False)
 return out

def resolve(candidate,context):
 context.check();payload=candidate.get('resolver') or {};native=dict(payload.get('native') or {});request=payload.get('request') or {}
 url=native.get('url') or candidate.get('url') or ''
 if url.startswith(('http://','https://')) and native.get('direct'):return url
 if url.startswith('magnet:'):
  # This is a chosen result, not discovery. A configured POV account may resolve it; otherwise use the app's
  # established torrent path without invoking POV's player/source-selection windows.
  debrid=_load(context,'modules.debrid');enabled=debrid.debrid_enabled()
  if not enabled:return url
  native['debrid']=native.get('debrid') or enabled[0]
  if not native.get('hash'):native['hash']=candidate.get('torrent_hash') or ''
  meta={'mediatype':request.get('media_type','movie'),'title':request.get('show_title') or request.get('title',''),
        'ep_name':request.get('title',''),'season':str(request.get('season',0)) if request.get('media_type')=='episode' else None,
        'episode':str(request.get('episode',0)) if request.get('media_type')=='episode' else None,'imdb_id':request.get('imdb','')}
  resolved=debrid.Source(native,meta).resolve_sources();context.check()
  if isinstance(resolved,str) and resolved.startswith(('http://','https://')):return resolved
  raise ValueError('POV did not resolve the selected source')
 if url.startswith(('http://','https://')):return url
 raise ValueError('POV source has no supported media locator')
