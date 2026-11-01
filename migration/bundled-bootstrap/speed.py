"""Video controls › speed: play slower or faster (Kodi keeps the pitch)."""
import json

def run():
 import xbmc,xbmcgui
 speeds=[0.8,0.9,1.0,1.1,1.25,1.5]
 rpc=lambda method,params:json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params})))
 players=rpc('Player.GetActivePlayers',{}).get('result') or []
 video=[p['playerid'] for p in players if p.get('type')=='video']
 if not video:return
 pick=xbmcgui.Dialog().select('Playback speed',['%gx'%s+('  (normal)' if s==1.0 else '') for s in speeds],preselect=2)
 if pick<0:return
 answer=rpc('Player.SetTempo',{'playerid':video[0],'tempo':speeds[pick]})
 if 'error' in answer:xbmcgui.Dialog().notification('Playback speed','This video cannot change speed',xbmcgui.NOTIFICATION_INFO,4000)

if __name__=='__main__':run()
