"""Sports reminders (owner-approved game page, docs/design/sports-game-mockups.html board C).

"Remind me" on a game asks what to be reminded about (a source is ready; 15 minutes before it starts). A saved reminder is checked
in the background; a notification goes out once per reason, and the page's button turns into Play when a source exists. Kept in
sports-reminders.json in the add-on's data folder. Pure apart from that file, so it is host-tested.
"""
import json
import os

FILE = 'sports-reminders.json'
BEFORE = 15 * 60          # seconds before the start for the "15 minutes before" reminder
KEEP_AFTER = 6 * 3600     # a reminder is dropped this long after the game started


def path(profile):
    return os.path.join(str(profile), 'addon_data', 'service.kodi.ios.bootstrap', FILE)


def load(profile):
    try:
        with open(path(profile), encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return {str(k): v for k, v in data.items() if isinstance(v, dict)} if isinstance(data, dict) else {}


def save(profile, data):
    target = path(profile)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    tmp = target + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(data, handle)
    os.replace(tmp, target)


def title_of(game):
    away, home = (game.get('away') or {}).get('name', ''), (game.get('home') or {}).get('name', '')
    return '%s %s %s' % (away, game.get('joiner') or 'vs', home) if home else away   # a tournament or race weekend has just its title


def set_reminder(profile, game, on_source=True, before=True):
    """Turn a reminder on for a game (both off removes it). Returns the saved record or None."""
    data = load(profile)
    gid = str(game['id'])
    if not (on_source or before):
        data.pop(gid, None)
        save(profile, data)
        return None
    old = data.get(gid, {})
    data[gid] = {'title': title_of(game), 'start': int(game.get('start') or 0), 'league': game.get('league', ''),
                 'on_source': bool(on_source), 'before': bool(before),
                 'told_source': bool(old.get('told_source')) and bool(on_source), 'told_before': bool(old.get('told_before')) and bool(before)}
    save(profile, data)
    return data[gid]


def get(profile, game_id):
    return load(profile).get(str(game_id))


def due(reminders, games, now):
    """[(game id, 'source' | 'before', title, text)] still to be sent. `games` maps game id -> its current game (or is missing)."""
    out = []
    for gid, r in reminders.items():
        game = games.get(gid)
        start = int((game or {}).get('start') or r.get('start') or 0)
        if r.get('on_source') and not r.get('told_source') and game and game.get('sources') and now < start + KEEP_AFTER:
            out.append((gid, 'source', r.get('title', 'Game'), 'A source is ready. Tap to play.'))
        if r.get('before') and not r.get('told_before') and 0 < start - now <= BEFORE:
            minutes = max(1, int((start - now + 59) // 60))
            out.append((gid, 'before', r.get('title', 'Game'), 'Starts in %d minute%s.' % (minutes, '' if minutes == 1 else 's')))
    return out


def sent(profile, gid, kind):
    data = load(profile)
    if gid in data:
        data[gid]['told_' + kind] = True
        save(profile, data)


def prune(profile, now):
    data = load(profile)
    keep = {g: r for g, r in data.items() if now < int(r.get('start') or 0) + KEEP_AFTER}
    if len(keep) != len(data):
        save(profile, keep)
    return keep


def pending(reminders):
    """Game ids whose source search is still worth running (a source reminder not yet sent)."""
    return [g for g, r in reminders.items() if r.get('on_source') and not r.get('told_source')]


def summary(reminder):
    """The note under 'Reminder on' ('' when there is none)."""
    if not reminder:
        return ''
    source, before = reminder.get('on_source'), reminder.get('before')
    if source and before:
        return "We'll notify you when a source is ready, and 15 minutes before it starts."
    if source:
        return "We'll notify you when a source is ready."
    if before:
        return "We'll notify you 15 minutes before it starts."
    return ''


def action(game_id):
    """What tapping the notification runs: the game's page (sports_game, id URL-quoted so it survives RunScript's commas)."""
    from urllib.parse import quote
    return 'RunScript(service.kodi.ios.bootstrap,sports_game,%s)' % quote(str(game_id), safe='')


def check(profile, provider, notify, now, search_every=600, state=None, log=lambda text: None):
    """One pass: look at every saved reminder, ask the provider for the game's sources, send what is due once. Returns the number sent.
    state: a dict that remembers when each game's source search was last asked (so it is not asked every pass)."""
    state = {} if state is None else state
    reminders = prune(profile, now)
    if not reminders:
        return 0
    games = {}
    for gid in reminders:
        try:
            games[gid] = provider.game(gid)
        except Exception as error:
            log('reminder: game lookup failed (%s)' % type(error).__name__)
    for gid in pending(reminders):
        r, game = reminders[gid], games.get(gid)
        start = int((game or {}).get('start') or r.get('start') or 0)
        if game and not game.get('sources') and now - state.get(gid, 0) >= search_every and 0 < start - now <= 3 * 3600 + KEEP_AFTER:
            state[gid] = now
            try:
                provider.request_game(gid)
            except Exception as error:
                log('reminder: source search failed (%s)' % type(error).__name__)
    count = 0
    for gid, kind, title, text in due(reminders, games, now):
        try:
            notify(title, text, action(gid))
        except Exception as error:
            log('reminder: notification failed (%s)' % type(error).__name__)
            continue
        sent(profile, gid, kind)
        count += 1
    return count


def watch(profile, get_provider, notify, wait, clock=None, every=120, log=lambda text: None):
    """The service loop: check every `every` seconds until `wait(seconds)` says to stop."""
    import time
    clock = clock or time.time
    state = {}
    while not wait(every):
        try:
            if load(profile):
                check(profile, get_provider(), notify, int(clock()), state=state, log=log)
        except Exception as error:
            log('reminder: check failed (%s)' % type(error).__name__)
