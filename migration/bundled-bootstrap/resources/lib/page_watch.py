"""One log line whenever the library page's folder changes, with what was going on around it (owner, 2026-11-25: tapping outside the "Resume / Play from beginning" menu took
them out of the show to the show list; the log (build 698, c4a0c119) showed two page loads right after the menu closed but not what asked for them).

`step(state, now, path, menu, content)` is called every half second while a video-library window is up; it returns the line to log, or None. The path is shortened to its
action and season/episode (never a Drive id or a query string), so the line carries nothing private. Everything the phone does is injected, so the rules are tested here."""
import re

KEEP = ('action', 'season', 'episode', 'kind')


def short(path):
    """'plugin.video.kodi.ios.watch action=library season=4' for a plugin folder; the scheme and first segment for anything else; '' for an empty path."""
    path = str(path or '')
    if not path:
        return ''
    if path.startswith('plugin://'):
        plugin, _, query = path[len('plugin://'):].partition('/')
        query = query.lstrip('?')
        pairs = [p.split('=', 1) for p in query.split('&') if '=' in p]
        keep = ['%s=%s' % (k, re.sub(r'[^A-Za-z0-9_.-]', '', v)[:24]) for k, v in pairs if k in KEEP]
        return ('%s %s' % (plugin.split('/')[0][:40], ' '.join(keep))).strip()
    return path.split('://', 1)[0] + '://' + path.split('://', 1)[-1].split('/', 1)[0][:30]


def step(state, now, path, menu, content, refreshed_at=0.0):
    """The line for a change of folder, or None. `menu` is True while a context menu is open; `refreshed_at` is when the service last refreshed the Drive lists (0 = never).
    state is a dict kept by the caller: {'path', 'menu_closed_at', 'menu'}."""
    shown = short(path)
    if state.get('menu') and not menu:
        state['menu_closed_at'] = now
    state['menu'] = bool(menu)
    before = state.get('path')
    state['path'] = shown
    if before is None or shown == before or not shown:
        return None
    notes = []
    closed = state.get('menu_closed_at')
    if menu:
        notes.append('a menu is open')
    elif closed is not None and 0 <= now - closed <= 3.0:
        notes.append('the menu closed %.1f s ago' % (now - closed))
    if refreshed_at and 0 <= now - refreshed_at <= 5.0:
        notes.append('the Drive lists were refreshed %.1f s ago' % (now - refreshed_at))
    return 'Kodi iOS page: folder changed from "%s" to "%s" (%s)%s' % (before, shown, content or '-', ' - ' + '; '.join(notes) if notes else '')
