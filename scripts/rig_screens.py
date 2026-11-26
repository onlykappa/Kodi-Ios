#!/usr/bin/env python3
"""Screenshots of the new source-resilience screens on the desktop Kodi rig (evidence class: desktop rig, never iPhone; images stay in KODI_RIG_HOME/shots).

Shows, with no network and no account: Accounts with the AllDebrid row, the sign-in code sheet, the sign-out sheet, the stream-from-peers prompt and the
"Waiting for peers" background progress. The sheets are the app's own choice sheet and Kodi's own dialogs; a fake code is used (no request goes to AllDebrid)."""
import os,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
RIG=Path(os.environ.get('KODI_RIG_HOME',Path.home()/'.cache/kodi-rig'))
SCREENS=('accounts','signin_pin','signin_manage','stream_prompt','download_prompt','peers_progress')

def run():
    sys.path.insert(0,str(ROOT/'scripts'));import kodi_rig
    me=str(Path(__file__).resolve())
    for name in SCREENS:
        kodi_rig.run_builtins('Dialog.Close(all,true)');time.sleep(1)
        if name=='accounts':kodi_rig.rpc('Addons.ExecuteAddon',{'addonid':kodi_rig.BOOT_ID,'params':['accounts_page'],'wait':False})
        else:kodi_rig.run_builtins('RunScript(%s,--inside-kodi,%s)'%(me,name))
        time.sleep(7 if name=='accounts' else 4);kodi_rig.shot('screen-'+name);print('shot',name)
    kodi_rig.run_builtins('Dialog.Close(all,true)')

def inside(name):
    import xbmc,xbmcgui,xbmcaddon
    sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
    import choice_sheet,debrid_signin_ui,torrent_prompt,p2p_rules
    here=xbmcaddon.Addon('service.kodi.ios.bootstrap').getAddonInfo('path')
    if name=='signin_pin':choice_sheet.choose(debrid_signin_ui.pin_spec('ABCD'),xbmcgui=xbmcgui,xbmc=xbmc,path=here)
    elif name=='signin_manage':choice_sheet.choose(debrid_signin_ui.signed_in_spec(),xbmcgui=xbmcgui,xbmc=xbmc,path=here)
    elif name=='stream_prompt':
        text,yes=torrent_prompt.message({'state':'unknown'},stream=True);xbmcgui.Dialog().yesno(torrent_prompt.STREAM_HEADING,text,nolabel='Cancel',yeslabel=yes)
    elif name=='download_prompt':
        text,yes=torrent_prompt.message({'state':'unknown'});xbmcgui.Dialog().yesno(torrent_prompt.HEADING,text,nolabel='Cancel',yeslabel=yes)
    elif name=='peers_progress':
        d=xbmcgui.DialogProgress();d.create('Streaming from peers',p2p_rules.status_text(36,90));d.update(40,p2p_rules.status_text(36,90));time.sleep(8);d.close()

if __name__=='__main__':
    if len(sys.argv)>2 and sys.argv[1]=='--inside-kodi':inside(sys.argv[2])
    else:run()
