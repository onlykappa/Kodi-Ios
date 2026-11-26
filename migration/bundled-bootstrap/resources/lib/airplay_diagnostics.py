"""Bounded local AirPlay evidence, sampled only while a player session exists. No URLs or media IDs."""
import collections,json,os,time
from pathlib import Path
import diagnostics
PLAYER=('generation','state','active','position','duration','rate','time_control','external','buffer_empty',
        'likely_to_keep_up','item_status','player_status','error_code','error_domain','stop_reason','sample_age_s')
# ISSUE-495: Apple's access-log counters and the seconds loaded ahead; only a framework newer than r76 reports them (-1: no value).
COUNTERS=('access_events','dropped_frames','stalls','observed_bps','indicated_bps','downloaded_s','transfer_s','buffered_ahead_s')
SAMPLE=('position','rate','time_control','buffer_empty','likely_to_keep_up','external','sample_age_s')+COUNTERS
PLAYER+=COUNTERS
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

class Judder:
 """ISSUE-491 (owner, 2026-11-26: "the fps lags at random times, it almost never buffers"): the 30 s samples hide short trouble. Every 5 s sample is compared with the one before:
 a change of the TV player's state (waiting / playing / buffer empty / likely to keep up / rate) is an event at once, and a stretch where the picture's clock advanced
 less than the wall clock while it was playing is a `position_slip` with how much was lost. A seek, a pause, or an iOS suspension (a gap over 12 s) is not a slip."""
 KEYS=('time_control','buffer_empty','likely_to_keep_up','rate','external')
 def __init__(self):self.last=None
 def observe(self,player,now):
  last=self.last;self.last=(dict(player),now)
  if not last:return []
  before,then=last;out=[]
  changes={k:[before.get(k),player.get(k)] for k in self.KEYS if before.get(k)!=player.get(k)}
  if changes:out.append(('state_change',{'changes':changes,'position':round(float(player.get('position') or 0),1)}))
  # ISSUE-495: a dropped frame or a stall the TV player counted since the last sample. -1 or absent is "no value", not a change.
  counted={k:[before.get(k),player.get(k)] for k in ('dropped_frames','stalls') if (before.get(k) is not None and before.get(k)>=0 and (player.get(k) or 0)>before.get(k))}
  if counted:out.append(('counter_change',{'changes':counted,'position':round(float(player.get('position') or 0),1)}))
  wall=now-then
  playing=lambda p:p.get('time_control')==2 and p.get('rate')==1.0
  if 3<=wall<=12 and playing(before) and playing(player):
   moved=float(player.get('position') or 0)-float(before.get('position') or 0)
   if 0<=moved and wall-moved>=1.5:   # moved<0 or far over the wall time is a seek
    out.append(('position_slip',{'wall_s':round(wall,1),'advanced_s':round(moved,1),'lost_s':round(wall-moved,1),'position':round(float(player.get('position') or 0),1)}))
  return out

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

def watch(lib,profile,window,write,wait,clock=time.time,recover=None):
 import airplay,remote_media
 if not hasattr(lib,'kodi_airplay_health'):return
 tracker=Tracker();judder=Judder();saved=logged=float('-inf')
 while not wait(5):
  try:
   player=selected(airplay.health(lib),PLAYER)
   if not player.get('generation'):continue
   if not player.get('active') and not tracker.played:continue
   try:source=selected(remote_media.stats(window),SOURCE)
   except Exception:source={} # a closing broker must not prevent the stop itself from being captured
   sample={'player':player,'network':selected(airplay.network(lib,window) or {},NETWORK),'source':source}
   if recover is not None:
    try:recover.observe(player)   # a cast that sits still is started again once, then the person is told (airplay_recover.py)
    except Exception as error:diagnostics.exception(write,'airplay_recover',error)
   was_playing=tracker.played
   now=clock();report=tracker.observe(sample,now)
   try:
    for name,fields in judder.observe(player,now):diagnostics.event(write,'airplay',name,source=source,network=sample['network'],**fields)
   except Exception as error:diagnostics.exception(write,'airplay_judder',error)
   # ISSUE-495: one short line per 5 s sample, so a stutter's clock time can be matched to the picture position.
   if player.get('active'):write('Kodi iOS AirPlay sample: '+json.dumps(selected(player,SAMPLE),separators=(',',':')))
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
