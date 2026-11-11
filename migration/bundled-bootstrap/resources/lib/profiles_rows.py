"""Profiles page (Settings > Profiles): one row per Kodi profile, the current one ticked and "Signed in now", then
Add Profile. Pure logic; profiles_page.py reads Kodi (JSON-RPC) and fills portrait/IOSProfiles.xml
(settings_page.profiles_page).

Owner-approved mockup: docs/design/settings-pages-mockups.html, board 09. "Ask Who's Watching" is left out: Kodi keeps
that flag in profiles.xml (useloginscreen), outside the settings JSON-RPC, so the page cannot read or set it."""
MAX = 8                 # profile rows on the page; more stay in Kodi's own Profiles window (Add Profile opens it)
ADD = 'Add Profile'
SIGNED_IN = 'Signed in now'
FOOT = 'Each profile has its own watched history, favourites and Home rows.'
GENERIC_THUMB = 'DefaultUser'   # Kodi's stand-in picture for a profile without one


def initials(name):
    """Two letters for the avatar, as accounts.initials does (kept here so settings_page can load this file alone)."""
    words = [w for w in str(name or '').replace('_', ' ').split() if w[:1].isalnum()]
    return ''.join(w[0] for w in words[:2]).upper() or '?'


def avatar(thumb):
    """The profile's picture, or '' when it has none (Kodi then returns its generic user picture)."""
    text = str(thumb or '')
    return '' if not text or GENERIC_THUMB in text else text


def entries(profiles, current):
    """[{'name', 'current', 'initials', 'thumb'}] from Profiles.GetProfiles; current is System.ProfileName."""
    out = []
    for profile in (profiles or [])[:MAX]:
        name = str(profile.get('label') or '')
        if name:
            out.append({'name': name, 'current': name == current, 'initials': initials(name),
                        'thumb': avatar(profile.get('thumbnail'))})
    return out


def properties(rows):
    """Window properties for IOSProfiles.xml: profile.n.* for row n (1-based) and rows = profiles + Add Profile."""
    props = {'rows': str(len(rows) + 1)}
    for n in range(1, MAX + 1):
        r = rows[n - 1] if n <= len(rows) else {}
        props['profile.%d.name' % n] = r.get('name', '')
        props['profile.%d.initials' % n] = r.get('initials', '')
        props['profile.%d.thumb' % n] = r.get('thumb', '')
        props['profile.%d.current' % n] = 'true' if r.get('current') else ''
    return props


def switch_target(rows, n):
    """The profile name row n switches to, or '' for the current profile or a row that is not there."""
    if 1 <= n <= len(rows) and not rows[n - 1].get('current'):
        return rows[n - 1]['name']
    return ''
