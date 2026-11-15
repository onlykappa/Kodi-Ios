"""What a notification means and what can be done about it (DEC-046, docs/design/notification-detail-mockups.html).

explain(item) turns a stored notice ({'kind', 'title', 'text', 'action'}) into the sheet's plain parts:
  {'title', 'line', 'happened', 'safe', 'good', 'fixes': [(label, sub, action)], 'facts': [(label, value)]}
'title' and 'line' are also the Notifications list row (two lines each, never cut to "…": owner, DEC-046). 'fixes[0]'
is the primary capsule and the list row's Fix button. An action is a key notifications.py runs (FIX_ACTIONS) or the
notice's own builtin ('notice'). Unknown problems get the H2 shape: plain words, Share the log.
Pure: no Kodi calls, so every entry is host-tested.
"""
import re

FIX_ACTIONS = {
    'library_status': 'RunScript(service.kodi.ios.bootstrap,library_status)',
    'library_files': 'RunScript(service.kodi.ios.bootstrap,library_manager)',
    'problems': 'RunScript(service.kodi.ios.bootstrap,copy_problems)',
    'accounts': 'RunScript(service.kodi.ios.bootstrap,accounts_page)',
    'share_log': 'RunScript(service.kodi.ios.bootstrap,export_logs)',
    'setup': 'RunScript(service.kodi.ios.bootstrap,recover)',
    'upscale': 'RunScript(service.kodi.ios.bootstrap,upscale_settings)',
    'retry_copies': '',      # notifications.py: debrid_drive.retry_failed
}


def _video(text):
    """'Naruto Shippuuden · S1 E16' from 'Naruto Shippuuden · S1 E16: This file has …'."""
    head = str(text or '').split(': ', 1)
    return head[0] if len(head) == 2 and len(head[0]) < 80 else ''


# (pattern on 'title: text', builder(item, video) -> dict). First match wins.
def _kept_tracks(item, video):
    return {'title': "Couldn't prepare %s" % (video or 'this video'),
            'line': "It has a track an MP4 can't keep",
            'happened': 'This file has DVD picture subtitles or a second video track an MP4 can\'t keep, so it couldn\'t be made '
                        'ready for AirPlay.',
            'safe': 'Nothing was lost: the original is on Google Drive and plays in Kodi.',
            'fixes': [('Find Another Version', "In the show's page: ••• › Pick Better Versions", 'library_files'),
                      ('Open Library status', 'See this video and what waits', 'library_status')]}


def _prep_problem(item, video):
    return {'title': "Couldn't prepare %s" % (video or 'a video'),
            'line': 'It will try again by itself',
            'happened': 'Getting this video ready for Kodi and AirPlay stopped: %s.' % _plain(item.get('text')),
            'safe': 'Nothing was lost: the original is on Google Drive and plays in Kodi.',
            'fixes': [('Open Library status', 'Try it again, or keep it as it is', 'library_status')]}


def _copy_problem(item, video):
    text = str(item.get('text') or '')
    blocked = re.search(r'(?i)blocked|sign-?in|unauthor|401|403', text)
    busy = re.search(r'(?i)busy|503|502|timed out|network|connection', text)
    # ISSUE-277: "is waiting" only when it really waits (busy or blocked); a copy that ended says it couldn't be copied.
    out = {'title': ('%s is waiting' % video) if video and (blocked or busy) else ("Couldn't copy %s" % video) if video
           else "Couldn't download to Google Drive",
           'line': 'AllDebrid blocked the sign-in' if blocked else 'AllDebrid was busy' if busy else 'It stopped; see why',
           'happened': ('AllDebrid blocked the sign-in from this network. Copies wait and carry on by themselves once it lets '
                        'them in.') if blocked else ('AllDebrid or the connection was busy. Copies wait and carry on by '
                                                     'themselves.') if busy else 'The copy to Google Drive stopped: %s.' % _plain(text),
           'warn': bool(blocked or busy),
           'fixes': [('Open Download problems', 'Everything that stopped, in one place', 'problems'),
                     ('Retry now', 'Try the copy again straight away', 'retry_copies')]}
    if blocked:
        out['fixes'].insert(0, ('Open Accounts', 'Check AllDebrid is signed in', 'accounts'))
    return out


def _fetching(item, video):
    """ISSUE-277 (owner screenshot, build 430): "AllDebrid is fetching it" is news, not a failure. It opened as "Couldn't
    download to Google Drive · The copy to Google Drive stopped" because the copy-problem rule matched the word AllDebrid."""
    what = str(item.get('text') or '').strip() or 'this video'
    return {'title': 'AllDebrid is fetching %s' % what, 'line': 'The copy starts once AllDebrid has it',
            'happened': "AllDebrid didn't have this version stored, so it is downloading it first. The copy to Google Drive "
                        "starts by itself once it has it. If nobody shares this version, it moves to Download problems so you "
                        "can pick another one.",
            'safe': 'Nothing else waits for it: the next episodes copy in the meantime.',
            'fixes': [('Open Library status', 'See what is copying and what waits', 'library_status')]}


def _saved(item, video):
    return {'title': str(item.get('title') or 'Saved to Google Drive'), 'line': str(item.get('text') or ''), 'good': True,
            'happened': str(item.get('text') or ''),
            'fixes': [('Open Library', 'See it in your Library', 'library_files')]}


def _setup_problem(item, video):
    return {'title': 'Setup and repair stopped', 'line': 'Run it again or share the log',
            'happened': 'The automatic setup that checks add-ons and settings stopped before it finished, and it didn\'t say why.',
            'safe': 'Everything that was already set up still works.',
            'fixes': [('Run Setup Again', 'Checks add-ons and settings now', 'setup'),
                      ('Share the log', 'Send it to whoever helps you with the app', 'share_log')]}


def _trakt(item, video):
    return {'title': 'Trakt connected', 'line': 'Your Trakt lists can fill Home', 'good': True,
            'happened': 'TMDb Helper signed in to Trakt. Your Trakt lists and "Because you watched" rows can now fill Home.',
            'fixes': [('Open Accounts', "See every service you're signed in to", 'accounts')]}


def _drive_signin(item, video):
    return {'title': 'Sign in to Google Drive again', 'line': 'Copies and preparation wait for it',
            'happened': 'Google Drive refused the saved sign-in. Copies, uploads and preparation wait until you sign in again.',
            'safe': 'Nothing was lost: everything carries on from where it stopped.',
            'fixes': [('Open Accounts', 'Sign in to Google Drive', 'accounts')]}


def _kept_as_is(item, video):
    v = _video(item.get('text')) or str(item.get('text') or '').split(' still plays')[0]
    return {'title': '%s is kept as it is' % v if v else 'Kept as it is', 'line': 'It still plays in Kodi',
            'happened': str(item.get('text') or ''), 'safe': 'Nothing was lost.',
            'fixes': [('Find Another Version', "In the show's page: ••• › Pick Better Versions", 'library_files')]}


def _upscale_ready(item, video):
    return {'title': 'AI Upscale copy ready', 'line': str(item.get('text') or ''), 'good': True,
            'happened': '%s now plays on the TV from its upscaled copy.' % (str(item.get('text') or 'This video')),
            'fixes': [('Open AI Upscale', 'See what is made and what waits', 'upscale')]}


def _quality_choice(item, video):
    """DEC-049 board A: one notice per season when the chosen quality does not exist; Choose opens board B."""
    return {'title': str(item.get('title') or 'Choose a version'), 'line': str(item.get('text') or ''), 'warn': True,
            'happened': 'No version of this season is really the quality you chose, so nothing was downloaded for it yet.',
            'safe': 'Nothing was downloaded at a lower quality without asking you.',
            'fixes': [('Choose', 'Use the best, pick another version, or keep looking', 'notice')]}


RULES = (
    (r'(?i)^no real .* for season', _quality_choice),
    (r'tracks MP4 cannot preserve|MP4 can.t keep', _kept_tracks),
    (r'(?i)^kept as it is', _kept_as_is),
    (r'(?i)trakt authori[sz]ed|trakt connected', _trakt),
    (r'(?i)automatic setup|setup and repair', _setup_problem),
    (r'(?i)sign in to google drive|drive sign-?in', _drive_signin),
    # ISSUE-277: matched on the notice's title. "alldebrid" anywhere also caught "AllDebrid is fetching it" and every
    # "Saved to Google Drive · straight from AllDebrid", which opened as "Couldn't download to Google Drive".
    (r'(?i)^alldebrid is fetching', _fetching),
    (r'(?i)^saved to google drive', _saved),
    (r'(?i)^couldn.t download to google drive', _copy_problem),
    (r'(?i)ai upscale ready', _upscale_ready),
    (r'(?i)video preparation paused|preparation (failed|stopped)', _prep_problem),
)


def _plain(text):
    """The raw message in plain words: no 'original retained', no Python error names, no trailing dot."""
    text = re.sub(r'(?i);?\s*original retained', '', str(text or ''))
    text = re.sub(r'\b[A-Z][A-Za-z]+Error:\s*', '', text)
    text = text.split(': ', 1)[1] if _video(text) else text
    return text.strip().rstrip('.') or 'no reason was given'


def explain(item):
    item = item or {}
    joined = '%s: %s' % (item.get('title', ''), item.get('text', ''))
    video = _video(item.get('text'))
    for pattern, build in RULES:
        if re.search(pattern, joined):
            out = build(item, video)
            break
    else:
        problem = item.get('kind') == 'problem'
        out = {'title': _tidy_title(item.get('title')), 'line': _plain(item.get('text')) if item.get('text') else '',
               'happened': _plain(item.get('text')) if problem else str(item.get('text') or ''),
               'good': not problem, 'fixes': [('Share the log', 'Send it to whoever helps you with the app', 'share_log')] if problem else []}
    out.setdefault('safe', '')
    out.setdefault('good', False)
    out.setdefault('warn', False)
    if item.get('action') and not any(a == 'notice' for _, _, a in out['fixes']):
        out['fixes'].insert(0, ('Open', 'Where this happened', 'notice'))
    out['fixes'] = out['fixes'][:3]
    return out


def _tidy_title(title):
    """'Kodi iOS Automatic Setup and Repair' -> 'Automatic Setup and Repair' (the app's own name says nothing here)."""
    return re.sub(r'^Kodi iOS\s+', '', str(title or '')).strip() or 'Kodi iOS'


def facts(item, records, probe=None):
    """Technical details' table: what step, which video, when (no JSON)."""
    import time as _time
    out = []
    m = re.search(r'phase=([^;]+)', ' '.join(str(r.get('text') or r.get('message') or '') for r in records or []))
    if m:
        out.append(('Step', m.group(1).replace('Step 3 of 3 · ', '').strip()))
    video = probe or {}
    if not video:
        m = re.search(r'video=(\{.*?\})', ' '.join(str(r.get('text') or '') for r in records or []))
        if m:
            try:
                import json
                video = json.loads(m.group(1))
            except ValueError:
                video = {}
    if video.get('height'):
        bits = ['%sp %s' % (video.get('height'), str(video.get('codec') or '').upper().replace('H264', 'H.264').replace('HEVC', 'HEVC'))]
        if video.get('audio_tracks'):
            bits.append('%d audio' % int(video['audio_tracks']))
        if video.get('subtitle_tracks'):
            bits.append('%d subtitle%s' % (int(video['subtitle_tracks']), '' if int(video['subtitle_tracks']) == 1 else 's'))
        out.append(('Video', ' · '.join(bits)))
        if video.get('other_image_subtitles'):
            out.append(('Subtitles', 'DVD picture subtitles'))
    if (item or {}).get('time'):
        out.append(('When', _time.strftime('%d %b %H:%M', _time.localtime(item['time']))))
    return out
