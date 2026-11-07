"""The rows on Home, Movies and TV (Settings › Customisation › Tabs & Rows, round-4 mockups 02-07).

The rows are Skin Variables' widget lists, the same files Fuse's widget editor (Custom_1116) wrote and portrait.py
reads: addon_data/script.skinvariables/nodes/skin.arctic.fuse.3/skinvariables-shortcut-<list>.json, a JSON list of
{label, path, icon, target, widget_style}. Every other key a row has is kept as it is. A row that is off keeps its
place with "disabled": "true" (portrait.usable skips it). The first change to a list keeps a copy of it, which
"Restore Default Rows" puts back. Pure logic: no Kodi modules.
"""
import json,os
from pathlib import Path

NODES='addon_data/script.skinvariables/nodes/skin.arctic.fuse.3/skinvariables-shortcut-%s.json'
DEFAULTS='addon_data/service.kodi.ios.bootstrap/rows-default/%s.json'
# Tabs & Rows: the tab bar's pages that have rows. Library and Search are fixed pages.
TABS=(('home','Home','homewidgets'),('movies','Movies','1102widgets'),('tv','TV Shows','1101widgets'))
STYLES=(('Poster','Poster'),('','Landscape'))   # widget_style value, name (portrait.row draws these two)
TMDB='plugin://plugin.video.themoviedb.helper/?info=%s&tmdb_type=%s'
# Add Row: ready-made rows (label, path), per tab; then "From an add-on…".
CATALOGUE={
 'movie':[('Trending Movies',TMDB%('trending_week','movie')),('Popular Movies',TMDB%('popular','movie')),
          ('Top Rated Movies',TMDB%('top_rated','movie')),('Now Playing',TMDB%('now_playing','movie')),
          ('Upcoming Movies',TMDB%('upcoming','movie')),('Recommended For You',TMDB%('trakt_becauseyouwatched','movie')),
          ('Your Trakt Watchlist',TMDB%('trakt_watchlist','movie')),('My Movie Library','videodb://movies/titles/'),
          ('Recently Added Movies','videodb://recentlyaddedmovies/')],
 'tv':[('Trending Shows',TMDB%('trending_week','tv')),('Popular Shows',TMDB%('popular','tv')),
       ('Top Rated Shows',TMDB%('top_rated','tv')),('Airing Today',TMDB%('airing_today','tv')),
       ('Recommended For You',TMDB%('trakt_becauseyouwatched','tv')),('Your Trakt Watchlist',TMDB%('trakt_watchlist','tv')),
       ('My TV Library','videodb://tvshows/titles/'),('Recently Added Episodes','videodb://recentlyaddedepisodes/')],
}
CATALOGUE['home']=CATALOGUE['movie'][:3]+CATALOGUE['tv'][:3]+[CATALOGUE['movie'][5],CATALOGUE['tv'][4]]
CATALOGUE['movies']=CATALOGUE.pop('movie')

def tab(key):
 for k,name,lst in TABS:
  if k==key:return k,name,lst
 raise ValueError(key)

def path_of(profile,lst):return Path(profile)/(NODES%lst)

def load(profile,lst):
 try:data=json.loads(path_of(profile,lst).read_text(encoding='utf-8'))
 except (OSError,ValueError):return []
 return [dict(w) for w in data if isinstance(w,dict)] if isinstance(data,list) else []

def _write(path,rows):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp')
 tmp.write_text(json.dumps(rows,indent=4,ensure_ascii=False)+'\n',encoding='utf-8');os.replace(tmp,path)

def save(profile,lst,rows):
 """Write the list; the first time, keep what was there for Restore Default Rows."""
 default=Path(profile)/(DEFAULTS%lst);current=path_of(profile,lst)
 if not default.exists() and current.exists():
  default.parent.mkdir(parents=True,exist_ok=True);default.write_bytes(current.read_bytes())
 _write(current,rows)

def restore(profile,lst):
 """Put the kept copy back; False when there is none (the list was never changed here)."""
 default=Path(profile)/(DEFAULTS%lst)
 try:data=default.read_bytes()
 except OSError:return False
 current=path_of(profile,lst);current.parent.mkdir(parents=True,exist_ok=True);current.write_bytes(data)
 return True

def is_on(row):return str(row.get('disabled') or '').lower() not in ('true','1')
def set_on(row,on):
 row=dict(row)
 if on:row.pop('disabled',None)
 else:row['disabled']='true'
 return row

def move(rows,i,step):
 j=i+step
 if not (0<=i<len(rows) and 0<=j<len(rows)):return list(rows)
 rows=list(rows);rows[i],rows[j]=rows[j],rows[i];return rows

def delete(rows,i):return [r for n,r in enumerate(rows) if n!=i]
def rename(rows,i,name):
 rows=list(rows)
 if name.strip():rows[i]=dict(rows[i],label=name.strip())
 return rows
def set_style(rows,i,style):
 rows=list(rows);row=dict(rows[i])
 if style:row['widget_style']=style
 else:row.pop('widget_style',None)
 rows[i]=row;return rows
def add(rows,label,path):
 return list(rows)+[{'label':label,'path':path,'icon':'special://skin/extras/icons/folder.png','target':'videos','widget_style':'Poster'}]

# What Home shows (portrait.hub_body: Continue Watching first, then the list's rows that are titles and on; scripts/
# test_customisation.py checks these match portrait.usable / portrait.in_progress). Owner (build 192): the page listed
# 17 rows, Home had 7 and started with Continue Watching.
def in_progress(row):
 text=(str(row.get('path') or '')+' '+str(row.get('label') or '')).lower()
 return 'inprogress' in text or 'in progress' in text or 'continue watching' in text
def is_titles(row):
 path=str(row.get('path') or '')
 if not path or path.startswith(('RunScript(','ActivateWindow(','library://','$','${')):return False
 return not (path.startswith('plugin://') and '?' not in path)
def why_not_shown(row):
 """'' when Home shows the row (if it is on); otherwise why it never shows."""
 if in_progress(row):return 'Not on Home · Continue Watching already shows these'
 if not is_titles(row):return 'Not on Home · a menu, not a row of titles'
 return ''
def view(rows):
 """Indices into rows in the page's order: the rows Home can show (in Home's order), then the others."""
 shown=[i for i,r in enumerate(rows) if not why_not_shown(r)]
 return shown+[i for i,r in enumerate(rows) if why_not_shown(r)]
def move_shown(rows,i,step):
 """Move row i one place up/down among the rows Home shows (rows Home never shows keep their places)."""
 shown=[n for n,r in enumerate(rows) if not why_not_shown(r)]
 if i not in shown:return list(rows)
 k=shown.index(i)+step
 if not 0<=k<len(shown):return list(rows)
 rows=list(rows);j=shown[k];rows[i],rows[j]=rows[j],rows[i];return rows

def style_name(row):
 return 'Poster' if str(row.get('widget_style') or '').lower()=='poster' else 'Landscape'

def source(path):
 """Where a row's titles come from, in plain words."""
 path=str(path or '')
 if 'plugin.video.themoviedb.helper' in path:return 'TMDb Helper'
 if path.startswith(('videodb://','library://')) or path.endswith('.xsp'):return 'Your library'
 if path.startswith('plugin://'):
  addon=path[len('plugin://'):].split('/')[0].split('?')[0]
  return addon.replace('plugin.video.','').replace('.',' ').title()
 return 'Folder'

def summary(row):
 why=why_not_shown(row)
 if why:return why
 return '%s · %s'%(style_name(row),source(row.get('path'))) if is_on(row) else 'Off · not on Home'

def shown_count(rows):
 """Rows on the page: Continue Watching and every row that is on and can show."""
 return 1+sum(1 for r in rows if is_on(r) and not why_not_shown(r))
def count(profile,lst):return shown_count(load(profile,lst))
def plural(n):return '%d row%s'%(n,'' if n==1 else 's')

def properties(rows,slots):
 """Window properties for the Rows page, slot n = the n-th row in view(rows): row.<n>.title / sub / off / up / down."""
 order=view(rows);shown=[i for i in order if not why_not_shown(rows[i])]
 out={'count':'%s on the page'%plural(shown_count(rows)),'empty':'' if shown else 'Only Continue Watching. Add a row below.'}
 for n in range(1,slots+1):
  i=order[n-1] if n<=len(order) else None;r=rows[i] if i is not None else None
  k=shown.index(i) if i in shown else -1
  out.update({'row.%d.title'%n:(r.get('label','') or 'Untitled') if r else '','row.%d.sub'%n:summary(r) if r else '',
              'row.%d.off'%n:'true' if r is not None and (not is_on(r) or why_not_shown(r)) else '',
              'row.%d.up'%n:'true' if k>0 else '','row.%d.down'%n:'true' if 0<=k<len(shown)-1 else ''})
 out['more']='%d more rows are not shown here.'%(len(rows)-slots) if len(rows)>slots else ''
 return out

def row_properties(row):
 return {'one.title':row.get('label',''),'one.on':'true' if is_on(row) else '','one.style':style_name(row),
         'one.source':source(row.get('path')),'one.path':str(row.get('path') or '')}
