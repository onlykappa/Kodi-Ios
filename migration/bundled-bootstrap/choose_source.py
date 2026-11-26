"""Long press > Choose source on an episode or a movie of a TMDb Helper page (the TV show page, Movies, search): the same menu Continue Watching has on Home (owner, 2026-11-25:
"choose source works on Home but not in the TV show menu"). It plays the title with `ios_choose=1`, which always asks: the Download / Stream sheet, the quality list, the version
list. Nothing saved (the last version, a completed copy, the remembered link) is used. The place to resume is asked for by the plugin's `choose_source` action when the title has one."""
import os,sys,urllib.parse
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'resources','lib'))

def target(kind,path,values,ids=None):
 """{'tmdb_type','tmdb_id'[,'season','episode']} for a movie or an episode, or None when the item carries no usable TMDb ids."""
 if ids is None:
  import elementum_download as dl;ids=dl.ids
 tmdb,season,episode=ids(kind,path,values)
 if not tmdb:return None
 if kind=='movie':return {'tmdb_type':'movie','tmdb_id':str(tmdb)}
 if kind=='episode' and season and episode:return {'tmdb_type':'tv','tmdb_id':str(tmdb),'season':str(season),'episode':str(episode)}
 return None

def action(found):
 """The plugin action that asks for the source of this title (default.py: choose_source)."""
 query=dict(found,action='choose_source')
 return 'RunPlugin(plugin://plugin.video.kodi.ios.watch/?%s)'%urllib.parse.urlencode(query)

def run():
 import xbmc,xbmcgui
 item=getattr(sys,'listitem',None)
 if item is None:return
 tag=item.getVideoInfoTag();kind=tag.getMediaType()
 values={'tmdb':item.getUniqueID('tmdb'),'tvshow.tmdb_id':item.getProperty('tvshow.tmdb_id'),
         'season':str(tag.getSeason()) if tag.getSeason()>0 else '','episode':str(tag.getEpisode()) if tag.getEpisode()>0 else ''}
 found=target(kind,item.getPath(),values)
 if not found:
  xbmcgui.Dialog().notification('Choose source','This item has no TMDb id, so its sources cannot be looked up.',xbmcgui.NOTIFICATION_INFO,4000);return
 xbmc.log('Kodi iOS choose source: asked from the menu for a %s'%('movie' if found['tmdb_type']=='movie' else 'episode'),xbmc.LOGINFO)
 xbmc.executebuiltin(action(found))

if __name__=='__main__':run()
