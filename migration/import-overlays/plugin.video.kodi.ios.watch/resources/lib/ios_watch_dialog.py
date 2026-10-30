"""Explicit source choice inside the existing movie/episode resolver; no autoplay."""
def choose_player(player):
 import xbmc,xbmcgui,xbmcaddon,xbmcvfs
 player.allow_playlist=False
 details=player.details;art=getattr(details,'art',{}) or {};info=getattr(details,'infolabels',{}) or {}
 settings=xbmcaddon.Addon('plugin.video.kodi.ios.watch')
 enabled=xbmc.getCondVisibility('System.AddonIsEnabled(plugin.video.elementum)')
 ready=enabled and settings.getSettingBool('enable_elementum_native_test')
 candidates=list(player.player_items.items_play)
 engine=next((p for p in candidates if p.file=='ios.elementum.json'),None)
 rows=[]
 if ready and engine:rows.append(('Elementum — select source (native test)','elementum',engine))
 else:rows.append(('Elementum — iOS engine not integrated','engine_status',None))
 for p in candidates:
  if p.is_local and p.kodi_file and xbmcvfs.exists(p.kodi_file):rows.append(('Local library file','local',p))
 rows.append(('Browse Google Drive separately','drive',None))
 items=[]
 for label,action,item in rows:
  li=xbmcgui.ListItem(label=label);li.setArt(art);items.append(li)
 selected=xbmcgui.Dialog().select('Watch options: '+str(info.get('title') or info.get('tvshowtitle') or ''),items)
 if selected<0 or selected>=len(rows):return None
 _,action,item=rows[selected]
 if action=='engine_status':
  xbmcgui.Dialog().ok('Elementum not ready','A real signed iOS engine and its player integration are required. This menu does not install or simulate an engine.');return None
 if action=='drive':
  xbmc.executebuiltin('ActivateWindow(Videos,plugin://plugin.googledrive/,return)');return None
 return item
