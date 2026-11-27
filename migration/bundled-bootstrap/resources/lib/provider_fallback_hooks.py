"""Fallback behind existing source searches; keep the same picker/ranking and resolve by source origin.

Only verified movie/episode identities enter the broker. A user cancellation never starts another provider.
No provider-native result is given to Umbrella's Coco resolver or to an Elementum source-list index.
"""
import ast,json,os,sys,time,urllib.parse

MARKER='# KODI-IOS-PROVIDER-FALLBACK'
MANUAL='KodiIOS.ProviderFallback.Request'


def broker():
 import provider_fallback
 return provider_fallback


def cancel_callback(cancel=None):
 if cancel is not None:return cancel
 try:
  import xbmc
  return xbmc.Monitor().abortRequested
 except ImportError:return lambda:False


def playback_uncertain():
 """A player is open, opening or buffering: a backup would start a second one. Unknown (no Kodi) counts as certain."""
 try:
  import xbmc
  return bool(xbmc.getCondVisibility('Player.HasMedia | Player.Caching'))
 except Exception:return False


def candidate_key(candidate):
 """Same torrent (info hash) or same release name and size is one source."""
 return str(candidate.get('torrent_hash') or '').lower() or (str(candidate.get('name') or '').lower(),round(float(candidate.get('size') or 0),1))


def dedupe(candidates):
 """One row per source within a picker round, keeping the best-seeded copy. A failed origin is not remembered here: another
 provider's copy of the same release must stay available as the next round's alternative."""
 best={}
 for c in candidates:
  k=candidate_key(c)
  if k not in best or (c.get('seeders') or 0)>(best[k].get('seeders') or 0):best[k]=c
 return [c for c in candidates if best[candidate_key(c)] is c]


def usable(deck,items,profile=None):
 profile=profile or {}
 kept=[p for p in items if p.get('seeds',0)>0 and not deck.is_bad(p)]
 if profile.get('strict_quality') and profile.get('quality'):
  kept=[p for p in kept if p['quality']==profile['quality'] and not deck.below_quality(p,profile['quality'],int(profile.get('runtime') or 0))]
 return bool(kept)


def _attempt(home,auto=None):
 return str((auto or {}).get('request_id') or (home.getProperty(MANUAL) if home else ''))


def _mark(home,auto=None):
 ident=_attempt(home,auto)
 if home is not None and ident:home.setProperty('KodiIOS.ProviderFallback.Done.'+ident,'true')


def _resolved(deck,exp,title,mode,auto=None,cancel=None,timeout=60):
 """Reuse the existing picker, retry only failed resolver origins, and bound the whole fallback turn."""
 pf=broker();base_cancel=cancel_callback(cancel);deadline=time.monotonic()+max(0,float(timeout));excluded=set()
 if playback_uncertain():return None
 profile=dict((auto or {}).get('profile') or {})
 purpose=(auto or {}).get('purpose') or ('stream' if mode=='stream' else 'download')
 request=pf.request_from_expected(exp,purpose,profile)
 home=deck._home()
 generation=_attempt(home,auto)
 def cancel():
  # A newer request replaced this one (its id left the Home window): this search is stale and must stop.
  return base_cancel() or (bool(generation) and home is not None and _attempt(home,auto)!=generation)
 _mark(home,auto)
 while len(excluded)<len(pf.PROVIDERS) and time.monotonic()<deadline:
  if cancel():raise pf.Canceled('Source search canceled')
  candidates=pf.search(request,primary='umbrella' if mode=='stream' else 'elementum',cancel=cancel,
                       timeout=max(.1,deadline-time.monotonic()),exclude=tuple(excluded))
  if cancel():raise pf.Canceled('Source search canceled')    # replaced or cancelled while searching: never show or start it
  candidates=dedupe(candidates)
  if not candidates:return None
  # Broker identity/quality checks and the current picker's codec/size checks both apply.
  labels=pf.picker_items(candidates);parsed=deck.parse_all(labels) or []
  if not usable(deck,parsed,profile):
   excluded.update(c['provider'] for c in candidates)
   continue
  # Foreign candidates are represented only as labels in the existing picker; the index maps back here.
  def source_check(parsed):
   index=parsed.get('idx')
   if not isinstance(index,int) or not 0<=index<len(candidates):return False
   candidate=candidates[index]
   return bool(pf.verified([candidate],request,candidate.get('provider')))
  index=deck.run(title,labels,expect=exp,mode=mode,fallback=False,source_check=source_check)
  if auto and purpose in ('scan','survey'):
   return {'scan':True,'request':request}
  if index is None or index<0:raise pf.Canceled('Source selection canceled')
  if index>=len(candidates):return None
  chosen=candidates[index]
  try:
   url=pf.resolve(chosen,request,cancel=cancel,timeout=min(15,max(.1,deadline-time.monotonic())))
   if url:return {'candidate':chosen,'url':url,'request':request}
  except pf.Canceled:raise
  except (RuntimeError,OSError,ValueError,TimeoutError):pass
  excluded.add(chosen['provider'])
 return None


def stream_url(url,request=None):
 if urllib.parse.urlsplit(url).scheme!='magnet':return url
 # The iPhone's Elementum /play route saves to Drive. Never turn Stream into a download.
 raise ValueError('This source requires the torrent download route')


def direct_wanted():
 """A torrent Stream may go to peers (behind the torrent prompt) when there is no debrid key at all, or once debrid has been failing (three
 service-level failures in a row, still cooling down). A working debrid or an unknown state keeps the old refusal."""
 try:
  import debrid_account,debrid_token
  if not debrid_token.has():return True
  return debrid_account.is_unavailable()
 except Exception:return False


def direct(selected,request,cancel=None):
 """Step 18: stream the chosen torrent from peers with the bundled Elementum engine. True when playing; False when declined, canceled or no peers."""
 import xbmcgui,elementum_download,backup_playback,p2p_rules,debrid_account,source_contract
 home=xbmcgui.Window(10000);bar=[]
 def show(text,percent=0):
  """Kodi's own progress dialog, in the skin's style, with its Cancel button: "Streaming from peers" / "Waiting for peers · 80 s". Closed when done."""
  try:
   home.setProperty(p2p_rules.STATUS,text) if text else home.clearProperty(p2p_rules.STATUS)
   if not text:
    if bar:bar.pop().close()
    return
   if not bar:
    dialog=xbmcgui.DialogProgress();dialog.create('Streaming from peers',text);bar.append(dialog)
   bar[0].update(percent or 0,text)
  except Exception:pass
 def stop():return bool((cancel and cancel()) or (bar and bar[0].iscanceled()))     # its Cancel button ends the wait and never moves on to another swarm
 try:
  p2p_rules.stream_best([selected['candidate']],request,backup_playback.Playback(backup_playback.KodiPlayer()),home,lambda:elementum_download._torrent_gate(stream=True),
                        health=debrid_account.shared_health(),cancel=stop,show=show)
  return True
 except source_contract.Outcome:return False
 finally:show('')


def dispatch(selected,auto=None,cancel=None):
 pf=broker();cancel=cancel_callback(cancel)
 if cancel():raise pf.Canceled('Source search canceled')
 url=selected['url'];request=selected['request']
 if request['purpose']=='stream':
  if urllib.parse.urlsplit(url).scheme=='magnet' and direct_wanted():
   return direct(selected,request,cancel)
  import xbmc
  xbmc.Player().play(stream_url(url,request))
  return True
 if urllib.parse.urlsplit(url).scheme=='magnet':
  import elementum_cloud
  params={'uri':url}
  for field in ('season','episode'):
   if request.get(field) not in (None,''):params[field]=request[field]
  return bool(elementum_cloud.route('http://127.0.0.1:9220/play?'+urllib.parse.urlencode(params),
                 quiet=auto is not None,request_id=(auto or {}).get('request_id')))
 return bool(pf.queue_download(selected['candidate'],url,request,auto=auto,cancel=cancel))


def deck_fallback(deck,exp,title,mode='download',auto=None,cancel=None,timeout=60):
 if not exp or exp.get('kind') not in ('movie','episode'):return None
 try:
  selected=_resolved(deck,exp,title,mode,auto,cancel,timeout)
  if selected is None:return None
  if selected.get('scan'):return True
  return True if dispatch(selected,auto,cancel) else None
 except broker().Canceled:
  return True
 except (ImportError,RuntimeError,OSError,ValueError,TimeoutError):return None


def expected_target(target):
 import source_match
 exp=source_match.expected('episode' if target.get('episode') is not None else 'season',
             [target.get('title') or ''],tmdb=str(target.get('tmdb') or ''),
             season=target.get('season'),episode=target.get('episode'))
 if not exp.get('titles'):exp=source_match.enrich(exp)
 return exp


def season_fallback(home,target,wanted,cancel=None,timeout=60):
 """No-dialog Elementum failures use the identical automatic picker/receipt path as successful searches."""
 ident=wanted['request_id'];key='KodiIOS.ProviderFallback.Done.'+ident
 if home.getProperty(key):return None
 import umbrella_picker,episode_watch
 deck=umbrella_picker.load();exp=expected_target(target)
 if not exp or exp.get('kind')!='episode':return None
 handled=deck_fallback(deck,exp,target.get('title') or '',auto=dict(wanted,_lane=wanted.get('_lane','')),cancel=cancel,timeout=timeout)
 if not handled:return None
 try:result=json.loads(home.getProperty(episode_watch.RESULT+wanted.get('_lane','')) or '{}')
 except ValueError:result={}
 return result if result.get('request_id')==ident else None


def download_follow(url,exp,follow,cancel=None,timeout=60):
 """Primary success remains untouched; a source-dialog fallback is not repeated after follow() returns."""
 import uuid,xbmcgui,elementum_download
 home=xbmcgui.Window(10000);ident=uuid.uuid4().hex;home.setProperty(MANUAL,ident)
 error=None;reached=None
 try:
  try:reached=follow(url)
  except elementum_download.Canceled:raise
  except (OSError,RuntimeError,ValueError,TimeoutError) as caught:error=caught
  if cancel and cancel():raise elementum_download.Canceled('Source search canceled')
  if home.getProperty('KodiIOS.ProviderFallback.Canceled.'+ident):
   raise elementum_download.Canceled('Source selection canceled')
  if home.getProperty('KodiIOS.ProviderFallback.Done.'+ident):return reached
  # A selected play/download redirect was already handled by the existing cloud route.
  if reached and urllib.parse.urlsplit(reached).path.rstrip('/') in ('/play','/download'):return reached
  if exp:
   import umbrella_picker
   deck=umbrella_picker.load()
   handled=deck_fallback(deck,exp,(exp.get('titles') or [''])[0],cancel=cancel,timeout=timeout)
   if handled:return reached
  if error:raise error
  return reached
 finally:
  if home.getProperty(MANUAL)==ident:home.clearProperty(MANUAL)
  home.clearProperty('KodiIOS.ProviderFallback.Done.'+ident)
  home.clearProperty('KodiIOS.ProviderFallback.Canceled.'+ident)


def umbrella_selection(meta,deck,exp):
 """A pre-window fallback returns an already-resolved URL via Umbrella's existing direct-play action."""
 try:
  selected=_resolved(deck,exp,(meta or {}).get('tvshowtitle') or (meta or {}).get('title') or '', 'stream')
  return (True,stream_url(selected['url'],selected['request'])) if selected else (False,None)
 except broker().Canceled:return True,None
 except (ImportError,RuntimeError,OSError,ValueError,TimeoutError):return False,None


def umbrella_empty(owner,meta=None):
 """Called before Umbrella's no-results error, including its zero-premium-provider path."""
 if getattr(owner,'_kodi_provider_cancelled',False) or getattr(owner,'_kodi_provider_done',False) or getattr(owner,'url',None)=='close://':return False
 owner._kodi_provider_done=True
 data=dict(getattr(owner,'_kodi_provider_request',{}) or getattr(owner,'playback_request',{}) or {})
 raw=meta if meta is not None else getattr(owner,'meta',None)
 if isinstance(raw,str):
  try:raw=json.loads(raw)
  except ValueError:raw={}
 if isinstance(raw,dict):data.update({k:v for k,v in raw.items() if v is not None})
 import source_match,umbrella_picker
 exp=source_match.from_meta(data)
 if not exp:return False
 try:
  exp=source_match.enrich(exp);deck=umbrella_picker.load();umbrella_picker.share(data)
  selected=_resolved(deck,exp,data.get('tvshowtitle') or data.get('title') or '', 'stream',cancel=cancel_callback())
  if not selected:return False
  # Use Umbrella's player metadata/resume plumbing, but never its provider-native Coco resolver.
  from resources.lib.modules import player
  player.Player().play_source(data.get('tvshowtitle') or data.get('title'),data.get('year'),data.get('season'),
      data.get('episode'),data.get('imdb'),data.get('tmdb'),data.get('tvdb'),stream_url(selected['url'],selected['request']),data)
  return True
 except broker().Canceled:
  owner._kodi_provider_cancelled=True
  return True
 except (ImportError,RuntimeError,OSError,ValueError,TimeoutError):return False


def install(path):
 """Conservatively add no-results/cancel hooks to an installed Umbrella Sources class; unknown versions stay intact."""
 from pathlib import Path
 path=Path(path)
 if not path.is_file():return False
 text=path.read_text(encoding='utf-8')
 if MARKER in text:return False
 try:tree=ast.parse(text)
 except SyntaxError:return False
 classes=[c for c in tree.body if isinstance(c,ast.ClassDef) and any(isinstance(n,ast.FunctionDef) and n.name=='errorForSources' for n in c.body)]
 if len(classes)!=1:return False
 methods={n.name:n for n in classes[0].body if isinstance(n,ast.FunctionDef)}
 if not {'play','errorForSources','sourceSelect','sourcesAutoPlay','getSources_dialog'}<=methods.keys():return False
 play=methods['play'];names={a.arg for a in play.args.args}
 if not {'title','year','imdb','tmdb','tvdb','season','episode','tvshowtitle','premiered','meta'}<=names:return False
 lines=text.splitlines(keepends=True);edits=[]
 def insert(node,body):
  line=lines[node.lineno-1];indent=line[:len(line)-len(line.lstrip())]
  edits.append((node.lineno-1,''.join(indent+t+'\n' for t in body),False))
 first=play.body[0]
 if isinstance(first,ast.Expr) and isinstance(first.value,ast.Constant) and isinstance(first.value.value,str):first=play.body[1]
 insert(first,["self._kodi_provider_cancelled = False","self._kodi_provider_done = False",
  "self._kodi_provider_request = dict(title=title, year=year, imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=season, episode=episode, tvshowtitle=tvshowtitle, premiered=premiered)"])
 first=methods['errorForSources'].body[0]
 insert(first,["if _kodi_provider_fallback(self): return"])
 premium=[n for n in ast.walk(play) if isinstance(n,ast.If) and ast.unparse(n.test).replace(' ','')=='notself.prem_providers']
 for node in premium:insert(node.body[0],["if _kodi_provider_fallback(self): return"])
 for name in ('getSources_dialog','sourcesAutoPlay','sourcesFilter'):
  method=methods.get(name)
  if not method:continue
  for node in ast.walk(method):
   if not isinstance(node,ast.If):continue
   test=ast.unparse(node.test)
   if test in ('progressDialog.iscanceled()','cancelled'):
    if node.body[0].lineno==node.lineno:
     old=lines[node.lineno-1];indent=old[:len(old)-len(old.lstrip())];head,tail=old.split(':',1)
     edits.append((node.lineno-1,head+':\n'+indent+'\tself._kodi_provider_cancelled = True\n'+indent+'\t'+tail.strip()+'\n',True))
    else:insert(node.body[0],["self._kodi_provider_cancelled = True"])
 for at,addition,replace in sorted(edits,reverse=True):
  if replace:lines[at]=addition
  else:lines.insert(at,addition)
 helper='''\n\n# KODI-IOS-PROVIDER-FALLBACK\ndef _kodi_provider_fallback(owner):
 try:
  import sys, xbmcvfs
  lib=xbmcvfs.translatePath('special://xbmc/addons/service.kodi.ios.bootstrap/resources/lib')
  if lib not in sys.path:sys.path.insert(0,lib)
  import provider_fallback_hooks
  return provider_fallback_hooks.umbrella_empty(owner)
 except Exception:
  return False
'''
 new=''.join(lines)+helper
 try:compile(new,str(path),'exec')
 except SyntaxError:return False
 path.write_text(new,encoding='utf-8');return True
