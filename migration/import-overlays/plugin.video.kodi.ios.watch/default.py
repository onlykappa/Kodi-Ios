"""Kodi renders this real directory UI; no mock screen or engine is generated."""
import os,sys
from urllib.parse import parse_qs
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'resources','lib'))
from ios_watch_routes import choices

def run(argv):
 import xbmc,xbmcaddon,xbmcgui,xbmcplugin
 handle=int(argv[1]);params={k:v[0] for k,v in parse_qs(argv[2].lstrip('?')).items()}
 if params.get('action')=='engine_status':
  xbmcgui.Dialog().ok('Elementum not available','Elementum is not installed or is switched off in this build. Check Add-ons > Video add-ons > Elementum.')
  xbmcplugin.endOfDirectory(handle,succeeded=False);return
 try:
  enabled=xbmc.getCondVisibility('System.AddonIsEnabled(plugin.video.elementum)')
  ready=enabled and xbmcaddon.Addon().getSettingBool('offer_elementum')
  entries=choices(params,ready)
 except (ValueError,RuntimeError):
  xbmcgui.Dialog().ok('Watch options','The media route is incomplete; use normal item information/episode navigation and record this failure.')
  xbmcplugin.endOfDirectory(handle,succeeded=False);return
 for entry in entries:
  li=xbmcgui.ListItem(label=entry['label']);li.setArt({k:params[k] for k in ['poster','fanart','thumb'] if params.get(k)})
  li.setInfo('video',{'title':params.get('title',''),'mediatype':params.get('kind','')})
  if not entry['folder']:li.setProperty('IsPlayable','true')
  xbmcplugin.addDirectoryItem(handle,entry['url'],li,isFolder=entry['folder'])
 xbmcplugin.setPluginCategory(handle,'Watch options');xbmcplugin.endOfDirectory(handle)
if __name__=='__main__':run(sys.argv)
