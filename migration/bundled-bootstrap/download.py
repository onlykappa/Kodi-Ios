"""Long press › Download (context menu), and Download on a show's seasons page (RunScript with key=value args)."""
import os,sys
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'resources','lib'))
import elementum_download as dl,elementum_engine,notices

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
 else:kind=args.get('kind','')
 dialog=xbmcgui.Dialog()
 tmdb,season,episode=dl.ids(kind,path,values)
 if not tmdb:dialog.ok('Download','This item has no TMDb id, so Elementum cannot look it up.');return
 if kind=='tvshow':
  season=dialog.numeric(0,'Download which season?',season or '1')
  if not season or not season.isdigit():return
  kind='season'
 if kind in ('season','episode') and not season:dialog.ok('Download','Could not tell which season this is.');return
 if not elementum_engine.running():
  dialog.ok('Download','Elementum is not running. Gear menu › Retry Elementum engine, then try again.');return
 wait=lambda:xbmc.Monitor().waitForAbort(1)
 def start(k,e=None):
  url=dl.plugin_url(k,tmdb,season,e);xbmc.log('Kodi iOS download: asking Elementum '+url,xbmc.LOGINFO)
  if k=='movie':xbmc.executebuiltin('RunPlugin(%s)'%url);return
  # Seasons and episodes: Elementum's redirects after the version page were lost with RunPlugin (owner build-133).
  def run():
   try:xbmc.log('Kodi iOS download: Elementum reached '+dl.follow(url),xbmc.LOGINFO)
   except Exception as error:
    xbmc.log('Kodi iOS download: Elementum request failed: %r'%error,xbmc.LOGWARNING)
    xbmcgui.Dialog().ok('Download','Elementum did not start the download: %s'%error)
  import threading;threading.Thread(target=run).start()   # not daemon: the script waits for it
 def watch(k,torrent=None,e=None):
  if torrent is None:return
  # Elementum shows a few seconds of buffering, then the video; the download carries on in the background.
  xbmc.executebuiltin('PlayMedia(%s)'%dl.watch_url(k,tmdb,torrent,season,e))
 def mode(labels):
  pick=dialog.select('Download',labels)
  return None if pick<0 else pick==1
 if kind=='season':
  pick=dialog.select('Download season %s'%season,['Full season','Choose episodes...'])
  if pick<0:return
  if pick==1:
   import json
   answer=json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':'Files.GetDirectory','params':{
    'directory':dl.season_path(tmdb,season),'media':'video','properties':['episode','title']}})))
   choices=dl.episode_choices(answer.get('result',{}).get('files'))
   if not choices:dialog.ok('Download','Could not list the episodes of season %s.'%season);return
   # Owner (build-132): ticking in Fuse's multi-select did not register, so OK came back empty and the page just
   # closed. One tap now picks one episode; "Several episodes..." keeps the tick list and says when none was ticked.
   labels=[label for n,label in choices]
   pick=dialog.select('Season %s: which episode?'%season,labels+['Several episodes...'])
   xbmc.log('Kodi iOS download: season %s episode list, picked %s'%(season,pick),xbmc.LOGINFO)
   if pick<0:return
   if pick<len(choices):chosen=[pick]
   else:
    chosen=dialog.multiselect('Season %s: tick the episodes'%season,labels) or []
    xbmc.log('Kodi iOS download: ticked %s'%chosen,xbmc.LOGINFO)
    if not chosen:dialog.ok('Download','No episode was ticked. Tap an episode to tick it, then OK.');return
   episodes=[choices[i][0] for i in chosen]
   watching=mode(dl.mode_labels('season',episodes))
   xbmc.log('Kodi iOS download: episodes %s, watch %s'%(episodes,watching),xbmc.LOGINFO)
   if watching is None:return
   first=min(episodes)
   # Every version is chosen first (one page per episode), then the first episode plays: a page for the next
   # episode never opens over the video.
   before=dl.torrents()
   start('episode',first)
   tid=dl.added(before,wait,attempts=300)
   added=([first] if tid else [])+dl.download_each([n for n in episodes if n!=first],lambda n:start('episode',n),wait)
   if added:notices.note('download','Downloading season %s'%season,'%d of %d episodes'%(len(added),len(episodes)))
   if watching:watch('episode',tid,first)
   return
  watching=mode(dl.mode_labels('season'))
  if watching is None:return
  # Elementum fetches one file of a season pack: switch the new pack to "download all" once it is added.
  before=dl.torrents()
  start('season')
  tid=dl.download_all_when_added(before,wait)
  if tid:notices.note('download','Downloading all of season %s'%season)
  if watching:watch('episode',tid,1)
  return
 watching=mode(dl.mode_labels(kind))
 if watching is None:return
 before=dl.torrents()
 start(kind,episode)
 if watching:watch(kind,dl.added(before,wait,attempts=300),episode)

def main():
 # Owner (build-127): after picking episodes nothing happened. Every step is logged and a failure is shown, never
 # a silent stop.
 import traceback,xbmc,xbmcgui
 try:run()
 except Exception as error:
  xbmc.log('Kodi iOS download failed: %s\n%s'%(error,traceback.format_exc()),xbmc.LOGERROR)
  xbmcgui.Dialog().ok('Download','Download could not start: %s'%error)

if __name__=='__main__':main()
