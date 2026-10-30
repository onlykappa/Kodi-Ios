"""Deck-style "How would you like to watch?" chooser inside TMDb Helper's movie/episode resolver; no autoplay."""
NOT_READY={'elementum':('Elementum not available yet','Elementum needs a native iOS engine, which this build does not include yet.'),
           'umbrella':('Umbrella not available yet','Umbrella has not been ported to this iPhone build yet. It will appear here once it is.')}

def choose_player(player):
 import xbmc,xbmcgui,xbmcaddon,xbmcvfs
 player.allow_playlist=False
 details=player.details;art=getattr(details,'art',{}) or {};info=getattr(details,'infolabels',{}) or {}
 settings=xbmcaddon.Addon('plugin.video.kodi.ios.watch')
 candidates=list(player.player_items.items_play)
 def installed(addon):return xbmc.getCondVisibility('System.AddonIsEnabled('+addon+')')
 rows=[]
 engine=next((p for p in candidates if p.file=='ios.elementum.json'),None)
 if engine and installed('plugin.video.elementum') and settings.getSettingBool('enable_elementum_native_test'):rows.append(('Elementum','play',engine))
 else:rows.append(('Elementum — not available on iPhone yet','elementum',None))
 # Any TMDb Helper player for Umbrella is offered once the add-on is installed, as on the Deck.
 umbrella=next((p for p in candidates if 'umbrella' in str(p.file).lower()),None)
 if umbrella and installed('plugin.video.umbrella'):rows.append(('Umbrella','play',umbrella))
 else:rows.append(('Umbrella — coming soon','umbrella',None))
 for p in candidates:
  if p.is_local and p.kodi_file and xbmcvfs.exists(p.kodi_file):rows.append(('Local library file','play',p))
 rows.append(('Google Drive','drive',None))
 items=[]
 for label,action,item in rows:
  li=xbmcgui.ListItem(label=label);li.setArt(art);items.append(li)
 title=str(info.get('title') or info.get('tvshowtitle') or '')
 selected=xbmcgui.Dialog().select('How would you like to watch'+(' '+title if title else '')+'?',items)
 if selected<0 or selected>=len(rows):return None
 _,action,item=rows[selected]
 if action in NOT_READY:
  xbmcgui.Dialog().ok(*NOT_READY[action]);return None
 if action=='drive':
  xbmc.executebuiltin('ActivateWindow(Videos,plugin://plugin.googledrive/,return)');return None
 return item
