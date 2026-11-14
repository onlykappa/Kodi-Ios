"""Favourites page (Settings > Favourites): the user's favourites as a poster grid, three across. Pure logic;
favourites_page.py reads Kodi (JSON-RPC) and fills portrait/IOSFavourites.xml (settings_page.favourites_page).

Owner-approved mockup: docs/design/settings-pages-mockups.html, board 10. There is no reorder: Kodi's JSON-RPC has
no call to move a favourite. Remove is Favourites.AddFavourite with the same entry, which Kodi toggles off (Kodi 21.3
source: xbmc/favourites/FavouritesService.cpp, AddOrRemove). Script and Android favourites are not removed from here:
removal was only checked against window and media favourites.
"""
MAX = 90            # poster cells on the page (12 rows of three); further favourites stay in Kodi's own window
TITLE = 'Favourites'
EMPTY = 'No favourites yet'
FOOT = 'Long-press a poster anywhere and choose Add to Favourites.'
EMPTY_LINE = 'Hold a poster anywhere and choose Add to Favourites.'   # DEC-045 board F1
FILTERS = (('all', 'All'), ('movie', 'Movies'), ('tv', 'Shows'))     # DEC-045 board F2
READ = ['path', 'window', 'windowparameter', 'thumbnail']   # Favourites.GetFavourites properties
REMOVABLE = ('window', 'media')


def quote(value):
    """A builtin's parameter the way Kodi writes its own favourite actions (StringUtils::Paramify)."""
    return '"%s"' % str(value).replace('\\', '\\\\').replace('"', '\\"')


def action_for(fav):
    """The builtin Kodi's Favourites window runs for this favourite, or '' when iOS cannot run it."""
    kind = fav.get('type')
    path = str(fav.get('path') or '')
    window = str(fav.get('window') or '')
    parameter = str(fav.get('windowparameter') or '')
    if kind == 'window' and window:
        return 'ActivateWindow(%s)' % (window if not parameter else '%s,%s' % (window, quote(parameter)))
    if kind == 'media' and path:
        return 'PlayMedia(%s)' % quote(path)
    if kind == 'script' and path:
        return 'RunScript(%s)' % quote(path)
    return ''


def remove_args(fav):
    """Favourites.AddFavourite parameters naming this favourite, so Kodi removes it."""
    args = {'title': str(fav.get('title') or ''), 'type': fav.get('type')}
    if fav.get('type') == 'window':
        args['window'] = fav.get('window') or ''
        args['windowparameter'] = fav.get('windowparameter') or ''
    else:
        args['path'] = fav.get('path') or ''
    return args


def kind_of(fav):
    """'movie', 'tv' or '' from the favourite's link (TMDb Helper's tmdb_type / type, Kodi's library paths)."""
    import re
    text = ' '.join(str(fav.get(k) or '') for k in ('path', 'windowparameter')).lower()
    if re.search(r'tmdb_type=movie|[?&]type=movie|videodb://movies|/movies?/|info=details.*movie', text):
        return 'movie'
    if re.search(r'tmdb_type=tv|[?&]type=(tv|tvshow|episode)|videodb://tvshows|/tvshows?/|[?&]season=|[?&]episode=', text):
        return 'tv'
    return ''


POSTER_URL = 'https://image.tmdb.org/t/p/w342'
HELPER = 'plugin://plugin.video.themoviedb.helper/'


def imported_entry(item):
    """A grid row for one imported title. It opens like a poster anywhere: a show's seasons page, a movie's play link (the
    app's own "How would you like to watch" chooser, or Continue when it was started: favourites_import_page.open_item)."""
    kind = item.get('kind')
    if kind == 'tv':
        action = 'ActivateWindow(Videos,%s?info=seasons&tmdb_type=tv&tmdb_id=%s,return)' % (HELPER, item.get('tmdb'))
    else:
        action = 'PlayMedia(%s)' % quote('%s?info=play&tmdb_type=movie&tmdb_id=%s' % (HELPER, item.get('tmdb')))
    poster = item.get('poster') or ''
    return {'title': str(item.get('title') or ''), 'thumb': (POSTER_URL + poster) if poster.startswith('/') else poster,
            'action': action, 'removable': True, 'remove': None, 'kind': kind if kind in ('movie', 'tv') else '',
            'imported': item, 'rank': int(item.get('rank') or 0), 'watched': int(item.get('watched') or 0),
            'year': str(item.get('year') or '')}


def shown(rows, filter_key='all'):
    """The favourites the filter shows (Movies / Shows; All shows everything)."""
    return list(rows) if filter_key == 'all' else [r for r in rows if r.get('kind') == filter_key]


def entries(favs):
    """[{'title', 'thumb', 'action', 'removable', 'remove'}] for the grid, in Kodi's order. Favourites iOS cannot open
    are left out."""
    out = []
    for fav in favs or []:
        action = action_for(fav)
        if not action:
            continue
        out.append({'title': str(fav.get('title') or ''), 'thumb': str(fav.get('thumbnail') or ''), 'action': action,
                    'removable': fav.get('type') in REMOVABLE, 'remove': remove_args(fav), 'kind': kind_of(fav)})
        if len(out) >= MAX:
            break
    return out


def properties(rows, ranked=False):
    """Window properties for IOSFavourites.xml: count, and fav.n.title / thumb / removable for cell n (1-based), plus the
    imported list's rank ("#3", only while sorted by list order) and watch count ("3\u00d7") for the poster badges."""
    props = {'count': str(len(rows))}
    for n in range(1, MAX + 1):
        r = rows[n - 1] if n <= len(rows) else {}
        props['fav.%d.title' % n] = r.get('title', '')
        props['fav.%d.thumb' % n] = r.get('thumb', '')
        props['fav.%d.removable' % n] = 'true' if r.get('removable') else ''
        props['fav.%d.rank' % n] = ('#%d' % r['rank']) if ranked and r.get('rank') else ''
        props['fav.%d.watched' % n] = ('%d\u00d7' % r['watched']) if r.get('watched') else ''
    return props
