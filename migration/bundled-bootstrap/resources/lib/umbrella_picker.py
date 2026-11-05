"""The Deck's "Choose a version" page for Umbrella's sources (deck_picker.py, the same page Elementum uses).

Umbrella's source window (resources/lib/windows/source_results.py) asks run() first, through a few lines the
bootstrap service adds to Umbrella at every start (umbrella_hook): pick a quality, then one of the five best
versions in it. The answer is what Umbrella's own window returns, so Umbrella plays it exactly as if it had been
tapped in its list: ('play_Item', item) or (None, '') when cancelled. None means "use Umbrella's own list"
(Show all, or too few sources to be worth a page). Uncached torrents and TorBox cloud folders need Umbrella's own
handling, so they are left to its list.

Kodi-iOS: only sources of the title being played (source_match.py, from Umbrella's meta: title, original title, year,
IMDb/TMDb ids, show/season/episode): the page hides the others behind a "N hidden (wrong title/year)" row, and when
Umbrella's own list opens it has only the verified ones (all hidden: asked first).
"""
import importlib.util,json,os,re,sys,time,types

HERE=os.path.dirname(os.path.abspath(__file__))
ROOT=os.path.dirname(os.path.dirname(HERE))   # service.kodi.ios.bootstrap: resources/skins/Default/720p/DeckSourceSelect.xml
QUALITY={'4K':'4K','2160P':'4K','UHD':'4K','1440P':'1440p','1080P':'1080p','720P':'720p','480P':'480p','SD':'SD'}
LOW={'CAM','SCR','TELE','TS','HDCAM','TELESYNC'}

def playable(item):
 return 'UNCACHED' not in str(item.get('source') or '').upper() and not item.get('cloud_folder')

def label(item):
 """One source as an Elementum-style entry: 'quality (seeds/peers) [size GB] tags - providers\\nrelease name'."""
 q=str(item.get('quality') or 'SD').upper()
 tags=re.sub(r'\s*\d+(?:\.\d+)?\s*[GM]B\s*','',str(item.get('info') or '')).replace('|',' ')
 if q in LOW:tags+=' CAM'  # the Deck page keeps low-quality copies last
 debrid=str(item.get('debrid') or '');provider=str(item.get('provider') or '')
 status='cached' if 'CACHED' in str(item.get('source') or '').upper() else ('unchecked' if 'UNCHECKED' in str(item.get('source') or '').upper() else '')
 providers=', '.join(p for p in (debrid,provider.title() if provider.islower() else provider,status) if p)
 try:size=float(item.get('size') or 0)
 except (TypeError,ValueError):size=0.0
 # Debrid links have no seeders; 1 keeps them "alive" for the ranking, and the page shows no seed count here.
 try:seeds=int(item.get('seeders') or 0)
 except (TypeError,ValueError):seeds=0
 seeds=seeds if not debrid and seeds else 1
 return u'%s (%d/0) [%.2f GB] %s - %s\n%s'%(QUALITY.get(q,'SD'),seeds,size,' '.join(tags.split()),providers,str(item.get('name') or ''))

def load(path=os.path.join(HERE,'deck_picker.py'),addon_path=ROOT):
 """deck_picker with stand-ins for what it imports from Elementum (Umbrella runs without it), and Umbrella's
 wording: sources come cached from a debrid service, so there is no seed count to show."""
 if 'kodi_six' not in sys.modules:
  import xbmc,xbmcgui
  six=types.ModuleType('kodi_six');six.xbmc=xbmc;six.xbmcgui=xbmcgui;sys.modules['kodi_six']=six
 try:import elementum.dialog,elementum.addon  # noqa: F401 (the real one, if this process has it)
 except ImportError:
  pkg=types.ModuleType('elementum');pkg.__path__=[]
  dialog=types.ModuleType('elementum.dialog');dialog.ACTION_PARENT_DIR=9;dialog.KEY_NAV_BACK=92;dialog.ACTION_PREVIOUS_MENU=10
  addon=types.ModuleType('elementum.addon');addon.ADDON_PATH=addon_path
  pkg.dialog=dialog;pkg.addon=addon
  sys.modules.update({'elementum':pkg,'elementum.dialog':dialog,'elementum.addon':addon})
 spec=importlib.util.spec_from_file_location('umbrella_deck_picker',path);deck=importlib.util.module_from_spec(spec);spec.loader.exec_module(deck)
 deck.meta_text=lambda it:deck.DOT.join([deck.size_text(it)]+([', '.join(it['providers'])] if it['providers'] else []))
 deck.SHOW_ALL_ROW=dict(deck.SHOW_ALL_ROW,tags=u"Umbrella's full list")
 return deck

def share(meta,window=None):
 """Title, poster, background, year/runtime and plot for the page (what the watch menu does for Elementum)."""
 meta=meta or {}
 tv=bool(meta.get('tvshowtitle'))
 title=meta.get('tvshowtitle') if tv else meta.get('title')
 bits=[]
 if tv and meta.get('season') and meta.get('episode'):
  try:bits.append('S%02dE%02d'%(int(meta['season']),int(meta['episode'])))
  except (TypeError,ValueError):pass
 if meta.get('year'):bits.append(str(meta['year']))
 try:minutes=int(float(meta.get('duration') or 0))//60
 except (TypeError,ValueError):minutes=0
 if minutes>0:bits.append('%d min'%minutes)
 values={'Title':title or '','Poster':meta.get('season_poster') or meta.get('poster') or '','Fanart':meta.get('fanart') or '',
         'Meta':'  |  '.join(bits),'Plot':meta.get('plot') or '','Time':str(time.time())}
 if window is None:
  import xbmcgui
  window=xbmcgui.Window(10000)
 for key,value in values.items():window.setProperty('Deck.Picker.'+key,str(value))
 return values

def matcher():
 try:
  import source_match
  return source_match
 except Exception:
  return None

def ask_reveal(message):
 import xbmcgui
 return xbmcgui.Dialog().yesno('Not this title?',message+'\n\nShow them anyway?')

def verify_list(results,exp,sm,ask=None):
 """Umbrella's own list keeps only sources of this title (in place: the window shows self.results). When every
 source would go, ask instead of showing an empty list: False means the person said no (cancel)."""
 if not exp or sm is None or not results:return True
 kept,hidden=sm.split(list(results),exp,name=lambda it:it.get('name') or '')
 sm.report("Umbrella's list",exp,kept,hidden,name=lambda it:it.get('name') or '')
 if not hidden:return True
 if kept:
  results[:]=kept
  return True
 return bool((ask or ask_reveal)('All %d sources look like a different title (%s).'%(len(hidden),sm.reasons_text(hidden))))

def run(results,meta,deck=None,make_item=None,sm=None,ask=None):
 """What Umbrella's source window should return, or None to show Umbrella's own list (which run() has left with
 only the sources of this title, source_match.py)."""
 sm=sm if sm is not None else matcher()
 exp=None
 if sm is not None:
  try:
   exp=sm.from_meta(meta)
   exp=sm.enrich(exp) if exp else None
  except Exception:exp=None
 playable_items=[(n,item) for n,item in enumerate(results or []) if playable(item)]
 if not playable_items:
  return None if verify_list(results,exp,sm,ask) else (None,'')
 deck=deck or load()
 share(meta)
 title=(meta or {}).get('tvshowtitle') or (meta or {}).get('title') or ''
 labels=[label(item) for _,item in playable_items]
 choice=deck.run(title,labels,expect=exp) if exp else deck.run(title,labels)
 if choice is None:
  return None if verify_list(results,exp,sm,ask) else (None,'')
 if choice<0:return (None,'')
 item=playable_items[choice][1]
 if make_item is None:
  import xbmcgui
  make_item=xbmcgui.ListItem
 listitem=make_item()
 listitem.setProperty('umbrella.source_dict',json.dumps([item]))
 return ('play_Item',listitem)

# ---- the lines added to Umbrella ------------------------------------------------------------------------------
HOOK_MARK='# KODI-IOS-DECK-PICKER'
ANCHOR='\tdef run(self):\n\t\tself.doModal()\n'
# r1 (builds up to 111) called self.clearProperties() before returning: Umbrella's window had never been shown, so
# that raised "Window id does not exist", the except fell through to self.doModal(), and Umbrella's own list
# opened after the owner had already picked on the Deck page (owner's debug log, ISSUE-069).
HOOK_R1=('\tdef run(self):\n'
      '\t\ttry:  '+HOOK_MARK+': the Deck\'s "Choose a version" page first (service.kodi.ios.bootstrap)\n'
      '\t\t\timport sys as _ksys, xbmcvfs as _kvfs\n'
      '\t\t\t_klib = _kvfs.translatePath(\'special://xbmc/addons/service.kodi.ios.bootstrap/resources/lib\')\n'
      '\t\t\tif _klib not in _ksys.path: _ksys.path.insert(0, _klib)\n'
      '\t\t\timport umbrella_picker as _kpick\n'
      '\t\t\t_kdeck = _kpick.run(self.results, self.meta)\n'
      '\t\t\tif _kdeck is not None:\n'
      '\t\t\t\tself.clearProperties()\n'
      '\t\t\t\treturn _kdeck\n'
      '\t\texcept Exception:\n'
      '\t\t\tpass\n'
      '\t\tself.doModal()\n')
HOOK=('\tdef run(self):\n'
      '\t\t_kdeck = None\n'
      '\t\ttry:  '+HOOK_MARK+' r2: the Deck\'s "Choose a version" page first (service.kodi.ios.bootstrap)\n'
      '\t\t\timport sys as _ksys, xbmcvfs as _kvfs\n'
      '\t\t\t_klib = _kvfs.translatePath(\'special://xbmc/addons/service.kodi.ios.bootstrap/resources/lib\')\n'
      '\t\t\tif _klib not in _ksys.path: _ksys.path.insert(0, _klib)\n'
      '\t\t\timport umbrella_picker as _kpick\n'
      '\t\t\t_kdeck = _kpick.run(self.results, self.meta)\n'
      '\t\texcept Exception:\n'
      '\t\t\t_kdeck = None\n'
      '\t\tif _kdeck is not None:\n'
      '\t\t\treturn _kdeck\n'
      '\t\tself.doModal()\n')

def umbrella_hook(path):
 """Add the hook to Umbrella's source window (again after an Umbrella update), or replace the r1 hook. Returns True
 if the file changed."""
 if not os.path.isfile(path):return False
 with open(path,encoding='utf-8') as f:text=f.read()
 if HOOK in text:return False
 if HOOK_R1 in text:new=text.replace(HOOK_R1,HOOK)
 elif HOOK_MARK in text or text.count(ANCHOR)!=1:return False
 else:new=text.replace(ANCHOR,HOOK)
 with open(path,'w',encoding='utf-8') as f:f.write(new)
 return True
