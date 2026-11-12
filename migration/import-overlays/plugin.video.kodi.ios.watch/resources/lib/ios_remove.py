"""Long press › Remove on a downloaded title (owner, 2026-11-12: a Downloaded TV Shows card with no name, only a torrent
id, "needs to be gone": "add a remove option that deletes the files and everything ... say remove in red").

The menu draws any row named Remove in red (portrait.CTX_RED). Remove asks first (iOS alert, red Remove), then:
- Google Drive: the show's folder or the file goes to Drive's Trash (drivelibrary.trash; restorable for 30 days, the
  app never deletes permanently), and it leaves the saved Library listing at once;
- this iPhone: the show's episode files or the movie file are deleted, and folders left empty under Kodi Downloads go;
- Continue Watching drops the cards that played those copies.
Kodi's own library rows (not downloads) get no Remove.

plugin://plugin.video.kodi.ios.watch/?action=library_remove&kind=tv|movie&name=N[&drive=ID][&file=PATH][&show=T&year=Y&any=1]
"""
import os,re,urllib.parse
ME='plugin://plugin.video.kodi.ios.watch/'
STOP=('Movies','TV Shows','Kodi Downloads','Elementum Downloads','Documents')


def show_key(title):return re.sub(r'[^0-9a-z]+','',str(title).casefold())


def target(path,label,info):
    """The remove request for a Library row, or None (Kodi's own library, the Refresh row)."""
    if info.get('source') not in ('local','drive','both'):return None
    kind='movie' if info.get('mediatype')=='movie' else 'tv'
    out={'kind':kind,'name':label}
    url=urllib.parse.urlsplit(str(path))
    query={k:v[0] for k,v in urllib.parse.parse_qs(url.query).items()}
    if url.scheme=='plugin' and url.netloc=='plugin.video.kodi.ios.watch' and query.get('action')=='library_play':
        return target(query.get('path',''),label,info)
    if url.scheme=='plugin' and url.netloc=='plugin.googledrive':
        if not query.get('item_id'):return None
        out['drive']=query['item_id']
    elif url.scheme=='plugin' and url.netloc=='plugin.video.kodi.ios.watch' and query.get('action')=='library':
        if query.get('folder'):out['drive']=query['folder']
        if query.get('local')=='1' or query.get('merge')=='1':
            out.update(show=query.get('show') or label,year=query.get('year',''))
            if query.get('merge')=='1':out['any']='1'
        if not out.get('drive') and not out.get('show'):return None
    elif url.scheme in ('','file') and str(path).startswith('/'):
        out['file']=str(path)
    else:
        return None
    return out


def menu_entry(path,label,info):
    """('Remove', RunPlugin(...)) for addContextMenuItems, or None."""
    t=target(path,label,info)
    return ('Remove','RunPlugin(%s?%s)'%(ME,urllib.parse.urlencode(dict(action='library_remove',**t)))) if t else None


def local_files(params,completed,parse):
    """The phone files Remove deletes: the one file, or every completed episode of the show. Only files the app lists
    as completed downloads are ever touched."""
    done=set(completed)
    if params.get('file'):
        return [params['file']] if params['file'] in done else []
    if not params.get('show'):return []
    want=show_key(params['show']);year=params.get('year','')
    out=[]
    for path in sorted(done):
        info=parse(os.path.basename(path));title=info.get('title') or ''
        if show_key(title)!=want:
            # A season pack names only S01E02: the show is the folder's name.
            parent=next((p for p in reversed(os.path.dirname(path).split(os.sep)) if p and not re.match(r'^(?:season\b|s\d+\b)',p,re.I)),'')
            if parent in STOP or show_key(parse(parent).get('title') or '')!=want:continue
        if year and not params.get('any') and info.get('year') and str(info['year'])!=str(year):continue
        out.append(path)
    return out


def delete_files(paths,remove=os.remove,rmdir=os.rmdir,listdir=os.listdir):
    """Deletes the files, then each folder they leave empty, stopping at Kodi Downloads' own folders. Returns how many
    files went."""
    gone=0;folders=set()
    for path in paths:
        try:
            remove(path);gone+=1
        except FileNotFoundError:
            gone+=1
        except OSError:
            continue
        folders.add(os.path.dirname(path))
    for folder in sorted(folders,key=len,reverse=True):
        while folder and os.path.basename(folder) not in STOP:
            try:
                if listdir(folder):break
                rmdir(folder)
            except OSError:
                break
            folder=os.path.dirname(folder)
    return gone


def forget_listing(cache,drive_id):
    """The saved Library listing without the removed Drive item (and the removed show's own episode list)."""
    out={}
    for slot,hit in cache.items():
        if not isinstance(hit,dict):out[slot]=hit;continue
        if slot.split(':',1)[-1]==drive_id:continue
        out[slot]=dict(hit,entries=[e for e in hit.get('entries') or [] if e.get('id')!=drive_id])
    return out


def forget_continue(data,drive_id='',files=()):
    """Continue Watching without the cards that played the removed copies."""
    def gone(entry):
        where=str(entry.get('path') or '')
        return bool((drive_id and drive_id in where) or (where and where in files))
    data['items']={k:v for k,v in (data.get('items') or {}).items() if not gone(v)}
    return data


def run(params):
    import xbmc,xbmcgui,xbmcvfs
    from ios_library import STATE,boot_path
    boot_path(xbmcvfs)
    import drivelibrary as lib
    name=params.get('name') or 'this download'
    where=[]
    if params.get('drive'):where.append('Google Drive (it stays in Drive’s Trash for 30 days)')
    if params.get('file') or params.get('show'):where.append('this iPhone')
    if not where:return
    if not xbmcgui.Dialog().yesno('Remove “%s”?'%name,'Its files are deleted from %s. This cannot be undone here.'%' and '.join(where),
                                  nolabel='Cancel',yeslabel='Remove'):
        return
    problems=[];files=[]
    if params.get('file') or params.get('show'):
        try:
            from ios_downloaded import completed_files
            files=local_files(params,completed_files(params.get('kind','tv')),lib.parse)
            delete_files(files)
        except Exception as error:
            problems.append('iPhone');xbmc.log('Kodi iOS Remove: phone files failed: '+type(error).__name__,xbmc.LOGWARNING)
    state=xbmcvfs.translatePath(STATE)
    if params.get('drive'):
        try:
            drive,_=lib.client()
            if not drive:raise RuntimeError('not signed in')
            lib.trash(drive,params['drive'])
            path=os.path.join(state,'drive-library.json')
            lib.save_json(path,forget_listing(lib.load_json(path,{}),params['drive']))
        except Exception as error:
            problems.append('Google Drive');xbmc.log('Kodi iOS Remove: Drive trash failed: '+type(error).__name__,xbmc.LOGWARNING)
    try:
        import ios_continue
        def read(p):
            f=xbmcvfs.File(p)
            try:return f.read()
            finally:f.close()
        def write(p,text):
            f=xbmcvfs.File(p,'w')
            try:f.write(text)
            finally:f.close()
        ios_continue.save(forget_continue(ios_continue.load(read),params.get('drive',''),set(files)),write)
    except Exception:
        pass
    if problems:
        xbmcgui.Dialog().ok('Could not remove everything','“%s” could not be removed from %s. Try again in a moment.'%(name,' and '.join(problems)))
    else:
        xbmcgui.Dialog().notification('Removed',name,xbmcgui.NOTIFICATION_INFO,2500)
    xbmc.executebuiltin('Container.Refresh')
