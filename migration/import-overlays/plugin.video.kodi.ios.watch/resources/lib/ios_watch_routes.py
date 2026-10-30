"""Pure route building. No network, Kodi calls, credential access or autoplay."""
from urllib.parse import urlencode,urlsplit,parse_qs
ID='plugin.video.kodi.ios.watch'
HELPER='plugin.video.themoviedb.helper'

def media_request(params):
 kind=params.get('kind');tmdb=str(params.get('tmdb_id',''))
 if kind not in {'movie','tvshow','episode'} or not tmdb.isdecimal():raise ValueError('Unsupported media request')
 if kind=='episode':
  for key in ['season','episode']:
   if not str(params.get(key,'')).isdecimal():raise ValueError('Episode coordinates required')
 if kind=='tvshow':
  u=urlsplit(params.get('browse',''));q=parse_qs(u.query)
  if u.scheme!='plugin' or u.netloc!=HELPER or q.get('info',[''])[0] not in {'seasons','flatseasons','episodes','flatepisodes','details'}:raise ValueError('Untrusted episode navigation URL')
 return params

def wrap_item(item,original):
 # Like the Deck: a show opens its seasons; the player choice comes when an episode or movie is played,
 # inside TMDb Helper's resolver (ios_watch_dialog.choose_player).
 return original

def wrap_item_r1(item,original):
 """Earlier routing that sent shows through a watch-options folder; kept for old plugin:// links."""
 kind=getattr(item,'mediatype',None)
 if kind!='tvshow' or urlsplit(original).netloc!=HELPER:return original
 args=getattr(item,'params',{})
 if args.get('info') not in {'play','seasons','flatseasons','episodes','flatepisodes','details'}:return original
 tmdb=args.get('tmdb_id') or getattr(item,'unique_ids',{}).get('tmdb')
 params={'kind':kind,'tmdb_id':str(tmdb or ''),'title':getattr(item,'label','')}
 if kind=='tvshow':params['browse']=original
 if kind=='episode':params.update(season=str(args.get('season','')),episode=str(args.get('episode','')))
 for key in ['poster','fanart','thumb']:
  art=getattr(item,'art',{}).get(key)
  if art:params[key]=art
 try:media_request(params)
 except ValueError:return original
 item.is_folder=True;item.infoproperties['isPlayable']='false'
 return 'plugin://'+ID+'/?'+urlencode(params)

def choices(params,elementum_test_ready=False):
 media_request(params);kind=params['kind'];id=params['tmdb_id']
 entries=[]
 if kind=='tvshow':
  entries.append({'label':'Browse episodes','url':params['browse'],'folder':True,'action':'episodes'})
 elif elementum_test_ready:
  path=f'movie/{id}/forcelinks' if kind=='movie' else f"show/{id}/season/{params['season']}/episode/{params['episode']}/forcelinks"
  entries.append({'label':'Elementum — select source (native test)','url':'plugin://plugin.video.elementum/'+path,'folder':False,'action':'elementum'})
 else:entries.append({'label':'Elementum — iOS engine not integrated','url':'plugin://'+ID+'/?action=engine_status','folder':True,'action':'engine_status'})
 entries.append({'label':'Browse Google Drive separately','url':'plugin://plugin.googledrive/','folder':True,'action':'drive'})
 return entries
