"""Bounded local AirPlay evidence, sampled only while a player session exists. No URLs or media IDs."""
import collections,json,os,time
from pathlib import Path
import diagnostics
PLAYER=('generation','state','active','position','duration','rate','time_control','external','buffer_empty',
        'likely_to_keep_up','item_status','player_status','error_code','error_domain','stop_reason','sample_age_s')
NETWORK=('phase','start_age_s','listen_age_s','tv_requests','tv_media','tv_video','first_tv_s','player_age_s','connect_age_s')
SOURCE=('http_requests','http_retries','http_errors','last_status','request_ms','source_read_ms','cache_hits',
        'cache_misses','cache_waits','read_bytes','last_read','read_error')

def selected(data,keys):return diagnostics.safe({key:data[key] for key in keys if key in data})

def store(profile,name,data):
 folder=Path(profile)/'addon_data/service.kodi.ios.bootstrap';folder.mkdir(parents=True,exist_ok=True)
 target=folder/name;temp=target.with_suffix('.tmp');temp.write_text(json.dumps(diagnostics.safe(data),separators=(',',':'))+'\n');os.replace(temp,target)

class Tracker:
 def __init__(self):
  self.generation=None;self.rows=collections.deque(maxlen=96);self.previous=None
  self.played=False;self.advanced=0;self.last_report={}
 def observe(self,sample,now):
  player=sample.get('player') or {};generation=player.get('generation')
  if not generation or player.get('sample_age_s',0)>15:return None
  if generation!=self.generation:
   self.__init__();self.generation=generation;self.advanced=now
  previous=self.previous or {};before=previous.get('player') or {}
  # An iOS suspension or a seek starts a new observation interval, not a proven continuous stall.
  gap=now-previous.get('at',now)
  if gap>20 or abs(player.get('position',0)-before.get('position',0))>.25:self.advanced=now
  self.rows.append(dict(sample,at=now));self.previous=self.rows[-1]
  if player.get('active') and player.get('state')==1:self.played=True
  if not self.played:return None
  why=None;reason=player.get('stop_reason',0)
  if reason==3:return None # explicitly closed by the owner/controller
  if reason==1:
   total=player.get('duration',0);remaining=total-player.get('position',0)
   if total>0 and remaining>max(10,min(30,total*.01)):why='ended_before_duration'
   else:return None
  elif reason==2 or player.get('state',0)<0:why='player_failed'
  elif before.get('external') and not player.get('external') and player.get('active'):why='receiver_route_ended'
  elif before.get('active') and not player.get('active'):why='unexpected_player_stop'
  elif player.get('time_control')==2 and now-self.advanced>=30:why='buffering_without_progress'
  if not why or now-self.last_report.get(why,float('-inf'))<60:return None
  self.last_report[why]=now
  return {'reason':why,'generation':generation,'at':now,'recent':list(self.rows)}

def capture(profile,report,write,queues=None):
 folder=Path(profile)/'addon_data/service.kodi.ios.bootstrap';folder.mkdir(parents=True,exist_ok=True)
 for name,next_name in (('airplay-stop-1.json','airplay-stop-2.json'),('airplay-stop-latest.json','airplay-stop-1.json')):
  source=folder/name
  if source.exists():os.replace(source,folder/next_name)
 report=dict(report,queues=queues or {})
 store(profile,'airplay-stop-latest.json',report)
 # The ordinary kodi.log also gets the useful tail, even when the owner doesn't use Export diagnostics.
 diagnostics.event(write,'airplay','unexpected_stop',reason=report['reason'],generation=report['generation'],
                   recent=report['recent'][-12:],queues=report['queues'])

def watch(lib,profile,window,write,wait,clock=time.time):
 import airplay,remote_media
 if not hasattr(lib,'kodi_airplay_health'):return
 tracker=Tracker();saved=logged=float('-inf')
 while not wait(5):
  try:
   player=selected(airplay.health(lib),PLAYER)
   if not player.get('generation'):continue
   if not player.get('active') and not tracker.played:continue
   try:source=selected(remote_media.stats(window),SOURCE)
   except Exception:source={} # a closing broker must not prevent the stop itself from being captured
   sample={'player':player,'network':selected(airplay.network(lib,window) or {},NETWORK),'source':source}
   was_playing=tracker.played
   now=clock();report=tracker.observe(sample,now)
   if report:capture(profile,report,write,diagnostics.snapshot(profile))
   if was_playing and not player.get('active') and player.get('state',0)<=0:
    store(profile,'airplay-recent.json',{'generation':tracker.generation,'recent':list(tracker.rows)})
    diagnostics.event(write,'airplay','playback_ended',**sample)
    tracker.played=False
   if player.get('active') and now-saved>=30:
    store(profile,'airplay-recent.json',{'generation':tracker.generation,'recent':list(tracker.rows)});saved=now
   if player.get('active') and now-logged>=30:
    diagnostics.event(write,'airplay','playback_progress',**sample);logged=now
  except Exception as error:diagnostics.exception(write,'airplay_diagnostics',error)
