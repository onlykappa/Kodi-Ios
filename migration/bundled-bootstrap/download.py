"""Long press › Download (context menu), and Download on a show's seasons page (RunScript with key=value args)."""
import os,sys
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'resources','lib'))
import elementum_download as dl,elementum_engine

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
 before=dl.torrents()
 xbmc.executebuiltin('RunPlugin(%s)'%dl.plugin_url(kind,tmdb,season,episode))
 if kind!='season':return
 # Elementum fetches one file of a season pack: switch the new pack to "download all" once it is added.
 tid=dl.download_all_when_added(before,lambda:xbmc.Monitor().waitForAbort(1))
 if tid:dialog.notification('Download','Downloading all of season %s'%season,xbmcgui.NOTIFICATION_INFO,6000)

if __name__=='__main__':run()
