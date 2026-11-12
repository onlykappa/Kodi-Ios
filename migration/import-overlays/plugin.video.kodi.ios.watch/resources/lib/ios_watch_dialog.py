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
 home=xbmcgui.Window(10000);home.clearProperty(RESUME_PROPERTY)
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
 # A finished download on the phone plays at once (owner build-132: Home fetched the torrent again).
 # Roadmap 2.8: every way in also finds a Drive copy (saved listing only, no wait), not just Continue Watching.
 try:downloaded=None if choosing(player) else downloaded_item(player,candidates,cloud=True if resume else 'cached')
 except DownloadLookupError:
  xbmcgui.Dialog().ok('Check downloaded copy','Completed downloads could not be checked. Try again before starting another download.')
  return None
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

def fast_copy(handle,params,read_art=None,find=None,play=None):
 """Roadmap 1C.2 (owner logs: 1.4-2.1 s in TMDb Helper before a downloaded copy played): Next Episode, spotlight
 Play and show pages play a copy already on the phone or Drive before TMDb Helper fetches details and builds its
 players. Only from saved data (art cache, saved Drive listing); Continue Watching and Choose source keep the full
 path (their resume and choice logic lives there). True when it played."""
 if params.get('ios_continue')=='1' or params.get('ios_choose')=='1':return False
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
