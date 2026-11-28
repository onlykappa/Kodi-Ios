"""One Pace (the fan re-cut of One Piece, onepace.net) as an ordinary show: arcs are its seasons, episodes play straight from Pixeldrain (plain MP4, ranged reads),
English Dub only (owner, 2026-11-28). Our own parser of the public watch page and the release feed; nothing here is copied from another project.

watch page -> arcs [{'slug','title','chapters','anime','episodes':[{'id','number','title','minutes','plot','variants':{'English Dub':{'1080p':url,...},...}}]}]
feed       -> releases [{'title','arcs_hint','date','category','hash'}] to notice new episodes and new arcs before the page lists them.
Everything is a pure function of text (tests use recorded samples); the network lives in `fetch`, which the callers inject."""
import html,json,re,time,urllib.parse

WATCH='https://onepace.net/en/watch'
FEED='https://onepace.net/en/releases/rss.xml'
DUB='English Dub'
RESOLUTIONS=('1080p','720p','480p')   # best first
FILE_URL='https://pixeldrain.net/api/file/%s'
SHOW_ID='onepace'
SHOW_TITLE='One Pace'

def clean(text):
 """Page text with the page's own non-breaking and figure spaces folded to plain spaces."""
 return re.sub(r'\s+',' ',html.unescape(str(text or '')).replace(' ',' ').replace('\xa0',' ')).strip()

def strip_tags(fragment):
 return clean(re.sub(r'<[^>]+>',' ',re.sub(r'<!--.*?-->','',fragment,flags=re.S)))

SITE='https://onepace.net'
WIDTHS=(640,750,828,1080,1200,1920,2048,3840)   # the sizes the site's image service offers

def image_source(fragment):
 """The site's own address (path and query) of the first picture in a piece of the page, or '' (only its image service for its own pictures is accepted)."""
 for tag in re.findall(r'<img\b[^>]*>',str(fragment or '')):
  m=re.search(r'\bsrc="(/_next/image\?url=%2F_next%2Fstatic%2Fmedia%2F[^"]+)"',tag)
  if m:return html.unescape(m.group(1))
 return ''

def image_url(source,width=1080):
 """A full address for a picture at one of the site's offered widths, or '' for anything that is not its image service."""
 if not str(source or '').startswith('/_next/image?url=%2F_next%2Fstatic%2Fmedia%2F'):return ''
 width=min((w for w in WIDTHS if w>=int(width)),default=WIDTHS[-1])
 return SITE+re.sub(r'([?&])w=\d+',r'\g<1>w=%d'%width,source)

def pixeldrain_id(url):
 m=re.match(r'https://pixeldrain\.(?:net|com)/u/([A-Za-z0-9]+)$',str(url or ''))
 return m.group(1) if m else ''

def file_url(url):
 """The address that serves the file itself (ranged MP4) for a Pixeldrain page link, or ''."""
 ident=pixeldrain_id(url)
 return FILE_URL%ident if ident else ''

def parse_watch(page):
 """Arcs, their episodes and every watch / download link of the page. Unknown markup gives fewer arcs, never an exception."""
 text=str(page or '')
 start=text.find('<main')
 text=re.sub(r'<svg.*?</svg>','',text[start if start>=0 else 0:],flags=re.S)
 marks=[(m.start(),m.group(1)) for m in re.finditer(r'<li\b[^>]*\bdata-timeline-segment="([a-z0-9-]+)"',text)]
 arcs=[]
 for n,(begin,slug) in enumerate(marks):
  end=marks[n+1][0] if n+1<len(marks) else len(text)
  block=text[begin:end]
  heading=re.search(r'<h2\b[^>]*>(.*?)</h2>',block,re.S)
  parts=re.split(r'(?=<li\b[^>]*\bid="%s-\d+"[^>]*\bvalue="\d+")'%re.escape(slug),block)
  head=strip_tags(parts[0])
  summary=re.search(r'<p\b[^>]*>(.*?)</p>',parts[0],re.S)
  chapters=re.search(r'Covered manga chapters\s*([0-9][0-9,\s–\-]*)',head)
  anime=re.search(r'Covered anime episodes\s*(.+?)(?:Duration|Covered|$)',head)
  episodes=[]
  for part in parts[1:]:
   ident=re.search(r'id="(%s-\d+)"'%re.escape(slug),part)
   number=re.search(r'\bvalue="(\d+)"',part)
   title=re.search(r'<h3\b[^>]*>(.*?)</h3>',part,re.S)
   plot=re.search(r'</h3>.*?<p\b[^>]*>(.*?)</p>',part,re.S)
   minutes=re.search(r'Duration\s*(\d+)\s*min',strip_tags(part))
   variants={}
   for chunk in re.split(r'<li\b[^>]*aria-labelledby=',part)[1:]:
    name=re.search(r'>\s*([^<>]+?)\s*<',chunk)
    links=re.findall(r'href="(https://pixeldrain\.(?:net|com)/u/[A-Za-z0-9]+)"[^>]*>\s*<span[^>]*>\s*Pixeldrain:?\s*</span>\s*(?:<span[^>]*>\s*(\d{3,4}p)\s*</span>)?',chunk)
    label=clean(name.group(1)) if name else ''
    if label and links and label!='All-in-One':
     found=variants.setdefault(label,{})
     for url,res in links:
      if res:found[res]=url
   if ident and number:
    episodes.append({'id':ident.group(1),'number':int(number.group(1)),'title':re.sub(r'^\d+\s*:\s*','',strip_tags(title.group(1))) if title else '',
                     'minutes':int(minutes.group(1)) if minutes else 0,'plot':strip_tags(plot.group(1)) if plot else '','image':image_source(part),'variants':variants})
  arcs.append({'slug':slug,'title':strip_tags(heading.group(1)) if heading else slug,'chapters':clean(chapters.group(1)) if chapters else '',
               'anime':clean(anime.group(1)) if anime else '','description':strip_tags(summary.group(1)) if summary else '','image':image_source(parts[0]),'episodes':episodes})
 return arcs

DUB_VARIANTS=('English Dub','English Dub with Dubtitles','English Dub with Closed Captions')   # best first: plain dub, then a dub whose captions are burned in
JAPANESE_VARIANT='English Subtitles'   # Japanese audio; the English subtitles are burned into the picture (the Pixeldrain files have only a video and an audio track)

def choose(episode,resolutions=RESOLUTIONS,prefer='dub'):
 """The file to play for an episode: {'audio': 'English dub' | 'Japanese', 'japanese_only': bool, 'resolution', 'page', 'file'} or None when it has neither yet.
 Owner (2026-11-28): the English dub whenever one exists, otherwise Japanese with English subtitles (the episode is then marked Japanese only);
 prefer='japanese' picks the Japanese file for an episode that also has a dub (the viewer asked for it)."""
 variants=episode.get('variants') or {}
 def best(names):
  for name in names:
   files=variants.get(name) or {}
   for res in resolutions:
    if files.get(res):return res,files[res]
  return None
 dub=best(DUB_VARIANTS);ja=best((JAPANESE_VARIANT,))
 if prefer=='japanese' and ja:dub=None
 got=dub or ja
 if not got:return None
 audio='English dub' if dub else 'Japanese'
 return {'audio':audio,'japanese_only':not best(DUB_VARIANTS),'resolution':got[0],'page':got[1],'file':file_url(got[1])}

def dub_choice(episode,resolutions=RESOLUTIONS):
 """Kept for callers of the first version: (resolution, page link) of the English dub, or None."""
 got=choose(episode,resolutions)
 return (got['resolution'],got['page']) if got and got['audio']=='English dub' else None

def seasons(arcs):
 """The show as the app lists it: every arc is a season, every released episode is an episode (English dub where there is one, else Japanese with English
 subtitles, marked japanese_only); an arc with no episode at all stays as an empty 'upcoming' season."""
 out=[]
 for number,arc in enumerate(arcs,1):
  episodes=[]
  for episode in arc['episodes']:
   got=choose(episode)
   if got:episodes.append(dict(episode,**got))
  out.append({'season':number,'slug':arc['slug'],'title':arc['title'],'chapters':arc['chapters'],'description':arc.get('description',''),'image':arc.get('image',''),'episodes':episodes,'upcoming':not episodes,
              'released':len(arc['episodes']),'dubbed':sum(1 for e in episodes if not e['japanese_only'])})
 return out

dub_arcs=seasons

def parse_feed(xml):
 """Release entries of the feed, newest first as listed: title, date, category, torrent hash. Only what the feed says; a malformed feed gives []."""
 out=[]
 for item in re.findall(r'<item>(.*?)</item>',str(xml or ''),re.S):
  def tag(name):
   m=re.search(r'<%s\b[^>]*>(.*?)</%s>'%(name,name),item,re.S)
   return clean(m.group(1)) if m else ''
  title=tag('title')
  if not title:continue
  m=re.match(r'\[One Pace\]\[([^\]]*)\]\s*(.+?)(?:\s*-\s*(Extended Cut|Alternate[^\[]*))?\s*\[(\d{3,4}p)\]',title)
  out.append({'title':title,'chapters':m.group(1) if m else '','name':m.group(2) if m else '','resolution':m.group(4) if m else '',
              'date':tag('pubDate'),'category':tag('category'),'hash':tag('torrent:infoHash') or tag('guid')})
 return out

def signature(seasons):
 """{arc slug: [playable episodes, dubbed episodes]}: the state that a new episode, a new dub or a new arc changes."""
 return {s['slug']:[len(s['episodes']),s['dubbed']] for s in seasons}

def changes(before,seasons):
 """What is new since `before` (a signature; {} the first time, which reports nothing): new arcs, new episodes, and episodes that now have an English dub."""
 new=[]
 if not before:return new
 for s in seasons:
  old=before.get(s['slug'])
  if old is None:new.append({'kind':'arc','arc':s['title'],'episodes':len(s['episodes'])})
  else:
   if len(s['episodes'])>old[0]:new.append({'kind':'episode','arc':s['title'],'count':len(s['episodes'])-old[0],'latest':s['episodes'][-1]['number']})
   if s['dubbed']>old[1]:new.append({'kind':'dub','arc':s['title'],'count':s['dubbed']-old[1]})
 return new
