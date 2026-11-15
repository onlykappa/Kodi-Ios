"""Anime-only headless Otaku providers. A TMDb season/episode is never treated as a MAL absolute episode."""
import hashlib,json,os,sqlite3,tempfile
from pathlib import Path
from urllib.parse import parse_qsl

MAPPINGS_SHA256='36ba8b785385787131f2f3e8ed218ddd4ceb2f9db16a2cd973db3bede9a47162'


def _mapping_rows(request,context):
 """Read all MAL seasons for a TMDb show from Otaku's pinned public metadata, never from a title search."""
 control=context.import_module('resources.lib.ui.control');path=Path(control.mappingDB)
 if not path.exists():
  source=Path(__file__).resolve().parents[3]/'provider-fallback/otaku/mappings.db'
  if not source.is_file():return []
  data=source.read_bytes();context.check()
  if hashlib.sha256(data).hexdigest()!=MAPPINGS_SHA256:raise ValueError('Otaku mapping metadata digest differs')
  path.parent.mkdir(parents=True,exist_ok=True)
  with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as output:
   temp=Path(output.name);output.write(data)
  try:
   if not path.exists():os.replace(temp,path)
  finally:
   if temp.exists():temp.unlink()
 try:
  with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as database:
   database.row_factory=sqlite3.Row
   return [dict(row) for row in database.execute('SELECT * FROM anime WHERE CAST(themoviedb_id AS TEXT)=?',(str(request['tmdb']),))]
 except sqlite3.DatabaseError:return []


def _tmdb_episode(request,context):
 """TMDb's episode ID/TVDB episode ID disambiguate ordering differences between TMDb and anime catalogues."""
 addon=context.import_module('xbmcaddon').Addon('plugin.video.themoviedb.helper')
 vfs=context.import_module('xbmcvfs');key=context.import_module('drivelibrary').tmdb_key(vfs.translatePath(addon.getAddonInfo('path')))
 if not key:return None
 client=context.import_module('resources.lib.ui.client')
 response=client.get('https://api.themoviedb.org/3/tv/%s/season/%d/episode/%d'%(request['tmdb'],int(request['season']),int(request['episode'])),
  params={'api_key':key,'append_to_response':'external_ids'})
 context.check()
 data=response.json() if response else {}
 if data.get('season_number')!=int(request['season']) or data.get('episode_number')!=int(request['episode']):return None
 return data


def _discover(request,context):
 if request.get('media_type')!='episode' or not str(request.get('tmdb') or '').isdigit():return None
 try:
  if int(request.get('season',-1))<0 or int(request.get('episode',0))<=0:return None
 except (ValueError,TypeError):return None
 rows=_mapping_rows(request,context)
 if not rows:return None  # ordinary TV has no anime mapping: no metadata or scraping network request
 episode=_tmdb_episode(request,context)
 if not episode:return None
 tmdb_id=str(episode.get('id') or '');tvdb_id=str((episode.get('external_ids') or {}).get('tvdb_id') or '')
 if not tmdb_id and not tvdb_id:return None
 api=context.import_module('resources.lib.indexers.anizip').ANIZIPAPI()
 # Season hints prioritize likely MAL entries but do not prove TMDb/TVDB season order equivalence.
 rows.sort(key=lambda row:(str(row.get('thetvdb_season'))!=str(request['season']),int(row.get('thetvdb_part') or 1)))
 found={}
 for row in rows[:16]:
  context.check()
  try:data=api.get_anime_info(int(row['mal_id'])) or {}
  except Exception:
   context.check();continue
  context.check()
  if str((data.get('mappings') or {}).get('mal_id'))!=str(row['mal_id']):continue
  matches=[]
  for key,item in (data.get('episodes') or {}).items():
   if not str(key).isdigit() or not isinstance(item,dict):continue
   candidate_tmdb=str(item.get('tmdbId') or item.get('tmdbEpisodeId') or '')
   candidate_tvdb=str(item.get('tvdbId') or '')
   correct=bool((tmdb_id and candidate_tmdb==tmdb_id) or (tvdb_id and candidate_tvdb==tvdb_id))
   if (tmdb_id and candidate_tmdb and candidate_tmdb!=tmdb_id) or (tvdb_id and candidate_tvdb and candidate_tvdb!=tvdb_id):correct=False
   if not correct:continue
   try:absolute=int(item['episode'])
   except (KeyError,ValueError,TypeError):continue
   if absolute<=0:continue
   matches.append({'verified':True,'source':'otaku-db+tmdb-episode+ani.zip','mal_id':int(row['mal_id']),
    'kitsu_id':row.get('kitsu_id'),'absolute_episode':absolute,'tmdb':str(request['tmdb']),
    'season':int(request['season']),'episode':int(request['episode']),'title':row.get('mal_title') or '',
    'anime_season':None if str(row.get('thetvdb_season'))=='a' else row.get('thetvdb_season'),
    'part':row.get('thetvdb_part'),'episode_tmdb':tmdb_id,'episode_tvdb':tvdb_id})
  unique={(m['mal_id'],m['absolute_episode']):m for m in matches}
  found.update(unique)
  if len(found)>1:return None
 return next(iter(found.values())) if len(found)==1 else None


def _verified(request,context):
 if request.get('media_type')!='episode' or request.get('anime') is not True:return None
 mapping=request.get('anime_mapping')
 if not isinstance(mapping,dict) or mapping.get('verified') is not True:return None
 try:
  mal=int(mapping.get('mal_id') or 0);absolute=int(mapping.get('absolute_episode') or 0)
  if mal<=0 or absolute<=0 or not request.get('tmdb'):return None
  if str(mapping.get('tmdb'))!=str(request['tmdb']):return None
  if int(mapping.get('season',-1))!=int(request.get('season',-2)) or int(mapping.get('episode',-1))!=int(request.get('episode',-2)):return None
 except (ValueError,TypeError):return None
 context.check()
 database=context.import_module('resources.lib.ui.database')
 saved=database.get_mappings(mal,'mal_id') or {}
 if str(saved.get('themoviedb_id'))!=str(request['tmdb']) or str(saved.get('mal_id'))!=str(mal):return None
 if mapping.get('kitsu_id') and str(saved.get('kitsu_id'))!=str(mapping['kitsu_id']):return None
 return dict(mapping,title=saved.get('mal_title') or mapping.get('title') or '')


def search(request,context):
 context.check()
 if request.get('media_type')!='episode':return []
 if not request.get('anime_mapping'):
  discovered=_discover(request,context)
  if discovered is None:return []
  request=dict(request,anime=True,anime_mapping=discovered)
 mapping=_verified(request,context)
 if mapping is None:return []
 control=context.import_module('resources.lib.ui.control');out=[];seen=set()
 for name in ('torrentio','nyaa','animetosho'):
  context.check()
  if not control.getBool('provider.'+name):continue
  if name!='torrentio' and not mapping.get('title'):continue  # no generic show-title guess for a specific MAL season
  module=context.import_module('resources.lib.pages.'+name)
  try:
   result=module.Sources().get_sources(mapping.get('title') or request.get('show_title') or request.get('title') or '',int(mapping['mal_id']),
    str(mapping['absolute_episode']),request.get('anime_status') or '', 'tv',season=mapping.get('anime_season'),part=mapping.get('part'))
  except Exception:
   context.check();continue
  context.check()
  for source in (result or {}).get('cached',[]):
   if not isinstance(source,dict) or source.get('cached') is False or 'uncached' in str(source.get('type','')):continue
   identity=(source.get('hash'),source.get('debrid_provider'))
   if identity in seen:continue
   seen.add(identity)
   quality=source.get('quality');quality=['sd','480p','720p','1080p','4k'][quality] if isinstance(quality,int) and 0<=quality<=4 else str(quality or '').lower()
   try:size=max(0,float(source.get('byte_size') or 0))/1024**3;seeders=max(0,int(source.get('seeders') or 0))
   except (ValueError,TypeError):size=0.0;seeders=0
   # Keep the validated mapping with the native payload so resolve can check it again after an asynchronous hop.
   payload=json.loads(json.dumps({'source':source,'request':request},default=lambda value:list(value) if isinstance(value,(set,tuple)) else str(value)))
   out.append({'name':str(source.get('release_title') or request.get('show_title') or ''),'quality':quality,'size':size,'seeders':seeders,
    'torrent_hash':str(source.get('hash') or ''),'resolver':payload,'cached':True,'media_type':'episode'})
 return out


def resolve(candidate,context):
 context.check();payload=candidate.get('resolver') or {};request=payload.get('request') or {}
 mapping=_verified(request,context);source=payload.get('source')
 if mapping is None or not isinstance(source,dict) or source.get('cached') is False or source.get('type')!='torrent':return None
 apis={'Alldebrid':('all_debrid','AllDebrid'),'Real-Debrid':('real_debrid','RealDebrid'),
  'Premiumize':('premiumize','Premiumize'),'TorBox':('torbox','TorBox'),'EasyDebrid':('easydebrid','EasyDebrid'),
  'Debrid-Link':('debrid_link','DebridLink')}
 api=apis.get(source.get('debrid_provider'))
 if api is None:return None
 module=context.import_module('resources.lib.debrid.'+api[0]);resolver=getattr(module,api[1])()
 hash_=str(source.get('hash') or '')
 if not hash_:return None
 link=resolver.resolve_single_magnet(hash_,'magnet:?xt=urn:btih:'+hash_,str(mapping['absolute_episode']),False,source.get('filename'))
 context.check()
 if isinstance(link,str) and '|' in link:
  url,headers=link.split('|',1);return {'url':url,'headers':dict(parse_qsl(headers))}
 return link
