"""Changelog row of the add-on page (RunScript(service.kodi.ios.bootstrap,addon_changelog)): the add-on's full changelog
(ListItem.AddonNews of the open add-on dialog) in Kodi's text viewer, which the portrait skin draws as a normal page.
The text can run to hundreds of lines, so it is not put on the add-on page itself."""
import xbmc,xbmcgui

def main():
 name=xbmc.getInfoLabel('ListItem.Label') or 'Add-on'
 text=xbmc.getInfoLabel('ListItem.AddonNews') or 'This add-on has no changelog.'
 xbmcgui.Dialog().textviewer('%s · Changelog'%name,text)

if __name__=='__main__':main()
