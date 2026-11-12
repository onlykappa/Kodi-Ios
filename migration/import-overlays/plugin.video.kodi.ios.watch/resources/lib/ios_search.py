"""Search results in sections (owner-approved board 12, docs/design/fuse-windows-mockups.html): MOVIES, then TV SHOWS,
each under a header row, for the Search page's All filter. TMDb Helper still does the searching: its movie and TV
searches run side by side (Files.GetDirectory), and this list hands their items back grouped. A Kodi list cannot
draw a heading between items, so each heading is an item of its own (property header) that the page draws as a
small grey caption (portrait.search_window)."""
import json
import threading
from urllib.parse import quote

TMDB = 'plugin://plugin.video.themoviedb.helper/?info=search&tmdb_type=%s&query=%s'
SECTIONS = (('movie', 'MOVIES'), ('tv', 'TV SHOWS'))
PER_SECTION = 6   # All shows the best few of each, so TV SHOWS is not pushed off the screen; the filters list them all
PROPERTIES = ['title', 'year', 'art', 'plot', 'genre', 'rating', 'mpaa']   # Files.GetDirectory's own field names only


def grouped(results):
    """[(kind, title, [files])] -> [('header', title) | ('item', kind, file)]; a section without results is left out."""
    out = []
    for kind, title, files in results:
        if not files:
            continue
        out.append(('header', title))
        out.extend(('item', kind, f) for f in files[:PER_SECTION])
    return out


def fetch(rpc, query):
    """Both TMDb Helper searches at once: [(kind, title, files)] in SECTIONS order."""
    found = {}

    def one(kind):
        request = {'jsonrpc': '2.0', 'id': 1, 'method': 'Files.GetDirectory',
                   'params': {'directory': TMDB % (kind, quote(query)), 'media': 'video', 'properties': PROPERTIES}}
        try:
            found[kind] = (json.loads(rpc(json.dumps(request))).get('result') or {}).get('files') or []
        except (ValueError, TypeError, AttributeError):
            found[kind] = []
    threads = [threading.Thread(target=one, args=(kind,)) for kind, _ in SECTIONS]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    return [(kind, title, found.get(kind) or []) for kind, title in SECTIONS]


def directory(handle, query):
    import xbmc
    import xbmcgui
    import xbmcplugin
    query = ' '.join(str(query or '').split())
    rows = []
    for entry in grouped(fetch(xbmc.executeJSONRPC, query)) if query else []:
        if entry[0] == 'header':
            li = xbmcgui.ListItem(entry[1])
            li.setProperty('header', 'true')
            rows.append(('', li, False))
            continue
        _, kind, f = entry
        li = xbmcgui.ListItem(f.get('label') or f.get('title') or '')
        li.setArt(f.get('art') or {})
        tag = li.getVideoInfoTag()
        tag.setMediaType('movie' if kind == 'movie' else 'tvshow')
        tag.setTitle(f.get('title') or f.get('label') or '')
        if f.get('year'):
            tag.setYear(int(f['year']))
        if f.get('plot'):
            tag.setPlot(f['plot'])
        li.setProperty('tmdb_type', kind)
        rows.append((f.get('file') or '', li, f.get('filetype') == 'directory'))
    xbmcplugin.addDirectoryItems(handle, rows)
    xbmcplugin.setContent(handle, 'videos')
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)
