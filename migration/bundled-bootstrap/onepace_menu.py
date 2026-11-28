"""Long press on a One Pace arc or episode (the show page of `plugin://plugin.video.kodi.ios.watch/?action=onepace`): Download, or Play in Japanese. One file for both
context items; the item's label decides through the script's argument (addon.xml passes it)."""
import sys,urllib.parse
ME='plugin://plugin.video.kodi.ios.watch/'

def action(mode,kind,season,episode):
 """The Kodi built-in for a menu choice, or '' when the item cannot do it. mode: 'download' | 'japanese'."""
 season=str(season or '');episode=str(episode or '')
 if mode=='download':
  if kind not in ('season','episode') or not season.isdigit() or (kind=='episode' and not episode.isdigit()):return ''
  query={'action':'onepace_download','season':season}
  if kind=='episode':query['episode']=episode
  return 'RunPlugin(%s?%s)'%(ME,urllib.parse.urlencode(query))
 if mode=='japanese':
  if kind!='episode' or not season.isdigit() or not episode.isdigit():return ''
  return 'PlayMedia(%s?%s)'%(ME,urllib.parse.urlencode({'action':'onepace_play','season':season,'episode':episode,'prefer':'japanese'}))
 return ''

def run():
 import xbmc
 item=getattr(sys,'listitem',None)
 if item is None:return
 tag=item.getVideoInfoTag()
 mode=sys.argv[1] if len(sys.argv)>1 else 'download'
 built=action(mode,tag.getMediaType(),tag.getSeason() if tag.getSeason()>0 else '',tag.getEpisode() if tag.getEpisode()>0 else '')
 if built:xbmc.executebuiltin(built)

if __name__=='__main__':run()
