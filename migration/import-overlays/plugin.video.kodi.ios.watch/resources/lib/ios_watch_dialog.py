"""Deck-style "How would you like to watch?" chooser inside TMDb Helper's movie/episode resolver; no autoplay."""
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
 except Exception:pass

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
  except Exception:pass
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
 if engine and installed('plugin.video.elementum') and settings.getSettingBool('offer_elementum'):rows.append(('Elementum','play',engine))
 else:rows.append(('Elementum — not available on iPhone yet','elementum',None))
 # Any TMDb Helper player for Umbrella is offered once the add-on is installed, as on the Deck.
 umbrella=next((p for p in candidates if 'umbrella' in str(p.file).lower()),None)
 if umbrella and installed('plugin.video.umbrella'):rows.append(('Umbrella','play',umbrella))
 else:rows.append(('Umbrella — coming soon','umbrella',None))
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
 try:downloaded=None if choosing(player) else downloaded_item(player,candidates,cloud=resume)
 except DownloadLookupError:
  xbmcgui.Dialog().ok('Check downloaded copy','Completed downloads could not be checked. Try again before starting another download.')
  return None
 if downloaded is not None:
  player._ios_copy_selected=True
  source=getattr(downloaded,'ios_download_source','local')
  xbmc.log('Kodi iOS watch: playing a completed %s copy; provider selection skipped'%source,xbmc.LOGINFO)
  try:
   from ios_continue import record
   record(player,read,write,choice=source,preserve_player=True)
  except Exception:pass
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
   li=xbmcgui.ListItem(label=label);li.setArt(art);items.append(li)
  name=str(info.get('title') or info.get('tvshowtitle') or '')
  selected=xbmcgui.Dialog().select('How would you like to watch'+(' '+name if name else '')+'?',items)
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
 except Exception:pass
 if item is engine:share_details(player)
 log('playing with %s (%s)'%(kind_of(item),getattr(item,'file','')))
 return item
