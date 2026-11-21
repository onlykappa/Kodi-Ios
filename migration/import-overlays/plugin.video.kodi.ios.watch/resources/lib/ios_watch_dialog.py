"""Deck-style "How would you like to watch?" chooser inside TMDb Helper's movie/episode resolver; no autoplay."""
# Owner (build 224): "Download or Stream" in place of the add-on names. The second line says what each one does.
ICON_DIR='special://skin/extras/icons/'
ROW_TILE={'elementum':('FF1F6FEB','cloud-arrow-down.png'),'umbrella':('FF7D3CFF','circle-play.png')}
ROW_DETAIL={'play':{False:''},'elementum':{True:'Not available on this iPhone yet'},'umbrella':{True:'Coming soon'}}
NOT_READY={'elementum':('Elementum not available','Elementum is not installed or is switched off in this build. Check Add-ons > Video add-ons > Elementum.'),
           'umbrella':('Umbrella not available yet','Umbrella has not been ported to this iPhone build yet. It will appear here once it is.')}

def share_details(player,window=None):
 """Leave this title's poster, background, year/runtime and plot on the Home window for Elementum's "Choose a
 version" page (deck_picker.py reads them back when the title matches and they are recent), as the Deck did."""
 import time
 try:
  details=player.details;info=getattr(details,'infolabels',None) or {};art=getattr(details,'art',None) or {}
  is_tv=getattr(player,'tmdb_type',None)=='tv'
  title=(info.get('tvshowtitle') if is_tv else None) or info.get('title') or info.get('originaltitle') or ''
  bits=[]
  if is_tv and info.get('season') not in (None,'') and info.get('episode') not in (None,''):bits.append('S%02dE%02d'%(int(info.get('season')),int(info.get('episode'))))
  if info.get('year'):bits.append(str(info.get('year')))
  try:minutes=int(float(info.get('duration') or 0))//60
  except (TypeError,ValueError):minutes=0
  if minutes>0:bits.append('%d min'%minutes)
  poster=(art.get('tvshow.poster') if is_tv else None) or art.get('poster') or ''
  fanart=art.get('fanart') or art.get('tvshow.fanart') or art.get('landscape') or ''
  if window is None:
   import xbmcgui
   window=xbmcgui.Window(10000)
  for key,value in (('Title',title),('Poster',poster),('Fanart',fanart),('Meta','  |  '.join(bits)),('Plot',info.get('plot') or ''),('Time',str(time.time()))):
   window.setProperty('Deck.Picker.'+key,str(value))
 except Exception as error:_quiet('ios_watch_dialog:26',error)

RESUME_PROPERTY='KodiIOS.Resume.Source'

class DownloadLookupError(Exception):pass

def continuing(argv=None):
 """True when TMDb Helper was started from a Continue Watching link (ios_continue.CONTINUE_FLAG)."""
 import sys
 argv=sys.argv if argv is None else argv
 return len(argv)>2 and 'ios_continue=1' in str(argv[2]).lstrip('?').split('&')

NEXT_PROPERTY='KodiIOS.Next.Source'   # ISSUE-331: deck_picker.next_wanted reads it

def following(argv=None):
 """ISSUE-331: the Continue Watching key of the episode Next Episode was pressed on (ios_next=<key>), or ''."""
 import sys
 from urllib.parse import parse_qs
 argv=sys.argv if argv is None else argv
 if len(argv)<=2:return ''
 return (parse_qs(str(argv[2]).lstrip('?')).get('ios_next') or [''])[0]

def downloaded_item(player,candidates,find=None,folders=None,cloud=False):
 """A TMDb Helper local player item for the downloaded copy of this title, or None."""
 try:
  import copy
  import ios_downloaded as d
  info=getattr(player.details,'infolabels',{}) or {}
  movie=getattr(player,'tmdb_type','')=='movie'
  title=info.get('title') if movie else (info.get('tvshowtitle') or info.get('title'))
  args=('movie' if movie else 'episode',title,info.get('year') or '',getattr(player,'season','') or '',getattr(player,'episode','') or '')
  copy_info={'path':find((folders or d.folders)(),*args),'source':'local'} if find else d.completed_copy(*args,cloud=cloud)
  path=(copy_info or {}).get('path')
  try:
   import xbmc;xbmc.log('Kodi iOS watch: completed-copy check (%s): %s'%(args[0],copy_info['source'] if path else 'none'),xbmc.LOGINFO)
  except ImportError:pass
  if not path:return None
  local=next((p for p in candidates if getattr(p,'is_local',False)),None)
  if local is not None:item=copy.copy(local)
  else:
   from tmdbhelper.lib.player.dialog.item.kodi import PlayerItemLocalMovie,PlayerItemLocalEpisode
   # PlayerResolver reads item.details: a bare {'tmdb': ...} dict cannot produce its playback ListItem.
   item=(PlayerItemLocalMovie if movie else PlayerItemLocalEpisode)(item=player.dictionary)
  # TMDb Helper's cached properties live in the instance, so these replace its library lookup.
  item.__dict__.update(kodi_file=path,kodi_file_contents=None,actions=path,is_valid=True,make_playlist=False,
                       ios_download_source=copy_info['source'])
  return item
 except Exception as error:
  try:
   import xbmc;xbmc.log('Kodi iOS watch: completed-copy check failed: '+type(error).__name__,xbmc.LOGWARNING)
  except Exception as error:_quiet('ios_watch_dialog:66',error)
  raise DownloadLookupError('Could not verify a completed copy') from error

def choosing(player=None,argv=None):
 """True when the owner asked to pick the source (long press › Choose source / Choose player): no saved player,
 no automatic completed copy, always the menu. Owner bug: those entries fell back to the resume question and the
 saved pick, so "choosing" never offered a choice."""
 import sys
 argv=sys.argv if argv is None else argv
 flag=len(argv)>2 and 'ios_choose=1' in str(argv[2]).lstrip('?').split('&')
 return flag or bool(getattr(player,'ignore_default',False))

def choose_player(player):
 import xbmc,xbmcgui,xbmcaddon,xbmcvfs
 player.allow_playlist=False
 home=xbmcgui.Window(10000);home.clearProperty(RESUME_PROPERTY);home.clearProperty(NEXT_PROPERTY)
 resume=continuing()
 if getattr(player,'_ios_copy_selected',False):
  xbmcgui.Dialog().ok('Downloaded copy','The completed copy could not be opened. Check the file or Drive connection. No replacement download was started.')
  return None
 if getattr(player,'_ios_resume_selected',False):
  xbmcgui.Dialog().ok('Continue Watching','The saved playback could not be opened. Try again or use Choose source. No new download was started.')
  return None
 details=player.details;art=getattr(details,'art',{}) or {};info=getattr(details,'infolabels',{}) or {}
 settings=xbmcaddon.Addon('plugin.video.kodi.ios.watch')
 candidates=list(player.player_items.items_play)
 def installed(addon):return xbmc.getCondVisibility('System.AddonIsEnabled('+addon+')')
 rows=[]
 engine=next((p for p in candidates if p.file=='ios.elementum.json'),None)
 if engine and installed('plugin.video.elementum') and settings.getSettingBool('offer_elementum'):rows.append(('Download','play',engine))
 else:rows.append(('Download — not available on iPhone yet','elementum',None))
 # Owner (build 224): the two ways are called what they do: Download (Elementum: a torrent that can save to Google Drive)
 # and Stream (Umbrella: a link from AllDebrid), not by their add-on names.
 # Any TMDb Helper player for Umbrella is offered once the add-on is installed, as on the Deck.
 umbrella=next((p for p in candidates if 'umbrella' in str(p.file).lower()),None)
 if umbrella and installed('plugin.video.umbrella'):rows.append(('Stream','play',umbrella))
 else:rows.append(('Stream — coming soon','umbrella',None))
 # Google Drive is not offered here: Elementum plays Drive-backed sources itself.
 for p in candidates:
  if p.is_local and p.kodi_file and xbmcvfs.exists(p.kodi_file):rows.append(('Local library file','play',p))
 def read(path):
  f=xbmcvfs.File(path)
  try:return f.read()
  finally:f.close()
 def write(path,text):
  xbmcvfs.mkdirs(path.rsplit('/',1)[0]);f=xbmcvfs.File(path,'w')
  try:f.write(text)
  finally:f.close()
 kind_of=lambda item:'elementum' if item is engine else 'umbrella' if item is umbrella else 'local'
 if choosing(player):
  # Asked to choose: offer the completed copy as one of the rows instead of playing it automatically.
  resume=False
  try:copy=downloaded_item(player,candidates,cloud=True)
  except DownloadLookupError:copy=None
  if copy is not None:rows.insert(0,('Downloaded copy','play',copy));kind_of=(lambda item,old=kind_of:getattr(item,'ios_download_source','local') if item is copy else old(item))
  xbmc.log('Kodi iOS watch: choose source asked; offering %d options'%len(rows),xbmc.LOGINFO)
 after='' if choosing(player) else following()
 # A finished download on the phone plays at once (owner build-132: Home fetched the torrent again).
 # Roadmap 2.8: every way in also finds a Drive copy (saved listing only, no wait), not just Continue Watching.
 try:downloaded=None if choosing(player) else downloaded_item(player,candidates,cloud=True if resume else 'cached')
 except DownloadLookupError:
  # ISSUE-299 (owner log beee3eba, build 442: Continue Watching did nothing twice, "completed-copy check failed: SignedOut"):
  # Google Drive being signed out must not stop a stream. Without a usable copy it plays from its saved player as before.
  # Elementum still stops (it would download a second time); a stream carries on.
  xbmc.log('Kodi iOS watch: completed copies could not be checked; a stream carries on without a copy',xbmc.LOGWARNING)
  downloaded=None;lookup_failed=True
 else:lookup_failed=False
 if downloaded is not None:
  player._ios_copy_selected=True
  source=getattr(downloaded,'ios_download_source','local')
  xbmc.log('Kodi iOS watch: playing a completed %s copy; provider selection skipped'%source,xbmc.LOGINFO)
  try:
   import ios_library;ios_library.mark_open(source+' copy')
  except Exception as error:_quiet('ios_watch_dialog:mark',error)
  try:
   from ios_continue import record
   record(player,read,write,choice=source,preserve_player=True)
  except Exception as error:_quiet('ios_watch_dialog:132',error)
  return downloaded
 # Continue Watching (its links carry the flag): the player and version picked last time, without asking.
 saved={}
 if resume:
  try:
   from ios_continue import player_key,saved_choice
   saved=saved_choice(read,player_key(player))
  except Exception:
   xbmcgui.Dialog().ok('Continue Watching','The saved player could not be read. Try again or use Choose source.');return None
 elif after:
  # ISSUE-331: Next Episode: the player the previous episode used, and its quality for the version page to match.
  try:
   from ios_continue import saved_choice
   saved=saved_choice(read,after)
  except Exception:saved={}
  if saved.get('player') not in ('umbrella','elementum'):saved={}
  version=saved.pop('version',None) or {}
  if saved and version.get('quality'):
   import json,time
   home.setProperty(NEXT_PROPERTY,json.dumps({'quality':version['quality'],'size':version.get('size') or 0,'time':time.time(),
                                              'tmdb':str(getattr(player,'tmdb_id','') or ''),'season':str(getattr(player,'season','') or ''),
                                              'episode':str(getattr(player,'episode','') or '')}))
  xbmc.log('Kodi iOS watch: next episode with %s%s'%(saved.get('player') or 'a choice',' at '+version['quality'] if saved and version.get('quality') else ''),xbmc.LOGINFO)
 selected=next((n for n,(_,action,item) in enumerate(rows) if action=='play' and saved.get('player')==kind_of(item)),None)
 if resume and selected is None and saved.get('player'):
  xbmcgui.Dialog().ok('Continue Watching','The previous player or completed copy is unavailable. Use Choose source to change it. No new download was started.')
  return None
 if selected is None:
  items=[]
  for label,action,item in rows:
   li=xbmcgui.ListItem(label=label,label2=ROW_DETAIL.get(action,{}).get(item is None,''));li.setArt(art)
   # Download and Stream get coloured tiles (the picker's approved look); other rows stay plain.
   tile=ROW_TILE.get(kind_of(item) if item is not None else action)
   if tile:li.setProperty('tint',tile[0]);li.setProperty('glyph',ICON_DIR+tile[1])
   items.append(li)
  name=str(info.get('title') or info.get('tvshowtitle') or '')
  selected=sheet_choice(rows,kind_of,art,info,name)
  if selected is None:selected=xbmcgui.Dialog().select('How would you like to watch'+(' '+name if name else '')+'?',items)
 # Owner logs (build-124): TMDb Helper reported "lib.player - Failure!" right after a row was tapped, i.e. this
 # returned nothing. Say what was offered and what came back, so the next log shows which way it went.
 log=lambda text:xbmc.log('Kodi iOS watch: '+text,xbmc.LOGINFO)
 log('offered %s; picked %s'%([label for label,_,_ in rows],selected))
 if selected<0 or selected>=len(rows):log('nothing picked (the menu closed without a row)');return None
 _,action,item=rows[selected]
 if lookup_failed and kind_of(item)=='elementum':
  xbmcgui.Dialog().ok('Check downloaded copy','Completed downloads could not be checked. Try again before starting another download.')
  return None
 if action in NOT_READY:
  log('%s is not available here'%action);xbmcgui.Dialog().ok(*NOT_READY[action]);return None
 if resume:player._ios_resume_selected=True
 if saved.get('version') and saved.get('player')==kind_of(item):
  # deck_picker.py (Elementum's and Umbrella's version page) takes this once and plays the same version.
  import json,time
  home.setProperty(RESUME_PROPERTY,json.dumps(dict(saved['version'],time=time.time())))
 try:
  # Continue Watching: remember what was started (the bootstrap service follows its progress).
  from ios_continue import record
  record(player,read,write,choice=kind_of(item))
 except Exception as error:_quiet('ios_watch_dialog:169',error)
 if item is engine:share_details(player)
 log('playing with %s (%s)'%(kind_of(item),getattr(item,'file','')))
 try:
  import ios_library;ios_library.mark_open(kind_of(item))
 except Exception as error:_quiet('ios_watch_dialog:mark',error)
 return item

SHEET_DETAIL={'elementum':'Saved to Google Drive \u00b7 watch any time','umbrella':'Plays now from your AllDebrid account',
              'drive':'Already on your Google Drive','local':'Already on this iPhone'}
def sheet_choice(rows,kind_of,art,info,name):
 """Owner-approved choice sheet (mockup board 13): the title's art with its kind and name, then Download and Stream
 as rows with their tiles and what each does. None when the sheet is not available (Kodi's box is used)."""
 try:
  import choice_sheet_loader
  sheet=choice_sheet_loader.load()
 except Exception:sheet=None
 if sheet is None:return None
 tv=bool(info.get('tvshowtitle')) and info.get('mediatype')!='movie'
 badge='EPISODE' if tv else 'MOVIE'
 if tv and info.get('season') not in (None,'') and info.get('episode') not in (None,''):
  try:badge+=' \u00b7 S%d E%d'%(int(info.get('season')),int(info.get('episode')))
  except (TypeError,ValueError):pass
 elif info.get('year'):badge+=' \u00b7 %s'%info.get('year')
 spec={'art':art.get('fanart') or art.get('tvshow.fanart') or art.get('landscape') or art.get('thumb') or '',
       'badge':badge,'art_title':(info.get('tvshowtitle') if tv else name) or name,'sub':'How would you like to get it?','rows':[]}
 for label,action,item in rows:
  kind=kind_of(item) if item is not None else action
  tile=ROW_TILE.get(kind)
  detail=ROW_DETAIL.get(action,{}).get(item is None,'') or SHEET_DETAIL.get(kind,'')
  if detail and ' \u2014 ' in label:label=label.split(' \u2014 ')[0]   # the line under it says why
  spec['rows'].append({'label':label,'detail':detail,'tint':tile[0] if tile else '','glyph':ICON_DIR+tile[1] if tile else ''})
 if not spec['art']:spec['heading']=name
 try:return sheet.choose(spec,path=getattr(sheet,'HOME',None))
 except Exception as error:
  _quiet('sheet_choice',error);return None

def _quiet(where,error,_seen=set()):
 """Log an error that is deliberately not shown on screen, once per place and kind (loops run every second)."""
 key=(where,type(error).__name__)
 if key in _seen:return
 _seen.add(key)
 try:
  import re,xbmc;text=re.sub(r'(?i)\b(?:https?|plugin|ftp|smb)://\S+|magnet:\?\S+','[URL redacted]',str(error))[:200];xbmc.log('Kodi iOS %s: %s: %s'%(where,type(error).__name__,text),xbmc.LOGWARNING)
 except Exception:pass

def title_for(tmdb_type,tmdb_id,art_cache):
 """(title, year) for a TMDb id from the Library's saved art (drive-library-art.json), no network; None if unknown."""
 kind='tv' if tmdb_type=='tv' else 'movie'
 for slot,value in (art_cache or {}).items():
  if not isinstance(value,dict) or str(value.get('tmdb_id') or '')!=str(tmdb_id):continue
  parts=slot.split(':')
  if len(parts)>=3 and parts[0]==kind and parts[1]:return parts[1],parts[2]
 return None

def count_run(name):
 """Roadmap 3.5: one more list run of TMDb Helper for the one-minute performance line (perf_summary.py)."""
 try:
  import xbmcgui
  window=xbmcgui.Window(10000);key='KodiIOS.Count.'+name
  window.setProperty(key,str(int(window.getProperty(key) or 0)+1))
 except Exception:pass

def warm_details(params,details_class=None):
 """Roadmap 1C.4: TMDb Helper's route info=ios_warm. Builds the details Play will ask for, with the same arguments, so
 TMDb Helper's own cache answers when Play is tapped. Quiet on any failure; nothing is played or shown."""
 tmdb_type=params.get('tmdb_type');tmdb_id=str(params.get('tmdb_id') or '')
 if tmdb_type not in ('movie','tv') or not tmdb_id.isdigit():return False
 try:
  if details_class is None:
   from tmdbhelper.lib.player.dialog.details import PlayerDetails as details_class
  season,episode=str(params.get('season') or ''),str(params.get('episode') or '')
  details_class(tmdb_type,tmdb_id,season if season.isdigit() else None,episode if episode.isdigit() else None).details
  return True
 except Exception as error:
  _quiet('ios_watch_dialog:warm',error)
  return False

def continue_position(kind,tmdb_id,season,episode,read=None):
 """(position, total) saved for this title in Continue Watching, or (0, 0)."""
 try:
  import ios_continue
  if read is None:
   import xbmcvfs
   def read(location):
    source=xbmcvfs.File(location)
    try:return source.read()
    finally:source.close()
  entry=ios_continue.load(read)['items'].get(ios_continue.key({'kind':kind,'tmdb_id':tmdb_id,'season':season,'episode':episode})) or {}
  return float(entry.get('position') or 0),float(entry.get('total') or 0)
 except Exception:
  return 0,0

def fast_copy(handle,params,read_art=None,find=None,play=None,resume=None):
 """A copy on the phone or Drive plays first (_fast_local); failing that, an Umbrella title being continued resumes from the link it was playing (fast_stream)."""
 if _fast_local(handle,params,read_art,find,play,resume):return True
 return fast_stream(handle,params)

def _fast_local(handle,params,read_art=None,find=None,play=None,resume=None):
 """Roadmap 1C.2 (owner logs: 1.4-2.1 s in TMDb Helper before a downloaded copy played): Next Episode, spotlight
 Play, show pages and Continue Watching play a copy already on the phone or Drive before TMDb Helper fetches details
 and builds its players. Only from saved data (art cache, saved Drive listing). Owner log 20b1ca76 (build 284): a
 downloaded movie from Continue Watching took 8.8 s, 2 s of it in TMDb Helper and 5.8 s through the Google Drive
 add-on; it now resumes from its saved place through the app's own Drive proxy (ios_library.play_downloaded asks
 Continue or Start over). Choose source keeps the full path (its choice logic lives there). True when it played."""
 if params.get('ios_choose')=='1':return False
 tmdb_type=params.get('tmdb_type');tmdb_id=str(params.get('tmdb_id') or '')
 if tmdb_type not in ('movie','tv') or not tmdb_id.isdigit():return False
 season,episode=str(params.get('season') or ''),str(params.get('episode') or '')
 if tmdb_type=='tv' and not (season.isdigit() and episode.isdigit()):return False
 try:
  if read_art is None:
   import json,os,xbmcvfs
   path=os.path.join(xbmcvfs.translatePath('special://profile/addon_data/service.kodi.ios.bootstrap/'),'drive-library-art.json')
   read_art=lambda:json.load(open(path,encoding='utf-8')) if os.path.exists(path) else {}
  known=title_for(tmdb_type,tmdb_id,read_art())
  if not known:return False
  title,year=known
  kind='movie' if tmdb_type=='movie' else 'episode'
  if find is None:
   import ios_downloaded
   find=lambda *a:ios_downloaded.completed_copy(*a,cloud='cached')
  copy=find(kind,title,year,season,episode)
  path=(copy or {}).get('path')
  if not path:return False
  values={'path':path,'title':title,'show':'' if kind=='movie' else title,'kind':kind,'year':year,
          'ask':'1' if kind=='movie' else '0','season':season or '0','episode':episode or '0','tmdb_id':tmdb_id}
  if params.get('ios_continue')=='1':
   position,total=(resume or continue_position)(kind,tmdb_id,season,episode)
   values.update(resume=position,total=total)
  if play is None:
   import ios_library
   play=ios_library.play_downloaded
  play(handle if handle is not None else -1,values)
  try:
   import xbmc;xbmc.log('Kodi iOS watch: fast path played a %s copy of %s (TMDb Helper skipped)'%(copy.get('source'),kind),xbmc.LOGINFO)
  except ImportError:pass
  return True
 except Exception as error:
  _quiet('ios_watch_dialog:fast_copy',error)
  return False

STREAM_FRESH=4*3600   # seconds a remembered Umbrella link is tried again (a debrid link lives for hours; the check below says when it does not)

def _link_alive(url,timeout=3):
 """True when the remembered link still answers a one-byte ranged read. Nothing of the address reaches the log."""
 import urllib.request,urllib.parse
 address,_,tail=url.partition('|');headers={'Range':'bytes=0-0'}
 headers.update({k:v for k,v in urllib.parse.parse_qsl(tail)})   # Kodi's own `|Header=value` suffix
 try:
  with urllib.request.urlopen(urllib.request.Request(address,headers=headers),timeout=timeout) as answer:
   return answer.status in (200,206)
 except Exception:return False

def _opening_kept(url):
 """True when the service has this link's opening on the phone."""
 try:
  import xbmcvfs,ios_library
  ios_library.boot_path(xbmcvfs)
  import resume_cache
  return resume_cache.ready(url)
 except Exception:return False

def _cache_route(url,resume=None):
 """The service's cache address for a remembered Umbrella link, or the link itself."""
 try:
  import xbmcgui,xbmcvfs,ios_library
  ios_library.boot_path(xbmcvfs)
  import remote_media
  return remote_media.for_kodi(url,xbmcgui.Window(10000),resume=resume)
 except Exception as error:
  _quiet('ios_watch_dialog:cache_route',error)
  return url

def fast_stream(handle,params,read=None,alive=None,play=None,now=None,route=None):
 """Continue an Umbrella title from the link it was playing, without asking TMDb Helper or Umbrella again (owner, build 618: continuing a show still took
 15 s: details 2 s, Umbrella 3 s, resolving 2 s, the cache wait 2 s and the server's slow start). Only when Continue started it (ios_continue), the video was
 last played through Umbrella within STREAM_FRESH, there is a place to resume and the link still answers; otherwise the normal way runs, as before."""
 if params.get('ios_continue')!='1' or params.get('ios_choose')=='1':return False
 tmdb_type=params.get('tmdb_type');tmdb_id=str(params.get('tmdb_id') or '')
 if tmdb_type not in ('movie','tv') or not tmdb_id.isdigit():return False
 season,episode=str(params.get('season') or ''),str(params.get('episode') or '')
 if tmdb_type=='tv' and not (season.isdigit() and episode.isdigit()):return False
 try:
  import time,ios_continue
  now=now or time.time
  if read is None:
   import xbmcvfs
   def read(location):
    source=xbmcvfs.File(location)
    try:return source.read()
    finally:source.close()
  kind='movie' if tmdb_type=='movie' else 'episode'
  data=ios_continue.load(read);item_key=ios_continue.key({'kind':kind,'tmdb_id':tmdb_id,'season':season,'episode':episode})
  entry=data['items'].get(item_key) or {}
  stream=entry.get('stream') or {};url=str(stream.get('url') or '')
  if entry.get('player')!='umbrella' or not url.startswith(('http://','https://')):return False
  if now()-float(stream.get('at') or 0)>STREAM_FRESH:return False
  position,total=float(entry.get('position') or 0),float(entry.get('total') or 0)
  if position<5 or (total and position>=0.92*total):return False   # nothing to resume: the normal way finds a fresh link
  if not (alive or _link_alive)(url):return False
  # Step 2 (owner, build 620 log 80ea6c76: Continue took 12.3 s to the first picture; Kodi read the debrid link itself over one connection: 2.8 s to
  # connect, 5.1 s for the file's start, 3.6 s for the resume seek). Umbrella's own path hands Kodi the service's cache (several connections, the
  # start, the end and now the resume point asked for at once: remote_media.for_kodi); Continue skipped Umbrella and with it the cache. It uses it
  # too now; when the cache does not answer in time the link itself is played, as before.
  # Build 622 (log ac85bba1) undid this by default: on that debrid link the cache had 1 of its 3 opening blocks after 2 s, handed Kodi the link with
  # 9 of its 40 reads still running, and the server then refused Kodi's own range request ("Requested range was not delivered"): the open failed.
  # Continue plays the remembered link directly again (build 620: 12.3 s, and it played). `route` stays for tests and a later, safer try.
  # Build 623 log 8c570737 (a second Continue took as long as the first, 10.7 s against 11.3 s): when the opening of this very link is already on the phone
  # (resume_cache, saved when the stream last stopped) the cache route is used: Kodi's open and its resume seek are answered from disk. Otherwise the link
  # plays directly, as in build 620 (the cache's race against a slow debrid server is what failed in build 622).
  if route is None and _opening_kept(url):route=_cache_route
  if route is not None:url=route(url,position/total if total else None)
  if play is None:
   import ios_library
   play=ios_library.play_stream
  play(handle if handle is not None else -1,entry,url,position,total)
  try:
   import xbmc,xbmcvfs
   xbmc.log('Kodi iOS watch: continued %s from its last Umbrella link (Umbrella skipped)'%kind,xbmc.LOGINFO)
   def write(location,text):
    target=xbmcvfs.File(location,'w')
    try:target.write(text)
    finally:target.close()
   data['current']=item_key;ios_continue.save(data,write)   # the progress tracker follows this title
  except ImportError:pass
  return True
 except Exception as error:
  _quiet('ios_watch_dialog:fast_stream',error)
  return False
