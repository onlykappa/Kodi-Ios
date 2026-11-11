"""Favourites page (Settings > Favourites): the user's favourites as a poster grid, three across. Pure logic;
favourites_page.py reads Kodi (JSON-RPC) and fills portrait/IOSFavourites.xml (settings_page.favourites_page).

Owner-approved mockup: docs/design/settings-pages-mockups.html, board 10. There is no reorder: Kodi's JSON-RPC has
no call to move a favourite. Remove is Favourites.AddFavourite with the same entry, which Kodi toggles off (Kodi 21.3
source: xbmc/favourites/FavouritesService.cpp, AddOrRemove). Script and Android favourites are not removed from here:
removal was only checked against window and media favourites.
"""
MAX = 36            # poster cells on the page (12 rows of three); further favourites stay in Kodi's own window
TITLE = 'Favourites'
EMPTY = 'No favourites yet'
FOOT = 'Long-press a poster anywhere and choose Add to Favourites.'
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


def entries(favs):
    """[{'title', 'thumb', 'action', 'removable', 'remove'}] for the grid, in Kodi's order. Favourites iOS cannot open
    are left out."""
    out = []
    for fav in favs or []:
        action = action_for(fav)
        if not action:
            continue
        out.append({'title': str(fav.get('title') or ''), 'thumb': str(fav.get('thumbnail') or ''), 'action': action,
                    'removable': fav.get('type') in REMOVABLE, 'remove': remove_args(fav)})
        if len(out) >= MAX:
            break
    return out


def properties(rows):
    """Window properties for IOSFavourites.xml: count, and fav.n.title / thumb / removable for cell n (1-based)."""
    props = {'count': str(len(rows))}
    for n in range(1, MAX + 1):
        r = rows[n - 1] if n <= len(rows) else {}
        props['fav.%d.title' % n] = r.get('title', '')
        props['fav.%d.thumb' % n] = r.get('thumb', '')
        props['fav.%d.removable' % n] = 'true' if r.get('removable') else ''
    return props
