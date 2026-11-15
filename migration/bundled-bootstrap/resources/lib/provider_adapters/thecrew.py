"""Headless bridge to the installed Crew movie/episode scraper and resolver; no plugin playback routes."""
import contextlib,json,re
from urllib.parse import parse_qsl


def _payload(value):
 return json.loads(json.dumps(value,default=lambda item:list(item) if isinstance(item,(set,tuple)) else str(item)))


def _quality(value):
 value=str(value or '').lower()
 if '2160' in value or '4k' in value:return '4k'
 if '1080' in value:return '1080p'
 if '720' in value:return '720p'
 return 'sd'


def _size(value):
 if isinstance(value,(int,float)):return max(0,float(value))
 match=re.search(r'([\d.]+)\s*(TB|GB|GIB|MB|MIB|KB|KIB)?',str(value or ''),re.I)
 if not match:return 0.0
 number=float(match[1]);unit=(match[2] or 'GB').upper()
 return number*1024 if unit=='TB' else number/1024 if unit in ('MB','MIB') else number/1024**2 if unit in ('KB','KIB') else number


def _link(value):
 if not isinstance(value,str):return value
 if '|' not in value:return value
 url,headers=value.split('|',1);return {'url':url,'headers':dict(parse_qsl(headers))}


@contextlib.contextmanager
def _headless(module):
 # The normal source module cleans up Kodi playback UI on a scrape exception. A backup search owns no playback UI.
 replacements={name:getattr(module,name) for name in ('cleanup_playback_ui','_show_tv_evening_source_failure') if hasattr(module,name)}
 try:
  for name in replacements:setattr(module,name,lambda *args,**kwargs:None)
  yield
 finally:
  for name,value in replacements.items():setattr(module,name,value)


def search(request,context):
 context.check()
 kind=request.get('media_type')
 if kind not in ('movie','episode'):return []
 if kind=='episode' and (request.get('season') is None or request.get('episode') is None or not request.get('show_title')):return []
 module=context.import_module('resources.lib.modules.sources')
 with _headless(module):
  scraper=module.Sources()
  sources=scraper.getSources(str(request.get('title') or request.get('show_title') or ''),str(request.get('year') or ''),
   request.get('imdb') or '',tvdb=request.get('tvdb'),tmdb=request.get('tmdb'),
   season=str(request.get('season','')) if kind=='episode' else '',episode=str(request.get('episode','')) if kind=='episode' else '',
   tvshowtitle=request.get('show_title','') if kind=='episode' else '',premiered=request.get('premiered',''),
   quality='4K' if _quality(request.get('quality'))=='4k' else 'HD',timeout=max(0.1,context.remaining()),show_dialog=False,use_overlay=False)
 context.check();out=[]
 for source in sources or []:
  if not isinstance(source,dict) or not source.get('url') or source.get('local'):continue
  try:seeders=int(source.get('seeders') or source.get('seeds') or 0)
  except (ValueError,TypeError):seeders=0
  hash_=str(source.get('info_hash') or source.get('hash') or '')
  if not hash_:
   found=re.search(r'(?i)btih:([a-f0-9]{40})(?:&|$)',str(source['url']))
   hash_=found[1].lower() if found else ''
  cached=source.get('cached') is True or str(source.get('source','')).lower()=='cached torrent'
  out.append({'name':str(source.get('release_title') or source.get('name') or source.get('label') or request.get('title') or request.get('show_title') or ''),
   'quality':_quality(source.get('quality')),'size':_size(source.get('size')),'seeders':seeders,
   'resolver':{'source':_payload(source)},'torrent_hash':hash_,'cached':cached,'media_type':kind})
 return out


def resolve(candidate,context):
 context.check();source=(candidate.get('resolver') or {}).get('source')
 if not isinstance(source,dict) or not source.get('url') or source.get('local'):return None
 module=context.import_module('resources.lib.modules.sources')
 with _headless(module):result=module.Sources().sourcesResolve(source,info=False)
 context.check();return _link(result)
