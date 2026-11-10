"""Remember Umbrella/AllDebrid's selected file in RAM; renew that link once without scraping or downloading again."""
import ast,json,urllib.parse,urllib.request
from pathlib import Path

PROPERTY='KodiIOS.UmbrellaRenewal'
MARK='# KODI-IOS-LINK-RENEWAL'

def web(url):
 try:
  p=urllib.parse.urlsplit(url)
  return p.scheme in ('http','https') and bool(p.hostname)
 except (TypeError,ValueError):return False

def remember(link,response,home=None):
 if not isinstance(response,dict) or not web(response.get('link','')) or not isinstance(link,str) or not 0<len(link)<8192:return
 if home is None:
  import xbmcgui
  home=xbmcgui.Window(10000)
 record={'source':response['link'],'link':link,'size':int(response.get('filesize') or 0),'filename':str(response.get('filename') or '')}
 if len(json.dumps(record))<20000:home.setProperty(PROPERTY,json.dumps(record))

def selected(source,home):
 try:
  record=json.loads(home.getProperty(PROPERTY))
  return record if record.get('source')==source.partition('|')[0] and record.get('link') else None
 except (ValueError,TypeError,AttributeError):return None

def renew(record,context=None,token=None,request=None):
 import alldebrid
 if token is None:
  import xbmcaddon
  token=xbmcaddon.Addon('plugin.video.umbrella').getSetting('alldebridtoken')
 def send(method,url,data=None,headers=None):
  body=urllib.parse.urlencode(data,doseq=True).encode() if data is not None else None
  req=urllib.request.Request(url,data=body,headers=headers or {},method=method)
  with urllib.request.urlopen(req,timeout=15,context=context) as response:return response.read()
 url,name,size=alldebrid.AllDebrid(token,request=request or send).unlock(record['link'])
 if not web(url):raise RuntimeError('The source did not give a valid stream link')
 if record.get('size') and size!=int(record['size']):raise RuntimeError('The refreshed stream is a different file')
 if record.get('filename') and name!=record['filename']:raise RuntimeError('The refreshed stream is a different file')
 return url

def hook(path):
 """Patch only a recognized AllDebrid unlock response, once. Unknown upstream versions remain untouched."""
 path=Path(path)
 if not path.is_file():return False
 text=path.read_text(encoding='utf-8')
 if MARK in text:return False
 try:
  tree=ast.parse(text)
  cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='AllDebrid')
  method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='unrestrict_link')
 except (SyntaxError,StopIteration):return False
 lines=text.splitlines(keepends=True);body=''.join(lines[method.lineno-1:method.end_lineno])
 anchor="\t\t\tresponse = self._get(url, url_append)\n"
 if body.count(anchor)!=1 or 'link' not in [a.arg for a in method.args.args]:return False
 injection=('\t\t\ttry: '+MARK+'\n'
            '\t\t\t\timport sys as _ksys, xbmcvfs as _kvfs\n'
            "\t\t\t\t_klib = _kvfs.translatePath('special://xbmc/addons/service.kodi.ios.bootstrap/resources/lib')\n"
            '\t\t\t\tif _klib not in _ksys.path: _ksys.path.insert(0, _klib)\n'
            '\t\t\t\timport umbrella_recovery as _krenew\n'
            '\t\t\t\t_krenew.remember(link, response)\n'
            '\t\t\texcept Exception: pass\n')
 lines[method.lineno-1:method.end_lineno]=[body.replace(anchor,anchor+injection)]
 updated=''.join(lines)
 try:compile(updated,str(path),'exec')
 except SyntaxError:return False
 path.write_text(updated,encoding='utf-8');return True
