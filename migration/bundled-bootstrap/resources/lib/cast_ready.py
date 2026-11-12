"""Roadmap 1G.8 (owner: "if the file is already good then no conversion is needed"; "yes" to offering a choice):
Play on TV on a download that preparation has not finished would convert it live on the phone and can stutter.
Before the TV is picked, the owner chooses Prepare first (front of the queue, converted once) or Play now."""
import re
import urllib.parse

DIRECT = re.compile(r'^/download/[^/]+/[^/]+/([^/]+)/')


def item_id(playing):
    """The Drive file id of what Kodi plays (the Drive add-on's play link or its local stream address), or ''."""
    url = str(playing or '').split('|', 1)[0]
    parts = urllib.parse.urlsplit(url)
    if parts.scheme == 'plugin' and parts.netloc == 'plugin.googledrive':
        return (urllib.parse.parse_qs(parts.query).get('item_id') or [''])[0]
    if parts.scheme == 'http' and parts.hostname in ('127.0.0.1', 'localhost'):
        m = DIRECT.match(parts.path)
        return urllib.parse.unquote(m.group(1)) if m else ''
    return ''


def not_ready(view, ident, probe_of=lambda row: row.get('probe')):
    """True when this Drive file is waiting for or in preparation (library_view rows) and its picture needs
    converting (or that is not known yet), so the TV would get a live conversion. A file whose picture is copied as it
    is (HEVC or 8-bit H.264 that only needs repackaging) plays live without stutter: False, as for ready or unknown."""
    if not ident:
        return False
    rows = (view or {}).get('rows') or {}
    for row in (rows.get('waiting') or []) + (rows.get('preparing') or []):
        if row.get('id') == ident:
            probe = probe_of(row) or {}
            return probe.get('copy_video') is not True
    return False


SHEET = {'heading': 'Not ready for the TV yet', 'sub': 'This video still needs converting so it plays smoothly.',
         'rows': [{'label': 'Prepare first', 'detail': 'Converts it once, then it plays on the TV as it is'},
                  {'label': 'Play now', 'detail': 'Converts live on this iPhone · may stutter'}]}
