"""Long press › Download (context menu), and Download on a show's seasons page (RunScript with key=value args)."""
import os,sys
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'resources','lib'))
import elementum_download as dl,elementum_engine,notices

def owned_copy(kind,title,year='',season='',episode=''):
 """The completed phone or Drive copy of this movie/episode (ios_downloaded.completed_copy, as Continue Watching
 uses), or None. A failed check never blocks a download."""
 if not title:return None
 try:
  import xbmc,xbmcaddon,xbmcvfs
  lib=os.path.join(xbmcvfs.translatePath(xbmcaddon.Addon('plugin.video.kodi.ios.watch').getAddonInfo('path')),'resources','lib')
  if lib not in sys.path:sys.path.append(lib)
  import ios_downloaded
  return ios_downloaded.completed_copy(kind,title,year,season,episode,cloud=True)
 except Exception as error:
  try:xbmc.log('Kodi iOS download: duplicate check skipped (%s)'%type(error).__name__,xbmc.LOGWARNING)
  except Exception:pass
  return None

def run():
 import xbmc,xbmcgui
 args=dict(a.split('=',1) for a in sys.argv[1:] if '=' in a)
 item=getattr(sys,'listitem',None)
 values=dict(args);path=args.get('path','')
 if item is not None:
  tag=item.getVideoInfoTag();kind=tag.getMediaType() or args.get('kind','')
  path=path or item.getPath()
  values.update({'tmdb':item.getUniqueID('tmdb'),'tvshow.tmdb_id':item.getProperty('tvshow.tmdb_id'),
                 'season':str(tag.getSeason()) if tag.getSeason()>0 else '','episode':str(tag.getEpisode()) if tag.getEpisode()>0 else ''})
  values.setdefault('title',(tag.getTVShowTitle() if kind in ('episode','season','tvshow') else '') or tag.getTitle())
  values.setdefault('year',str(tag.getYear() or ''))
 else:kind=args.get('kind','')
 dialog=xbmcgui.Dialog()
 tmdb,season,episode=dl.ids(kind,path,values)
 if not tmdb:dialog.ok('Download','This item has no TMDb id, so Elementum cannot look it up.');return
 if kind=='tvshow':
  # ISSUE-162: the iPhone keyboard, not the skin's number pad.
  season=(dialog.input('Download which season?',season or '1',type=xbmcgui.INPUT_ALPHANUM) or '').strip()
  if not season or not season.isdigit():return
  kind='season'
 if kind in ('season','episode') and not season:dialog.ok('Download','Could not tell which season this is.');return
 title,year=values.get('title',''),values.get('year','')
 if kind=='season':
  # Owner-approved season picker (mockup round 3): the show and season as the heading, each choice with a line under it.
  rows=[('[B]Full season[/B]','Every aired episode, in one quality'),('[B]Choose episodes\u2026[/B]','Pick the ones you want'),
        ('[B]Follow new episodes[/B]','Each one downloads when it comes out')]
  heading='%s \u00b7 Season %s'%(values.get('title') or 'Download',season)
  try:
   import choice_sheet
   pick=choice_sheet.choose({'heading':heading,'rows':[{'label':n.replace('[B]','').replace('[/B]',''),'detail':d} for n,d in rows]},xbmcgui=xbmcgui)
  except Exception as error:
   xbmc.log('Kodi iOS download: season sheet unavailable (%s)'%type(error).__name__,xbmc.LOGWARNING)
   pick=dialog.select(heading,[xbmcgui.ListItem(label=n,label2=d) for n,d in rows])
  if pick<0:return
  if pick==2:
   import episode_watch,xbmcvfs
   profile=xbmcvfs.translatePath('special://profile/')
   if episode_watch.register(profile,tmdb,title,season,1,episode_watch.library_preference(profile,title)):
    dialog.notification('New episodes','Show added to followed episodes.',xbmcgui.NOTIFICATION_INFO,4000)
   return
 if not elementum_engine.running():
  # Not started at launch (performance 1E.1): start it now, with the busy ring while it loads.
  xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
  try:started=elementum_engine.ensure_here()
  finally:xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
  if not started:
   dialog.ok('Download','Elementum is not running. Gear menu › Retry Elementum engine, then try again.');return
 wait=lambda:xbmc.Monitor().waitForAbort(1)
 def check(k,s='',e=''):
  # Library status › "Find a version without converting" (replace=1): the copy we have is the one being replaced.
  if args.get('replace')=='1':return None
  xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
  try:return owned_copy(k,title,year if k=='movie' else '',s,e)
  finally:xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
 def again(name,copy):
  return dialog.yesno('Already downloaded','%s is already downloaded %s. Download it again?'%(name,dl.where(copy)),nolabel='Cancel',yeslabel='Download again')
 if kind=='movie':
  copy=check('movie')
  if copy and not again('%s%s'%(title,' (%s)'%year if year else ''),copy):return
 if kind=='episode':
  copy=check('episode',season,episode)
  if copy and not again('%s · S%s E%s'%(title,season,episode),copy):return
 def start(k,e=None):
  # Every entry point shares the post-selection cloud prompt. Do not wait for a local torrent:
  # the /play or /download URI is intercepted before Elementum can add one.
  url=dl.plugin_url(k,tmdb,season,e)
  # The searching card names what is searched in the app's own words (Burst may only know the original-language
  # title, e.g. Japanese, which the app's font cannot draw): KODI-IOS-SEARCH-CARD reads these for two minutes.
  try:
   import time as _t
   home=xbmcgui.Window(10000)
   home.setProperty('IOSSearch.Name',str(title));home.setProperty('IOSSearch.NameAt',str(_t.time()))
   home.setProperty('IOSSearch.Context','Season %s · Episode %s'%(season,e) if k=='episode' else ('%s'%year if year else ''))
  except Exception:pass
  if k=='episode':
   import episode_watch
   episode_watch.canceled(xbmcgui.Window(10000),{'tmdb':tmdb,'season':season,'episode':e},clear=True)
  dl.follow(url)
 if kind=='season':
  if pick==1:
   import json
   answer=json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':'Files.GetDirectory','params':{
    'directory':dl.season_path(tmdb,season),'media':'video','properties':['episode','title']}})))
   choices=dl.episode_choices(answer.get('result',{}).get('files'))
   if not choices:dialog.ok('Download','Could not list the episodes of season %s.'%season);return
   # Owner (build-132): ticking in Fuse's multi-select did not register, so OK came back empty and the page just
   # closed. One tap now picks one episode; "Several episodes..." keeps the tick list and says when none was ticked.
   owned=[bool(check('episode',season,n)) for n,label in choices]
   labels=dl.mark_owned([label for n,label in choices],owned)
   pick=dialog.select('Season %s: which episode?'%season,labels+['Several episodes...'])
   xbmc.log('Kodi iOS download: season %s episode list, picked %s'%(season,pick),xbmc.LOGINFO)
   if pick<0:return
   if pick<len(choices):chosen=[pick]
   else:
    chosen=dialog.multiselect('Season %s: tick the episodes'%season,labels) or []
    xbmc.log('Kodi iOS download: ticked %s'%chosen,xbmc.LOGINFO)
    if not chosen:dialog.ok('Download','No episode was ticked. Tap an episode to tick it, then OK.');return
   again_chosen=[i for i in chosen if owned[i]]
   if again_chosen and not dialog.yesno('Already downloaded','%d of the chosen episodes %s already downloaded. Download %s again?'%(
     len(again_chosen),'is' if len(again_chosen)==1 else 'are','it' if len(again_chosen)==1 else 'them'),nolabel='Skip them',yeslabel='Download again'):
    chosen=[i for i in chosen if not owned[i]]
    if not chosen:return
   episodes=[choices[i][0] for i in chosen]
   # Build 206: the first is picked by hand; the others follow that pick (rest_of_season), one question.
   home=xbmcgui.Window(10000);home.clearProperty(SEASON_PICK)
   start('episode',episodes[0])
   if len(episodes)>1:
    try:pick=json.loads(home.getProperty(SEASON_PICK) or 'null')
    except ValueError:pick=None
    if pick:home.setProperty(SEASON_PICK,json.dumps(dict(pick,coverage='Episode %d only'%episodes[0])))
    rest_of_season(xbmc,xbmcgui,dialog,home,title,season,episodes,set(),lambda n:start('episode',n))
   return
  # Whole season: verify real packs first, otherwise scan aired episodes before offering quality.
  numbers=[];names={}
  import json,season_sources
  for attempt in (1,2):   # TMDb Helper can time out on its first listing of a long season; once more
   try:
    answer=json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':'Files.GetDirectory','params':{
     'directory':dl.season_path(tmdb,season),'media':'video','properties':['episode','title','firstaired','premiered']}})))
    files=answer.get('result',{}).get('files') or []
    numbers=season_sources.aired(files)
    names={int(f['episode']):f.get('title') or '' for f in files if f.get('episode')}
    xbmc.log('Kodi iOS download: season %s listing: %d rows, %d aired%s'%(season,len(files),len(numbers),
             (' (error %s)'%answer['error'].get('message','')) if answer.get('error') else ''),xbmc.LOGINFO)
   except Exception as error:
    xbmc.log('Kodi iOS download: season %s listing failed: %s'%(season,type(error).__name__),xbmc.LOGWARNING)
   if numbers:break
  owned={n for n in numbers if check('episode',season,n)}
  question=dl.season_question(season,len(owned),len(numbers)) if numbers else None
  if question and not dialog.yesno(question[0],question[1],nolabel='Cancel',yeslabel='Download'):return
  import season_sources,xbmcvfs
  profile=xbmcvfs.translatePath('special://profile/')
  if numbers and set(numbers)<=owned|season_sources.pending_episodes(profile,tmdb,season,numbers):
   dialog.ok('Download season','Every aired episode is already downloaded or queued.');return
  home=xbmcgui.Window(10000);home.clearProperty(SEASON_PICK)
  if not numbers:
   dialog.ok('Download season','No aired episodes could be verified for this season. Try refreshing the show.');return
  # Owner (2026-11-12): a season is always built from single episodes at the quality picked, never a ready-made pack
  # (season-pack-mockups boards B, C, D; season_sources.build).
  home.setProperty('IOSSeason.Poster',xbmc.getInfoLabel('ListItem.Art(tvshow.poster)') or xbmc.getInfoLabel('ListItem.Art(poster)'))
  season_sources.build(xbmc,xbmcgui,dialog,home,profile,tmdb,title,season,numbers,owned,names)
  return
 start(kind,episode)

QUALITY_NAMES={'4k':'4K','1440p':'1440p','1080p':'1080p','720p':'720p','480p':'480p','sd':'SD'}
def quality_name(q):return QUALITY_NAMES.get(str(q or '').lower(),str(q or 'SD').upper())
SEASON_PICK='KodiIOS.SeasonPick';AUTO_PICK='KodiIOS.AutoPick';AUTO_RESULT='KodiIOS.AutoPick.Result'
AUTO_SECONDS=300   # one episode's search and queueing; renewed for each

def covered(coverage):
 """The episodes an "Episode 3 only" / "Episodes 1-4 only" version holds (deck_picker / source_match.coverage)."""
 import re
 m=re.match(r'Episodes? (\d+)(?:-(\d+))? only',coverage or '')
 return set(range(int(m.group(1)),int(m.group(2) or m.group(1))+1)) if m else set()

def missing_episodes(numbers,owned,pick):
 """The season's episodes still to get after the version picked: none when it was a full season (coverage '') or
 unknown; otherwise every listed episode that is neither in that version nor already downloaded."""
 if not pick or pick.get('coverage') in (None,''):return []
 have=covered(pick['coverage'])|set(owned)
 return [n for n in numbers if n not in have]

def summary(title,season,results,quality):
 """'Lanterns season 1: 8 episodes queued in 4K' and what came at another quality or was not found."""
 got=[n for n,r in results if r.get('found')]
 other=['E%02d in %s'%(n,quality_name(r['quality'])) for n,r in results if r.get('found') and r.get('quality')!=quality]
 lost=['E%02d'%n for n,r in results if not r.get('found')]
 text='%d episode%s queued in %s'%(len(got),'' if len(got)==1 else 's',quality_name(quality))
 if other:text+=' · '+', '.join(other)
 if lost:text+=' · not found yet: '+', '.join(lost)
 return '%s season %s'%(title,season),text

def rest_of_season(xbmc,xbmcgui,dialog,home,title,season,numbers,owned,start_episode,now=None):
 """Owner (build 205): "cant it automatically pick sources based off my first quality pick?". When the version
 picked for a season held some episodes only, the others are found and queued one by one in the same quality
 (deck_picker.auto_choose picks; elementum_cloud queues without asking again)."""
 import json,time
 try:pick=json.loads(home.getProperty(SEASON_PICK) or 'null')
 except ValueError:pick=None
 home.clearProperty(SEASON_PICK)
 rest=missing_episodes(numbers,owned,pick)
 if not rest:return []
 label='%s%s'%(quality_name(pick['quality']),' · '+pick['hdr'] if pick.get('hdr') else '')
 if not dialog.yesno('Rest of season %s'%season,'That version held %s. Get the other %d episode%s automatically in the same quality (%s)?'%(
   pick['coverage'][0].lower()+pick['coverage'][1:],len(rest),'' if len(rest)==1 else 's',label),nolabel='Not now',yeslabel='Get them'):return []
 try:mode=int(home.getProperty('KodiIOS.LastSaveMode') or 0)
 except ValueError:mode=0
 progress=xbmcgui.DialogProgress();progress.create('Rest of season %s'%season,'Finding versions…')
 results=[]
 try:
  for k,n in enumerate(rest):
   if progress.iscanceled() or xbmc.Monitor().abortRequested():break
   progress.update(int(100*k/len(rest)),'Finding %s · S%02dE%02d (%d of %d)'%(title,int(season),n,k+1,len(rest)))
   home.clearProperty(AUTO_RESULT)
   home.setProperty(AUTO_PICK,json.dumps({'profile':pick,'mode':mode,'until':(now or time.time())+AUTO_SECONDS}))
   try:start_episode(n)
   except Exception as error:import diagnostics;xbmc.log('Kodi iOS download: S%sE%s automatic: %s'%(season,n,diagnostics.error_text(error)),xbmc.LOGWARNING)
   try:result=json.loads(home.getProperty(AUTO_RESULT) or '{}')
   except ValueError:result={}
   results.append((n,result))
   xbmc.log('Kodi iOS download: S%sE%s automatic: %s'%(season,n,result.get('name') or 'nothing found'),xbmc.LOGINFO)
 finally:
  home.clearProperty(AUTO_PICK);progress.close()
 if results:
  heading,text=summary(title,season,results,pick['quality'])
  notices.note('download',heading,text)
  dialog.notification(heading,text,xbmcgui.NOTIFICATION_INFO,6000)
 return results

def main():
 # Owner (build-127): after picking episodes nothing happened. Every step is logged and a failure is shown, never
 # a silent stop.
 import traceback,xbmc,xbmcgui
 try:run()
 except Exception as error:
  xbmc.log('Kodi iOS download failed: %s\n%s'%(error,traceback.format_exc()),xbmc.LOGERROR)
  xbmcgui.Dialog().ok('Download','Download could not start: %s'%error)

if __name__=='__main__':main()
